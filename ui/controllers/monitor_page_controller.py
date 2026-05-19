# -*- coding: utf-8 -*-
"""Monitor page controller."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QEvent, QObject, Qt, QDateTime, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# 导入 DesignTokens 统一样式系统
try:
    from ui.design_tokens import DT

    DESIGN_TOKENS_AVAILABLE = True
except ImportError:
    DESIGN_TOKENS_AVAILABLE = False


class MonitorPageController(QObject):
    """Encapsulates monitor page creation, card/chart display, and register table."""

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self._device_cards_layout: Optional[QGridLayout] = None
        self._chart_layout: Optional[QVBoxLayout] = None
        self._register_table: Optional[QWidget] = None
        self._monitor_tabs: Optional[QTabWidget] = None
        self._device_name_label: Optional[QLabel] = None
        self._device_desc_label: Optional[QLabel] = None
        self._last_update_label: Optional[QLabel] = None
        self._expand_btn: Optional[QPushButton] = None
        self._right_splitter: Optional[QSplitter] = None
        self._on_expand_panel_cb: Optional[Callable] = None
        self._current_chart = None
        self._current_chart_card_name = None
        self._card_precision: Dict[str, int] = {}
        self._current_device_id: Optional[str] = None
        self._card_to_register: Dict[QWidget, str] = {}

    def build(
        self,
        parent: QWidget,
        styles: dict,
        constants: dict,
        on_expand_panel: Callable,
    ) -> QWidget:
        self._on_expand_panel_cb = on_expand_panel
        self._constants = constants

        page = QWidget()
        layout = QVBoxLayout(page)
        # 简化边距，减少视觉噪音
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)  # 更紧凑的垂直间距

        # ═══ 第一行：页面标题 ═══
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self._expand_btn = QPushButton(">")
        self._expand_btn.setObjectName("left_expand_btn")
        self._expand_btn.setFixedSize(24, 24)
        self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expand_btn.setToolTip("展开面板")
        if DESIGN_TOKENS_AVAILABLE:
            expand_font = DT.T.get_font(*DT.T.BODY_SMALL)
            self._expand_btn.setFont(expand_font)
        else:
            expand_font = QFont("Segoe UI Symbol", 10)
            self._expand_btn.setFont(expand_font)
        self._expand_btn.clicked.connect(on_expand_panel)
        self._expand_btn.hide()
        header_layout.addWidget(self._expand_btn)

        self._device_title_label = QLabel(constants.get("DEVICE_MONITOR_TITLE", "设备监控"))
        if DESIGN_TOKENS_AVAILABLE:
            title_font = DT.T.get_font(*DT.T.TITLE_MEDIUM)
            self._device_title_label.setFont(title_font)
            self._device_title_label.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY}; background: transparent;")
        else:
            self._device_title_label.setFont(QFont("Segoe UI Variable", 18, QFont.Weight.Bold))
            self._device_title_label.setStyleSheet("color: #24292F; background: transparent;")
        header_layout.addWidget(self._device_title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # ═══ 第二行：设备信息卡片（紧凑型）═══
        info_container = QWidget()
        if DESIGN_TOKENS_AVAILABLE:
            info_container.setStyleSheet(
                f"""
                background-color: {DT.C.BG_SECONDARY};
                border-radius: {DT.R.SM}px;
                padding: {DT.S.SM}px;
            """
            )
        else:
            info_container.setStyleSheet(
                """
                background-color: #F6F8FA;
                border-radius: 6px;
                padding: 8px;
            """
            )
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(16)

        # 设备名称（主要信息）
        self._device_name_label = QLabel("未选择设备")
        if DESIGN_TOKENS_AVAILABLE:
            name_font = DT.T.get_font(*DT.T.BODY)
            self._device_name_label.setFont(name_font)
            self._device_name_label.setStyleSheet(
                f"color: {DT.C.TEXT_PRIMARY}; background: transparent; font-weight: 500;"
            )
        else:
            self._device_name_label.setStyleSheet(
                "color: #24292F; font-size: 14px; font-weight: 500; background: transparent;"
            )
        info_layout.addWidget(self._device_name_label)

        # 设备描述（可选信息）
        self._device_desc_label = QLabel("")
        if DESIGN_TOKENS_AVAILABLE:
            desc_font = DT.T.get_font(*DT.T.CAPTION)
            self._device_desc_label.setFont(desc_font)
            self._device_desc_label.setStyleSheet(f"color: {DT.C.TEXT_SECONDARY}; background: transparent;")
        else:
            self._device_desc_label.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent;")
        info_layout.addWidget(self._device_desc_label)

        # 状态徽章
        from ui.widgets.visual import AnimatedStatusBadge

        device_status_badge = AnimatedStatusBadge("Not Connected")
        info_layout.addWidget(device_status_badge)

        info_layout.addStretch()

        # 最后更新时间（次要信息）
        self._last_update_label = QLabel("-")
        if DESIGN_TOKENS_AVAILABLE:
            update_font = DT.T.get_font(*DT.T.CAPTION)
            self._last_update_label.setFont(update_font)
            self._last_update_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; background: transparent;")
        else:
            self._last_update_label.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent;")
        info_layout.addWidget(self._last_update_label)

        layout.addWidget(info_container)

        self._right_splitter = QSplitter(Qt.Orientation.Vertical)

        self._monitor_tabs = QTabWidget()
        # 使用 DesignTokens 优化标签页样式
        if DESIGN_TOKENS_AVAILABLE:
            tab_stylesheet = f"""
                QTabWidget::pane {{
                    border: 1px solid {DT.C.BORDER_DEFAULT};
                    border-radius: {DT.R.MD}px;
                    background-color: {DT.C.BG_PRIMARY};
                    padding: {DT.S.SM}px;
                }}
                QTabBar::tab {{
                    background-color: {DT.C.BG_SECONDARY};
                    color: {DT.C.TEXT_SECONDARY};
                    border: 1px solid {DT.C.BORDER_DEFAULT};
                    border-bottom: none;
                    border-top-left-radius: {DT.R.MD}px;
                    border-top-right-radius: {DT.R.MD}px;
                    padding: {DT.S.SM}px {DT.S.MD}px;
                    margin-right: 2px;
                    font-family: '{DT.T.BODY[0]}';
                    font-size: {DT.T.BODY[1]}px;
                    font-weight: {DT.T.BODY[2]};
                }}
                QTabBar::tab:selected {{
                    background-color: {DT.C.BG_PRIMARY};
                    color: {DT.C.TEXT_PRIMARY};
                    border-bottom: 2px solid {DT.C.ACCENT_PRIMARY};
                    font-weight: 600;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: {DT.C.BG_HOVER};
                    color: {DT.C.TEXT_PRIMARY};
                }}
            """
            self._monitor_tabs.setStyleSheet(tab_stylesheet)
        else:
            self._monitor_tabs.setStyleSheet(styles.get("TAB_WIDGET", ""))
        self._monitor_tabs.setDocumentMode(True)  # 改善标签页渲染

        data_tab = self._build_data_tab(styles)
        register_tab = self._build_register_tab()

        tab_data_text = constants.get("TAB_REALTIME_DATA", "实时数据")
        tab_reg_text = constants.get("TAB_REGISTERS", "寄存器")

        # 确保标签文字正确显示（使用 Unicode 安全的字符串）
        self._monitor_tabs.addTab(data_tab, str(tab_data_text))
        self._monitor_tabs.addTab(register_tab, str(tab_reg_text))

        # 设置标签页的最小宽度防止文字被截断，并使用合适的字体
        if DESIGN_TOKENS_AVAILABLE:
            tab_font = DT.T.get_font(*DT.T.LABEL)
            self._monitor_tabs.tabBar().setFont(tab_font)
            # 根据文字长度动态计算最小宽度
            max_text_len = max(len(tab_data_text), len(tab_reg_text))
            min_width = max(100, max_text_len * 16 + 32)  # 每个字符约 16px + 边距
            self._monitor_tabs.tabBar().setMinimumWidth(min_width)
        else:
            self._monitor_tabs.tabBar().setMinimumWidth(100)

        self._right_splitter.addWidget(self._monitor_tabs)

        log_panel = self._build_unified_log_panel()
        self._right_splitter.addWidget(log_panel)

        self._right_splitter.setStretchFactor(0, 7)
        self._right_splitter.setStretchFactor(1, 3)

        initial_height = max(self.height() if hasattr(self, "height") else 600, 400)
        monitor_h = int(initial_height * 0.70)
        log_h = int(initial_height * 0.30)
        self._right_splitter.setSizes([monitor_h, log_h])

        layout.addWidget(self._right_splitter)

        self._device_status_badge = device_status_badge

        return page

    def _build_unified_log_panel(self) -> QWidget:
        from PySide6.QtWidgets import QTextBrowser

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        log_title = QLabel("系统日志")
        if DESIGN_TOKENS_AVAILABLE:
            title_font = DT.T.get_font(*DT.T.LABEL)
            log_title.setFont(title_font)
            log_title.setStyleSheet(
                f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};"
            )
        else:
            log_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #57606A; background: transparent;")
        header_layout.addWidget(log_title)

        clear_btn_text = self._constants.get("BTN_CLEAR_LOG", "清空日志")
        from ui.widgets import SecondaryButton

        self._log_clear_btn = SecondaryButton(clear_btn_text)
        self._log_clear_btn.setFixedSize(80, 26)
        self._log_clear_btn.clicked.connect(self._clear_log)
        header_layout.addStretch()
        header_layout.addWidget(self._log_clear_btn)
        layout.addLayout(header_layout)

        self._unified_log_view = QTextBrowser()
        self._unified_log_view.setReadOnly(True)
        self._unified_log_view.setOpenLinks(False)

        if DESIGN_TOKENS_AVAILABLE:
            bg_color = DT.C.BG_PRIMARY
            border_color = DT.C.BORDER_SUBTLE
            text_color = DT.C.TEXT_PRIMARY
            radius = f"{DT.R.SM}px"
            self._unified_log_view.setStyleSheet(
                f"""
                QTextBrowser {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: {radius};
                    color: {text_color};
                    font-family: '{DT.T.CODE[0]}';
                    font-size: {DT.T.CODE[1]}px;
                    padding: {DT.S.SM}px;
                }}
            """
            )
        else:
            self._unified_log_view.setStyleSheet(
                """
                QTextBrowser {
                    background-color: #1E1E1E;
                    border: 1px solid #333;
                    border-radius: 6px;
                    color: #D4D4D4;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 11px;
                    padding: 8px;
                }
            """
            )

        layout.addWidget(self._unified_log_view)
        return container

    def append_log(self, message: str, level: str = "INFO") -> None:
        if not hasattr(self, "_unified_log_view") or self._unified_log_view is None:
            return
        ts = QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
        color_map = {
            "INFO": "#4CAF50",
            "SUCCESS": "#2196F3",
            "WARNING": "#FF9800",
            "ERROR": "#F44336",
            "CRITICAL": "#E91E63",
        }
        color = color_map.get(level, "#D4D4D4")
        html = f'<span style="color:#888;">[{ts}]</span> <span style="color:{color};">[{level}]</span> <span style="color:#D4D4D4;">{message}</span>'
        self._unified_log_view.append(html)

    def _clear_log(self) -> None:
        if hasattr(self, "_unified_log_view") and self._unified_log_view is not None:
            self._unified_log_view.clear()

    def _build_data_tab(self, styles: dict) -> QWidget:
        from ui.widgets import SecondaryButton

        tab = QWidget()
        main_layout = QHBoxLayout(tab)
        if DESIGN_TOKENS_AVAILABLE:
            main_layout.setContentsMargins(DT.S.SM, DT.S.SM, DT.S.SM, DT.S.SM)
            main_layout.setSpacing(DT.S.MD)
        else:
            main_layout.setContentsMargins(12, 12, 12, 12)
            main_layout.setSpacing(16)

        # ═══ 左侧：数据卡片纵向列表 ═══
        left_panel = QWidget()
        left_panel.setMinimumWidth(180)
        left_panel.setMaximumWidth(260)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 卡片列表标题
        cards_title = QLabel("数据列表")
        if DESIGN_TOKENS_AVAILABLE:
            title_font = DT.T.get_font(*DT.T.LABEL)
            cards_title.setFont(title_font)
            cards_title.setStyleSheet(
                f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};"
            )
        else:
            cards_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #57606A; background: transparent;")
        left_layout.addWidget(cards_title)

        # 可滚动卡片容器
        from PySide6.QtWidgets import QScrollArea

        self._cards_scroll_area = QScrollArea()
        self._cards_scroll_area.setWidgetResizable(True)
        self._cards_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if DESIGN_TOKENS_AVAILABLE:
            self._cards_scroll_area.setStyleSheet(
                f"""
                QScrollArea {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea > QWidget > QWidget {{
                    background: {DT.C.BG_PRIMARY};
                }}
            """
            )
        else:
            self._cards_scroll_area.setStyleSheet(
                """
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollArea > QWidget > QWidget {
                    background: #FFFFFF;
                }
            """
            )

        self._device_cards_layout = QVBoxLayout()
        self._device_cards_layout.setSpacing(10)
        self._device_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        if DESIGN_TOKENS_AVAILABLE:
            self._device_cards_layout.setContentsMargins(DT.S.SM, DT.S.SM, DT.S.SM, DT.S.SM)
        else:
            self._device_cards_layout.setContentsMargins(8, 8, 8, 8)

        scroll_content = QWidget()
        scroll_content.setLayout(self._device_cards_layout)
        self._cards_scroll_area.setWidget(scroll_content)
        left_layout.addWidget(self._cards_scroll_area, 1)
        main_layout.addWidget(left_panel)

        # ═══ 右侧：实时曲线图区域（占满剩余空间）═══
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # 曲线标题栏：显示当前选中变量的名称
        self._chart_title_label = QLabel("实时曲线 — 请选择变量")
        if DESIGN_TOKENS_AVAILABLE:
            chart_title_font = DT.T.get_font(*DT.T.LABEL)
            self._chart_title_label.setFont(chart_title_font)
            self._chart_title_label.setStyleSheet(
                f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};"
            )
        else:
            self._chart_title_label.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #57606A; background: transparent;"
            )

        chart_header = QHBoxLayout()
        chart_header.addWidget(self._chart_title_label)
        chart_header.addStretch()
        right_layout.addLayout(chart_header)

        # 图表容器
        chart_container = QWidget()
        if DESIGN_TOKENS_AVAILABLE:
            chart_container.setStyleSheet(
                f"""
                background-color: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_SUBTLE};
                border-radius: {DT.R.SM}px;
            """
            )
        else:
            chart_container.setStyleSheet(
                """
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
            """
            )

        self._chart_layout = QVBoxLayout(chart_container)
        if DESIGN_TOKENS_AVAILABLE:
            self._chart_layout.setContentsMargins(DT.S.MD, DT.S.MD, DT.S.MD, DT.S.MD)
            self._chart_layout.setSpacing(DT.S.SM)
        else:
            self._chart_layout.setContentsMargins(12, 12, 12, 12)
            self._chart_layout.setSpacing(8)

        self._chart_empty_label = QLabel("← 点击左侧数据卡片查看实时曲线")
        if DESIGN_TOKENS_AVAILABLE:
            self._chart_empty_label.setStyleSheet(
                f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px; background: transparent;"
            )
        else:
            self._chart_empty_label.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent;")
        self._chart_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chart_layout.addWidget(self._chart_empty_label)

        right_layout.addWidget(chart_container, 1)
        main_layout.addWidget(right_panel, 1)

        # 选中状态跟踪
        self._selected_card_name: Optional[str] = None
        self._selected_card_widget: Optional[QWidget] = None
        self._card_widgets: Dict[str, "DataCard"] = {}
        self._card_history: Dict[str, Dict[str, list]] = {}  # device_id → card_name → history
        self._max_history_points = 120  # 保留最近120个数据点（约2分钟@1Hz）

        return tab

    def _on_card_clicked(self, card_name: str, card_widget: "DataCard") -> None:
        """数据卡片点击回调 — 切换选中并更新曲线图"""
        # 取消之前选中的高亮
        if self._selected_card_widget is not None:
            self._selected_card_widget.setStyleSheet(
                f"""
                DataCard {{
                    background: {'#F8FAFC' if DESIGN_TOKENS_AVAILABLE else '#FFFFFF'};
                    border: 1px solid {'#E5E7EB' if DESIGN_TOKENS_AVAILABLE else '#E5E7EB'};
                    border-radius: 10px;
                    padding: 14px;
                }}
                DataCard:hover {{
                    border-color: {'#93C5FD' if DESIGN_TOKENS_AVAILABLE else '#3B82F6'};
                    background: {'#EFF6FF' if DESIGN_TOKENS_AVAILABLE else '#F0F7FF'};
                }}
                """
            )

        # 设置新选中
        self._selected_card_name = card_name
        self._selected_card_widget = card_widget

        # 高亮选中卡片
        card_widget.setStyleSheet(
            f"""
            DataCard {{
                background: {'#EFF6FF' if DESIGN_TOKENS_AVAILABLE else '#EBF5FF'};
                border: 2px solid {'#3B82F6' if DESIGN_TOKENS_AVAILABLE else '#2563EB'};
                border-radius: 10px;
                padding: 14px;
            }}
            """
        )

        # 更新标题
        self._chart_title_label.setText(f"实时曲线 — {card_name}")

        # 用已有历史数据重绘曲线
        self._refresh_chart_for_card(card_name)

    def _refresh_chart_for_card(self, card_name: str) -> None:
        """用指定变量的历史数据刷新曲线图（增量更新，避免闪烁）"""
        device_id = self._current_device_id or ""
        device_history = self._card_history.get(device_id, {})
        history = device_history.get(card_name, [])

        if not history:
            self._clear_chart()
            self._current_chart = None
            self._current_chart_card_name = None
            empty = QLabel("← 点击左侧数据卡片查看实时曲线")
            if DESIGN_TOKENS_AVAILABLE:
                empty.setStyleSheet(
                    f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px; background: transparent;"
                )
            else:
                empty.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._chart_layout.addWidget(empty)
            return

        try:
            from ui.widgets.visual import RealtimeChart
            import time

            if self._current_chart is not None and self._current_chart_card_name == card_name:
                self._current_chart.clear_series(card_name)
                self._current_chart.add_series(card_name, "#3B82F6")
                base_time = time.time() - len(history)
                for i, val in enumerate(history):
                    self._current_chart.add_point(card_name, base_time + i, float(val))
                self._current_chart.update()
                return

            self._clear_chart()

            chart = RealtimeChart(title="")
            chart.add_series(card_name, "#3B82F6")
            base_time = time.time() - len(history)
            for i, val in enumerate(history):
                chart.add_point(card_name, base_time + i, float(val))

            self._chart_layout.addWidget(chart)
            self._current_chart = chart
            self._current_chart_card_name = card_name
        except Exception as e:
            self._clear_chart()
            self._current_chart = None
            self._current_chart_card_name = None
            empty = QLabel(f"曲线图加载失败: {e}")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._chart_layout.addWidget(empty)

    def _clear_chart(self):
        """清空曲线图布局中的所有widget"""
        while self._chart_layout.count():
            item = self._chart_layout.itemAt(0)
            if item and item.widget():
                item.widget().deleteLater()
                self._chart_layout.removeItem(item)

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        """事件过滤器 — 处理卡片点击事件"""
        if event.type() == QEvent.Type.MouseButtonPress and obj in self._card_to_register:
            register_name = self._card_to_register[obj]
            self._on_card_clicked(register_name, obj)
            return True
        return QObject.eventFilter(self, obj, event)

    def update_selected_card_chart(self, card_name: str, value: float) -> None:
        """更新选中卡片的曲线图（增量添加单个数据点，不重建图表）"""
        device_id = self._current_device_id or ""
        if device_id not in self._card_history:
            self._card_history[device_id] = {}
        device_history = self._card_history[device_id]
        if card_name not in device_history:
            device_history[card_name] = []

        history = device_history[card_name]
        history.append(value)
        if len(history) > self._max_history_points:
            history.pop(0)

        if card_name == self._selected_card_name:
            if self._current_chart is not None and self._current_chart_card_name == card_name:
                import time

                self._current_chart.add_point(card_name, time.time(), float(value))
                self._current_chart.update()
            else:
                self._refresh_chart_for_card(card_name)

    def _build_register_tab(self) -> QWidget:
        from ui.widgets import DataTable

        tab = QWidget()
        layout = QVBoxLayout(tab)
        # 使用 DesignTokens 设置边距
        if DESIGN_TOKENS_AVAILABLE:
            layout.setContentsMargins(DT.S.MD, DT.S.MD, DT.S.MD, DT.S.MD)
        else:
            layout.setContentsMargins(8, 8, 8, 8)

        self._register_table = DataTable(columns=["Address", "Function Code", "Variable Name", "Value", "Unit"])
        self._register_table.horizontalHeader().setStretchLastSection(True)
        self._register_table.verticalHeader().setVisible(False)
        # 使用 DesignTokens 优化表格样式
        if DESIGN_TOKENS_AVAILABLE:
            table_font = DT.T.get_font(*DT.T.BODY_SMALL)
            self._register_table.setFont(table_font)
        layout.addWidget(self._register_table)

        return tab

    def update_cards_display(
        self,
        current_device_id: str,
        device_cards: Dict[str, Any],
        data_card_cls: type,
    ) -> None:
        self._current_device_id = current_device_id
        # 清空现有卡片和选中状态
        while self._device_cards_layout.count():
            item = self._device_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._card_widgets.clear()
        self._card_to_register.clear()
        self._selected_card_name = None
        self._selected_card_widget = None

        # 如果没有选择设备，显示提示信息
        if not current_device_id:
            empty_label = QLabel("请先选择一个设备")
            if DESIGN_TOKENS_AVAILABLE:
                empty_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px;")
            else:
                empty_label.setStyleSheet("color: #8B949E; font-size: 13px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._device_cards_layout.addWidget(empty_label)
            return

        cards_config = device_cards.get(current_device_id, [])

        # 如果没有卡片配置，显示提示信息
        if not cards_config:
            empty_label = QLabel("该设备暂无数据卡片配置")
            if DESIGN_TOKENS_AVAILABLE:
                empty_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px;")
            else:
                empty_label.setStyleSheet("color: #8B949E; font-size: 13px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._device_cards_layout.addWidget(empty_label)
            return

        first_card = None
        for config in cards_config:
            register_name = config.get("register_name", "")
            card_title = config.get("title", register_name)

            card = data_card_cls(title=card_title, value="--")
            card.register_name = register_name
            self._card_precision[register_name] = config.get("decimal_places", 2)

            if DESIGN_TOKENS_AVAILABLE:
                # 增加卡片最小尺寸确保文字完整显示
                card.setMinimumSize(150, 95)
                card.setStyleSheet(
                    f"""
                    DataCard {{
                        background-color: {DT.C.BG_PRIMARY};
                        border: 1px solid {DT.C.BORDER_DEFAULT};
                        border-radius: {DT.R.MD}px;
                        padding: {DT.S.XS}px;
                    }}
                    DataCard:hover {{
                        border-color: {DT.C.ACCENT_PRIMARY};
                        background-color: {DT.C.BG_HOVER};
                    }}
                """
                )
            else:
                # 增加卡片最小尺寸确保文字完整显示
                card.setMinimumSize(140, 90)

            # 单位已由 _update_card_values 合入 value_label 中，不再需要独立 unit_label

            # 点击事件：切换选中卡片并更新曲线图（使用事件过滤器替代monkey-patch）
            card.installEventFilter(self)
            self._card_to_register[card] = register_name

            self._device_cards_layout.addWidget(card)
            self._card_widgets[register_name] = card

            if first_card is None:
                first_card = (register_name, card)

        # 自动选中第一张卡片
        if first_card:
            name, widget = first_card
            QTimer.singleShot(100, lambda n=name, w=widget: self._on_card_clicked(n, w))

    def get_register_table(self):
        return self._register_table

    def get_chart_layout(self):
        return self._chart_layout

    def get_monitor_tabs(self):
        return self._monitor_tabs

    def get_card_widget(self, register_name: str):
        """根据寄存器名称获取数据卡片控件"""
        return self._card_widgets.get(register_name)

    def get_all_card_widgets(self) -> dict:
        """获取所有卡片控件的字典 {register_name: DataCard}"""
        return dict(self._card_widgets)

    def get_first_card(self) -> Optional["DataCard"]:
        """获取第一张数据卡片"""
        for card in self._card_widgets.values():
            return card
        return None

    def get_card_count(self) -> int:
        """获取当前卡片数量"""
        return len(self._card_widgets)

    def get_card_precision(self, register_name: str) -> int:
        """获取指定卡片的显示小数位数"""
        return self._card_precision.get(register_name, 2)

    def clear_all_cards(self) -> None:
        """清空所有数据卡片，显示默认状态"""
        self._selected_card_name = None
        self._selected_card_widget = None
        self._current_chart = None
        self._current_chart_card_name = None
        self._card_precision.clear()
        self._card_to_register.clear()
        device_id = self._current_device_id or ""
        self._card_history.pop(device_id, None)
        while self._device_cards_layout.count():
            item = self._device_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._card_widgets.clear()
        self._clear_chart()

    # ═══════════════════════════════════════════════════════════
    # 公共属性接口 (Public Properties)
    # 提供对内部控件的受控访问，避免直接访问私有属性
    # ═══════════════════════════════════════════════════════════

    @property
    def expand_btn(self) -> QPushButton:
        """展开/折叠按钮"""
        return self._expand_btn

    @property
    def device_title_label(self) -> QLabel:
        """设备标题标签"""
        return self._device_title_label

    @property
    def device_name_label(self) -> QLabel:
        """设备名称标签"""
        return self._device_name_label

    @property
    def device_desc_label(self) -> QLabel:
        """设备描述标签"""
        return self._device_desc_label

    @property
    def last_update_label(self) -> QLabel:
        """最后更新时间标签"""
        return self._last_update_label

    @property
    def device_status_badge(self) -> "AnimatedStatusBadge":
        """设备状态徽章"""
        return self._device_status_badge

    @property
    def right_splitter(self) -> QSplitter:
        """右侧分割器"""
        return self._right_splitter

    @property
    def monitor_tabs(self) -> QTabWidget:
        """监控页标签控件"""
        return self._monitor_tabs

    @property
    def data_cards_layout(self) -> QGridLayout:
        """数据卡片布局"""
        return self._device_cards_layout

    @property
    def chart_layout(self) -> QVBoxLayout:
        """图表布局"""
        return self._chart_layout

    def get_all_widgets(self) -> Dict[str, QWidget]:
        """
        获取所有关键控件的字典

        Returns:
            Dict[str, QWidget]: 控件名称到控件的映射
        """
        return {
            "expand_btn": self._expand_btn,
            "device_title_label": self._device_title_label,
            "device_name_label": self._device_name_label,
            "last_update_label": self._last_update_label,
            "device_status_badge": self._device_status_badge,
            "right_splitter": self._right_splitter,
            "monitor_tabs": self._monitor_tabs,
            "data_cards_layout_widget": self._device_cards_layout,
            "chart_layout_widget": self._chart_layout,
            "register_table": self.get_register_table(),
        }
