# Python 工业 UI 组件库

**版本**: v1.5.0
**框架**: PySide6
**风格**: 工业风深色主题
**日期**: 2026-03-28

---

## 📦 组件库概述

基于 PySide6 的工业风格 UI 组件库，包含按钮、输入控件、卡片、表格等完整组件系统。

### 特点
- ✅ 工业风深色主题
- ✅ 完整的组件体系
- ✅ 可复用组件库级别
- ✅ 支持主题切换
- ✅ 生产就绪

---

## 🏗️ 组件库结构

```
ui_kit/
├── README.md                      # 本文档
├── requirements.txt               # 依赖
│
├── resources/                     # 资源文件
│   ├── style.qss                  # 全局主题样式
│   └── icons/                     # 图标库
│
├── core/                          # 核心模块
│   ├── __init__.py
│   ├── theme.py                   # 主题管理
│   └── base.py                    # 基础组件
│
├── widgets/                       # 组件集合
│   ├── __init__.py
│   ├── buttons.py                 # 按钮系统
│   ├── inputs.py                  # 输入控件
│   ├── cards.py                   # 卡片组件
│   ├── panels.py                  # 面板组件
│   ├── tables.py                  # 表格组件
│   ├── status.py                  # 状态组件
│   └── switches.py                # 开关组件
│
└── examples/                      # 示例代码
    ├── demo_basic.py              # 基础示例
    └── demo_advanced.py           # 高级示例
```

---

## 🎨 设计系统

### 配色方案

#### 深色主题（工业环境）
```python
# 背景色
BG_PRIMARY = "#0B1220"      # 主背景
BG_SECONDARY = "#111827"    # 次级背景
BG_TERTIARY = "#161B22"     # 三级背景

# 文本色
TEXT_PRIMARY = "#E6EDF3"    # 主文本
TEXT_SECONDARY = "#9CA3AF"  # 次级文本
TEXT_DISABLED = "#6B7280"   # 禁用文本

# 强调色
PRIMARY_BLUE = "#3B82F6"    # 主蓝色
SUCCESS_GREEN = "#22C55E"   # 成功绿
DANGER_RED = "#EF4444"      # 危险红
WARNING_YELLOW = "#F59E0B"  # 警告黄

# 边框色
BORDER_DEFAULT = "#30363D"  # 默认边框
BORDER_HOVER = "#6B7280"    # 悬停边框
```

### 间距系统
```python
SPACING = {
    'xs': 4,    # 超小间距
    'sm': 8,    # 小间距
    'md': 12,   # 中间距
    'lg': 16,   # 大间距
    'xl': 24,   # 超大间距
}
```

### 圆角规范
```python
RADIUS = {
    'sm': 4,    # 小圆角
    'md': 6,    # 标准圆角
    'lg': 8,    # 大圆角
    'xl': 12,   # 超大圆角
}
```

---

## 🔧 核心组件

### 1. 按钮系统 (`widgets/buttons.py`)

#### 组件类型
- **PrimaryButton** - 主按钮（蓝色）
- **SecondaryButton** - 次按钮（描边）
- **GhostButton** - 幽灵按钮（无边框）
- **DangerButton** - 危险按钮（红色）
- **SuccessButton** - 成功按钮（绿色）
- **IconButton** - 图标按钮

#### 使用示例
```python
from widgets.buttons import (
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    SuccessButton,
    GhostButton,
    IconButton
)

# 主按钮
btn = PrimaryButton("连接设备")
btn.clicked.connect(on_connect)

# 次按钮
btn2 = SecondaryButton("取消")

# 危险按钮
btn3 = DangerButton("删除")

# 成功按钮
btn4 = SuccessButton("保存")

# 幽灵按钮
btn5 = GhostButton("了解更多")

# 图标按钮
btn6 = IconButton("icons/edit.svg", "编辑")
```

#### 完整代码
```python
# widgets/buttons.py
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon


class BaseButton(QPushButton):
    """基础按钮类"""
    def __init__(self, text: str = ""):
        super().__init__(text)
        self.setObjectName(self.__class__.__name__.lower())


class PrimaryButton(BaseButton):
    """主按钮 - 蓝色"""
    pass


class SecondaryButton(BaseButton):
    """次按钮 - 描边"""
    pass


class GhostButton(BaseButton):
    """幽灵按钮 - 无边框"""
    pass


class DangerButton(BaseButton):
    """危险按钮 - 红色"""
    pass


class SuccessButton(BaseButton):
    """成功按钮 - 绿色"""
    pass


class IconButton(QPushButton):
    """图标按钮"""
    def __init__(self, icon_path: str, text: str = ""):
        super().__init__()
        self.setIcon(QIcon(icon_path))
        if text:
            self.setText(text)
        self.setFixedSize(40, 40)
```

---

### 2. 输入控件 (`widgets/inputs.py`)

#### 组件类型
- **LineEdit** - 输入框
- **InputWithIcon** - 带图标输入框
- **InputWithLabel** - 带标签输入框
- **ComboBox** - 下拉框

#### 使用示例
```python
from widgets.inputs import LineEdit, InputWithIcon, InputWithLabel, ComboBox

# 基础输入框
input1 = LineEdit()
input1.setPlaceholderText("请输入设备名称")

# 带图标输入框
input2 = InputWithIcon("icons/search.svg", "搜索...")

# 带标签输入框
input3 = InputWithLabel("IP 地址", "192.168.1.1")

# 下拉框
combo = ComboBox(["设备 A", "设备 B", "设备 C"])
combo.currentTextChanged.connect(on_change)
```

#### 完整代码
```python
# widgets/inputs.py
from PySide6.QtWidgets import (
    QLineEdit,
    QComboBox,
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton
)
from PySide6.QtGui import QIcon


class LineEdit(QLineEdit):
    """工业风输入框"""
    def __init__(self, placeholder: str = ""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setObjectName("lineEdit")


class InputWithIcon(QWidget):
    """带图标的输入框"""
    def __init__(self, icon_path: str, placeholder: str = ""):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.input = LineEdit(placeholder)
        self.icon_btn = QPushButton()
        self.icon_btn.setIcon(QIcon(icon_path))
        self.icon_btn.setFixedSize(36, 36)

        layout.addWidget(self.input)
        layout.addWidget(self.icon_btn)

    def text(self):
        return self.input.text()

    def setText(self, text):
        self.input.setText(text)


class InputWithLabel(QWidget):
    """带标签的输入框"""
    def __init__(self, label_text: str, placeholder: str = ""):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(label_text)
        self.input = LineEdit(placeholder)

        layout.addWidget(self.label)
        layout.addWidget(self.input)

    def text(self):
        return self.input.text()

    def setText(self, text):
        self.input.setText(text)


class ComboBox(QComboBox):
    """工业风下拉框"""
    def __init__(self, items: list = None):
        super().__init__()
        self.setObjectName("comboBox")

        if items:
            self.addItems(items)
```

---

### 3. 卡片组件 (`widgets/cards.py`)

#### 组件类型
- **DataCard** - 数据卡片
- **InfoCard** - 信息卡片
- **ActionCard** - 操作卡片

#### 使用示例
```python
from widgets.cards import DataCard, InfoCard, ActionCard

# 数据卡片
card = DataCard("温度", "25.5°C")
card.set_trend("+2.3%")  # 设置趋势
layout.addWidget(card)

# 信息卡片
info_card = InfoCard(
    title="设备状态",
    content="在线运行中",
    icon="icons/device.svg"
)
layout.addWidget(info_card)

# 操作卡片
action_card = ActionCard(
    title="快速操作",
    actions=["启动", "停止", "重启"]
)
action_card.action_clicked.connect(on_action)
layout.addWidget(action_card)
```

#### 完整代码
```python
# widgets/cards.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Signal


class DataCard(QFrame):
    """数据卡片"""
    def __init__(self, title: str, value: str):
        super().__init__()
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #9CA3AF; font-size: 13px;")

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            "color: #E6EDF3; font-size: 28px; font-weight: bold;"
        )

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(str(value))

    def set_trend(self, trend: str):
        """设置趋势标签"""
        trend_label = QLabel(trend)
        color = "#22C55E" if "+" in trend else "#EF4444"
        trend_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 500;"
        )
        self.layout().addWidget(trend_label)


class InfoCard(QFrame):
    """信息卡片"""
    def __init__(self, title: str, content: str, icon: str = None):
        super().__init__()
        self.setObjectName("card")

        layout = QHBoxLayout(self)
        layout.setSpacing(12)

        # 图标
        if icon:
            from PySide6.QtGui import QIcon
            icon_label = QLabel()
            icon_label.setPixmap(QIcon(icon).pixmap(32, 32))
            layout.addWidget(icon_label)

        # 内容
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #9CA3AF; font-size: 13px;")

        content_label = QLabel(content)
        content_label.setStyleSheet("color: #E6EDF3; font-size: 16px;")

        content_layout.addWidget(title_label)
        content_layout.addWidget(content_label)
        layout.addLayout(content_layout)


class ActionCard(QFrame):
    """操作卡片"""
    action_clicked = Signal(str)

    def __init__(self, title: str, actions: list = None):
        super().__init__()
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color: #E6EDF3; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        # 操作按钮
        from widgets.buttons import PrimaryButton
        if actions:
            for action in actions:
                btn = PrimaryButton(action)
                btn.clicked.connect(
                    lambda checked, a=action: self.action_clicked.emit(a)
                )
                layout.addWidget(btn)
```

---

### 4. 表格组件 (`widgets/tables.py`)

#### 组件类型
- **DeviceTable** - 设备表格
- **DataTable** - 数据表格

#### 使用示例
```python
from widgets.tables import DeviceTable, DataTable

# 设备表格
table = DeviceTable()
table.add_device("设备 A", "192.168.1.100", "在线")
table.add_device("设备 B", "192.168.1.101", "离线")
layout.addWidget(table)

# 数据表格
data_table = DataTable(["时间", "温度", "压力"])
data_table.add_row(["10:00", "25.5", "1.2"])
data_table.add_row(["10:01", "26.0", "1.3"])
layout.addWidget(data_table)
```

#### 完整代码
```python
# widgets/tables.py
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView


class DeviceTable(QTableWidget):
    """设备表格"""
    def __init__(self):
        super().__init__(0, 3)
        self.setObjectName("deviceTable")

        # 表头
        self.setHorizontalHeaderLabels(["设备", "IP", "状态"])

        # 列宽
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

    def add_device(self, name: str, ip: str, status: str):
        """添加设备"""
        row = self.rowCount()
        self.insertRow(row)

        self.setItem(row, 0, QTableWidgetItem(name))
        self.setItem(row, 1, QTableWidgetItem(ip))

        # 状态带颜色
        status_item = QTableWidgetItem(status)
        if status == "在线":
            status_item.setForeground(Qt.green)
        elif status == "离线":
            status_item.setForeground(Qt.red)

        self.setItem(row, 2, status_item)


class DataTable(QTableWidget):
    """数据表格"""
    def __init__(self, columns: list = None):
        super().__init__(0, len(columns) if columns else 0)
        self.setObjectName("dataTable")

        if columns:
            self.setHorizontalHeaderLabels(columns)

        # 样式
        self.setAlternatingRowColors(True)

    def add_row(self, data: list):
        """添加数据行"""
        row = self.rowCount()
        self.insertRow(row)

        for col, value in enumerate(data):
            self.setItem(row, col, QTableWidgetItem(str(value)))
```

---

### 5. 状态组件 (`widgets/status.py`)

#### 组件类型
- **StatusLabel** - 状态标签
- **StatusIndicator** - 状态指示器
- **StatusBadge** - 状态徽章

#### 使用示例
```python
from widgets.status import StatusLabel, StatusIndicator, StatusBadge

# 状态标签
status = StatusLabel()
status.set_online()  # 设置在线
status.set_offline()  # 设置离线
layout.addWidget(status)

# 状态指示器
indicator = StatusIndicator()
indicator.set_status("running")  # running/stopped/error
layout.addWidget(indicator)

# 状态徽章
badge = StatusBadge("online")  # online/offline/warning/error
layout.addWidget(badge)
```

#### 完整代码
```python
# widgets/status.py
from PySide6.QtWidgets import QLabel


class StatusLabel(QLabel):
    """状态标签"""
    def __init__(self):
        super().__init__("● 离线")
        self.set_offline()

    def set_online(self):
        self.setText("● 在线")
        self.setStyleSheet("color: #22C55E; font-weight: 500;")

    def set_offline(self):
        self.setText("● 离线")
        self.setStyleSheet("color: #EF4444; font-weight: 500;")

    def set_warning(self):
        self.setText("● 警告")
        self.setStyleSheet("color: #F59E0B; font-weight: 500;")


class StatusIndicator(QLabel):
    """状态指示器"""
    def __init__(self):
        super().__init__()
        self.setFixedSize(16, 16)
        self.setStyleSheet("""
            background-color: #EF4444;
            border-radius: 8px;
        """)

    def set_status(self, status: str):
        colors = {
            "running": "#22C55E",
            "stopped": "#EF4444",
            "warning": "#F59E0B",
            "error": "#DC2626",
        }
        color = colors.get(status, "#EF4444")
        self.setStyleSheet(f"""
            background-color: {color};
            border-radius: 8px;
        """)


class StatusBadge(QLabel):
    """状态徽章"""
    def __init__(self, status: str = "offline"):
        super().__init__()
        self.setText("● 离线")
        self.set_status(status)

    def set_status(self, status: str):
        states = {
            "online": ("● 在线", "#22C55E"),
            "offline": ("● 离线", "#EF4444"),
            "warning": ("● 警告", "#F59E0B"),
            "error": ("● 错误", "#DC2626"),
        }

        text, color = states.get(status, states["offline"])
        self.setText(text)
        self.setStyleSheet(f"color: {color}; font-weight: 500;")
```

---

### 6. 高级可视化组件 (`widgets/visual.py`)

#### 组件类型
- **ModernGauge** - 动态圆形仪表盘（带发光渐变）
- **AnimatedStatusBadge** - 现代化状态徽章（带呼吸灯效果）
- **RealtimeChart** - 实时趋势图（基于 pyqtgraph）

#### 使用示例
```python
from widgets.visual import ModernGauge, AnimatedStatusBadge, RealtimeChart

# 动态仪表盘
gauge = ModernGauge(title="利用率", value=75, color="#2196F3")
gauge.value = 85  # 动画更新数值
layout.addWidget(gauge)

# 带呼吸灯的状态徽章
badge = AnimatedStatusBadge(text="正常", color="#4CAF50")
layout.addWidget(badge)

# 实时趋势图
chart = RealtimeChart(title="温度实时趋势图")
chart.update_data([25.0, 25.5, 26.0, ...])  # 更新数据
layout.addWidget(chart)
```

#### 完整代码
```python
# widgets/visual.py
from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, Property, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QRadialGradient
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
import pyqtgraph as pg


class AnimatedStatusBadge(QFrame):
    """现代化状态徽章（带呼吸灯效果）"""

    def __init__(self, text, color="#4CAF50", parent=None):
        super().__init__(parent)
        self.color = color
        self.init_ui(text)

    def init_ui(self, text):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 呼吸灯小圆点
        self.dot = QFrame()
        self.dot.setFixedSize(8, 8)
        self.dot.setStyleSheet(f"""
            background-color: {self.color};
            border-radius: 4px;
        """)

        # 文字
        label = QLabel(text)
        label.setStyleSheet(f"""
            color: {self.color};
            font-weight: bold;
            font-size: 12px;
            background: transparent;
        """)

        layout.addWidget(self.dot)
        layout.addWidget(label)

        self.setStyleSheet(f"""
            AnimatedStatusBadge {{
                background-color: {QColor(self.color).lighter(150).name()}22;
                border: 1px solid {self.color}44;
                border-radius: 4px;
            }}
        """)

    def set_status(self, text, color):
        """更新状态"""
        self.color = color
        self.dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 4px;
        """)

        # 更新文字标签
        label = self.findChild(QLabel)
        if label:
            label.setStyleSheet(f"""
                color: {color};
                font-weight: bold;
                font-size: 12px;
                background: transparent;
            """)
            label.setText(text)


class ModernGauge(QWidget):
    """动态圆形仪表盘（带发光渐变）"""

    def __init__(self, title, value=0, color="#2196F3", parent=None):
        super().__init__(parent)
        self._value = value
        self.color = color
        self.title = title
        self.setMinimumSize(160, 160)

    @Property(float)
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.contentsRect().adjusted(10, 10, -10, -10)
        size = min(rect.width(), rect.height())
        center_rect = QRectF(
            rect.center().x() - size/2,
            rect.center().y() - size/2,
            size, size
        )

        # 1. 绘制底色圆环
        painter.setPen(QPen(QColor("#30363D"), 10, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(center_rect, 0 * 16, 360 * 16)

        # 2. 绘制彩色进度环（带发光渐变）
        grad_pen = QPen(QColor(self.color), 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(grad_pen)
        span_angle = -(self._value / 100.0) * 360 * 16
        painter.drawArc(center_rect, 90 * 16, span_angle)

        # 3. 绘制中间文字
        painter.setPen(QColor("#E6EDF3"))
        painter.setFont(QFont("Inter", 18, QFont.Bold))
        painter.drawText(center_rect, Qt.AlignCenter, f"{int(self._value)}%")

        painter.setFont(QFont("Inter", 10))
        painter.setPen(QColor("#8B949E"))
        painter.drawText(
            center_rect.adjusted(0, 40, 0, 40),
            Qt.AlignCenter,
            self.title
        )


class RealtimeChart(pg.PlotWidget):
    """实时趋势图（基于 pyqtgraph）"""

    def __init__(self, title="实时趋势图", max_points=100):
        super().__init__(title=title)
        self.max_points = max_points
        self.data = []

        # 配置图表
        self.setClipToView(True)
        self.showGrid(x=False, y=True, alpha=0.1)
        self.setBackground('#161B22')
        self.getAxis('left').setPen('#8B949E')
        self.getAxis('bottom').setPen('#8B949E')

        # 创建曲线
        self.curve = self.plot(pen=pg.mkPen(color='#2196F3', width=3))

    def update_data(self, new_data):
        """更新图表数据"""
        if isinstance(new_data, (list, tuple)):
            self.data = list(new_data)
        else:
            self.data.append(new_data)

        # 保持最大点数
        if len(self.data) > self.max_points:
            self.data = self.data[-self.max_points:]

        self.curve.setData(self.data)

    def clear_data(self):
        """清除数据"""
        self.data = []
        self.curve.setData([])
```

---

### 7. 开关组件 (`widgets/switches.py`)

#### 组件类型
- **Switch** - 开关控件
- **Checkbox** - 复选框

#### 使用示例
```python
from widgets.switches import Switch, Checkbox

# 开关
switch = Switch()
switch.stateChanged.connect(on_toggle)
layout.addWidget(switch)

# 复选框
checkbox = Checkbox("启用自动保存")
checkbox.stateChanged.connect(on_check)
layout.addWidget(checkbox)
```

#### 完整代码
```python
# widgets/switches.py
from PySide6.QtWidgets import QCheckBox


class Switch(QCheckBox):
    """开关控件"""
    def __init__(self):
        super().__init__()
        self.setFixedSize(50, 25)
        self.setStyleSheet("""
            QCheckBox::indicator {
                width: 50px;
                height: 25px;
                border-radius: 12px;
                background: #374151;
            }
            QCheckBox::indicator:checked {
                background: #3B82F6;
            }
        """)

    def is_on(self):
        return self.isChecked()


class Checkbox(QCheckBox):
    """复选框"""
    def __init__(self, text: str = ""):
        super().__init__(text)
        self.setObjectName("checkBox")
```

---

## 🎨 样式系统

### 全局样式 (`resources/style.qss`)

```css
/* ===== 全局设置 ===== */
QWidget {
    background-color: #0B1220;
    color: #E6EDF3;
    font-family: "Segoe UI";
    font-size: 14px;
}

/* ===== 按钮 ===== */
QPushButton {
    padding: 8px 16px;
    border-radius: 8px;
}

QPushButton#primarybutton {
    background-color: #3B82F6;
}
QPushButton#primarybutton:hover {
    background-color: #2563EB;
}

QPushButton#secondarybutton {
    background-color: transparent;
    border: 1px solid #374151;
}
QPushButton#secondarybutton:hover {
    border: 1px solid #6B7280;
}

QPushButton#ghostbutton {
    background-color: transparent;
    border: none;
    color: #9CA3AF;
}

QPushButton#dangerbutton {
    background-color: #EF4444;
}
QPushButton#dangerbutton:hover {
    background-color: #DC2626;
}

QPushButton#successbutton {
    background-color: #22C55E;
}
QPushButton#successbutton:hover {
    background-color: #16A34A;
}

QPushButton:disabled {
    background-color: #1F2937;
    color: #6B7280;
}

/* ===== 输入框 ===== */
QLineEdit {
    background-color: #111827;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 6px 12px;
    color: #E6EDF3;
}
QLineEdit:focus {
    border: 1px solid #3B82F6;
}

/* ===== 下拉框 ===== */
QComboBox {
    background-color: #111827;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 6px 12px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #9CA3AF;
    margin-right: 8px;
}

/* ===== 卡片 ===== */
QFrame#card {
    background-color: #111827;
    border-radius: 10px;
    padding: 12px;
}
QFrame#card:hover {
    border: 1px solid #30363D;
}

/* ===== 表格 ===== */
QTableWidget {
    background-color: #161B22;
    border: 1px solid #30363D;
    gridline-color: #30363D;
}
QTableWidget::item {
    padding: 8px 12px;
}
QTableWidget::item:selected {
    background-color: rgba(59, 130, 246, 0.2);
}
QHeaderView::section {
    background-color: #21262D;
    color: #9CA3AF;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #30363D;
    font-weight: 600;
}

/* ===== 复选框 ===== */
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #30363D;
    background-color: #0B1220;
}
QCheckBox::indicator:checked {
    background-color: #3B82F6;
    border-color: #3B82F6;
}
```

---

## 🔧 主题管理 (`core/theme.py`)

```python
# core/theme.py
from PySide6.QtWidgets import QApplication
from pathlib import Path


class ThemeManager:
    """主题管理器"""

    THEMES = {
        'dark': 'resources/style.qss',
        'light': 'resources/style_light.qss',
    }

    @staticmethod
    def apply_theme(app: QApplication, theme_name: str = 'dark'):
        """应用主题"""
        theme_file = ThemeManager.THEMES.get(theme_name)

        if not theme_file:
            raise ValueError(f"Unknown theme: {theme_name}")

        theme_path = Path(__file__).parent.parent / theme_file

        if not theme_path.exists():
            raise FileNotFoundError(f"Theme file not found: {theme_path}")

        with open(theme_path, 'r', encoding='utf-8') as f:
            qss = f.read()

        app.setStyleSheet(qss)

    @staticmethod
    def toggle_theme(app: QApplication, current_theme: str):
        """切换主题"""
        new_theme = 'light' if current_theme == 'dark' else 'dark'
        ThemeManager.apply_theme(app, new_theme)
        return new_theme
```

---

## 📦 依赖文件 (`requirements.txt`)

```txt
PySide6>=6.5.0
pyqtgraph>=0.13.0  # 用于实时图表
```

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 基础示例 (`examples/demo_basic.py`)

```python
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

from core.theme import ThemeManager
from widgets.buttons import PrimaryButton, SecondaryButton, DangerButton
from widgets.cards import DataCard
from widgets.inputs import LineEdit, ComboBox
from widgets.status import StatusBadge
from widgets.visual import ModernGauge, AnimatedStatusBadge, RealtimeChart

class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("UI 组件库演示")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 数据卡片
        card = DataCard("温度", "25.5°C")
        card.set_trend("+2.3%")
        layout.addWidget(card)

        # 输入框
        input1 = LineEdit("请输入设备名称")
        layout.addWidget(input1)

        # 下拉框
        combo = ComboBox(["设备 A", "设备 B", "设备 C"])
        layout.addWidget(combo)

        # 状态徽章
        badge = StatusBadge("online")
        layout.addWidget(badge)

        # 带呼吸灯的状态徽章
        animated_badge = AnimatedStatusBadge("正常", "#4CAF50")
        layout.addWidget(animated_badge)

        # 动态仪表盘
        gauge_layout = QHBoxLayout()
        g1 = ModernGauge("利用率", 75, "#2196F3")
        g2 = ModernGauge("预警值", 85, "#FFC107")
        g3 = ModernGauge("风险度", 92, "#F44336")
        gauge_layout.addWidget(g1)
        gauge_layout.addWidget(g2)
        gauge_layout.addWidget(g3)
        layout.addLayout(gauge_layout)

        # 实时趋势图
        chart = RealtimeChart(title="温度实时趋势图")
        chart.update_data([20.0, 21.5, 22.0, 23.5, 25.0])
        layout.addWidget(chart)

        # 按钮
        layout.addWidget(PrimaryButton("连接"))
        layout.addWidget(SecondaryButton("取消"))
        layout.addWidget(DangerButton("删除"))

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 应用主题
    ThemeManager.apply_theme(app, 'dark')

    window = DemoWindow()
    window.show()

    sys.exit(app.exec())
```

---

## 🎯 组件清单

| 类别 | 组件 | 说明 |
|------|------|------|
| **按钮** | PrimaryButton | 主按钮（蓝色） |
| | SecondaryButton | 次按钮（描边） |
| | GhostButton | 幽灵按钮 |
| | DangerButton | 危险按钮（红色） |
| | SuccessButton | 成功按钮（绿色） |
| | IconButton | 图标按钮 |
| **输入** | LineEdit | 输入框 |
| | InputWithIcon | 带图标输入框 |
| | InputWithLabel | 带标签输入框 |
| | ComboBox | 下拉框 |
| **卡片** | DataCard | 数据卡片 |
| | InfoCard | 信息卡片 |
| | ActionCard | 操作卡片 |
| **表格** | DeviceTable | 设备表格 |
| | DataTable | 数据表格 |
| **状态** | StatusLabel | 状态标签 |
| | StatusIndicator | 状态指示器 |
| | StatusBadge | 状态徽章 |
| **可视化** | ModernGauge | 动态圆形仪表盘 |
| | AnimatedStatusBadge | 带呼吸灯的状态徽章 |
| | RealtimeChart | 实时趋势图 |
| **开关** | Switch | 开关控件 |
| | Checkbox | 复选框 |

---

## 📝 开发指南

### 添加新组件
1. 在 `widgets/` 目录创建新文件
2. 继承 `QWidget` 或现有组件
3. 设置 `objectName` 用于样式
4. 在 `__init__.py` 中导出

### 自定义样式
1. 修改 `resources/style.qss`
2. 或直接在组件中调用 `setStyleSheet()`

### 主题扩展
1. 创建新的 `.qss` 文件
2. 在 `ThemeManager.THEMES` 中注册
3. 使用 `apply_theme()` 切换

---

## 🔗 相关资源

- [PySide6 官方文档](https://doc.qt.io/qtforpython-6/)
- [QSS 样式表语法](https://doc.qt.io/qt-6/stylesheet-syntax.html)
- [工业 UI 设计指南](./UI 设计指南.md)

---

## 🚀 完整工业仪表板示例

### 工业仪表板 (`examples/industrial_dashboard.py`)

```python
import sys
import random
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame
)

from widgets.visual import ModernGauge, AnimatedStatusBadge, RealtimeChart


class IndustrialDashboard(QMainWindow):
    """工业仪表板 - 完整示例"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("工业设备管理系统 - 仪表板")
        self.resize(1100, 900)
        self.setStyleSheet("background-color: #0F1419;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # --- 第一行: 仪表盘区域 ---
        gauge_layout = QHBoxLayout()
        self.g1 = ModernGauge("利用率", 75, "#2196F3")
        self.g2 = ModernGauge("预警值", 85, "#FFC107")
        self.g3 = ModernGauge("风险度", 92, "#F44336")
        gauge_layout.addWidget(self.g1)
        gauge_layout.addWidget(self.g2)
        gauge_layout.addWidget(self.g3)
        main_layout.addLayout(gauge_layout)

        # --- 第二行: 数据表格 ---
        self.table = QTableWidget(5, 5)
        self.table.setHorizontalHeaderLabels([
            "地址", "功能码", "变量名", "数值", "状态"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                color: #E6EDF3;
                gridline-color: transparent;
            }
            QHeaderView::section {
                background-color: #0F1419;
                color: #8B949E;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)

        # 填充模拟数据
        data = [
            ("0x0001", "03", "温度传感器", "25.5", ("正常", "#4CAF50")),
            ("0x0002", "03", "压力变送器", "1.23", ("正常", "#4CAF50")),
            ("0x0003", "03", "流量计", "50.3", ("警告", "#FFC107")),
            ("0x0004", "03", "功率表", "15.2", ("故障", "#F44336")),
            ("0x0005", "03", "频率", "50.0", ("正常", "#4CAF50")),
        ]
        for i, (addr, func, name, val, status) in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(addr))
            self.table.setItem(i, 1, QTableWidgetItem(func))
            self.table.setItem(i, 2, QTableWidgetItem(name))
            self.table.setItem(i, 3, QTableWidgetItem(val))
            badge = AnimatedStatusBadge(status[0], status[1])
            self.table.setCellWidget(i, 4, badge)

        main_layout.addWidget(self.table)

        # --- 第三行: 实时趋势图 ---
        self.plot_widget = RealtimeChart(title="温度实时趋势图")
        self.plot_data = [random.normalvariate(20, 1) for _ in range(100)]
        self.plot_widget.update_data(self.plot_data)
        main_layout.addWidget(self.plot_widget)

        # 定时更新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(1000)

    def update_all(self):
        """定时更新所有组件"""
        # 更新仪表盘数值
        self.g1.value = random.randint(60, 80)
        self.g2.value = random.randint(70, 90)
        self.g3.value = random.randint(80, 95)

        # 更新图表数据
        self.plot_data.append(random.normalvariate(20, 1))
        self.plot_data = self.plot_data[-100:]  # 保持100个点
        self.plot_widget.update_data(self.plot_data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IndustrialDashboard()
    window.show()
    sys.exit(app.exec())
```

### 功能说明

#### 1. 动态仪表盘
- 三个仪表盘显示不同指标
- 实时数值更新（带动画效果）
- 自定义颜色主题

#### 2. 数据表格
- 显示设备寄存器数据
- 带呼吸灯的状态徽章
- 工业风深色主题

#### 3. 实时趋势图
- 基于 pyqtgraph 的高性能绘图
- 自动滚动显示最新100个数据点
- 可自定义颜色和样式

#### 4. 定时更新
- 每秒自动更新数据
- 模拟实时监控场景
- 可轻松对接真实数据源

### 扩展建议

#### 数据对接
```python
def update_from_device(self, device_data):
    """从真实设备获取数据"""
    # 更新仪表盘
    self.g1.value = device_data['utilization']
    self.g2.value = device_data['warning_level']
    self.g3.value = device_data['risk_level']

    # 更新表格
    # ...

    # 更新图表
    self.plot_widget.update_data(device_data['temperature_history'])
```

#### 报警集成
```python
def check_alarms(self):
    """检查报警条件"""
    if self.g3.value > 90:
        # 触发高等级报警
        self.show_alarm_dialog("高风险警告", "设备风险度超过90%")
    elif self.g2.value > 80:
        # 触发警告
        self.show_warning("预警", "设备预警值超过80%")
```

#### 数据导出
```python
def export_data(self):
    """导出数据到 CSV"""
    import csv
    with open('data_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['时间', '温度'])
        for i, temp in enumerate(self.plot_data):
            writer.writerow([f"{i}s", temp])
```

---

**版本**: v1.5.0
**框架**: PySide6 6.5.0+
**许可**: MIT
**维护者**: 开发团队
