# 工业设备管理系统 v1.1

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/yourusername/equipment-management/releases)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 项目概述

基于 **PySide6 Widgets** 的现代化工业设备管理系统，采用四层解耦架构设计，支持报警系统、数据导出、批量操作和寄存器配置功能。

![版本](https://img.shields.io/badge/版本 -1.1.0-blue)
![更新](https://img.shields.io/badge/更新 -2026--03--24-green)

## 项目结构

```
equipment management/
├── main.py                         # 主程序入口
├── requirements.txt                # 项目依赖
│
├── core/                          # 核心模块
│   ├── device/                    # 设备管理层
│   │   ├── device_manager.py       # 设备管理器
│   │   ├── device_model.py        # 设备模型
│   │   ├── device_type_manager.py  # 设备类型管理
│   │   ├── device_factory.py      # 设备工厂
│   │   └── simulator.py           # 设备模拟器
│   │
│   ├── communication/            # 通信层
│   │   ├── base_driver.py        # 通信驱动基类
│   │   ├── serial_driver.py       # 串口驱动
│   │   └── tcp_driver.py         # TCP 驱动
│   │
│   ├── protocols/               # 协议层
│   │   ├── base_protocol.py     # 协议基类
│   │   └── modbus_protocol.py   # Modbus 协议
│   │
│   └── utils/                  # 工具模块
│       ├── logger.py            # 日志系统
│       ├── alarm_manager.py     # 报警管理系统
│       └── data_exporter.py     # 数据导出工具
│
├── ui/                           # UI 模块
│   ├── styles.py                 # 样式管理
│   ├── device_type_dialogs.py   # 设备类型对话框
│   └── add_device_dialog.py      # 添加设备对话框
│
├── config/                       # 配置文件目录
│   └── pump_station_a.json      # 设备配置示例
│
└── data/                         # 数据目录
    └── equipment_management.db  # SQLite 数据库
```

## 技术栈

- **UI框架**: PySide6 Widgets
- **Python版本**: Python 3.8+
- **依赖**: PySide6>=6.6.0, pyserial>=3.5

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 核心功能

### 1. 设备管理
- 添加、编辑、删除设备
- 设备类型管理（支持自定义设备类型）
- 设备分组管理
- 设备连接/断开控制
- 实时设备状态监控
- **批量操作**（批量连接/断开/删除设备）
- **寄存器配置**（每个设备可配置多个寄存器地址）

### 2. 数据监控
- 实时数据卡片展示
- 数据表格显示
- 寄存器监控
- 通信日志查看

### 3. 报警系统
- 阈值报警（高温、高压等）
- 设备离线报警
- 通信错误报警
- 多级报警（INFO、WARNING、ERROR、CRITICAL）
- 报警历史记录
- **可视化报警规则配置界面**

### 4. 数据导出
- 支持 CSV 格式导出
- 支持 Excel 格式导出
- 支持 JSON 格式导出
- 报警历史导出

### 5. 四层架构
- **UI 层**: PySide6 Widgets 组件
- **设备管理层**: DeviceManager 统一管理
- **通信层**: 串口/TCP 驱动
- **协议层**: Modbus 协议解析

### 6. 系统功能
- 完整的日志系统
- 配置管理
- 数据库存储
- 历史数据记录

## 快速开始

### 环境要求

- Python 3.8+
- PySide6 6.5+
- openpyxl（Excel 导出支持）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python main.py
```

### 功能使用

#### 1. 添加设备

1. 点击左侧"+ 添加设备"
2. 输入设备名称
3. 选择设备类型
4. 配置通信参数（IP 地址、端口等）
5. **配置寄存器地址**（点击"⚙️ 配置寄存器地址"按钮）
   - 可添加多个寄存器，每个寄存器对应一个变量
   - 支持设置地址、功能码、变量名、数据类型、读写权限等
   - 支持快速添加常用寄存器（温度、压力、流量等）
6. 勾选"启用仿真模式"（测试用）
7. 点击"确定"

#### 2. 连接设备

1. 在设备列表中选择设备
2. 点击设备右侧的"连接"按钮
3. 查看右侧实时数据卡片

#### 3. 配置报警

**快速配置：**
1. 点击"文件"菜单 → "报警规则配置"
2. 点击"添加规则"按钮
3. 填写规则信息：
   - 规则 ID（唯一标识）
   - 设备 ID（* 表示所有设备）
   - 监测参数（如：温度、压力）
   - 报警类型（高阈值/低阈值/设备离线/通信错误）
   - 阈值设置
   - 报警级别（INFO/WARNING/ERROR/CRITICAL）
4. 点击"保存"

**默认报警规则：**
- 温度过高 (>80°C) - WARNING 级别
- 压力过高 (>2.0MPa) - WARNING 级别

#### 4. 导出数据

1. 点击"文件"菜单 → "数据导出"
2. 选择保存位置
3. 选择文件格式（CSV/Excel/JSON）
4. 点击"保存"

#### 5. 查看报警历史

1. 点击"工具"菜单 → "报警历史"
2. 查看最近 100 条报警记录

#### 6. 批量操作设备

1. 点击"文件"菜单 → "批量操作"
2. 在设备列表中选择要操作的设备（支持全选/反选）
3. 选择操作类型：
   - 批量连接设备
   - 批量断开设备
   - 批量删除设备
   - 批量导出配置
   - 批量启动/停止仿真
4. 点击"执行操作"
5. 查看操作结果统计

## 开发说明

### 模块说明

- `core/device/` - 设备管理核心逻辑
- `core/communication/` - 设备通信驱动
- `core/protocols/` - 通信协议实现
- `core/utils/` - 工具模块（日志、报警、数据导出）
- `ui/` - 用户界面组件

### 添加新设备类型

1. 点击"文件"菜单 → "设备类型管理"
2. 点击"添加类型"按钮
3. 输入设备类型名称（描述会自动生成为"通用 xxx 设备"）
4. 点击"确定"保存

### 样式定制

UI 样式统一管理在 `ui/styles.py` 的 `AppStyles` 类中。

### 报警规则配置

在 `main.py` 的 `_setup_alarm_rules()` 方法中配置默认报警规则：

```python
def _setup_alarm_rules(self):
    default_rules = [
        AlarmRule(
            rule_id="TEMP_HIGH",
            device_id="*",
            parameter="温度",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=80.0,
            level=AlarmLevel.WARNING,
            description="温度过高报警"
        ),
        # 添加更多规则...
    ]
```

## 更新日志

详细更新内容请查看 [CHANGELOG.md](CHANGELOG.md)

### v1.1.0 (2026-03-24)
- 新增报警系统和可视化配置界面
- 新增数据导出功能（CSV/Excel/JSON）
- 新增批量操作功能
- 新增寄存器配置功能
- 优化 UI 布局和按钮样式

### v1.0.0 (2026-03-20)
- 初始版本发布
