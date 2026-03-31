# -*- coding: utf-8 -*-
"""
Main Window v2 - Industrial Equipment Management System
Refactored with maintainable constants and clear text mappings
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QTimer, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTableWidget  # noqa: F401  (base class of DataTable)
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.data import DatabaseManager
from core.device.device_manager_v2 import DeviceManagerV2
from core.device.device_model import DeviceStatus
from core.utils.alarm_manager import AlarmLevel, AlarmManager, AlarmRule, AlarmType
from core.utils.data_exporter import DataExporter
from core.utils.logger_v2 import get_logger
from ui.add_device_dialog import AddDeviceDialog
from ui.app_styles import AppStyles
from ui.batch_operations_dialog import BatchOperationsDialog
from ui.core import ThemeManager
from ui.device_type_dialogs import DeviceTypeDialog
from ui.widgets import (
    DangerButton,
    DataCard,
    DataTable,
    DeviceTree,
    GhostButton,
    LineEdit,
    PrimaryButton,
    SecondaryButton,
    StatusBadge,
    SuccessButton,
)


if TYPE_CHECKING:
    from core.device.device_model import Device  # noqa: F401

logger = get_logger("main_window_v2")


class TextConstants:
    """UI text constants - centralized for easy maintenance"""

    APP_NAME = "工业设备管理系统"
    APP_VERSION = "1.6.0"
    WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"

    DEVICE_LIST_TITLE = "设备列表"
    ADD_DEVICE_BTN = "添加设备"
    REMOVE_DEVICE_BTN = "移除设备"
    SEARCH_PLACEHOLDER = "搜索设备名称..."

    WELCOME_TITLE = "欢迎使用工业设备管理系统"
    WELCOME_SUBTITLE = "请从左侧面板选择设备进行监控"

    DEVICE_MONITOR_TITLE = "设备监控"
    DEVICE_NAME_LABEL = "设备名称:"
    STATUS_LABEL = "状态:"
    LAST_UPDATE_LABEL = "最后更新:"

    TAB_REALTIME_DATA = "实时数据"
    TAB_REGISTERS = "寄存器"

    TREE_HEADER_NAME = "设备名称"
    TREE_HEADER_ID = "设备 ID"
    TREE_HEADER_STATUS = "状态"
    TREE_HEADER_ACTIONS = "操作"

    BTN_EDIT = "编辑"
    BTN_CONNECT = "连接"
    BTN_DISCONNECT = "断开"

    MENU_FILE = "文件 (&F)"
    MENU_TOOLS = "工具 (&T)"
    MENU_HELP = "帮助 (&H)"

    ACTION_DEVICE_TYPE_MGMT = "设备类型管理 (&T)"
    ACTION_ALARM_RULE_CONFIG = "报警规则配置 (&C)"
    ACTION_ALARM_SETTINGS = "报警设置 (&A)"
    ACTION_DATA_EXPORT = "数据导出 (&E)"
    ACTION_BATCH_OPS = "批量操作"
    ACTION_EXIT = "退出 (&X)"
    ACTION_ALARM_HISTORY = "报警历史 (&H)"
    ACTION_ABOUT = "关于 (&A)"


class StatusText:
    """Device status text and badge type mappings"""

    STATUS_MAP = {
        DeviceStatus.CONNECTED: ("已连接", "success"),
        DeviceStatus.DISCONNECTED: ("未连接", "warning"),
        DeviceStatus.CONNECTING: ("连接中...", "info"),
        DeviceStatus.ERROR: ("错误", "error"),
    }

    @classmethod
    def get_text(cls, status: int) -> str:
        return cls.STATUS_MAP.get(status, ("Unknown", "default"))[0]

    @classmethod
    def get_badge_type(cls, status: int) -> str:
        return cls.STATUS_MAP.get(status, ("Unknown", "default"))[1]

    @classmethod
    def get_text_with_badge(cls, status: int) -> tuple:
        return cls.STATUS_MAP.get(status, ("Unknown", "default"))


class LogMessages:
    """Log message templates"""

    APP_STARTUP = "应用程序已启动"
    APP_SHUTDOWN = "应用程序已关闭"
    DB_INIT_SUCCESS = "数据库初始化成功"

    DEVICE_ADDED = "设备已添加：{device_id}"
    DEVICE_REMOVED = "设备已移除：{device_id}"
    DEVICE_CONNECTED = "设备已连接：{device_id}"
    DEVICE_DISCONNECTED = "设备已断开：{device_id}"
    DEVICE_CONNECTING = "正在连接设备：{device_id}"
    DEVICE_CONNECT_FAILED = "设备连接失败：{device_id}"

    DEVICE_EDIT_SUCCESS = "设备已更新：{device_id}"
    DEVICE_EDIT_FAILED = "设备更新失败：{device_id}"

    BATCH_OPS_COMPLETE = "批量操作完成：{success}/{total} 成功"

    ALARM_RULES_UPDATED = "报警规则已更新"
    DATA_EXPORT_SUCCESS = "数据已导出至：{path}"
    DATA_EXPORT_FAILED = "数据导出失败"


class UIMessages:
    """User interface message templates"""

    CONFIRM_DELETE_TITLE = "确认删除"
    CONFIRM_DELETE_MSG = "确定要删除此设备吗？"

    CONNECT_FAILED_TITLE = "连接失败"
    CONNECT_FAILED_MSG = "无法连接到设备"

    SELECT_DEVICE_TITLE = "选择设备"
    SELECT_DEVICE_MSG = "请先选择一个设备"

    EXPORT_SUCCESS_TITLE = "导出成功"
    EXPORT_SUCCESS_MSG = "数据已导出至:\n{path}"

    EXPORT_FAILED_TITLE = "导出失败"
    EXPORT_FAILED_MSG = "数据导出失败，请检查文件格式或权限"

    NO_ALARM_HISTORY_TITLE = "报警历史"
    NO_ALARM_HISTORY_MSG = "无报警记录"

    ALARM_DIALOG_TITLE = "报警设置"
    ALARM_DIALOG_MSG = (
        "报警设置功能正在开发中...\n\n"
        "默认启用的报警规则:\n"
        "- 温度过高 (>80°C)\n"
        "- 压力过高 (>2.0MPa)\n\n"
        "请使用'报警规则配置'进行详细设置。"
    )

    ABOUT_TITLE = "关于"
    ABOUT_MSG = (
        f"{TextConstants.APP_NAME} v{TextConstants.APP_VERSION}\n\n"
        "基于 PySide6 和 Modbus 协议的工业设备监控软件\n"
        "采用四层解耦架构设计\n\n"
        "功能特性:\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "【协议支持】\n"
        "  • Modbus TCP - 以太网通信\n"
        "  • Modbus RTU - 串口通信\n"
        "  • Modbus ASCII - ASCII编码通信\n\n"
        "【设备管理】\n"
        "  • 多设备并发管理 (100+设备、20000+寄存器)\n"
        "  • 设备增删改查、搜索、批量操作\n"
        "  • JSON配置持久化\n"
        "  • 自动重连和失败重试\n\n"
        "【数据可视化】\n"
        "  • DataCard 数据卡片\n"
        "  • Canvas 仪表盘\n"
        "  • 实时趋势图\n"
        "  • 高性能实时曲线图\n\n"
        "【报警系统】\n"
        "  • 四级报警 (高高/高/低/低低)\n"
        "  • 死区控制，防止频繁报警\n"
        "  • 报警确认、历史记录、统计分析\n\n"
        "【系统功能】\n"
        "  • Fluent Design 风格主题\n"
        "  • 数据导出 (CSV/Excel)\n"
        "  • 日志查看器\n"
        "  • 设备仿真模式\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Power By 喝口阔落"
    )


class MainWindowV2(QMainWindow):
    """
    主窗口 v2 - 工业设备管理系统

    提供完整的设备管理功能，包括：
    - 设备列表管理
    - 实时数据监控
    - 报警系统
    - 数据导出
    - 批量操作
    - 主题切换

    Attributes:
        _db_manager: 数据库管理器
        _device_manager: 设备管理器
        _alarm_manager: 报警管理器
        _theme_manager: 主题管理器
        _current_device_id: 当前选中设备ID
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None) -> None:
        """
        初始化主窗口

        Args:
            db_manager: 数据库管理器实例，为None时自动创建
            parent: 父窗口
        """
        super().__init__(parent)

        self._db_manager = db_manager or DatabaseManager()
        self._device_manager = DeviceManagerV2(db_manager=self._db_manager)
        self._alarm_manager = AlarmManager()
        self._theme_manager = ThemeManager()
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._sort_column = 0
        self._current_device_id: Optional[str] = None
        self._left_panel_collapsed = False
        self._left_panel_saved_size = 480

        # 数据卡片配置存储: {device_id: [card_configs]}
        self._device_cards: Dict[str, List[Dict[str, Any]]] = {}

        # 趋势图配置存储: {device_id: [chart_configs]}
        self._device_charts: Dict[str, List[Dict[str, Any]]] = {}

        # 数据清理调度器
        from core.data.cleanup_scheduler import CleanupScheduler

        self._cleanup_scheduler = CleanupScheduler(self._db_manager)
        self._cleanup_scheduler.start()

        self._init_ui()
        self._connect_signals()
        self._setup_alarm_rules()
        self._refresh_device_list()
        self._apply_theme()

        logger.info(LogMessages.APP_STARTUP)

    def _init_ui(self) -> None:
        self.setWindowTitle(TextConstants.WINDOW_TITLE)
        self.setMinimumSize(1600, 900)

        self._create_menu_bar()

        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)

        main_layout = QVBoxLayout(self._central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_tool_bar()

        # ── QSplitter: 左面板 + 右面板 + 报文生成工具 ──
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self._splitter)

        # 左侧面板
        self._left_panel = self._create_left_panel()
        self._splitter.addWidget(self._left_panel)

        # 中间面板 (StackedWidget: 监控页面)
        self._stack_widget = QStackedWidget()
        self._stack_widget.setStyleSheet(AppStyles.STACKED_WIDGET)
        self._stack_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        welcome_page = self._create_welcome_page()
        self._stack_widget.addWidget(welcome_page)

        monitor_page = self._create_monitor_page()
        self._stack_widget.addWidget(monitor_page)

        self._splitter.addWidget(self._stack_widget)

        # 右侧面板 (报文生成工具)
        from ui.modbus_generator_widget import ModbusGeneratorWidget

        self._modbus_generator = ModbusGeneratorWidget()
        self._modbus_generator.setVisible(False)  # 默认隐藏
        self._splitter.addWidget(self._modbus_generator)

        # 默认显示监控页面（显示日志栏目）
        self._stack_widget.setCurrentIndex(1)
        self._log_message("程序启动，等待设备连接...", "INFO")

        # Splitter 配置
        self._splitter.setStretchFactor(0, 15)
        self._splitter.setStretchFactor(1, 70)
        self._splitter.setStretchFactor(2, 15)
        self._splitter.setSizes([self._left_panel_saved_size, 1100, 0])
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)
        self._splitter.setCollapsible(2, True)
        self._splitter.setStyleSheet(AppStyles.SPLITTER)
        self._splitter.splitterMoved.connect(self._on_splitter_moved)

        # ── 折叠/展开浮动按钮 ──
        self._create_collapse_buttons()

        self._create_status_bar()

    def _create_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu(TextConstants.MENU_FILE)

        device_type_action = file_menu.addAction(TextConstants.ACTION_DEVICE_TYPE_MGMT)
        device_type_action.triggered.connect(self._show_device_type_dialog)

        file_menu.addSeparator()

        alarm_config_action = file_menu.addAction(TextConstants.ACTION_ALARM_RULE_CONFIG)
        alarm_config_action.triggered.connect(self._show_alarm_config_dialog)

        alarm_action = file_menu.addAction(TextConstants.ACTION_ALARM_SETTINGS)
        alarm_action.triggered.connect(self._show_alarm_dialog)

        export_action = file_menu.addAction(TextConstants.ACTION_DATA_EXPORT)
        export_action.triggered.connect(self._show_export_dialog)

        file_menu.addSeparator()

        exit_action = file_menu.addAction(TextConstants.ACTION_EXIT)
        exit_action.triggered.connect(self.close)

        tools_menu = menubar.addMenu(TextConstants.MENU_TOOLS)

        # 报文生成工具
        self._modbus_gen_action = tools_menu.addAction("报文生成工具")
        self._modbus_gen_action.setCheckable(True)
        self._modbus_gen_action.triggered.connect(self._toggle_modbus_generator)

        tools_menu.addSeparator()

        alarm_history_action = tools_menu.addAction(TextConstants.ACTION_ALARM_HISTORY)
        alarm_history_action.triggered.connect(self._show_alarm_history)

        help_menu = menubar.addMenu(TextConstants.MENU_HELP)

        about_action = help_menu.addAction(TextConstants.ACTION_ABOUT)
        about_action.triggered.connect(self._show_about)

    def _create_tool_bar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(AppStyles.TOOLBAR)
        self.addToolBar(toolbar)

    def _create_status_bar(self) -> None:
        status_bar = self.statusBar()
        status_bar.setStyleSheet(AppStyles.STATUSBAR)

        # 左侧消息区域
        self._status_msg_label = QLabel("就绪")
        self._status_msg_label.setStyleSheet("color: #6B7280; font-size: 12px; padding: 0 8px;")
        status_bar.addWidget(self._status_msg_label)

        # 分隔符
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: #D1D5DB; font-size: 12px; padding: 0 4px;")
        status_bar.addPermanentWidget(sep1)

        # 设备统计标签（彩色圆点 + 数字）
        self._status_total_label = self._make_status_label("设备 0", "#374151")
        status_bar.addPermanentWidget(self._status_total_label)

        # 在线
        self._status_online_label = self._make_status_label("● 在线 0", "#4CAF50")
        status_bar.addPermanentWidget(self._status_online_label)

        # 离线
        self._status_offline_label = self._make_status_label("● 离线 0", "#9E9E9E")
        status_bar.addPermanentWidget(self._status_offline_label)

        # 错误
        self._status_error_label = self._make_status_label("● 错误 0", "#F44336")
        status_bar.addPermanentWidget(self._status_error_label)

        # 分隔符
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: #D1D5DB; font-size: 12px; padding: 0 4px;")
        status_bar.addPermanentWidget(sep2)

        # 自动重连状态
        self._status_auto_reconnect_enabled = self._make_status_label("● 自动重连启用 0", "#2196F3")
        status_bar.addPermanentWidget(self._status_auto_reconnect_enabled)

        self._status_auto_reconnect_disabled = self._make_status_label("● 自动重连禁用 0", "#FF9800")
        status_bar.addPermanentWidget(self._status_auto_reconnect_disabled)

    @staticmethod
    def _make_status_label(text: str, color: str) -> QLabel:
        """创建状态栏统计标签"""
        label = QLabel(text)
        label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500; padding: 0 8px;")
        return label

    # ═══════════════════════════════════════════════════════════
    # 折叠/展开按钮系统
    # ═══════════════════════════════════════════════════════════

    def _create_collapse_buttons(self) -> None:
        """创建折叠和展开浮动按钮.

        按钮是 central_widget 的子控件, 通过绝对定位放置在
        splitter 左侧面板右边缘, 始终跟随面板拉伸移动。
        """
        # 折叠按钮 (面板展开时显示)
        self._collapse_btn = QPushButton("◀", self._central_widget)
        self._collapse_btn.setFixedSize(20, 48)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.setToolTip("折叠面板")
        self._apply_edge_btn_style(self._collapse_btn)
        self._collapse_btn.clicked.connect(self._collapse_left_panel)

        # 展开按钮 (面板折叠后显示)
        self._expand_btn = QPushButton("▶", self._central_widget)
        self._expand_btn.setFixedSize(20, 48)
        self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expand_btn.setToolTip("展开面板")
        self._apply_edge_btn_style(self._expand_btn)
        self._expand_btn.clicked.connect(self._expand_left_panel)

        self._expand_btn.hide()

        # 初始定位 (延迟到布局完成后)
        QTimer.singleShot(0, self._reposition_edge_buttons)

    def _apply_edge_btn_style(self, btn: QPushButton) -> None:
        """为边缘按钮设置主题感知的右侧圆角样式."""
        colors = self._theme_manager.colors
        bg = colors.bg_hover
        border_right = f"1px solid {colors.border_default}"
        border_top = f"1px solid {colors.border_default}"
        border_bottom = f"1px solid {colors.border_default}"

        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {bg};
                color: {colors.text_secondary};
                border-top: {border_top};
                border-right: {border_right};
                border-bottom: {border_bottom};
                border-left: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                padding: 0px 4px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background: {colors.bg_overlay};
                color: {colors.text_primary};
            }}
        """
        )

    def _reposition_edge_buttons(self) -> None:
        """重新定位折叠/展开按钮到左侧面板右边缘."""
        # 左面板在 central_widget 中的位置
        panel_geo = self._left_panel.geometry()

        # 按钮位于面板右边缘, 垂直居中
        x = panel_geo.right() - 10  # 按钮宽度一半覆盖边缘
        y = panel_geo.center().y() - 24  # 按钮高度一半

        self._collapse_btn.move(x, y)
        self._expand_btn.move(0, y)  # 展开按钮固定在最左侧

    def _collapse_left_panel(self) -> None:
        """折叠左侧面板."""
        self._left_panel_saved_size = self._splitter.sizes()[0]
        self._left_panel.setVisible(False)
        self._collapse_btn.hide()
        self._expand_btn.show()
        self._left_panel_collapsed = True
        self._reposition_edge_buttons()

    def _expand_left_panel(self) -> None:
        """展开左侧面板."""
        self._left_panel.setVisible(True)
        self._expand_btn.hide()
        self._collapse_btn.show()
        self._left_panel_collapsed = False
        # 恢复之前的大小
        total = self._splitter.width()
        left_size = min(self._left_panel_saved_size, total - 300)
        self._splitter.setSizes([left_size, total - left_size])
        QTimer.singleShot(50, self._reposition_edge_buttons)
        QTimer.singleShot(50, self._update_tree_adaptive_sizes)

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Splitter 拉动时重新定位按钮并自适应调整."""
        if not self._left_panel_collapsed:
            self._reposition_edge_buttons()
            self._update_tree_adaptive_sizes()

    def resizeEvent(self, event) -> None:
        """窗口缩放时重新定位按钮."""
        super().resizeEvent(event)
        QTimer.singleShot(0, self._reposition_edge_buttons)

    def showEvent(self, event) -> None:
        """窗口显示时初始化按钮位置."""
        super().showEvent(event)
        QTimer.singleShot(0, self._reposition_edge_buttons)

    def _create_left_panel(self) -> QWidget:
        left_widget = QWidget()
        # 最小宽度计算:
        # - 边距左右各 12px = 24px
        # - 设备名称列(Stretch) 最小 ~120px
        # - 设备编号列(Stretch) 最小 ~80px
        # - 状态列(Stretch) 最小 ~60px
        # - 操作列(Fixed) 170px (两按钮各58px + 间距6px + 边距)
        # 总计: 24 + 120 + 80 + 60 + 170 = 454px → 取整 460px
        left_widget.setMinimumWidth(460)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        # 浅色背景
        left_widget.setStyleSheet("background-color: #FFFFFF;")

        # ── 标题行 ──
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        self._left_title_label = QLabel(TextConstants.DEVICE_LIST_TITLE)
        self._left_title_label.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self._left_title_label.setStyleSheet("color: #24292F; background: transparent;")
        title_layout.addWidget(self._left_title_label)
        title_layout.addStretch()

        left_layout.addLayout(title_layout)

        # ── 搜索框 ──
        self._search_edit = LineEdit(TextConstants.SEARCH_PLACEHOLDER)
        self._search_edit.setMinimumHeight(30)
        self._search_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search_edit.textChanged.connect(self._filter_devices)
        left_layout.addWidget(self._search_edit)

        # ── 设备树 (弹性拉伸) ──
        self._device_tree = DeviceTree(self)
        self._device_tree.currentItemChanged.connect(self._on_device_selected)
        self._device_tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self._device_tree, 1)

        # ── 底部按钮行 ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)  # 增加按钮之间的间距
        btn_layout.setContentsMargins(16, 16, 16, 16)  # 添加边距

        # 自动重连控制按钮 - 放置在添加设备按钮左侧
        self._auto_reconnect_btn = PrimaryButton("启用重连")
        self._auto_reconnect_btn.setCheckable(True)
        self._auto_reconnect_btn.setChecked(True)
        self._auto_reconnect_btn.setMinimumHeight(36)
        self._auto_reconnect_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._auto_reconnect_btn.clicked.connect(self._toggle_all_auto_reconnect)
        self._auto_reconnect_btn.setToolTip("切换所有设备的自动重连功能")

        self._add_device_btn = SuccessButton(TextConstants.ADD_DEVICE_BTN)
        self._add_device_btn.setMinimumHeight(36)
        self._add_device_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._add_device_btn.clicked.connect(self._add_device)

        self._batch_ops_btn = PrimaryButton(TextConstants.ACTION_BATCH_OPS)
        self._batch_ops_btn.setMinimumHeight(36)
        self._batch_ops_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._batch_ops_btn.clicked.connect(self._show_batch_operations)

        self._remove_btn = DangerButton(TextConstants.REMOVE_DEVICE_BTN)
        self._remove_btn.setMinimumHeight(36)
        self._remove_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._remove_btn.clicked.connect(self._remove_device)

        btn_layout.addWidget(self._auto_reconnect_btn)
        btn_layout.addWidget(self._add_device_btn)
        btn_layout.addWidget(self._batch_ops_btn)
        btn_layout.addWidget(self._remove_btn)
        left_layout.addLayout(btn_layout)

        return left_widget

    def _create_welcome_page(self) -> QWidget:
        welcome_page = QWidget()
        welcome_layout = QVBoxLayout(welcome_page)
        welcome_layout.setContentsMargins(40, 40, 40, 40)
        welcome_layout.setSpacing(20)

        welcome_label = QLabel(TextConstants.WELCOME_TITLE)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        welcome_label.setStyleSheet("color: #24292F;")
        welcome_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        welcome_layout.addWidget(welcome_label)

        welcome_sub_label = QLabel(TextConstants.WELCOME_SUBTITLE)
        welcome_sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_sub_label.setFont(QFont("Inter", 14))
        welcome_sub_label.setStyleSheet("color: #57606A;")
        welcome_sub_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        welcome_layout.addWidget(welcome_sub_label)
        welcome_layout.addStretch()

        return welcome_page

    def _create_monitor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self._device_title_label = QLabel(TextConstants.DEVICE_MONITOR_TITLE)
        self._device_title_label.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        self._device_title_label.setStyleSheet("color: #24292F;")
        layout.addWidget(self._device_title_label)

        info_layout = QHBoxLayout()
        self._device_name_label = QLabel(f"{TextConstants.DEVICE_NAME_LABEL} -")
        self._device_name_label.setStyleSheet("color: #57606A; font-size: 13px;")
        self._device_status_badge = StatusBadge("Not Connected", "error")
        self._last_update_label = QLabel(f"{TextConstants.LAST_UPDATE_LABEL} -")
        self._last_update_label.setStyleSheet("color: #8B949E; font-size: 12px;")

        info_layout.addWidget(self._device_name_label)
        info_layout.addWidget(self._device_status_badge)
        info_layout.addStretch()
        info_layout.addWidget(self._last_update_label)

        layout.addLayout(info_layout)

        # 创建分割器：上方是标签页，下方是日志
        self._right_splitter = QSplitter(Qt.Orientation.Vertical)

        # 上部：标签页
        self._monitor_tabs = QTabWidget()
        self._monitor_tabs.setStyleSheet(AppStyles.TAB_WIDGET)

        self._data_tab = self._create_data_tab()
        self._register_tab = self._create_register_tab()

        self._monitor_tabs.addTab(self._data_tab, TextConstants.TAB_REALTIME_DATA)
        self._monitor_tabs.addTab(self._register_tab, TextConstants.TAB_REGISTERS)

        self._right_splitter.addWidget(self._monitor_tabs)

        # 下部：日志区域
        self._log_widget = self._create_log_widget()
        self._right_splitter.addWidget(self._log_widget)

        # 设置分割比例（上部70%，下部30%）
        self._right_splitter.setSizes([500, 200])
        self._right_splitter.setStretchFactor(0, 7)
        self._right_splitter.setStretchFactor(1, 3)

        layout.addWidget(self._right_splitter)

        return page

    def _create_data_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        # 趋势图区域
        chart_header_layout = QHBoxLayout()
        chart_title = QLabel("实时趋势图")
        chart_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #24292F;")
        chart_header_layout.addWidget(chart_title)
        chart_header_layout.addStretch()

        # 管理趋势图按钮
        self._manage_charts_btn = SecondaryButton("管理趋势图")
        self._manage_charts_btn.setFixedSize(110, 32)
        self._manage_charts_btn.clicked.connect(self._on_manage_charts)
        chart_header_layout.addWidget(self._manage_charts_btn)

        layout.addLayout(chart_header_layout)

        # 趋势图容器
        self._chart_container = QWidget()
        self._chart_container.setMinimumHeight(300)
        self._chart_layout = QVBoxLayout(self._chart_container)
        layout.addWidget(self._chart_container)

        # 分隔线
        line = QLabel()
        line.setStyleSheet("background-color: #E5E7EB; min-height: 1px; max-height: 1px;")
        line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(line)

        # 数据卡片区域
        cards_header_layout = QHBoxLayout()
        cards_title = QLabel("数据卡片")
        cards_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #24292F;")
        cards_header_layout.addWidget(cards_title)
        cards_header_layout.addStretch()

        # 管理数据卡片按钮
        self._manage_cards_btn = SecondaryButton("管理卡片")
        self._manage_cards_btn.setFixedSize(110, 32)
        self._manage_cards_btn.clicked.connect(self._on_manage_cards)
        cards_header_layout.addWidget(self._manage_cards_btn)

        layout.addLayout(cards_header_layout)

        self._data_cards_layout = QGridLayout()
        self._data_cards_layout.setSpacing(16)
        layout.addLayout(self._data_cards_layout)

        layout.addStretch()
        return tab

    def _create_register_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self._register_table = DataTable(columns=["Address", "Function Code", "Variable Name", "Value", "Unit"])
        self._register_table.horizontalHeader().setStretchLastSection(True)
        self._register_table.verticalHeader().setVisible(False)
        layout.addWidget(self._register_table)

        return tab

    def _create_log_widget(self) -> QWidget:
        """创建日志区域（内嵌在主窗口右侧）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题栏
        header_layout = QHBoxLayout()
        log_title = QLabel("通信日志")
        log_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #24292F;")
        header_layout.addWidget(log_title)
        header_layout.addStretch()

        # 清空按钮
        clear_btn = SecondaryButton("清空")
        clear_btn.setFixedSize(70, 32)
        clear_btn.clicked.connect(self._clear_log)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        # 日志文本框
        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._log_text.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )
        font = QFont("JetBrains Mono", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._log_text.setFont(font)
        layout.addWidget(self._log_text)

        return widget

    def _clear_log(self) -> None:
        """清空日志"""
        if hasattr(self, "_log_text") and self._log_text:
            self._log_text.clear()

    def _log_message(self, message: str, level: str = "INFO") -> None:
        """记录日志消息到日志区域"""
        if not hasattr(self, "_log_text") or not self._log_text:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # 根据级别设置颜色（使用ANSI风格的文本标记）
        level_markers = {
            "INFO": "",
            "WARNING": "[WARN] ",
            "ERROR": "[ERR] ",
            "DEBUG": "[DBG] ",
            "SUCCESS": "[OK] ",
        }
        marker = level_markers.get(level, "")

        log_line = f"[{timestamp}] {marker}{message}"
        self._log_text.appendPlainText(log_line)

        # 自动滚动到底部
        scrollbar = self._log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _connect_signals(self) -> None:
        self._device_manager.device_added.connect(self._on_device_added)
        self._device_manager.device_removed.connect(self._on_device_removed)
        self._device_manager.device_connected.connect(self._on_device_connected)
        self._device_manager.device_disconnected.connect(self._on_device_disconnected)
        self._device_manager.device_data_updated.connect(self._on_device_data_updated)
        self._device_manager.device_error.connect(self._on_device_error)

        self._alarm_manager.alarm_triggered.connect(self._on_alarm_triggered)

    def _setup_alarm_rules(self) -> None:
        default_rules = [
            AlarmRule(
                rule_id="TEMP_HIGH",
                device_id="*",
                parameter="Temperature",
                alarm_type=AlarmType.THRESHOLD_HIGH,
                threshold_high=80.0,
                level=AlarmLevel.WARNING,
                description="Temperature too high alarm",
            ),
            AlarmRule(
                rule_id="PRESSURE_HIGH",
                device_id="*",
                parameter="Pressure",
                alarm_type=AlarmType.THRESHOLD_HIGH,
                threshold_high=2.0,
                level=AlarmLevel.WARNING,
                description="Pressure too high alarm",
            ),
        ]

        for rule in default_rules:
            self._alarm_manager.add_rule(rule)

    def _apply_theme(self) -> None:
        self._theme_manager.apply_theme()

    def _refresh_device_list(self, search_text: str = "") -> None:
        # 保存当前选中的设备ID
        current_device_id = self._current_device_id

        # 临时断开信号，避免clear时触发不必要的切换
        self._device_tree.currentItemChanged.disconnect(self._on_device_selected)
        self._device_tree.clear()

        for device_info in self._device_manager.get_all_devices():
            name = device_info["name"]
            if search_text and search_text.lower() not in name.lower():
                continue

            device_id = device_info["device_id"]
            item = QTreeWidgetItem()
            item.setText(0, name)
            item.setText(1, device_info["config"].get("device_number", ""))

            status = device_info["status"]
            status_text = StatusText.get_text(status)
            item.setText(2, status_text)

            item.setTextAlignment(0, Qt.AlignmentFlag.AlignCenter)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            item.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
            item.setData(0, Qt.ItemDataRole.UserRole, device_id)
            item.setSizeHint(0, QSize(0, 48))
            self._device_tree.addTopLevelItem(item)

            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)

            edit_btn = PrimaryButton(TextConstants.BTN_EDIT)
            edit_btn.setMinimumHeight(30)
            edit_btn.setMaximumHeight(38)
            edit_btn.setMinimumWidth(44)
            edit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            edit_btn.setToolTip("Edit device")
            edit_btn.clicked.connect(lambda checked, did=device_id: self._edit_device_by_id(did))

            if status == DeviceStatus.CONNECTED:
                conn_btn = DangerButton(TextConstants.BTN_DISCONNECT)
                conn_btn.setToolTip("Disconnect")
            else:
                conn_btn = SuccessButton(TextConstants.BTN_CONNECT)
                conn_btn.setToolTip("Connect device")
            conn_btn.setMinimumHeight(30)
            conn_btn.setMaximumHeight(38)
            conn_btn.setMinimumWidth(44)
            conn_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            conn_btn.clicked.connect(lambda checked, did=device_id: self._toggle_connection_by_id(did))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(conn_btn)

            self._device_tree.setItemWidget(item, 3, action_widget)

        # 重新连接信号
        self._device_tree.currentItemChanged.connect(self._on_device_selected)

        # 恢复之前选中的设备
        if current_device_id:
            for i in range(self._device_tree.topLevelItemCount()):
                item = self._device_tree.topLevelItem(i)
                if item and item.data(0, Qt.ItemDataRole.UserRole) == current_device_id:
                    self._device_tree.setCurrentItem(item)
                    break

        # 刷新后自适应调整尺寸
        QTimer.singleShot(0, self._update_tree_adaptive_sizes)
        # 更新自动重连状态显示
        self._update_auto_reconnect_status()

    def _filter_devices(self) -> None:
        search_text = self._search_edit.text()
        self._refresh_device_list(search_text)

    def _toggle_all_auto_reconnect(self) -> None:
        """一键控制所有设备的自动重连功能"""
        # 获取按钮当前状态（已经自动切换）
        enabled = self._auto_reconnect_btn.isChecked()

        # 设置所有设备的自动重连状态
        count = self._device_manager.set_all_devices_auto_reconnect(enabled)

        # 更新按钮文本
        self._auto_reconnect_btn.setText(f"{'启用重连' if enabled else '禁用重连'}")

        # 动态更新按钮样式
        from ui.widgets import Colors

        if enabled:
            # 启用状态 - 蓝色
            self._auto_reconnect_btn.setStyleSheet(
                f""
                f"QPushButton {{ background: {Colors.PRIMARY}; color: #FFFFFF; "
                f"border: none; border-radius: {Colors.RADIUS}; padding: 6px 16px; "
                f"font-size: 13px; font-weight: 500; }}"
                f"QPushButton:hover {{ background: {Colors.PRIMARY_HOVER}; }}"
                f"QPushButton:pressed {{ background: {Colors.PRIMARY}; opacity: 0.8; }}"
                f"QPushButton:disabled {{ color: #9CA3AF; background: #F3F4F6; }}"
                f""
            )
        else:
            # 禁用状态 - 红色
            self._auto_reconnect_btn.setStyleSheet(
                f""
                f"QPushButton {{ background: {Colors.DANGER}; color: #FFFFFF; "
                f"border: none; border-radius: {Colors.RADIUS}; padding: 6px 16px; "
                f"font-size: 13px; font-weight: 500; }}"
                f"QPushButton:hover {{ background: {Colors.DANGER_HOVER}; }}"
                f"QPushButton:pressed {{ background: {Colors.DANGER}; opacity: 0.8; }}"
                f"QPushButton:disabled {{ color: #9CA3AF; background: #F3F4F6; }}"
                f""
            )

        # 更新状态栏
        self._update_auto_reconnect_status()

        # 显示操作结果
        status_msg = f"已{'启用' if enabled else '禁用'}所有设备的自动重连功能，共影响{count}台设备"
        self._status_msg_label.setText(status_msg)
        logger.info(status_msg)

    def _update_auto_reconnect_status(self) -> None:
        """更新状态栏的自动重连状态显示"""
        enabled_count, disabled_count = self._device_manager.get_auto_reconnect_status()

        self._status_auto_reconnect_enabled.setText(f"● 自动重连启用 {enabled_count}")
        self._status_auto_reconnect_disabled.setText(f"● 自动重连禁用 {disabled_count}")

    def _update_tree_adaptive_sizes(self) -> None:
        """根据面板当前宽度自适应调整设备树行高和操作列按钮.

        当面板被 splitter 拉伸/压缩时调用,
        动态调整行高和操作列宽度以保持比例协调。
        """
        if self._left_panel_collapsed:
            return

        panel_width = self._left_panel.width()
        # 行高随面板宽度线性缩放: 460px→48, 650px→56, 850px→64
        row_height = int(40 + max(0, min(panel_width - 460, 500)) * 0.032)
        row_height = max(48, min(row_height, 70))

        # 操作列宽度: 面板越宽, 操作按钮可分配越多空间
        # 基准 170px (两按钮各58px + 间距6px + 边距), 最大 260px
        action_col_width = int(150 + max(0, panel_width - 440) * 0.20)
        action_col_width = max(170, min(action_col_width, 260))
        self._device_tree.setColumnWidth(3, action_col_width)

        # 更新所有行的行高和操作列按钮
        from PySide6.QtWidgets import QPushButton

        btn_min_h = max(26, row_height - 20)
        btn_max_h = row_height - 10

        for i in range(self._device_tree.topLevelItemCount()):
            item = self._device_tree.topLevelItem(i)
            item.setSizeHint(0, QSize(0, row_height))
            # 更新操作列中的按钮尺寸
            action_widget = self._device_tree.itemWidget(item, 3)
            if action_widget:
                for btn in action_widget.findChildren(QPushButton):
                    btn.setMinimumHeight(btn_min_h)
                    btn.setMaximumHeight(btn_max_h)

    def _add_device(self) -> None:
        from ui.device_type_dialogs import DeviceTypeManager

        logger.debug("Opening add device dialog")
        device_type_manager = DeviceTypeManager("device_types.json")
        dialog = AddDeviceDialog(device_type_manager, self)
        if dialog.exec():
            config = dialog.get_device_config()
            self._device_manager.add_device(config)
            logger.info(LogMessages.DEVICE_ADDED.format(device_id=config.get("name", "Unnamed")))

    def _remove_device(self) -> None:
        item = self._device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.ItemDataRole.UserRole)
        self._remove_device_by_id(device_id)

    def _remove_device_by_id(self, device_id: str) -> None:
        reply = QMessageBox.question(
            self,
            UIMessages.CONFIRM_DELETE_TITLE,
            UIMessages.CONFIRM_DELETE_MSG,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._device_manager.remove_device(device_id)
            logger.info(LogMessages.DEVICE_REMOVED.format(device_id=device_id))

    def _connect_device_by_id(self, device_id: str) -> None:
        success, error_type, error_msg = self._device_manager.connect_device(device_id)
        if success:
            self._status_msg_label.setText("正在连接...")
            logger.info(LogMessages.DEVICE_CONNECTING.format(device_id=device_id))
        else:
            # 根据错误类型生成更详细的错误消息
            detailed_msg = f"{error_msg}\n\n错误类型: {error_type}\n\n是否需要重新配置设备?"
            reply = QMessageBox.warning(
                self,
                UIMessages.CONNECT_FAILED_TITLE,
                detailed_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            # 如果用户选择"是"，则打开设备编辑对话框
            if reply == QMessageBox.StandardButton.Yes:
                self._edit_device_by_id(device_id)

            logger.error(LogMessages.DEVICE_CONNECT_FAILED.format(device_id=device_id))
            logger.error(f"连接失败详情: 类型={error_type}, 消息={error_msg}")

    def _disconnect_device_by_id(self, device_id: str) -> None:
        self._device_manager.disconnect_device(device_id)
        logger.info(LogMessages.DEVICE_DISCONNECTED.format(device_id=device_id))

    def _toggle_connection_by_id(self, device_id: str) -> None:
        device = self._device_manager.get_device(device_id)
        if device:
            # 自动选中当前设备（如果未选中）
            if self._current_device_id != device_id:
                for i in range(self._device_tree.topLevelItemCount()):
                    item = self._device_tree.topLevelItem(i)
                    if item and item.data(0, Qt.ItemDataRole.UserRole) == device_id:
                        self._device_tree.setCurrentItem(item)
                        break

            if device.get_status() == DeviceStatus.CONNECTED:
                self._disconnect_device_by_id(device_id)
            else:
                self._connect_device_by_id(device_id)

    def _edit_device(self) -> None:
        item = self._device_tree.currentItem()
        if not item:
            QMessageBox.warning(self, UIMessages.SELECT_DEVICE_TITLE, UIMessages.SELECT_DEVICE_MSG)
            return

        device_id = item.data(0, Qt.ItemDataRole.UserRole)
        self._edit_device_by_id(device_id)

    def _edit_device_by_id(self, device_id: str) -> None:
        device = self._device_manager.get_device(device_id)
        if not device:
            return

        from ui.device_type_dialogs import DeviceTypeManager

        config = device.get_device_config()
        device_type_manager = DeviceTypeManager("device_types.json")
        dialog = AddDeviceDialog(device_type_manager, self, edit_mode=True, device_config=config)
        if dialog.exec():
            new_config = dialog.get_device_config()
            self._device_manager.edit_device(device_id, new_config)
            logger.info(LogMessages.DEVICE_EDIT_SUCCESS.format(device_id=device_id))

    def _update_monitor_page(self, device_id: str) -> None:
        device = self._device_manager.get_device(device_id)
        if not device:
            # 没有选中设备时，显示默认信息
            self._device_title_label.setText(f"{TextConstants.DEVICE_MONITOR_TITLE} - 未选择设备")
            self._device_name_label.setText(f"{TextConstants.DEVICE_NAME_LABEL} -")
            self._device_status_badge.set_status("offline")
            self._last_update_label.setText(f"{TextConstants.LAST_UPDATE_LABEL} -")
            self._update_cards_display()
            self._update_register_table([])
            return

        config = device.get_device_config()
        status = device.get_status()

        self._device_title_label.setText(f"{TextConstants.DEVICE_MONITOR_TITLE} - {config.get('name', 'Unknown')}")
        self._device_name_label.setText(f"{TextConstants.DEVICE_NAME_LABEL} {config.get('name', '-')}")

        status_text, badge_type = StatusText.get_text_with_badge(status)
        # badge_type: "success"/"warning"/"info"/"error" → StatusBadge status: "online"/"offline"/"warning"/"error"
        badge_status_map = {"success": "online", "warning": "warning", "info": "warning", "error": "error"}
        badge_status = badge_status_map.get(badge_type, "offline")
        self._device_status_badge.set_status(badge_status)

        self._last_update_label.setText(f"{TextConstants.LAST_UPDATE_LABEL} {datetime.now().strftime('%H:%M:%S')}")

        # 获取寄存器列表 (从设备对象或配置中获取)
        register_map = config.get("register_map", [])
        if not register_map and hasattr(device, "_register_map"):
            register_map = device._register_map

        self._update_cards_display()
        self._update_register_table(register_map)

        self._log_message(f"Device {config.get('name')} selected", "INFO")

    def _update_data_cards(self, data: Dict) -> None:
        while self._data_cards_layout.count():
            item = self._data_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row, col = 0, 0
        max_cols = 3

        for name, info in data.items():
            card = self._create_data_card(name, info)
            self._data_cards_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _create_data_card(self, name: str, info: Dict) -> DataCard:
        value = info.get("value", 0)
        unit = info.get("unit", "")

        card = DataCard(name, f"{value:.2f}")
        card.unit_label = QLabel(unit)
        card.unit_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        card.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.layout().addWidget(card.unit_label)

        return card

    def _update_register_table(self, registers: List) -> None:
        self._register_table.setRowCount(len(registers))

        for row, reg in enumerate(registers):
            self._register_table.setItem(row, 0, QTableWidgetItem(str(reg.get("address", ""))))
            self._register_table.setItem(row, 1, QTableWidgetItem(str(reg.get("function_code", ""))))
            self._register_table.setItem(row, 2, QTableWidgetItem(reg.get("name", "")))
            self._register_table.setItem(row, 3, QTableWidgetItem(str(reg.get("value", ""))))
            self._register_table.setItem(row, 4, QTableWidgetItem(reg.get("unit", "")))

            for col in range(5):
                item = self._register_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self._register_table.resizeColumnsToContents()

    def _show_device_type_dialog(self) -> None:
        from ui.device_type_dialogs import DeviceTypeManager

        logger.debug("Opening device type management dialog")
        device_type_manager = DeviceTypeManager("device_types.json")
        dialog = DeviceTypeDialog(device_type_manager, self)
        dialog.exec()

    def _show_alarm_dialog(self) -> None:
        QMessageBox.information(self, UIMessages.ALARM_DIALOG_TITLE, UIMessages.ALARM_DIALOG_MSG)

    def _show_alarm_config_dialog(self) -> None:
        """打开报警规则配置对话框"""
        # TODO: 修复报警配置对话框，当前缺少alarm_config_dialog.py文件
        QMessageBox.warning(self, "功能未实现", "报警规则配置功能当前不可用")

    def _show_export_dialog(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)",
        )

        if file_path:
            devices = self._device_manager.get_all_devices()
            export_data = []

            for device_info in devices:
                device = device_info.get("config", {})
                device_obj = self._device_manager.get_device(device_info["device_id"])
                data = device_obj.get_current_data() if device_obj else {}

                row = {
                    "Device ID": device_info["device_id"],
                    "Device Name": device.get("name", ""),
                    "Device Type": device.get("device_type", ""),
                    "Status": StatusText.get_text(device_info["status"]),
                    "IP Address": device.get("host", ""),
                    "Port": device.get("port", ""),
                }

                for param_name, param_info in data.items():
                    if isinstance(param_info, dict):
                        row[f"{param_name}({param_info.get('unit', '')})"] = param_info.get("value", "")

                row["Export Time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                export_data.append(row)

            if file_path.endswith(".csv"):
                success = DataExporter.export_to_csv(export_data, file_path)
            elif file_path.endswith(".xlsx"):
                success = DataExporter.export_to_excel(export_data, file_path)
            elif file_path.endswith(".json"):
                success = DataExporter.export_to_json(export_data, file_path)
            else:
                success = False

            if success:
                QMessageBox.information(
                    self, UIMessages.EXPORT_SUCCESS_TITLE, UIMessages.EXPORT_SUCCESS_MSG.format(path=file_path)
                )
                logger.info(LogMessages.DATA_EXPORT_SUCCESS.format(path=file_path))
            else:
                QMessageBox.warning(self, UIMessages.EXPORT_FAILED_TITLE, UIMessages.EXPORT_FAILED_MSG)

    def _show_alarm_history(self) -> None:
        alarms = self._alarm_manager.get_alarm_history(100)

        if not alarms:
            QMessageBox.information(self, UIMessages.NO_ALARM_HISTORY_TITLE, UIMessages.NO_ALARM_HISTORY_MSG)
            return

        alarm_text = "Alarm History (Last 100):\n\n"
        for alarm in alarms[-20:]:
            alarm_dict = alarm.to_dict()
            alarm_text += (
                f"{alarm_dict['timestamp']} | {alarm_dict['device_id']} | "
                f"{alarm_dict['parameter']} | {alarm_dict['level_name']} | "
                f"Value:{alarm_dict['value']}\n"
            )

        QMessageBox.information(self, UIMessages.NO_ALARM_HISTORY_TITLE, alarm_text)

    def _show_batch_operations(self) -> None:
        dialog = BatchOperationsDialog(self._device_manager, self)
        dialog.operations_completed.connect(self._on_batch_operations_completed)
        dialog.exec()

    def _on_batch_operations_completed(self, success_count: int, total_count: int) -> None:
        self._refresh_device_list()
        self._update_status_bar()
        logger.info(LogMessages.BATCH_OPS_COMPLETE.format(success=success_count, total=total_count))

    def _show_about(self) -> None:
        QMessageBox.about(self, UIMessages.ABOUT_TITLE, UIMessages.ABOUT_MSG)

    def _toggle_modbus_generator(self, checked: bool) -> None:
        """切换报文生成工具显示/隐藏"""
        if hasattr(self, "_modbus_generator"):
            if checked:
                self._modbus_generator.setVisible(True)
                # 设置合适的宽度
                sizes = self._splitter.sizes()
                if sizes[2] == 0:  # 如果当前宽度为0，设置为350
                    total = sum(sizes)
                    sizes[0] = int(total * 0.15)
                    sizes[1] = int(total * 0.60)
                    sizes[2] = int(total * 0.25)
                    self._splitter.setSizes(sizes)
                    # 调整splitter大小后重新定位按钮
                    QTimer.singleShot(0, self._reposition_edge_buttons)
                self._log_message("报文生成工具已打开", "INFO")
            else:
                self._modbus_generator.setVisible(False)
                # 将宽度设为0
                sizes = self._splitter.sizes()
                sizes[2] = 0
                self._splitter.setSizes(sizes)
                # 调整splitter大小后重新定位按钮
                QTimer.singleShot(0, self._reposition_edge_buttons)
                self._log_message("报文生成工具已关闭", "INFO")

    def _on_device_selected(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        if not current:
            self._stack_widget.setCurrentIndex(0)
            return

        device_id = current.data(0, Qt.ItemDataRole.UserRole)
        self._current_device_id = device_id
        self._update_monitor_page(device_id)
        self._stack_widget.setCurrentIndex(1)

    @Slot(str)
    def _on_device_added(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._status_msg_label.setText(f"设备已添加: {device_id}")

    @Slot(str)
    def _on_device_removed(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._stack_widget.setCurrentIndex(0)
        self._status_msg_label.setText(f"设备已移除: {device_id}")

    @Slot(str)
    def _on_device_connected(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._status_msg_label.setText(f"设备已连接: {device_id}")
        logger.info(LogMessages.DEVICE_CONNECTED.format(device_id=device_id))
        if self._current_device_id == device_id:
            self._update_monitor_page(device_id)

    @Slot(str)
    def _on_device_disconnected(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._status_msg_label.setText(f"设备已断开: {device_id}")
        logger.info(LogMessages.DEVICE_DISCONNECTED.format(device_id=device_id))
        if self._current_device_id == device_id:
            self._update_monitor_page(device_id)

    @Slot(str, dict)
    def _on_device_data_updated(self, device_id: str, data: dict) -> None:
        for param_name, param_info in data.items():
            if isinstance(param_info, dict) and "value" in param_info:
                self._alarm_manager.check_value(device_id, param_name, param_info["value"])

        if self._current_device_id == device_id:
            self._update_card_values(data)
            self._update_chart_data(data)
            self._last_update_label.setText(f"{TextConstants.LAST_UPDATE_LABEL} {datetime.now().strftime('%H:%M:%S')}")

    def _update_chart_data(self, data: dict) -> None:
        """更新图表数据"""
        if not hasattr(self, "_chart_widget") or not self._chart_widget:
            return

        # 遍历数据，添加到图表
        for param_name, param_info in data.items():
            if isinstance(param_info, dict) and "value" in param_info:
                try:
                    value = float(param_info["value"])
                    self._chart_widget.add_value(param_name, value)
                except (ValueError, TypeError):
                    # 忽略无法转换为数值的数据
                    pass

    @Slot(str, str)
    def _on_device_error(self, device_id: str, error: str) -> None:
        logger.error(f"Device error: {device_id} - {error}")
        self._status_msg_label.setText(f"设备错误: {device_id} - {error}")
        self._update_status_bar()

    def _on_alarm_triggered(self, alarm) -> None:
        alarm_dict = alarm.to_dict()
        self._log_message(
            f"Alarm: {alarm_dict['device_id']} - "
            f"{alarm_dict['parameter']} ({alarm_dict['level_name']}): "
            f"{alarm_dict['value']} {alarm_dict.get('threshold_high', '')}",
            "WARNING",
        )

        QMessageBox.warning(
            self,
            "Alarm Alert",
            f"Device: {alarm_dict['device_id']}\n"
            f"Parameter: {alarm_dict['parameter']}\n"
            f"Level: {alarm_dict['level_name']}\n"
            f"Value: {alarm_dict['value']}\n"
            f"Description: {alarm_dict['description']}",
        )

    def _update_status_bar(self) -> None:
        all_devices = self._device_manager.get_all_devices()
        total_count = len(all_devices)
        online_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.CONNECTED)
        offline_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.DISCONNECTED)
        error_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.ERROR)

        self._status_total_label.setText(f"设备 {total_count}")
        self._status_online_label.setText(f"● 在线 {online_count}")
        self._status_offline_label.setText(f"● 离线 {offline_count}")
        self._status_error_label.setText(f"● 错误 {error_count}")

    def _on_manage_charts(self) -> None:
        """管理趋势图"""
        if not self._current_device_id:
            QMessageBox.information(self, "提示", "请先选择一个设备")
            return

        # 清除现有图表
        while self._chart_layout.count():
            item = self._chart_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        from ui.widgets.visual import RealtimeChart

        # 获取数据卡片配置
        cards_config = self._device_cards.get(self._current_device_id, [])

        if not cards_config:
            # 如果没有数据卡片，添加默认趋势图
            chart = RealtimeChart(title="设备数据趋势图")
            chart.setMinimumHeight(300)
            self._chart_layout.addWidget(chart)
        else:
            # 使用一个图表显示所有数据卡片变量
            chart = RealtimeChart(title="设备数据趋势图")
            chart.setMinimumHeight(300)
            self._chart_layout.addWidget(chart)

        # 保存图表配置
        self._device_charts[self._current_device_id] = [{"title": "设备数据趋势图", "registers": []}]

        # 初始化设备数据关联
        self._init_chart_data()

    def _init_chart_data(self) -> None:
        """初始化图表数据关联"""
        if not self._current_device_id:
            return

        # 确保有图表实例
        if not hasattr(self, "_chart_layout") or self._chart_layout.count() == 0:
            return

        chart_item = self._chart_layout.itemAt(0)
        if not chart_item or not chart_item.widget():
            return

        self._chart_widget = chart_item.widget()
        self._chart_widget.clear()

        # 从数据卡片配置中获取寄存器信息
        cards_config = self._device_cards.get(self._current_device_id, [])

        for card_config in cards_config:
            register_name = card_config.get("register_name", "")
            if register_name:
                self._chart_widget.add_series(register_name)

        # 如果没有数据卡片，则从设备寄存器中获取
        if not cards_config:
            device = self._device_manager.get_device(self._current_device_id)
            if not device:
                return

            if isinstance(device, dict):
                register_map = device.get("register_map", [])
            else:
                config = device.get_device_config()
                register_map = config.get("register_map", [])

            for reg in register_map:
                if isinstance(reg, dict) and reg.get("name"):
                    self._chart_widget.add_series(reg["name"])

    def _on_manage_cards(self) -> None:
        """打开数据卡片管理对话框"""
        if not self._current_device_id:
            QMessageBox.information(self, "提示", "请先选择一个设备")
            return

        device = self._device_manager.get_device(self._current_device_id)
        if not device:
            return

        # 获取设备寄存器列表 (从 register_map 获取)
        if isinstance(device, dict):
            register_map = device.get("register_map", [])
        else:
            # Device 对象
            config = device.get_device_config()
            register_map = config.get("register_map", [])

        # 转换为可用格式
        available_registers = []
        for reg in register_map:
            if isinstance(reg, dict):
                available_registers.append(
                    {
                        "name": reg.get("name", ""),
                        "address": reg.get("address", ""),
                    }
                )

        # 获取当前数据卡片配置
        existing_cards = self._device_cards.get(self._current_device_id, [])

        # 打开数据卡片管理对话框
        from ui.widgets.card_manager_dialog import CardManagerDialog

        dialog = CardManagerDialog(
            device_id=self._current_device_id,
            device_name=device.get("name", "") if isinstance(device, dict) else getattr(device, "name", ""),
            available_registers=available_registers,
            existing_cards=existing_cards,
            parent=self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._device_cards[self._current_device_id] = dialog.get_cards()
            self._update_cards_display()

    def _update_cards_display(self) -> None:
        """更新数据卡片显示"""
        # 清除现有卡片
        while self._data_cards_layout.count():
            item = self._data_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self._current_device_id:
            return

        cards_config = self._device_cards.get(self._current_device_id, [])

        # 添加数据卡片
        row, col = 0, 0
        max_cols = 3

        for config in cards_config:
            card = DataCard(
                title=config.get("title", ""),
                value="--",
            )
            card.register_name = config.get("register_name", "")

            # 添加单位标签
            unit = config.get("unit", "")
            if unit:
                card.unit_label = QLabel(unit)
                card.unit_label.setStyleSheet("color: #8B949E; font-size: 12px;")
                card.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                card.layout().addWidget(card.unit_label)

            card.setMinimumSize(140, 100)
            self._data_cards_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _update_card_values(self, data: Dict[str, Any]) -> None:
        """更新数据卡片数值"""
        # 遍历所有数据卡片，根据关联的寄存器名更新数值
        for i in range(self._data_cards_layout.count()):
            item = self._data_cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, DataCard) and hasattr(card, "register_name"):
                    register_name = card.register_name
                    if register_name and register_name in data:
                        value_info = data[register_name]
                        if isinstance(value_info, dict):
                            value = value_info.get("value", 0)
                        else:
                            value = float(value_info) if value_info else 0
                        card.set_value(f"{value:.2f}")

    def cleanup(self) -> None:
        logger.info(LogMessages.APP_SHUTDOWN)
        # 停止数据清理调度器
        if hasattr(self, "_cleanup_scheduler") and self._cleanup_scheduler:
            self._cleanup_scheduler.stop()
        self._device_manager.cleanup()

    def closeEvent(self, event) -> None:
        self.cleanup()
        event.accept()
