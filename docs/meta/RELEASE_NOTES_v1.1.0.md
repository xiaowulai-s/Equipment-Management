# 工业设备管理系统 v1.1.0 发布说明

🎉 **发布时间**: 2026-03-24
📦 **版本类型**: 重大功能更新
🔗 **GitHub Release**: [v1.1.0](https://github.com/xiaowulai-s/Equipment-Management/releases/tag/v1.1.0)

---

## 🚀 新增功能

### 1. 📊 报警系统
完整的工业报警管理系统，支持：
- ✅ **多级报警**: INFO、WARNING、ERROR、CRITICAL 四个报警级别
- ✅ **阈值报警**: 高温、高压等参数阈值监控
- ✅ **设备离线报警**: 实时检测设备连接状态
- ✅ **通信错误报警**: Modbus 通信异常检测
- ✅ **可视化配置界面**: 直观的报警规则配置对话框
- ✅ **报警历史记录**: 最近 100 条报警记录查询

**配置示例**:
```python
# 默认报警规则
- 温度过高 (>80°C) - WARNING 级别
- 压力过高 (>2.0MPa) - WARNING 级别
```

### 2. 📤 数据导出功能
支持多种格式的数据导出：
- ✅ **CSV 格式**: 通用数据格式，支持 Excel 打开
- ✅ **Excel 格式**: .xlsx 格式，支持格式化输出
- ✅ **JSON 格式**: 结构化数据，支持程序读取
- ✅ **报警历史导出**: 完整报警记录导出

### 3. ⚡ 批量操作
提高设备管理效率：
- ✅ **批量连接设备**: 一键连接多个设备
- ✅ **批量断开设备**: 批量断开设备连接
- ✅ **批量删除设备**: 批量移除设备配置
- ✅ **批量导出配置**: 批量备份设备配置
- ✅ **批量仿真控制**: 批量启停仿真模式
- ✅ **设备选择界面**: 支持全选/反选操作

### 4. 🔧 寄存器配置
灵活的 Modbus 寄存器管理：
- ✅ **多寄存器配置**: 每个设备支持多个寄存器地址
- ✅ **变量映射**: 寄存器地址与变量名映射
- ✅ **数据类型支持**: uint16、int16、uint32、float32 等
- ✅ **读写权限**: 支持只读/读写配置
- ✅ **快速添加**: 常用寄存器模板（温度、压力、流量等）
- ✅ **配置管理对话框**: 可视化寄存器配置界面

---

## 🎨 界面优化

### 工业级 UI 规范
- ✅ 统一使用 Qt Layout 布局（QVBoxLayout / QHBoxLayout）
- ✅ 所有控件在 layout 中管理，无绝对定位
- ✅ 完全支持窗口缩放和自适应
- ✅ 合理的 stretch 和 sizePolicy 设置

### 按钮风格统一
- ✅ **主按钮**: 蓝色 (#0969DA) - 用于主要操作
- ✅ **次要按钮**: 白色 (#FFFFFF) - 用于次要操作
- ✅ **危险按钮**: 红色 (#CF222E) - 用于删除/断开操作
- ✅ **文字标记**: 编辑/连接/断开使用清晰的文字按钮

### 表格样式优化
- ✅ 统一表格样式和交互效果
- ✅ 表头底部蓝色边框线
- ✅ 单元格 padding 优化 (10px)
- ✅ 悬停和选中状态视觉反馈
- ✅ 设备树样式优化

---

## 🏗️ 架构改进

### 四层解耦架构
```
┌─────────────────────┐
│      UI 层           │  PySide6 Widgets
├─────────────────────┤
│   设备管理层         │  DeviceManager
├─────────────────────┤
│   通信驱动层         │  TCP/Serial Driver
├─────────────────────┤
│   协议层            │  Modbus Protocol
└─────────────────────┘
```

### 新增核心模块
- ✅ **AlarmManager**: 报警管理系统
- ✅ **DataExporter**: 数据导出工具
- ✅ **DeviceManager 批量操作**: 批量连接/断开/删除方法

### 新增 UI 组件
- ✅ `ui/alarm_config_dialog.py`: 报警规则配置对话框
- ✅ `ui/batch_operations_dialog.py`: 批量操作对话框
- ✅ `ui/register_config_dialog.py`: 寄存器配置对话框

---

## 📝 文档更新

- ✅ **README.md**: 完整的项目说明和使用指南
- ✅ **CHANGELOG.md**: 详细的版本更新日志
- ✅ **GITHUB_UPLOAD.md**: GitHub 上传和发布指南
- ✅ **RELEASE_NOTES_v1.1.0.md**: 当前版本发布说明

---

## 🛠️ 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 编程语言 |
| PySide6 | 6.5+ | GUI 框架 |
| openpyxl | latest | Excel 导出支持 |
| Modbus TCP | - | 工业协议支持 |

---

## 📦 安装和使用

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
python main.py
```

### 环境要求
- Windows 10/11
- Python 3.8 或更高版本
- 4GB RAM 以上
- 100MB 可用磁盘空间

---

## 🎯 快速开始

### 1. 添加设备
1. 点击左侧"+ 添加设备"
2. 输入设备名称和类型
3. 配置通信参数（IP、端口）
4. 配置寄存器地址（可选）
5. 启用仿真模式（测试用）

### 2. 配置报警
1. 文件 → 报警规则配置
2. 添加规则：参数、阈值、级别
3. 保存规则

### 3. 批量操作
1. 文件 → 批量操作
2. 选择设备
3. 选择操作类型
4. 执行操作

---

## 🐛 Bug 修复

- ✅ 修复按钮显示问题
- ✅ 修复表格样式问题
- ✅ 修复布局自适应问题
- ✅ 修复图标渲染问题

---

## 📊 统计信息

### 代码变更
```
59 files changed
7,959 insertions(+)
10,341 deletions(-)
```

### 新增文件
- `core/utils/alarm_manager.py` - 报警管理
- `core/utils/data_exporter.py` - 数据导出
- `ui/alarm_config_dialog.py` - 报警配置界面
- `ui/batch_operations_dialog.py` - 批量操作界面
- `ui/register_config_dialog.py` - 寄存器配置界面
- `CHANGELOG.md` - 更新日志
- `.gitignore` - Git 忽略配置

### 删除文件
- 所有 QML 相关文件（已废弃）
- `main_v2.py` - 旧版本
- `Backend.py` - QML 后端
- 其他冗余文件

---

## 🔗 相关链接

- **GitHub 仓库**: [Equipment-Management](https://github.com/xiaowulai-s/Equipment-Management)
- **Issue 反馈**: [提交问题](https://github.com/xiaowulai-s/Equipment-Management/issues)
- **项目文档**: [README.md](https://github.com/xiaowulai-s/Equipment-Management/blob/main/README.md)
- **更新日志**: [CHANGELOG.md](https://github.com/xiaowulai-s/Equipment-Management/blob/main/CHANGELOG.md)

---

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

## 👨‍💻 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📧 联系方式

- **作者**: xiaowulai-s
- **项目**: 工业设备管理系统
- **邮箱**: [通过 GitHub Issues 联系](https://github.com/xiaowulai-s/Equipment-Management/issues)

---

**感谢使用工业设备管理系统 v1.1.0！** 🎉
