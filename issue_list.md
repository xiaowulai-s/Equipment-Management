**问题1: 响应数据双通道消费导致数据错乱**

**位置**: `modbus_protocol.py:810-862` (`_poll_buffer`) + `tcp_driver.py:207-213` (`_receive_loop`)

**问题**: 同一份数据被写入两个通道，但只从一个通道消费：

```
_receive_loop 收到数据:
  ├─→ _append_to_buffer(data)     → 写入 _buffer（字节缓冲区）
  └─→ data_received.emit(data)    → 触发信号
        └─→ _on_driver_response() → 写入 _pending_response

_poll_buffer():
  ├─ 第1步: 检查 _pending_response → 有数据！返回 ← 消费了信号路径
  └─ 第2步: _buffer 中的数据永远没被清除！

```

**后果**:

- 下一次 `_poll_buffer` 调用可能从 `_buffer` 读到**上一次的残留响应**
- 心跳响应在 `_buffer` 中持续累积，后续正常读取可能读到心跳包

**修复方案**: 在 `_on_driver_response` 中不再写 `_pending_response`，统一走 `_buffer` 路径；或在 `_poll_buffer` 消费 `_pending_response` 后同步清除 `_buffer`。

***

#### **问题2: FC08心跳响应污染数据缓冲区**

**位置**: `tcp_driver.py:243-312` (`_send_heartbeat`) + `base_driver.py:59-66` (`_append_to_buffer`)

**问题**: 每10秒发送FC08诊断请求，响应数据通过 `_receive_loop` → `_append_to_buffer` 写入缓冲区。**没有任何代码消费/清除这些心跳响应**。

**后果**:

- 缓冲区无限增长（内存泄漏）
- 正常的 `read_registers` 调用可能从缓冲区读到心跳响应数据，导致：
  - 功能码不匹配（期望FC03，收到FC08）→ 解析失败
  - Transaction ID 不匹配 → 静默错误
  - 数据值完全错乱（温度突然变成诊断回显值）

**修复方案**:

```
# 方案A: 心跳响应单独处理，不入公共缓冲区
def _receive_loop(self):
    data = self._socket.recv(4096)
    if data:
        if self._is_heartbeat_response(data):
            self._on_heartbeat_response(data)  # 单独处理，丢弃
        else:
            self._append_to_buffer(data)
            self.data_received.emit(data)

# 方案B: 使用带Transaction ID匹配的响应队列替代全局缓冲区

```

***

#### **问题3: `_transaction_id` 无锁并发递增**

**位置**:

- `modbus_protocol.py:168` — 工作线程中调用 `_build_tcp_header`
- `tcp_driver.py:267` — 主线程QTimer中调用 `_send_heartbeat`

**问题**: 两个类各自维护 `_transaction_id`，且都无锁保护：

```
# modbus_protocol.py:168
self._transaction_id = (self._transaction_id + 1) % 65536  # 工作线程

# tcp_driver.py:267
self._transaction_id = (self._transaction_id + 1) % 65536  # 主线程(心跳)

```

**后果**: 并发递增导致 Transaction ID 冲突或回绕异常。虽然 Modbus TCP 允许 ID 重复（设备不检查），但如果上层做响应匹配会出错。

**修复**: 加 `threading.Lock` 或改用 `threading.atomic`（Python 3.10+ 可用 `+=` 原子操作对简单计数器在 CPython 中因 GIL 实际安全，但不应依赖 GIL 语义）。

***

#### **问题4: MCGS Service 默认字节序为 CDAB（疑似错误）**

**位置**: `mcgs_service.py:258`

```
def _get_byte_order(self, device_id: str) -> str:
    # ... 各种尝试获取配置 ...
    return "CDAB"  # ⚠️ 默认小端序！

```

**问题**: DL8017 是标准 Modbus 设备，默认字节序应为 **ABCD**（大端）。CDAB 是 Intel x86 小端序。如果用户未显式配置字节序，所有 float32 值将解析为乱码（如 `123.45` → `1.23e-42` 或类似 NaN）。

**影响**: 这是用户报告"数据显示异常"的最常见根因。

**修复**: 改为 `return "ABCD"` 或从设备型号自动推断。

***

#### **问题5: `read_registers_batch` 是假批量**

**位置**: `modbus_protocol.py:209-233`

```
def read_registers_batch(self, addresses: List[tuple[int, int]]) -> Optional[Dict[...]]:
    results = {}
    for start_addr, count in addresses:        # ← 逐个顺序读取！
        data = self._read_registers(start_addr, count, ...)
        results[start_addr] = data
    return results

```

**问题**: 方法名暗示"批量优化"，实际是循环单次读取。N 个地址块 = N 次 RTT（每次 \~25ms），10个点 = 250ms。

**对比**: `DeviceConnection._poll_data_with_config()` 已实现了真正的连续地址合并（v3.2），但 `ModbusProtocol.read_registers_batch()` 未利用此优化。

**性能影响**: 当寄存器地址不连续时无法合并，这是协议限制；但当地址连续时，应合并为一次 `read_registers(start, total_count)` 调用。

***

#### **问题6: `_is_connected` 读写竞态**

**位置**: `tcp_driver.py:189-191` vs `232-241`

```
def send_data(self, data):         # 任意线程调用
    if not self._is_connected:     # ← 无锁读
        return False

def _handle_connection_loss(self): # 接收线程调用
    with self._lock:
        self._is_connected = False  # ← 有锁写

```

**后果**: 理论上可能读到过期值（CPython GIL 缓解了大部分情况，但在 PyPy 或未来无 GIL Python 中会暴露）。

**修复**: `is_connected()` 也加锁，或使用 `threading.Event` 替代 bool 标志。

***

#### **问题7: `DeviceConnection._current_data` 无线程保护**

**位置**: `device_connection.py:152` + `474-476`

```
# 写入：工作线程（QThreadPool → poll_data）
self._current_data = dict(result)     # 行474

# 读取：主线程（UI定时刷新）
def get_current_data(self):
    return dict(self._current_data)   # 行201-203

```

**问题**: `dict(result)` 赋值非原子操作（先清空再填充期间，其他线程读到空字典或不完整数据）。

**后果**: UI 闪烁、显示短暂空白、或 `dict changed size during iteration` RuntimeError。

**修复**: 使用 `threading.RLock` 保护，或使用 `copy.deepcopy` + 原子引用替换。

***

#### **问题8: 心跳发送阻塞主线程**

**位置**: `tcp_driver.py:243-297` (`_send_heartbeat`) + `61-62`

```
self._heartbeat_timer = QTimer()
self._heartbeat_timer.timeout.connect(self._send_heartbeat)  # 主线程执行！

def _send_heartbeat(self):
    self._socket.sendall(heartbeat_request)  # ← 阻塞式socket写！

```

**问题**: `QTimer` 回调在主线程执行，`socket.sendall()` 在网络拥塞时可阻塞数秒 → **UI 冻结**。

**修复**: 将心跳移到 `_receive_loop` 所在线程，或使用异步发送（`socket.send()` 非阻塞 + select）。

***

#### **问题9: `PollingSchedulerSignals` 引用错误**

**位置**: `polling_scheduler.py:98`

```
self._signals = PollingSchedulerDevices()  # ❌ 应为 PollingSchedulerSignals

```

**问题**: `PollingSchedulerDevices` 定义在文件末尾（行360），且与 `PollingSchedulerSignals`（行33）是**两个不同的类**。此处实例化了向后兼容别名类而非预期的信号类。

**运行时影响**: 如果外部代码访问 `scheduler.signals.poll_success`，由于两个类恰好定义了相同的 Signal 属性，不会立即报错。但违反设计意图，重构时容易引入隐蔽缺陷。

***

#### **问题10: 响应无 Transaction ID 校验**

**位置**: `modbus_protocol.py:281-283` + `293-349` (`_parse_read_response`)

**问题**: 发送请求时生成 Transaction ID，但接收响应时**完全不校验**返回的 Transaction ID：

```
# 发送时
request = self._build_tcp_header(...)  # 包含 trans_id=N

# 接收时
response = self._poll_buffer(...)
return self._parse_read_response(response, ...)  # 不检查 trans_id！

```

**场景**: 如果网络延迟导致旧响应迟到，新请求可能匹配到旧响应数据（虽然 Modbus 串行请求-响应模型降低了概率，但不保证）。

***

#### **问题11: `_parse_read_response` 寄存器边界越界风险**

**位置**: `modbus_protocol.py:340-343`

```
for i in range(count):
    if 2 + i * 2 + 1 < len(pdu):   # ← 应该是 <= ?
        reg_val = struct.unpack(">H", pdu[2 + i * 2 : 4 + i * 2])[0]

```

**分析**: 需要 `pdu[2+i*2 : 4+i*2]` 共2字节，即索引 `2+i*2` 和 `3+i*2` 都必须有效。 条件 `2 + i*2 + 1 < len(pdu)` 即 `3 + i*2 < len(pdu)` 即 `len(pdu) > 3 + i*2`，即最大有效索引 `3+i*2` ≤ `len(pdu)-1`。✅ 正确。

但切片 `pdu[2+i*2 : 4+i*2]` 在 Python 中越界不会报错（返回短于预期的 bytes），`struct.unpack` 会因数据不足抛出 `struct.error`，被外层 try-except 吞掉返回 None。**功能正确但静默丢数据**。

***

#### **问题12: `ModbusValueParser.parse_batch` 报警条件运算符优先级错误**

**位置**: `modbus_value_parser.py:188`

```
if not isinstance(raw_value, bool) and point.alarm_high is not None or point.alarm_low is not None:

```

**问题**: `and` 优先级高于 `or`，实际解析为：

```
if (not isinstance(raw_value, bool) and point.alarm_high is not None) or point.alarm_low is not None:

```

这意味着：只要 `alarm_low` 不为 None，就一定会检查报警——即使 `raw_value` 是布尔值。逻辑应为全部用 `and` 连接或加括号。

***

#### **问题13: `DeviceConnection` 双重信号发射**

**位置**: `device_connection.py:475-476`

```
self.data_received.emit(self.device_id, result)   # 新信号
self.data_updated.emit(result)                     # 旧兼容信号

```

**问题**: 两套信号同时发射，如果 UI 同时连接了两个信号，同一份数据会被处理两次。增加 CPU 开销，可能导致状态机重复触发。

***

#### **问题14: `__del__` 中执行断连操作**

**位置**: `device_connection.py:1596-1602`

```
def __del__(self):
    if self._is_connected:
        self.disconnect()  # 在GC中执行复杂的信号断开+socket关闭

```

**问题**:

- `__del__` 调用时，Qt 对象可能已部分销毁（C++层已释放），调用 `disconnect()` 会访问无效内存
- Python GC 时机不确定，可能在任意线程触发 `__del__`，而 `disconnect()` 不是线程安全的
- 可能导致 "wrapped C/C++ object has been deleted" 错误或死锁

***

## **五、重构方案**

### **Phase 1: 紧急修复（1-2天）**

```
1. 修复 问题1: 统一响应数据到单一缓冲区路径
   - 删除 _pending_response 机制
   - _poll_buffer 只从 _get_buffer() 读取

2. 修复 问题2: 心跳响应隔离
   - _receive_loop 中识别并过滤 FC08 响应
   - 或为心跳创建独立 socket/独立缓冲区

3. 修复 问题4: 默认字节序改为 ABCD

4. 修复 问题9: PollingSchedulerSignals 引用

```

### **Phase 2: 线程安全加固（2-3天）**

```
5. 修复 问题3: _transaction_id 加 threading.Lock
6. 修复 问题6: is_connected() 加锁 / 改用 threading.Event
7. 修复 问题7: _current_data 加 RLock
8. 修复 问题8: 心跳移至接收线程

```

### **Phase 3: 架构重构（3-5天）**

```
9. 统一解析器:
   - 删除 ModbusProtocol._parse_register_value()
   - 删除 DeviceConnection._decode_point_value()
   - 全部委托给 ModbusValueParser

10. 真正的批量读取:
    - read_addresses_optimized(addresses):
      - 输入: [(addr, count, dtype), ...]
      - 输出: {addr: value}
      - 内部: 按 FC 分组 → 地址排序 → 连续合并 → 最少次数读取

11. 响应匹配机制:
    - 发送时记录 (trans_id, expected_fc, timestamp)
    - 接收时校验 trans_id + fc 匹配
    - 超时未匹配的请求自动重试

12. 协议层瘦身:
    - ModbusProtocol 只保留: read/write 原语
    - 业务逻辑上移到 DeviceConnection / MCGSService

```

### **Phase 4: 性能优化（可选）**

```
13. 自适应超时: 基于历史 RTT 动态调整 timeout_ms
14. 批量写合并: FC16 连续地址自动合并
15. 压缩轮询: 值未变化时不发射 data_updated 信号
16. 连接池: 多设备同主机时复用 TCP 连接

```
