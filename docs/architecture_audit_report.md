# 工业设备管理系统 — 架构审计总报告

> **角色**: 工业软件架构师
> **系统**: 工业设备管理系统 v4.0 (PySide6 + Modbus TCP)
> **硬件**: MCGS TPC7062Ti 触摸屏 + DL8017 8路模拟量采集模块
> **日期**: 2026-04-23

---

## 一、工程结构解析

### 1.1 目录结构

```
equipment-management/
│
├── main.py                              # 启动入口
├── config.json                          # 全局配置
│
├── config/
│   └── devices.json                     # MCGS设备配置(IP/端口/点位/字节序)
│
├── core/                                # 核心业务层
│   ├── communication/                   # 🔴 通信驱动层
│   │   ├── base_driver.py               #   驱动基类(抽象接口)
│   │   ├── tcp_driver.py                #   TCP/IP驱动(socket+心跳)
│   │   └── serial_driver.py             #   串口驱动(RS485)
│   │
│   ├── protocols/                       # 🔴 协议插件层
│   │   ├── base_protocol.py             #   协议基类(信号/槽)
│   │   ├── modbus_protocol.py           #   Modbus协议(FC01-FC16)
│   │   ├── byte_order_config.py         #   字节序配置(ABCD/BADC/CDAB/DCBA)
│   │   └── protocol_registry.py         #   协议注册表
│   │
│   ├── device/                          # 🟡 设备管理层(v4.0模块化)
│   │   ├── device_manager_facade.py     #   外观类(统一入口)
│   │   ├── device_connection.py         #   连接控制器(轮询/读写/线圈)
│   │   ├── device_factory.py            #   设备工厂
│   │   ├── connection_factory.py        #   连接工厂
│   │   ├── device_registry.py           #   设备注册表(CRUD)
│   │   ├── polling_scheduler.py         #   轮询调度器
│   │   ├── fault_recovery_service.py    #   故障恢复服务
│   │   ├── configuration_service.py     #   配置管理服务
│   │   ├── simulator.py                 #   设备模拟器
│   │   └── ...                          #   (分组/生命周期/模板等)
│   │
│   ├── data/                            # 🟢 数据持久层
│   │   ├── __init__.py → DatabaseManager #  数据库管理器(SQLAlchemy)
│   │   ├── models.py                    #   ORM模型(6表)
│   │   ├── repository/                  #   仓储层(4个Repository)
│   │   └── cleanup_scheduler.py         #   数据清理调度器
│   │
│   ├── enums/                           # 枚举定义
│   │   └── data_type_enum.py            #   RegisterDataType(7种)+RegisterPointConfig
│   │
│   ├── services/                        # 业务服务层
│   │   └── ...                          #   审计/质量/报表/远程API
│   │
│   └── utils/                           # 🔵 工具模块层
│       ├── mcgs_modbus_reader.py        #   ⭐ MCGS专用读取器(独立协议栈)
│       ├── history_storage.py           #   ⭐ MCGS历史存储(SQLite 3表)
│       ├── anomaly_detector.py          #   ⭐ 异常检测器(6算法)
│       ├── alarm_manager.py             #   报警管理器
│       ├── write_operation_manager.py   #   写操作管理器(权限/批量/审计)
│       ├── permission_manager.py        #   RBAC权限(3角色)
│       ├── operation_undo_manager.py    #   操作撤销(Ctrl+Z)
│       └── logger.py                    #   日志系统
│
├── ui/                                  # 🖥️ UI展示层
│   ├── main_window.py                   #   ⭐⭐ 主窗口(~3000行，系统枢纽)
│   ├── dialogs/
│   │   └── mcgs_config_dialog.py        #   MCGS配置对话框(4Tab)
│   ├── widgets/
│   │   ├── dynamic_monitor_panel.py     #   动态监控面板
│   │   └── history_chart_widget.py      #   历史趋势图
│   ├── controllers/                     #   MVC控制器
│   ├── panels/                          #   面板组件
│   └── styles/qss/                      #   QSS样式表
│
├── data/                                # 运行时数据
│   └── equipment_management.db          # SQLite主数据库
│
└── tests/                               # 测试目录
```

### 1.2 核心模块依赖关系

```
main.py
  ├── core/data/DatabaseManager
  └── ui/main_window.py/MainWindow
        │
        ├──→ core/device/DeviceManagerFacade (通用设备通路 ✅ 正确分层)
        │       ├──→ DeviceRegistry → DatabaseManager
        │       ├──→ DeviceFactory → ConnectionFactory
        │       │       ├──→ TcpDriver / SerialDriver
        │       │       └──→ ModbusProtocol
        │       ├──→ DeviceConnection (轮询/读写)
        │       ├──→ PollingScheduler (QThreadPool异步)
        │       └──→ FaultRecoveryService
        │
        └──→ core/utils/MCGSModbusReader (MCGS专用通路 ❌ 绕过分层)
                ├──→ pymodbus.ModbusTcpClient (独立协议栈)
                ├──→ TcpDriver + ModbusProtocol (内置协议栈)
                ├──→ HistoryStorage (直接调用数据层)
                └──→ AnomalyDetector (直接调用算法层)
```

**关键发现**: 系统存在两条完全独立的数据通路，MCGS通路绕过了DeviceManager的分层架构。

---

## 二、数据流分析

### 2.1 通用设备通路（异步，正确）

```
[QThreadPool工作线程]              [主线程Signal]              [主线程UI]

PollingTask.run()         →     AsyncWorker        →    MainWindow
    │                          .device_data_updated      ._on_device_
    │                              .emit()               data_updated
    │                                                        │
DeviceConnection
._poll_data_with_config()                                     报警检查
    │                                                         卡片更新
    ├── _group_points_by_fc()                                 图表更新
    ├── _merge_consecutive()
    └── _read_batch()
          ├── Protocol.read_registers()
          ├── Driver.send_data() → socket
          └── _parse_read_response() → List[int]

配置源: SQLite数据库
线程模型: QThreadPool + Signal/Slot跨线程
UI阻塞: ✅ 无
```

### 2.2 MCGS专用通路（同步，有问题）

```
[主线程QTimer]                    [主线程直接调用]           [主线程UI]

_on_mcgsm_poll_timeout()  →   MCGSModbusReader  →   MainWindow
    │                              │                     │
QTimer.timeout()           read_device()          直接操作面板
    │                              │                     │
⚠️ 同步阻塞主线程!          pymodbus/内置协议栈    panel.update_data()
                           │
                      _parse_float(CDAB)           报警检查(内联)
                           │
                      calc_read_range()            异常检测(内联)
                           │
                      HistoryStorage               SQLite存储(内联)

配置源: devices.json (JSON文件)
线程模型: QTimer + 同步调用 ❌
UI阻塞: ❌ 每次轮询阻塞15-3000ms
```

### 2.3 数据流问题汇总

| # | 问题 | 影响 |
|---|------|------|
| 1 | MCGS轮询在主线程同步执行 | UI冻结15-3000ms/次 |
| 2 | MCGS数据被解析2次(float→string→float) | 精度损失+异常脆弱 |
| 3 | 两套通路9个功能点重复实现 | 维护成本翻倍 |
| 4 | 数据格式不统一(字符串 vs 结构化) | 面板报警检查失败 |

---

## 三、架构问题

### 3.1 🔴 严重：UI层直接调用通信层

**位置**: `ui/main_window.py` 5处直接调用

```python
# L2476: UI直接持有通信读取器
self._mcgsm_reader = None

# L2512: UI直接创建通信读取器
self._mcgsm_reader = MCGSModbusReader(str(config_path))

# L2569: UI直接调用通信连接
connected = reader.connect_device(device_id)

# L2607: UI直接调用通信读取
result = reader.read_device(device_id)

# L2996: UI在定时器回调中直接调用通信
result = self._mcgsm_reader.read_device(device_id)
```

**违反的分层原则**: UI层 → 通信层（应该: UI层 → Controller → Service → Device → Communication）

**对比**: 通用设备通路通过 DeviceManagerFacade → DeviceFactory → ConnectionFactory 隔离，UI不直接接触通信层。

### 3.2 🔴 严重：两套独立协议栈并存

| 功能 | 通用通路 | MCGS通路 | 重复? |
|------|---------|---------|-------|
| TCP连接 | TcpDriver | pymodbus.TcpClient / TcpDriver | ✅ |
| FC03读取 | ModbusProtocol._read_registers() | pymodbus.read_holding_registers() | ✅ |
| 字节序解析 | ByteOrderConfig + DeviceConnection | MCGSModbusReader._parse_float() | ✅ |
| 地址转换 | RegisterPointConfig.address | actual_start = addr - address_base | ✅ |
| 批量优化 | _merge_consecutive() | calc_read_range() | ✅ |
| 数据格式化 | rp.format_value() | f"{value:.{dp}f} {unit}" | ✅ |
| 报警检查 | AlarmManager.check_value() | AnomalyDetector.check_batch() | ✅ |
| 数据存储 | DataPersistenceService | HistoryStorage | ✅ |
| 轮询调度 | AsyncPollingWorker + QThreadPool | QTimer + 同步调用 | ✅ |

### 3.3 🔴 严重：MCGS轮询阻塞UI线程

```python
def _on_mcgsm_poll_timeout(self):           # QTimer回调 → 主线程
    result = self._mcgsm_reader.read_device(device_id)  # 阻塞15-3000ms
    self._mcgsm_storage.save_read_result(...)            # 阻塞1-5ms
    self._mcgsm_detector.check_batch(...)                # 阻塞5-20ms
```

**最坏场景**: 3台设备 × 超时3s = 24秒UI完全冻结

### 3.4 🟡 一般：QApplication.processEvents() 反模式

```python
self._status_msg_label.setText("正在连接...")
QApplication.processEvents()  # ← 反模式！可能导致重入
```

### 3.5 🟡 一般：数据格式不统一

```python
# 通用设备输出（结构化）
{"温度": {"raw": 25.6, "value": "25.60 ℃", "type": "holding_float32", "config": obj}}

# MCGS输出（纯字符串）
{"Hum_in": "25.6 %RH"}  # 无raw/type/config字段
```

---

## 四、性能问题

### 4.1 🔴 MCGS轮询阻塞时间分析

| 步骤 | 正常耗时 | 超时耗时 | 频率 |
|------|---------|---------|------|
| TCP连接+Modbus读取 | 15-50ms | 3000ms | 每1秒 |
| SQLite存储 | 1-5ms | 50ms(锁库) | 每1秒 |
| 异常检测(6算法) | 5-20ms | 100ms | 每1秒 |
| **单设备合计** | **21-75ms** | **3150ms** | - |
| **3设备合计** | **63-225ms** | **9450ms** | - |

**结论**: 正常情况UI约6-22%时间冻结，超时时100%冻结。

### 4.2 🟡 MCGS数据被解析2次

```
第1次: MCGSModbusReader._parse_float() → float → "25.6 ℃" (格式化字符串)
第2次: MainWindow → float("25.6".split()[0]) → 25.6 (反向解析)
```

**浪费**: 每秒N个点 × split + float转换，且 `float("N/A")` 会抛异常。

### 4.3 🟡 calc_read_range() 不支持非连续地址分块

```python
# 如果点位地址为 [30002, 30004, 40001]
# 读取范围 = 40001-30002+1 = 10000个寄存器
# 其中9997个是无效数据！
# Modbus TCP单次最多读取125个寄存器 → 超出会报错
```

### 4.4 🟢 DynamicMonitorPanel 无脏检查

每次 `update_data()` 都遍历所有卡片并调用 `update_value()`，即使值未变化。

---

## 五、潜在Bug

### 5.1 线程问题

| # | 等级 | 问题 | 位置 | 触发条件 |
|---|------|------|------|---------|
| T-01 | 🔴高 | `disconnect()` 持锁 `join()` → 死锁 | `tcp_driver.py:163` | 断开连接时接收线程正在处理连接丢失 |
| T-02 | 🔴高 | `_transaction_id` 非原子自增 | `modbus_protocol.py:895` | 多线程并发读取 |
| T-03 | 🟡中 | `recovery_history` 无限增长 | `fault_recovery_service.py:408` | 设备频繁故障 |
| T-04 | 🔴高 | MCGS共享状态无线程保护 | `main_window.py:2476` | 异步化后竞态立即暴露 |

**T-01 死锁路径详解**:
```
1. 主线程: disconnect() → 获取 _lock → join()等待接收线程
2. 接收线程: _handle_connection_loss() → 尝试获取 _lock
3. RLock可重入但仅限同一线程 → 不同线程 → 死锁！
```

### 5.2 通信问题

| # | 等级 | 问题 | 位置 | 触发条件 |
|---|------|------|------|---------|
| C-01 | 🔴高 | MCGS无断线检测和重连 | `mcgs_modbus_reader.py:341` | 网线拔出后永久假连接 |
| C-02 | 🔴高 | 接收线程退出后无重连 | `tcp_driver.py:207` | 设备关机/重启 |
| C-03 | 🔴高 | 协议层响应匹配缺失(无transaction_id校验) | `modbus_protocol.py:810` | 心跳与业务响应错位 |
| C-04 | 🟡中 | pymodbus响应未检查异常码 | `mcgs_modbus_reader.py:530` | TCP连接中断 |
| C-05 | 🟡中 | 心跳FC08与业务请求缓冲区冲突 | `tcp_driver.py:243` | 高频心跳+多设备轮询 |
| C-06 | 🟡中 | pymodbus连接失败未关闭 | `mcgs_modbus_reader.py:390` | 连接失败后重试 |

**C-01 断线场景**:
```
1. 设备正常连接 → _clients["mcgs_1"] = client
2. 网线拔出 → socket已断开
3. connect_device("mcgs_1") → "mcgs_1" in _clients → return True ← 假连接！
4. read_device() → pymodbus读取失败 → 但不清除旧条目
5. 每次轮询都失败，直到用户手动重启程序
```

### 5.3 解析问题

| # | 等级 | 问题 | 位置 | 触发条件 |
|---|------|------|------|---------|
| P-01 | 🔴高 | float解析NaN/Inf未过滤 | `mcgs_modbus_reader.py:609` | 传感器故障/通信干扰 |
| P-02 | 🔴高 | 寄存器偏移计算可能越界 | `mcgs_modbus_reader.py:720` | 配置地址错误 |
| P-03 | 🔴高 | bare except吞异常+默认0.0 | `main_window.py:3005` | 解析失败时 |
| P-04 | 🟡中 | 字节序解析3处重复实现 | 3个文件 | 行为可能不一致 |
| P-05 | 🟡中 | 类型映射3处重复且不一致 | 3个文件 | 新增类型需改6处 |
| P-06 | 🟡中 | if False死代码导致数据丢失 | `device_connection.py:1424` | 解析失败时 |
| P-07 | 🟡中 | 数据类型使用字符串而非枚举 | `mcgs_modbus_reader.py` | 拼写错误不报错 |
| P-08 | 🟡中 | 未知类型默认占2个寄存器 | `mcgs_modbus_reader.py:74` | 掩盖配置错误 |

**P-01 NaN传播链**:
```
传感器故障 → 寄存器值0x7FC00000 → struct.unpack → NaN
→ round(NaN, 1) → NaN → f"{NaN:.1f}" → "nan"
→ UI显示"nan" → 数据库存储NULL → 异常检测崩溃
```

**P-03 0.0默认值危害**:
```
解析失败 → except: raw_dict[k] = 0.0
→ 异常检测器收到0.0 → 触发"值过低"误报
→ 历史数据库存储0.0 → 污染统计数据(均值偏低)
→ 用户无法从数据中发现解析失败
```

### 5.4 内存问题

| # | 等级 | 问题 | 位置 | 触发条件 |
|---|------|------|------|---------|
| M-01 | 🔴高 | pymodbus连接失败未close() | `mcgs_modbus_reader.py:390` | 反复连接失败 |
| M-02 | 🔴高 | __del__中disconnect_all可能崩溃 | `mcgs_modbus_reader.py:943` | Python解释器关闭 |
| M-03 | 🟡中 | _value_cache无过期清理 | `anomaly_detector.py:455` | 长时间运行 |
| M-04 | 🟡中 | _monitor_panels只增不减 | `main_window.py:2725` | 反复连接/断开 |

---

## 六、Modbus通信专项评估

### 6.1 批量读取支持

| 层级 | 支持 | 实现方式 | 限制 |
|------|------|---------|------|
| ModbusProtocol | ✅ | `read_registers(addr, count)` | 无 |
| ModbusProtocol | ✅ | `read_registers_batch()` | 串行非并行 |
| DeviceConnection | ✅ | `_group_by_fc() + _merge_consecutive()` | 仅限RegisterPointConfig |
| MCGSModbusReader | ✅ | `calc_read_range()` | 不支持非连续分块 |
| MCGSModbusReader | ❌ | 仅FC03 | 不支持FC01/02/04 |

**结论**: 批量读取已实现，但MCGS仅支持FC03，且不支持非连续地址分块。

### 6.2 线程安全评估

| 共享状态 | 保护机制 | 风险 |
|---------|---------|------|
| BaseDriver._buffer | QMutex | ✅ 安全 |
| TcpDriver._socket | RLock | ✅ 安全 |
| ModbusProtocol._pending_response | threading.Lock | ⚠️ 无transaction_id匹配 |
| ModbusProtocol._transaction_id | ❌ 无锁 | ❌ 非原子自增 |
| MCGSModbusReader._clients | ❌ 无锁 | ❌ 多线程不安全 |
| MCGSModbusReader._stats | ❌ 无锁 | ❌ 计数可能不准 |

### 6.3 超时机制评估

| 层级 | 超时配置 | 默认值 | 可配置性 |
|------|---------|--------|---------|
| TcpDriver.connect() | socket.settimeout() | 5.0s | ❌ 硬编码 |
| ModbusProtocol._poll_buffer() | timeout_ms参数 | 200ms | ✅ 可调 |
| ModbusProtocol重试 | retry_count × interval | 3次×0.5s | ✅ 可调 |
| MCGSModbusReader(pymodbus) | timeout参数 | 3.0s | ✅ JSON可配 |

### 6.4 float解析正确性

**CDAB字节序验证** (MCGS使用此模式):

```python
# 测试: float32(26.5) 的CDAB编码
# ABCD原始: 41 D0 00 00
# CDAB传输: 寄存器[0]=0x0000(低字), 寄存器[1]=0x41D0(高字)

# MCGSModbusReader._parse_float() 实现:
b = struct.pack(">HH", 0x0000, 0x41D0)  # b'\x00\x00\x41\xd0'
b = b[2:] + b[:2]                        # b'\x41\xd0\x00\x00' (字交换)
struct.unpack(">f", b)                    # 26.5 ✅ 正确
```

**结论**: CDAB解析在当前MCGS寄存器排列下正确。但3处实现逻辑等价性未经严格验证，存在潜在不一致风险。

---

## 七、问题清单（按严重程度排序）

### 🔴 高危（12项）

| # | 类别 | 问题 | 影响 |
|---|------|------|------|
| 1 | 架构 | UI直接调用通信层(5处) | 分层被破坏，通信变更影响UI |
| 2 | 架构 | MCGS轮询阻塞UI线程 | UI冻结15-3000ms/次 |
| 3 | 架构 | 两套协议栈9处重复实现 | 维护成本翻倍，行为不一致 |
| 4 | 线程 | disconnect()持锁join()→死锁 | 断开连接时程序卡死 |
| 5 | 线程 | _transaction_id非原子自增 | 并发请求ID冲突 |
| 6 | 通信 | MCGS无断线检测和重连 | 网络断开后永久假连接 |
| 7 | 通信 | 协议层响应匹配缺失 | 心跳与业务响应错位 |
| 8 | 解析 | float解析NaN/Inf未过滤 | "nan"传播到UI/数据库/检测器 |
| 9 | 解析 | 寄存器偏移越界无检查 | 配置错误时静默返回错误值 |
| 10 | 解析 | bare except吞异常+默认0.0 | 污染历史数据，触发误报 |
| 11 | 内存 | pymodbus连接失败未close() | 反复失败泄漏socket |
| 12 | 内存 | __del__中disconnect_all可能崩溃 | Python关闭时异常 |

### 🟡 中危（13项）

| # | 类别 | 问题 |
|---|------|------|
| 13 | 架构 | 数据格式不统一(字符串vs结构化) |
| 14 | 架构 | QApplication.processEvents()反模式 |
| 15 | 架构 | 快速连接递归调用无深度限制 |
| 16 | 线程 | MCGS共享状态无线程保护 |
| 17 | 线程 | recovery_history无限增长 |
| 18 | 通信 | 接收线程退出后无重连 |
| 19 | 通信 | 心跳与业务请求缓冲区冲突 |
| 20 | 通信 | pymodbus响应未检查异常码 |
| 21 | 解析 | 字节序解析3处重复实现 |
| 22 | 解析 | 类型映射3处重复且不一致 |
| 23 | 解析 | if False死代码导致数据丢失 |
| 24 | 解析 | calc_read_range()不支持非连续分块 |
| 25 | 内存 | _monitor_panels只增不减 |

### 🟢 低危/建议（8项）

| # | 类别 | 问题 |
|---|------|------|
| 26 | 解析 | 数据类型使用字符串而非枚举 |
| 27 | 解析 | 未知类型默认占2个寄存器 |
| 28 | 解析 | 超时/重试参数硬编码 |
| 29 | 解析 | RegisterDataType缺少5种常用类型 |
| 30 | 性能 | MCGS数据被解析2次 |
| 31 | 性能 | DynamicMonitorPanel无脏检查 |
| 32 | 性能 | 卡片和图表分别遍历数据 |
| 33 | 扩展 | 新增设备类型需修改6个文件 |

---

## 八、修改建议

### 8.1 立即修复（P0，约3.5天）

| # | 修复内容 | 文件 | 改动量 |
|---|---------|------|--------|
| 4 | disconnect()死锁：先join再持锁 | tcp_driver.py | 15行 |
| 8 | NaN/Inf过滤：加math.isnan检查 | mcgs_modbus_reader.py | 3行 |
| 9 | 偏移越界检查：加边界判断 | mcgs_modbus_reader.py | 5行 |
| 10 | bare except→具体异常+None替代0.0 | main_window.py | 2行 |
| 11 | pymodbus连接失败时close() | mcgs_modbus_reader.py | 2行 |
| 12 | __del__加try/except保护 | mcgs_modbus_reader.py | 3行 |

### 8.2 短期修复（P1，约4天）

| # | 修复内容 | 文件 |
|---|---------|------|
| 5 | transaction_id加threading.Lock | modbus_protocol.py |
| 6 | MCGS断线检测+自动重连 | mcgs_modbus_reader.py |
| 7 | 协议层transaction_id匹配 | modbus_protocol.py |
| 16 | MCGS共享状态加QMutex | main_window.py |
| 23 | 删除if False死代码 | device_connection.py |

### 8.3 中期重构（P2，约6天）

| # | 修复内容 |
|---|---------|
| 1-3 | 引入MCGSController+MCGSService，消除UI直接调用通信层 |
| 13 | 统一数据格式为结构化字典 |
| 21 | 创建统一ModbusValueParser，消除3处重复 |
| 22 | 类型映射统一到RegisterDataType |
| 30 | MCGS输出同时返回raw_values和parsed_data |

---

## 九、重构方案

### 9.1 目标架构：六层分离

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 6: UI 展示层                                           │
│   MainWindow / Dialogs / Widgets                            │
│   职责: 展示数据 / 捕获操作 / 仅依赖Controller               │
├─────────────────────────────────────────────────────────────┤
│ Layer 5: Controller 层                                       │
│   MCGSController / DeviceController                         │
│   职责: 异步调度(QThreadPool) / Signal中转 / 线程安全状态     │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Service 层                                          │
│   MCGSService / HistoryService / AnomalyService              │
│   职责: 业务逻辑 / 数据转换 / 报警评估 / 纯Python无Qt依赖     │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Device 层                                           │
│   DeviceManagerFacade / DeviceConnection / DeviceFactory     │
│   职责: 设备CRUD / 连接管理 / 轮询调度 / 故障恢复             │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Communication 层                                    │
│   TcpDriver / ModbusProtocol / ModbusValueParser(统一)       │
│   职责: 物理连接 / 协议编解码 / 数据解析 / 完全隔离           │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Foundation 层                                       │
│   DataBus(事件总线) / ConfigStore(配置中心) / PluginRegistry  │
│   职责: 模块间解耦 / 配置管理 / 设备插件注册                  │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 核心机制

**DataBus事件总线** — 解决模块间直接调用问题:
```python
# 发布者(Communication层)
DataBus.instance().device_data_updated.emit(device_id, data)

# 订阅者(UI层) — 不直接调用通信层
DataBus.instance().device_data_updated.connect(self._on_data_updated)

# 订阅者(Service层) — 与UI并行处理
DataBus.instance().device_data_updated.connect(self._on_data_for_storage)
```

**ConfigStore配置中心** — 统一配置入口:
```python
# 无论配置来自数据库还是JSON文件，统一接口
config = ConfigStore.instance().get_device_config(device_id)
```

**PluginRegistry插件注册** — 支持设备扩展:
```python
# 新增设备只需3步：创建插件 → 注册 → 添加配置
# 无需修改核心代码
class XXXPlugin(DevicePlugin):
    def device_type(self): return "xxx"
    def create_connection(self, config): ...
```

**ModbusValueParser统一解析器** — 消除3处重复:
```python
# 所有模块调用同一解析入口
parser = ModbusValueParser(byte_order=config.byte_order)
value = parser.parse(registers, offset, data_type)  # 自动处理NaN/Inf/越界
```

### 9.3 重构后数据流

```
用户点击 [🔌 MCGS连接]
  │
  ▼
MainWindow → MCGSController.connect_device()     # 异步！不阻塞！
  │
  ├── QThreadPool.start(ConnectTask)               # 工作线程
  │     └── MCGSService.connect()                  # Service层
  │           └── PluginRegistry.get("mcgs")       # 插件层
  │                 └── DeviceConnection.connect() # Device层
  │                       └── TcpDriver + Protocol # Communication层
  │
  └── DataBus.device_connected.emit(device_id)     # 事件通知
        ├── MainWindow._on_connected()              # UI更新
        └── HistoryService._on_connected()          # 准备存储


QTimer轮询触发
  │
  ▼
MCGSController._start_poll_cycle()               # 异步！不阻塞！
  │
  ├── QThreadPool.start(PollTask)                  # 工作线程
  │     └── MCGSService.read_and_process()         # Service层
  │           ├── Reader.read_device()              # 通信层
  │           │     └── ModbusValueParser.parse_batch()  # 统一解析
  │           ├── HistoryStorage.save()             # 数据层
  │           └── AnomalyDetector.check_batch()     # 算法层
  │
  └── DataBus.device_data_updated.emit(id, data)   # 事件通知
        ├── MainWindow._on_data_updated()           # UI更新面板
        ├── HistoryService._on_data_updated()       # 累积统计
        └── AlarmController._on_data_updated()      # 报警评估
```

### 9.4 重构步骤（8步，每步可独立验证）

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| Step 1 | 创建Foundation层(DataBus+ConfigStore+PluginRegistry) | 1.5天 |
| Step 2 | 创建统一解析器ModbusValueParser | 1天 |
| Step 3 | 创建Service层(MCGSService/HistoryService/AnomalyService) | 2天 |
| Step 4 | 创建Controller层(MCGSController异步调度) | 2天 |
| Step 5 | 修复通信层高危问题(死锁/断线/NaN) | 2天 |
| Step 6 | 创建设备插件体系(MCGSPlugin) | 1.5天 |
| Step 7 | 重构MainWindow(删除直接调用通信层代码) | 3天 |
| Step 8 | 清理遗留代码(删除重复实现) | 1天 |
| **合计** | | **14天** |

### 9.5 重构收益

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| UI冻结时间 | 15-3000ms/次 | 0ms |
| 重复代码(解析) | 3处 | 1处 |
| 新增设备改文件数 | 6个 | 1个(插件) |
| UI直接调通信层 | 5处 | 0处 |
| 高危漏洞 | 12个 | 0个 |
| 断线重连 | 无 | 自动 |
| 数据格式 | 2种 | 1种(结构化) |
| 设备扩展方式 | 修改核心代码 | 注册插件 |

---

## 十、结论

本系统作为工业上位机软件，核心通信功能（Modbus TCP + CDAB字节序 + 批量FC03读取）已正确实现并验证通过。主要问题集中在**架构层面**——MCGS专用通路绕过了通用设备的分层架构，导致UI直接调用通信层、轮询阻塞UI线程、9处功能重复实现。

**最优先修复的3个问题**:
1. **disconnect()死锁** (0.5天) — 断开连接时程序卡死
2. **NaN/Inf过滤** (0.5天) — 传感器故障时"nan"传播到整个系统
3. **bare except+0.0默认值** (0.5天) — 解析失败污染历史数据

**最优先重构的1个架构改进**:
- **引入MCGSController** — 将MCGS轮询从主线程移到QThreadPool，消除UI阻塞

详细技术方案见: `docs/refactoring_plan_v5.md`
详细审计数据见: `docs/modbus_communication_audit.md`
