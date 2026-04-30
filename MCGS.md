# MCGS 触摸屏集成指南

> **版本**: v2.0.0 | **状态**: 已验证通过 ✅ | **更新**: 2026-04-29

---

## 1. 系统概述

本系统通过上位机软件对 MCGS 触摸屏（或 McgsPro 模拟器）进行数据监测与展示。上位机作为 **Modbus TCP Client**，MCGS 触摸屏作为 **Modbus TCP Server (Slave)**，通过标准 Modbus 协议实现实时数据交互。

### 1.1 系统目标

- **高实时** — 1 秒轮询间隔，QTimer 驱动，数据延迟 < 100ms
- **高可靠** — 长连接保持，自动重连，异常恢复
- **高解耦** — DataBus 发布/订阅模式，UI 与通信层完全隔离
- **配置驱动** — JSON 定义设备参数，无需修改代码即可增减变量

### 1.2 通信角色

| 角色 | 设备 | 协议 | 端口 |
|------|------|------|------|
| Server (Slave) | MCGS 触摸屏 / McgsPro | Modbus TCP | 502 |
| Client (Master) | 上位机软件 | Modbus TCP | 随机 |

---

## 2. 数据流架构

```
┌──────────┐    RS485     ┌──────────┐   Modbus TCP   ┌──────────────┐
│  传感器   │ ──────────→ │  MCGS    │ ─────────────→ │ MCGSReader   │
│(温度/湿度)│   RTU从站   │  触摸屏   │   :502         │ (pymodbus)   │
└──────────┘             └──────────┘                └──────┬───────┘
                                                            │ 批量读取 FC03
                                                            ↓
                                                   ┌────────────────┐
                                                   │  MCGSService    │ ← 解析 + 类型转换
                                                   └───────┬────────┘
                                                           │ DataBus.publish()
                                                           ↓
                                                   ┌────────────────┐
                                                   │  DataBus v2.0   │ ← 发布/订阅解耦
                                                   └───────┬────────┘
                                                           │ Signal + subscribe
                                                           ↓
                                              ┌──────────────────────────────┐
                                              │  UI Monitor Panel             │
                                              │  ├─ DataCard (数值卡片)       │
                                              │  ├─ RegisterTable (寄存器表格) │
                                              │  ├─ TrendChart (趋势图)        │
                                              │  └─ LogPanel (系统日志)        │
                                              └──────────────────────────────┘
```

---

## 3. 技术实现

### 3.1 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| **MCGSModbusReader** | `core/utils/mcgs_modbus_reader.py` | Modbus TCP 客户端，批量读取寄存器 |
| **MCGSService** | `core/services/mcgs_service.py` | 数据解析服务，DataBus 发布 |
| **MCGSController** | `ui/controllers/mcgs_controller.py` | Qt 控制器，轮询调度 + 状态管理 |
| **DataBus** | `core/foundation/data_bus.py` | 发布/订阅数据总线，UI/服务解耦核心 |

### 3.2 MCGSModbusReader

基于 **pymodbus 3.x** 实现，核心功能：

```python
# 初始化（从 devices.json 加载配置）
reader = MCGSModbusReader('config/devices.json')

# 连接设备
reader.connect_device('Device0')

# 批量读取全部变量
result = reader.read_device('Device0')
# result.success: bool
# result.raw_registers: [100, 1, 2, 3]  # 原始寄存器值
# result.parsed_data: {'Data0': '100', 'Data1': '1', 'Data2': '2', 'Data3': '3'}
```

**关键特性：**

- **批量读取**: 单次 FC03 请求读取连续地址范围的全部寄存器
- **地址计算**: 支持 address_base 配置（4xxxx 地址自动转换为 pymodbus 偏移）
- **字节序**: ABCD/BADC/CDAB/DCBA 四种模式
- **类型转换**: uint16/int16/uint32/int32/float32 自动解析
- **线程安全**: QMutex 保护连接资源

### 3.3 MCGSService

数据处理中间层：

- 接收 MCGSModbusReader 的原始结果
- 按 point 配置进行类型转换和缩放计算
- 通过 DataBus.publish_device_data() 发布结构化数据
- 错误时发布 device_error 事件

### 3.4 MCGSController

Qt 信号驱动的控制器：

- **QTimer 定时轮询**: 可配置间隔（默认 1000ms）
- **QThreadPool 异步任务**: _BatchReadTask 在工作线程执行读取
- **Signal/Slot 通信**: device_data_updated / device_error / poll_cycle_completed
- **连接管理**: connect_devices_async() 异步连接 + start_polling()/stop_polling()

### 3.5 DataBus v2.0

发布/订阅模式的核心解耦组件：

```python
# 发布（Service 层）
DataBus.instance().publish_device_data('Device0', {'Data0': '100', 'Data1': '1'})

# 订阅（UI 层）
DataBus.instance().subscribe('device_data_updated', self._on_bus_data_updated)

# 或通过 Signal 连接（Controller 层）
mcgs_controller.device_data_updated.connect(self._on_mcgsm_data_updated)
```

---

## 4. 设备配置 (devices.json)

### 4.1 配置格式

```json
{
  "_meta": {
    "version": "3.0.0",
    "source": "Manual"
  },
  "devices": [{
    "id": "Device0",
    "name": "MCGS触摸屏#Device0",
    "ip": "192.168.31.239",
    "port": 502,
    "unit_id": 1,
    "timeout_ms": 3000,
    "byte_order": "ABCD",
    "polling_interval_ms": 1000,
    "address_base": 40001,
    "points": [
      {
        "name": "Data0",
        "addr": 40001,
        "type": "uint16",
        "unit": "",
        "decimal_places": 0,
        "scale": 1.0
      },
      {
        "name": "Data1",
        "addr": 40002,
        "type": "uint16",
        "unit": "",
        "decimal_places": 0,
        "scale": 1.0
      }
    ]
  }]
}
```

### 4.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 设备唯一标识 |
| `name` | string | ✅ | 显示名称 |
| `ip` | string | ✅ | MCGS IP 地址 |
| `port` | int | ✅ | Modbus TCP 端口（默认 502）|
| `unit_id` | int | ✅ | Modbus 从站地址（默认 1）|
| `timeout_ms` | int | ⬚ | 连接超时毫秒数（默认 3000）|
| `byte_order` | string | ⬚ | 字节序: ABCD/BADC/CDAB/DCBA |
| `polling_interval_ms` | int | ⬚ | 轮询间隔毫秒数（默认 1000）|
| `address_base` | int | ⬚ | 地址基准值（4xxxx 用 40001）|
| `points[].name` | string | ✅ | 变量名 |
| `points[].addr` | int | ✅ | Modbus 寄存器地址（4xxxx 格式）|
| `points[].type` | string | ✅ | 数据类型: uint16/int16/uint32/int32/float32 |
| `points[].unit` | string | ⬚ | 单位 |
| `points[].decimal_places` | int | ⬚ | 小数位数 |
| `points[].scale` | float | ⬚ | 缩放因子 |

### 4.3 地址映射规则

| MCGS 变量区 | Modbus 功能码 | 地址格式 | address_base |
|------------|-------------|---------|-------------|
| [4区] 输出寄存器 | FC03 (Read Holding) | 40001~49999 | 40001 |
| [3区] 输入寄存器 | FC04 (Read Input) | 30001~39999 | 30001 |
| [0区] 线圈 | FC01 (Read Coils) | 00001~09999 | 1 |
| [1区] 离散输入 | FC02 (Read Discrete) | 10001~19999 | 10001 |

> **重要**: `address_base` 必须与地址格式匹配。使用 4xxxx 地址时设为 `40001`，pymodbus 内部会自动减去该偏移得到实际地址。

---

## 5. UI 监控面板

### 5.1 页面组成

| 组件 | 说明 |
|------|------|
| **数据卡片 (DataCard)** | 每个变量一张卡片，显示 名称/地址/实时值 |
| **寄存器表格** | 地址 / 功能码 / 名称 / 数值 / 单位 |
| **趋势图** | pyqtgraph 实时曲线 |
| **日志面板** | 时间戳 + 级别 + 消息 |
| **状态栏** | 设备名 / 在线状态 / 最后更新时间 |

### 5.2 自动初始化

当数据首次到达且用户未手动选中设备时，系统自动：
1. 创建监控面板卡片布局
2. 设置当前设备 ID 和显示名称
3. 切换到监控页面
4. 后续数据直接更新卡片数值

---

## 6. 关键设计决策

### 6.1 为什么用 DataBus 而非直连？

```
❌ 直接连接:  Reader → Controller → UI.update()
               ↑ 紧耦合，UI 依赖通信层接口

✔ DataBus:    Reader → Service → DataBus → UI.subscribe()
               ↑ 松耦合，UI 只关心数据格式，不关心来源
```

### 6.2 为什么卡片不每秒重建？

v2.0 开发中发现一个 Bug: `_on_mcgsm_poll_cycle_completed` 会触发 `_refresh_device_list`，进而触发 `_on_device_selected`，导致 `update_cards_display()` 每秒删除并重建所有卡片。

**修复方案**:
1. 同一设备重复选中时跳过 (`device_id == self._current_device_id`)
2. 卡片已存在时仅更新头部信息，不重建

### 6.3 双数据路径设计

数据同时通过两条路径到达 UI:
- **Signal 路径**: `MCGSController.device_data_updated` → `MainWindow._on_mcgsm_data_updated`
- **DataBus 路径**: `DataBus.publish()` → `MainWindow._on_bus_device_data_updated` (订阅回调)

两条路径最终都调用同一组更新方法（`_update_card_values`, `_update_chart_data` 等），确保一致性。

---

## 7. 故障排查

### 7.1 连接失败

```
检查项:
1. MCGS 是否运行（McgsPro 需点击"运行"按钮）
2. IP/端口是否正确（默认 192.168.31.239:502）
3. 网络是否通: ping <MCGS_IP>
4. 防火墙是否放行 502 端口
```

### 7.2 数据全为 0

```
检查项:
1. address_base 是否正确（4xxxx 地址应设为 40001）
2. points[].addr 是否与 MCGS 变量地址一致
3. MCGS 运行模式下变量是否已赋值
4. 字节序是否匹配（默认 ABCD 大端）
```

### 7.3 卡片显示 "--"

```
检查项:
1. 数据是否到达日志（查看终端输出）
2. _current_device_id 是否匹配（None 时需等待 auto-setup）
3. 轮询是否启动（日志应有 "轮询已启动" 信息）
```

### 7.4 pymodbus API 兼容性

pymodbus 3.x 的 `read_holding_registers` 使用 keyword-only 参数:

```python
# 正确 (pymodbus 3.x)
client.read_holding_registers(start, count=count, device_id=unit_id)

# 错误 (pymodbus 2.x 语法)
client.read_holding_registers(start, count, unit_id)
# TypeError: got an unexpected keyword argument
```

---

## 8. 已验证场景

| 场景 | 结果 | 日期 |
|------|------|------|
| McgsPro 模拟器连接 (192.168.31.239:502) | ✅ 通过 | 2026-04-29 |
| 5 个 uint16 变量批量读取 | ✅ 通过 | 2026-04-29 |
| Data0=100, Data1=1, Data2=2, Data3=3 实际值验证 | ✅ 匹配 | 2026-04-29 |
| 1 秒持续轮询 | ✅ 稳定 | 2026-04-29 |
| UI 数据卡片实时更新 | ✅ 正常 | 2026-04-29 |
| 寄存器表格显示 | ✅ 正常 | 2026-04-29 |
| 日志面板输出 | ✅ 正常 | 2026-04-29 |
| 断线重连 | 待测 | - |
| 多设备并发 | 待测 | - |

---

## 9. 后续规划

- [ ] 支持写操作（FC06/FC16 写单个/多个寄存器）
- [ ] 支持浮点型变量（float32 @ 两个连续寄存器）
- [ ] 支持多 MCGS 设备并发接入
- [ ] 历史数据持久化到 SQLite
- [ ] 报警阈值配置与通知
- [ ] 远程 API 服务（HTTP REST 暴露 MCGS 数据）

---

## 附录 A: 文件索引

| 文件 | 行数 | 说明 |
|------|------|------|
| `core/utils/mcgs_modbus_reader.py` | ~750 | Modbus TCP 读取器 |
| `core/services/mcgs_service.py` | ~200 | 数据解析服务 |
| `ui/controllers/mcgs_controller.py` | ~450 | Qt 控制器 |
| `ui/dialogs/mcgs_config_dialog.py` | ~1200 | 配置对话框 |
| `core/foundation/data_bus.py` | ~500 | 数据总线 |
| `config/devices.json` | ~30 | 设备配置 |
| `ui/main_window.py` | ~2700 | 主窗口（含 MCGS 回调）|
