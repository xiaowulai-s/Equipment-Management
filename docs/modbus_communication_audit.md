### 问题1：MCGS轮询在主线程同步阻塞

**文件**: `ui/main_window.py` L2996\
**代码**:

```python
def _on_mcgsm_poll_timeout(self):        # QTimer回调 → 主线程执行
    result = self._mcgsm_reader.read_device(device_id)  # 同步阻塞！
```

**问题分析**:

- `_on_mcgsm_poll_timeout()` 由 `QTimer.timeout` 触发，运行在**主线程**
- `read_device()` 内部执行完整的 TCP连接 + Modbus请求/响应 + 字节序解析
- 单次耗时：正常 15\~50ms，超时可达 3000ms（`timeout_ms=3000`）
- 多设备串行：3台设备 = 3 × 50ms = 150ms 冻结
- 每 1000ms 触发一次，叠加存储+检测后可达 200ms+

**影响**:

- UI冻结导致界面卡顿、无法响应用户操作
- 窗口拖动/缩放时出现"白屏"
- 操作系统可能标记程序为"未响应"

**对比**: 通用设备通路使用 `QThreadPool` + `Signal/Slot`，完全不阻塞UI

**修改建议**:

```python
# 方案：参照 AsyncPollingWorker 模式，将 MCGS 读取放入工作线程

# 1. 创建 MCGS 专用轮询任务
class MCGSPollingTask(QRunnable):
    class Signals(QObject):
        poll_success = Signal(str, dict, dict, float)  # device_id, parsed, raw, duration
        poll_failed = Signal(str, str)                  # device_id, error

    def __init__(self, reader, device_id):
        super().__init__()
        self.setAutoDelete(True)
        self._reader = reader
        self._device_id = device_id
        self.signals = self.Signals()

    def run(self):
        result = self._reader.read_device(self._device_id)  # 在工作线程中执行
        if result.success:
            raw_dict = {}
            for k, v in result.parsed_data.items():
                try: raw_dict[k] = float(v.split()[0])
                except: raw_dict[k] = 0.0
            self.signals.poll_success.emit(self._device_id, result.parsed_data, raw_dict, result.read_duration_ms)
        else:
            self.signals.poll_failed.emit(self._device_id, result.error_message or "未知错误")

# 2. 在 MainWindow 中使用线程池
def _on_mcgsm_poll_timeout(self):
    for device_id in self._mcgsm_reader.list_devices():
        task = MCGSPollingTask(self._mcgsm_reader, device_id)
        task.signals.poll_success.connect(self._on_mcgsm_poll_success)
        task.signals.poll_failed.connect(self._on_mcgsm_poll_failed)
        self._thread_pool.start(task)  # 提交到线程池，不阻塞UI

@Slot(str, dict, dict, float)
def _on_mcgsm_poll_success(self, device_id, parsed_data, raw_dict, duration_ms):
    # 在主线程安全更新UI
    if self._mcgsm_storage:
        self._mcgsm_storage.save_read_result(device_id, parsed_data, raw_dict)
    if device_id in self._monitor_panels:
        self._monitor_panels[device_id].update_data(parsed_data)
```

***

### 问题2：ModbusProtocol.\_poll\_buffer() 竞态条件

**文件**: `core/protocols/modbus_protocol.py` L810-864\
**代码**:

```python
def _poll_buffer(self, timeout_ms=200, interval_ms=5):
    with self._response_lock:
        self._pending_response = None          # ① 重置

    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        with self._response_lock:
            if self._pending_response is not None:   # ② 检查
                result = self._pending_response
                self._pending_response = None
                return result

        # ⚠️ 问题：直接访问 driver 的内部缓冲区
        if self._driver and hasattr(self._driver, '_get_buffer'):
            response = self._driver._get_buffer()    # ③ 绕过锁
            if response:
                return response

        time.sleep(interval_ms / 1000.0)
```

**问题分析**:

1. **响应匹配缺失**：`_pending_response` 只有一个槽位。如果心跳FC08的响应和业务FC03的响应同时到达，后到的会覆盖先到的，导致：
   - 业务请求收到心跳响应 → 解析失败 → 数据丢失
   - 心跳请求收到业务响应 → 误判心跳成功
2. **缓冲区直接访问**：`_driver._get_buffer()` 绕过了 `_response_lock`，与 `_on_driver_response()` 存在竞态
3. **无事务ID匹配**：TCP模式下每个请求有 `transaction_id`，但 `_poll_buffer()` 不检查响应的 `transaction_id` 是否匹配当前请求

**影响**:

- 多设备并发轮询时，响应可能错位
- 心跳与业务请求冲突时数据丢失
- 实际场景：3台设备同时轮询 + FC08心跳 = 高概率响应错位

**修改建议**:

```python
# 方案：基于 transaction_id 的请求-响应匹配

class ModbusProtocol(BaseProtocol):
    def __init__(self, ...):
        ...
        self._pending_requests: Dict[int, threading.Event] = {}
        self._pending_results: Dict[int, bytes] = {}
        self._request_lock = threading.Lock()

    def _read_registers(self, address, count, function_code):
        # 构建请求并记录 transaction_id
        trans_id = self._next_transaction_id()
        request = self._build_tcp_header_with_id(trans_id, ...) + pdu

        # 注册等待事件
        event = threading.Event()
        with self._request_lock:
            self._pending_requests[trans_id] = event
            self._pending_results[trans_id] = None

        # 发送请求
        self._driver.send_data(request)

        # 等待匹配的响应（带超时）
        if event.wait(timeout=self._timeout):
            with self._request_lock:
                response = self._pending_results.pop(trans_id, None)
                self._pending_requests.pop(trans_id, None)
            return self._parse_read_response(response, function_code, count)

        # 超时清理
        with self._request_lock:
            self._pending_requests.pop(trans_id, None)
            self._pending_results.pop(trans_id, None)
        return None

    def _on_driver_response(self, data: bytes):
        # 从响应中提取 transaction_id
        if len(data) >= 7 and self._mode == "TCP":
            resp_trans_id = struct.unpack(">H", data[0:2])[0]
            with self._request_lock:
                if resp_trans_id in self._pending_requests:
                    self._pending_results[resp_trans_id] = data
                    self._pending_requests[resp_trans_id].set()  # 唤醒等待线程
```

***

**问题3：数据格式不统一（中等）**

通路A的数据格式：

```
{"温度": {"raw": 25.6, "value": "25.
60 ℃", "type": "holding_float32", 
"writable": False, "config": 
RegisterPointConfig}}
```

通路B的数据格式：

```
{"Hum_in": "25.6 %RH"}   # 仅字符串！
无raw/type/writable/config
```

影响 ：

- DynamicMonitorPanel.update\_data() 期望通路A的格式（需要 raw / value / config 字段）
- MCGS通路传入的 parsed\_data 是纯字符串字典
- 导致面板无法正确执行报警检查（ config.check\_alarm(float(raw\_value)) 会失败）

**问题4：MCGS轮询中重复解析字符串（中等）**

位置 : main\_window\.py:3001-3006

```
# 每次轮询都要从格式化字符串中反向提取数值
for k, v in result.parsed_data.items
():
    try:
        raw_dict[k] = float(v.split
        ()[0])    # "25.6 ℃" → 25.6
    except:
        raw_dict[k] = 0.0
```

问题 ：

- MCGSModbusReader 先把 float → 格式化字符串 "25.6 ℃"
- MainWindow 再把字符串 → split → float
- 精度损失 + 性能浪费 + 异常处理脆弱

**问题6：DeviceConnection中存在死代码（轻微）**

位置 : device\_connection.py:1424-1441

```
if False:    # ← 永远不会执行的代码块
    if isinstance(raw_value, bool):
        formatted_value = rp.
        format_value(raw_value)
    else:
        formatted_value = rp.
        format_value(raw_value)
    result[rp.name] = {"raw": 
    raw_value, "value": 
    formatted_value, ...}
else:
    logger.warning("数据索引越界 ...
    ")   # ← 这才是实际执行的
```

if False: 块是旧版代码残留，包含重复的格式化逻辑。

**问题7：MCGS快速连接中递归调用风险（轻微）**

位置 : main\_window\.py:2601

```
self._on_mcgsm_quick_connect()   # 
递归调用自身
return
```

如果用户在配置对话框中保存后，新配置仍然连接失败，会再次弹出配置对话框，形成无限递归。虽然有 return 阻止继续执行，但没有递归深度限制。

### 问题8：MCGSModbusReader 连接泄漏

**文件**: `core/utils/mcgs_modbus_reader.py` L341-388\
**代码**:

```python
{"温度": {"raw": 25.6, "value": "25.
60 ℃", "type": "holding_float32", 
"writable": False, "config": 
RegisterPointConfig}}
```

**问题分析**:

1. **无连接健康检查**：`if device_id in self._clients` 只检查字典键是否存在，不验证底层socket是否仍然存活
2. **无断线检测**：网络中断后 `_clients` 中仍保留旧条目，`connect_device()` 返回 `True` 但实际已断开
3. **无重连机制**：连接断开后需要手动清除 `_clients` 才能重新连接
4. **pymodbus客户端无关闭**：`_create_pymodbus_client()` 创建的 `ModbusTcpClient` 在连接失败时未关闭

**影响**:

- 网络闪断后，MCGS轮询持续返回"已连接"但读取全部失败
- 每次重连创建新的 TCP socket，旧的未关闭 → 资源泄漏
- 长时间运行后可能耗尽文件描述符

**修改建议**:

```python
def connect_device(self, device_id: str) -> bool:
    if device_id in self._clients:
        # ✅ 增加连接健康检查
        client_info = self._clients[device_id]
        if client_info["type"] == "pymodbus":
            if client_info["client"].connected:  # pymodbus 连接状态检查
                return True
            else:
                # 连接已断开，清理旧连接
                try: client_info["client"].close()
                except: pass
                del self._clients[device_id]
        elif client_info["type"] == "builtin":
            driver = client_info["connection"].get("driver")
            if driver and driver.is_connected():
                return True
            else:
                try: driver.disconnect()
                except: pass
                del self._clients[device_id]

    # 创建新连接...
```

***

### 问题9：MCGS快速连接递归调用无深度限制

**文件**: `ui/main_window.py` L2598-2602\
**代码**:

```python
if config_saved:
    self._mcgsm_reader = None
    self._on_mcgsm_quick_connect()   # ← 递归调用自身
    return
```

**问题分析**:

- 如果用户在配置对话框中修改了参数但仍然无法连接，会再次弹出"是否打开配置编辑器"的提示
- 用户反复点击 \[Yes] → 修改 → 保存 → 连接失败 → 再弹出提示 → 形成无限递归
- 每次递归都会创建新的 `MCGSConfigDialog` 实例，内存持续增长
- Python 默认递归深度限制 1000，但在此之前 UI 已经完全不可用

**修改建议**:

```python
# 方案：增加重试次数限制
def _on_mcgsm_quick_connect(self, _retry_depth=0):  # 新增参数
    ...
    if config_saved:
        if _retry_depth < 2:  # 最多重试2次
            self._mcgsm_reader = None
            self._on_mcgsm_quick_connect(_retry_depth=_retry_depth + 1)
            return
        else:
            QMessageBox.warning(self, "连接仍失败",
                "已尝试2次重新连接，请检查网络和设备状态后重试。")
            return
```

***

### 问题10：字节序解析重复实现

**文件A**: `core/protocols/modbus_protocol.py` L446-554 (`_parse_register_value`)\
**文件B**: `core/utils/mcgs_modbus_reader.py` L609-688 (`_parse_float` / `_parse_int32`)\
**文件C**: `core/device/device_connection.py` L1459-1497 (`_decode_point_value`)

**问题分析**:
三处代码独立实现了相同的字节序解析逻辑，且实现方式不同：

| 位置               | ABCD                        | CDAB          | BADC                           | DCBA      | 输出格式              |
| ---------------- | --------------------------- | ------------- | ------------------------------ | --------- | ----------------- |
| ModbusProtocol   | `bo.swap_bytes_for_32bit()` | 同左            | 同左                             | 同左        | `(raw, value)` 元组 |
| MCGSModbusReader | `pass`                      | `b[2:]+b[:2]` | `bytes([b[1],b[0],b[3],b[2]])` | `b[::-1]` | `float` 值         |
| DeviceConnection | `bo.swap_bytes_for_32bit()` | 同左            | 同左                             | 同左        | `float/int` 值     |

**影响**:

- 三套代码行为可能不一致（如边界条件处理不同）
- 修改字节序逻辑需要改三处，容易遗漏
- MCGSModbusReader 的实现最简单，缺少对异常字节序值的保护

**修改建议**:

```python
# 方案：统一使用 ByteOrderConfig + ModbusProtocol.decode_float32()

# 在 MCGSModbusReader 中复用已有协议层
def _parse_float(self, regs, byte_order):
    from core.protocols.byte_order_config import ByteOrderConfig
    from core.protocols.modbus_protocol import ModbusProtocol

    bo = ByteOrderConfig.from_string(byte_order)
    raw_bytes = struct.pack(">HH", regs[0], regs[1])
    return ModbusProtocol.decode_float32(None, raw_bytes, byte_order=bo)
    # 注意：需要将 decode_float32 改为 @staticmethod
```

***

### 问题11：MCGS与通用系统数据格式不统一

**文件**: `core/utils/mcgs_modbus_reader.py` L720-788\
**代码**:

```python
# MCGS 输出格式：纯字符串字典
parsed[point.name] = formatted  # "25.6 ℃"

# 通用系统输出格式：结构化字典
result[rp.name] = {
    "raw": decoded_value,        # float
    "value": rp.format_value(),  # "25.60 ℃"
    "type": rp.data_type.code,   # "holding_float32"
    "writable": rp.writable,     # False
    "config": rp,                # RegisterPointConfig
}
```

**问题分析**:

- `DynamicMonitorPanel.update_data()` 期望通用系统的格式（需要 `raw`/`value`/`config` 字段）
- MCGS传入的 `parsed_data` 是 `{"Hum_in": "25.6 %RH"}` 纯字符串
- 导致面板中 `config.check_alarm(float(raw_value))` 无法执行（缺少 `config` 和 `raw` 字段）
- `MainWindow` 中需要反向解析字符串提取数值：`float(v.split()[0])`

**修改建议**:

```python
# 方案：MCGS 输出统一为结构化格式
def _parse_all_points(self, registers, points, start_addr, byte_order, device_id):
    parsed = {}
    for point in points:
        ...
        if raw_value is not None:
            scaled_value = raw_value * point.scale
            formatted = f"{scaled_value:.{point.decimal_places}f}"
            if point.unit:
                formatted += f" {point.unit}"

            # ✅ 统一输出格式
            parsed[point.name] = {
                "raw": raw_value,           # 原始浮点值
                "value": formatted,          # 格式化字符串
                "type": point.type,          # 数据类型
                "writable": False,           # MCGS默认只读
                "config": point,             # 配置对象
            }
    return parsed
```

***

### 问题12：心跳FC08与业务请求的缓冲区冲突

**文件**: `core/communication/tcp_driver.py` L243-298\
**代码**:

```python
def _send_heartbeat(self):
    ...
    self._socket.sendall(heartbeat_request)   # ← 直接发送，不经过 Protocol 层
    self._heartbeat_sent_count += 1
```

**问题分析**:

- 心跳请求直接通过 `socket.sendall()` 发送，绕过了 `ModbusProtocol` 层
- 心跳响应到达后进入 `_receive_loop()` → `_append_to_buffer()`
- `ModbusProtocol._poll_buffer()` 从 buffer 中取数据时，可能取到心跳响应而非业务响应
- 没有基于 `transaction_id` 的过滤机制

**影响**:

- 心跳响应被误认为业务响应 → 解析失败 → 数据丢失
- 业务响应被心跳逻辑忽略 → 超时重试 → 通信效率降低
- 高频心跳（10s间隔）+ 多设备轮询 = 冲突概率显著

**修改建议**:

```python
# 方案1（推荐）：心跳也通过 Protocol 层发送，利用 transaction_id 匹配
# 方案2：在 _receive_loop 中根据 transaction_id 分流
def _receive_loop(self):
    while self._is_running and self._socket:
        data = self._socket.recv(4096)
        if data:
            self._append_to_buffer(data)
            # 检查是否为心跳响应
            if len(data) >= 9:
                trans_id = struct.unpack(">H", data[0:2])[0]
                fc = data[7] if len(data) > 7 else 0
                if fc == 0x08:  # FC08 诊断响应
                    self._heartbeat_success_count += 1
                    # 不放入业务缓冲区
                    continue
            self.data_received.emit(data)
```

***

### 问题13：\_poll\_buffer() 直接访问 driver 内部缓冲区

**文件**: `core/protocols/modbus_protocol.py` L849-852\
**代码**:

```python
if self._driver and hasattr(self._driver, '_get_buffer'):
    response = self._driver._get_buffer()    # ← 访问私有方法
    if response:
        return response
```

**问题分析**:

1. **违反封装原则**：直接调用 `_get_buffer()`（以下划线开头的私有方法）
2. **竞态条件**：`_get_buffer()` 返回 buffer 的完整拷贝但不消费，下次调用仍返回相同数据
3. **数据重复**：如果 `_on_driver_response()` 已经将数据放入 `_pending_response`，`_get_buffer()` 仍会返回同一份数据，导致重复处理
4. **无MBAP头解析**：直接返回 buffer 全部内容，可能包含多个Modbus帧

**修改建议**:

```python
# 方案：移除直接访问 driver 缓冲区的代码，完全依赖信号驱动
def _poll_buffer(self, timeout_ms=200, interval_ms=5):
    with self._response_lock:
        self._pending_response = None

    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        with self._response_lock:
            if self._pending_response is not None:
                result = self._pending_response
                self._pending_response = None
                return result
        time.sleep(interval_ms / 1000.0)

    return None  # 超时
```

***

### 问题14：DeviceConnection.\_format\_batch\_data() 中的死代码

**文件**: `core/device/device_connection.py` L1424-1441\
**代码**:

```python
if False:    # ← 永远不会执行
    if isinstance(raw_value, bool):
        formatted_value = rp.format_value(raw_value)
    else:
        formatted_value = rp.format_value(raw_value)
    result[rp.name] = {"raw": raw_value, "value": formatted_value, ...}
else:
    logger.warning("数据索引越界 ...")   # ← 实际执行的分支
```

**问题分析**:

- `if False:` 块是旧版代码残留，永远不会执行
- `else:` 分支的日志消息"数据索引越界"与实际逻辑不符（此处不是越界，而是 `decoded_value is None`）
- 降低了代码可读性，增加维护成本

**修改建议**:

```python
# 删除 if False: 块，修正 else 分支逻辑
decoded_value = self._decode_point_value(rp, raw_data, index_offset)
if decoded_value is not None:
    result[rp.name] = {
        "raw": decoded_value,
        "value": rp.format_value(decoded_value),
        "type": rp.data_type.code,
        "writable": rp.writable,
        "config": rp,
    }
else:
    logger.warning(
        "数据解码失败 [参数=%s, 偏移=%d]",
        rp.name, index_offset
    )
```

***

### 问题15：统一两条数据通路

**现状**:

- 通路A（通用设备）：`DeviceManager` → `DeviceConnection` → `ModbusProtocol` → `TcpDriver`
- 通路B（MCGS专用）：`MCGSModbusReader` → `pymodbus` / 内置协议栈

两条通路完全独立，9个功能点重复实现（TCP连接/FC03读取/字节序解析/地址转换/批量优化/数据格式化/报警检查/数据存储/轮询调度）

**建议**:

- MCGS设备也通过 `DeviceManager` 管理，复用 `DeviceConnection` 的配置驱动轮询
- `MCGSModbusReader` 降级为配置加载器，只负责解析 `devices.json` 并转换为 `RegisterPointConfig`
- 消除 `pymodbus` 依赖，统一使用内置协议栈

***

### 问题16：MCGS轮询异步化

**现状**: MCGS轮询使用 `QTimer` + 同步调用，每次轮询阻塞主线程 15-3000ms

**建议**:

- 参照 `AsyncPollingWorker` + `DevicePollingTask` 模式
- 将 `MCGSModbusReader.read_device()` 放入 `QThreadPool` 工作线程
- 通过 `Signal/Slot` 将结果传回主线程更新UI
- 存储和检测也在工作线程中执行

***

### 问题17：连接池化

**现状**: 每个设备独立创建 `TcpDriver` + `ModbusProtocol` 实例

**建议**:

- 对于同IP同端口的设备（如MCGS触摸屏下挂多个模块），共享一个TCP连接
- 实现连接池管理器，支持连接复用和自动回收
- 减少TCP连接数，降低设备端负载

***

### 问题18：增加通信质量监控

**现状**: 仅有基本的成功/失败计数

**建议**:

- 增加通信质量指标：响应时间P50/P95/P99、丢包率、重试率
- 实现滑动窗口统计（最近60秒/5分钟/15分钟）
- 通信质量下降时自动降级（增加轮询间隔、减少读取点位）
- 在UI中展示通信质量仪表盘

#### 问题19：MCGS数据被解析两次

**链路追踪**:

```
MCGSModbusReader._parse_all_points()
  → _parse_float(regs, "CDAB")           # 第1次解析: float → "25.6 ℃"
  → parsed_data["Hum_in"] = "25.6 ℃"    # 输出: 格式化字符串

MainWindow._on_mcgsm_poll_timeout()
  → raw_dict[k] = float(v.split()[0])    # 第2次解析: "25.6 ℃" → 25.6
  → storage.save_read_result(parsed, raw) # 两个版本都存储
  → detector.check_batch(raw_dict)        # 使用第2次解析的值
  → panel.update_data(parsed_data)        # 使用第1次解析的字符串
```

**问题**: 同一数据被解析了2次——第1次 float→string，第2次 string→float。中间的字符串转换导致：

- 精度损失（`25.6 ℃` 无法还原为 `25.60000038147...`）
- 性能浪费（每秒N个点 × split + float转换）
- 异常脆弱（`float("N/A".split()[0])` → ValueError）

#### 问题20：字节序解析逻辑重复3处

| 位置                          | 方法                        | 输入                                | 输出                | 依赖ByteOrderConfig |
| --------------------------- | ------------------------- | --------------------------------- | ----------------- | ----------------- |
| `modbus_protocol.py:446`    | `_parse_register_value()` | `List[int]` + type\_str           | `(raw, value)` 元组 | ✅                 |
| `mcgs_modbus_reader.py:609` | `_parse_float()`          | `List[int]` + byte\_order\_str    | `float`           | ❌ 自实现             |
| `device_connection.py:1459` | `_decode_point_value()`   | `List[int]` + RegisterPointConfig | `float/int/bool`  | ✅                 |

三处代码实现了相同的字节序交换逻辑，但接口和输出格式各不相同。

#### 问题21：类型映射重复2处

**位置A**: `mcgs_modbus_reader.py:68-74` (DevicePointConfig)

```python
type_map = {
    "float": 2, "float32": 2, "int32": 2, "uint32": 2,
    "int16": 1, "uint16": 1, "coil": 1, "di": 1,
}
```

**位置B**: `main_window.py:2695-2699` (MCGS面板创建)

```python
type_map = {
    'float': RegisterDataType.HOLDING_FLOAT32,
    'int16': RegisterDataType.HOLDING_INT16,
    'coil': RegisterDataType.COIL,
    'di': RegisterDataType.DISCRETE_INPUT,
}
```

**位置C**: `RegisterDataType.get_register_count()` (data\_type\_enum.py:59-64)

```python
if self in (RegisterDataType.HOLDING_INT32, RegisterDataType.HOLDING_FLOAT32,
            RegisterDataType.INPUT_FLOAT32):
    return 2
return 1
```

三处独立定义了"数据类型→寄存器数量"的映射关系，且不一致。

---

## 十二、工程潜在问题全面扫描

> **扫描范围**: 全工程 Python 源文件
> **扫描重点**: 线程问题 / 内存泄漏 / 异常未处理 / 通信异常 / 数据错误

---

### 12.1 线程问题

#### 🔴 高-V01：TcpDriver.disconnect() 中 join() 持有锁等待线程退出 — 潜在死锁

**文件**: `core/communication/tcp_driver.py:163-186`

```python
def disconnect(self):
    with self._lock:                          # ① 获取 RLock
        self._is_running = False
        self._heartbeat_timer.stop()
        if self._socket:
            self._socket.close()
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2.0)  # ② 等待线程退出
```

**触发条件**: `_receive_loop()` 中 `_handle_connection_loss()` 也需要获取 `_lock`：

```python
def _handle_connection_loss(self):
    with self._lock:                          # ③ 尝试获取同一把 RLock
        self._is_connected = False
```

**死锁路径**:
1. 主线程调用 `disconnect()` → 获取 `_lock` → `join()` 等待接收线程
2. 接收线程检测到连接断开 → 调用 `_handle_connection_loss()` → 尝试获取 `_lock`
3. 虽然 RLock 可重入，但 `join()` 的线程和 `_lock` 的持有者不是同一线程 → **死锁**

**修复方案**:
```python
def disconnect(self):
    # 先停止接收线程（不持锁）
    self._is_running = False
    if self._receive_thread and self._receive_thread.is_alive():
        self._receive_thread.join(timeout=2.0)

    # 线程退出后再持锁清理
    with self._lock:
        self._heartbeat_timer.stop()
        if self._socket:
            try: self._socket.close()
            except OSError: pass
            self._socket = None
        self._is_connected = False
        self._clear_buffer()
    self._safe_emit_signal(self.disconnected)
```

---

#### 🔴 高-V02：MCGSModbusReader._transaction_id 非原子自增

**文件**: `core/protocols/modbus_protocol.py:895`

```python
self._transaction_id = (self._transaction_id + 1) % 65536
```

**触发条件**: 多线程并发调用 `read_registers()` 时，`_transaction_id` 的读取-修改-写入不是原子操作，可能导致两个请求使用相同的 transaction_id。

**修复方案**:
```python
import threading
self._tid_lock = threading.Lock()

def _next_transaction_id(self) -> int:
    with self._tid_lock:
        self._transaction_id = (self._transaction_id + 1) % 65536
        return self._transaction_id
```

---

#### 🟡 中-V03：FaultRecoveryService.recovery_history 无限增长

**文件**: `core/device/fault_recovery_service.py:408`

```python
stats.recovery_history.append(attempt)  # 无上限！
```

**触发条件**: 设备频繁故障时，`recovery_history` 列表持续增长。每台设备每次故障恢复追加1条记录，24小时故障循环可达 86400 条。

**对比**: `OperationUndoManager` 有 `max_history=100` 限制，`audit_log` 有 1000/2000 条限制。但 `recovery_history` 没有任何限制。

**修复方案**:
```python
stats.recovery_history.append(attempt)
MAX_RECOVERY_HISTORY = 500
if len(stats.recovery_history) > MAX_RECOVERY_HISTORY:
    stats.recovery_history = stats.recovery_history[-MAX_RECOVERY_HISTORY:]
```

---

### 12.2 内存泄漏风险

#### 🔴 高-V04：pymodbus 连接失败时客户端未关闭

**文件**: `core/utils/mcgs_modbus_reader.py:390-412`

```python
def _create_pymodbus_client(self, device):
    client = ModbusTcpClient(host=device.ip, port=device.port, timeout=...)
    if client.connect():
        return client          # ✅ 成功：返回客户端
    else:
        return None            # ❌ 失败：客户端未关闭！
```

**触发条件**: 每次连接失败都创建一个 `ModbusTcpClient` 实例但不关闭。如果用户反复点击"快速连接"或轮询自动重连，每次失败都泄漏一个 socket。

**修复方案**:
```python
def _create_pymodbus_client(self, device):
    client = ModbusTcpClient(host=device.ip, port=device.port, timeout=...)
    if client.connect():
        return client
    else:
        try: client.close()    # ← 关闭失败的客户端
        except: pass
        return None
```

---

#### 🔴 高-V05：MCGSModbusReader.__del__() 中调用 disconnect_all() 可能失败

**文件**: `core/utils/mcgs_modbus_reader.py:943-945`

```python
def __del__(self):
    self.disconnect_all()
```

**触发条件**: Python 解释器关闭时，模块级变量可能已被垃圾回收。`disconnect_all()` 内部调用 `client.close()` 和 `driver.disconnect()`，但这些对象可能已经不存在。

**修复方案**:
```python
def __del__(self):
    try:
        self.disconnect_all()
    except Exception:
        pass  # 析构时静默忽略所有异常
```

---

#### 🟡 中-V06：AnomalyDetector._value_cache 无过期清理

**文件**: `core/utils/anomaly_detector.py:455-460`

```python
cache.append((timestamp, value))
max_size = 2000
if len(cache) > max_size:
    self._value_cache[cache_key] = cache[-max_size:]
```

**触发条件**: 每个设备每个参数最多缓存 2000 条记录。如果有 10 台设备 × 7 个参数 = 70 个缓存列表 × 2000 条 = 140,000 条记录。每条记录包含 (timestamp, value) 约 40 字节，总计约 5.6MB。虽然不大，但缺少基于时间的过期清理（如删除30天前的数据）。

**修复方案**: 增加时间维度清理：
```python
# 清理超过7天的缓存数据
cutoff = time.time() - 7 * 86400
cache = [(t, v) for t, v in cache if t > cutoff]
```

---

#### 🟡 中-V07：MainWindow._monitor_panels 字典只增不减

**文件**: `ui/main_window.py:2725`

```python
self._monitor_panels[device_id] = panel
```

**触发条件**: 每次快速连接都创建新的 `DynamicMonitorPanel` 并添加到字典和 TabWidget。但断开连接时没有从字典中移除面板。如果用户反复连接/断开同一设备，面板会累积。

**修复方案**: 在断开连接时清理面板：
```python
def _on_mcgsm_disconnect(self, device_id):
    if device_id in self._monitor_panels:
        panel = self._monitor_panels.pop(device_id)
        index = self._monitor_tabs.indexOf(panel)
        if index >= 0:
            self._monitor_tabs.removeTab(index)
        panel.deleteLater()
```

---

### 12.3 异常未处理

#### 🔴 高-V08：main_window.py:3005 bare except 吞掉所有异常

**文件**: `ui/main_window.py:3001-3006`

```python
for k, v in result.parsed_data.items():
    try:
        raw_dict[k] = float(v.split()[0])
    except:                    # ← 吞掉所有异常，包括 KeyboardInterrupt
        raw_dict[k] = 0.0     # ← 默认值0.0可能掩盖传感器故障
```

**触发条件**: 当 `parsed_data` 包含 `"N/A"` 或 `"PARSE_ERR"` 时，`float("N/A")` 抛出 ValueError，被静默捕获并替换为 0.0。这会导致：
- 异常检测器收到 0.0 而非 None，可能触发误报（"值过低"）
- 历史数据库存储 0.0，污染统计数据
- 用户无法从数据中发现解析失败

**修复方案**:
```python
for k, v in result.parsed_data.items():
    try:
        raw_dict[k] = float(v.split()[0])
    except (ValueError, AttributeError, IndexError):
        raw_dict[k] = None    # 用 None 表示解析失败，而非 0.0
```

---

#### 🟡 中-V09：DeviceConnection.__del__() 中调用 disconnect() 可能触发异常链

**文件**: `core/device/device_connection.py:1596-1602`

```python
def __del__(self):
    try:
        if self._is_connected:
            self.disconnect()
    except Exception:
        pass
```

**触发条件**: `disconnect()` 内部调用 `self._driver.disconnect()` 和 `self._protocol.close()`。如果 `_driver` 或 `_protocol` 已被 GC 回收（Python 不保证析构顺序），访问它们会抛出 AttributeError，被 `except Exception` 捕获。虽然不会崩溃，但可能导致资源未正确释放。

**修复方案**:
```python
def __del__(self):
    try:
        if hasattr(self, '_is_connected') and self._is_connected:
            if hasattr(self, '_driver') and self._driver:
                self._driver.disconnect()
    except Exception:
        pass
```

---

#### 🟡 中-V10：HistoryStorage 查询无结果时返回空列表而非 None

**文件**: `core/utils/history_storage.py`

**触发条件**: `query_range()` 返回空列表 `[]`，调用方需要区分"无数据"和"查询失败"。当前代码 `if data:` 可以处理空列表，但如果查询本身抛出异常（如数据库锁定），异常会向上传播到 UI 层。

**修复方案**: 在 `query_range()` 中增加异常保护，返回 `None` 表示查询失败：
```python
def query_range(self, ...):
    try:
        cursor.execute(...)
        return cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.error("查询失败: %s", e)
        return None  # 区分"无数据"和"查询失败"
```

---

### 12.4 通信异常

#### 🔴 高-V11：MCGSModbusReader 无断线检测和自动重连

**文件**: `core/utils/mcgs_modbus_reader.py:341-388`

```python
def connect_device(self, device_id: str) -> bool:
    if device_id in self._clients:
        return True  # ← 仅检查字典键，不检查实际连接状态
```

**触发条件**:
1. 设备正常连接后，网线被拔出
2. `_clients` 中仍保留旧条目
3. 后续 `read_device()` 调用 `connect_device()` 返回 True
4. pymodbus 读取失败，但不会自动清除旧连接
5. 每次轮询都失败，直到用户手动重启程序

**修复方案**: 参见审计文档严重-03，增加连接健康检查。

---

#### 🔴 高-V12：TcpDriver._receive_loop 退出后无重连机制

**文件**: `core/communication/tcp_driver.py:207-228`

```python
def _receive_loop(self):
    while self._is_running and self._socket:
        try:
            data = self._socket.recv(4096)
            if data:
                self._append_to_buffer(data)
            else:
                logger.info("连接被对端关闭")
                break                    # ← 退出循环，无重连
```

**触发条件**: 设备主动关闭连接（重启/关机）→ `recv()` 返回空数据 → 接收线程退出 → `_is_connected` 设为 False → 但上层 `DeviceConnection` 不知道连接已断开（除非下次轮询失败）。

**修复方案**: 在 `_handle_connection_loss()` 中发射信号，由 `FaultRecoveryService` 触发重连：
```python
def _handle_connection_loss(self):
    with self._lock:
        self._is_connected = False
        ...
    self._safe_emit_signal(self.error_occurred, "连接丢失")
    # FaultRecoveryService 监听此信号并触发重连
```

---

#### 🟡 中-V13：pymodbus 读取响应未检查异常码

**文件**: `core/utils/mcgs_modbus_reader.py:530-545`

```python
def _read_with_pymodbus(self, client, start, count, unit_id):
    response = client.read_holding_registers(start, count, slave=unit_id)
    if response.isError():
        return None
    return list(response.registers)
```

**触发条件**: pymodbus 的 `isError()` 只检查 Modbus 异常响应，不检查 TCP 层错误。如果 TCP 连接在请求/响应之间断开，`response` 可能是 `ModbusIOException`，调用 `response.registers` 会抛出 AttributeError。

**修复方案**:
```python
def _read_with_pymodbus(self, client, start, count, unit_id):
    try:
        response = client.read_holding_registers(start, count, slave=unit_id)
        if response.isError():
            logger.warning("Modbus异常响应: %s", response)
            return None
        if not hasattr(response, 'registers'):
            logger.warning("响应缺少registers属性")
            return None
        return list(response.registers)
    except Exception as e:
        logger.error("pymodbus读取异常: %s", e)
        return None
```

---

### 12.5 数据错误风险

#### 🔴 高-V14：MCGS解析中寄存器偏移计算可能越界

**文件**: `core/utils/mcgs_modbus_reader.py:720-740`

```python
for point in points:
    offset = (point.addr - start_addr) * 2  # 字节偏移
    # ...
    point_regs = registers[offset : offset + reg_count]
```

**触发条件**: 如果 `point.addr` 小于 `start_addr`（配置错误），`offset` 为负数，Python 切片不会报错但返回空列表，导致解析结果为 None。如果 `offset + reg_count > len(registers)`，切片返回部分数据，可能导致解析出错误值。

**修复方案**:
```python
for point in points:
    offset = point.addr - start_addr  # 寄存器偏移（非字节偏移）
    if offset < 0 or offset + reg_count > len(registers):
        logger.warning(
            "数据点 [%s] 偏移越界: offset=%d, need=%d, available=%d",
            point.name, offset, reg_count, len(registers)
        )
        parsed[point.name] = "N/A"
        continue
    point_regs = registers[offset : offset + reg_count]
```

---

#### 🔴 高-V15：float 解析 NaN/Inf 未过滤

**文件**: `core/utils/mcgs_modbus_reader.py:609-660`

```python
value = struct.unpack(">f", b)[0]  # 可能返回 NaN 或 Inf
```

**触发条件**: 当寄存器值为 `0x7FC00000` (NaN) 或 `0x7F800000` (+Inf) 时，`struct.unpack` 正常返回但值为非数值。后续 `round(value, dp)` 和 `f"{value:.1f}"` 会产生 `"nan"` 或 `"inf"` 字符串，而非有意义的工程值。

**修复方案**:
```python
import math

value = struct.unpack(">f", b)[0]
if math.isnan(value) or math.isinf(value):
    logger.warning("数据点 [%s] 解析结果异常: %s", point.name, value)
    return None  # 或返回 0.0 并标记异常
```

---

#### 🟡 中-V16：DeviceConnection._format_batch_data 中 if False 死代码导致数据丢失

**文件**: `core/device/device_connection.py:1424-1441`

```python
if False:    # ← 永远不执行
    result[rp.name] = {"raw": raw_value, "value": formatted_value, ...}
else:
    logger.warning("数据索引越界 ...")  # ← 实际执行：数据被丢弃！
```

**触发条件**: 当 `_decode_point_value()` 返回 None 时（解析失败），数据点不会出现在结果字典中。UI 层无法区分"该点未配置"和"该点解析失败"。

**修复方案**: 删除 `if False:` 块，将解析失败的点也加入结果（标记为错误）：
```python
decoded_value = self._decode_point_value(rp, raw_data, index_offset)
if decoded_value is not None:
    result[rp.name] = {"raw": decoded_value, "value": rp.format_value(decoded_value), ...}
else:
    result[rp.name] = {"raw": None, "value": "N/A", "type": rp.data_type.code, "error": "decode_failed"}
```

---

#### 🟡 中-V17：MCGS calc_read_range() 地址间隙过大时读取无效数据

**文件**: `core/utils/mcgs_modbus_reader.py:276-337`

```python
@staticmethod
def calc_read_range(points):
    min_addr = min(p.addr for p in points)
    max_addr = max(p.addr + p.register_count - 1 for p in points)
    return min_addr, max_addr - min_addr + 1
```

**触发条件**: 如果点位地址为 [30002, 30004, 40001]，读取范围 = 40001-30002+1 = 10000 个寄存器，其中 9997 个是无效数据。Modbus TCP 单次最多读取 125 个寄存器（某些设备限制更小），超出限制会返回异常。

**修复方案**: 将非连续地址分为多个读取块：
```python
@staticmethod
def calc_read_ranges(points, max_gap=10, max_regs=125):
    """将点位按地址连续性分为多个读取块"""
    sorted_points = sorted(points, key=lambda p: p.addr)
    ranges = []
    current_start = sorted_points[0].addr
    current_end = sorted_points[0].addr + sorted_points[0].register_count - 1

    for point in sorted_points[1:]:
        point_end = point.addr + point.register_count - 1
        if point.addr - current_end <= max_gap and (point_end - current_start + 1) <= max_regs:
            current_end = max(current_end, point_end)
        else:
            ranges.append((current_start, current_end - current_start + 1))
            current_start = point.addr
            current_end = point_end

    ranges.append((current_start, current_end - current_start + 1))
    return ranges
```

---

### 12.6 问题总览

| # | 等级 | 类别 | 问题 | 触发条件 | 修复方案 |
|---|------|------|------|---------|---------|
| V01 | 🔴高 | 线程 | disconnect()中join()持锁→死锁 | 断开连接时接收线程正在处理连接丢失 | 先join再持锁 |
| V02 | 🔴高 | 线程 | transaction_id非原子自增 | 多线程并发读取 | 加Lock保护 |
| V03 | 🟡中 | 线程 | recovery_history无限增长 | 设备频繁故障 | 增加上限500条 |
| V04 | 🔴高 | 内存 | pymodbus连接失败未关闭 | 连接失败后重试 | 失败时close() |
| V05 | 🔴高 | 内存 | __del__中disconnect_all可能失败 | Python解释器关闭 | try/except保护 |
| V06 | 🟡中 | 内存 | _value_cache无过期清理 | 长时间运行 | 增加时间维度清理 |
| V07 | 🟡中 | 内存 | _monitor_panels只增不减 | 反复连接/断开 | 断开时清理面板 |
| V08 | 🔴高 | 异常 | bare except吞掉异常+默认0.0 | 解析失败时 | 用None替代0.0 |
| V09 | 🟡中 | 异常 | __del__中访问可能已GC的对象 | Python关闭时 | hasattr检查 |
| V10 | 🟡中 | 异常 | 查询失败与无数据无法区分 | 数据库锁定 | 返回None区分 |
| V11 | 🔴高 | 通信 | MCGS无断线检测和重连 | 网络断开 | 健康检查+自动重连 |
| V12 | 🔴高 | 通信 | 接收线程退出后无重连 | 设备关机/重启 | 发射信号触发重连 |
| V13 | 🟡中 | 通信 | pymodbus响应未检查异常码 | TCP连接中断 | hasattr检查 |
| V14 | 🔴高 | 数据 | 寄存器偏移计算可能越界 | 配置地址错误 | 边界检查+日志 |
| V15 | 🔴高 | 数据 | float解析NaN/Inf未过滤 | 传感器故障/通信干扰 | math.isnan检查 |
| V16 | 🟡中 | 数据 | if False死代码导致数据丢失 | 解析失败时 | 删除死代码+标记错误 |
| V17 | 🟡中 | 数据 | 地址间隙过大读取无效数据 | 非连续地址配置 | 分块读取 |

---

### 12.7 按等级统计

| 等级 | 线程 | 内存 | 异常 | 通信 | 数据 | 合计 |
|------|------|------|------|------|------|------|
| 🔴 高 | 2 | 2 | 1 | 2 | 2 | **9** |
| 🟡 中 | 1 | 2 | 2 | 1 | 2 | **8** |
| **合计** | **3** | **4** | **3** | **3** | **4** | **17** |

---

### 12.8 修复优先级建议

| 优先级 | 问题编号 | 修复内容 | 预估工作量 |
|--------|---------|---------|-----------|
| P0 | V01 | disconnect()死锁修复 | 0.5天 |
| P0 | V04 | pymodbus连接失败关闭 | 0.5天 |
| P0 | V08 | bare except改为具体异常+None替代0.0 | 0.5天 |
| P0 | V11 | MCGS断线检测+自动重连 | 1天 |
| P0 | V14 | 寄存器偏移边界检查 | 0.5天 |
| P0 | V15 | NaN/Inf过滤 | 0.5天 |
| P1 | V02 | transaction_id加锁 | 0.5天 |
| P1 | V05 | __del__异常保护 | 0.5天 |
| P1 | V12 | 接收线程退出后触发重连信号 | 1天 |
| P1 | V16 | 删除if False死代码 | 0.5天 |
| P2 | V03 | recovery_history加上限 | 0.5天 |
| P2 | V06 | _value_cache过期清理 | 0.5天 |
| P2 | V07 | _monitor_panels断开清理 | 0.5天 |
| P2 | V09 | __del__中hasattr检查 | 0.5天 |
| P2 | V10 | 查询失败返回None | 0.5天 |
| P2 | V13 | pymodbus响应属性检查 | 0.5天 |
| P2 | V17 | 非连续地址分块读取 | 1天 |

**总计**: P0约3.5天，P1约2.5天，P2约4天，合计约10天
return 1
```

三处独立定义了"数据类型→寄存器数量"的映射关系，且不一致：

- 位置A支持 `uint32`，位置B不支持
- 位置C缺少 `INPUT_INT16` 的显式处理
- 位置B缺少 `int32`/`uint32`/`uint16`/`float32`/`input_int16`/`input_float32`

#### 问题22：MCGS地址基数硬编码

**文件**: `mcgs_modbus_reader.py:102,270,505`

```python
address_base: int = 1                          # 默认值硬编码
address_base=int(raw.get("address_base", 1)),  # JSON默认值硬编码
actual_start = start_addr - device.address_base # 1-based → 0-based
```

**问题**: Modbus标准中，保持寄存器(3xxxx)的地址基数取决于设备实现：

- 标准Modbus: 1-based (address\_base=1)
- pymodbus库: 0-based (address\_base=0)
- 某些PLC: 使用40001格式 (address\_base=40001)

当前硬编码 `address_base=1`，如果用户设备使用0-based地址，所有读取都会偏移1个寄存器。

#### 问题23：超时和重试参数硬编码

| 参数             | 位置                          | 硬编码值      | 应该可配置      |
| -------------- | --------------------------- | --------- | ---------- |
| socket连接超时     | `tcp_driver.py:112`         | `5.0`     | ✅          |
| poll\_buffer超时 | `modbus_protocol.py:810`    | `200ms`   | ✅          |
| 重试次数           | `modbus_protocol.py:49`     | `3`       | ✅          |
| 重试间隔           | `modbus_protocol.py:50`     | `0.5s`    | ✅          |
| 心跳间隔           | `tcp_driver.py:66`          | `10000ms` | ✅          |
| 轮询间隔           | `mcgs_modbus_reader.py:101` | `1000ms`  | ✅ (JSON可配) |

#### 问题24：数据类型字符串硬编码

**文件**: `mcgs_modbus_reader.py:745-756`

```python
if dtype in ("float", "float32"):        # 硬编码类型名
    raw_value = self._parse_float(...)
elif dtype in ("int16", "uint16"):       # 硬编码类型名
    raw_value = self._parse_int16(...)
elif dtype in ("int32", "uint32"):       # 硬编码类型名
    raw_value = self._parse_int32(...)
elif dtype in ("coil", "di"):            # 硬编码类型名
    raw_value = bool(point_regs[0])
```

这些类型名应该使用 `RegisterDataType` 枚举，而不是字符串比较。

#### 问题25：寄存器数量映射硬编码

**文件**: `mcgs_modbus_reader.py:68-74`

```python
type_map = {
    "float": 2, "float32": 2, "int32": 2, "uint32": 2,
    "int16": 1, "uint16": 1, "coil": 1, "di": 1,
}
return type_map.get(self.type.lower(), 2)  # 默认2 ← 未知类型默认占2个寄存器
```

**问题**: 未知类型默认返回2，可能掩盖配置错误。应该抛出异常或返回0。

#### 问题26：Modbus功能码硬编码

**文件**: `modbus_protocol.py:33-41`

```python
FC_READ_COILS = 0x01
FC_READ_DISCRETE_INPUTS = 0x02
FC_READ_HOLDING_REGISTERS = 0x03
...
```

这些是Modbus标准功能码，硬编码合理。但缺少FC08（诊断）和FC11（报告从站ID）的定义（FC08在 `tcp_driver.py` 中单独定义）。
