"""
自定义控件 - 圆形仪表盘
"""
import numpy as np
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt5.QtCore import Qt, QRectF


class CircularGauge(QWidget):
    """自定义圆形仪表盘控件"""

    def __init__(self, parent=None, min_value=0, max_value=100,
                 unit="", title="", normal_value=50):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.value = normal_value
        self.normal_value = normal_value
        self.unit = unit
        self.title = title
        self.setMinimumSize(140, 140)

    def setValue(self, value):
        """设置仪表盘值"""
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        side = min(width, height)

        # 背景圆弧区域
        rect = QRectF(15, 15, side - 30, side - 30)

        # 绘制背景圆弧 (灰色)
        painter.setPen(QPen(QColor("#3A3A3A"), 10))
        painter.drawArc(rect, 45 * 16, 270 * 16)

        # 计算数值对应的角度
        ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        end_angle = 45 + 270 * ratio

        # 根据数值选择颜色
        if ratio < 0.6:
            color = QColor("#00FFAA")  # 绿色-正常
        elif ratio < 0.8:
            color = QColor("#FFAA00")  # 黄色-警告
        else:
            color = QColor("#FF5555")  # 红色-危险

        # 绘制数值圆弧
        painter.setPen(QPen(color, 10))
        painter.drawArc(rect, 45 * 16, int(end_angle * 16))

        # 绘制指针圆点
        center_x = rect.center().x()
        center_y = rect.center().y()
        pointer_radius = (side - 30) / 2 - 15
        pointer_angle = (180 - end_angle) * 3.14159 / 180
        pointer_x = center_x + pointer_radius * 0.7 * np.cos(pointer_angle)
        pointer_y = center_y - pointer_radius * 0.7 * np.sin(pointer_angle)

        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color, 2))
        painter.drawEllipse(int(pointer_x) - 6, int(pointer_y) - 6, 12, 12)

        # 绘制中心数值
        painter.setPen(QColor("#FFFFFF"))
        value_font = QFont("Microsoft YaHei", 16, QFont.Bold)
        painter.setFont(value_font)
        value_text = f"{self.value:.1f}"
        painter.drawText(rect, Qt.AlignCenter, value_text)

        # 绘制单位
        if self.unit:
            unit_font = QFont("Microsoft YaHei", 9)
            painter.setFont(unit_font)
            painter.setPen(QColor("#888888"))
            painter.drawText(rect.adjusted(0, 25, 0, 0), Qt.AlignCenter, self.unit)

        # 绘制标题
        if self.title:
            title_font = QFont("Microsoft YaHei", 10)
            painter.setFont(title_font)
            painter.setPen(QColor("#AAAAAA"))
            painter.drawText(rect.adjusted(0, -35, 0, 0), Qt.AlignCenter, self.title)
