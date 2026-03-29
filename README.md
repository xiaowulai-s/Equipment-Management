# 工业设备管理系统 (Equipment Management System)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.10%2B-green.svg)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

基于 PySide6 和 Modbus 协议的工业设备上位机监控软件，采用四层解耦架构，支持多设备并发管理和实时数据可视化。

## ✨ 特性

### 协议支持
- **Modbus TCP** — 以太网通信，支持 Keepalive 和 SSL
- **Modbus RTU** — 串口通信（RS485/RS232），支持 CRC-16 校验
- **Modbus ASCII** — ASCII 编码串口通信，支持 LRC 校验

### 设备管理
- 多设备并发管理（支持 100+ 设备、20000+ 寄存器）
- 设备增删改查 + 搜索 + 批量操作
- JSON 配置持久化
- 自动重连和失败重试

### 数据可视化
- **DataCard** — 数据卡片，实时值 + 状态 + 趋势
- **Gauge** — Canvas 仪表盘，弧形进度条
- **TrendChart** — Canvas 趋势图
- **RealTimeChart** — pyqtgraph 高性能实时曲线图（支持缩放/平移/多系列）

### 报警系统
- 四级报警：高高(HH) / 高(H) / 低(L) / 低低(LL)
- 死区控制，防止频繁报警
- 冷却机制，避免报警风暴
- 通知渠道：弹窗 / 声音 / 自定义
- 报警确认 + 历史记录 + 统计分析

### 系统功能
- Fluent Design 风格浅色主题
- 五页系统设置对话框
- 数据导出（CSV / Excel）
- 日志查看器
- 批量操作
- 默认示例设备（5 TCP + 5 RTU）

## 🏗 架构

```
┌─────────────────────────────────────────┐
│            UI 层 (PySide6 Widgets)       │
│  MainWindow + MonitorPage + Widgets      │
├─────────────────────────────────────────┤
│          设备管理层 (DeviceManager)       │
│  Device + Register + DataCollector       │
├─────────────────────────────────────────┤
│        通信驱动层 (TCP/Serial)           │
│  TcpDriver + SerialDriver               │
├─────────────────────────────────────────┤
│         协议层 (Modbus Protocol)         │
│  TCP + RTU + ASCII + CRC/LRC            │
└─────────────────────────────────────────┘
          ↕
┌─────────────────────────────────────────┐
│        数据持久化层 (SQLite)              │
│  DatabaseManager + Repository            │
└─────────────────────────────────────────┘
```

## 📁 项目结构

```
equipment-management/
├── src/                        # 核心源码
│   ├── protocols/              # 第一层: 协议层
│   ├── communication/          # 第二层: 通信驱动层
│   ├── device/                 # 第三层: 设备管理层
│   ├── data/                   # 数据持久化层 (SQLite)
│   │   └── repository/         # Repository 模式
│   ├── alarm/                  # 报警系统
│   └── utils/                  # 工具模块
├── ui/                         # 第四层: UI 层
│   ├── styles/                 # Fluent Design 样式系统
│   │   ├── theme.py            # 色彩/字体/间距常量
│   │   └── qss/                # QSS 样式表 (base/dark/light)
│   ├── dialogs/                # 对话框集合
│   ├── widgets/                # 自定义可视化组件
│   └── main_window.py          # 主窗口
├── tests/                      # 测试套件 (pytest)
├── docs/                       # 文档
├── config/                     # 配置文件
├── scripts/                    # 构建脚本
├── data/                       # 数据库文件
└── logs/                       # 日志文件
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11, macOS 10.15+, 或 Linux

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd equipment-management

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 核心依赖

| 包 | 版本 | 用途 |
|----|------|------|
| [PySide6](https://pypi.org/project/PySide6/) | 6.10+ | Qt for Python UI 框架 |
| [SQLAlchemy](https://pypi.org/project/SQLAlchemy/) | 2.0+ | 数据库 ORM |
| [pyserial](https://pypi.org/project/pyserial/) | 3.5+ | 串口通信 |
| [pyqtgraph](https://pypi.org/project/pyqtgraph/) | 0.13+ | 高性能数据可视化 |
| [numpy](https://pypi.org/project/numpy/) | 1.24+ | 数值计算 |

## 📖 文档

| 文档 | 说明 |
|------|------|
| [用户文档](docs/用户文档.md) | 安装、配置和使用指南 |
| [安装部署指南](docs/安装部署指南.md) | 打包部署和故障排除 |
| [新架构说明](docs/architecture/新架构说明_v2.md) | v2.0 架构设计详解 |
| [性能优化建议](docs/性能优化建议.md) | 性能测试结果和优化方案 |
| [测试指南](docs/TESTING_GUIDE.md) | 测试框架和编写规范 |
| [类型提示指南](docs/TYPE_HINTS_GUIDE.md) | 类型注解规范 |

## 🧪 测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_step2_2.py -v    # ModbusTCP 协议测试
pytest tests/test_step4_1.py -v    # 设备模型测试

# 性能测试
python tests/test_ui_performance.py
python tests/test_large_scale_performance.py

# 内存泄漏检测
python tests/memory_leak_detector.py
```

测试覆盖：**1800+ 项测试用例**

## 🎨 设计规范

| 项目 | 值 |
|------|-----|
| 主色 | `#2196F3` (科技蓝) |
| 辅助色 | `#00BCD4` (青色) |
| 成功 | `#4CAF50` |
| 警告 | `#FFC107` |
| 错误 | `#F44336` |
| 深色背景 | `#0F1419` / `#161B22` / `#1C2128` |
| 正文字体 | Segoe UI |
| 等宽字体 | JetBrains Mono |

## 🔧 开发

### 构建可执行文件

```bash
# 使用打包脚本
python scripts/build.py

# 或手动使用 PyInstaller
pyinstaller build.spec
```

### 代码规范

```bash
# 代码检查
flake8 src/ ui/ --config .flake8

# 格式化
autopep8 src/ ui/ --in-place
```

### 技术栈

| 技术 | 用途 |
|------|------|
| PySide6 | UI 框架 |
| SQLite (WAL) | 嵌入式数据库 |
| SQLAlchemy 2.0 | ORM + Repository 模式 |
| pyqtgraph | GPU 加速数据可视化 |
| QThread + Signal/Slot | 线程间通信 |

## 📋 版本历史

### v1.5.2 (2026-03-29)

**项目整理**
- 整理项目文件夹结构，移动 30+ 散落文档到 `docs/` 子目录（project/architecture/ai/design/reports/meta）
- 移动工具脚本到 `scripts/`，截图资源到 `assets/`
- 清理临时目录和构建产物
- 修复 pre-commit flake8 配置

---

### v1.5.1 (2026-03-29)

**主题简化 & Bug 修复**
- 简化主题系统：移除深色主题，保留浅色主题为默认
- 修复手动断开后设备自动重连的问题（`_manually_disconnected` 机制）
- 修复设备列表操作按钮白色边框问题
- 状态栏增强：显示总设备数、在线数、离线数、错误数
- 新增默认设备：首次启动自动创建 5 TCP + 5 RTU 示例设备
- QSS 样式系统重构

---

### v1.5.0 (2026-03-28)

**架构重构 & 可视化升级**
- 四层解耦架构完成：协议层 → 通信层 → 设备层 → 数据/UI 层
- Modbus TCP/RTU/ASCII 协议实现（含 CRC-16/LRC 校验）
- TCP 驱动（非阻塞 I/O + SSL + 自动重连）
- 串口驱动（pyserial + 流控 + 热插拔）
- 数据持久化层（SQLite WAL + 6 表 ORM + Repository 模式）
- 报警系统（四级报警 + 死区控制 + 冷却机制）
- 数据采集引擎（线程池 + 请求合并 + 统计监控）
- 高级可视化组件：ModernGauge、DataCard、TrendChart、RealTimeChart
- DashboardPage 监控仪表板页面
- ThemeManager 主题管理系统
- 设备编辑/添加功能（保留运行时状态）
- 五页系统设置对话框
- PyInstaller 打包配置
- 1800+ 项测试用例

---

### v1.3.0 (2026-03-26)

**UI 组件库**
- 23 个可复用组件（按钮、输入、卡片、表格、状态、可视化、开关）
- 工业级组件设计和实现
- 统一的样式系统和主题管理
- 中文本地化（TextConstants / StatusText / LogMessages / UIMessages）
- 类型提示完整覆盖，PEP 8 规范遵循

---

### v1.1.0 (2026-03-24)

**报警 & 数据导出**
- 报警系统（多级报警、阈值报警、设备离线报警、通信错误报警）
- 数据导出（CSV / Excel / JSON）
- 批量操作（批量连接/断开/删除/导出/启停仿真）
- 寄存器配置（每设备多寄存器、快速添加常用寄存器）
- 界面优化：Qt Layout 布局、窗口缩放、按钮风格统一、表格样式优化

---

### v1.0.0 (2026-03-20)

**初始版本**
- 基础设备管理功能
- Modbus 通信协议支持
- 实时监控界面
- 设备类型管理
- 基础日志系统
- 配置文件管理

## 📄 License

MIT License

---

**版本**: v1.5.2 | **更新**: 2026-03-29
