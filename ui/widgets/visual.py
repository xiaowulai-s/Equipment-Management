# -*- coding: utf-8 -*-
"""
可视化组件库 - 高级 UI 组件

包含:
- ModernGauge: 动态圆形仪表盘
- AnimatedStatusBadge: 动画状态徽章
- RealtimeChart: 实时图表
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QFont, QPainter, QPaintEvent, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class ModernGauge(QWidget):
    """
    动态圆形仪表盘

    特性:
    - 平滑动画数值变化 (QPropertyAnimation)
    - 发光渐变效果
    - 可自定义范围、单位、颜色
    - 支持关联寄存器变量

    Signals:
        clicked: 点击仪表盘时触发
    """

    clicked = Signal()

    def __init__(
        self,
        title: str = "",
        value: float = 0.0,
        color: str = "#2196F3",
        min_value: float = 0.0,
        max_value: float = 100.0,
        unit: str = "",
        register_name: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._value = value
        self._target_value = value
        self._color = QColor(color)
        self._min_value = min_value
        self._max_value = max_value
        self._unit = unit
        self._register_name = register_name  # 关联的寄存器变量名

        self._setup_ui()
        self._setup_animation()

        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self) -> None:
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题标签
        self._title_label = QLabel(self._title)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(f"color: #1F2937; font-size: 12px; font-weight: 500;")
        layout.addWidget(self._title_label)

        # 数值标签
        self._value_label = QLabel(self._format_value(self._value))
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setStyleSheet(f"color: {self._color.name()}; font-size: 24px; font-weight: 700;")
        layout.addWidget(self._value_label)

        # 单位标签
        self._unit_label = QLabel(self._unit)
        self._unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._unit_label.setStyleSheet("color: #6B7280; font-size: 10px;")
        layout.addWidget(self._unit_label)

        # 寄存器关联标签
        if self._register_name:
            self._register_label = QLabel(f"📎 {self._register_name}")
            self._register_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._register_label.setStyleSheet("color: #2196F3; font-size: 9px;")
            layout.addWidget(self._register_label)
        else:
            self._register_label = None

        layout.addStretch()

    def _setup_animation(self) -> None:
        """设置数值动画"""
        self._animation = QPropertyAnimation(self, b"animated_value")
        self._animation.setDuration(500)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _format_value(self, value: float) -> str:
        """格式化数值显示"""
        if abs(value) >= 100:
            return f"{value:.0f}"
        elif abs(value) >= 10:
            return f"{value:.1f}"
        else:
            return f"{value:.2f}"

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 计算绘制区域
        rect = self.rect()
        size = min(rect.width(), rect.height()) - 20
        x = (rect.width() - size) // 2
        y = (rect.height() - size) // 2 + 20  # 为文字留出空间

        # 绘制背景圆环
        pen = QPen(QColor("#E5E7EB"))
        pen.setWidth(8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(x, y, size, size)

        # 计算当前值对应的进度
        progress = (self._value - self._min_value) / (self._max_value - self._min_value)
        progress = max(0.0, min(1.0, progress))

        # 绘制进度圆环
        pen = QPen(self._color)
        pen.setWidth(8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # 绘制弧形进度条
        start_angle = 225 * 16  # 从左上开始
        span_angle = -progress * 270 * 16  # 逆时针绘制
        painter.drawArc(x, y, size, size, start_angle, span_angle)

        # 绘制发光效果
        if progress > 0:
            gradient = QRadialGradient(
                rect.center().x(),
                rect.center().y() + 10,
                size // 2,
            )
            gradient.setColorAt(0, QColor(self._color.red(), self._color.green(), self._color.blue(), 30))
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x - 5, y - 5, size + 10, size + 10)

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        self.clicked.emit()
        super().mousePressEvent(event)

    @Property(float)
    def animated_value(self) -> float:
        """动画属性值"""
        return self._value

    @animated_value.setter
    def animated_value(self, value: float) -> None:
        self._value = value
        self._value_label.setText(self._format_value(value))
        self.update()

    @property
    def value(self) -> float:
        """获取当前值"""
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        """设置值（带动画）"""
        self._target_value = max(self._min_value, min(self._max_value, value))
        self._animation.stop()
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(self._target_value)
        self._animation.start()

    @property
    def register_name(self) -> str:
        """获取关联的寄存器变量名"""
        return self._register_name

    @register_name.setter
    def register_name(self, name: str) -> None:
        """设置关联的寄存器变量名"""
        self._register_name = name
        if self._register_label:
            if name:
                self._register_label.setText(f"📎 {name}")
                self._register_label.show()
            else:
                self._register_label.hide()

    def update_from_register(self, value: float) -> None:
        """从寄存器更新数值"""
        self.value = value


class AnimatedStatusBadge(QWidget):
    """
    动画状态徽章

    特性:
    - 呼吸灯效果动画
    - 多种状态样式 (在线/离线/警告/错误)
    - 支持脉冲动画指示活动状态
    - 可自定义颜色和文字

    Signals:
        clicked: 点击徽章时触发
    """

    clicked = Signal()

    # 状态颜色配置
    STATUS_COLORS = {
        "online": ("#4CAF50", "#81C784"),  # 绿色
        "offline": ("#9E9E9E", "#BDBDBD"),  # 灰色
        "warning": ("#FF9800", "#FFB74D"),  # 橙色
        "error": ("#F44336", "#E57373"),  # 红色
        "idle": ("#2196F3", "#64B5F6"),  # 蓝色
    }

    def __init__(
        self,
        text: str = "",
        status: str = "online",
        animated: bool = True,
        pulse: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._text = text
        self._status = status
        self._animated = animated
        self._pulse = pulse
        self._opacity = 1.0
        self._pulse_direction = -1  # 1: 增加, -1: 减少
        self._pulse_speed = 0.02

        self._setup_ui()
        self._setup_animation()

        self.setMinimumSize(60, 24)
        self.setMaximumHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self) -> None:
        """设置UI布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 状态指示点
        self._indicator = QLabel()
        self._indicator.setFixedSize(8, 8)
        self._update_indicator_style()
        layout.addWidget(self._indicator)

        # 状态文字
        self._text_label = QLabel(self._text)
        self._text_label.setStyleSheet("color: white; font-size: 11px; font-weight: 500;")
        layout.addWidget(self._text_label)

        self._update_badge_style()

    def _setup_animation(self) -> None:
        """设置呼吸灯动画"""
        if self._animated and self._pulse:
            from PySide6.QtCore import QTimer

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._update_pulse)
            self._timer.start(50)  # 50ms更新一次

    def _update_pulse(self) -> None:
        """更新脉冲效果"""
        self._opacity += self._pulse_speed * self._pulse_direction
        if self._opacity <= 0.4:
            self._opacity = 0.4
            self._pulse_direction = 1
        elif self._opacity >= 1.0:
            self._opacity = 1.0
            self._pulse_direction = -1
        self._update_indicator_style()

    def _update_indicator_style(self) -> None:
        """更新指示点样式"""
        colors = self.STATUS_COLORS.get(self._status, self.STATUS_COLORS["online"])
        base_color = colors[0]
        opacity = int(self._opacity * 255) if self._pulse else 255
        self._indicator.setStyleSheet(
            f"""
            QLabel {{
                background-color: {base_color};
                border-radius: 4px;
                opacity: {self._opacity};
            }}
        """
        )

    def _update_badge_style(self) -> None:
        """更新徽章整体样式"""
        colors = self.STATUS_COLORS.get(self._status, self.STATUS_COLORS["online"])
        base_color = colors[0]
        self.setStyleSheet(
            f"""
            AnimatedStatusBadge {{
                background-color: {base_color};
                border-radius: 12px;
                padding: 4px 8px;
            }}
        """
        )
        self._update_indicator_style()

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        self.clicked.emit()
        super().mousePressEvent(event)

    @property
    def text(self) -> str:
        """获取显示文字"""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """设置显示文字"""
        self._text = value
        self._text_label.setText(value)

    @property
    def status(self) -> str:
        """获取当前状态"""
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        """设置状态"""
        if value in self.STATUS_COLORS:
            self._status = value
            self._update_badge_style()

    def start_animation(self) -> None:
        """启动动画"""
        if hasattr(self, "_timer") and not self._timer.isActive():
            self._timer.start(50)
        self._animated = True

    def stop_animation(self) -> None:
        """停止动画"""
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()
        self._animated = False
        self._opacity = 1.0
        self._update_indicator_style()


class RealtimeChart(QWidget):
    """
    实时趋势图

    特性:
    - 实时数据滚动显示
    - 支持多条曲线
    - 自动缩放和网格
    - 可配置时间窗口
    - 暂停/继续功能

    Signals:
        clicked: 点击图表时触发
    """

    clicked = Signal()

    def __init__(
        self,
        title: str = "",
        max_points: int = 100,
        y_min: Optional[float] = None,
        y_max: Optional[float] = None,
        auto_scale: bool = True,
        show_grid: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._max_points = max_points
        self._y_min = y_min
        self._y_max = y_max
        self._auto_scale = auto_scale
        self._show_grid = show_grid
        self._paused = False
        self._series: dict[str, list[tuple[float, float]]] = {}  # name -> [(timestamp, value)]
        self._colors: dict[str, str] = {}
        self._default_colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0"]
        self._color_index = 0

        self._setup_ui()

        self.setMinimumSize(200, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self) -> None:
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题
        if self._title:
            self._title_label = QLabel(self._title)
            self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._title_label.setStyleSheet("color: #24292F; font-size: 12px; font-weight: 500;")
            layout.addWidget(self._title_label)
        else:
            self._title_label = None

    def paintEvent(self, event) -> None:
        """绘制图表"""
        from PySide6.QtGui import QPainterPath

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 计算绘图区域
        chart_rect = self.rect()
        if self._title_label:
            chart_rect.setTop(24)  # 为标题留出空间

        width = chart_rect.width() - 20
        height = chart_rect.height() - 20
        x_offset = 10
        y_offset = 10

        # 绘制背景
        painter.fillRect(chart_rect, QColor("#FAFAFA"))

        # 绘制网格
        if self._show_grid:
            self._draw_grid(painter, x_offset, y_offset, width, height)

        # 计算Y轴范围
        y_min, y_max = self._calculate_y_range()
        if y_min is None or y_max is None or y_min == y_max:
            return

        # 绘制数据曲线
        for series_name, data_points in self._series.items():
            if len(data_points) < 2:
                continue

            color = self._colors.get(series_name, self._default_colors[0])
            pen = QPen(QColor(color))
            pen.setWidth(2)
            painter.setPen(pen)

            path = QPainterPath()
            first = True

            for i, (timestamp, value) in enumerate(data_points):
                x = (
                    x_offset + (i / (self._max_points - 1)) * width
                    if len(data_points) >= self._max_points
                    else x_offset + (i / max(1, len(data_points) - 1)) * width
                )
                y = y_offset + height - ((value - y_min) / (y_max - y_min)) * height

                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)

            painter.drawPath(path)

        # 绘制边框
        painter.setPen(QPen(QColor("#E0E0E0")))
        painter.drawRect(x_offset, y_offset, width, height)

    def _draw_grid(self, painter: QPainter, x: int, y: int, width: int, height: int) -> None:
        """绘制网格"""
        pen = QPen(QColor("#E8E8E8"))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)

        # 水平线
        for i in range(1, 5):
            y_pos = y + (height * i) // 5
            painter.drawLine(x, y_pos, x + width, y_pos)

        # 垂直线
        for i in range(1, 5):
            x_pos = x + (width * i) // 5
            painter.drawLine(x_pos, y, x_pos, y + height)

    def _calculate_y_range(self) -> tuple[Optional[float], Optional[float]]:
        """计算Y轴范围"""
        if not self._auto_scale and self._y_min is not None and self._y_max is not None:
            return self._y_min, self._y_max

        all_values = []
        for data_points in self._series.values():
            all_values.extend([v for _, v in data_points])

        if not all_values:
            return self._y_min, self._y_max

        y_min = min(all_values)
        y_max = max(all_values)

        # 添加一些边距
        margin = (y_max - y_min) * 0.1 if y_max != y_min else 1.0
        return y_min - margin, y_max + margin

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        self.clicked.emit()
        super().mousePressEvent(event)

    def add_series(self, name: str, color: Optional[str] = None) -> None:
        """添加数据系列"""
        self._series[name] = []
        if color:
            self._colors[name] = color
        else:
            self._colors[name] = self._default_colors[self._color_index % len(self._default_colors)]
            self._color_index += 1

    def remove_series(self, name: str) -> None:
        """移除数据系列"""
        if name in self._series:
            del self._series[name]
            del self._colors[name]

    def add_point(self, series_name: str, timestamp: float, value: float) -> None:
        """添加数据点"""
        if self._paused:
            return

        if series_name not in self._series:
            self.add_series(series_name)

        self._series[series_name].append((timestamp, value))

        # 保持最大点数
        if len(self._series[series_name]) > self._max_points:
            self._series[series_name] = self._series[series_name][-self._max_points :]

        self.update()

    def add_value(self, series_name: str, value: float) -> None:
        """添加数据点（自动使用当前时间）"""
        import time

        self.add_point(series_name, time.time(), value)

    def clear(self) -> None:
        """清空所有数据"""
        self._series.clear()
        self.update()

    def clear_series(self, name: str) -> None:
        """清空指定系列的数据"""
        if name in self._series:
            self._series[name].clear()
            self.update()

    def pause(self) -> None:
        """暂停更新"""
        self._paused = True

    def resume(self) -> None:
        """继续更新"""
        self._paused = False

    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._paused

    @property
    def max_points(self) -> int:
        """最大数据点数"""
        return self._max_points

    @max_points.setter
    def max_points(self, value: int) -> None:
        """设置最大数据点数"""
        self._max_points = max(10, value)
        # 裁剪现有数据
        for name in self._series:
            if len(self._series[name]) > self._max_points:
                self._series[name] = self._series[name][-self._max_points :]
        self.update()
