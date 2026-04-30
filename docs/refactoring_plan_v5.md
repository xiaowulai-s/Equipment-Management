# 工业设备管理系统 — 完整重构方案

> **版本**: v5.0
> **日期**: 2026-04-23
> **目标**: 分层架构 / DataBus解耦 / 配置驱动 / 设备扩展

---

## 一、当前架构问题

```
当前架构（v4.0）:

  MainWindow ──────────────────→ MCGSModbusReader (通信层)
      │                              │
      ├── 直接调用 connect_device()   ├── pymodbus (独立协议栈)
      ├── 直接调用 read_device()      ├── 内置 Protocol (重复协议栈)
      ├── 直接调用 HistoryStorage     └── _parse_float() (重复解析)
      ├── 直接调用 AnomalyDetector
      └── QTimer 同步轮询 (阻塞UI)

  MainWindow ──→ DeviceManagerFacade ──→ DeviceConnection ──→ Protocol ──→ Driver
  (通用通路，正确分层)                   (MCGS通路，绕过分层)

  问题汇总:
  ├── 🔴 UI直接调用通信层 (5处)
  ├── 🔴 MCGS轮询阻塞UI (15-3000ms/次)
  ├── 🔴 两套协议栈并存 (pymodbus + 内置)
  ├── 🔴 字节序解析3处重复
  ├── 🔴 数据格式不统一 (字符串 vs 结构化)
  ├── 🟡 无断线检测/重连
  ├── 🟡 transaction_id竞态
  └── 🟡 bare except吞异常
```

---

## 二、目标架构

### 2.1 六层架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Layer 6: UI 展示层                              │
│                                                                         │
│  MainWindow / Dialogs / Widgets / Panels                                │
│  职责: 展示数据 / 捕获用户操作 / 发射信号给Controller                     │
│  禁止: 直接调用通信层 / 直接操作数据库 / 在主线程执行阻塞操作              │
│  依赖: 仅依赖 Controller 层                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                         Layer 5: Controller 层                           │
│                                                                         │
│  DeviceController / MCGSController / AlarmController                    │
│  职责: 协调UI和Service / 异步调度(QThreadPool) / 线程安全状态管理         │
│  特点: 持有QThreadPool / 管理QTimer / Signal中转                         │
│  依赖: 仅依赖 Service 层 + DataBus                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                          Layer 4: Service 层                             │
│                                                                         │
│  DeviceService / MCGSService / HistoryService / AnomalyService          │
│  职责: 业务逻辑 / 数据转换 / 报警评估 / 历史存储                         │
│  特点: 纯Python / 无Qt依赖 / 可独立测试                                  │
│  依赖: 仅依赖 Device 层 + Data 层                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                         Layer 3: Device 层                               │
│                                                                         │
│  DeviceManagerFacade / DeviceConnection / DeviceFactory                  │
│  职责: 设备CRUD / 连接管理 / 轮询调度 / 故障恢复                         │
│  特点: 管理设备生命周期 / 配置驱动创建                                    │
│  依赖: 仅依赖 Communication 层 + Data 层                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                      Layer 2: Communication 层                           │
│                                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐     │
│  │  Driver 层       │  │  Protocol 层      │  │  Parser 层          │     │
│  │  TcpDriver      │  │  ModbusProtocol  │  │  ModbusValueParser │     │
│  │  SerialDriver   │  │  (FC01-FC16)     │  │  (统一字节序解析)   │     │
│  │  SimulatedDriver│  │  ProtocolRegistry│  │  (NaN/Inf过滤)     │     │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘     │
│  职责: 物理连接 / 协议编解码 / 数据解析                                   │
│  特点: 完全隔离 / 可替换 / 无业务逻辑                                     │
│  依赖: 仅依赖 DataBus (发送解析结果)                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                          Layer 1: Foundation 层                          │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  DataBus      │  │  ConfigStore  │  │  Data Layer   │                  │
│  │  (事件总线)   │  │  (配置中心)   │  │  (ORM/SQLite) │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│  职责: 模块间解耦通信 / 配置管理 / 数据持久化                             │
│  特点: 全局单例 / 线程安全 / 所有层均可访问                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

| 原则 | 说明 | 实现方式 |
|------|------|---------|
| **单向依赖** | 上层依赖下层，下层不感知上层 | import方向: UI→Controller→Service→Device→Comm→Foundation |
| **DataBus解耦** | 模块间通过事件总线通信，不直接调用 | 发布/订阅模式，主题驱动 |
| **配置驱动** | 所有设备参数来自配置文件，代码不硬编码 | ConfigStore + devices.json + 数据库 |
| **插件扩展** | 新设备类型通过注册表添加，不修改核心代码 | DevicePlugin接口 + PluginRegistry |

---

## 三、DataBus 事件总线

### 3.1 设计

```python
# core/foundation/data_bus.py

class DataBus(QObject):
    """
    全局事件总线 — 模块间解耦通信的核心

    设计原则:
    - 发布/订阅模式: 生产者不关心谁消费
    - 主题驱动: 按主题过滤消息
    - 线程安全: 跨线程Signal自动排队
    - 类型安全: 每个主题有明确的数据类型
    """

    _instance = None

    @classmethod
    def instance(cls) -> 'DataBus':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── 信号定义（按主题分组）──

    # 设备生命周期主题
    device_connected = Signal(str)                    # device_id
    device_disconnected = Signal(str)                 # device_id
    device_status_changed = Signal(str, str)          # device_id, status

    # 数据更新主题
    device_data_updated = Signal(str, dict)           # device_id, structured_data
    device_raw_updated = Signal(str, dict)            # device_id, raw_values

    # 报警主题
    alarm_triggered = Signal(str, str, str, float)    # device_id, param, level, value
    alarm_cleared = Signal(str, str)                  # device_id, param

    # 通信主题
    comm_error = Signal(str, str)                     # device_id, error_msg
    comm_quality_updated = Signal(str, dict)          # device_id, quality_stats

    # 配置主题
    config_changed = Signal(str)                      # config_section
    device_config_updated = Signal(str)               # device_id

    # 系统主题
    system_shutdown = Signal()
```

### 3.2 DataBus 使用示例

```python
# ── 发布者（Communication层）──
class DeviceConnection:
    def _on_poll_success(self, device_id, data):
        DataBus.instance().device_data_updated.emit(device_id, data)

# ── 订阅者（UI层）──
class MainWindow:
    def __init__(self):
        DataBus.instance().device_data_updated.connect(self._on_data_updated)

    def _on_data_updated(self, device_id, data):
        self._update_monitor_panel(device_id, data)

# ── 订阅者（Service层，与UI并行）──
class HistoryService:
    def __init__(self):
        DataBus.instance().device_data_updated.connect(self._on_data_for_storage)

    def _on_data_for_storage(self, device_id, data):
        self.save(device_id, data)  # 独立于UI的存储逻辑
```

### 3.3 DataBus 解决的问题

| 问题 | DataBus如何解决 |
|------|----------------|
| UI直接调用通信层 | UI订阅DataBus信号，不直接调用通信层 |
| 数据格式不统一 | DataBus传递标准化的StructuredData |
| 重复刷新 | DataBus信号只发一次，多个订阅者各自处理 |
| 新增功能需改多处 | 新功能只需订阅DataBus信号，不修改发布者 |
| 线程安全 | Qt Signal/Slot自动跨线程排队 |

---

## 四、ConfigStore 配置中心

### 4.1 设计

```python
# core/foundation/config_store.py

class ConfigStore(QObject):
    """
    配置中心 — 统一管理所有配置源

    配置优先级: 命令行 > 环境变量 > 用户配置 > 默认值

    配置源:
    1. config.json — 全局系统配置
    2. devices.json — MCGS设备配置
    3. 数据库 — 设备注册信息
    4. 代码默认值 — 兜底配置
    """

    config_changed = Signal(str)  # section_name

    _instance = None

    @classmethod
    def instance(cls) -> 'ConfigStore':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        """获取设备配置（统一入口，无论来源）"""
        # 1. 先查数据库（用户通过UI添加的设备）
        config = self._db_repo.get(device_id)
        if config:
            return config

        # 2. 再查devices.json（MCGS配置文件）
        config = self._json_config.get(device_id)
        if config:
            return config

        return None

    def update_device_config(self, device_id: str, config: DeviceConfig):
        """更新设备配置（自动持久化）"""
        self._db_repo.save(device_id, config)
        self.config_changed.emit(device_id)
        DataBus.instance().device_config_updated.emit(device_id)
```

### 4.2 统一设备配置模型

```python
# core/foundation/config_models.py

@dataclass
class DeviceConfig:
    """统一设备配置模型 — 所有设备类型共用"""

    id: str
    name: str
    device_type: str                          # "mcgs" / "plc" / "meter" / "custom"

    # 连接参数
    connection: ConnectionConfig

    # 数据点位
    points: List[PointConfig]

    # 轮询参数
    polling_interval_ms: int = 1000
    timeout_ms: int = 3000
    max_retries: int = 3

    # 字节序
    byte_order: str = "CDAB"
    address_base: int = 1

    # 报警阈值（全局默认，可被点位级覆盖）
    default_alarm_high: Optional[float] = None
    default_alarm_low: Optional[float] = None

    # 扩展属性（插件可自由使用）
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConnectionConfig:
    protocol: str = "modbus_tcp"              # "modbus_tcp" / "modbus_rtu" / "opcua" / "custom"
    ip: str = "127.0.0.1"
    port: int = 502
    unit_id: int = 1
    serial_port: Optional[str] = None         # RTU模式
    baud_rate: int = 9600                     # RTU模式

@dataclass
class PointConfig:
    name: str
    addr: int
    data_type: RegisterDataType               # 使用枚举，不再用字符串
    unit: str = ""
    decimal_places: int = 1
    scale: float = 1.0
    alarm_high: Optional[float] = None
    alarm_low: Optional[float] = None
    writable: bool = False
    description: str = ""

    @property
    def register_count(self) -> int:
        return self.data_type.get_register_count()
```

---

## 五、设备插件扩展机制

### 5.1 设计

```python
# core/foundation/plugin_registry.py

class DevicePlugin(ABC):
    """设备插件接口 — 所有设备类型必须实现"""

    @abstractmethod
    def device_type(self) -> str:
        """设备类型标识，如 'mcgs', 'plc_s7', 'meter_dl8017'"""
        ...

    @abstractmethod
    def create_connection(self, config: DeviceConfig) -> 'DeviceConnection':
        """根据配置创建设备连接实例"""
        ...

    @abstractmethod
    def create_parser(self, config: DeviceConfig) -> 'ModbusValueParser':
        """根据配置创建数据解析器"""
        ...

    @abstractmethod
    def default_config(self) -> Dict:
        """返回该设备类型的默认配置模板"""
        ...

    @abstractmethod
    def validate_config(self, config: DeviceConfig) -> Tuple[bool, str]:
        """验证配置是否合法"""
        ...


class PluginRegistry:
    """插件注册表 — 运行时注册/发现设备插件"""

    _plugins: Dict[str, DevicePlugin] = {}

    @classmethod
    def register(cls, plugin: DevicePlugin):
        cls._plugins[plugin.device_type()] = plugin

    @classmethod
    def get(cls, device_type: str) -> Optional[DevicePlugin]:
        return cls._plugins.get(device_type)

    @classmethod
    def list_types(cls) -> List[str]:
        return list(cls._plugins.keys())
```

### 5.2 内置插件

```python
# core/plugins/mcgs_plugin.py

class MCGSPlugin(DevicePlugin):
    """MCGS触摸屏设备插件"""

    def device_type(self) -> str:
        return "mcgs"

    def create_connection(self, config: DeviceConfig):
        # 复用现有 DeviceConnection，但通过 ConfigStore 驱动
        return DeviceConnection(config)

    def create_parser(self, config: DeviceConfig):
        # 使用统一的 ModbusValueParser，不再自实现
        return ModbusValueParser(byte_order=config.byte_order)

    def default_config(self) -> Dict:
        return {
            "id": "mcgs_1",
            "name": "MCGS触摸屏",
            "device_type": "mcgs",
            "connection": {"protocol": "modbus_tcp", "ip": "192.168.1.100", "port": 502},
            "byte_order": "CDAB",
            "address_base": 1,
            "points": [
                {"name": "Hum_in", "addr": 30002, "data_type": "holding_float32", "unit": "%RH"},
                ...
            ]
        }

    def validate_config(self, config: DeviceConfig):
        errors = []
        if config.byte_order not in ("ABCD", "BADC", "CDAB", "DCBA"):
            errors.append(f"不支持的字节序: {config.byte_order}")
        if config.connection.protocol != "modbus_tcp":
            errors.append("MCGS仅支持Modbus TCP")
        return len(errors) == 0, "; ".join(errors)


# core/plugins/__init__.py — 自动注册所有内置插件
def register_builtin_plugins():
    PluginRegistry.register(MCGSPlugin())
    PluginRegistry.register(PLCPlugin())
    PluginRegistry.register(MeterPlugin())
```

### 5.3 扩展新设备只需3步

```python
# 步骤1: 创建插件文件 core/plugins/xxx_plugin.py
class XXXPlugin(DevicePlugin):
    def device_type(self): return "xxx"
    def create_connection(self, config): ...
    def create_parser(self, config): ...
    def default_config(self): ...
    def validate_config(self, config): ...

# 步骤2: 注册插件 core/plugins/__init__.py
PluginRegistry.register(XXXPlugin())

# 步骤3: 添加配置 config/devices.json
{
    "id": "xxx_1",
    "device_type": "xxx",
    "connection": {...},
    "points": [...]
}
```

无需修改任何核心代码。

---

## 六、统一解析器

### 6.1 设计

```python
# core/communication/modbus_value_parser.py

class ModbusValueParser:
    """
    统一的Modbus寄存器值解析器

    替代当前3处重复实现:
    - ModbusProtocol._parse_register_value()
    - MCGSModbusReader._parse_float()
    - DeviceConnection._decode_point_value()
    """

    def __init__(self, byte_order: ByteOrderConfig = None):
        self._byte_order = byte_order or ByteOrderConfig.big_endian()
        self._tid_lock = threading.Lock()
        self._transaction_id = 0

    def parse(self, registers: List[int], offset: int,
              data_type: RegisterDataType) -> Optional[Union[bool, int, float]]:
        """
        统一解析入口

        Args:
            registers: 原始寄存器值列表
            offset: 起始偏移（寄存器索引，非字节索引）
            data_type: 数据类型枚举

        Returns:
            解析后的值，失败返回None
        """
        import math

        reg_count = data_type.get_register_count()

        # 边界检查
        if offset < 0 or offset + reg_count > len(registers):
            return None

        # 布尔类型
        if data_type in (RegisterDataType.COIL, RegisterDataType.DISCRETE_INPUT):
            return bool(registers[offset])

        # 16位类型
        if reg_count == 1:
            raw = registers[offset]
            if data_type == RegisterDataType.HOLDING_INT16:
                return struct.unpack(">h", struct.pack(">H", raw))[0]
            return raw  # uint16

        # 32位类型
        regs = registers[offset:offset + reg_count]
        raw_bytes = struct.pack(">HH", int(regs[0]), int(regs[1]))
        swapped = self._byte_order.swap_bytes_for_32bit(raw_bytes)
        fmt = self._byte_order.get_struct_format("float32")
        value = struct.unpack(fmt, swapped)[0]

        # NaN/Inf过滤
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None

        return value

    def parse_batch(self, registers: List[int],
                    points: List[PointConfig],
                    start_addr: int) -> Dict[str, Any]:
        """
        批量解析 — 替代 _parse_all_points()

        Returns:
            {point_name: {"raw": float, "value": str, "type": str, "config": PointConfig}}
        """
        result = {}
        for point in points:
            offset = point.addr - start_addr
            raw_value = self.parse(registers, offset, point.data_type)

            if raw_value is not None:
                scaled = raw_value * point.scale
                formatted = f"{scaled:.{point.decimal_places}f}"
                if point.unit:
                    formatted += f" {point.unit}"

                result[point.name] = {
                    "raw": raw_value,
                    "value": formatted,
                    "type": point.data_type.code,
                    "writable": point.writable,
                    "config": point,
                }
            else:
                result[point.name] = {
                    "raw": None,
                    "value": "N/A",
                    "type": point.data_type.code,
                    "writable": point.writable,
                    "config": point,
                    "error": "parse_failed",
                }

        return result
```

---

## 七、重构步骤（8步，每步可独立验证）

### Step 1: 创建 Foundation 层（DataBus + ConfigStore）

**目标**: 建立基础设施，不修改任何现有代码

**新增文件**:
```
core/foundation/__init__.py
core/foundation/data_bus.py          # 事件总线
core/foundation/config_store.py     # 配置中心
core/foundation/config_models.py    # 统一配置模型
core/foundation/plugin_registry.py  # 插件注册表
```

**验证**: 单元测试 DataBus 的发布/订阅、ConfigStore 的读写

**工作量**: 1.5天

---

### Step 2: 创建统一解析器 ModbusValueParser

**目标**: 消除3处重复解析，统一数据格式

**新增文件**:
```
core/communication/modbus_value_parser.py
```

**验证**: 用现有 quick_verify.py 的20个测试用例验证新解析器

**工作量**: 1天

---

### Step 3: 创建 Service 层

**目标**: 将业务逻辑从 MainWindow 和 DeviceManager 中提取出来

**新增文件**:
```
core/services/mcgs_service.py       # MCGS业务服务（封装Reader+Storage+Detector）
core/services/history_service.py    # 历史数据服务
core/services/anomaly_service.py    # 异常检测服务
```

**关键**: MCGSService 封装 MCGSModbusReader + HistoryStorage + AnomalyDetector，对外只暴露 `read_and_process()` 方法

**验证**: 单元测试 MCGSService 的完整流程

**工作量**: 2天

---

### Step 4: 创建 Controller 层

**目标**: 将异步调度和线程管理从 MainWindow 中提取出来

**新增文件**:
```
ui/controllers/mcgs_controller.py   # MCGS控制器（异步轮询+Signal中转）
ui/controllers/device_controller.py # 通用设备控制器
```

**关键改动**:
- MCGSController 持有 QThreadPool，将 `read_and_process()` 放入工作线程
- 通过 DataBus 发射数据更新信号
- MainWindow 只连接 Controller 的信号

**验证**: 运行程序，确认MCGS轮询不再阻塞UI

**工作量**: 2天

---

### Step 5: 修复通信层高危问题

**目标**: 修复审计发现的9个高危问题

**修改文件**:
```
core/communication/tcp_driver.py     # V01: disconnect()死锁修复
core/protocols/modbus_protocol.py    # V02: transaction_id加锁
core/utils/mcgs_modbus_reader.py    # V04: pymodbus连接关闭, V05: __del__保护
                                      # V11: 断线检测, V14: 偏移越界, V15: NaN过滤
ui/main_window.py                    # V08: bare except修复
```

**验证**: 运行程序，手动测试断线/重连/超时场景

**工作量**: 2天

---

### Step 6: 创建设备插件体系

**目标**: 将 MCGS 设备逻辑从硬编码改为插件注册

**新增文件**:
```
core/plugins/__init__.py             # 插件注册入口
core/plugins/mcgs_plugin.py          # MCGS设备插件
```

**修改文件**:
```
core/device/device_factory.py        # 使用 PluginRegistry 创建设备
```

**关键**: DeviceFactory.create() 改为:
```python
def create(config: DeviceConfig) -> DeviceConnection:
    plugin = PluginRegistry.get(config.device_type)
    if plugin:
        return plugin.create_connection(config)
    raise ValueError(f"未注册的设备类型: {config.device_type}")
```

**验证**: 运行程序，确认MCGS设备通过插件创建

**工作量**: 1.5天

---

### Step 7: 重构 MainWindow

**目标**: MainWindow 只保留UI逻辑，所有业务操作委托给 Controller

**修改文件**:
```
ui/main_window.py                    # 大幅精简，删除直接调用通信层的代码
```

**关键改动**:
```python
# 改造前 (约3000行):
class MainWindow:
    self._mcgsm_reader = MCGSModbusReader(...)   # 直接持有通信层
    self._mcgsm_storage = HistoryStorage(...)     # 直接持有数据层
    self._mcgsm_detector = AnomalyDetector(...)   # 直接持有算法层

    def _on_mcgsm_poll_timeout(self):
        result = self._mcgsm_reader.read_device(...)  # 阻塞！
        self._mcgsm_storage.save_read_result(...)      # 阻塞！
        self._mcgsm_detector.check_batch(...)          # 阻塞！

# 改造后 (约2000行):
class MainWindow:
    self._mcgs_controller = MCGSController(self)      # 只持有Controller

    def __init__(self):
        DataBus.instance().device_data_updated.connect(self._on_data_updated)

    def _on_mcgsm_quick_connect(self):
        self._mcgs_controller.connect_device(device_id)  # 异步！不阻塞！

    @Slot(str, dict)
    def _on_data_updated(self, device_id, data):
        self._update_monitor_panel(device_id, data)      # 纯UI更新
```

**验证**: 运行程序，确认所有功能正常且UI不卡顿

**工作量**: 3天

---

### Step 8: 清理遗留代码

**目标**: 删除被替代的旧代码，消除冗余

**删除/替换**:
```
删除: MCGSModbusReader._parse_float()     → 被 ModbusValueParser.parse() 替代
删除: MCGSModbusReader._parse_int32()     → 被 ModbusValueParser.parse() 替代
删除: MCGSModbusReader._parse_int16()     → 被 ModbusValueParser.parse() 替代
删除: MCGSModbusReader.type_map           → 被 RegisterDataType.get_register_count() 替代
删除: DeviceConnection._decode_point_value() → 被 ModbusValueParser.parse() 替代
删除: ModbusProtocol._parse_register_value() → 被 ModbusValueParser.parse() 替代
删除: main_window.py 中的 bare except      → 被 MCGSService 结构化异常处理替代
删除: main_window.py 中的 processEvents()  → 被 Controller 异步化替代
修复: DeviceConnection._format_batch_data() if False 死代码
```

**验证**: 全量回归测试

**工作量**: 1天

---

## 八、重构后目录结构

```
equipment-management/
│
├── core/
│   ├── foundation/                    ← 新增：基础设施层
│   │   ├── __init__.py
│   │   ├── data_bus.py               # 事件总线（全局单例）
│   │   ├── config_store.py           # 配置中心（统一配置入口）
│   │   ├── config_models.py          # 统一配置数据模型
│   │   └── plugin_registry.py        # 插件注册表
│   │
│   ├── communication/                 # 通信层（重构）
│   │   ├── base_driver.py
│   │   ├── tcp_driver.py             # 修复：死锁/重连
│   │   ├── serial_driver.py
│   │   ├── modbus_value_parser.py    # 新增：统一解析器
│   │   └── comm_quality_monitor.py   # 新增：通信质量监控
│   │
│   ├── protocols/                     # 协议层（保持）
│   │   ├── base_protocol.py
│   │   ├── modbus_protocol.py        # 修复：transaction_id加锁
│   │   └── byte_order_config.py
│   │
│   ├── device/                        # 设备层（保持，接入插件）
│   │   ├── device_manager_facade.py
│   │   ├── device_connection.py      # 修复：死代码/重连信号
│   │   ├── device_factory.py         # 修改：使用PluginRegistry
│   │   └── ...
│   │
│   ├── plugins/                       ← 新增：设备插件目录
│   │   ├── __init__.py               # 自动注册内置插件
│   │   ├── mcgs_plugin.py            # MCGS触摸屏插件
│   │   ├── plc_plugin.py             # PLC插件（未来）
│   │   └── meter_plugin.py           # 仪表插件（未来）
│   │
│   ├── services/                      # 服务层（重构）
│   │   ├── mcgs_service.py           ← 新增：MCGS业务服务
│   │   ├── history_service.py        ← 新增：历史数据服务
│   │   ├── anomaly_service.py        ← 新增：异常检测服务
│   │   └── ...
│   │
│   └── ...
│
├── ui/
│   ├── controllers/                   ← 新增：控制器层
│   │   ├── mcgs_controller.py        # MCGS异步控制器
│   │   └── device_controller.py      # 通用设备控制器
│   │
│   ├── main_window.py                # 精简：只保留UI逻辑
│   └── ...
│
└── config/
    └── devices.json                   # 统一配置文件（所有设备类型）
```

---

## 九、重构后数据流

```
用户点击 [🔌 MCGS连接]
  │
  ▼
MainWindow._on_mcgsm_quick_connect()          # UI层：只发指令
  │
  ▼
MCGSController.connect_device(device_id)      # Controller层：异步调度
  │
  ├── QThreadPool.start(ConnectTask)           # 工作线程
  │     │
  │     ▼
  │   MCGSService.connect(device_id)           # Service层：业务逻辑
  │     │
  │     ▼
  │   PluginRegistry.get("mcgs").create_connection(config)  # 插件层
  │     │
  │     ▼
  │   DeviceConnection.connect()               # Device层：连接管理
  │     │
  │     ▼
  │   TcpDriver.connect() → ModbusProtocol    # Communication层
  │
  ├── 连接成功 → DataBus.device_connected.emit(device_id)
  │                    │
  │                    ├── MainWindow._on_device_connected()  # UI更新状态
  │                    └── HistoryService._on_device_connected()  # 准备存储
  │
  └── 连接失败 → DataBus.comm_error.emit(device_id, error)
                       │
                       └── MainWindow._on_comm_error()  # UI弹出配置引导


QTimer轮询触发
  │
  ▼
MCGSController._start_poll_cycle()            # Controller层：异步调度
  │
  ├── QThreadPool.start(PollTask)              # 工作线程
  │     │
  │     ▼
  │   MCGSService.read_and_process(device_id)  # Service层：读取+存储+检测
  │     │
  │     ├── MCGSModbusReader.read_device()     # 通信层：读取寄存器
  │     │     └── ModbusValueParser.parse_batch()  # 统一解析
  │     │
  │     ├── HistoryStorage.save_read_result()  # 数据层：SQLite存储
  │     │
  │     └── AnomalyDetector.check_batch()      # 算法层：异常检测
  │
  └── DataBus.device_data_updated.emit(device_id, structured_data)
                       │
                       ├── MainWindow._on_data_updated()       # UI更新面板
                       ├── HistoryService._on_data_updated()   # 累积统计
                       └── AlarmController._on_data_updated()  # 报警评估
```

---

## 十、重构工作量估算

| 步骤 | 内容 | 工作量 | 风险 | 可独立验证 |
|------|------|--------|------|-----------|
| Step 1 | Foundation层(DataBus+ConfigStore) | 1.5天 | 低 | ✅ 单元测试 |
| Step 2 | 统一解析器 ModbusValueParser | 1天 | 低 | ✅ 20个测试用例 |
| Step 3 | Service层(MCGS/History/Anomaly) | 2天 | 中 | ✅ 集成测试 |
| Step 4 | Controller层(异步调度) | 2天 | 中 | ✅ UI不卡顿 |
| Step 5 | 修复通信层9个高危问题 | 2天 | 高 | ✅ 断线/重连测试 |
| Step 6 | 设备插件体系 | 1.5天 | 低 | ✅ 插件注册测试 |
| Step 7 | 重构MainWindow | 3天 | 高 | ✅ 全功能回归 |
| Step 8 | 清理遗留代码 | 1天 | 低 | ✅ 全量回归 |
| **合计** | | **14天** | | |

---

## 十一、重构风险控制

| 风险 | 应对策略 |
|------|---------|
| Step 5 修改通信层可能影响现有功能 | 先写测试用例覆盖现有行为，再修改代码 |
| Step 7 重构MainWindow改动量大 | 分3个子步骤：先加Controller并行运行→逐步迁移→最后删除旧代码 |
| 新旧代码并存期 | 使用特性开关(`feature_flag`)控制走新/旧通路 |
| 回归测试不足 | 每步完成后运行全量测试，确保无功能退化 |

---

## 十二、重构后收益

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| UI冻结时间 | 15-3000ms/次 | 0ms | ✅ 100%消除 |
| 重复代码(字节序解析) | 3处 | 1处 | ✅ 67%减少 |
| 重复代码(类型映射) | 3处 | 1处 | ✅ 67%减少 |
| 新增设备类型需修改文件数 | 6个 | 1个(插件) | ✅ 83%减少 |
| UI层直接调用通信层 | 5处 | 0处 | ✅ 100%消除 |
| 高危漏洞 | 9个 | 0个 | ✅ 100%修复 |
| 数据格式 | 2种(字符串/结构化) | 1种(结构化) | ✅ 统一 |
| 断线重连 | 无 | 自动 | ✅ 新增 |
| 通信质量监控 | 无 | 有 | ✅ 新增 |
| 设备扩展方式 | 修改核心代码 | 注册插件 | ✅ 开闭原则 |
