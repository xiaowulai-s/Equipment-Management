# 更新日志 (CHANGELOG)

## [1.6.0] - 2026-03-30

### 新增功能

#### 0. 循环导入修复
- ✅ 创建 core/utils/alarm_enums.py 独立模块
- ✅ 将 AlarmLevel、AlarmType、AlarmRule、Alarm 类移至 alarm_enums.py
- ✅ 修改 alarm_manager.py 从 alarm_enums.py 导入
- ✅ 修改 alarm_config_dialog.py 从 alarm_enums.py 导入
- ✅ 修改 alarm_rule_persistence.py 从 alarm_enums.py 导入
- ✅ 消除循环导入：alarm_manager ↔ data/models ↔ alarm_rule_persistence ↔ alarm_manager
- ✅ 所有模块导入测试通过

#### 1. UI组件库完整实现
- ✅ 创建完整的UI组件库模块（ui/widgets/）
- ✅ 23个可复用组件，分为7大类：
  - 按钮系统：PrimaryButton、SecondaryButton、SuccessButton、DangerButton、GhostButton
  - 输入控件：LineEdit、ComboBox、InputWithLabel、Checkbox
  - 卡片组件：DataCard、InfoCard、ActionCard
  - 表格组件：DeviceTree、DataTable、DeviceTable
  - 状态组件：StatusLabel、StatusIndicator、StatusBadge、AnimatedStatusBadge
  - 可视化组件：ModernGauge、RealtimeChart
  - 开关组件：Switch、Checkbox、SwitchGroup

#### 2. 主题管理系统
- ✅ 实现 ThemeManager（ui/core/theme.py）
- ✅ 单例模式确保线程安全
- ✅ 支持浅色/深色主题切换
- ✅ theme_changed 信号通知
- ✅ 便捷函数：get_theme_manager()、apply_theme()、toggle_theme()

#### 3. 主窗口重构
- ✅ 替换所有 QPushButton 为组件库按钮
- ✅ 替换 QLineEdit 为 LineEdit
- ✅ 替换 QComboBox 为 ComboBox
- ✅ 替换 QTableWidget 为 DataTable/DeviceTree
- ✅ 替换状态标签为 StatusBadge
- ✅ 移除所有内联样式（StyleProvider类，~200行代码）
- ✅ 添加完整的类文档字符串和方法参数说明
- ✅ 向后兼容：保留旧组件，确保平滑迁移
- ✅ 移除菜单栏"批量操作"入口
- ✅ 在"移除设备"按钮左侧添加"批量操作"按钮（SecondaryButton）
- ✅ 优化UI布局，批量操作更易访问

#### 4. 对话框重构
- ✅ add_device_dialog.py - 完全重构完成
- ✅ batch_operations_dialog.py - 完全重构完成
- ✅ data_export_dialog.py - 完全重构完成
- ✅ 移除所有 setStyleSheet(AppStyles.*) 调用
- ✅ 统一使用组件库标准组件

### 改进

#### 代码质量
- ✅ 完整的类型提示覆盖（TYPE_CHECKING）
- ✅ 详细的文档字符串（类和方法）
- ✅ 符合 PEP 8 规范
- ✅ 移除代码重复，提高可维护性

#### 样式系统
- ✅ 统一样式管理（QSS文件）
- ✅ 移除硬编码样式字符串
- ✅ 支持主题切换
- ✅ 组件行为一致

### 向后兼容

- ✅ 保留所有旧组件（data_card、gauge、trend_chart、realtime_chart）
- ✅ 通过 __init__.py 导出确保平滑迁移
- ✅ 所有重构保持现有功能不变
- ✅ 所有信号槽连接保持完整
- ✅ 所有数据验证逻辑保持不变

### 技术细节

#### 组件库文件结构
```
ui/widgets/
├── __init__.py          # 组件导出
├── buttons.py           # 6个按钮组件
├── inputs.py            # 4个输入控件
├── cards.py            # 3个卡片组件
├── tables.py           # 3个表格组件
├── status.py           # 4个状态组件
├── visual.py           # 2个可视化组件
└── switches.py         # 3个开关组件
```

#### ThemeManager 实现
```python
# 单例模式，线程安全
class ThemeManager(QObject):
    theme_changed = Signal(str)

    _instance: Optional['ThemeManager'] = None
    _lock = threading.Lock()

    @staticmethod
    def get_theme_manager() -> 'ThemeManager':
        """获取主题管理器单例"""
        with ThemeManager._lock:
            if ThemeManager._instance is None:
                ThemeManager._instance = ThemeManager()
            return ThemeManager._instance
```

### 文档更新

- ✅ 更新 README.md 项目结构
- ✅ 添加 UI组件库 特性说明
- ✅ 更新版本号为 v1.6.0
- ✅ 记录重构变更到 CHANGELOG.md

### 测试验证

- ✅ add_device_dialog.py 导入测试通过
- ✅ batch_operations_dialog.py 导入测试通过
- ✅ data_export_dialog.py 导入测试通过
- ✅ main_window_v2.py 导入测试通过

### 待完成

- [ ] device_type_dialogs.py 重构
- [ ] log_viewer_dialog.py 重构
- [ ] register_config_dialog.py 重构
- [ ] dialogs/settings_dialog.py 重构

---

## [1.5.2] - 2026-03-29

### 变更
- 项目文件夹结构整理：移动 30+ 散落文档到 `docs/` 子目录
  - `docs/project/` — 项目总览、架构、进度、分析报告
  - `docs/architecture/` — 架构说明、功能模块联系图
  - `docs/ai/` — AI 开发流程、组件提示词
  - `docs/design/` — UI 设计方案、重构报告、组件库、QML 对比
  - `docs/reports/` — 阶段报告、文档索引、模板
  - `docs/meta/` — CONTRIBUTING、RELEASE_NOTES、GITHUB_UPLOAD
- 移动工具脚本到 `scripts/`（main_v2、migrate_database、monitor_changes 等）
- 移动截图资源到 `assets/`
- 清理临时目录和构建产物（device_manager_test_*、build/、dist/、htmlcov/ 等）
- 删除测试输出临时文件（test_output*.txt、tests/*.txt）
- 更新 `.gitignore`：添加 `device_manager_test_*` 规则
- 修复 pre-commit flake8 配置：移除已废弃的 W503 规则，修复 scripts/ lint 错误

---

## [1.5.1] - 2026-03-29

### 变更
- 统一项目版本号为 v1.5.1
- 简化主题系统：移除深色主题，保留浅色主题为默认
- 清理冗余代码：删除 theme_toggle_button.py、theme_preference.py 及相关测试
- 修复手动断开后设备自动重连的问题（`_manually_disconnected` 机制）
- 修复设备列表操作按钮白色边框问题，改用组件库按钮
- 状态栏增强：显示总设备数、在线数、离线数、错误数
- 新增默认设备：首次启动自动创建 5 个 Modbus TCP + 5 个 Modbus RTU 示例设备
- QSS 样式系统重构：创建 base.qss、base_light.qss、light.qss
- 整理项目文档，更新 README.md 和 CHANGELOG.md

---

## [1.5.0] - 2026-03-28

### 新增功能

#### 1. 新架构迁移
- ✅ 四层解耦架构完成：协议层 → 通信层 → 设备层 → 数据/UI 层
- ✅ 新架构核心代码（src/）独立于旧架构（core/）
- ✅ Modbus TCP/RTU/ASCII 协议实现（含 CRC-16/LRC 校验）
- ✅ TCP 驱动（非阻塞 I/O + SSL + 自动重连）
- ✅ 串口驱动（pyserial + 流控 + 热插拔）
- ✅ 数据持久化层（SQLite WAL + 6 表 ORM + Repository 模式）
- ✅ 报警系统（四级报警 + 死区控制 + 冷却机制）
- ✅ 数据采集引擎（线程池 + 请求合并 + 统计监控）

#### 2. 高级可视化组件
- ✅ ModernGauge - 动态圆形仪表盘（QPropertyAnimation 平滑动画 + 发光渐变）
- ✅ AnimatedStatusBadge - 带呼吸灯的状态徽章
- ✅ RealTimeChart - 基于 pyqtgraph 的实时趋势图（多曲线 + 时间戳 X 轴）
- ✅ DataCard - 数据卡片组件（实时值 + 状态 + 趋势）
- ✅ TrendChart - Canvas 趋势图组件

#### 3. 监控仪表板
- ✅ DashboardPage 高级可视化仪表板页面
- ✅ RegisterCache 滑动窗口缓存（默认 100 点）
- ✅ 自动为设备创建仪表盘和趋势图

#### 4. 主题系统
- ✅ ThemeManager 统一主题管理（QSS 组合加载）
- ✅ ThemeColors 动态颜色 API（语义化色彩查询）
- ✅ 深色/浅色主题支持（QSS 文件分层）
- ✅ 主题切换按钮（3 种样式）

#### 5. 设备管理增强
- ✅ 设备编辑功能（保留运行时状态）
- ✅ 设备添加功能（对话框配置 → Device.from_dict）
- ✅ device_updated 信号（列表 + 监控页联动刷新）

#### 6. 系统功能
- ✅ 五页系统设置对话框（采集/报警/日志/界面/关于）
- ✅ 性能优化和压力测试工具套件
- ✅ PyInstaller 打包配置（单文件/目录模式）
- ✅ 完整项目文档（用户文档 + 部署指南 + 性能优化建议）

### 测试覆盖
- ✅ 1800+ 项测试用例
- ✅ 协议层: 80 项（TCP）+ 117 项（RTU/ASCII）
- ✅ 设备模型: 180 项，设备管理器: 144 项
- ✅ 数据采集引擎: ~80 项

---

## [1.3.0] - 2026-03-26

### 新增功能

#### 1. UI 组件库
- ✅ 完整的 Python UI 组件库系统
  - 23 个可复用组件（按钮、输入、卡片、表格、状态、可视化、开关）
  - 工业级组件设计和实现
  - 统一的样式系统和主题管理

#### 2. 中文本地化
- ✅ TextConstants / StatusText / LogMessages / UIMessages
- ✅ 应用名称："工业设备管理系统"

#### 3. AI 辅助系统
- ✅ AI 组件使用提示词文档

### 改进和优化
- 类型提示完整覆盖，PEP 8 规范遵循
- 四层解耦架构：UI 层 / 设备管理层 / 通信层 / 协议层

---

## [1.1.0] - 2026-03-24

### 新增功能
- 报警系统（多级报警、阈值报警、设备离线报警、通信错误报警）
- 数据导出（CSV / Excel / JSON）
- 批量操作（批量连接/断开/删除/导出/启停仿真）
- 寄存器配置（每设备多寄存器、快速添加常用寄存器）

### 界面优化
- Qt Layout 布局、窗口缩放、按钮风格统一、表格样式优化

---

## [1.0.0] - 2026-03-20

### 初始版本
- 基础设备管理功能
- Modbus 通信协议支持
- 实时监控界面
- 设备类型管理
- 基础日志系统
- 配置文件管理

---

## 版本说明

### 当前版本: **v1.5.2**
### 技术栈: Python 3.10+ | PySide6 6.6+ | PyQtGraph | openpyxl | SQLAlchemy 2.0+
### 系统要求: Windows 10/11 | Python 3.10+ | 4GB RAM | 100MB 磁盘
