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
- Fluent Design 风格深色/浅色主题
- 五页系统设置对话框
- 数据导出（CSV / Excel）
- 日志查看器
- 批量操作

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
| [新架构说明](新架构说明_v2.md) | v2.0 架构设计详解 |
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

## 📋 开发进度

### 已完成

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1.1 | 四层架构目录结构 | ✅ |
| 1.2 | 代码规范（异常层次 + 日志 + 配置） | ✅ |
| 2.1 | Modbus 协议基类 | ✅ |
| 2.2 | ModbusTCP 协议（80 项测试） | ✅ |
| 2.3 | ModbusRTU/ASCII 协议（117 项测试） | ✅ |
| 3.1 | 通信驱动基类 | ✅ |
| 3.2 | TCP 驱动（非阻塞 I/O + SSL） | ✅ |
| 3.3 | 串口驱动（热插拔 + 缓冲区） | ✅ |
| 4.1 | 设备模型（180 项测试） | ✅ |
| 4.2 | 设备管理器（144 项测试） | ✅ |
| 4.3 | 数据采集引擎（858 行） | ✅ |
| 5.1-5.4 | 数据持久化层（6 表 ORM + 5 Repository） | ✅ |
| 6.1-6.2 | 报警系统 | ✅ |
| 7.1 | 新架构主窗口（1136 行） | ✅ |
| 7.2 | 对话框迁移（7 个对话框） | ✅ |
| 7.3 | 导入验证 + 集成测试 | ✅ |
| 7.4 | 架构文档 | ✅ |
| 8.1 | 自定义可视化组件（DataCard + Gauge + TrendChart） | ✅ |
| 8.2 | MonitorPage 监控页面集成 | ✅ |
| 8.3 | pyqtgraph 实时曲线图 | ✅ |
| 8.4 | 系统设置对话框（5 页） | ✅ |
| 8.5 | 性能优化和压力测试 | ✅ |
| 9.1 | PyInstaller 打包配置 | ✅ |
| 9.2 | 用户文档 + 部署指南 | ✅ |

## 📄 License

MIT License

---

**版本**: v1.5.0 | **更新**: 2026-03-28
