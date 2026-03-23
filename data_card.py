"""
自定义控件 - 数据卡片 v2.0
现代化工业风格设计
"""
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient
from PyQt5.QtCore import Qt, QRectF


class DataCard(QFrame):
    """数据卡片控件 - 现代化工业风格"""

    def __init__(self, parent=None, title="", unit="", value=0, icon="", accent_color="#2196F3"):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.value = value
        self.icon = icon
        self.accent_color = accent_color
        self.prev_value = value
        self.initUI()

    def initUI(self):
        # 颜色配置
        self.colors = {
            'bg': '#161B22',
            'bg_hover': '#1C2128',
            'border': '#30363D',
            'text_primary': '#E6EDF3',
            'text_secondary': '#8B949E',
            'text_tertiary': '#6E7681',
            'accent': self.accent_color,
        }

        self.setStyleSheet(f"""
            DataCard {{
                background-color: {self.colors['bg']};
                border-radius: 10px;
                border: 1px solid {self.colors['border']};
            }}
            DataCard:hover {{
                background-color: {self.colors['bg_hover']};
                border: 1px solid {self.colors['accent']}60;
            }}
        """)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # 顶部区域：图标 + 标题 + 状态指示
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # 图标
        if self.icon:
            icon_label = QLabel(self.icon)
            icon_label.setFixedSize(28, 28)
            icon_label.setFont(QFont("Segoe UI Emoji", 14))
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet(f"""
                background-color: {self.colors['accent']}20;
                border-radius: 6px;
            """)
            header_layout.addWidget(icon_label)

        # 标题
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Medium))
        title_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 趋势指示器
        self.trend_label = QLabel("→")
        self.trend_label.setFont(QFont("Segoe UI", 12))
        self.trend_label.setStyleSheet(f"color: {self.colors['text_tertiary']};")
        header_layout.addWidget(self.trend_label)

        layout.addLayout(header_layout)

        # 数值显示
        value_layout = QHBoxLayout()
        value_layout.setSpacing(6)

        self.value_label = QLabel(f"{self.value:.1f}")
        self.value_label.setFont(QFont("Segoe UI", 26, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {self.colors['text_primary']};")

        value_layout.addWidget(self.value_label)

        # 单位
        unit_label = QLabel(self.unit)
        unit_label.setFont(QFont("Segoe UI", 12))
        unit_label.setStyleSheet(f"color: {self.colors['text_tertiary']};")
        unit_label.setAlignment(Qt.AlignBottom)
        unit_label.setContentsMargins(0, 0, 0, 4)
        value_layout.addWidget(unit_label)

        value_layout.addStretch()

        layout.addLayout(value_layout)

        # 底部状态条（渐变装饰）
        status_bar = QFrame()
        status_bar.setFixedHeight(3)
        status_bar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {self.colors['accent']},
                stop:1 {self.colors['accent']}00);
            border-radius: 1.5px;
        """)
        layout.addWidget(status_bar)

    def setValue(self, value):
        """设置卡片数值"""
        self.prev_value = self.value
        self.value = value

        # 检测变化趋势
        if value > self.prev_value:
            self.trend_label.setText("↑")
            self.trend_label.setStyleSheet(f"color: #3FB950;")
        elif value < self.prev_value:
            self.trend_label.setText("↓")
            self.trend_label.setStyleSheet(f"color: #F85149;")
        else:
            self.trend_label.setText("→")
            self.trend_label.setStyleSheet(f"color: {self.colors['text_tertiary']};")

        self.value_label.setText(f"{value:.1f}")

    def setValueColor(self, color):
        """设置数值颜色"""
        self.value_label.setStyleSheet(f"color: {color};")

    def setAccentColor(self, color):
        """设置强调色"""
        self.accent_color = color
        self.colors['accent'] = color
        self.update()


class MiniDataCard(QWidget):
    """迷你数据卡片"""

    def __init__(self, title="", value="", unit="", color="#2196F3"):
        super().__init__()
        self.title = title
        self.value = value
        self.unit = unit
        self.color = color
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            background-color: #1C2128;
            border-radius: 6px;
            border: 1px solid #30363D;
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # 标题
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 9))
        title_label.setStyleSheet("color: #6E7681;")
        layout.addWidget(title_label)

        # 数值
        value_layout = QHBoxLayout()
        value_layout.setSpacing(4)

        self.value_label = QLabel(self.value)
        self.value_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {self.color};")
        value_layout.addWidget(self.value_label)

        unit_label = QLabel(self.unit)
        unit_label.setFont(QFont("Segoe UI", 9))
        unit_label.setStyleSheet("color: #6E7681;")
        value_layout.addWidget(unit_label)

        value_layout.addStretch()
        layout.addLayout(value_layout)