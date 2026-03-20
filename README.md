# Equipment Management System

工业设备管理系统上位机 - Version 1.0

## 项目简介

基于 Python + PyQt5 构建的现代化工业监控界面，实现设备列表管理、实时数据监控、仪表盘展示和 Modbus 寄存器通信功能。

## 技术栈

| 技术 | 说明 |
|------|------|
| Python 3.10+ | 编程语言 |
| PyQt5 | GUI 框架 |
| Matplotlib | 图表绘制 |
| NumPy | 数值计算 |
| pyserial | 串口通信 |

## 项目架构

```
equipment management/
├── main.py                 # 主程序入口
├── gauge.py                # 圆形仪表盘控件
├── trend_chart.py           # 实时趋势图控件
├── data_card.py             # 数据卡片控件
├── modbus_table.py          # Modbus寄存器表格控件
├── run.py                   # 启动脚本
├── requirements.txt         # Python依赖
├── README.md                # 项目文档
├── App.xaml/.cs             # 原C#版本（已废弃）
├── 界面设计图.png           # UI设计稿
└── 界面设计图描述.md        # 设计说明文档
```

## 功能特性

### 界面模块

| 模块 | 功能 |
|------|------|
| 设备列表 | 左侧设备列表，支持多设备切换，显示在线/离线状态 |
| 实时趋势图 | 基于 Matplotlib 的温度/压力实时曲线，每秒更新 |
| 仪表盘 | 4个圆形仪表盘（SQ10/AR2/B/C），支持多颜色状态显示 |
| 数据卡片 | 4个关键数据卡片：温度、压力、气体浓度、湿度 |
| Modbus表格 | 寄存器地址/功能码/值/状态 完整展示 |

### 核心功能

- **深色主题 UI** - 工业风格蓝青色调
- **实时数据更新** - QTimer 驱动，每秒刷新
- **自定义控件** - CircularGauge、RealTimeTrendChart 等
- **模块化设计** - 清晰的 MVC 架构分离

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python run.py
```

或使用虚拟环境：

```bash
.\venv\Scripts\python.exe run.py
```

## 项目结构说明

### 主程序 (main.py)

- `IndustrialMonitorApp` - 主窗口类
- `create_sidebar()` - 设备列表侧边栏
- `create_content_area()` - 主内容区域
- `create_top_bar()` - 顶部标题栏
- `create_trend_section()` - 趋势图区域
- `create_gauge_section()` - 仪表盘区域
- `create_cards_section()` - 数据卡片区域
- `create_modbus_section()` - Modbus表格区域
- `init_timer()` / `update_data()` - 实时数据更新

### 自定义控件

| 文件 | 控件类 | 说明 |
|------|--------|------|
| gauge.py | CircularGauge | 圆形仪表盘，基于 QPainter 绘制 |
| trend_chart.py | RealTimeTrendChart | 趋势图，基于 Matplotlib |
| data_card.py | DataCard | 数据展示卡片 |
| modbus_table.py | ModbusRegisterTable | Modbus 寄存器表格 |

## 界面预览

```
┌─────────────┬──────────────────────────────────────────┐
│  Device     │  Pump Station A        [👤][📊][🔔][⚙️]  │
│  List       ├──────────────────────────────────────────┤
│             │  Real-Time Trend                         │
│  Sensor B   │  ┌────────────────────────────────────┐  │
│  Sensor T   │  │     📈 温度趋势曲线                  │  │
│  Sensor A   │  └────────────────────────────────────┘  │
│  Mirror L   │  Dashboard                               │
│  WallPump S │  ┌────┐ ┌────┐ ┌────┐ ┌────┐            │
│  Fansoh     │  │SQ10│ │AR2 │ │ B  │ │ C  │            │
│             │  └────┘ └────┘ └────┘ └────┘            │
│             │  Key Data                                │
│             │  ┌────────┐ ┌────────┐ ┌────────┐ ...   │
├─────────────┤  │Temp   │ │Pressure│ │Gas    │        │
│ ● Connected │  │ 25.5C │ │123.4AsB│ │405cAsB│        │
│ [Settings]  │  └────────┘ └────────┘ └────────┘        │
└─────────────┴──────────────────────────────────────────┘
```

## 开发说明

### 虚拟环境

推荐使用虚拟环境隔离依赖：

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Qt 平台插件

如遇 Qt 平台插件加载问题，程序会自动设置 `QT_QPA_PLATFORM_PLUGIN_PATH`。

## 版本历史

- **v1.0** (2026-03-20) - 初始版本，实现基础监控界面功能

## License

MIT License
