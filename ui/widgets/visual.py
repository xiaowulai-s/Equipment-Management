# -*- coding: utf-8 -*-
"""
可视化组件库 - 高级 UI 组件

包含:
- AnimatedStatusBadge: 动画状态徽章
- RealtimeChart: 实时图表
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QFont, QPainter, QPaintEvent, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


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
            # 优化：从50ms改为100ms，减少CPU占用同时保持流畅的呼吸效果
            self._timer.start(100)  # 100ms更新一次（约10fps）

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
            self._timer.start(100)  # 与 _setup_animation 保持一致
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
        self._series: dict[str, list[tuple[float, float]]] = {}
        self._colors: dict[str, str] = {}
        self._default_colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0"]
        self._color_index = 0

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._on_refresh_tick)
        self._refresh_timer.start(1000)

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

        # 为坐标轴标签留出空间
        width = chart_rect.width() - 60  # 右侧和底部留出空间
        height = chart_rect.height() - 60  # 左侧和顶部留出空间
        x_offset = 50  # 左侧留出空间
        y_offset = 20  # 顶部留出空间

        # 绘制背景
        painter.fillRect(chart_rect, QColor("#FAFAFA"))

        # 绘制网格和坐标轴
        if self._show_grid:
            self._draw_grid(painter, x_offset, y_offset, width, height)

        # 计算Y轴范围
        y_min, y_max = self._calculate_y_range()
        if y_min is None or y_max is None or y_min == y_max:
            return

        import time as _time

        now = _time.time()
        window_secs = max(self._max_points, 10)

        all_timestamps_list = []
        for data_points in self._series.values():
            all_timestamps_list.extend([ts for ts, _ in data_points])

        if all_timestamps_list:
            global_min_ts = max(min(all_timestamps_list), now - window_secs)
        else:
            global_min_ts = now - window_secs
        global_max_ts = now

        if global_max_ts <= global_min_ts:
            global_max_ts = global_min_ts + 1.0
        ts_range = global_max_ts - global_min_ts

        # 绘制坐标轴
        self._draw_axes(painter, x_offset, y_offset, width, height, y_min, y_max, global_min_ts, global_max_ts)

        # 绘制数据曲线
        for series_name, data_points in self._series.items():
            if not data_points:
                continue

            color = self._colors.get(series_name, self._default_colors[0])
            pen = QPen(QColor(color))
            pen.setWidth(2)
            painter.setPen(pen)

            if len(data_points) == 1:
                ts, value = data_points[0]
                if ts >= global_min_ts:
                    x_ratio = (ts - global_min_ts) / ts_range
                    x = x_offset + x_ratio * width
                else:
                    x = x_offset + width / 2
                y = y_offset + height - ((value - y_min) / (y_max - y_min)) * height
                painter.setBrush(QBrush(QColor(color)))
                painter.drawEllipse(x - 3, y - 3, 6, 6)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                continue

            painter.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            first = True

            for timestamp, value in data_points:
                if timestamp < global_min_ts:
                    continue
                x_ratio = (timestamp - global_min_ts) / ts_range
                x = x_offset + x_ratio * width
                y = y_offset + height - ((value - y_min) / (y_max - y_min)) * height

                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)

            if not first:
                painter.drawPath(path)

        # 绘制边框
        painter.setPen(QPen(QColor("#E0E0E0")))
        painter.drawRect(x_offset, y_offset, width, height)

    def _draw_axes(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        height: int,
        y_min: float,
        y_max: float,
        start_time: float,
        end_time: float,
    ) -> None:
        """绘制坐标轴和标签"""
        # 绘制坐标轴
        pen = QPen(QColor("#666666"))
        pen.setWidth(1)
        painter.setPen(pen)

        # X轴 (时间轴)
        painter.drawLine(x, y + height, x + width, y + height)

        # Y轴 (数值轴)
        painter.drawLine(x, y, x, y + height)

        # 设置文字样式
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Arial", 8))

        # 绘制Y轴数值标签（与5×5网格对齐）
        NUM_TICKS = 6  # 5个大格子 = 6条刻度线
        DIVISIONS = NUM_TICKS - 1  # 5等分
        for i in range(NUM_TICKS):
            y_value = y_min + (y_max - y_min) * (1 - i / DIVISIONS)
            y_pos = y + (height * i) // DIVISIONS

            # 绘制Y轴刻度线
            painter.drawLine(x - 5, y_pos, x, y_pos)

            # 绘制Y轴数值
            value_text = f"{y_value:.1f}"
            text_rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignmentFlag.AlignRight, value_text)
            painter.drawText(x - text_rect.width() - 10, y_pos + 5, value_text)

        # 绘制X轴时间标签（与5×5网格对齐）
        import time

        # 绘制X轴刻度线和时间标签
        for i in range(NUM_TICKS):
            x_pos = x + (width * i) // DIVISIONS

            # 绘制X轴刻度线
            painter.drawLine(x_pos, y + height, x_pos, y + height + 5)

            # 计算对应时间
            timestamp = start_time + (end_time - start_time) * (i / DIVISIONS)
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))

            # 绘制X轴时间
            text_rect = painter.boundingRect(0, 0, 100, 20, Qt.AlignmentFlag.AlignCenter, time_str)
            painter.drawText(x_pos - text_rect.width() // 2, y + height + 20, time_str)

    def _draw_grid(self, painter: QPainter, x: int, y: int, width: int, height: int) -> None:
        """绘制5×5网格 - 与坐标轴刻度对齐"""
        MAJOR = 5  # 大格子数（5×5 = 25个小格子）

        # 浅色细线（小格子线）
        pen_light = QPen(QColor("#E8E8E8"))
        pen_light.setWidth(1)
        pen_light.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen_light)

        # 小格子线：i=1..MAJOR-1 共4条内线
        for i in range(1, MAJOR):
            # 水平小格子线
            y_pos = y + (height * i) // MAJOR
            painter.drawLine(x, y_pos, x + width, y_pos)
            # 垂直小格子线
            x_pos = x + (width * i) // MAJOR
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

    def _on_refresh_tick(self) -> None:
        import time as _time

        now = _time.time()
        cutoff = now - max(self._max_points * 2, 20)
        for name in list(self._series.keys()):
            pts = self._series[name]
            while pts and pts[0][0] < cutoff:
                pts.pop(0)
        self.update()

    def stop_timer(self) -> None:
        """停止刷新定时器"""
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()

    def start_timer(self) -> None:
        """启动刷新定时器"""
        if not self._refresh_timer.isActive():
            self._refresh_timer.start(1000)

    def hideEvent(self, event) -> None:
        """隐藏时停止定时器以减少资源消耗"""
        self.stop_timer()
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        """显示时恢复定时器"""
        self.start_timer()
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        """关闭时清理定时器"""
        self.stop_timer()
        super().closeEvent(event)

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
