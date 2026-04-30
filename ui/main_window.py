# -*- coding: utf-8 -*-
"""
Main Window - Industrial Equipment Management System
Refactored with maintainable constants and clear text mappings
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QTimer, Slot
from PySide6.QtGui import QFont, QBrush, QColor
from PySide6.QtWidgets import QApplication, QTableWidget  # noqa: F401  (base class of DataTable)
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
from core.device.device_manager import DeviceManager
from core.device.device_model import DeviceStatus
from core.utils.logger import get_logger
from core.utils.qt_helpers import is_valid_qt_object, safe_reconnect
from core.utils.write_operation_manager import WriteOperationManager
from core.version import __version__
from ui.add_device_dialog import AddDeviceDialog
from ui.app_styles import AppStyles
from ui.batch_operations_dialog import BatchOperationsDialog
from ui.core import ThemeManager
from ui.device_type_dialogs import DeviceTypeDialog
from ui.register_write_dialog import RegisterWriteDialog
from ui.widgets.dynamic_monitor_panel import DynamicMonitorPanel
from ui.dialogs.mcgs_config_dialog import MCGSConfigDialog
from ui.controllers.device_controller import DeviceController
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

logger = get_logger("main_window")


class TextConstants:
    """UI text constants - centralized for easy maintenance"""

    APP_NAME = "工业设备管理系统"
    APP_VERSION = __version__
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
    ACTION_DATA_EXPORT = "数据导出 (&E)"
    ACTION_EXPORT_DEVICE_CONFIG = "设备配置导出 (&O)"
    ACTION_IMPORT_DEVICE_CONFIG = "设备配置导入 (&I)"
    ACTION_BATCH_OPS = "批量操作"
    ACTION_EXIT = "退出 (&X)"
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
    EXPORT_SUCCESS_MSG = "数据已导出至：{path}"
    DEVICE_CONFIG_EXPORT_SUCCESS_MSG = "设备配置已成功导出至：{path}"

    EXPORT_FAILED_TITLE = "导出失败"
    EXPORT_FAILED_MSG = "数据导出失败，请检查文件格式或权限"
    DEVICE_CONFIG_EXPORT_FAILED_MSG = "设备配置导出失败"

    IMPORT_SUCCESS_TITLE = "导入成功"
    DEVICE_CONFIG_IMPORT_SUCCESS_MSG = "设备配置已成功导入"

    IMPORT_FAILED_TITLE = "导入失败"
    DEVICE_CONFIG_IMPORT_FAILED_MSG = "设备配置导入失败"

    IMPORT_CONFIRM_TITLE = "确认导入"
    DEVICE_CONFIG_IMPORT_CONFIRM_MSG = "确定要导入设备配置吗？\n现有设备将被覆盖。"

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
        "【系统功能】\n"
        "  • Fluent Design 风格主题\n"
        "  • 数据导出 (CSV/Excel)\n"
        "  • 日志查看器\n"
        "  • 设备仿真模式\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Power By 喝口阔落"
    )


class MainWindow(QMainWindow):
    """
    主窗口 - 工业设备管理系统

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
        self._device_manager = DeviceManager(db_manager=self._db_manager)
        self._device_controller = DeviceController(self._device_manager, parent=self)
        self._theme_manager = ThemeManager()
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._sort_column = 0
        self._current_device_id: Optional[str] = None
        self._left_panel_collapsed = False
        self._left_panel_saved_size = 520  # 从480增加到520，确保设备列表有足够空间显示

        # 操作防重复点击锁（P0-2修复）
        self._operation_lock = False
        self._current_operation_btn = None  # 记录当前操作的按钮，用于恢复状态

        # 数据卡片配置存储: {device_id: [card_configs]}
        self._device_cards: Dict[str, List[Dict[str, Any]]] = {}

        # 趋势图配置存储: {device_id: [chart_configs]}
        self._device_charts: Dict[str, List[Dict[str, Any]]] = {}

        # v3.2 新增：动态监控面板存储 {device_id: DynamicMonitorPanel实例}
        self._monitor_panels: Dict[str, DynamicMonitorPanel] = {}

        # v3.2 新增：写操作管理器（安全网关）
        self._write_manager = WriteOperationManager(self)
        self._pending_write_req_id: Optional[str] = None  # 当前待确认的写请求ID

        # ✅ 新增：权限管理器（三级权限体系）
        from core.utils.permission_manager import PermissionManager

        self._permission_mgr = PermissionManager(parent=self)
        self._permission_mgr.permission_changed.connect(self._on_permission_changed)
        self._permission_mgr.session_timeout.connect(self._on_session_timeout)

        # 将权限管理器注入到写操作管理器
        self._write_manager.set_permission_manager(self._permission_mgr)

        # ✅ 新增：操作撤销管理器
        from core.utils.operation_undo_manager import OperationUndoManager

        self._undo_mgr = OperationUndoManager(max_history=100, parent=self)
        self._undo_req_map: Dict[str, str] = {}
        self._undo_mgr.undo_executed.connect(self._on_undo_executed)
        self._undo_mgr.undo_failed.connect(self._on_undo_failed)

        # ✅ 新增：将撤销管理器注入到写操作管理器
        self._write_manager.set_undo_manager(self._undo_mgr)

        # ✅ 新增：MCGS快速连接模块 — 通过 MCGSController 异步调度
        self._init_mcgsm_controller()

        # 数据清理调度器
        from core.data.cleanup_scheduler import CleanupScheduler

        self._cleanup_scheduler = CleanupScheduler(self._db_manager)
        self._cleanup_scheduler.start()

        # UI 偏好持久化服务
        from core.services.ui_preferences_service import UIPreferencesService

        self._ui_prefs = UIPreferencesService()

        from ui.controllers.status_bar_controller import StatusBarController
        from ui.controllers.monitor_page_controller import MonitorPageController

        self._status_bar_controller = StatusBarController()
        self._monitor_controller = MonitorPageController()

        self._init_ui()
        self._connect_signals()
        self._refresh_device_list()
        self._apply_theme()
        self._load_ui_preferences()
        self._cleaned = False

        logger.info(LogMessages.APP_STARTUP)

    def __del__(self) -> None:
        if getattr(self, "_cleaned", True):
            return
        self._cleaned = True

        try:
            if hasattr(self, "_cleanup_scheduler"):
                self._cleanup_scheduler.stop()
                del self._cleanup_scheduler
        except Exception:
            pass

        try:
            if hasattr(self, "_device_manager"):
                for device_info in list(self._device_manager.get_all_devices()):
                    try:
                        device_id = device_info.get("device_id")
                        if device_id:
                            self._device_manager.disconnect_device(device_id)
                    except Exception as e:
                        if "Signal source has been deleted" not in str(e):
                            logger.error("断开设备连接失败: %s", str(e))
        except Exception:
            pass

        try:
            if hasattr(self, "_db_manager"):
                del self._db_manager
        except Exception:
            pass

        try:
            if hasattr(self, "_device_cards"):
                self._device_cards.clear()
            if hasattr(self, "_device_charts"):
                self._device_charts.clear()
        except Exception:
            pass

    def _init_ui(self) -> None:
        self.setWindowTitle(TextConstants.WINDOW_TITLE)
        # 设置合理的最小窗口尺寸（支持自适应调整）
        self.setMinimumSize(1024, 768)

        # 获取屏幕可用区域，智能设置初始窗口大小
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen().availableGeometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # 初始窗口大小：屏幕的80%，但不超过1600x900
        init_width = min(int(screen_width * 0.8), 1600)
        init_height = min(int(screen_height * 0.8), 900)
        self.resize(init_width, init_height)

        self._create_menu_bar()

        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)

        main_layout = QVBoxLayout(self._central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_tool_bar()

        # ── QSplitter: 左面板 + 右面板 ──
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self._splitter)

        # 左侧面板
        self._left_panel = self._create_left_panel()
        self._splitter.addWidget(self._left_panel)

        # 中间面板 (StackedWidget: 页面容器)
        self._stack_widget = QStackedWidget()
        self._stack_widget.setStyleSheet(AppStyles.STACKED_WIDGET)
        self._stack_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 页面0: 欢迎页
        welcome_page = self._create_welcome_page()
        self._stack_widget.addWidget(welcome_page)

        # 页面1: 设备监控页（内嵌命令终端）
        monitor_page = self._create_monitor_page()
        self._stack_widget.addWidget(monitor_page)

        self._splitter.addWidget(self._stack_widget)

        # 默认显示欢迎页 (index 0)
        self._stack_widget.setCurrentIndex(0)

        # Splitter 配置（支持自适应调整，增加左侧面板权重）
        self._splitter.setStretchFactor(0, 30)  # 左侧面板占30%
        self._splitter.setStretchFactor(1, 70)  # 中间面板占70%

        # 初始尺寸比例：左30% + 中70%
        total_width = max(self.width(), 1024)
        initial_sizes = [
            int(total_width * 0.30),
            int(total_width * 0.70),
        ]
        self._splitter.setSizes(initial_sizes)

        # 允许面板折叠
        self._splitter.setCollapsible(0, True)  # 左侧面板可折叠
        self._splitter.setCollapsible(1, False)  # 中间主区域不可折叠

        # 设置分割器的最小尺寸约束（防止面板被压缩到不可用）
        self._splitter.setHandleWidth(3)  # 细分割线，更现代的外观

        self._splitter.setStyleSheet(AppStyles.SPLITTER)
        self._splitter.splitterMoved.connect(self._on_splitter_moved)

        # 初始化命令终端设备列表（命令终端在监控页中已创建）
        QTimer.singleShot(200, self._setup_command_terminal_device_links)

        # ── 折叠/展开浮动按钮 ──
        self._create_collapse_buttons()

        self._create_status_bar()

    def _create_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu(TextConstants.MENU_FILE)

        device_type_action = file_menu.addAction(TextConstants.ACTION_DEVICE_TYPE_MGMT)
        device_type_action.triggered.connect(self._show_device_type_dialog)

        file_menu.addSeparator()

        export_action = file_menu.addAction(TextConstants.ACTION_DATA_EXPORT)
        export_action.triggered.connect(self._show_export_dialog)

        # 设备配置导出/导入选项
        export_config_action = file_menu.addAction(TextConstants.ACTION_EXPORT_DEVICE_CONFIG)
        export_config_action.triggered.connect(self._show_export_device_config_dialog)

        import_config_action = file_menu.addAction(TextConstants.ACTION_IMPORT_DEVICE_CONFIG)
        import_config_action.triggered.connect(self._show_import_device_config_dialog)

        file_menu.addSeparator()

        exit_action = file_menu.addAction(TextConstants.ACTION_EXIT)
        exit_action.triggered.connect(self.close)

        tools_menu = menubar.addMenu(TextConstants.MENU_TOOLS)

        # ✅ 新增：MCGS快速连接入口
        mcgsm_connect_action = tools_menu.addAction("🔌 MCGS快速连接")
        mcgsm_connect_action.triggered.connect(self._on_mcgsm_quick_connect)
        mcgsm_connect_action.setToolTip("使用devices.json配置快速连接MCGS触摸屏")

        # MCGS历史数据查看
        mcgsm_history_action = tools_menu.addAction("📊 MCGS历史数据")
        mcgsm_history_action.triggered.connect(self._on_mcgsm_show_history)

        # MCGS异常检测报告
        mcgsm_anomaly_action = tools_menu.addAction("⚠️ MCGS健康检测")
        mcgsm_anomaly_action.triggered.connect(self._on_mcgsm_health_check)

        # ✅ 新增：MCGS设备配置入口
        mcgsm_config_action = tools_menu.addAction("⚙️ MCGS设备配置")
        mcgsm_config_action.triggered.connect(self._on_show_mcgsm_config)
        mcgsm_config_action.setToolTip("打开可视化配置编辑器，编辑devices.json")

        tools_menu.addSeparator()

        help_menu = menubar.addMenu(TextConstants.MENU_HELP)

        about_action = help_menu.addAction(TextConstants.ACTION_ABOUT)
        about_action.triggered.connect(self._show_about)

    def _create_tool_bar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(AppStyles.TOOLBAR)
        self.addToolBar(toolbar)

        # ✅ 新增：MCGS快速连接工具栏按钮
        mcgsm_btn = QPushButton("🔌 MCGS连接")
        mcgsm_btn.setToolTip("快速连接MCGS触摸屏（使用devices.json配置）")
        mcgsm_btn.clicked.connect(self._on_mcgsm_quick_connect)
        mcgsm_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
        """
        )
        toolbar.addWidget(mcgsm_btn)

        # MCGS历史数据按钮
        history_btn = QPushButton("📊 历史")
        history_btn.setToolTip("查看MCGS设备的历史数据趋势图")
        history_btn.clicked.connect(self._on_mcgsm_show_history)
        toolbar.addWidget(history_btn)

        # MCGS健康检测按钮
        health_btn = QPushButton("⚠️ 检测")
        health_btn.setToolTip("运行异常检测算法检查设备健康状态")
        health_btn.clicked.connect(self._on_mcgsm_health_check)
        toolbar.addWidget(health_btn)

        # ✅ 新增：MCGS配置按钮
        config_btn = QPushButton("⚙️ 配置")
        config_btn.setToolTip("打开MCGS设备可视化配置编辑器")
        config_btn.clicked.connect(self._on_show_mcgsm_config)
        config_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #6366F1;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
            QPushButton:pressed {
                background-color: #3730A3;
            }
        """
        )
        toolbar.addWidget(config_btn)

        toolbar.addSeparator()

    def _create_status_bar(self) -> None:
        self._status_bar_controller.build(self, AppStyles.__dict__)

        self._status_msg_label = self._status_bar_controller._status_msg_label
        self._status_total_label = self._status_bar_controller._status_total_label
        self._status_online_label = self._status_bar_controller._status_online_label
        self._status_offline_label = self._status_bar_controller._status_offline_label
        self._status_error_label = self._status_bar_controller._status_error_label
        self._status_auto_reconnect_enabled = self._status_bar_controller._status_auto_reconnect_enabled
        self._status_auto_reconnect_disabled = self._status_bar_controller._status_auto_reconnect_disabled
        self._status_tx_label = self._status_bar_controller._status_tx_label
        self._status_rx_label = self._status_bar_controller._status_rx_label

        # 最后更新时间
        self._status_time_label = self._make_status_label("更新时间: 00:00:00", "#6B7280")
        self.statusBar().addPermanentWidget(self._status_time_label)

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
        """初始化折叠和展开按钮的样式和状态.

        按钮已经在左侧面板和监控页面中创建，这里只处理样式和初始状态。
        """
        # 应用按钮样式
        if hasattr(self, "_collapse_btn"):
            self._apply_edge_btn_style(self._collapse_btn)

        if hasattr(self, "_expand_btn"):
            self._apply_edge_btn_style(self._expand_btn)
            self._expand_btn.hide()  # 默认隐藏，面板折叠后显示

    def _apply_edge_btn_style(self, btn: QPushButton) -> None:
        """为边缘按钮设置主题感知的圆角样式."""
        colors = self._theme_manager.colors

        # 根据按钮对象名称判断类型
        btn_name = btn.objectName()

        if btn_name in ["left_collapse_btn", "left_expand_btn"]:
            # 标题栏左侧按钮：圆形，无边框，悬停效果
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {colors.text_secondary};
                    border: none;
                    border-radius: 50%;
                    padding: 4px;
                    font-size: 12px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background: {colors.bg_hover};
                    color: {colors.text_primary};
                }}
            """
            )
        elif btn_name.startswith("right_"):
            # 右侧边沿按钮：左侧圆角
            bg = colors.bg_hover
            border_top = f"1px solid {colors.border_default}"
            border_left = f"1px solid {colors.border_default}"
            border_bottom = f"1px solid {colors.border_default}"
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {bg};
                    color: {colors.text_secondary};
                    border-top: {border_top};
                    border-left: {border_left};
                    border-bottom: {border_bottom};
                    border-right: none;
                    border-top-left-radius: 6px;
                    border-bottom-left-radius: 6px;
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
        """重新定位折叠/展开按钮."""
        # 移除了对报文工具浮动按钮的处理，因为现在使用标题栏按钮

    def _collapse_left_panel(self) -> None:
        """折叠左侧面板."""
        current_sizes = self._splitter.sizes()
        self._left_panel_saved_size = current_sizes[0]
        total = self._splitter.width()
        self._splitter.setSizes([0, total])
        self._left_panel.setVisible(False)
        self._collapse_btn.hide()
        self._expand_btn.show()
        self._left_panel_collapsed = True
        QTimer.singleShot(50, self._reposition_edge_buttons)

        QTimer.singleShot(50, lambda: self._adjust_vertical_splitter())

    def _expand_left_panel(self) -> None:
        """展开左侧面板（自适应当前窗口大小）."""
        self._left_panel.setVisible(True)
        self._expand_btn.hide()
        self._collapse_btn.show()
        self._left_panel_collapsed = False

        total = self._splitter.width()

        # 智能恢复宽度：根据当前窗口大小动态计算（确保设备列表完整显示）
        if hasattr(self, "_left_panel_saved_size") and self._left_panel_saved_size > 0:
            # 使用保存的宽度，但不超过当前窗口的合理比例
            saved = self._left_panel_saved_size
            max_left = int(total * 0.35)  # 左侧最多占35%（从30%增加）
            left_size = min(saved, max_left)
            # 确保最小宽度足够显示设备树
            left_size = max(left_size, int(total * 0.25))  # 至少占25%
        else:
            # 无保存记录时使用默认比例（优化后的值）
            if total < 1280:
                left_size = int(total * 0.25)  # 小屏幕25%（从18%增加）
            elif total < 1600:
                left_size = int(total * 0.28)  # 中等屏幕28%（从20%增加）
            else:
                left_size = int(total * 0.30)  # 大屏幕30%（从22%增加）

        min_middle = int(total * 0.45)
        middle_width = total - left_size
        if middle_width < min_middle:
            left_size = total - min_middle

        self._splitter.setSizes([left_size, total - left_size])

        QTimer.singleShot(50, self._reposition_edge_buttons)
        QTimer.singleShot(50, self._update_tree_adaptive_sizes)

        # 重新调整垂直分割器大小，确保高度比例一致
        QTimer.singleShot(50, lambda: self._adjust_vertical_splitter())

    def _adjust_vertical_splitter(self) -> None:
        """智能调整垂直分割器（监控区+终端）的高度比例."""
        if not hasattr(self, "_right_splitter"):
            return

        vertical_height = self._right_splitter.height()

        # 根据窗口总高度动态调整比例
        total_height = self.height()

        if total_height < 800:
            # 小高度窗口：监控区占更多空间 (80%)
            monitor_ratio = 0.80
        elif total_height < 1000:
            # 中等高度：标准比例 (70%)
            monitor_ratio = 0.70
        else:
            # 大高度窗口：监控区适当减少，给终端更多空间 (65%)
            monitor_ratio = 0.65

        monitor_height = int(vertical_height * monitor_ratio)
        log_height = vertical_height - monitor_height

        # 确保最小高度（防止组件被压缩到不可用）
        min_monitor = 300  # 监控区最小高度
        min_terminal = 150  # 终端最小高度

        if monitor_height < min_monitor:
            monitor_height = min_monitor
            log_height = vertical_height - monitor_height
            if log_height < min_terminal:
                log_height = min_terminal

        self._right_splitter.setSizes([monitor_height, log_height])

    @Slot(str, bytes)
    def _on_command_terminal_send(self, device_id: str, data: bytes) -> None:
        if not hasattr(self, "_device_controller") or self._device_controller is None:
            self._command_terminal.add_received_data("[Error] Controller not initialized".encode("utf-8"))
            return
        if not self._device_controller.is_device_connected(device_id):
            self._command_terminal.add_received_data("[Error] Device not connected".encode("utf-8"))
            return
        self._device_controller.send_raw_command(device_id, data)

    def _setup_command_terminal_device_links(self) -> None:
        if not hasattr(self, "_command_terminal") or not hasattr(self, "_device_controller"):
            return
        if self._device_controller is None:
            return
        from core.foundation.data_bus import DataBus

        devices = self._device_controller.get_device_list()
        self._command_terminal.update_device_list(devices)
        bus = DataBus.instance()
        bus.subscribe("device_raw_bytes_received", self._on_command_terminal_data_received)
        bus.subscribe("device_data_updated", self._on_command_terminal_protocol_data)

    @Slot(str, bytes)
    def _on_command_terminal_data_received(self, device_id: str, data: bytes) -> None:
        if hasattr(self, "_command_terminal"):
            selected_id = self._command_terminal.device_combo.currentData(Qt.ItemDataRole.UserRole)
            if selected_id == device_id or not selected_id:
                self._command_terminal.add_received_data(data)

    @Slot(str, object)
    def _on_command_terminal_protocol_data(self, device_id: str, data: dict) -> None:
        if hasattr(self, "_command_terminal"):
            selected_id = self._command_terminal.device_combo.currentData(Qt.ItemDataRole.UserRole)
            if selected_id == device_id or not selected_id:
                self._command_terminal.add_protocol_data(data)

    @Slot(str, bool, str)
    def _on_raw_send_result(self, device_id: str, success: bool, msg: str) -> None:
        if not success and hasattr(self, "_command_terminal") and msg:
            self._command_terminal.add_received_data(f"[Error] {msg}".encode("utf-8"))

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Splitter 拉动时重新定位按钮并自适应调整（含最小尺寸保护）."""
        if not self._left_panel_collapsed:
            self._reposition_edge_buttons()
            self._update_tree_adaptive_sizes()

        # 重新调整垂直分割器大小，确保高度比例一致
        self._adjust_vertical_splitter()

        # 最小尺寸保护：检查并纠正不合理的面板尺寸
        self._enforce_minimum_panel_sizes()

    def _enforce_minimum_panel_sizes(self) -> None:
        if not hasattr(self, "_splitter"):
            return

        sizes = list(self._splitter.sizes())
        total = sum(sizes)

        if total == 0:
            return

        MIN_LEFT = 300
        MIN_MIDDLE = 500

        adjusted = False

        if sizes[0] > 0 and sizes[0] < MIN_LEFT:
            sizes[0] = MIN_LEFT
            adjusted = True

        if sizes[1] < MIN_MIDDLE:
            deficit = MIN_MIDDLE - sizes[1]
            if sizes[0] > MIN_LEFT:
                borrow = min(deficit, sizes[0] - MIN_LEFT)
                sizes[0] -= borrow
                deficit -= borrow
            sizes[1] = MIN_MIDDLE
            adjusted = True

        if adjusted:
            diff = total - sum(sizes)
            if diff != 0:
                sizes[1] += diff
            self._splitter.setSizes(sizes)

    def resizeEvent(self, event) -> None:
        """窗口缩放时智能调整布局 - 自适应响应式设计."""
        super().resizeEvent(event)
        # 使用 QTimer.singleShot 确保在布局完成后执行调整，避免闪烁
        QTimer.singleShot(0, self._reposition_edge_buttons)
        QTimer.singleShot(0, self._adjust_vertical_splitter)
        # 新增：智能自适应布局调整
        QTimer.singleShot(0, self._adaptive_layout_adjustment)

    def _adaptive_layout_adjustment(self) -> None:
        """根据窗口尺寸智能调整各组件布局比例."""
        if not hasattr(self, "_splitter"):
            return

        current_width = self.width()
        current_height = self.height()

        # 获取当前分割器状态
        sizes = list(self._splitter.sizes())
        total = sum(sizes)

        if total == 0:
            return

        # 自适应策略：根据窗口宽度动态调整面板比例（优化左侧面板显示）
        if current_width < 1280:
            # 小屏幕模式 (<1280px)：保持左侧面板合理宽度，适当压缩中间区域
            left_width = max(sizes[0], int(total * 0.25))  # 左侧至少25%（从15%增加）
            middle_width = total - left_width
            self._splitter.setSizes([left_width, middle_width])
        elif current_width < 1600:
            # 中等屏幕 (1280-1600px)：标准比例 左28% + 中52% + 右20%
            left_width = int(total * 0.28)  # 从20%增加到28%
            middle_width = total - left_width
            self._splitter.setSizes([left_width, middle_width])
        else:
            # 大屏幕 (>1600px)：左侧适当放宽，确保设备列表完整显示
            left_width = int(total * 0.30)  # 从22%增加到30%
            middle_width = total - left_width
            self._splitter.setSizes([left_width, middle_width])

        # 动态调整左侧面板最小宽度（确保设备树5列能完整显示）
        if hasattr(self, "_left_panel"):
            if current_width < 1280:
                self._left_panel.setMinimumWidth(300)  # 从220增加到300，确保基本可用
            elif current_width < 1600:
                self._left_panel.setMinimumWidth(320)  # 从260增加到320
            else:
                self._left_panel.setMinimumWidth(340)  # 从280增加到340，大屏幕更宽敞

    def showEvent(self, event) -> None:
        """窗口显示时初始化按钮位置."""
        super().showEvent(event)
        QTimer.singleShot(0, self._reposition_edge_buttons)

    def _create_left_panel(self) -> QWidget:
        left_widget = QWidget()
        # 增加左侧面板最小宽度，确保设备树5列能完整显示
        left_widget.setMinimumWidth(320)  # 从280增加到320，确保设备列表完整显示
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        # 浅色背景
        left_widget.setStyleSheet("background-color: #FFFFFF;")

        # ── 标题行 ──
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # 添加折叠按钮到标题左侧
        self._collapse_btn = QPushButton("<")
        self._collapse_btn.setObjectName("left_collapse_btn")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._collapse_btn.setToolTip("折叠面板")
        # 使用安全的 ASCII 字符确保跨平台兼容性
        try:
            from ui.design_tokens import DT

            collapse_font = DT.T.get_font(*DT.T.BODY_SMALL)
            self._collapse_btn.setFont(collapse_font)
        except (ImportError, AttributeError):
            from PySide6.QtGui import QFont

            self._collapse_btn.setFont(QFont("Segoe UI Symbol", 10))
        title_layout.addWidget(self._collapse_btn)
        self._collapse_btn.clicked.connect(self._collapse_left_panel)

        self._left_title_label = QLabel(TextConstants.DEVICE_LIST_TITLE)
        try:
            self._left_title_label.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        except NameError:
            from PySide6.QtGui import QFont

            self._left_title_label.setFont(QFont("Segoe UI Variable", 20, QFont.Weight.Bold))
        self._left_title_label.setStyleSheet("color: #24292F; background: transparent;")
        title_layout.addWidget(self._left_title_label)
        title_layout.addStretch()

        # 添加刷新按钮到标题右侧
        self._refresh_btn = PrimaryButton("刷新设备列表")
        self._refresh_btn.setMinimumHeight(32)
        self._refresh_btn.setMinimumWidth(120)
        self._refresh_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._refresh_btn.clicked.connect(self._on_full_refresh_devices)
        self._refresh_btn.setToolTip("刷新设备列表，显示最新的设备配置")
        title_layout.addWidget(self._refresh_btn)

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
        from ui.widgets import Colors

        self._auto_reconnect_btn = PrimaryButton("禁用重连")
        self._auto_reconnect_btn.setCheckable(True)
        self._auto_reconnect_btn.setChecked(False)
        self._auto_reconnect_btn.setMinimumHeight(36)
        self._auto_reconnect_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._auto_reconnect_btn.clicked.connect(self._toggle_all_auto_reconnect)
        self._auto_reconnect_btn.setToolTip("切换所有设备的自动重连功能")
        # 初始样式 - 禁用状态（红色）
        self._auto_reconnect_btn.setStyleSheet(
            f"""
            QPushButton {{ background: {Colors.DANGER}; color: #FFFFFF;
            border: none; border-radius: {Colors.RADIUS}; padding: 6px 16px;
            font-size: 13px; font-weight: 500; }}
            QPushButton:hover {{ background: {Colors.DANGER_HOVER}; }}
            QPushButton:pressed {{ background: {Colors.DANGER}; opacity: 0.8; }}
            QPushButton:disabled {{ color: #9CA3AF; background: #F3F4F6; }}
            """
        )

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
        from ui.command_terminal import CommandTerminalWidget

        page = self._monitor_controller.build(
            parent=self,
            styles=AppStyles.__dict__,
            constants=TextConstants.__dict__,
            on_manage_cards=self._on_manage_cards,
            on_manage_charts=self._on_manage_charts,
            on_expand_panel=self._expand_left_panel,
            on_command_send=self._on_command_terminal_send,
            command_terminal_cls=CommandTerminalWidget,
        )

        self._expand_btn = self._monitor_controller.expand_btn
        self._device_title_label = self._monitor_controller.device_title_label
        self._device_name_label = self._monitor_controller.device_name_label
        self._last_update_label = self._monitor_controller.last_update_label
        self._device_status_badge = self._monitor_controller.device_status_badge
        self._right_splitter = self._monitor_controller.right_splitter
        self._monitor_tabs = self._monitor_controller.monitor_tabs
        self._command_terminal = self._monitor_controller.get_command_terminal()
        self._data_cards_layout = self._monitor_controller.data_cards_layout
        self._chart_layout = self._monitor_controller.chart_layout
        self._register_table = self._monitor_controller.get_register_table()
        self._manage_cards_btn = self._monitor_controller.manage_cards_btn
        self._manage_charts_btn = self._monitor_controller.manage_charts_btn

        return page

    def _update_cards_display(self) -> None:
        from ui.widgets import DataCard

        self._monitor_controller.update_cards_display(
            current_device_id=self._current_device_id or "",
            device_cards=self._device_cards,
            data_card_cls=DataCard,
        )

    def _log_message(self, message: str, level: str = "INFO", device_id: str = None, operation: str = None) -> None:
        if hasattr(self, "_command_terminal"):
            self._command_terminal.add_system_log(message, level)

    def _connect_signals(self) -> None:
        """连接设备管理器信号到UI处理槽函数（v4.0 DataBus订阅版）"""
        self._device_manager.device_added.connect(self._on_device_added)
        self._device_manager.device_removed.connect(self._on_device_removed)
        self._device_manager.device_connected.connect(self._on_device_connected)
        self._device_manager.device_disconnected.connect(self._on_device_disconnected)
        self._device_manager.device_error.connect(self._on_device_error)

        if hasattr(self._device_manager, "async_poll_success"):
            self._device_manager.async_poll_success.connect(self._on_async_poll_success)
            self._device_manager.async_poll_failed.connect(self._on_async_poll_failed)
            self._device_manager.async_poll_timeout.connect(self._on_async_poll_timeout)

        self._write_manager.confirm_required.connect(self._show_write_confirmation)
        self._write_manager.operation_result.connect(self._on_write_operation_result)

        self._device_controller.raw_send_result.connect(self._on_raw_send_result)

        self._connect_data_bus()

    def _connect_data_bus(self):
        """订阅 DataBus 全局信号 — 统一数据更新入口（规范控制点⑥）"""
        from core.foundation.data_bus import DataBus

        bus = DataBus.instance()

        bus.subscribe("device_data_updated", self._on_bus_device_data_updated)
        bus.subscribe("device_data_changed", self._on_bus_device_data_changed)
        bus.subscribe("comm_error", self._on_bus_comm_error)
        bus.subscribe("device_status_changed", self._on_bus_device_status_changed)
        bus.subscribe("device_connected", self._on_bus_device_connected)
        bus.subscribe("device_disconnected", self._on_bus_device_disconnected)
        bus.subscribe("alarm_triggered", self._on_bus_alarm_triggered)

    @Slot(str, dict)
    def _on_bus_device_data_updated(self, device_id: str, data: dict):
        """DataBus 数据更新回调 — 更新日志 + 监控面板数据"""
        if data:
            param_names = list(data.keys())[:3]
            param_str = ", ".join(param_names)
            if len(data) > 3:
                param_str += f" 等{len(data)}个参数"
            message = f"数据更新: {param_str}"
            self._log_message(message, "INFO", device_id, "DATA_UPDATE")
            self._last_update_label.setText(f"{TextConstants.LAST_UPDATE_LABEL} {datetime.now().strftime('%H:%M:%S')}")
        if data:
            was_none = self._current_device_id is None
            if was_none or self._current_device_id == device_id:
                if device_id not in self._device_cards:
                    self._auto_setup_monitor_for_device(device_id)
                self._update_card_values(data)
                self._update_chart_data(data)
                self._update_register_table_from_data(data)

    def _auto_setup_monitor_for_device(self, device_id: str):
        """数据到达时自动初始化监控面板（用户未手动选中设备时）"""
        reader = None
        if self._mcgs_controller:
            reader = self._mcgs_controller.get_reader()
        config = None
        if reader:
            config = reader.get_device_config(device_id)
        if config:
            self._current_device_id = device_id
            self._stack_widget.setCurrentIndex(1)
            display_name = getattr(config, "name", device_id) or device_id
            self._device_name_label.setText(display_name)
            self._device_status_badge.set_status("online")
            points = getattr(config, "points", []) or []
            cards_config = []
            register_map = []
            for p in points:
                p_name = getattr(p, "name", "")
                p_addr = getattr(p, "addr", "")
                p_unit = getattr(p, "unit", "")
                cards_config.append({"title": f"{p_name}\n[{p_addr}]", "register_name": p_name})
                register_map.append(
                    {"address": p_addr, "function_code": "03", "name": p_name, "value": "-", "unit": p_unit}
                )
            self._device_cards[device_id] = cards_config
            self._update_cards_display()
            self._update_register_table(register_map)

    def _update_register_table_from_data(self, data: dict):
        """根据DataBus数据更新寄存器表格"""
        self._register_table.setRowCount(len(data))
        for row, (name, value_info) in enumerate(data.items()):
            if isinstance(value_info, dict):
                value = value_info.get("value", "")
                addr = value_info.get("address", "")
                unit = value_info.get("unit", "")
            else:
                value = str(value_info) if value_info is not None else ""
                addr = ""
                unit = ""
            self._register_table.setItem(row, 0, QTableWidgetItem(str(addr)))
            self._register_table.setItem(row, 1, QTableWidgetItem("03"))
            self._register_table.setItem(row, 2, QTableWidgetItem(name))
            self._register_table.setItem(row, 3, QTableWidgetItem(str(value)))
            self._register_table.setItem(row, 4, QTableWidgetItem(unit))
            for col in range(5):
                item = self._register_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._register_table.resizeColumnsToContents()

    @Slot(str, dict, set)
    def _on_bus_device_data_changed(self, device_id: str, data: dict, changed_keys: set):
        """DataBus 死区过滤后的数据变更回调 — 更新监控面板"""
        if data:
            if self._current_device_id is None or self._current_device_id == device_id:
                self._update_card_values(data)
                self._update_chart_data(data)
                self._update_register_table_from_data(data)

    @Slot(str, str)
    def _on_bus_comm_error(self, device_id: str, error_msg: str):
        """DataBus 通信错误回调"""
        logger.warning("[DataBus] 通信错误 [%s]: %s", device_id, error_msg)
        self._status_msg_label.setText(f"通信错误: {device_id} - {error_msg}")

    @Slot(str, str)
    def _on_bus_device_status_changed(self, device_id: str, status: str):
        """DataBus 设备状态变更回调"""
        logger.info("[DataBus] 设备状态 [%s]: %s", device_id, status)
        self._update_status_bar()

    @Slot(str)
    def _on_bus_device_connected(self, device_id: str):
        """DataBus 设备连接回调"""
        self._refresh_device_list(self._search_edit.text())
        self._setup_command_terminal_device_links()
        self._log_message("设备已连接", "SUCCESS", device_id, "CONNECT")

    @Slot(str)
    def _on_bus_device_disconnected(self, device_id: str):
        """DataBus 设备断开回调"""
        self._refresh_device_list(self._search_edit.text())
        self._setup_command_terminal_device_links()
        self._log_message("设备已断开", "INFO", device_id, "DISCONNECT")

    @Slot(str, str, str, float)
    def _on_bus_alarm_triggered(self, device_id: str, param_name: str, alarm_type: str, value: float):
        """DataBus 报警触发回调"""
        self._log_message(f"报警: {param_name} {alarm_type} (值={value})", "WARNING", device_id, "ALARM")

    def _apply_theme(self) -> None:
        self._theme_manager.apply_theme()

    def _on_full_refresh_devices(self) -> None:
        """刷新设备列表（重载 MCGS 配置 + 刷新 UI）"""
        # 重新创建 MCGS 读取器以加载最新的 devices.json
        if self._mcgs_controller:
            self._mcgs_controller.reset_reader()
            self._get_or_create_mcgsm_reader()

        self._refresh_device_list()
        self._setup_command_terminal_device_links()
        self._log_message("设备列表已刷新", "INFO")

    def _refresh_device_list(self, search_text: str = "") -> None:
        """从 MCGS 配置 (devices.json) 加载设备列表，替代通用协议栈"""
        current_device_id = self._current_device_id

        self._device_tree.currentItemChanged.disconnect(self._on_device_selected)
        self._device_tree.clear()

        # ── 从 MCGS Controller 获取设备列表 ──
        mcgs_devices = self._get_mcgs_device_list()

        for dev in mcgs_devices:
            device_id = dev["id"]
            name = dev["name"]

            if search_text and search_text.lower() not in name.lower():
                continue

            is_connected = dev.get("connected", False)

            item = QTreeWidgetItem()
            item.setText(0, "MCGS触摸屏")  # 设备类型
            item.setText(1, f"{dev['ip']}:{dev['port']}")  # IP:端口标识
            item.setText(2, str(dev.get("point_count", 0)))  # 点位数量
            item.setText(3, "在线" if is_connected else "离线")  # 连接状态

            item.setTextAlignment(0, Qt.AlignmentFlag.AlignCenter)
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            item.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
            item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
            item.setData(0, Qt.ItemDataRole.UserRole, device_id)
            item.setSizeHint(0, QSize(0, 48))
            self._device_tree.addTopLevelItem(item)

            # 操作按钮：仅连接/断开（无编辑按钮，MCGS 设备通过配置对话框编辑）
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)

            if is_connected:
                conn_btn = DangerButton(TextConstants.BTN_DISCONNECT)
                conn_btn.setToolTip("断开连接")
            else:
                conn_btn = SuccessButton(TextConstants.BTN_CONNECT)
                conn_btn.setToolTip("连接设备")
            conn_btn.setMinimumHeight(30)
            conn_btn.setMaximumHeight(38)
            conn_btn.setMinimumWidth(44)
            conn_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            conn_btn.clicked.connect(lambda checked, did=device_id: self._toggle_mcgs_connection(did))

            action_layout.addWidget(conn_btn)
            self._device_tree.setItemWidget(item, 4, action_widget)

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

    def _get_mcgs_device_list(self) -> list:
        """
        从 MCGS 配置获取设备列表数据。

        优先从 MCGSModbusReader 获取，备用从 DeviceManager 网关模型获取。

        Returns:
            list[dict]: 每个元素包含 id, name, ip, port, point_count, connected 等字段
        """
        result = []

        if self._mcgs_controller is not None:
            reader = self._mcgs_controller.get_reader()
            if reader is not None:
                try:
                    device_ids = reader.list_devices()
                    for device_id in device_ids:
                        config = reader.get_device_config(device_id)
                        if config:
                            result.append(
                                {
                                    "id": config.id,
                                    "name": config.name,
                                    "ip": config.ip,
                                    "port": config.port,
                                    "point_count": len(config.points),
                                    "connected": reader.is_device_connected(device_id),
                                }
                            )
                except Exception as e:
                    logger.warning("获取 MCGS 设备列表失败: %s", e)

        if not result and hasattr(self._device_manager, "get_all_gateway_models"):
            try:
                models = self._device_manager.get_all_gateway_models()
                for gw_id, model in models.items():
                    result.append(
                        {
                            "id": model.id,
                            "name": model.name,
                            "ip": model.ip,
                            "port": model.port,
                            "point_count": model.variable_count,
                            "connected": self._device_manager.is_gateway_connected(gw_id),
                        }
                    )
            except Exception as e:
                logger.warning("从网关模型获取设备列表失败: %s", e)

        return result

    def _toggle_mcgs_connection(self, device_id: str) -> None:
        """切换 MCGS 设备的连接状态（通过 MCGSController 异步调度）"""
        if self._mcgs_controller is None:
            self._log_message("MCGS 控制器未初始化", "ERROR")
            return

        reader = self._mcgs_controller.get_reader()
        is_connected = reader and reader.is_device_connected(device_id)

        if is_connected:
            self._mcgs_controller.disconnect_device(device_id)
            self._log_message(f"MCGS 断开请求已发送: {device_id}", "INFO", device_id, "DISCONNECT")
        else:
            self._mcgs_controller.connect_device(device_id)
            self._log_message(f"MCGS 连接请求已发送: {device_id}", "INFO", device_id, "CONNECT")

        # 延迟刷新列表以反映状态变化
        QTimer.singleShot(500, lambda: self._refresh_device_list(self._search_edit.text()))

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
        # 基准 150px (两按钮各50px + 间距6px + 边距)，最大 200px
        action_col_width = int(130 + max(0, panel_width - 600) * 0.15)
        action_col_width = max(150, min(action_col_width, 200))  # 从170-260调整为150-200
        # 操作列索引为4，因为前面有4列（0-3）
        self._device_tree.setColumnWidth(4, action_col_width)

        # 更新所有行的行高和操作列按钮
        from PySide6.QtWidgets import QPushButton

        btn_min_h = max(26, row_height - 20)
        btn_max_h = row_height - 10

        for i in range(self._device_tree.topLevelItemCount()):
            item = self._device_tree.topLevelItem(i)
            item.setSizeHint(0, QSize(0, row_height))
            # 更新操作列中的按钮尺寸，操作列索引为4
            action_widget = self._device_tree.itemWidget(item, 4)
            if action_widget:
                for btn in action_widget.findChildren(QPushButton):
                    btn.setMinimumHeight(btn_min_h)
                    btn.setMaximumHeight(btn_max_h)

    def _add_device(self) -> None:
        from ui.device_type_dialogs import DeviceTypeManager

        logger.debug("Opening add device dialog")
        try:
            device_type_manager = DeviceTypeManager("device_types.json")
            dialog = AddDeviceDialog(device_type_manager, self)
            if dialog.exec():
                config = dialog.get_device_config()
                device_id = self._device_manager.add_device(config)
                logger.info(LogMessages.DEVICE_ADDED.format(device_id=device_id))
                self._status_msg_label.setText(f"设备添加成功: {device_id}")
        except Exception as e:
            logger.error("添加设备失败: %s", str(e))
            QMessageBox.warning(self, "添加设备失败", f"无法添加设备: {str(e)}")
            self._status_msg_label.setText(f"添加设备失败: {str(e)}")

    def _remove_device(self) -> None:
        item = self._device_tree.currentItem()
        if not item:
            QMessageBox.warning(self, UIMessages.SELECT_DEVICE_TITLE, UIMessages.SELECT_DEVICE_MSG)
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
            try:
                success = self._device_manager.remove_device(device_id)
                if success:
                    logger.info(LogMessages.DEVICE_REMOVED.format(device_id=device_id))
                    self._status_msg_label.setText(f"设备移除成功: {device_id}")
                else:
                    logger.error("移除设备失败: %s", device_id)
                    QMessageBox.warning(self, "移除设备失败", f"无法移除设备: {device_id}")
                    self._status_msg_label.setText(f"移除设备失败: {device_id}")
            except Exception as e:
                logger.error("移除设备失败: %s", str(e))
                QMessageBox.warning(self, "移除设备失败", f"无法移除设备: {str(e)}")
                self._status_msg_label.setText(f"移除设备失败: {str(e)}")

    def _set_operation_lock(self, locked: bool, btn: Optional[QPushButton] = None, loading_text: str = "") -> None:
        """设置操作锁，防止重复点击（P0-2修复）

        Args:
            locked: 是否锁定
            btn: 需要禁用的按钮（可选）
            loading_text: 按钮在锁定时显示的文字
        """
        self._operation_lock = locked

        if locked and btn is not None:
            # 锁定：禁用按钮并显示加载状态
            self._current_operation_btn = btn
            original_text = btn.text()
            btn.setEnabled(False)
            btn.setText(loading_text or original_text)
            # 存储原始文字以便恢复
            if not hasattr(btn, "_original_text"):
                btn._original_text = original_text
        elif not locked and self._current_operation_btn is not None:
            # 解锁：恢复按钮状态
            btn = self._current_operation_btn
            btn.setEnabled(True)
            if hasattr(btn, "_original_text"):
                btn.setText(btn._original_text)
                delattr(btn, "_original_text")
            self._current_operation_btn = None

    def _connect_device_by_id(self, device_id: str) -> None:
        # P0-2修复：检查操作锁，防止重复点击
        if self._operation_lock:
            logger.debug("连接操作正在进行中，忽略重复请求")
            return

        try:
            # 获取当前行的连接按钮并锁定
            current_item = self._device_tree.currentItem()
            connect_btn = None
            if current_item:
                action_widget = self._device_tree.itemWidget(current_item, 4)
                if action_widget:
                    for btn in action_widget.findChildren(QPushButton):
                        if "连接" in btn.text() or "Connect" in btn.text():
                            connect_btn = btn
                            break

            self._set_operation_lock(True, connect_btn, "连接中...")
            self._status_msg_label.setText("正在连接...")

            success, error_type, error_msg = self._device_manager.connect_device(device_id)
            if success:
                logger.info(LogMessages.DEVICE_CONNECTING.format(device_id=device_id))
                self._status_msg_label.setText(f"设备连接成功: {device_id}")
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
                logger.error("连接失败详情: 类型=%s, 消息=%s", error_type, error_msg)
                self._status_msg_label.setText(f"设备连接失败: {error_msg}")
        except Exception as e:
            logger.error("连接设备失败: %s", str(e))
            QMessageBox.warning(self, UIMessages.CONNECT_FAILED_TITLE, f"连接设备时发生错误: {str(e)}")
            self._status_msg_label.setText(f"连接设备失败: {str(e)}")
        finally:
            # P0-2修复：解锁操作
            self._set_operation_lock(False)

            # 刷新设备列表，更新连接状态
            self._refresh_device_list()
            # 更新状态栏显示
            self._update_status_bar()

    def _disconnect_device_by_id(self, device_id: str) -> None:
        # P0-2修复：检查操作锁，防止重复点击
        if self._operation_lock:
            logger.debug("断开操作正在进行中，忽略重复请求")
            return

        try:
            # 获取当前行的断开按钮并锁定
            current_item = self._device_tree.currentItem()
            disconnect_btn = None
            if current_item:
                action_widget = self._device_tree.itemWidget(current_item, 4)
                if action_widget:
                    for btn in action_widget.findChildren(QPushButton):
                        if "断开" in btn.text() or "Disconnect" in btn.text():
                            disconnect_btn = btn
                            break

            self._set_operation_lock(True, disconnect_btn, "断开中...")
            success = self._device_manager.disconnect_device(device_id)
            if success:
                logger.info(LogMessages.DEVICE_DISCONNECTED.format(device_id=device_id))
                self._status_msg_label.setText(f"设备断开成功: {device_id}")
            else:
                logger.error("断开设备失败: %s", device_id)
                self._status_msg_label.setText(f"断开设备失败: {device_id}")
        except Exception as e:
            logger.error("断开设备失败: %s", str(e))
            self._status_msg_label.setText(f"断开设备失败: {str(e)}")
        finally:
            # P0-2修复：解锁操作
            self._set_operation_lock(False)

            # 刷新设备列表，更新连接状态
            self._refresh_device_list()
            # 更新状态栏显示
            self._update_status_bar()

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

        try:
            from ui.device_type_dialogs import DeviceTypeManager

            config = device.get_device_config()
            device_type_manager = DeviceTypeManager("device_types.json")
            dialog = AddDeviceDialog(device_type_manager, self, edit_mode=True, device_config=config)
            if dialog.exec():
                new_config = dialog.get_device_config()
                success = self._device_manager.edit_device(device_id, new_config)
                if success:
                    logger.info(LogMessages.DEVICE_EDIT_SUCCESS.format(device_id=device_id))
                    self._status_msg_label.setText(f"设备编辑成功: {device_id}")
                else:
                    logger.error("编辑设备失败: %s", device_id)
                    self._status_msg_label.setText(f"编辑设备失败: {device_id}")
        except Exception as e:
            logger.error("编辑设备失败: %s", str(e))
            QMessageBox.warning(self, "编辑设备失败", f"无法编辑设备: {str(e)}")
            self._status_msg_label.setText(f"编辑设备失败: {str(e)}")
        finally:
            # 确保对话框被正确释放
            if "dialog" in locals():
                dialog.deleteLater()
            if "device_type_manager" in locals():
                del device_type_manager

    def _update_monitor_page(self, device_id: str) -> None:
        device = self._device_manager.get_device(device_id)
        if not device:
            # 没有选中设备时，显示默认信息
            self._device_title_label.setText(f"{TextConstants.DEVICE_MONITOR_TITLE}")
            self._device_name_label.setText("未选择设备")
            self._device_status_badge.set_status("offline")
            self._last_update_label.setText("-")
            self._update_cards_display()
            self._update_register_table([])
            return

        config = device.get_device_config()
        status = device.get_status()

        # 优化设备名称显示：优先使用name，如果name包含ID格式则提取友好名称
        raw_name = config.get("name", "") or ""
        # 如果name为空或只是device_id的副本，使用更友好的显示
        if not raw_name or raw_name == device_id:
            # 尝试从device_type生成友好名称
            device_type = config.get("device_type", "未知设备")
            display_name = f"{device_type} ({device_id[:8]}...)"
        elif len(raw_name) > 30:
            # 名称过长时截断
            display_name = f"{raw_name[:27]}..."
        else:
            display_name = raw_name

        self._device_title_label.setText(f"{TextConstants.DEVICE_MONITOR_TITLE}")
        self._device_name_label.setText(display_name)

        status_text, badge_type = StatusText.get_text_with_badge(status)
        # badge_type: "success"/"warning"/"info"/"error" → StatusBadge status: "online"/"offline"/"warning"/"error"
        badge_status_map = {"success": "online", "warning": "warning", "info": "warning", "error": "error"}
        badge_status = badge_status_map.get(badge_type, "offline")
        self._device_status_badge.set_status(badge_status)

        self._last_update_label.setText(datetime.now().strftime("%H:%M:%S"))

        # 获取寄存器列表 (从设备对象或配置中获取)
        register_map = config.get("register_map", [])
        if not register_map and hasattr(device, "_register_map"):
            register_map = device._register_map

        self._update_cards_display()
        self._update_register_table(register_map)

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
                fmt = "csv"
            elif file_path.endswith(".xlsx"):
                fmt = "excel"
            elif file_path.endswith(".json"):
                fmt = "json"
            else:
                fmt = ""
            success = self._device_controller.export_data(export_data, file_path, fmt) if fmt else False

            if success:
                QMessageBox.information(
                    self, UIMessages.EXPORT_SUCCESS_TITLE, UIMessages.EXPORT_SUCCESS_MSG.format(path=file_path)
                )
                logger.info(LogMessages.DATA_EXPORT_SUCCESS.format(path=file_path))
            else:
                QMessageBox.warning(self, UIMessages.EXPORT_FAILED_TITLE, UIMessages.EXPORT_FAILED_MSG)

    def _show_batch_operations(self) -> None:
        dialog = BatchOperationsDialog(self._device_manager, self)
        dialog.operations_completed.connect(self._on_batch_operations_completed)
        dialog.exec()

    def _on_batch_operations_completed(self, success_count: int, total_count: int) -> None:
        self._refresh_device_list()
        self._update_status_bar()
        logger.info(LogMessages.BATCH_OPS_COMPLETE.format(success=success_count, total=total_count))

    def _show_export_device_config_dialog(self) -> None:
        """打开设备配置导出对话框"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出设备配置", "", "JSON Files (*.json)")

        if file_path:
            # 导出所有设备配置
            success = self._device_manager.export_devices_config(file_path)
            if success:
                QMessageBox.information(
                    self,
                    UIMessages.EXPORT_SUCCESS_TITLE,
                    UIMessages.DEVICE_CONFIG_EXPORT_SUCCESS_MSG.format(path=file_path),
                )
                logger.info(LogMessages.DATA_EXPORT_SUCCESS.format(path=file_path))
            else:
                QMessageBox.warning(self, UIMessages.EXPORT_FAILED_TITLE, UIMessages.DEVICE_CONFIG_EXPORT_FAILED_MSG)

    def _show_import_device_config_dialog(self) -> None:
        """打开设备配置导入对话框"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入设备配置", "", "JSON Files (*.json)")

        if file_path:
            # 确认导入
            reply = QMessageBox.question(
                self,
                UIMessages.IMPORT_CONFIRM_TITLE,
                UIMessages.DEVICE_CONFIG_IMPORT_CONFIRM_MSG,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 导入设备配置
                success = self._device_manager.import_devices_config(file_path, overwrite=True)
                if success:
                    QMessageBox.information(
                        self, UIMessages.IMPORT_SUCCESS_TITLE, UIMessages.DEVICE_CONFIG_IMPORT_SUCCESS_MSG
                    )
                    # 刷新设备列表
                    self._refresh_device_list()
                else:
                    QMessageBox.warning(
                        self, UIMessages.IMPORT_FAILED_TITLE, UIMessages.DEVICE_CONFIG_IMPORT_FAILED_MSG
                    )

    def _show_about(self) -> None:
        QMessageBox.about(self, UIMessages.ABOUT_TITLE, UIMessages.ABOUT_MSG)

    def _on_device_selected(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        if not current:
            self._stack_widget.setCurrentIndex(0)
            return

        device_id = current.data(0, Qt.ItemDataRole.UserRole)

        if device_id == self._current_device_id:
            logger.info("[设备选中] 同一设备已选中，跳过重建: %s", device_id)
            return

        logger.info("[设备选中] _on_device_selected 触发: device_id=%s (之前=%s)", device_id, self._current_device_id)
        self._current_device_id = device_id

        is_mcgs_device = False
        reader = None
        if self._mcgs_controller:
            reader = self._mcgs_controller.get_reader()
        if reader:
            config = reader.get_device_config(device_id)
            if config:
                is_mcgs_device = True
                self._log_message(
                    f"MCGS设备已选中: {config.name} ({config.ip}:{config.port})", "INFO", device_id, "SELECT"
                )
                self._update_monitor_page_for_mcgs(device_id, config)
            else:
                self._log_message(f"设备已选中: {device_id}", "INFO", device_id, "SELECT")
        else:
            self._log_message(f"设备已选中: {device_id}", "INFO", device_id, "SELECT")

        if not is_mcgs_device:
            self._stack_widget.setCurrentIndex(0)

    def _update_monitor_page_for_mcgs(self, device_id: str, config) -> None:
        """为MCGS设备更新监控面板"""
        self._stack_widget.setCurrentIndex(1)
        display_name = getattr(config, "name", device_id) or device_id
        self._device_name_label.setText(display_name)
        self._device_status_badge.set_status("online")
        self._last_update_label.setText(datetime.now().strftime("%H:%M:%S"))
        points = getattr(config, "points", []) or []

        cards_already_exist = device_id in self._device_cards and self._data_cards_layout.count() > 0
        if cards_already_exist:
            logger.info("[MCGS监控页] 卡片已存在，仅更新头部信息，跳过重建: %s", device_id)
            return

        logger.info("[MCGS监控页] 首次创建卡片: %s", device_id)
        register_map = []
        cards_config = []
        for p in points:
            p_name = getattr(p, "name", "")
            p_addr = getattr(p, "addr", "")
            p_unit = getattr(p, "unit", "")
            p_desc = getattr(p, "description", "")
            register_map.append(
                {
                    "address": p_addr,
                    "function_code": "03",
                    "name": p_name,
                    "value": "-",
                    "unit": p_unit,
                }
            )
            cards_config.append(
                {
                    "title": f"{p_name}\n[{p_addr}]",
                    "register_name": p_name,
                }
            )
        self._device_cards[device_id] = cards_config
        self._update_cards_display()
        self._update_register_table(register_map)

    @Slot(str)
    def _on_device_added(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._setup_command_terminal_device_links()
        message = f"设备已添加"
        self._status_msg_label.setText(f"设备已添加: {device_id}")
        self._log_message(message, "SUCCESS", device_id, "ADD")

    @Slot(str)
    def _on_device_removed(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._setup_command_terminal_device_links()
        self._stack_widget.setCurrentIndex(0)
        message = f"设备已移除"
        self._status_msg_label.setText(f"设备已移除: {device_id}")
        self._log_message(message, "INFO", device_id, "REMOVE")

    @Slot(str)
    def _on_device_connected(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._setup_command_terminal_device_links()
        message = f"设备已连接"
        self._status_msg_label.setText(f"设备已连接: {device_id}")
        logger.info(LogMessages.DEVICE_CONNECTED.format(device_id=device_id))
        self._log_message(message, "SUCCESS", device_id, "CONNECT")

    @Slot(str)
    def _on_device_disconnected(self, device_id: str) -> None:
        self._refresh_device_list(self._search_edit.text())
        self._update_status_bar()
        self._setup_command_terminal_device_links()
        message = f"设备已断开"
        self._status_msg_label.setText(f"设备已断开: {device_id}")
        logger.info(LogMessages.DEVICE_DISCONNECTED.format(device_id=device_id))
        self._log_message(message, "INFO", device_id, "DISCONNECT")
        if self._current_device_id == device_id:
            self._update_monitor_page(device_id)

    @Slot(str, dict)
    def _on_device_data_updated(self, device_id: str, data: dict) -> None:
        """设备数据更新回调 — 已迁移至 DataBus 订阅（保留向后兼容）"""
        self._on_bus_device_data_updated(device_id, data)

    def _update_card_values(self, data: Dict[str, Any]) -> None:
        """更新数据卡片数值"""
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
        logger.error("Device error: %s - %s", device_id, error)
        message = f"错误: {error}"
        self._status_msg_label.setText(f"设备错误: {device_id} - {error}")
        self._update_status_bar()
        self._log_message(message, "ERROR", device_id, "ERROR")

    # ══════════════════════════════════════════════
    # 异步轮询结果处理（v3.0新增）
    # ══════════════════════════════════════════════

    @Slot(str, dict, float)
    def _on_async_poll_success(
        self,
        device_id: str,
        data: dict,
        response_time_ms: float,
    ) -> None:
        """
        处理异步轮询成功（带性能数据）

        此方法在主线程中被调用（Qt Signal/Slot自动排队），
        可以安全地更新UI元素。

        Args:
            device_id: 设备唯一标识符
            data: 轮询到的数据字典
            response_time_ms: 响应耗时（毫秒），用于性能监控
        """
        # 性能监控：如果响应时间过长，记录警告
        if response_time_ms > 100:
            logger.warning(
                "[PERF] 设备 %s 轮询响应时间过长: %.1fms (正常<50ms)",
                device_id,
                response_time_ms,
            )

        # 更新状态栏显示（带性能数据）
        self._status_msg_label.setText(f"设备 {device_id[:8]}... 轮询完成 ({response_time_ms:.0f}ms)")
        self._update_status_bar()

    @Slot(str, str, str)
    def _on_async_poll_failed(
        self,
        device_id: str,
        error_type: str,
        error_msg: str,
    ) -> None:
        """处理异步轮询失败"""
        logger.warning(
            "Async poll failed: %s - [%s] %s",
            device_id,
            error_type,
            error_msg,
        )

        # 更新状态栏（不阻塞UI，因为这是异步通知）
        self._status_msg_label.setText(f"轮询异常: {device_id[:8]}... - {error_type}")
        self._update_status_bar()

    @Slot(str, float)
    def _on_async_poll_timeout(
        self,
        device_id: str,
        elapsed_ms: float,
    ) -> None:
        """处理异步轮询超时"""
        logger.debug("Async poll timeout: %s (%.1fms)", device_id, elapsed_ms)

        # 超时是常见情况（Modbus RTU慢速设备），仅记录不告警
        if elapsed_ms > 200:
            logger.info(
                "设备 %s 轮询超时较严重: %.1fms",
                device_id,
                elapsed_ms,
            )

    def _update_status_bar(self) -> None:
        """更新状态栏信息"""
        all_devices = self._device_manager.get_all_devices()
        total_count = len(all_devices)
        online_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.CONNECTED)
        offline_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.DISCONNECTED)
        connecting_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.CONNECTING)
        error_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.ERROR)

        # 更新设备状态统计
        self._status_total_label.setText(f"设备 {total_count}")
        self._status_online_label.setText(f"● 在线 {online_count}")
        self._status_offline_label.setText(f"● 离线 {offline_count}")
        self._status_error_label.setText(f"● 错误 {error_count}")

        # 如果有正在连接的设备，显示连接中状态
        if connecting_count > 0:
            self._status_msg_label.setText(f"正在连接 {connecting_count} 台设备...")

        # 更新自动重连状态
        self._update_auto_reconnect_status()

        # 添加时间戳，显示最后更新时间
        current_time = datetime.now().strftime("%H:%M:%S")
        self._status_time_label.setText(f"更新时间: {current_time}")

        # 更新命令统计
        if hasattr(self, "_command_terminal"):
            tx_count = self._command_terminal.get_tx_count()
            rx_count = self._command_terminal.get_rx_count()
            if hasattr(self, "_status_tx_label"):
                self._status_tx_label.setText(f"TX: {tx_count}")
            if hasattr(self, "_status_rx_label"):
                self._status_rx_label.setText(f"RX: {rx_count}")

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
            self._ui_prefs.save_cards(self._current_device_id, self._device_cards[self._current_device_id])
            self._update_cards_display()

    def cleanup(self) -> None:
        if getattr(self, "_cleaned", False):
            return
        self._cleaned = True
        logger.info(LogMessages.APP_SHUTDOWN)
        self._save_ui_preferences()

        # 清理全局动画调度器单例
        try:
            from ui.animation_scheduler import AnimationScheduler

            AnimationScheduler.cleanup_instance()
        except Exception:
            pass

        if hasattr(self, "_cleanup_scheduler") and self._cleanup_scheduler:
            self._cleanup_scheduler.stop()
        self._device_manager.cleanup()

    def _load_ui_preferences(self) -> None:
        try:
            self._device_cards = {}
            self._device_charts = {}
            panel_state = self._ui_prefs.load_panel_state()
            if panel_state:
                self._left_panel_collapsed = panel_state.get("left_collapsed", False)
                self._left_panel_saved_size = panel_state.get("left_width", 480)

            raw_cards = getattr(self._ui_prefs, "_data", {}).get("device_cards", {})
            for device_id in raw_cards:
                self._device_cards[device_id] = self._ui_prefs.load_cards(device_id)
            raw_charts = getattr(self._ui_prefs, "_data", {}).get("device_charts", {})
            for device_id in raw_charts:
                self._device_charts[device_id] = self._ui_prefs.load_charts(device_id)

            logger.debug(
                "UI 偏好配置已加载: %d 设备卡片, %d 设备图表",
                len(self._device_cards),
                len(self._device_charts),
            )
        except Exception:
            logger.exception("加载 UI 偏好配置失败")

    def _save_ui_preferences(self) -> None:
        try:
            for device_id, cards in self._device_cards.items():
                self._ui_prefs.save_cards(device_id, cards)
            for device_id, charts in self._device_charts.items():
                self._ui_prefs.save_charts(device_id, charts)
            self._ui_prefs.save_panel_state(
                left_collapsed=self._left_panel_collapsed,
                left_width=self._left_panel_saved_size,
            )
            logger.debug("UI 偏好配置已保存")
        except Exception:
            logger.exception("保存 UI 偏好配置失败")

    # ══════════════════════════════════════════════════════════
    # ✅ 新增：权限管理相关方法
    # ══════════════════════════════════════════════════════════

    def _on_permission_changed(self) -> None:
        """
        权限状态变化槽函数

        当用户登录/登出或角色变更时调用，
        更新UI状态（按钮启用/禁用、菜单显示等）。
        """
        self._update_permission_ui()

    def _on_session_timeout(self, username: str) -> None:
        """
        会话超时槽函数

        Args:
            username: 超时的用户名
        """
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(
            self,
            "会话超时",
            f"用户 '{username}' 的会话已超时（30分钟无操作），已自动登出。\n\n" "请重新登录以继续操作。",
        )

        # 更新状态栏
        self._status_msg_label.setText(f"会话超时: {username} 已自动登出")

    def _update_permission_ui(self) -> None:
        """
        根据当前权限状态更新UI

        - 更新状态栏显示
        - 启用/禁用写操作相关按钮
        - 更新菜单项可见性
        """
        if not hasattr(self, "_permission_mgr"):
            return

        if self._permission_mgr.is_logged_in:
            # 已登录状态
            username = self._permission_mgr.current_username
            role = self._permission_mgr.current_user_role

            if role:
                role_display = role.display_name
                can_write = self._permission_mgr.can_write

                # 更新状态栏（如果有专门的权限标签）
                if hasattr(self, "_permission_label"):
                    self._permission_label.setText(f"用户: {username} ({role_display})")

                logger.debug("权限UI更新 [用户=%s, 角色=%s, 可写=%s]", username, role_display, can_write)
        else:
            # 未登录状态
            if hasattr(self, "_permission_label"):
                self._permission_label.setText("未登录")

            logger.debug("权限UI更新: 未登录")

    def show_login_dialog(self) -> None:
        """显示登录对话框"""
        from ui.login_dialog import LoginDialog

        dialog = LoginDialog(self._permission_mgr, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            username = dialog.username
            role = self._permission_mgr.current_user_role

            self._status_msg_label.setText(f"登录成功: {username} ({role.display_name if role else ''})")
            logger.info("用户登录成功: %s", username)
        else:
            logger.debug("登录对话框被取消")

    def show_logout_action(self) -> None:
        """执行登出操作"""
        if not self._permission_mgr.is_logged_in:
            return

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "确认登出",
            "确定要退出当前账户吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            username = self._permission_mgr.current_username
            self._permission_mgr.logout()

            self._status_msg_label.setText(f"已登出: {username}")
            logger.info("用户已登出: %s", username)

    # ═══════════════════════════════════════════════════════════
    # ✅ MCGS 快速连接模块 (v2.0 - 2026-04-23)
    # ═══════════════════════════════════════════════════════════

    def _init_mcgsm_controller(self) -> None:
        """初始化MCGS控制器（异步调度+Signal中转，替代直接调用通信层）"""
        try:
            from ui.controllers.mcgs_controller import MCGSController
            from core.services.mcgs_service import MCGSService
            from core.services.history_service import HistoryService
            from core.services.anomaly_service import AnomalyService

            db_path = (
                self._db_manager.db_path if hasattr(self._db_manager, "db_path") else "data/equipment_management.db"
            )

            history_service = HistoryService(db_path=db_path)
            history_service.initialize()

            anomaly_service = AnomalyService(history_service=history_service)
            anomaly_service.initialize()

            mcgs_service = MCGSService(
                history_service=history_service,
                anomaly_service=anomaly_service,
            )

            self._mcgs_controller = MCGSController(mcgs_service=mcgs_service, parent=self)

            self._mcgs_controller.device_connected.connect(self._on_mcgsm_device_connected)
            self._mcgs_controller.device_data_updated.connect(self._on_mcgsm_data_updated)
            self._mcgs_controller.device_error.connect(self._on_mcgsm_device_error)
            self._mcgs_controller.polling_started.connect(self._on_mcgsm_polling_started)
            self._mcgs_controller.polling_stopped.connect(self._on_mcgsm_polling_stopped)
            self._mcgs_controller.poll_cycle_completed.connect(self._on_mcgsm_poll_cycle_completed)

            logger.info("MCGSController 初始化完成")

        except Exception as e:
            logger.error(f"MCGSController初始化失败: {e}")
            self._mcgs_controller = None
            QMessageBox.warning(self, "MCGS模块初始化失败", f"MCGS控制器初始化失败:\n{str(e)}")

    def _get_or_create_mcgsm_reader(self):
        """获取或创建MCGS读取器（通过Controller延迟初始化+缓存）"""
        if self._mcgs_controller is None:
            return None

        reader = self._mcgs_controller.get_reader()
        if reader is not None:
            return reader

        try:
            config_path = Path(__file__).parent.parent / "config" / "devices.json"

            if config_path.exists():
                reader = self._mcgs_controller.create_reader(str(config_path))
                if reader:
                    logger.info(f"MCGS读取器已创建: {config_path}")
                    return reader
                return None
            else:
                QMessageBox.warning(
                    self,
                    "配置文件缺失",
                    f"MCGS配置文件不存在:\n{config_path}\n\n" f"请创建 devices.json 并配置设备参数。",
                )
                return None

        except Exception as e:
            logger.error(f"创建MCGS读取器失败: {e}")
            QMessageBox.critical(self, "MCGS连接错误", f"无法初始化MCGS读取器:\n{str(e)}")
            return None

    @Slot()
    def _on_mcgsm_quick_connect(self) -> None:
        """
        MCGS快速连接入口（菜单/工具栏按钮触发）

        重构后: 通过 MCGSController 异步调度，不再阻塞UI

        功能：
        1. 加载devices.json配置
        2. 通过Controller异步连接MCGS触摸屏
        3. 结果通过Controller的Signal回调处理
        """
        logger.info("MCGS快速连接被触发")

        if self._mcgs_controller is None:
            QMessageBox.warning(self, "功能不可用", "MCGS控制器未初始化")
            return

        reader = self._get_or_create_mcgsm_reader()
        if reader is None:
            return

        try:
            self._status_msg_label.setText("正在连接MCGS设备...")

            device_ids = reader.list_devices()
            if not device_ids:
                QMessageBox.information(
                    self, "无设备", "devices.json中未配置任何设备。\n" "请先编辑 config/devices.json 添加设备配置。"
                )
                return

            self._mcgs_pending_connect_devices = list(device_ids)
            self._mcgs_connect_index = 0
            self._connect_next_mcgsm_device()

        except Exception as e:
            error_msg = f"MCGS连接过程出错: {str(e)}"
            logger.exception(error_msg)
            QMessageBox.critical(self, "MCGS连接错误", error_msg)
            self._status_msg_label.setText("MCGS连接失败")

    def _connect_next_mcgsm_device(self):
        """逐个异步连接MCGS设备"""
        if not hasattr(self, "_mcgs_pending_connect_devices"):
            return

        if self._mcgs_connect_index >= len(self._mcgs_pending_connect_devices):
            self._on_mcgsm_all_devices_connected()
            return

        device_id = self._mcgs_pending_connect_devices[self._mcgs_connect_index]
        logger.info(
            "异步连接MCGS设备: %s (%d/%d)",
            device_id,
            self._mcgs_connect_index + 1,
            len(self._mcgs_pending_connect_devices),
        )

        self._mcgs_controller.connect_device(device_id)

    def _on_mcgsm_all_devices_connected(self):
        """所有设备连接完成后的处理"""
        logger.info("[MCGS流程] _on_mcgsm_all_devices_connected 被调用")
        if not hasattr(self, "_mcgs_pending_connect_devices"):
            logger.warning("[MCGS流程] _mcgs_pending_connect_devices 不存在，跳过")
            return

        device_ids = self._mcgs_pending_connect_devices
        logger.info("[MCGS流程] 设备列表: %s, is_polling=%s", device_ids, self._mcgs_controller.is_polling)

        if not self._mcgs_controller.is_polling and device_ids:
            first_device = device_ids[0]
            reader = self._mcgs_controller.get_reader()
            if reader:
                config = reader.get_device_config(first_device) if hasattr(reader, "get_device_config") else None
                interval_ms = getattr(config, "polling_interval_ms", 1000) if config else 1000
            else:
                interval_ms = 1000
            self._mcgs_controller.start_polling(device_ids, interval_ms)

        del self._mcgs_pending_connect_devices
        if hasattr(self, "_mcgs_connect_index"):
            del self._mcgs_connect_index

    @Slot(str, bool, str)
    def _on_mcgsm_device_connected(self, device_id: str, success: bool, msg: str):
        """MCGS设备连接结果回调（由Controller异步触发）"""
        self._refresh_device_list(self._search_edit.text())

        if success:
            reader = self._mcgs_controller.get_reader() if self._mcgs_controller else None
            config = reader.get_device_config(device_id) if reader and hasattr(reader, "get_device_config") else None

            if self._mcgs_controller:
                self._mcgs_controller.read_device(device_id)

            self._status_msg_label.setText(f"MCGS连接成功: {device_id}")
            logger.info("[%s] MCGS设备连接成功", device_id)
            self._log_message(f"MCGS连接成功: {device_id}", "SUCCESS", device_id, "CONNECT")
        else:
            reader = self._mcgs_controller.get_reader() if self._mcgs_controller else None
            config = reader.get_device_config(device_id) if reader and hasattr(reader, "get_device_config") else None

            self._log_message(f"MCGS连接失败: {device_id}", "ERROR", device_id, "ERROR")

            error_detail = f"无法连接到设备 [{device_id}]\n"
            if config:
                error_detail += f"{config.name}@{config.ip}:{config.port}\n\n"
            error_detail += f"原因: {msg}"
            logger.warning("[%s] MCGS连接失败: %s", device_id, msg)
            error_detail += (
                f"可能的原因：\n"
                f"• IP地址或端口号错误\n"
                f"• 设备未开机或网络不通\n"
                f"• Modbus TCP端口502未开放\n"
                f"• Unit ID不匹配\n"
            )

            reply = QMessageBox.question(
                self,
                "连接失败 - 配置引导",
                f"{error_detail}\n\n" f"是否打开【设备配置编辑器】检查并修正参数？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                config_saved = self._open_mcgsm_config_dialog(device_id)
                if config_saved and self._mcgs_controller:
                    self._mcgs_controller.reset_reader()
                    new_reader = self._get_or_create_mcgsm_reader()
                    if new_reader:
                        self._mcgs_controller.set_reader(new_reader)

        if hasattr(self, "_mcgs_connect_index"):
            self._mcgs_connect_index += 1
            self._connect_next_mcgsm_device()

        if success and self._mcgs_controller and not self._mcgs_controller.is_polling:
            device_ids = [device_id]
            reader = self._mcgs_controller.get_reader()
            if reader:
                config = reader.get_device_config(device_id)
                if config:
                    interval_ms = getattr(config, "polling_interval_ms", 1000)
                    self._mcgs_controller.start_polling(device_ids, interval_ms)
                    logger.info("[MCGS轮询] 连接后自动启动轮询: %s, interval=%dms", device_id, interval_ms)

    @Slot(str, dict)
    def _on_mcgsm_data_updated(self, device_id: str, data: dict):
        """MCGS数据更新回调 — 已迁移至 DataBus 订阅（保留向后兼容）"""
        self._on_bus_device_data_updated(device_id, data)

    @Slot(str, str)
    def _on_mcgsm_device_error(self, device_id: str, error_msg: str):
        """MCGS设备错误回调"""
        logger.warning("[%s] MCGS错误: %s", device_id, error_msg)
        self._status_msg_label.setText(f"MCGS错误 [{device_id}]: {error_msg}")
        self._log_message(f"MCGS错误 [{device_id}]: {error_msg}", "ERROR", device_id, "ERROR")
        # 刷新设备列表以反映可能的断线状态
        self._refresh_device_list(self._search_edit.text())

    @Slot()
    def _on_mcgsm_polling_started(self):
        """轮询启动回调"""
        logger.info("MCGS自动轮询已启动")
        self._log_message("MCGS自动轮询已启动", "INFO")

    @Slot()
    def _on_mcgsm_polling_stopped(self):
        """轮询停止回调"""
        logger.info("MCGS自动轮询已停止")
        self._log_message("MCGS自动轮询已停止", "INFO")

    @Slot(int, int)
    def _on_mcgsm_poll_cycle_completed(self, success_count: int, fail_count: int):
        """轮询周期完成回调"""
        if fail_count > 0:
            self._log_message(f"轮询完成: {success_count}成功, {fail_count}失败", "WARNING")
        # 每个周期刷新设备列表（轻量，仅当列表可见时有效）
        self._refresh_device_list(self._search_edit.text())

    def _create_mcgsm_monitor_panel(self, device_id: str, config, initial_data: Dict[str, str]) -> DynamicMonitorPanel:
        """为MCGS设备创建专用监控面板"""
        from ui.widgets.dynamic_monitor_panel import DynamicMonitorPanel

        # 如果面板已存在，则更新数据
        if device_id in self._monitor_panels:
            panel = self._monitor_panels[device_id]
            panel.update_data(initial_data)
            return panel

        # 创建新面板
        panel = DynamicMonitorPanel(device_id)

        # 从RegisterPointConfig列表构建配置（适配DynamicMonitorPanel接口）
        rp_list = []
        for point in config.points:
            from core.enums.data_type_enum import RegisterDataType, RegisterPointConfig

            type_map = {
                "float": RegisterDataType.HOLDING_FLOAT32,
                "int16": RegisterDataType.HOLDING_INT16,
                "coil": RegisterDataType.COIL,
                "di": RegisterDataType.DISCRETE_INPUT,
            }

            rp = RegisterPointConfig(
                name=point.name,
                data_type=type_map.get(point.type.lower(), RegisterDataType.HOLDING_FLOAT32),
                address=point.addr,
                decimal_places=point.decimal_places,
                unit=point.unit,
                alarm_high=point.alarm_high,
                alarm_low=point.alarm_low,
                writable=False,  # MCGS默认只读
            )
            rp_list.append(rp)

        # 构建面板UI
        panel.build_from_config(rp_list)

        # 填充初始数据
        panel.update_data(initial_data)

        # 连接信号
        panel.coil_write_requested.connect(self._on_coil_write_request)

        # 存储并添加到Tab
        self._monitor_panels[device_id] = panel
        tab_text = f"MCGS-{config.name}"
        self._monitor_tabs.addTab(panel, tab_text)

        logger.info(f"MCGS监控面板已创建: {tab_text} ({len(rp_list)}个数据点)")
        return panel

    @Slot()
    def _on_mcgsm_show_history(self) -> None:
        if not self._mcgs_controller or not self._mcgs_controller.is_history_available():
            QMessageBox.warning(self, "功能不可用", "历史数据存储模块未初始化")
            return

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit
        from PySide6.QtCore import QDate
        from ui.widgets.history_chart_widget import HistoryChartWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("MCGS历史数据查看")
        dialog.resize(1000, 700)

        layout = QVBoxLayout(dialog)

        control_bar = QHBoxLayout()

        control_bar.addWidget(QLabel("设备:"))
        device_combo = QComboBox()
        device_ids = self._mcgs_controller.list_devices() if self._mcgs_controller else []
        for dev_id in device_ids:
            device_combo.addItem(dev_id, dev_id)
        control_bar.addWidget(device_combo)

        control_bar.addWidget(QLabel("参数:"))
        param_combo = QComboBox()
        param_combo.addItems(
            [
                "Hum_in (进气湿度)",
                "RH_in (相对湿度)",
                "AT_in (进气温度)",
                "Flow_in (进气流量)",
                "VPa (大气压)",
                "VPaIn (进气压力)",
            ]
        )
        control_bar.addWidget(param_combo)

        control_bar.addWidget(QLabel("时间范围:"))
        range_combo = QComboBox()
        range_combo.addItems(["最近1小时", "最近6小时", "最近24小时", "最近7天"])
        range_combo.setCurrentIndex(2)
        control_bar.addWidget(range_combo)

        refresh_btn = QPushButton("刷新")
        control_bar.addWidget(refresh_btn)

        export_btn = QPushButton("导出CSV")
        control_bar.addWidget(export_btn)

        control_bar.addStretch()
        layout.addLayout(control_bar)

        chart_widget = HistoryChartWidget("mcgsm_viewer")
        layout.addWidget(chart_widget)

        def load_chart_data():
            dev_id = device_combo.currentData() or device_combo.currentText()
            param_name = param_combo.currentText().split()[0]

            hours_map = {"最近1小时": 1, "最近6小时": 6, "最近24小时": 24, "最近7天": 168}
            hours = hours_map.get(range_combo.currentText(), 24)

            data = self._mcgs_controller.query_history_trend(dev_id, param_name, hours=hours)

            if data:
                chart_widget.clear_series()
                series = chart_widget.add_data_series(param_name)
                for timestamp, value in data:
                    series.append(timestamp.toMSecsSinceEpoch(), value)
                chart_widget.refresh_chart()
            else:
                QMessageBox.information(dialog, "无数据", f"未找到 [{dev_id}].[{param_name}] 的历史数据")

        def on_export():
            from pathlib import Path

            file_path, _ = QFileDialog.getSaveFileName(dialog, "导出CSV", "", "CSV Files (*.csv)")
            if file_path:
                dev_id = device_combo.currentData() or device_combo.currentText()
                param_name = param_combo.currentText().split()[0]
                success = self._mcgs_controller.export_history_csv(file_path, dev_id, [param_name])
                if success:
                    QMessageBox.information(dialog, "导出成功", f"数据已保存至:\n{file_path}")

        refresh_btn.clicked.connect(load_chart_data)
        export_btn.clicked.connect(on_export)
        device_combo.currentIndexChanged.connect(load_chart_data)
        param_combo.currentIndexChanged.connect(load_chart_data)
        range_combo.currentTextChanged.connect(load_chart_data)

        load_chart_data()

        dialog.exec()

    @Slot()
    def _on_mcgsm_health_check(self) -> None:
        if (
            not self._mcgs_controller
            or not self._mcgs_controller.is_anomaly_available()
            or self._mcgs_controller.get_reader() is None
        ):
            QMessageBox.warning(self, "功能不可用", "异常检测模块或MCGS读取器未初始化")
            return

        from PySide6.QtWidgets import QTextBrowser

        dialog = QDialog(self)
        dialog.setWindowTitle("⚠️ MCGS设备健康检测报告")
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        report_browser = QTextBrowser()
        report_browser.setOpenExternalLinks(True)
        layout.addWidget(report_browser)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        report_html = "<h2>📋 MCGS设备健康检测报告</h2>\n"
        report_html += f"<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n"

        device_ids = self._mcgs_controller.list_devices()

        overall_status = "✅ 正常"

        for device_id in device_ids:
            config = self._mcgs_controller.get_device_config(device_id)

            report_html += f"<hr><h3>🔌 设备: {config.name} [{device_id}]</h3>\n"
            report_html += f"<b>地址:</b> {config.ip}:{config.port}<br>\n"
            report_html += f"<b>字节序:</b> {config.byte_order}<br>\n"
            report_html += f"<b>数据点:</b> {len(config.points)} 个<br><br>\n"

            health_report = self._mcgs_controller.get_health_report(device_id)

            status_icon = (
                "🟢"
                if health_report["overall_status"] == "OK"
                else "🟡" if health_report["overall_status"] == "WARNING" else "🔴"
            )

            report_html += f"<h4>{status_icon} 整体状态: {health_report['overall_status']}</h4>\n"
            report_html += f"<b>异常参数数:</b> {health_report['anomaly_count']}<br><br>\n"

            if health_report["anomaly_count"] > 0:
                overall_status = "⚠️ 发现异常"

                report_html += "<table border='1' cellpadding='5' style='border-collapse:collapse'>\n"
                report_html += "<tr bgcolor='#FEE'><th>参数</th><th>当前值</th><th>状态</th><th>详情</th></tr>\n"

                for param_name, info in health_report["parameters"].items():
                    if not info["is_normal"]:
                        report_html += f"<tr style='color:red'>\n"
                        report_html += f"  <td>{param_name}</td>\n"
                        report_html += f"  <td>{info['current_value']:.2f}</td>\n"
                        report_html += f"  <td>⚠️ 异常</td>\n"
                        report_html += f"  <td>{info.get('anomaly_info', '')}</td>\n"
                        report_html += f"</tr>\n"

                report_html += "</table><br>\n"
            else:
                report_html += "<p style='color:green'>✅ 所有参数正常</p><br>\n"

            report_html += "<details open><summary><b>📊 所有参数详情</b></summary>\n"
            report_html += "<table border='1' cellpadding='4' style='border-collapse:collapse;font-size:12px'>\n"
            report_html += "<tr bgcolor='#E8F4FD'><th>参数</th><th>当前值</th><th>格式化</th><th>最后更新</th></tr>\n"

            for param_name, info in health_report["parameters"].items():
                color = "" if info["is_normal"] else ' style="background:#FFF0F0"'
                report_html += f"<tr{color}>\n"
                report_html += f"  <td>{param_name}</td>\n"
                report_html += f"  <td>{info.get('current_value', 'N/A'):.2f}</td>\n"
                report_html += f"  <td>{info.get('formatted', 'N/A')}</td>\n"
                report_html += f"  <td>{info.get('last_update', 'N/A')}</td>\n"
                report_html += f"</tr>\n"

            report_html += "</table></details><br>\n"

        stats = self._mcgs_controller.stats if self._mcgs_controller else {}
        report_html += f"<hr><h3>采集统计</h3>\n"
        report_html += f"<ul>\n"
        report_html += f"  <li><b>总读取次数:</b> {stats.get('total_reads', 0)}</li>\n"
        report_html += f"  <li><b>成功次数:</b> {stats.get('successful_reads', 0)}</li>\n"
        report_html += f"  <li><b>失败次数:</b> {stats.get('failed_reads', 0)}</li>\n"
        report_html += f"  <li><b>最后读取:</b> {stats.get('last_read_time') or '从未'}</li>\n"
        report_html += f"</ul>\n"

        report_html += f"<hr><h3>💡 建议</h3>\n"
        if overall_status == "✅ 正常":
            report_html += "<p>🎉 设备运行正常，继续保持监控。</p>"
        else:
            report_html += "<p>⚠️ 发现异常，建议：</p><ol>\n"
            report_html += "<li>检查物理连接和网络状态</li>\n"
            report_html += "<li>对比MCGS触摸屏显示值确认数据准确性</li>\n"
            report_html += "<li>检查传感器是否需要校准或更换</li>\n"
            report_html += "<li>查看历史趋势图确认是瞬时波动还是持续异常</li>\n"
            report_html += "</ol>\n"

        report_browser.setHtml(report_html)
        dialog.exec()

    @Slot()
    def _on_show_mcgsm_config(self) -> None:
        """
        打开MCGS设备可视化配置编辑器（菜单/工具栏按钮触发）

        功能：
        - 加载当前 devices.json 配置
        - 提供可视化编辑界面（4个Tab）
        - 保存后自动刷新读取器
        """
        self._open_mcgsm_config_dialog()

    def _open_mcgsm_config_dialog(self, focus_device_id: str = None) -> bool:
        """
        打开MCGS配置对话框（内部调用版本）

        Args:
            focus_device_id: 可选，指定要聚焦的设备ID（用于连接失败时的引导）

        Returns:
            bool: 用户是否保存了配置
        """
        from pathlib import Path

        config_path = Path(__file__).parent.parent / "config" / "devices.json"

        # 创建对话框实例
        dialog = MCGSConfigDialog(config_path, parent=self)

        # 如果指定了设备ID，尝试切换到该设备的配置
        if focus_device_id:
            dialog.setFocusDevice(focus_device_id)

        # 以模态方式打开对话框
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            logger.info(f"MCGS配置已通过编辑器更新: {config_path}")

            if self._mcgs_controller:
                self._mcgs_controller.reset_reader()

            self._status_msg_label.setText("✅ MCGS配置已更新，下次连接将使用新配置")

            return True
        else:
            # 用户取消了对话框
            logger.info("MCGS配置编辑器已取消")
            return False

    # ══════════════════════════════════════════════════════════
    # ✅ 新增：操作撤销相关方法
    # ══════════════════════════════════════════════════════════

    def _on_undo_executed(self, req_id: str) -> None:
        """
        撤销操作执行槽函数

        当 OperationUndoManager 发射 undo_executed 信号时调用，
        通过 WriteOperationManager 发起安全恢复写入。

        Args:
            req_id: 原操作的请求ID
        """
        if not hasattr(self, "_undo_mgr"):
            return

        record = self._undo_mgr.get_record_by_req_id(req_id)
        if record is None:
            logger.error("未找到撤销记录: %s", req_id)
            return

        logger.info(
            "执行撤销操作 [参数=%s, 恢复为=%s]",
            record.param_name,
            DeviceController.format_undo_value(record.previous_value),
        )

        device_id = record.device_id
        if device_id != self._current_device_id:
            logger.info("切换到设备 %s 以执行撤销", device_id)

        try:
            device = self._device_manager.get_device(device_id)
            if not device:
                self._undo_mgr.mark_undo_failed(req_id, "设备对象不存在")
                return

            rp = None
            if hasattr(device, "register_points"):
                rp = device.get_register_point_by_name(record.param_name)

            if rp is None:
                self._undo_mgr.mark_undo_failed(req_id, f"未找到参数配置: {record.param_name}")
                return

            restore_value = (
                bool(record.previous_value) if record.operation_type == "coil_write" else record.previous_value
            )

            undo_req_id = self._write_manager.request_write(
                device_id=device_id,
                param_name=record.param_name,
                value=restore_value,
                config=rp,
                skip_confirm=True,
            )
            self._undo_req_map[undo_req_id] = req_id

        except Exception as e:
            error_msg = f"撤销异常: {str(e)}"
            logger.error(error_msg)
            self._undo_mgr.mark_undo_failed(req_id, error_msg)
            self._status_msg_label.setText(error_msg)

    def _on_undo_failed(self, req_id: str, reason: str) -> None:
        """
        撤销失败槽函数

        Args:
            req_id: 请求ID
            reason: 失败原因
        """
        logger.error("撤销操作失败 [req=%s]: %s", req_id, reason)
        self._status_msg_label.setText(f"撤销失败: {reason}")

    def undo_last_operation(self) -> None:
        """
        撤销最后一次操作（公开方法）

        可由工具栏按钮、快捷键Ctrl+Z或右键菜单调用。
        """
        if not hasattr(self, "_undo_mgr") or not self._undo_mgr.can_undo:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(self, "无法撤销", "没有可撤销的操作。")
            return

        # 权限检查
        if not self._permission_mgr.can_write:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "权限不足", "当前用户无权执行撤销操作。")
            return

        # 确认对话框
        from PySide6.QtWidgets import QMessageBox

        history = self._undo_mgr.get_undo_history(limit=1)
        if history:
            last_record = history[0]
            summary = last_record.display_summary

            reply = QMessageBox.question(
                self,
                "确认撤销",
                f"确定要撤销以下操作吗？\n\n"
                f"{summary}\n\n"
                f"这将把 '{last_record.param_name}' 恢复为 "
                f"{DeviceController.format_undo_value(last_record.previous_value)}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._undo_mgr.undo_last_operation()

    def show_undo_history(self) -> None:
        """显示撤销历史面板"""
        if not hasattr(self, "_undo_mgr"):
            return

        history = self._undo_mgr.get_undo_history(limit=10)

        if not history:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(self, "撤销历史", "暂无撤销记录。")
            return

        # 构建历史信息文本
        lines = ["最近10次操作历史：\n"]
        for i, record in enumerate(history, 1):
            status = "可撤销" if record.can_undo and not record.undone_at else "已撤销"
            time_str = record.executed_at.strftime("%H:%M:%S")
            lines.append(f"{i}. [{time_str}] {record.display_summary} ({status})")

        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(self, "撤销历史", "\n".join(lines))

    def closeEvent(self, event) -> None:
        self.cleanup()
        event.accept()

    # ══════════════════════════════════════════════════════════
    # v3.2 新增：写操作管理相关方法
    # ══════════════════════════════════════════════════════════

    def _show_write_confirmation(self, device_id: str, param_name: str, value: object, config: object) -> None:
        """
        显示写操作确认对话框（由 WriteOperationManager.confirm_required 信号触发）

        弹出 QMessageBox 询问用户是否确认写入操作。
        用户响应后调用 on_user_confirmed()。

        Args:
            device_id: 设备ID
            param_name: 参数名称
            value: 目标值
            config: RegisterPointConfig 实例
        """
        # 格式化显示值
        display_value = "ON (闭合)" if value else "OFF (断开)"

        # 构建确认消息
        message = (
            f"确定要执行以下写操作吗？\n\n"
            f"设备: {device_id}\n"
            f"参数: {param_name}\n"
            f"目标值: {display_value}\n\n"
            f"⚠️ 此操作将立即影响设备运行状态！"
        )

        reply = QMessageBox.question(
            self,
            "写操作确认",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        # 调用 WriteOperationManager 的用户确认回调
        if hasattr(self, "_pending_write_req_id") and self._pending_write_req_id:
            self._write_manager.on_user_confirmed(
                self._pending_write_req_id, approved=(reply == QMessageBox.StandardButton.Yes)
            )
            self._pending_write_req_id = None

    def _on_coil_write_request(self, param_name: str, value: bool) -> None:
        """
        处理线圈写请求（由 DynamicMonitorPanel.coil_write_requested 信号触发）

        这是用户点击可写线圈按钮时的入口点。
        通过 WriteOperationManager 发起安全写流程。

        Args:
            param_name: 参数名称
            value: 目标状态
        """
        if not self._current_device_id:
            QMessageBox.warning(self, "操作失败", "请先选择一个设备")
            return

        device = self._device_manager.get_device(self._current_device_id)
        if not device:
            QMessageBox.warning(self, "操作失败", "设备对象不存在")
            return

        # 查找配置
        if hasattr(device, "register_points"):
            rp = device.get_register_point_by_name(param_name)
        else:
            rp = None

        if rp is None:
            logger.warning("未找到参数配置: %s", param_name)
            return

        try:
            # 通过 WriteOperationManager 发起请求
            req_id = self._write_manager.request_write(
                device_id=self._current_device_id,
                param_name=param_name,
                value=value,
                config=rp,
            )

            # 保存当前请求ID（用于回调时使用）
            self._pending_write_req_id = req_id

            logger.info("线圈写请求已提交 [设备=%s, 参数=%s, req=%s]", self._current_device_id, param_name, req_id)

        except Exception as e:
            QMessageBox.critical(self, "操作失败", f"发起写请求失败:\n{str(e)}")
            logger.error("发起写请求失败: %s", str(e), exc_info=True)

    def _on_write_operation_result(self, req_id: str, operation_dict: dict) -> None:
        """
        处理写操作完成通知（由 WriteOperationManager.operation_result 信号触发）

        当用户确认/取消或执行完成后，此方法被调用。
        对于已确认的操作，需要实际调用 DeviceConnection 执行写入。

        Args:
            req_id: 请求ID
            operation_dict: 操作详情字典
        """
        status = operation_dict.get("status")
        device_id = operation_dict.get("device_id", "")
        param_name = operation_dict.get("param_name", "")

        logger.debug("写操作结果 [req=%s, 状态=%s, 设备=%s, 参数=%s]", req_id, status, device_id, param_name)

        # 如果是已确认状态，需要执行实际的写入
        if status == "CONFIRMED":
            self._execute_confirmed_write(req_id, operation_dict)
        elif status == "CANCELLED":
            self._status_msg_label.setText(f"写操作已取消: {param_name}")
        elif status == "EXECUTED":
            success = operation_dict.get("result", False)
            if success:
                self._status_msg_label.setText(f"✓ 写入成功: {param_name}")
            else:
                error = operation_dict.get("error_message", "未知错误")
                self._status_msg_label.setText(f"✗ 写入失败: {param_name} - {error}")
            orig_req_id = self._undo_req_map.pop(req_id, None)
            if orig_req_id and hasattr(self, "_undo_mgr"):
                if success:
                    self._undo_mgr.mark_undo_success(orig_req_id)
                else:
                    self._undo_mgr.mark_undo_failed(orig_req_id, error)
        elif status == "ABORTED":
            error = operation_dict.get("error_message", "未知错误")
            self._status_msg_label.setText(f"✗ 写入中止: {param_name} - {error}")
            orig_req_id = self._undo_req_map.pop(req_id, None)
            if orig_req_id and hasattr(self, "_undo_mgr"):
                self._undo_mgr.mark_undo_failed(orig_req_id, error)

    def _execute_confirmed_write(self, req_id: str, operation_dict: dict) -> None:
        """
        执行已确认的写操作

        从 operation_dict 中提取参数，
        调用 DeviceConnection.confirm_write() 执行实际写入。

        Args:
            req_id: 请求ID
            operation_dict: 操作详情字典
        """
        device_id = operation_dict.get("device_id", "")
        param_name = operation_dict.get("param_name", "")
        value = operation_dict.get("value")

        # 验证当前选中的设备是否匹配
        if device_id != self._current_device_id:
            logger.warning("设备ID不匹配 [期望=%s, 当前=%s]", device_id, self._current_device_id)
            return

        # 获取设备连接对象
        device = self._device_manager.get_device(device_id)
        if not device or not hasattr(device, "confirm_write"):
            logger.error("设备不支持写操作或设备不存在: %s", device_id)
            self._write_manager.mark_executed(req_id, False, "设备不存在或不支持写操作")
            return

        try:
            # 执行实际的写入
            success = device.confirm_write(param_name, bool(value))

            # 标记操作完成
            self._write_manager.mark_executed(req_id, success)

            # 更新状态栏
            if success:
                self._status_msg_label.setText(f"写入成功 [{param_name}={'ON' if value else 'OFF'}]")
                logger.info("线圈写入成功 [设备=%s, 参数=%s, 值=%s]", device_id, param_name, "ON" if value else "OFF")
            else:
                self._status_msg_label.setText(f"写入失败: {param_name}")
                logger.error("线圈写入失败 [设备=%s, 参数=%s]", device_id, param_name)

        except Exception as e:
            error_msg = f"执行写入异常: {str(e)}"
            logger.error("线圈写入异常 [设备=%s, 参数=%s]: %s", device_id, param_name, str(e), exc_info=True)
            self._write_manager.mark_executed(req_id, False, error_msg)

    def _on_add_device_with_monitor(self) -> None:
        """
        添加设备并自动创建动态监控面板（v3.2 增强版）

        在原有添加设备逻辑基础上，
        成功后自动创建 DynamicMonitorPanel 并加入 Tab 页面。
        """
        from ui.device_type_dialogs import DeviceTypeManager

        logger.debug("Opening add device dialog with monitor panel support")
        try:
            device_type_manager = DeviceTypeManager("device_types.json")
            dialog = AddDeviceDialog(device_type_manager, self)
            if dialog.exec():
                config = dialog.get_device_config()
                device_id = self._device_manager.add_device(config)

                if device_id:
                    # ✅ 创建动态监控面板
                    register_points_config = config.get("register_points", [])
                    if register_points_config:
                        from core.enums.data_type_enum import RegisterPointConfig

                        # 转换为 RegisterPointConfig 对象列表
                        rp_list = []
                        for rp_dict in register_points_config:
                            try:
                                rp = RegisterPointConfig.from_dict(rp_dict)
                                rp_list.append(rp)
                            except Exception as e:
                                logger.warning("转换RegisterPointConfig失败: %s", str(e))

                        # 创建面板
                        monitor_panel = DynamicMonitorPanel(device_id, self)
                        monitor_panel.build_from_config(rp_list)

                        # 连接写请求信号
                        monitor_panel.coil_write_requested.connect(self._on_coil_write_request)

                        # 存储到字典
                        self._monitor_panels[device_id] = monitor_panel

                        # 添加到 Tab 页面
                        tab_text = f"{config.get('name', device_id)}_监控"
                        self._monitor_tabs.addTab(monitor_panel, tab_text)

                        logger.info("动态监控面板已创建 [设备=%s, 数据点=%d]", device_id, len(rp_list))

                    logger.info(LogMessages.DEVICE_ADDED.format(device_id=device_id))
                    self._status_msg_label.setText(f"设备添加成功: {device_id}")

        except Exception as e:
            logger.error("添加设备失败: %s", str(e))
            QMessageBox.warning(self, "添加设备失败", f"无法添加设备: {str(e)}")
            self._status_msg_label.setText(f"添加设备失败: {str(e)}")
