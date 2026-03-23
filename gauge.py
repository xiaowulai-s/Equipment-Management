"""
自定义控件 - 圆形仪表盘 v2.0
现代化工业风格设计
"""
import numpy as np
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush, QLinearGradient
from PyQt5.QtCore import Qt, QRectF


class CircularGauge(QWidget):
    """自定义圆形仪表盘控件 - 现代化工业风格"""

    def __init__(self, parent=None, min_value=0, max_value=100,
                 unit="", title="", normal_value=50):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.value = normal_value
        self.normal_value = normal_value
        self.unit = unit
        self.title = title
        self.setMinimumSize(160, 160)

        # 颜色配置
        self.colors = {
            'bg': '#1C2128',
            'ring_bg': '#30363D',
            'ring_start': '#2196F3',
            'ring_end': '#00BCD4',
            'text_primary': '#E6EDF3',
            'text_secondary': '#8B949E',
            'text_tertiary': '#6E7681',
            'success': '#3FB950',
            'warning': '#D29922',
            'error': '#F85149',
        }

    def setValue(self, value):
        """设置仪表盘值"""
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()

    def get_color_for_ratio(self, ratio):
        """根据比例获取颜色"""
        if ratio < 0.6:
            return self.colors['success']
        elif ratio < 0.8:
            return self.colors['warning']
        else:
            return self.colors['error']

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        side = min(width, height)

        # 外边距
        margin = 12
        rect = QRectF(margin, margin, side - margin * 2, side - margin * 2)

        # 绘制背景圆
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.colors['bg']))
        painter.drawEllipse(rect)

        # 绘制背景圆弧
        painter.setPen(QPen(QColor(self.colors['ring_bg']), 8))
        painter.drawArc(rect, 45 * 16, 270 * 16)

        # 计算数值对应的角度
        ratio = (self.value - self.min_value) / (self.max_value - self.min_value)
        ratio = max(0, min(1, ratio))
        end_angle = 45 + 270 * ratio

        # 根据数值选择颜色
        gauge_color = self.get_color_for_ratio(ratio)

        # 创建渐变画笔
        pen = QPen(QColor(gauge_color), 8)
        pen.setCapStyle(Qt.RoundCap)

        # 绘制数值圆弧
        painter.setPen(pen)
        painter.drawArc(rect, 45 * 16, int(end_angle * 16))

        # 绘制发光效果
        glow_color = QColor(gauge_color)
        glow_color.setAlpha(60)
        glow_pen = QPen(glow_color, 12)
        glow_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(glow_pen)
        painter.drawArc(rect, 45 * 16, int(end_angle * 16))

        # 绘制刻度线
        self.draw_tick_marks(painter, rect, side)

        # 绘制指针圆点
        center_x = rect.center().x()
        center_y = rect.center().y()
        pointer_radius = (side - margin * 2) / 2 - 20
        pointer_angle = (180 - end_angle) * np.pi / 180
        pointer_x = center_x + pointer_radius * np.cos(pointer_angle)
        pointer_y = center_y - pointer_radius * np.sin(pointer_angle)

        # 指针发光
        glow_brush = QBrush(glow_color)
        painter.setBrush(glow_brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(pointer_x) - 10, int(pointer_y) - 10, 20, 20)

        # 指针圆点
        painter.setBrush(QBrush(QColor(gauge_color)))
        painter.drawEllipse(int(pointer_x) - 6, int(pointer_y) - 6, 12, 12)

        # 绘制中心区域
        inner_rect = QRectF(center_x - 35, center_y - 35, 70, 70)
        painter.setBrush(QColor(self.colors['bg']))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(inner_rect)

        # 绘制中心数值
        painter.setPen(QColor(self.colors['text_primary']))
        value_font = QFont("Segoe UI", 18, QFont.Bold)
        painter.setFont(value_font)
        value_text = f"{self.value:.1f}"
        painter.drawText(inner_rect, Qt.AlignCenter, value_text)

        # 绘制单位
        if self.unit:
            unit_font = QFont("Segoe UI", 9)
            painter.setFont(unit_font)
            painter.setPen(QColor(self.colors['text_tertiary']))
            unit_rect = QRectF(inner_rect.left(), inner_rect.bottom() + 2, inner_rect.width(), 15)
            painter.drawText(unit_rect, Qt.AlignCenter, self.unit)

        # 绘制标题
        if self.title:
            title_font = QFont("Segoe UI", 11, QFont.Medium)
            painter.setFont(title_font)
            painter.setPen(QColor(self.colors['text_secondary']))
            title_rect = QRectF(rect.left(), rect.top() - 5, rect.width(), 20)
            painter.drawText(title_rect, Qt.AlignCenter, self.title)

    def draw_tick_marks(self, painter, rect, side):
        """绘制刻度线"""
        center_x = rect.center().x()
        center_y = rect.center().y()
        radius = (side - 12 * 2) / 2 - 15

        painter.setPen(QPen(QColor(self.colors['text_tertiary']), 1.5))

        # 绘制主刻度（0%, 50%, 100%位置）
        tick_angles = [45, 135, 225]  # 开始、中间、结束位置

        for angle in tick_angles:
            rad = (180 - angle) * np.pi / 180
            inner_radius = radius - 5
            outer_radius = radius + 2

            x1 = center_x + inner_radius * np.cos(rad)
            y1 = center_y - inner_radius * np.sin(rad)
            x2 = center_x + outer_radius * np.cos(rad)
            y2 = center_y - outer_radius * np.sin(rad)

            painter.drawLine(int(x1), int(y1), int(x2), int(y2))


class GaugeCard(QWidget):
    """仪表盘卡片容器"""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            background-color: #161B22;
            border-radius: 8px;
            border: 1px solid #30363D;
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        if self.title:
            title_label = QLabel(self.title)
            title_label.setFont(QFont("Segoe UI", 10))
            title_label.setStyleSheet("color: #8B949E;")
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)