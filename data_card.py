"""
自定义控件 - 数据卡片
"""
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt


class DataCard(QFrame):
    """数据卡片控件"""

    def __init__(self, parent=None, title="", unit="", value=0, icon=""):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.value = value
        self.icon = icon
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            DataCard {
                background-color: #2A2A2A;
                border-radius: 8px;
                border: 1px solid #3A3A3A;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        if self.icon:
            icon_label = QLabel(self.icon)
            icon_label.setFont(QFont("Segoe UI Emoji", 14))
            title_layout.addWidget(icon_label)

        title_label = QLabel(self.title)
        title_label.setFont(QFont("Microsoft YaHei", 11))
        title_label.setStyleSheet("color: #888888;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 数值显示
        self.value_label = QLabel(f"{self.value:.1f} {self.unit}")
        self.value_label.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        self.value_label.setStyleSheet("color: #00FFAA;")
        layout.addWidget(self.value_label)

    def setValue(self, value):
        """设置卡片数值"""
        self.value = value
        self.value_label.setText(f"{value:.1f} {self.unit}")

    def setValueColor(self, color):
        """设置数值颜色"""
        self.value_label.setStyleSheet(f"color: {color};")
