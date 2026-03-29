# AI提示词：使用UI组件库重构现有项目

> **项目名称**: 工业设备管理系统 (Equipment Management System)
> **版本**: v1.3.0
> **目标**: 使用UI组件库重构现有项目，提升代码质量和可维护性

---

## 📋 目录

1. [项目背景](#1-项目背景)
2. [组件库资源](#2-组件库资源)
3. [重构目标](#3-重构目标)
4. [重构步骤](#4-重构步骤)
5. [代码示例](#5-代码示例)
6. [注意事项](#6-注意事项)

---

## 1. 项目背景

### 当前状态
- **项目路径**: `e:\下载\app\equipment management`
- **当前版本**: v1.3.0
- **技术栈**: PySide6 + Python 3.8+
- **架构**: 四层解耦架构（UI层、设备管理层、通信层、协议层）

### 现有UI实现
- 使用原生PySide6控件
- 样式分散在各个文件中
- 缺乏统一的组件库
- 部分UI代码重复度高

### 重构需求
- 使用统一的UI组件库
- 提升代码可维护性
- 统一样式系统
- 改善用户体验

---

## 2. 组件库资源

### 可用组件文档
```
✅ Python UI 组件库完整方案.md
   - 23个可复用组件
   - 完整的使用示例
   - 工业级设计风格

✅ UI组件库.md
   - 按钮系统
   - 图标按钮
   - 输入控件
   - 开关组件
   - 完整实现代码

✅ AI组件使用提示词.md
   - 10个场景的提示词模板
   - 最佳实践指南
   - 常见问题解答
```

### 组件分类

#### 1. 按钮组件
- **PrimaryButton** - 主要操作按钮（蓝色）
- **SecondaryButton** - 次要操作按钮（白色带边框）
- **GhostButton** - 幽灵按钮（透明背景）
- **DangerButton** - 危险操作按钮（红色）
- **SuccessButton** - 成功操作按钮（绿色）
- **IconButton** - 带图标的按钮

#### 2. 输入组件
- **InputWithLabel** - 带标签的输入框
- **SelectBox** - 下拉选择框
- **LineEdit** - 标准输入框（带占位符）
- **ComboBox** - 标准下拉框

#### 3. 卡片组件
- **DataCard** - 数据卡片（显示数值和单位）
- **InfoCard** - 信息卡片（显示文本信息）
- **ActionCard** - 操作卡片（包含按钮）

#### 4. 表格组件
- **DeviceTable** - 设备列表表格
- **DataTable** - 通用数据表格

#### 5. 状态组件
- **StatusLabel** - 状态标签
- **StatusIndicator** - 状态指示器（圆点）
- **StatusBadge** - 状态徽章
- **AnimatedStatusBadge** - 带呼吸灯的状态徽章

#### 6. 可视化组件
- **ModernGauge** - 动态圆形仪表盘（带发光渐变）
- **RealtimeChart** - 实时趋势图（基于pyqtgraph）
- **TrendChart** - 趋势图

#### 7. 开关组件
- **Switch** - 开关控件
- **Checkbox** - 复选框

---

## 3. 重构目标

### 3.1 代码质量提升
- ✅ 减少代码重复
- ✅ 提高可维护性
- ✅ 统一样式系统
- ✅ 改善类型安全

### 3.2 用户体验优化
- ✅ 统一的视觉风格
- ✅ 更好的交互反馈
- ✅ 流畅的动画效果
- ✅ 响应式布局

### 3.3 开发效率提升
- ✅ 快速构建UI
- ✅ 减少样式调试时间
- ✅ 便于团队协作
- ✅ 简化新功能开发

---

## 4. 重构步骤

### 步骤1：分析现有UI代码

```
请帮我分析项目的UI代码结构：

## 任务要求
1. 读取并分析 `ui/main_window_v2.py` 文件
2. 识别所有可以替换为组件库组件的原生控件
3. 列出需要创建的组件文件
4. 给出重构优先级和方案

## 分析重点
- 按钮使用情况
- 输入控件使用情况
- 样式定义方式
- 布局结构

## 输出要求
- 详细的分析报告
- 可替换组件清单
- 重构优先级排序
- 潜在风险和解决方案
```

### 步骤2：创建组件库模块

```
请帮我创建完整的UI组件库模块：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 参考文档：Python UI 组件库完整方案.md

## 创建任务
1. 创建 `ui/widgets/` 目录（如果不存在）
2. 创建以下组件文件：
   - buttons.py - 按钮组件
   - inputs.py - 输入组件
   - cards.py - 卡片组件
   - tables.py - 表格组件
   - status.py - 状态组件
   - visual.py - 可视化组件
   - switches.py - 开关组件
3. 创建 `ui/styles/` 目录（如果不存在）
4. 创建样式文件：
   - base.qss - 基础样式
   - light.qss - 浅色主题
   - dark.qss - 深色主题
5. 创建 `ui/core/` 目录（如果不存在）
6. 创建主题管理器：
   - theme.py - 主题加载和管理

## 实现要求
- 严格遵循参考文档中的API设计
- 添加完整的类型提示
- 添加详细的文档字符串
- 确保线程安全
- 支持主题切换

## 代码质量
- 符合 PEP 8 规范
- 添加必要的注释
- 处理边界情况
- 提供错误处理
```

### 步骤3：重构主窗口

```
请帮我重构主窗口，使用新的UI组件库：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 主窗口文件：ui/main_window_v2.py
- 组件库文档：Python UI 组件库完整方案.md

## 重构要求

### 1. 按钮替换
将所有 QPushButton 替换为组件库按钮：
- "确定" → PrimaryButton
- "取消" → SecondaryButton
- "删除" → DangerButton
- "保存" → SuccessButton
- "编辑" → SecondaryButton
- "连接" → SuccessButton
- "断开" → DangerButton

### 2. 输入控件替换
将输入控件替换为组件库组件：
- QLineEdit → LineEdit
- 带标签的输入 → InputWithLabel
- QComboBox → ComboBox

### 3. 表格替换
- QTableWidget → DeviceTable 或 DataTable
- 确保表格样式统一

### 4. 样式统一
- 移除所有内联样式
- 使用 AppStyles 中的统一样式
- 确保主题切换正常工作

### 5. 状态显示优化
- 使用 StatusBadge 或 AnimatedStatusBadge
- 统一状态颜色映射
- 添加状态动画效果

## 功能保持
- 保持所有现有功能不变
- 保持所有信号槽连接
- 保持所有数据验证逻辑
- 保持所有事件处理

## 代码质量要求
- 添加类型提示
- 添加文档字符串
- 符合 PEP 8 规范
- 添加必要的注释

## 输出要求
- 完整的重构代码
- 详细的变更说明
- 兼容性测试报告
```

### 步骤4：重构对话框

```
请帮我批量重构项目中的所有对话框：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：Python UI 组件库完整方案.md

## 需要重构的对话框文件
1. ui/add_device_dialog.py
2. ui/batch_operations_dialog.py
3. ui/data_export_dialog.py
4. ui/device_type_dialogs.py
5. ui/log_viewer_dialog.py
6. ui/register_config_dialog.py
7. ui/dialogs/settings_dialog.py

## 重构任务（对每个对话框执行）

### 1. 按钮标准化
- 主操作按钮 → PrimaryButton
- 次要操作按钮 → SecondaryButton
- 危险操作 → DangerButton
- 成功操作 → SuccessButton

### 2. 输入控件统一
- 使用 InputWithLabel 替换带标签的输入框
- 使用 SelectBox 替换下拉框
- 确保占位符正确设置

### 3. 样式统一
- 移除所有内联样式
- 使用组件库的统一样式
- 确保深色/浅色主题一致

### 4. 布局优化
- 使用 Qt Layout（QVBoxLayout / QHBoxLayout）
- 合理设置 spacing 和 margins
- 确保窗口可缩放

## 功能保持
- 保持所有现有功能不变
- 保持所有信号槽连接
- 保持所有数据验证逻辑
- 保持所有事件处理

## 代码质量
- 添加类型提示
- 添加文档字符串
- 符合 PEP 8 规范
- 添加必要的注释

## 执行顺序
1. 先重构第一个对话框
2. 测试确认无误后
3. 再重构下一个对话框
4. 依此类推

## 输出要求
- 每个对话框的重构代码
- 详细的变更说明
- 测试验证报告
```

### 步骤5：集成高级可视化组件

```
请帮我集成高级可视化组件到项目中：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：Python UI 组件库完整方案.md

## 集成任务

### 1. 创建监控仪表板
创建一个新的监控面板类，集成以下组件：
- ModernGauge - 设备利用率仪表盘
- ModernGauge - 温度仪表盘
- ModernGauge - 压力仪表盘
- AnimatedStatusBadge - 设备状态徽章
- RealtimeChart - 实时趋势图

### 2. 集成到主窗口
- 在主窗口中添加监控仪表板页面
- 使用 QTabWidget 管理多个页面
- 确保数据和信号正确连接

### 3. 数据更新逻辑
- 连接设备管理器的数据更新信号
- 实现定时更新机制
- 添加数据缓存和优化

## 实现要求
- 使用 QTimer 定时更新（1000ms）
- 支持多设备数据展示
- 实现数据平滑动画
- 添加错误处理和日志

## 样式要求
- 所有组件使用统一的深色主题
- 确保响应式布局
- 添加必要的间距和边距

## 输出要求
- 完整的仪表板代码
- 数据集成说明
- 使用示例和文档
```

### 步骤6：主题系统整合

```
请帮我整合主题系统到项目中：

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：Python UI 组件库完整方案.md

## 集成任务

### 1. 创建主题管理器
实现 ThemeManager 类，功能包括：
- 加载和保存主题偏好
- 应用主题到应用程序
- 支持主题切换
- 主题通知信号

### 2. 定义样式常量
在 styles.py 中定义：
- 浅色主题样式
- 深色主题样式
- 基础样式常量
- 颜色常量（成功、警告、错误、主色）

### 3. 主题切换按钮
在状态栏添加主题切换按钮：
- 显示当前主题图标
- 点击切换主题
- 保存用户偏好

### 4. 应用主题到所有组件
- 确保所有组件响应主题变化
- 使用信号通知主题变更
- 实现主题热切换

## 实现要求
- 浅色主题作为默认主题
- 支持深色/浅色主题切换
- 主题设置持久化
- 主题切换平滑过渡

## 输出要求
- 主题管理器完整代码
- 样式定义文件
- 主题切换按钮实现
- 使用文档和示例
```

---

## 5. 代码示例

### 示例1：按钮替换

#### 原始代码
```python
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

class OldDialog(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        btn_ok = QPushButton("确定")
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
            }
        """)

        layout.addWidget(btn_ok)
```

#### 重构后代码
```python
from ui.widgets.buttons import PrimaryButton, SecondaryButton, DangerButton
from PySide6.QtWidgets import QVBoxLayout, QWidget

class NewDialog(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 使用组件库按钮
        btn_ok = PrimaryButton("确定")
        btn_cancel = SecondaryButton("取消")
        btn_delete = DangerButton("删除")

        layout.addWidget(btn_ok)
        layout.addWidget(btn_cancel)
        layout.addWidget(btn_delete)
```

### 示例2：输入控件替换

#### 原始代码
```python
from PySide6.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QWidget

class OldForm(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)

        label = QLabel("设备名称:")
        label.setStyleSheet("color: #E6EDF3;")

        input_field = QLineEdit()
        input_field.setPlaceholderText("请输入设备名称")
        input_field.setStyleSheet("""
            QLineEdit {
                background-color: #111827;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px;
            }
        """)

        layout.addWidget(label)
        layout.addWidget(input_field)
```

#### 重构后代码
```python
from ui.widgets.inputs import InputWithLabel
from PySide6.QtWidgets import QVBoxLayout, QWidget

class NewForm(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 使用组件库输入控件
        name_input = InputWithLabel("设备名称", "请输入设备名称")
        ip_input = InputWithLabel("IP地址", "192.168.0.1")
        port_input = InputWithLabel("端口", "502")

        layout.addWidget(name_input)
        layout.addWidget(ip_input)
        layout.addWidget(port_input)
```

### 示例3：状态显示优化

#### 原始代码
```python
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget

class OldStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)

        status_label = QLabel("状态")
        status_text = QLabel("在线")
        status_text.setStyleSheet("color: #22C55E; font-weight: bold;")

        layout.addWidget(status_label)
        layout.addWidget(status_text)
```

#### 重构后代码
```python
from ui.widgets.status import AnimatedStatusBadge
from PySide6.QtWidgets import QVBoxLayout, QWidget

class NewStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 使用带呼吸灯的状态徽章
        status_badge = AnimatedStatusBadge("在线", "#22C55E")

        layout.addWidget(status_badge)

    def update_status(self, online: bool):
        if online:
            self.status_badge.set_status("在线", "#22C55E")
        else:
            self.status_badge.set_status("离线", "#EF4444")
```

### 示例4：高级可视化组件集成

#### 创建监控仪表板
```python
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from ui.widgets.visual import ModernGauge, AnimatedStatusBadge, RealtimeChart
from PySide6.QtCore import QTimer
import random

class MonitorDashboard(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # 仪表盘区域
        gauge_layout = QHBoxLayout()
        self.utilization_gauge = ModernGauge("利用率", 75, "#2196F3")
        self.temperature_gauge = ModernGauge("温度", 45, "#FF9800")
        self.pressure_gauge = ModernGauge("压力", 60, "#4CAF50")

        gauge_layout.addWidget(self.utilization_gauge)
        gauge_layout.addWidget(self.temperature_gauge)
        gauge_layout.addWidget(self.pressure_gauge)
        layout.addLayout(gauge_layout)

        # 状态徽章
        self.status_badge = AnimatedStatusBadge("正常", "#4CAF50")
        layout.addWidget(self.status_badge)

        # 实时趋势图
        self.chart = RealtimeChart(title="温度实时趋势图", max_points=100)
        layout.addWidget(self.chart)

        # 定时更新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)

    def update_data(self):
        # 更新仪表盘
        self.utilization_gauge.value = random.randint(60, 90)
        self.temperature_gauge.value = random.randint(30, 60)
        self.pressure_gauge.value = random.randint(50, 80)

        # 更新图表
        self.chart.update_data([random.gauss(25, 2) for _ in range(10)])
```

---

## 6. 注意事项

### 6.1 兼容性
- ✅ 确保所有现有功能不受影响
- ✅ 保持所有信号槽连接
- ✅ 保持所有数据验证逻辑
- ✅ 保持所有事件处理

### 6.2 性能优化
- ✅ 避免不必要的重绘
- ✅ 使用数据缓冲减少绘制次数
- ✅ 优化布局计算
- ✅ 合理使用 QTimer

### 6.3 代码质量
- ✅ 添加完整的类型提示
- ✅ 添加详细的文档字符串
- ✅ 符合 PEP 8 规范
- ✅ 添加必要的注释

### 6.4 测试验证
- ✅ 每次重构后立即测试
- ✅ 验证功能完整性
- ✅ 检查主题切换
- ✅ 确保响应式布局

### 6.5 文档更新
- ✅ 更新组件库文档
- ✅ 添加使用示例
- ✅ 记录重构变更
- ✅ 更新 CHANGELOG

---

## 7. 完整AI提示词模板

### 提示词1：分析现有代码

```
我需要分析现有项目的UI代码，准备使用组件库重构。

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 主窗口文件：ui/main_window_v2.py
- 组件库文档：Python UI 组件库完整方案.md

## 分析要求
1. 读取并分析主窗口文件
2. 识别所有可替换的原生控件
3. 列出需要创建的组件
4. 给出重构优先级和方案

## 分析重点
- 按钮使用情况和样式
- 输入控件使用情况和样式
- 表格使用情况和样式
- 样式定义方式

## 输出要求
- 详细的分析报告
- 可替换组件清单
- 重构优先级排序
- 潜在风险和解决方案
```

### 提示词2：创建组件库

```
请帮我创建完整的UI组件库模块，用于重构项目。

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 参考文档：Python UI 组件库完整方案.md

## 创建任务
1. 创建 `ui/widgets/` 目录
2. 创建以下组件文件：
   - buttons.py - 按钮系统
   - inputs.py - 输入控件
   - cards.py - 卡片组件
   - tables.py - 表格组件
   - status.py - 状态组件
   - visual.py - 可视化组件
   - switches.py - 开关组件
3. 创建 `ui/styles/` 目录
4. 创建样式文件：
   - base.qss - 基础样式
   - light.qss - 浅色主题
   - dark.qss - 深色主题

## 实现要求
- 严格遵循参考文档中的API设计
- 添加完整的类型提示
- 添加详细的文档字符串
- 确保线程安全
- 支持主题切换

## 代码质量
- 符合 PEP 8 规范
- 添加必要的注释
- 处理边界情况
- 提供错误处理
```

### 提示词3：重构主窗口

```
请帮我重构主窗口，使用新的UI组件库。

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 主窗口文件：ui/main_window_v2.py
- 组件库文档：Python UI 组件库完整方案.md

## 重构要求

### 1. 按钮替换
将所有 QPushButton 替换为组件库按钮：
- "确定" → PrimaryButton
- "取消" → SecondaryButton
- "删除" → DangerButton
- "保存" → SuccessButton

### 2. 输入控件替换
将输入控件替换为组件库组件：
- QLineEdit → LineEdit
- 带标签的输入 → InputWithLabel
- QComboBox → ComboBox

### 3. 样式统一
- 移除所有内联样式
- 使用 AppStyles 中的统一样式
- 确保主题切换正常工作

### 4. 状态显示优化
- 使用 StatusBadge 或 AnimatedStatusBadge
- 统一状态颜色映射
- 添加状态动画效果

## 功能保持
- 保持所有现有功能不变
- 保持所有信号槽连接
- 保持所有数据验证逻辑
- 保持所有事件处理

## 代码质量要求
- 添加类型提示
- 添加文档字符串
- 符合 PEP 8 规范
- 添加必要的注释

## 输出要求
- 完整的重构代码
- 详细的变更说明
- 兼容性测试报告
```

### 提示词4：批量重构对话框

```
请帮我批量重构项目中的所有对话框，使用UI组件库。

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：Python UI 组件库完整方案.md

## 需要重构的对话框文件
1. ui/add_device_dialog.py
2. ui/batch_operations_dialog.py
3. ui/data_export_dialog.py
4. ui/device_type_dialogs.py
5. ui/log_viewer_dialog.py
6. ui/register_config_dialog.py
7. ui/dialogs/settings_dialog.py

## 重构任务（对每个对话框执行）

### 1. 按钮标准化
- 主操作按钮 → PrimaryButton
- 次要操作按钮 → SecondaryButton
- 危险操作 → DangerButton
- 成功操作 → SuccessButton

### 2. 输入控件统一
- 使用 InputWithLabel 替换带标签的输入框
- 使用 SelectBox 替换下拉框
- 确保占位符正确设置

### 3. 样式统一
- 移除所有内联样式
- 使用组件库的统一样式
- 确保深色/浅色主题一致

## 功能保持
- 保持所有现有功能不变
- 保持所有信号槽连接
- 保持所有数据验证逻辑
- 保持所有事件处理

## 执行顺序
1. 先重构第一个对话框
2. 测试确认无误后
3. 再重构下一个对话框
4. 依此类推

## 输出要求
- 每个对话框的重构代码
- 详细的变更说明
- 测试验证报告
```

### 提示词5：集成高级可视化组件

```
请帮我集成高级可视化组件到项目中。

## 项目信息
- 项目路径：e:\下载\app\equipment management
- 组件库文档：Python UI 组件库完整方案.md

## 集成任务

### 1. 创建监控仪表板
创建一个新的监控面板类，集成以下组件：
- ModernGauge - 设备利用率仪表盘
- AnimatedStatusBadge - 设备状态徽章
- RealtimeChart - 实时趋势图

### 2. 集成到主窗口
- 在主窗口中添加监控仪表板页面
- 使用 QTabWidget 管理多个页面
- 确保数据和信号正确连接

### 3. 数据更新逻辑
- 连接设备管理器的数据更新信号
- 实现定时更新机制
- 添加数据缓存和优化

## 实现要求
- 使用 QTimer 定时更新（1000ms）
- 支持多设备数据展示
- 实现数据平滑动画
- 添加错误处理和日志

## 样式要求
- 所有组件使用统一的深色主题
- 确保响应式布局
- 添加必要的间距和边距

## 输出要求
- 完整的仪表板代码
- 数据集成说明
- 使用示例和文档
```

---

## 8. 推荐工作流程

### 阶段1：准备阶段
1. 阅读组件库文档
2. 分析现有UI代码
3. 制定重构计划

### 阶段2：基础重构
1. 创建组件库模块
2. 重构主窗口
3. 重构对话框（逐个进行）
4. 每次重构后测试

### 阶段3：高级功能
1. 集成高级可视化组件
2. 实现主题系统
3. 优化性能和动画

### 阶段4：验证和文档
1. 全面测试功能
2. 更新文档
3. 记录变更日志
4. 准备发布

---

## 9. 常见问题

### Q: 重构会影响现有功能吗？

**A:** 不会。重构的目标是提升代码质量，不改变功能逻辑。所有现有功能都会保持不变。

### Q: 如何确保兼容性？

**A:**
1. 保持所有信号槽连接
2. 保持所有数据验证逻辑
3. 保持所有事件处理
4. 每次重构后立即测试
5. 进行回归测试

### Q: 组件不够用怎么办？

**A:** 可以基于现有组件创建自定义组件，参考组件库文档中的实现方式。

### Q: 如何处理样式冲突？

**A:**
1. 移除所有内联样式
2. 使用统一的样式系统
3. 使用 objectName 区分组件
4. 通过主题管理器统一样式

### Q: 性能会有影响吗？

**A:** 不会。组件库经过优化，使用组件库通常可以提升性能。

---

**文档版本**: v1.0.0
**最后更新**: 2026-03-28
**维护者**: 开发团队
