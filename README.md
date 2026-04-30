# 工业设备管理系统 (Equipment Management System) v2.0.0

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green.svg)](https://pypi.org/project/PySide6/)
[![Version](https://img.shields.io/badge/Version-2.0.0-orange.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCGS](https://img.shields.io/badge/MCGS-Modbus_TCP-integrationred.svg)](MCGS.md)

基于 **PySide6** 和 **Modbus 协议** 的工业设备上位机监控软件，采用 **四层解耦 + 服务化架构**，支持 **MCGS 触摸屏集成**、多设备并发管理、实时数据可视化和智能故障恢复。

> **v2.0.0 正式发布** — 完整支持 MCGS 触摸屏 Modbus TCP 通信，数据实时读取与可视化已验证通过 ✅

---

## 核心特性

### 🔌 MCGS 触摸屏集成（v2.0 核心）

| 特性 | 说明 |
|------|------|
| **Modbus TCP 通信** | 上位机作为 Client，MCGS 触摸屏作为 Server（Slave），端口 502 |
| **批量寄存器读取** | 单次请求读取全部变量，高性能低延迟 |
| **4种字节序支持** | ABCD / BADC / CDAB / DCBA，适配各品牌 PLC |
| **7种数据类型** | uint16 / int16 / uint32 / int32 / float32 等 |
| **配置驱动** | JSON 配置文件定义设备、地址、类型、缩放因子 |
| **自动轮询** | 可配置轮询间隔（默认 1s），QTimer 驱动 |
| **DataBus 数据总线** | 发布/订阅模式，UI 与通信层完全解耦 |
| **实时监控面板** | 数据卡片 + 寄存器表格 + 趋势图 + 日志 |

### 协议支持

- **Modbus TCP** — 以太网通信，FC08 诊断心跳 + TCP KeepAlive 双重保活
- **Modbus RTU** — 串口通信（RS485/RS232），TOCTOU 安全读取，CRC-16 校验
- **Modbus ASCII** — ASCII 编码串口通信，LRC 校验
- **4 种字节序** — ABCD（大端）/ BADC / CDAB（小端）/ DCBA
- **7 种数据类型** — Coil / DiscreteInput / HoldingInt16 / Int32 / Float32 / InputInt16 / Float32

### 设备管理

- 多设备并发管理（支持 100+ 设备、20000+ 寄存器）
- 设备增删改查 + 搜索 + 批量操作
- JSON 配置持久化，端口信息完整保存
- 可配置自动重连（全局/设备级控制）
- 设备分组管理与分组轮询
- 设备模板管理（快速创建/克隆设备）
- 配置导入/导出（含版本兼容性检查）
- 协议插件注册表（运行时扩展新协议）

### 智能故障恢复

- **FaultRecoveryService** — 多模式故障恢复（指数退避 / 固定间隔 / 即时重试）
- 随机抖动防惊群（Jitter）
- 故障检测与诊断
- 恢复状态查询与统计分析
- 信号驱动的恢复事件通知

### 通信驱动

- **TCPDriver** — FC08 Modbus 诊断心跳（10s 间隔），TCP KeepAlive（10s/5s/3次），线程安全
- **SerialDriver** — TOCTOU 安全读取（v2.0），混合/阻塞/非阻塞三种模式，自适应波特率超时
- **BaseDriver** — QMutex 缓冲区保护，统一信号接口
- shiboken6 全面对象生命周期保护

### 数据可视化

- **DataCard** — 数据卡片，实时值 + 状态 + 趋势
- **Gauge** — Canvas 仪表盘，弧形进度条
- **TrendChart** — Canvas 趋势图
- **RealTimeChart** — pyqtgraph 高性能实时曲线图（支持缩放/平移/多系列）
- **DynamicMonitorPanel** — 动态监控面板，支持卡片布局自由编排
- **HistoryChartWidget** — 历史数据趋势图

### UI 组件库

- **按钮系统**：PrimaryButton / SecondaryButton / SuccessButton / DangerButton / GhostButton
- **输入控件**：LineEdit / ComboBox / InputWithLabel / Checkbox
- **卡片组件**：DataCard / InfoCard / ActionCard
- **表格组件**：DeviceTree / DataTable / DeviceTable
- **状态组件**：StatusLabel / StatusBadge / AnimatedStatusBadge
- **可视化组件**：ModernGauge / RealtimeChart
- **主题管理**：ThemeManager（Fluent Design 风格浅色主题）+ DesignTokens 设计令牌系统
- **动画调度**：AnimationScheduler（全局单定时器，CPU 占用降低 80%+）

### 报警系统

- 四级报警：信息(INFO) / 警告(WARNING) / 错误(ERROR) / 严重(CRITICAL)
- 四类阈值：高高(HH) / 高(H) / 低(L) / 低低(LL)
- 死区控制 + 冷却机制，防止报警风暴
- 8 种错误智能分类
- 通知渠道：弹窗 / 声音 / 自定义
- 报警确认 + 历史记录 + 统计分析

---

## 系统架构

```
┌──────────────────────────────────────────────────────┐
│                  UI 层 (PySide6 Widgets)               │
│    MainWindow + Controllers + Panels + Dialogs        │
│         ┌─ MCGSController (MCGS触摸屏通信)             │
│         └─ MonitorPageController (监控页)              │
├──────────────────────────────────────────────────────┤
│              设备管理层 (DeviceManagerFacade v4.0)      │
│   Registry + Scheduler + Recovery + Configuration     │
│   GroupManager + Lifecycle + DataPersistence          │
├──────────────────┬───────────────────────────────────┤
│  MCGS 通信层     │      通用通信驱动层                 │
│  MCGSReader      │     TCP / Serial Driver            │
│  MCGSService     │     BaseDriver                     │
│  MCGSController  │                                    │
├──────────────────┴───────────────────────────────────┤
│                协议层 (Modbus Protocol)                │
│       TCP + RTU + ASCII + CRC-16 / LRC               │
│           ByteOrderConfig + ProtocolRegistry          │
├──────────────────────────────────────────────────────┤
│              数据总线 (DataBus v2.0)                   │
│     Publish/Subscribe — 单向数据流 — 解耦核心          │
├──────────────────────────────────────────────────────┤
│            数据持久化层 (SQLite WAL)                   │
│      DatabaseManager + Repository + Services         │
│              7 ORM Models + 5 Repositories            │
└──────────────────────────────────────────────────────┘
```

### MCGS 数据流架构

```
┌──────────┐    RS485     ┌──────────┐   Modbus TCP   ┌──────────┐
│  传感器   │ ──────────→ │  MCGS    │ ─────────────→ │  上位机   │
│(温度/湿度)│   RTU从站   │  触摸屏   │   Server:502   │  Client  │
└──────────┘             └──────────┘                └────┬─────┘
                                                            │
                        ┌───────────────────────────────────┘
                        ↓
              ┌─────────────────────┐
              │  MCGSModbusReader   │ ← 批量读取 Holding Registers
              │  (pymodbus 3.x)     │
              └─────────┬───────────┘
                        ↓
              ┌─────────────────────┐
              │   MCGSService       │ ← 数据解析 + 类型转换
              └─────────┬───────────┘
                        ↓
              ┌─────────────────────┐
              │    DataBus v2.0     │ ← 发布/订阅
              └─────────┬───────────┘
                        ↓
              ┌─────────────────────┐
              │  UI Monitor Panel   │ ← 卡片/表格/图表/日志
              └─────────────────────┘
```

---

## 项目结构

```
equipment-management/
├── core/                              # 核心源码
│   ├── foundation/                    # 基础设施层
│   │   └── data_bus.py               # DataBus v2.0 (发布/订阅)
│   ├── engine/                       # 引擎层
│   │   └── gateway_engine.py         # 网关引擎
│   ├── protocols/                    # 协议层
│   │   ├── modbus_protocol.py        # Modbus TCP/RTU/ASCII
│   │   └── byte_order_config.py      # 字节序配置
│   ├── communication/                # 通信驱动层
│   │   ├── tcp_driver.py             # TCP 驱动
│   │   └── serial_driver.py          # 串口驱动
│   ├── device/                       # 设备管理层 (v4.0)
│   │   ├── device_manager_facade.py  # 统一入口
│   │   ├── device_registry.py        # 注册中心
│   │   ├── polling_scheduler.py      # 轮询调度
│   │   └── fault_recovery_service.py # 故障恢复
│   ├── services/                     # 业务服务层
│   │   ├── mcgs_service.py           # MCGS 服务
│   │   ├── audit_log_service.py      # 审计日志
│   │   └── report_service.py         # 报表服务
│   ├── utils/                        # 工具模块
│   │   ├── mcgs_modbus_reader.py     # MCGS Modbus 读取器 ⭐
│   │   ├── alarm_manager.py          # 报警管理
│   │   └── data_exporter.py          # 数据导出
│   ├── data/                         # 数据持久化层
│   │   ├── models.py                 # ORM 模型 (7表)
│   │   └── repository/               # Repository 模式
│   └── version.py                    # 版本号 v2.0.0
├── ui/                               # UI 层
│   ├── main_window.py                # 主窗口
│   ├── controllers/
│   │   ├── mcgs_controller.py        # MCGS 控制器 ⭐
│   │   └── monitor_page_controller.py # 监控页控制器
│   ├── dialogs/
│   │   └── mcgs_config_dialog.py     # MCGS 配置对话框
│   ├── widgets/                      # 自定义组件
│   │   ├── visual.py                 # DataCard/Gauge/TrendChart
│   │   └── history_chart_widget.py   # 历史趋势图
│   └── design_tokens.py              # 设计令牌系统
├── config/
│   └── devices.json                  # MCGS 设备配置 ⭐
├── main.py                           # 程序入口
├── MCGS.md                           # MCGS 集成文档 ⭐
└── README.md                         # 本文件
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11
- MCGS 触摸屏（或 McgsPro 模拟器）— 可选

### 安装与运行

```bash
# 克隆项目
git clone https://github.com/xiaowulai-s/Equipment-Management.git
cd Equipment-Management

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### MCGS 快速连接

1. 编辑 `config/devices.json` 配置 MCGS 设备 IP 和端口
2. 启动程序 → 点击 **「MCGS连接」** 按钮
3. 自动进入监控页面，显示实时数据卡片和寄存器表格

```json
{
  "devices": [{
    "id": "Device0",
    "name": "MCGS触摸屏",
    "ip": "192.168.31.239",
    "port": 502,
    "unit_id": 1,
    "points": [
      {"name": "Data0", "addr": 40001, "type": "uint16"},
      {"name": "Data1", "addr": 40002, "type": "uint16"},
      {"name": "Data2", "addr": 40003, "type": "uint16"},
      {"name": "Data3", "addr": 40004, "type": "uint16"}
    ]
  }]
}
```

### 核心依赖

| 包 | 版本 | 用途 |
|---|---|---|
| [PySide6](https://pypi.org/project/PySide6/) | 6.6+ | Qt for Python UI 框架 |
| [pymodbus](https://pypi.org/project/pymodbus/) | 3.x | Modbus 协议栈 |
| [SQLAlchemy](https://www.pypi.org/project/SQLAlchemy/) | 2.0+ | 数据库 ORM |
| [pyserial](https://pypi.org/project/pyserial/) | 3.5+ | 串口通信 |
| [pyqtgraph](https://pypi.org/project/pyqtgraph/) | 0.13+ | 高性能数据可视化 |
| [openpyxl](https://pypi.org/project/openpyxl/) | 3.1+ | Excel 导出 |

---

## 文档

| 文档 | 说明 |
|---|---|
| [MCGS 集成指南](MCGS.md) | MCGS 触摸屏接入规范、数据流设计、AI 开发流程 |
| [更新日志](CHANGELOG.md) | 版本变更记录 |
| [项目架构文档](项目架构与功能文档.md) | 架构设计、模块说明、数据库表结构 |
| [安装部署指南](docs/安装部署指南.md) | 打包部署和故障排除 |
| [新架构说明](docs/architecture/新架构说明_v2.md) | v2.0 架构设计详解 |

---

## 测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_step2_2.py -v    # Modbus TCP 协议测试
pytest tests/test_step4_1.py -v    # 设备模型测试

# 性能测试
python tests/test_ui_performance.py
```

---

## 数据库

### ORM 模型（7 表）

| 表 | 模型类 | 说明 |
|---|---|---|
| devices | DeviceModel | 设备信息（名称/类型/协议/连接状态） |
| register_maps | RegisterMapModel | 寄存器映射（地址/类型/缩放/单位） |
| historical_data | HistoricalDataModel | 历史数据（值/原始值/质量码/时间戳） |
| alarms | AlarmModel | 报警记录（阈值/确认/时间戳） |
| alarm_rules | AlarmRuleModel | 报警规则（启用/阈值/描述） |
| system_logs | SystemLogModel | 系统日志（级别/模块/异常） |
| device_status_history | DeviceStatusHistoryModel | 设备状态历史 |

### SQLite 配置

- **WAL 模式** — 读写并发不阻塞
- **外键约束** — CASCADE 级联删除
- **复合索引** — (device_id, timestamp) 高频查询优化

---

## 版本历史

### v2.0.0 (2026-04-29) — 正式发布

#### MCGS 触摸屏集成（核心亮点）

- **MCGSModbusReader** — 基于 pymodbus 3.x 的 Modbus TCP 客户端
  - 批量读取 Holding Registers（FC03），单次请求获取全部变量
  - 支持 4 种字节序（ABCD/BADC/CDAB/DCBA）
  - 支持 7 种数据类型（uint16/int16/uint32/int32/float32 等）
  - 连接管理 + 超时处理 + 自动重连
- **MCGSService** — 数据解析服务层
  - 原始寄存器 → 结构化数据转换
  - DataBus 发布/订阅推送
  - 数据质量标记
- **MCGSController** — Qt 控制器（Signal/Slot）
  - QTimer 定时轮询（可配置间隔）
  - QThreadPool 异步读取任务
  - 设备连接/断开/轮询状态管理
- **UI 监控面板**
  - DataCard 数据卡片（实时数值 + 地址标签）
  - 寄存器表格（地址/功能码/名称/值/单位）
  - 系统日志面板（时间戳/级别/消息）
  - 自动初始化监控面板（数据到达时自动创建卡片）
- **MCGS 配置对话框** — IP/端口/点位/类型可视化配置
- **devices.json 配置驱动** — JSON 定义设备参数，无需修改代码

#### 架构升级（服务化重构）

- 设备管理层 v4.0 模块化重构（7 个独立服务）
- `DeviceManagerFacade` 外观类统一入口
- 设备模型 v3.2 配置驱动重构（dataclass 零副作用）
- DataBus v2.0 发布/订阅模式
- 接口定义层（依赖注入支持）

#### 通信增强

- TCP 驱动 FC08 心跳 + KeepAlive 双保活
- 串口驱动 TOCTOU 安全修复（v2.0）
- 字节序配置模块 + 协议插件注册表

#### UI 增强

- DesignTokens 设计令牌系统
- 全局动画调度器（CPU 降低 80%+）
- 动态监控面板 + 历史趋势图
- 操作撤销 + 权限管理（三级 + SHA256）

### v1.6.0 ~ v1.0.0

详见 [CHANGELOG.md](CHANGELOG.md)

---

## 设计规范

| 项目 | 值 |
|---|---|
| 主色 | `#2196F3` (科技蓝) |
| 辅助色 | `#00BCD4` (青色) |
| 成功 | `#4CAF50` |
| 警告 | `#FFC107` |
| 错误 | `#F44336` |
| 设计令牌 | DesignTokens 系统化管控颜色/字体/间距 |

---

## 开发

### 构建

```bash
pyinstaller build.spec
```

### 代码规范

```bash
flake8 core/ ui/ --config .flake8
black core/ ui/
mypy core/ ui/
```

---

## License

MIT License

---

**版本**: v2.0.0 | **更新**: 2026-04-29 | **状态**: 正式发布 ✅
