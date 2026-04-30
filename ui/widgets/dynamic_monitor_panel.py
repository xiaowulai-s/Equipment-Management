# -*- coding: utf-8 -*-
"""
动态监控面板 - 自动UI生成系统
Dynamic Monitor Panel (Auto UI Generation)

根据 RegisterPointConfig 列表自动生成监控卡片布局。

核心功能:
✅ 接收 List[RegisterPointConfig] → 自动生成 UI 卡片网格
✅ 智能卡片类型识别：
   - COIL(可写) → 可点击圆形按钮（绿=OFF/红=ON）
   - COIL(只读)/DI → 状态指示灯（●亮/○灭）
   - INT16/FLOAT32 → 数值卡片（大字显示+单位+报警变色）
✅ 网格自适应布局（每行最多4个卡片）
✅ 报警值自动变红/橙色

设计原则:
✅ 配置驱动：无需手写UI代码，完全由数据配置决定界面
✅ 类型安全：基于 RegisterDataType 枚举自动选择控件类型
✅ 响应式：支持动态添加/删除数据点后重新构建布局
✅ 信号驱动：通过 coil_write_requested 信号通知写操作请求

使用示例:
    >>> panel = DynamicMonitorPanel("device_001")
    >>> panel.build_from_config(register_points)
    >>> panel.update_data({"温度": {"value": "25.6 ℃", ...}})
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.enums.data_type_enum import RegisterDataType, RegisterPointConfig

logger = logging.getLogger(__name__)


class SwitchCard(QFrame):
    """
    开关卡片组件（用于COIL/DI类型）

    UI规则:
    - 可写COIL: 圆形可点击按钮（绿=OFF, 红=ON），点击触发写请求
    - 只读COIL/DI: 状态指示灯（●亮=ON, ○灭=OFF）
    """

    # 自定义信号：开关状态变化时发射
    toggled = Signal(str, bool)  # param_name, new_state

    def __init__(self, config: RegisterPointConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._current_state: Optional[bool] = None
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFixedWidth(140)
        self.setFixedHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 参数名称标签
        name_label = QLabel(self._config.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont("Microsoft YaHei", 9))
        name_label.setStyleSheet("color: #374151; background: transparent;")
        layout.addWidget(name_label)

        # 开关按钮/指示灯
        if self._config.writable and self._config.data_type == RegisterDataType.COIL:
            # 可写模式：圆形按钮
            self.switch_btn = QPushButton()
            self.switch_btn.setFixedSize(50, 50)
            self.switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.switch_btn.setText("OFF")
            self.switch_btn.clicked.connect(self._on_button_clicked)
            self._update_button_style(False)
            layout.addWidget(self.switch_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            # 只读模式：指示灯
            self.indicator = QLabel("○")
            self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.indicator.setFont(QFont("Segoe UI Symbol", 36))
            self.indicator.setStyleSheet("color: #D1D5DB; background: transparent; font-size: 40px;")
            layout.addWidget(self.indicator, alignment=Qt.AlignmentFlag.AlignCenter)

        # 地址信息（小字）
        addr_label = QLabel(f"@{self._config.address}")
        addr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        addr_label.setFont(QFont("Consolas", 8))
        addr_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(addr_label)

    def _on_button_clicked(self) -> None:
        """按钮点击事件"""
        # 切换状态预览（实际写入需等待确认）
        new_state = not self._current_state if self._current_state is not None else True

        # 发射信号（不直接改变状态，等确认后再更新）
        self.toggled.emit(self._config.name, new_state)

    def update_state(self, state: bool) -> None:
        """
        更新开关状态

        Args:
            state: True=ON, False=OFF
        """
        self._current_state = state

        if hasattr(self, "switch_btn") and self.switch_btn is not None:
            # 更新可写按钮
            self.switch_btn.setText("ON" if state else "OFF")
            self._update_button_style(state)
        elif hasattr(self, "indicator") and self.indicator is not None:
            # 更新只读指示灯
            if state:
                self.indicator.setText("●")
                self.indicator.setStyleSheet("color: #059669; background: transparent; font-size: 40px;")
            else:
                self.indicator.setText("○")
                self.indicator.setStyleSheet("color: #D1D5DB; background: transparent; font-size: 40px;")

    def _update_button_style(self, state: bool) -> None:
        """更新按钮样式"""
        if state:
            # ON状态：红色背景
            self.switch_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #DC2626;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #B91C1C;
                }
                QPushButton:pressed {
                    background-color: #991B1B;
                }
            """
            )
        else:
            # OFF状态：绿色背景
            self.switch_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #059669;
                    color: white;
                    border: none;
                    border-radius: 25px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #047857;
                }
                QPushButton:pressed {
                    background-color: #065F46;
                }
            """
            )


class ValueCard(QFrame):
    """
    数值卡片组件（用于寄存器类型：INT16/INT32/FLOAT32等）

    显示内容：
    - 大字数值显示（22px粗体）
    - 单位标签
    - 报警变色功能（高限红色，低限橙色）
    """

    def __init__(self, config: RegisterPointConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = config
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setFixedWidth(160)
        self.setFixedHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 参数名称标签
        name_label = QLabel(self._config.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont("Microsoft YaHei", 9))
        name_label.setStyleSheet("color: #374151; background: transparent;")
        layout.addWidget(name_label)

        # 数值显示（大字体）
        self.value_label = QLabel("--")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont("Consolas", 22, QFont.Weight.Bold))
        self.value_label.setStyleSheet("color: #111827; background: transparent;")
        layout.addWidget(self.value_label)

        # 单位标签
        unit_text = self._config.unit or ""
        if unit_text:
            unit_label = QLabel(unit_text)
            unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            unit_label.setFont(QFont("Microsoft YaHei", 9))
            unit_label.setStyleSheet("color: #6B7280; background: transparent;")
            layout.addWidget(unit_label)

        # 地址信息（小字）
        addr_label = QLabel(f"@{self._config.address}")
        addr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        addr_label.setFont(QFont("Consolas", 8))
        addr_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(addr_label)

    def update_value(self, value_str: str, alarm_status: Optional[str] = None) -> None:
        """
        更新数值显示

        Args:
            value_str: 格式化后的字符串值（如 "25.60 ℃"）
            alarm_status: 报警状态 ("high"/"low"/None)
        """
        self.value_label.setText(value_str)

        # 根据报警状态改变颜色
        if alarm_status == "high":
            # 高限报警：红色
            self.value_label.setStyleSheet("color: #DC2626; background: transparent; font-weight: bold;")
        elif alarm_status == "low":
            # 低限报警：橙色
            self.value_label.setStyleSheet("color: #F97316; background: transparent; font-weight: bold;")
        else:
            # 正常：黑色
            self.value_label.setStyleSheet("color: #111827; background: transparent;")


class DynamicMonitorPanel(QWidget):
    """
    动态监控面板主组件

    根据传入的 RegisterPointConfig 列表自动生成监控卡片网格。

    核心方法:
    - build_from_config(): 根据配置列表创建所有卡片
    - update_data(): 批量更新所有卡片的显示值
    - clear(): 清空所有卡片

    信号:
    - coil_write_requested(str, bool): 用户点击可写线圈时发射

    使用示例:
        >>> panel = DynamicMonitorPanel("device_001")
        >>> panel.build_from_config(register_points)
        >>> panel.coil_write_requested.connect(on_write_request)
        >>> panel.update_data(data_dict)
    """

    # 信号：线圈写操作请求
    coil_write_requested = Signal(str, bool)  # param_name, value

    # ✅ 新增信号：批量写操作请求
    batch_write_requested = Signal(str, list)  # device_id, [(name, value), ...]

    # 布局常量
    MAX_COLUMNS = 4  # 每行最多4个卡片

    def __init__(self, device_id: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.device_id = device_id
        self._register_points: List[RegisterPointConfig] = []
        self._card_widgets: Dict[str, QWidget] = {}  # {param_name: card_widget}

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """
        )

        # 内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        self._grid_layout = QGridLayout(content_widget)
        self._grid_layout.setContentsMargins(16, 12, 16, 12)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # 空状态提示
        self._empty_label = QLabel("暂无数据点配置\n请在设备向导中添加数据点")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setFont(QFont("Microsoft YaHei", 12))
        self._empty_label.setStyleSheet(
            """
            color: #9CA3AF;
            background: transparent;
            padding: 40px;
        """
        )
        self._grid_layout.addWidget(self._empty_label, 0, 0, Qt.AlignmentFlag.AlignCenter)

    def build_from_config(self, register_points: List[RegisterPointConfig]) -> None:
        """
        根据寄存器点配置列表构建UI卡片

        这是核心方法，遍历配置列表并为每个数据点创建对应的卡片控件。

        Args:
            register_points: 寄存器点配置列表

        Examples:
            >>> config_list = [
            ...     RegisterPointConfig("进水阀", RegisterDataType.COIL, 0),
            ...     RegisterPointConfig("温度", RegisterDataType.HOLDING_FLOAT32, 0,
            ...                          scale=0.1, unit="℃"),
            ... ]
            >>> panel.build_from_config(config_list)
        """
        # 清空现有卡片
        self.clear()

        # 保存配置引用
        self._register_points = list(register_points)

        if not register_points:
            # 显示空状态提示
            self._empty_label.show()
            return

        # 隐藏空状态提示
        self._empty_label.hide()

        # 遍历配置，创建卡片
        row = 0
        col = 0

        for rp in register_points:
            try:
                card = self._create_card(rp)

                if card is not None:
                    # 存储到字典中（用于后续更新）
                    self._card_widgets[rp.name] = card

                    # 添加到网格布局
                    self._grid_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

                    # 更新行列计数
                    col += 1
                    if col >= self.MAX_COLUMNS:
                        col = 0
                        row += 1

            except Exception as e:
                logger.error("创建卡片失败 [参数=%s]: %s", rp.name, str(e), exc_info=True)
                continue

        logger.info(
            "设备 %s 动态面板已构建 %d 个卡片 (%d 行 × %d 列)",
            self.device_id,
            len(self._card_widgets),
            row + (1 if col > 0 else 0),
            min(col + 1, self.MAX_COLUMNS),
        )

    def _create_card(self, rp: RegisterPointConfig) -> Optional[QWidget]:
        """
        根据数据类型创建对应类型的卡片

        创建规则:
        - COIL / DISCRETE_INPUT → SwitchCard（开关卡片）
        - HOLDING_INT16 / INT32 / FLOAT32 → ValueCard（数值卡片）
        - INPUT_INT16 / FLOAT32 → ValueCard（只读数值卡片）

        Args:
            rp: 寄存器点配置

        Returns:
            卡片Widget实例，失败返回None
        """
        # 判断是否为布尔类型（COIL或DI）
        if rp.data_type in (RegisterDataType.COIL, RegisterDataType.DISCRETE_INPUT):
            return self._create_switch_card(rp)
        else:
            # 其他类型为数值型
            return self._create_value_card(rp)

    def _create_switch_card(self, rp: RegisterPointConfig) -> SwitchCard:
        """
        创建开关卡片（COIL/DI类型）

        UI规则:
        - COIL(可写): 可点击圆形按钮（绿=OFF, 红=ON）
        - COIL(只读)/DI: 状态指示灯（●亮/○灭）

        Args:
            rp: 寄存器点配置

        Returns:
            SwitchCard 实例
        """
        card = SwitchCard(rp, self)

        # 连接信号：用户点击可写线圈时发射请求信号
        if rp.writable and rp.data_type == RegisterDataType.COIL:
            card.toggled.connect(self._on_switch_toggled)

        return card

    def _create_value_card(self, rp: RegisterPointConfig) -> ValueCard:
        """
        创建数值卡片（寄存器类型）

        UI特征:
        - 22px粗体Consolas字体显示数值
        - 单位标签
        - 报警变色（高限红/低限橙）

        Args:
            rp: 寄存器点配置

        Returns:
            ValueCard 实例
        """
        return ValueCard(rp, self)

    def _on_switch_toggled(self, param_name: str, value: bool) -> None:
        """
        开关状态切换槽函数

        当用户点击可写的COIL按钮时触发，
        发射 coil_write_requested 信号通知上层处理。

        注意：此处不直接执行写入操作，
        而是通过信号机制让 MainWindow 或 WriteOperationManager 处理。

        Args:
            param_name: 参数名称
            value: 目标状态（True=ON, False=OFF）
        """
        logger.debug("设备 %s 线圈写请求 [参数=%s, 值=%s]", self.device_id, param_name, "ON" if value else "OFF")

        # 发射信号（由外部处理器负责确认和执行）
        self.coil_write_requested.emit(param_name, value)

    def update_data(self, data: Dict[str, Any]) -> None:
        """
        批量更新所有卡片的显示值

        这是轮询数据更新时的主要调用入口。
        由外部的定时轮询任务定期调用。

        Args:
            data: 数据字典 {参数名: {raw, value, type, writable, config}}

        Examples:
            >>> data = {
            ...     "进水阀": {"raw": True, "value": "ON", "type": "coil", ...},
            ...     "温度": {"raw": 2560, "value": "256.00 ℃", "type": "holding_float32", ...},
            ... }
            >>> panel.update_data(data)
        """
        if not data:
            return

        updated_count = 0

        for param_name, param_info in data.items():
            # 查找对应的卡片控件
            card = self._card_widgets.get(param_name)
            if card is None:
                continue

            try:
                if isinstance(card, SwitchCard):
                    # 开关卡片：提取布尔值
                    raw_value = param_info.get("raw", param_info.get("value"))
                    if isinstance(raw_value, bool):
                        card.update_state(raw_value)
                        updated_count += 1

                elif isinstance(card, ValueCard):
                    # 数值卡片：格式化字符串 + 报警状态
                    value_str = param_info.get("value", "--")
                    raw_value = param_info.get("raw")

                    # 检查报警状态
                    alarm_status = None
                    config = param_info.get("config")
                    if config and isinstance(config, RegisterPointConfig) and isinstance(raw_value, (int, float)):
                        alarm_status = config.check_alarm(float(raw_value))

                    card.update_value(str(value_str), alarm_status)
                    updated_count += 1

            except Exception as e:
                logger.warning("更新卡片显示失败 [参数=%s]: %s", param_name, str(e))
                continue

        if updated_count > 0:
            logger.debug("设备 %s 面板已更新 %d/%d 个卡片", self.device_id, updated_count, len(self._card_widgets))

    def clear(self) -> None:
        """清空所有卡片"""
        # 移除所有卡片控件
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # 清空内部状态
        self._card_widgets.clear()
        self._register_points.clear()

        # 显示空状态提示
        self._empty_label.show()

    def get_card_count(self) -> int:
        """获取当前卡片数量"""
        return len(self._card_widgets)

    def get_register_point_names(self) -> List[str]:
        """获取所有已注册的参数名称"""
        return list(self._card_widgets.keys())

    # ==================== ✅ 新增：批量写操作方法 ====================

    def get_selected_coils_state(self) -> List[Dict[str, Any]]:
        """
        获取当前所有可写线圈的状态（用于批量操作）

        Returns:
            可写线圈状态列表 [{"name": "进水阀", "value": True, "address": 0}, ...]
        """
        coils_state = []

        for param_name, card in self._card_widgets.items():
            if isinstance(card, SwitchCard):
                config = card.config
                if config.writable and config.data_type == RegisterDataType.COIL:
                    # 获取当前状态（如果有的话）
                    current_value = card.current_state
                    if current_value is not None:
                        coils_state.append(
                            {
                                "name": param_name,
                                "value": current_value,
                                "address": config.address,
                            }
                        )

        return coils_state

    def show_batch_write_dialog(self) -> None:
        """
        弹出批量写操作对话框

        收集所有可写线圈状态，发射 batch_write_requested 信号，
        由 MainWindow 或上层组件显示确认对话框。
        """
        coils_state = self.get_selected_coils_state()

        if not coils_state:
            logger.info("设备 %s 没有可写的线圈", self.device_id)
            return

        logger.info("设备 %s 发起批量写请求 [可写线圈数=%d]", self.device_id, len(coils_state))

        # 发射信号，携带设备ID和操作列表
        self.batch_write_requested.emit(self.device_id, [(c["name"], c["value"]) for c in coils_state])

    def set_writable(self, allowed: bool) -> None:
        """
        根据权限设置是否允许写操作

        Args:
            allowed: True=允许写操作, False=禁用写操作（按钮灰色）
        """
        for param_name, card in self._card_widgets.items():
            if isinstance(card, SwitchCard):
                config = card.config
                if config.writable and config.data_type == RegisterDataType.COIL:
                    card.setEnabled(allowed)
                    if not allowed:
                        card.setToolTip("权限不足：需要写操作权限")
                    else:
                        card.setToolTip("")

    # ==================== ✅ 新增：历史趋势图集成 ====================

    def show_history_chart(self, param_name: Optional[str] = None) -> None:
        """
        显示历史趋势图（在新窗口或DockWidget中）

        Args:
            param_name: 要显示的参数名（可选，None则显示全部）
        """
        from .history_chart_widget import HistoryChartWidget

        # 创建或获取趋势图窗口
        if not hasattr(self, "_history_chart") or self._history_chart is None:
            self._history_chart = HistoryChartWidget(self.device_id, parent=self)
            self._history_chart.setWindowTitle(f"历史趋势图 - {self.device_id}" if self.device_id else "历史趋势图")
            self._history_chart.resize(900, 600)

        # 如果指定了参数名，确保该参数有数据
        if param_name:
            logger.info("设备 %s 打开趋势图 [参数=%s]", self.device_id, param_name)

        # 显示趋势图窗口
        self._history_chart.show()
        self._history_chart.raise_()
        self._history_chart.activateWindow()

    def _on_value_card_double_clicked(self, param_name: str) -> None:
        """
        双击数值卡片打开该点的趋势图

        Args:
            param_name: 参数名称
        """
        logger.info("双击数值卡片，打开趋势图 [设备=%s, 参数=%s]", self.device_id, param_name)
        self.show_history_chart(param_name)
