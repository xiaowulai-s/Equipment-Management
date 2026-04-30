# -*- coding: utf-8 -*-
"""Monitor page controller."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt
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


class MonitorPageController:
    """Encapsulates monitor page creation, card/chart display, and register table."""

    def __init__(self) -> None:
        self._device_cards_layout: Optional[QGridLayout] = None
        self._chart_layout: Optional[QVBoxLayout] = None
        self._register_table: Optional[QWidget] = None
        self._monitor_tabs: Optional[QTabWidget] = None
        self._device_name_label: Optional[QLabel] = None
        self._last_update_label: Optional[QLabel] = None
        self._expand_btn: Optional[QPushButton] = None
        self._manage_cards_btn: Optional[QPushButton] = None
        self._manage_charts_btn: Optional[QPushButton] = None
        self._right_splitter: Optional[QSplitter] = None
        self._on_manage_cards_cb: Optional[Callable] = None
        self._on_manage_charts_cb: Optional[Callable] = None
        self._on_expand_panel_cb: Optional[Callable] = None
        self._on_command_send_cb: Optional[Callable] = None

    def build(
        self,
        parent: QWidget,
        styles: dict,
        constants: dict,
        on_manage_cards: Callable,
        on_manage_charts: Callable,
        on_expand_panel: Callable,
        on_command_send: Callable,
        command_terminal_cls: type,
    ) -> QWidget:
        self._on_manage_cards_cb = on_manage_cards
        self._on_manage_charts_cb = on_manage_charts
        self._on_expand_panel_cb = on_expand_panel
        self._on_command_send_cb = on_command_send

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
            info_container.setStyleSheet(f"""
                background-color: {DT.C.BG_SECONDARY};
                border-radius: {DT.R.SM}px;
                padding: {DT.S.SM}px;
            """)
        else:
            info_container.setStyleSheet("""
                background-color: #F6F8FA;
                border-radius: 6px;
                padding: 8px;
            """)
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(16)

        # 设备名称（主要信息）
        self._device_name_label = QLabel("未选择设备")
        if DESIGN_TOKENS_AVAILABLE:
            name_font = DT.T.get_font(*DT.T.BODY)
            self._device_name_label.setFont(name_font)
            self._device_name_label.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY}; background: transparent; font-weight: 500;")
        else:
            self._device_name_label.setStyleSheet("color: #24292F; font-size: 14px; font-weight: 500; background: transparent;")
        info_layout.addWidget(self._device_name_label)

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

        command_terminal = command_terminal_cls(compact=True)
        command_terminal.command_sent.connect(on_command_send)
        self._right_splitter.addWidget(command_terminal)

        # 垂直分割器配置（支持自适应调整）
        self._right_splitter.setStretchFactor(0, 7)   # 监控区域占70%
        self._right_splitter.setStretchFactor(1, 3)   # 命令终端占30%
        
        # 初始尺寸基于可用高度动态计算（将在 showEvent 中更新）
        initial_height = max(self.height() if hasattr(self, 'height') else 600, 400)
        monitor_h = int(initial_height * 0.70)  # 监控区70%
        terminal_h = int(initial_height * 0.30)  # 终端区30%
        self._right_splitter.setSizes([monitor_h, terminal_h])

        layout.addWidget(self._right_splitter)

        self._command_terminal = command_terminal
        self._device_status_badge = device_status_badge

        return page

    def _build_data_tab(self, styles: dict) -> QWidget:
        from ui.widgets import SecondaryButton

        tab = QWidget()
        layout = QVBoxLayout(tab)
        # 紧凑的边距和间距
        if DESIGN_TOKENS_AVAILABLE:
            layout.setContentsMargins(DT.S.SM, DT.S.SM, DT.S.SM, DT.S.SM)
            layout.setSpacing(DT.S.MD)
        else:
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(16)

        # ═══ 实时趋势图区域（紧凑型）═══
        chart_header_layout = QHBoxLayout()
        chart_header_layout.setSpacing(8)

        chart_title = QLabel("实时趋势图")
        if DESIGN_TOKENS_AVAILABLE:
            title_font = DT.T.get_font(*DT.T.LABEL)  # 使用LABEL而非LABEL_LARGE
            chart_title.setFont(title_font)
            chart_title.setStyleSheet(f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};")
        else:
            chart_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #57606A; background: transparent;")
        chart_header_layout.addWidget(chart_title)
        chart_header_layout.addStretch()

        self._manage_charts_btn = SecondaryButton("管理趋势图")
        self._manage_charts_btn.setFixedSize(100, 28)  # 更小的按钮
        if self._on_manage_charts_cb:
            self._manage_charts_btn.clicked.connect(self._on_manage_charts_cb)
        chart_header_layout.addWidget(self._manage_charts_btn)

        layout.addLayout(chart_header_layout)

        # 图表容器
        chart_container = QWidget()
        chart_container.setMinimumHeight(200)  # 进一步减小高度
        if DESIGN_TOKENS_AVAILABLE:
            chart_container.setStyleSheet(f"""
                background-color: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_SUBTLE};
                border-radius: {DT.R.SM}px;
            """)
        else:
            chart_container.setStyleSheet("""
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
            """)

        self._chart_layout = QVBoxLayout(chart_container)
        if DESIGN_TOKENS_AVAILABLE:
            self._chart_layout.setContentsMargins(DT.S.MD, DT.S.MD, DT.S.MD, DT.S.MD)
            self._chart_layout.setSpacing(DT.S.SM)
        else:
            self._chart_layout.setContentsMargins(12, 12, 12, 12)
            self._chart_layout.setSpacing(8)

        # 空状态提示
        self._chart_empty_label = QLabel("暂无趋势图数据")
        if DESIGN_TOKENS_AVAILABLE:
            self._chart_empty_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px; background: transparent;")
        else:
            self._chart_empty_label.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent;")
        self._chart_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chart_layout.addWidget(self._chart_empty_label)

        layout.addWidget(chart_container)

        # ═══ 数据卡片区域（紧凑型）═══
        cards_header_layout = QHBoxLayout()
        cards_header_layout.setSpacing(8)

        cards_title = QLabel("数据卡片")
        if DESIGN_TOKENS_AVAILABLE:
            cards_title_font = DT.T.get_font(*DT.T.LABEL)  # 使用LABEL而非LABEL_LARGE
            cards_title.setFont(cards_title_font)
            cards_title.setStyleSheet(f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};")
        else:
            cards_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #57606A; background: transparent;")
        cards_header_layout.addWidget(cards_title)
        cards_header_layout.addStretch()

        self._manage_cards_btn = SecondaryButton("管理卡片")
        self._manage_cards_btn.setFixedSize(100, 28)  # 更小的按钮
        if self._on_manage_cards_cb:
            self._manage_cards_btn.clicked.connect(self._on_manage_cards_cb)
        cards_header_layout.addWidget(self._manage_cards_btn)

        layout.addLayout(cards_header_layout)

        # 数据卡片网格布局
        self._device_cards_layout = QGridLayout()
        if DESIGN_TOKENS_AVAILABLE:
            self._device_cards_layout.setSpacing(DT.S.MD)
            self._device_cards_layout.setContentsMargins(DT.S.ZERO, DT.S.XS, DT.S.ZERO, DT.S.ZERO)
        else:
            self._device_cards_layout.setSpacing(12)
            self._device_cards_layout.setContentsMargins(0, 4, 0, 0)
        layout.addLayout(self._device_cards_layout)

        # 弹性空间
        layout.addStretch()

        return tab

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
        # 清空现有卡片
        while self._device_cards_layout.count():
            item = self._device_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 如果没有选择设备，显示提示信息
        if not current_device_id:
            empty_label = QLabel("请先选择一个设备")
            if DESIGN_TOKENS_AVAILABLE:
                empty_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px;")
            else:
                empty_label.setStyleSheet("color: #8B949E; font-size: 13px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._device_cards_layout.addWidget(empty_label, 0, 0)
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
            self._device_cards_layout.addWidget(empty_label, 0, 0)
            return

        row, col = 0, 0
        max_cols = 3

        for config in cards_config:
            card = data_card_cls(
                title=config.get("title", ""),
                value="--",
            )
            card.register_name = config.get("register_name", "")

            # 使用 DesignTokens 优化卡片样式
            if DESIGN_TOKENS_AVAILABLE:
                card.setMinimumSize(160, 120)  # 增大最小尺寸以改善可读性
                # 应用 Fluent Design 卡片样式
                card.setStyleSheet(f"""
                    DataCard {{
                        background-color: {DT.C.BG_PRIMARY};
                        border: 1px solid {DT.C.BORDER_DEFAULT};
                        border-radius: {DT.R.LG}px;
                        padding: {DT.S.MD}px;
                    }}
                    DataCard:hover {{
                        border-color: {DT.C.ACCENT_PRIMARY};
                        background-color: {DT.C.BG_HOVER};
                    }}
                """)
            else:
                card.setMinimumSize(140, 100)

            unit = config.get("unit", "")
            if unit:
                card.unit_label = QLabel(unit)
                # 使用 DesignTokens 统一单位标签样式
                if DESIGN_TOKENS_AVAILABLE:
                    unit_font = DT.T.get_font(*DT.T.CAPTION)
                    card.unit_label.setFont(unit_font)
                    card.unit_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.CAPTION[1]}px; background: transparent;")
                else:
                    card.unit_label.setStyleSheet("color: #8B949E; font-size: 12px;")
                card.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                card.layout().addWidget(card.unit_label)

            self._device_cards_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def get_command_terminal(self):
        return getattr(self, "_command_terminal", None)

    def get_register_table(self):
        return self._register_table

    def get_chart_layout(self):
        return self._chart_layout

    def get_monitor_tabs(self):
        return self._monitor_tabs

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
    def last_update_label(self) -> QLabel:
        """最后更新时间标签"""
        return self._last_update_label

    @property
    def device_status_badge(self) -> 'AnimatedStatusBadge':
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

    @property
    def manage_cards_btn(self) -> QPushButton:
        """管理卡片按钮"""
        return self._manage_cards_btn

    @property
    def manage_charts_btn(self) -> QPushButton:
        """管理图表按钮"""
        return self._manage_charts_btn

    def get_all_widgets(self) -> Dict[str, QWidget]:
        """
        获取所有关键控件的字典

        Returns:
            Dict[str, QWidget]: 控件名称到控件的映射
        """
        return {
            'expand_btn': self._expand_btn,
            'device_title_label': self._device_title_label,
            'device_name_label': self._device_name_label,
            'last_update_label': self._last_update_label,
            'device_status_badge': self._device_status_badge,
            'right_splitter': self._right_splitter,
            'monitor_tabs': self._monitor_tabs,
            'data_cards_layout_widget': self._device_cards_layout,
            'chart_layout_widget': self._chart_layout,
            'manage_cards_btn': self._manage_cards_btn,
            'manage_charts_btn': self._manage_charts_btn,
            'command_terminal': self.get_command_terminal(),
            'register_table': self.get_register_table(),
        }
