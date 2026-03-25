# 工业设备管理系统

<div align="center">

![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.11.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**基于 PySide6 和 Modbus 协议的工业设备上位机管理系统**

[文档](#文档) • [功能特性](#功能特性) • [快速开始](#快速开始) • [使用说明](#使用说明)

</div>

---

## 📋 目录

- [简介](#简介)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [使用说明](#使用说明)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [测试](#测试)
- [文档](#文档)
- [常见问题](#常见问题)
- [贡献](#贡献)
- [许可证](#许可证)
- [联系方式](#联系方式)

---

## 📖 简介

工业设备管理系统是一款专业的上位机软件，用于监控和管理工业现场设备。系统基于 Modbus TCP/RTU/ASCII协议，支持多设备并发管理，提供实时数据监控、历史记录、报警管理等完整功能。

### 应用场景

- 🏭 工厂自动化监控系统
- 🔌 PLC 设备数据采集
- 🌡️ 温湿度传感器监控
- ⚡ 电力仪表数据采集
- 🎛️ 变频器控制与监控

---

## ✨ 功能特性

### 核心功能

- ✅ **多协议支持**: Modbus TCP、Modbus RTU、Modbus ASCII
- ✅ **多设备管理**: 支持同时管理多个设备，独立配置
- ✅ **实时监控**: 实时显示设备状态和数据
- ✅ **历史数据**: 自动记录历史数据，支持查询导出
- ✅ **报警系统**: 可视化报警规则配置，多级报警
- ✅ **主题切换**: 浅色/深色主题，偏好自动保存
- ✅ **数据导出**: 支持 CSV、Excel 格式导出

### 技术特性

- ✅ 四层解耦架构（UI/设备管理/通信/协议）
- ✅ 信号槽机制实现松耦合
- ✅ SQLAlchemy ORM 数据库
- ✅ 线程安全的数据流
- ✅ 批量读取优化
- ✅ 完整的测试覆盖

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────┐
│           UI 层 (PySide6)               │
│  MainWindow | Dialogs | Widgets         │
├─────────────────────────────────────────┤
│         设备管理层 (DeviceManager)      │
│  Device  | DeviceFactory | DeviceType   │
├─────────────────────────────────────────┤
│          通信层 (Driver Layer)          │
│  TCPDriver | SerialDriver               │
├─────────────────────────────────────────┤
│          协议层 (Protocol Layer)        │
│  ModbusProtocol (TCP/RTU/ASCII)         │
└─────────────────────────────────────────┘
```

---

## 📦 安装指南

### 环境要求

- **操作系统**: Windows 10/11
- **Python**: 3.9 或更高版本
- **内存**: 最低 2GB，推荐 4GB
- **磁盘**: 500MB 可用空间

### 步骤 1：克隆项目

```bash
git clone https://github.com/xiaowulai-s/Equipment-Management.git
cd equipment management
```

### 步骤 2：创建虚拟环境

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 步骤 3：安装依赖

```bash
# 安装运行依赖
pip install -r requirements.txt

# (可选) 安装开发依赖
pip install -r requirements-dev.txt

# (可选) 安装文档生成依赖
pip install -r requirements-docs.txt
```

### 步骤 4：运行程序

```bash
python main.py
```

---

## 🚀 快速开始

### 1. 启动程序

```bash
python main.py
```

### 2. 添加设备

1. 点击 **"添加设备"** 按钮
2. 填写设备信息：
   - 设备名称：`PLC-001`
   - 协议类型：`Modbus TCP`
   - IP 地址：`192.168.1.100`
   - 端口：`502`
   - 从站 ID: `1`
3. 点击 **"测试连接"** 验证
4. 点击 **"确定"** 保存

### 3. 配置寄存器

1. 点击设备行的 **"编辑"** 按钮
2. 切换到 **"寄存器配置"** 标签
3. 添加寄存器：
   - 地址：`40001`
   - 名称：`温度`
   - 数据类型：`Int16`
4. 点击 **"保存"**

### 4. 连接设备

点击 **"连接"** 按钮，查看实时数据。

---

## 📚 使用说明

### 设备管理

#### 支持的设备类型

- **PLC**: 可编程逻辑控制器
- **Sensor**: 传感器（温湿度、压力等）
- **Meter**: 仪表（电表、水表等）
- **VFD**: 变频器
- **Generic**: 通用设备

#### 设备操作

- **编辑**: 修改设备配置
- **连接**: 建立通信连接
- **断开**: 断开通信
- **删除**: 移除设备

### 通信配置

#### Modbus TCP

```yaml
协议类型：Modbus TCP
IP 地址：192.168.1.100
端口：502
从站 ID: 1
超时：1000ms
```

#### Modbus RTU

```yaml
协议类型：Modbus RTU
串口号：COM1
波特率：9600
数据位：8
停止位：1
校验位：None
从站 ID: 1
```

### 报警配置

1. 点击 **"报警配置"**
2. 选择设备和参数
3. 设置报警条件：
   - 上限报警：值 > 阈值
   - 下限报警：值 < 阈值
4. 设置报警级别：提示、警告、严重、紧急

### 主题切换

点击右上角状态栏按钮切换主题（浅色/深色）。

---

## 📁 项目结构

```
equipment management/
├── core/                      # 核心业务逻辑
│   ├── communication/         # 通信层
│   │   ├── tcp_driver.py     # TCP 驱动
│   │   └── serial_driver.py  # 串口驱动
│   ├── device/               # 设备管理
│   │   ├── device_manager.py # 设备管理器
│   │   ├── device_model.py   # 设备模型
│   │   └── device_factory.py # 设备工厂
│   ├── protocols/            # 协议层
│   │   └── modbus_protocol.py # Modbus 协议
│   ├── utils/                # 工具模块
│   │   ├── alarm_manager.py  # 报警管理器
│   │   ├── logger.py         # 日志系统
│   │   └── serial_utils.py   # 串口工具
│   └── data/                 # 数据层
│       ├── models.py         # 数据库模型
│       └── repository/       # 数据仓库
├── ui/                       # UI 层
│   ├── main_window_v2.py     # 主窗口
│   ├── styles.py             # 样式系统
│   ├── theme_manager.py      # 主题管理
│   ├── add_device_dialog.py  # 添加设备对话框
│   └── ...
├── tests/                    # 测试目录
│   ├── test_core/           # 核心层测试
│   └── test_ui/             # UI 层测试
├── docs/                     # 文档目录
│   ├── 用户文档.md          # 用户手册
│   └── API 文档              # API 参考
├── config/                   # 配置文件
├── data/                     # 数据文件
├── logs/                     # 日志文件
├── main.py                   # 程序入口
├── requirements.txt          # 依赖包
└── README.md                 # 项目说明
```

---

## 💻 开发指南

### 代码规范

遵循 PEP 8 规范，使用以下工具：

```bash
# 代码格式化
black core/ ui/

# 导入排序
isort core/ ui/

# 代码检查
flake8 core/ ui/
```

### Pre-commit 钩子

```bash
# 安装 pre-commit
pip install pre-commit
pre-commit install

# 运行所有检查
pre-commit run --all-files
```

### 添加新功能

1. 在对应模块创建新文件
2. 编写单元测试
3. 更新文档
4. 提交代码

---

## 🧪 测试

### 运行测试

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 运行所有测试
python -m pytest tests/ -v

# 生成覆盖率报告
python -m pytest tests/ --cov=core --cov=ui --cov-report=html

# 查看报告
start htmlcov\index.html
```

### 测试覆盖

当前测试覆盖率：

- **核心模块**: 91%
- **UI 模块**: 87%
- **总体**: 8%

目标：提升到 80%+

---

## 📖 文档

### 用户文档

详细的使用手册，包括：

- 安装指南
- 快速入门
- 功能说明
- 高级配置
- 常见问题

查看：[docs/用户文档.md](docs/用户文档.md)

### API 文档

使用 Sphinx 生成的 API 参考文档：

```bash
# 安装文档依赖
pip install -r requirements-docs.txt

# 生成文档
cd docs
sphinx-build -b html . _build/html

# 打开文档
start _build/html/index.html
```

查看：[docs/index.rst](docs/index.rst)

---

## ❓ 常见问题

### Q: 无法连接到设备？

**检查项**:
1. IP 地址和端口是否正确
2. 设备是否开机
3. 网络是否连通（ping 测试）
4. 防火墙是否阻止

### Q: 串口无法打开？

**解决方法**:
1. 检查串口号（设备管理器中查看）
2. 关闭占用串口的其他程序
3. 使用"串口测试"功能验证

### Q: 读取的数据不正确？

**检查项**:
1. 寄存器地址是否正确
2. 数据类型是否匹配
3. 字节顺序设置

更多问题请查看 [用户文档](docs/用户文档.md)

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 贡献方式

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献指南

- 遵守代码规范
- 编写单元测试
- 更新相关文档
- 确保测试通过

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 📞 联系方式

- **项目地址**: https://github.com/xiaowulai-s/Equipment-Management
- **问题反馈**: https://github.com/xiaowulai-s/Equipment-Management/issues
- **邮箱**: support@example.com

---

## 📈 更新日志

### v1.1.0 (2026-03-25)

**新增功能**:
- ✅ 支持 Modbus ASCII 协议
- ✅ 主题切换功能（浅色/深色）
- ✅ 串口测试功能
- ✅ 批量读取寄存器
- ✅ 报警规则持久化

**优化改进**:
- ✅ 设备管理性能优化
- ✅ UI 响应速度提升
- ✅ 日志系统完善
- ✅ 测试覆盖率提升

**Bug 修复**:
- ✅ 修复设备状态同步问题
- ✅ 修复串口通信异常
- ✅ 修复主题切换卡顿

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给一个 Star！⭐**

[⬆ 返回顶部](#工业设备管理系统)

</div>
