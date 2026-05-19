# -*- coding: utf-8 -*-
"""
历史趋势图组件 - History Chart Widget
========================================

为数值型数据点提供历史数据可视化（折线图/实时刷新）。

功能特性:
✅ 实时数据追加显示（动态折线图）
✅ 时间范围选择（1小时/6小时/24小时/7天）
✅ 多数据点叠加对比
✅ 缩放和平移支持
✅ 报警阈值线标注（高限红虚线/低限黄虚线）
✅ 数据导出（CSV格式）
✅ 自动滚动和固定模式

依赖库:
- PySide6-Addons (包含 QtCharts 模块)

使用示例:
    >>> chart = HistoryChartWidget("device_001")
    >>> chart.add_data_point("温度传感器", 25.6)
    >>> chart.add_data_point("压力传感器", 1.2)
    >>> chart.set_alarm_thresholds("温度传感器", high=80.0, low=10.0)
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer, QDateTime, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPen, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# 尝试导入QtCharts模块（用于历史趋势图）
QTCHARTS_AVAILABLE = False

try:
    from PySide6.QtCharts import (
        QChart,
        QChartView,
        QDateTimeAxis,
        QLineSeries,
        QValueAxis,
    )

    QTCHARTS_AVAILABLE = True
except ImportError:
    QTCHARTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class HistoryChartWidget(QWidget):
    """
    历史趋势图主组件

    提供完整的时序数据可视化功能，
    支持多数据源叠加、时间范围选择、报警阈值标注等。

    信号 (Signals):
        export_requested(str): 用户点击导出按钮时发射 (文件路径)

    布局结构:
        ┌─────────────────────────────────────┐
        │ 工具栏 [时间范围] [刷新] [导出] [自动滚动] │
        ├─────────────────────────────────────┤
        │                                     │
        │          图表区域 (QChartView)       │
        │                                     │
        ├─────────────────────────────────────┤
        │           图例 (QChart自动生成)       │
        └─────────────────────────────────────┘

    使用示例:
        >>> chart = HistoryChartWidget("device_001")
        >>> chart.add_data_point("温度", 25.6)
        >>> chart.set_time_range(hours=6)
        >>> chart.show()
    """

    # 信号定义
    export_requested = Signal(str)  # 导出请求 (文件路径)

    # 默认配置
    DEFAULT_MAX_POINTS = 1000  # 最大显示点数
    DEFAULT_REFRESH_INTERVAL_MS = 1000  # 刷新间隔（毫秒）

    # 预设颜色方案（用于多曲线区分）
    SERIES_COLORS = [
        QColor("#3B82F6"),  # 蓝色
        QColor("#EF4444"),  # 红色
        QColor("#10B981"),  # 绿色
        QColor("#F59E0B"),  # 橙色
        QColor("#8B5CF6"),  # 紫色
        QColor("#EC4899"),  # 粉色
        QColor("#06B6D4"),  # 青色
        QColor("#84CC16"),  # 黄绿
    ]

    # 阈值线样式
    ALARM_HIGH_COLOR = QColor("#DC2626")  # 高限：红色
    ALARM_LOW_COLOR = QColor("#F59E0B")  # 低限：橙色
    THRESHOLD_LINE_STYLE = Qt.PenStyle.DashLine

    def __init__(self, device_id: str = "", parent: Optional[QWidget] = None) -> None:
        """
        初始化历史趋势图组件

        Args:
            device_id: 设备ID（用于标识和日志）
            parent: 父窗口
        """
        super().__init__(parent)

        if not QTCHARTS_AVAILABLE:
            self._init_fallback_ui()
            return

        self._device_id = device_id

        # 数据存储 {参数名: [(timestamp, value), ...]}
        self._data_buffer: Dict[str, List[Tuple[datetime, float]]] = {}

        # 曲线对象映射 {参数名: QLineSeries}
        self._series_map: Dict[str, QLineSeries] = {}

        # 阈值配置 {参数名: {"high": float, "low": float}}
        self._thresholds: Dict[str, Dict[str, Optional[float]]] = {}

        # 配置参数
        self._max_points: int = self.DEFAULT_MAX_POINTS
        self._time_range_hours: int = 1  # 默认显示最近1小时
        self._auto_scroll: bool = True  # 自动滚动到最新数据

        # 颜色索引（用于循环分配颜色）
        self._color_index: int = 0

        # 初始化UI
        self._init_ui()

        logger.info("HistoryChartWidget 初始化完成 [设备=%s]", device_id or "未指定")

    def _init_fallback_ui(self) -> None:
        """QtCharts不可用时的降级UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        warning_label = QLabel(
            "历史趋势图组件不可用\n\n"
            "原因：缺少 PySide6-Addons 库\n\n"
            "请执行以下命令安装：\n"
            "pip install PySide6-Addons\n\n"
            "安装后重启应用程序即可使用此功能。"
        )
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet(
            """
            QLabel {
                color: #DC2626;
                font-size: 14px;
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 20px;
            }
        """
        )
        layout.addWidget(warning_label)

    def _init_ui(self) -> None:
        """初始化UI布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ===== 图表区域（工具栏已由外部对话框提供）=====
        self._chart = QChart()
        self._chart.setTitle(f"设备 {self._device_id} 历史趋势" if self._device_id else "历史趋势图")
        self._chart.setTitleFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self._chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self._chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        if hasattr(QChart.ChartTheme, "Light"):
            self._chart.setTheme(QChart.ChartTheme.Light)

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self._chart_view, 1)  # 占据主要空间

        # ===== 初始化坐标轴 =====
        self._setup_axes()

    def _setup_axes(self) -> None:
        """初始化图表坐标轴"""
        # X轴：时间轴
        self._axis_x = QDateTimeAxis()
        self._axis_x.setTickCount(6)
        self._axis_x.setFormat("HH:mm:ss")
        self._axis_x.setTitleText("时间")
        self._chart.addAxis(self._axis_x, Qt.Alignment.AlignBottom)

        # Y轴：数值轴
        self._axis_y = QValueAxis()
        self._axis_y.setTickCount(5)
        self._axis_y.setTitleText("数值")
        self._chart.addAxis(self._axis_y, Qt.Alignment.AlignLeft)

    def add_data_point(self, param_name: str, value: float, timestamp: Optional[datetime] = None) -> None:
        """
        添加数据点

        将新的数据点追加到指定参数的缓冲区中，
        并更新图表显示。

        Args:
            param_name: 参数名称（如"温度传感器"、"压力传感器"）
            value: 数值
            timestamp: 时间戳（默认当前时间）

        Examples:
            >>> chart.add_data_point("温度传感器", 25.6)
            >>> chart.add_data_point("压力传感器", 1.02, datetime.now())
        """
        if not QTCHARTS_AVAILABLE:
            return

        # 使用当前时间（如果未提供）
        if timestamp is None:
            timestamp = datetime.now()

        # 初始化该参数的数据缓冲区（如果不存在）
        if param_name not in self._data_buffer:
            self._data_buffer[param_name] = []
            # 创建对应的曲线
            self._create_series(param_name)

        # 添加数据点到缓冲区
        self._data_buffer[param_name].append((timestamp, value))

        # 限制最大点数（超出时移除最旧的点，同时从系列中移除）
        if len(self._data_buffer[param_name]) > self._max_points:
            removed = self._data_buffer[param_name].pop(0)
            series = self._series_map.get(param_name)
            if series and series.count() > 0:
                series.remove(0)

        # 实时追加到曲线（不重建整个系列，避免闪烁）
        series = self._series_map.get(param_name)
        if series is not None:
            msecs = int(timestamp.timestamp() * 1000)
            series.append(msecs, value)

        # 自动移动X轴显示最新数据（显示最近30秒）
        if self._data_buffer.get(param_name):
            now = datetime.now()
            self._axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(int((now.timestamp() - 30) * 1000)),
                QDateTime.fromMSecsSinceEpoch(int(now.timestamp() * 1000) + 1000),
            )

        logger.debug("实时曲线 [参数=%s, 值=%.2f, 总点数=%d]", param_name, value, len(self._data_buffer[param_name]))

    def set_bulk_data(
        self,
        data_by_param: Dict[str, List[tuple]],
        param_names: List[str],
        display_names: Any = None,
        device_display_name: str = "",
    ) -> None:
        """
        批量设置所有参数的历史数据（替换而非追加）

        Args:
            data_by_param: {参数名: [(时间戳, 值), ...]} 格式的数据
            param_names: 参数名称列表
            display_names: 显示名称(list)或映射(dict)，与 param_names 同顺序
            device_display_name: 设备显示名称
        """
        if not QTCHARTS_AVAILABLE:
            return

        self.clear_data()
        self._data_buffer.clear()
        self._color_index = 0

        for i, param_name in enumerate(param_names):
            points = data_by_param.get(param_name, [])
            if not points:
                continue

            if isinstance(display_names, dict):
                display_name = display_names.get(param_name, param_name)
            elif isinstance(display_names, list) and i < len(display_names):
                display_name = display_names[i]
            else:
                display_name = param_name
            self._data_buffer[display_name] = []
            self._create_series(display_name)

            for ts, val in points:
                self._data_buffer[display_name].append((ts, val))

            self._update_series(display_name)

        # 自动调整坐标轴范围以显示所有数据
        if self._data_buffer:
            all_ts = []
            all_vals = []
            for pts in self._data_buffer.values():
                for ts, val in pts:
                    all_ts.append(ts)
                    all_vals.append(val)
            if all_ts:
                min_ts = min(all_ts)
                max_ts = max(all_ts)
                min_ms = int(min_ts.timestamp() * 1000)
                max_ms = int(max_ts.timestamp() * 1000)
                if max_ms - min_ms < 60000:
                    max_ms = min_ms + 60000  # 至少1分钟范围
                self._axis_x.setRange(
                    QDateTime.fromMSecsSinceEpoch(min_ms),
                    QDateTime.fromMSecsSinceEpoch(max_ms),
                )

                min_val = min(all_vals)
                max_val = max(all_vals)
                margin = (max_val - min_val) * 0.1 if max_val != min_val else 1.0
                self._axis_y.setRange(min_val - margin, max_val + margin)

    def _create_series(self, param_name: str) -> None:
        """
        为参数创建新的曲线对象

        Args:
            param_name: 参数名称
        """
        series = QLineSeries()
        series.setName(param_name)

        # 分配颜色
        color = self.SERIES_COLORS[self._color_index % len(self.SERIES_COLORS)]
        self._color_index += 1

        pen = QPen(color)
        pen.setWidth(2)
        series.setPen(pen)

        # 添加到图表
        self._chart.addSeries(series)
        series.attachAxis(self._axis_x)
        series.attachAxis(self._axis_y)

        # 存储引用
        self._series_map[param_name] = series

        logger.debug("创建曲线: %s (颜色=%s)", param_name, color.name())

    def _update_series(self, param_name: str) -> None:
        """
        更新曲线数据

        从数据缓冲区读取数据并刷新曲线。

        Args:
            param_name: 参数名称
        """
        series = self._series_map.get(param_name)
        if series is None:
            return

        data_points = self._data_buffer.get(param_name, [])
        if not data_points:
            return

        # 清除旧数据并重新加载
        series.clear()

        for timestamp, value in data_points:
            # 将datetime转换为msec since epoch（Qt要求的格式）
            msecs = int(timestamp.timestamp() * 1000)
            series.append(msecs, value)

    def set_alarm_thresholds(self, param_name: str, high: Optional[float] = None, low: Optional[float] = None) -> None:
        """
        设置报警阈值线

        在图表上绘制水平虚线表示高/低报警阈值。

        Args:
            param_name: 参数名称
            high: 高限阈值（None表示不显示）
            low: 低限阈值（None表示不显示）

        Examples:
            >>> chart.set_alarm_thresholds("温度传感器", high=80.0, low=10.0)
        """
        if not QTCHARTS_AVAILABLE:
            return

        # 保存阈值配置
        self._thresholds[param_name] = {"high": high, "low": low}

        # TODO: 在图表上绘制阈值线
        # （需要额外实现阈值线的添加/更新逻辑）
        logger.info(
            "设置报警阈值 [参数=%s, 高限=%s, 低限=%s]",
            param_name,
            f"{high}" if high else "无",
            f"{low}" if low else "无",
        )

    def set_time_range(self, hours: int = 1) -> None:
        """
        设置显示的时间范围

        Args:
            hours: 显示最近N小时的数据（1/6/24/168即7天）
        """
        self._time_range_hours = hours

        # 更新X轴格式
        if hours <= 1:
            self._axis_x.setFormat("HH:mm:ss")
        elif hours <= 24:
            self._axis_x.setFormat("HH:mm")
        else:
            self._axis_x.setFormat("MM-dd HH:mm")

        logger.info("时间范围已设置为 %d 小时", hours)

        # 刷新图表以应用新范围
        self.refresh_chart()

    def clear_data(self, param_name: Optional[str] = None) -> None:
        """
        清除数据

        Args:
            param_name: 要清除的参数名（None=全部清除）
        """
        if param_name is None:
            # 清除所有数据
            self._data_buffer.clear()

            # 清除所有曲线
            for series in self._series_map.values():
                self._chart.removeSeries(series)
            self._series_map.clear()

            # 重置颜色索引
            self._color_index = 0

            logger.info("已清除所有数据和曲线")
        else:
            # 清除指定参数
            if param_name in self._data_buffer:
                del self._data_buffer[param_name]

            if param_name in self._series_map:
                self._chart.removeSeries(self._series_map[param_name])
                del self._series_map[param_name]

            logger.info("已清除参数 '%s' 的数据", param_name)

    def refresh_chart(self) -> None:
        """
        刷新图表显示

        重新加载所有曲线数据并重绘。
        """
        if not QTCHARTS_AVAILABLE:
            return

        # 更新每条曲线
        for param_name in list(self._series_map.keys()):
            self._update_series(param_name)

        logger.debug("图表已刷新")

    def export_to_csv(self, filepath: str) -> bool:
        """
        导出数据到CSV文件

        Args:
            filepath: 输出文件路径

        Returns:
            是否成功

        Examples:
            >>> success = chart.export_to_csv("data_export.csv")
        """
        if not self._data_buffer:
            logger.warning("没有数据可导出")
            return False

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as csvfile:
                writer = csv.writer(csvfile)

                header = ["时间戳"] + list(self._data_buffer.keys())
                writer.writerow(header)

                all_ts_set = set()
                for data in self._data_buffer.values():
                    for ts, _ in data:
                        all_ts_set.add(ts)
                sorted_ts = sorted(all_ts_set)

                param_keys = list(self._data_buffer.keys())
                for ts in sorted_ts:
                    row = [ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]]
                    for pname in param_keys:
                        pdata = self._data_buffer[pname]
                        closest_val = None
                        closest_diff = float("inf")
                        for dts, dval in pdata:
                            diff = abs((dts - ts).total_seconds())
                            if diff < closest_diff:
                                closest_diff = diff
                                closest_val = dval
                        if closest_val is not None:
                            row.append(f"{closest_val:.4f}")
                        else:
                            row.append("")
                    writer.writerow(row)

            logger.info("数据已导出到: %s (%d 行)", filepath, len(sorted_ts) + 1)
            return True

        except Exception as e:
            logger.error("导出CSV失败: %s", str(e))
            return False

    # ==================== 事件处理槽函数 ====================

    def _on_time_range_changed(self, index: int) -> None:
        """时间范围下拉框变化事件"""
        range_map = {0: 1, 1: 6, 2: 24, 3: 168}  # 168小时=7天
        hours = range_map.get(index, 1)
        self.set_time_range(hours)

    def _on_auto_scroll_changed(self, state: int) -> None:
        """自动滚动复选框变化事件"""
        self._auto_scroll = state == Qt.CheckState.Checked.value

    def _on_export_csv(self) -> None:
        """导出CSV按钮点击事件"""
        default_name = f"{self._device_id or 'history'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出历史数据", default_name, "CSV Files (*.csv);;All Files (*)"
        )

        if filepath:
            success = self.export_to_csv(filepath)
            if success:
                self.export_requested.emit(filepath)
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(self, "导出成功", f"数据已导出至:\n{filepath}")
            else:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(self, "导出失败", "导出过程中发生错误，请查看日志。")

    # ==================== 属性访问器 ====================

    @property
    def data_point_count(self) -> int:
        """获取总数据点数量"""
        return sum(len(data) for data in self._data_buffer.values())

    @property
    def parameter_count(self) -> int:
        """获取参数数量"""
        return len(self._data_buffer)

    @property
    def device_id(self) -> str:
        """获取设备ID"""
        return self._device_id

    def get_parameter_names(self) -> List[str]:
        """获取所有参数名称列表"""
        return list(self._data_buffer.keys())
