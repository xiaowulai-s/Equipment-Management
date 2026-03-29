# AI 组件使用提示词模板

## 📋 目录
1. [快速开始提示词](#1-快速开始提示词)
2. [组件集成提示词](#2-组件集成提示词)
3. [UI重构提示词](#3-ui重构提示词)
4. [新功能开发提示词](#4-新功能开发提示词)
5. [最佳实践](#5-最佳实践)

---

## 1. 快速开始提示词

### 场景：在现有项目中使用组件库

```
我有一个工业设备管理系统项目，项目路径是：e:\下载\app\equipment management

项目使用 PySide6 开发，包含以下组件库文档：
- 文档位置：e:\下载\app\equipment management\Python UI 组件库完整方案.md

组件库包含以下模块：
- widgets/buttons.py - 按钮系统
- widgets/inputs.py - 输入控件
- widgets/cards.py - 卡片组件
- widgets/tables.py - 表格组件
- widgets/status.py - 状态组件
- widgets/visual.py - 高级可视化组件（ModernGauge, AnimatedStatusBadge, RealtimeChart）
- widgets/charts.py - 图表组件
- widgets/switches.py - 开关组件
- core/theme.py - 主题管理

请帮我：
1. 读取 ui/main_window_v2.py 文件
2. 分析现有UI代码结构
3. 使用组件库中的组件替换现有的原生控件
4. 确保所有组件使用统一的工业风深色主题
5. 保持现有功能不变，只优化UI实现方式
```

---

## 2. 组件集成提示词

### 场景：添加新的可视化组件

```
我需要在项目中添加一个实时数据监控面板，要求如下：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：e:\下载\app\equipment management\Python UI 组件库完整方案.md

## 需求
1. 创建一个新的监控面板类 MonitorPanel
2. 集成以下可视化组件：
   - ModernGauge：显示设备利用率（0-100%）
   - AnimatedStatusBadge：显示设备状态
   - RealtimeChart：显示温度实时趋势

## 组件使用要求
- ModernGauge:
  * title="设备利用率"
  * value=当前利用率（通过信号更新）
  * color="#2196F3"（蓝色）

- AnimatedStatusBadge:
  * text=状态文字
  * color=状态颜色
  * 状态映射：
    - "在线" → "#4CAF50"
    - "离线" → "#EF4444"
    - "警告" → "#FFC107"
    - "错误" → "#F44336"

- RealtimeChart:
  * title="温度实时趋势图"
  * max_points=100（保持最近100个数据点）
  * update_data() 方法接收温度列表

## 布局要求
- 使用 QVBoxLayout 垂直布局
- 组件间距：20px
- 边距：25px
- 仪表盘水平排列（QHBoxLayout）

## 数据更新
- 使用 QTimer 每1000ms更新一次
- 数据来源：通过信号连接到设备管理器
- 模拟数据：使用 random 模拟温度波动

## 样式要求
- 背景色：#0F1419
- 所有组件使用工业风深色主题
- 确保响应式布局，支持窗口缩放
```

---

## 3. UI重构提示词

### 场景：重构现有对话框使用组件库

```
我需要重构项目中的对话框，使用统一的UI组件库，要求如下：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：e:\下载\app\equipment management\Python UI 组件库完整方案.md
- 需要重构的文件：ui/add_device_dialog.py

## 重构要求

### 按钮替换
- 将所有 QPushButton 替换为组件库按钮：
  * "确定" → PrimaryButton
  * "取消" → SecondaryButton
  * "删除" → DangerButton
  * "保存" → SuccessButton

### 输入控件替换
- QLineEdit → LineEdit（带占位符）
- QComboBox → ComboBox
- QCheckBox → Checkbox

### 状态显示
- 状态标签 → StatusBadge 或 AnimatedStatusBadge

### 表格样式
- QTableWidget → DataTable（如果适用）
- 确保表格样式与组件库一致

## 样式统一
- 移除所有内联样式
- 使用组件库的统一样式
- 确保深色主题一致性

## 功能保持
- 保持所有现有功能不变
- 保持所有信号槽连接
- 保持所有数据验证逻辑

## 代码质量
- 添加类型提示
- 添加文档字符串
- 遵循 PEP 8 规范
- 添加必要的注释

请先读取原文件，然后给出重构方案，最后执行重构。
```

---

## 4. 新功能开发提示词

### 场景：开发设备监控仪表板

```
我需要开发一个设备监控仪表板，完整功能如下：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：e:\下载\app\equipment management\Python UI 组件库完整方案.md
- 参考示例：e:\下载\app\equipment management\Python UI 组件库完整方案.md 中的工业仪表板示例

## 功能需求

### 1. 主界面布局
- 使用 QMainWindow 作为主窗口
- 标题："工业设备监控仪表板"
- 尺寸：1100x900
- 深色主题背景：#0F1419

### 2. 仪表盘区域
- 三个 ModernGauge 组件水平排列
- 分别显示：利用率（蓝色）、预警值（黄色）、风险度（红色）
- 初始值：75, 85, 92
- 实时更新：每1秒随机变化

### 3. 数据表格
- 5行5列的 QTableWidget
- 表头：地址、功能码、变量名、数值、状态
- 样式：深色主题
- 状态列使用 AnimatedStatusBadge 组件
- 数据示例：
  * 0x0001, 03, 温度传感器, 25.5, 正常(绿色)
  * 0x0002, 03, 压力变送器, 1.23, 正常(绿色)
  * 0x0003, 03, 流量计, 50.3, 警告(黄色)
  * 0x0004, 03, 功率表, 15.2, 故障(红色)
  * 0x0005, 03, 频率, 50.0, 正常(绿色)

### 4. 实时趋势图
- 使用 RealtimeChart 组件
- 标题："温度实时趋势图"
- 显示最近100个数据点
- 每秒添加新数据，自动滚动
- 初始数据：100个正态分布随机数（均值20，标准差1）

### 5. 定时更新
- 使用 QTimer 每1000ms 触发一次
- 更新三个仪表盘的数值
- 更新图表数据
- 模拟真实设备数据波动

## 技术要求
- 使用 PySide6
- 遵循组件库文档的API
- 所有组件使用统一的深色主题
- 代码符合 PEP 8 规范
- 添加类型提示和文档字符串

## 交付物
1. 完整的 Python 代码文件
2. 可直接运行的主程序
3. 代码注释说明
4. 扩展建议

请参考组件库文档中的示例，实现这个仪表板。
```

---

### 场景：集成Modbus设备数据

```
我需要将设备数据集成到可视化组件中，要求如下：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：e:\下载\app\equipment management\Python UI 组件库完整方案.md
- 设备管理器：core/device/device_manager_v2.py

## 需求

### 数据源
- 从 DeviceManagerV2 获取实时设备数据
- 设备数据包括：温度、压力、流量、状态等

### 可视化组件集成

#### 1. ModernGauge 集成
- 创建多个仪表盘显示不同参数
- 温度仪表盘：显示设备温度（0-100°C）
- 压力仪表盘：显示设备压力（0-2.5 MPa）
- 流量仪表盘：显示设备流量（0-100 m³/h）
- 通过信号连接到设备数据更新

#### 2. RealtimeChart 集成
- 显示温度历史趋势
- 每秒更新一次
- 保持最近100个数据点
- 支持多条曲线（温度、压力）

#### 3. AnimatedStatusBadge 集成
- 显示设备在线/离线状态
- 状态变化时自动更新颜色和文字
- 正常：绿色，"在线"
- 异常：红色，"离线"

### 实现步骤
1. 读取 device_manager_v2.py，了解数据结构
2. 创建可视化面板类
3. 创建可视化组件实例
4. 连接设备管理器的信号到可视化组件
5. 实现数据更新逻辑
6. 添加错误处理

### 信号连接示例
```python
# 连接设备状态变化信号
device_manager.device_status_changed.connect(self.on_device_status_changed)

# 连接数据更新信号
device_manager.data_updated.connect(self.on_data_updated)
```

### 错误处理
- 设备连接失败时显示错误状态
- 数据异常时显示警告
- 记录日志到日志系统

## 输出要求
- 完整的 Python 代码
- 信号连接说明
- 测试方法
- 错误处理说明
```

---

## 5. 最佳实践

### 5.1 提示词结构模板

```
## 项目信息
- 项目路径：[具体路径]
- 组件库文档：[文档路径]
- 相关文件：[需要操作的文件列表]

## 需求描述
[详细描述你的需求]

## 技术约束
- [技术栈要求]
- [框架版本]
- [编码规范]
- [性能要求]

## 输出要求
- [代码质量要求]
- [文档要求]
- [测试要求]

## 参考资源
- [相关文档链接]
- [示例代码]
- [设计图]
```

### 5.2 组件使用规范

#### 按钮组件
```
使用 PrimaryButton 作为主要操作按钮
使用 SecondaryButton 作为次要操作
使用 DangerButton 用于删除等危险操作
使用 SuccessButton 用于保存等成功操作
```

#### 状态显示
```
使用 StatusLabel 显示简单状态文字
使用 StatusIndicator 显示状态圆点
使用 AnimatedStatusBadge 显示带呼吸灯的状态徽章
```

#### 可视化
```
使用 ModernGauge 显示百分比/比率数据
使用 RealtimeChart 显示实时趋势
使用 DataCard 显示关键指标
```

### 5.3 主题管理

```
在应用启动时应用主题：
from core.theme import ThemeManager

app = QApplication(sys.argv)
ThemeManager.apply_theme(app, 'dark')

主题切换：
new_theme = ThemeManager.toggle_theme(app, current_theme)
```

### 5.4 布局规范

```
- 使用 QVBoxLayout 进行垂直布局
- 使用 QHBoxLayout 进行水平布局
- 使用 QGridLayout 进行网格布局
- 合理使用 setSpacing() 和 setContentsMargins()
- 确保窗口可缩放，不使用固定尺寸
```

### 5.5 信号槽规范

```
- 使用 PyQt/PySide6 的信号槽机制
- 信号命名：finished, changed, updated, clicked
- 槽函数命名：on_<signal_name>()
- 示例：
  button.clicked.connect(self.on_button_clicked)
  data_updated.connect(self.on_data_updated)
```

### 5.6 错误处理

```
- 使用 try-except 捕获异常
- 记录错误日志
- 向用户显示友好的错误信息
- 不要让应用崩溃

示例：
try:
    device.connect()
except ConnectionError as e:
    logger.error(f"连接失败: {e}")
    QMessageBox.warning(self, "连接失败", "无法连接到设备")
```

### 5.7 代码组织

```
项目结构：
ui/
├── main_window.py          # 主窗口
├── widgets/               # 自定义组件
│   ├── __init__.py
│   ├── buttons.py
│   ├── cards.py
│   └── visual.py
├── dialogs/               # 对话框
│   ├── __init__.py
│   └── add_dialog.py
└── styles.py              # 样式定义
```

---

## 6. 常用提示词片段

### 片段1：读取组件库文档

```
请先读取 e:\下载\app\equipment management\Python UI 组件库完整方案.md
文档，了解所有可用的组件及其使用方法。
```

### 片段2：分析现有代码

```
请读取 ui/main_window_v2.py 文件，分析其UI结构，
并列出所有可以替换为组件库组件的原生控件。
```

### 片段3：组件替换建议

```
基于现有代码分析，请给出以下替换建议：
1. 哪些 QPushButton 可以替换为 PrimaryButton/SecondaryButton？
2. 哪些表格可以使用 DataTable 组件？
3. 哪些状态显示可以使用 AnimatedStatusBadge？
4. 是否需要添加可视化组件？
```

### 片段4：实现步骤

```
请按照以下步骤实现：
1. 首先创建组件库模块文件（如果不存在）
2. 然后修改主窗口，导入组件
3. 逐个替换控件，每次替换后测试
4. 确保功能不受影响
5. 优化布局和样式
```

### 片段5：测试验证

```
实现完成后，请：
1. 检查代码是否有语法错误
2. 验证所有功能是否正常
3. 确保样式统一
4. 检查窗口缩放是否正常
5. 给出测试报告
```

---

## 7. 高级场景提示词

### 场景：创建自定义可视化组件

```
我需要创建一个自定义的可视化组件，要求如下：

## 组件需求
- 类名：CustomProgressRing
- 继承自 QWidget
- 功能：显示一个带渐变的环形进度条
- 支持属性：
  * value: float (0-100)
  * color: QColor (进度条颜色)
  * title: str (标题文字)

## 技术要求
- 使用 QPainter 绘制
- 支持抗锯齿
- 响应式尺寸
- 支持动画效果（使用 QPropertyAnimation）

## 集成要求
- 符合组件库的代码风格
- 添加到 widgets/visual.py
- 在组件库文档中添加说明
- 提供使用示例

## 参考组件
- 参考 ModernGauge 的实现
- 参考 AnimatedStatusBadge 的样式
```

### 场景：批量重构UI文件

```
我需要批量重构项目中的UI文件，使用统一的组件库：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：e:\下载\app\equipment management\Python UI 组件库完整方案.md

## 需要重构的文件列表
1. ui/add_device_dialog.py
2. ui/alarm_config_dialog.py
3. ui/batch_operations_dialog.py
4. ui/data_export_dialog.py
5. ui/log_viewer_dialog.py

## 重构任务
对每个文件执行以下操作：
1. 读取并分析文件
2. 识别可替换的原生控件
3. 使用组件库组件替换
4. 统一样式和主题
5. 保持功能不变
6. 添加类型提示和文档

## 执行顺序
1. 先重构第一个文件
2. 测试确认无误后
3. 再重构下一个文件
4. 依此类推

## 质量要求
- 代码符合 PEP 8
- 添加必要的注释
- 保持可读性
- 确保向后兼容
```

---

## 8. 调试和优化提示词

### 场景：性能优化

```
我的实时数据更新界面性能较差，需要优化：

## 问题现象
- 实时数据更新时界面卡顿
- 内存占用持续增长
- CPU 使用率高

## 优化方向
1. 检查是否有不必要的重绘
2. 优化数据更新频率
3. 使用数据缓冲减少绘制次数
4. 检查内存泄漏
5. 优化布局计算

## 具体要求
- 分析 ui/main_window_v2.py 的性能瓶颈
- 给出优化建议
- 实现优化方案
- 提供性能对比数据
```

### 场景：样式问题调试

```
我的组件样式不一致，需要调试：

## 问题描述
- 不同对话框中的按钮样式不同
- 表格边框颜色不统一
- 深色主题部分组件未生效

## 调试要求
1. 检查每个UI文件的样式设置
2. 识别样式冲突
3. 统一使用 AppStyles 中的样式
4. 确保所有组件正确设置 objectName
5. 验证主题切换功能

## 交付物
- 样式问题清单
- 修复方案
- 修复后的代码
- 样式验证报告
```

---

## 9. 文档和培训提示词

### 场景：编写组件使用文档

```
我需要为团队成员编写组件使用文档：

## 文档要求
- 语言：中文
- 格式：Markdown
- 内容：详细的组件使用指南
- 示例：完整的代码示例

## 文档结构
1. 组件库概述
2. 快速开始
3. 组件详解（每个组件一个章节）
   - 组件说明
   - 使用示例
   - API 文档
   - 常见问题
4. 最佳实践
5. 实战案例

## 目标读者
- 初级开发人员
- 不熟悉 PySide6 的开发人员
- 需要快速上手的团队成员

## 参考文档
- e:\下载\app\equipment management\Python UI 组件库完整方案.md
- e:\下载\app\equipment management\新架构说明.md
```

---

## 10. 总结

### 使用提示词的关键点

1. **明确项目路径**：让AI知道从哪里读取文件
2. **提供组件库文档**：让AI了解可用组件
3. **详细的需求描述**：越具体越好
4. **技术约束说明**：框架版本、编码规范等
5. **清晰的输出要求**：代码质量、文档、测试等
6. **参考资源**：提供示例代码、设计图等

### 推荐的工作流程

```
1. 准备阶段
   - 整理项目信息
   - 准备组件库文档
   - 明确需求

2. 编写提示词
   - 使用模板
   - 添加具体细节
   - 设置输出要求

3. 执行任务
   - 让AI先分析
   - 逐步实现
   - 及时反馈

4. 验证和优化
   - 测试功能
   - 检查代码质量
   - 收集团队反馈
```

### 常见问题

**Q: AI不了解我的项目结构怎么办？**
A: 在提示词中提供详细的项目结构说明，包括文件路径和目录树。

**Q: 组件库组件不够用怎么办？**
A: 让AI基于现有组件创建自定义组件，参考文档中的实现方式。

**Q: 如何确保代码质量？**
A: 在提示词中明确要求：类型提示、文档字符串、PEP 8规范、错误处理。

**Q: 如何处理复杂需求？**
A: 将复杂需求拆分为多个小任务，使用多个提示词逐步完成。

**Q: 如何让AI保持一致性？**
A: 在每个提示词中重复关键约束和风格要求，或创建项目特定的提示词模板。

---

**版本**: v1.0.0
**更新日期**: 2026-03-26
**维护者**: 开发团队
