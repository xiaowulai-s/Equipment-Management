# -*- coding: utf-8 -*-
"""
主窗口 v2
Main Window V2 - 整合数据层和新的设备管理器
"""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.data import AlarmRepository, DatabaseManager, DeviceRepository
from core.data.models import AlarmModel
from core.device.device_manager_v2 import DeviceManagerV2, DeviceStatus
from core.device.device_model import DeviceStatus as DeviceStatusEnum
from core.device.device_type_manager import DeviceTypeManager
from core.utils.logger_v2 import get_logger
from ui.add_device_dialog import AddDeviceDialog
from ui.batch_operations_dialog import BatchOperationsDialog
from ui.device_type_dialogs import DeviceTypeDialog
from ui.styles import AppStyles
from ui.theme_manager import ThemeManager
from ui.theme_preference import ThemePreferenceManager
from ui.theme_toggle_button import ThemeStatusBarButton

logger = get_logger("main_window")


class MainWindowV2(QMainWindow):
    """主窗口 v2"""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db_manager = db_manager
        self._device_manager = DeviceManagerV2(config_file="config.json", db_manager=db_manager, parent=self)
        self._device_type_manager = DeviceTypeManager("device_types.json")

        self._current_monitor_device_id: Optional[str] = None

        # 主题管理器
        self._theme_manager = ThemeManager(self)

        self._init_ui()
        self._connect_signals()
        self._refresh_device_list()
        self._setup_alarm_rules()

        # 加载主题偏好
        self._load_theme_preference()

        logger.info("主窗口初始化完成")

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("工业设备管理系统 v2.0")
        self.setMinimumSize(1600, 900)
        self.resize(1600, 900)

        self._create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_tool_bar()

        # 主分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板
        left_widget = self._create_left_panel()
        splitter.addWidget(left_widget)

        # 右侧面板
        self._right_stack = QStackedWidget()
        self._right_stack.setStyleSheet(AppStyles.STACKED_WIDGET)
        splitter.addWidget(self._right_stack)

        # 创建页面
        self._welcome_page = self._create_welcome_page()
        self._monitor_page = self._create_monitor_page()

        self._right_stack.addWidget(self._welcome_page)
        self._right_stack.addWidget(self._monitor_page)

        # 设置分割比例
        splitter.setStretchFactor(0, 20)
        splitter.setStretchFactor(1, 80)
        splitter.setSizes([350, 1250])

        # 状态栏
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status_bar()

        # 添加主题切换按钮到状态栏
        self._add_theme_button()

    def _add_theme_button(self):
        """添加主题切换按钮到状态栏"""
        theme_btn = ThemeStatusBarButton()
        theme_btn.theme_changed.connect(self._on_theme_changed)
        self._status_bar.addPermanentWidget(theme_btn)

    def _load_theme_preference(self):
        """加载主题偏好"""
        theme = ThemePreferenceManager.load_theme_preference()
        self._theme_manager.apply_theme(theme)
        logger.info(f"加载主题偏好：{theme}")

    def _on_theme_changed(self, theme: str):
        """主题变化时的处理"""
        logger.info(f"主题已切换到：{theme}")
        # 保存用户偏好
        ThemePreferenceManager.save_theme_preference(theme)

    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        left_widget = QWidget()
        left_widget.setMinimumWidth(300)
        left_widget.setMaximumWidth(450)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("设备列表")
        title_label.setFont(QFont("Inter", 14, QFont.Bold))
        title_label.setStyleSheet("color: #24292F;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self.add_device_btn = QPushButton("+ 添加")
        self.add_device_btn.setStyleSheet(self._get_primary_button_style())
        self.add_device_btn.setFixedHeight(32)
        self.add_device_btn.clicked.connect(self._add_device)
        title_layout.addWidget(self.add_device_btn)

        left_layout.addLayout(title_layout)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索设备...")
        self.search_edit.setStyleSheet(AppStyles.LINE_EDIT)
        self.search_edit.setFixedHeight(32)
        self.search_edit.textChanged.connect(self._filter_devices)
        left_layout.addWidget(self.search_edit)

        # 设备树
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["设备名称", "编号", "状态", "操作"])
        self.device_tree.currentItemChanged.connect(self._on_device_selected)
        self.device_tree.setSortingEnabled(True)

        header = self.device_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.device_tree.setColumnWidth(3, 120)
        header.setDefaultAlignment(Qt.AlignCenter)

        self.device_tree.setStyleSheet(self._get_device_tree_style())
        left_layout.addWidget(self.device_tree, 1)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.remove_btn = QPushButton("删除设备")
        self.remove_btn.setStyleSheet(self._get_danger_button_style())
        self.remove_btn.setFixedHeight(32)
        self.remove_btn.clicked.connect(self._remove_device)

        btn_layout.addStretch()
        btn_layout.addWidget(self.remove_btn)
        left_layout.addLayout(btn_layout)

        return left_widget

    def _create_welcome_page(self) -> QWidget:
        """创建欢迎页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        welcome_label = QLabel("欢迎使用工业设备管理系统 v2.0")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setFont(QFont("Inter", 22, QFont.Bold))
        welcome_label.setStyleSheet("color: #24292F;")
        layout.addWidget(welcome_label)

        sub_label = QLabel("从左侧设备列表选择设备进行监控")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setFont(QFont("Inter", 12))
        sub_label.setStyleSheet("color: #57606A;")
        layout.addWidget(sub_label)

        # 统计信息
        stats_layout = QHBoxLayout()
        stats_layout.addStretch()

        self.stats_connected = QLabel("已连接: 0")
        self.stats_connected.setStyleSheet("color: #1A7F37; font-size: 14px; padding: 10px;")
        stats_layout.addWidget(self.stats_connected)

        self.stats_disconnected = QLabel("已断开: 0")
        self.stats_disconnected.setStyleSheet("color: #CF222E; font-size: 14px; padding: 10px;")
        stats_layout.addWidget(self.stats_disconnected)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        layout.addStretch()
        return page

    def _create_monitor_page(self) -> QWidget:
        """创建监控页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 设备信息栏
        self.device_title_label = QLabel("设备监控")
        self.device_title_label.setFont(QFont("Inter", 18, QFont.Bold))
        self.device_title_label.setStyleSheet("color: #24292F;")
        layout.addWidget(self.device_title_label)

        info_layout = QHBoxLayout()
        self.device_name_label = QLabel("设备名称: -")
        self.device_name_label.setStyleSheet("color: #57606A; font-size: 13px;")

        self.device_status_label = QLabel("状态: 未连接")
        self.device_status_label.setStyleSheet("color: #CF222E; font-size: 13px;")

        self.last_update_label = QLabel("最后更新: -")
        self.last_update_label.setStyleSheet("color: #8B949E; font-size: 12px;")

        info_layout.addWidget(self.device_name_label)
        info_layout.addWidget(self.device_status_label)
        info_layout.addStretch()
        info_layout.addWidget(self.last_update_label)
        layout.addLayout(info_layout)

        # 标签页
        self.monitor_tabs = QTabWidget()
        self.monitor_tabs.setStyleSheet(self._get_tab_style())

        self.data_tab = self._create_data_tab()
        self.register_tab = self._create_register_tab()
        self.log_tab = self._create_log_tab()

        self.monitor_tabs.addTab(self.data_tab, "实时数据")
        self.monitor_tabs.addTab(self.register_tab, "寄存器")
        self.monitor_tabs.addTab(self.log_tab, "通信日志")

        layout.addWidget(self.monitor_tabs)
        return page

    def _create_data_tab(self) -> QWidget:
        """创建数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.data_cards_layout = QGridLayout()
        self.data_cards_layout.setSpacing(16)
        layout.addLayout(self.data_cards_layout)
        layout.addStretch()
        return tab

    def _create_register_tab(self) -> QWidget:
        """创建寄存器标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.register_table = QTableWidget()
        self.register_table.setColumnCount(5)
        self.register_table.setHorizontalHeaderLabels(["地址", "功能码", "变量名", "值", "单位"])
        self.register_table.setStyleSheet(self._get_table_style())
        self.register_table.horizontalHeader().setStretchLastSection(True)
        self.register_table.setAlternatingRowColors(False)
        self.register_table.verticalHeader().setVisible(False)
        layout.addWidget(self.register_table)

        return tab

    def _create_log_tab(self) -> QWidget:
        """创建日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D0D7DE;
                border-radius: 8px;
                color: #24292F;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
            }
        """
        )
        layout.addWidget(self.log_text)

        return tab

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件 (&F)")

        device_type_action = QAction("设备类型管理 (&T)", self)
        device_type_action.triggered.connect(self._show_device_type_dialog)
        file_menu.addAction(device_type_action)

        file_menu.addSeparator()

        export_action = QAction("数据导出 (&E)", self)
        export_action.triggered.connect(self._show_export_dialog)
        file_menu.addAction(export_action)

        batch_action = QAction("批量操作 (&B)", self)
        batch_action.triggered.connect(self._show_batch_operations)
        file_menu.addAction(batch_action)

        file_menu.addSeparator()

        exit_action = QAction("退出 (&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具 (&T)")

        alarm_history_action = QAction("报警历史 (&H)", self)
        alarm_history_action.triggered.connect(self._show_alarm_history)
        tools_menu.addAction(alarm_history_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助 (&H)")

        about_action = QAction("关于 (&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(AppStyles.TOOLBAR)
        self.addToolBar(toolbar)

    def _connect_signals(self):
        """连接信号"""
        self._device_manager.device_added.connect(self._on_device_added)
        self._device_manager.device_removed.connect(self._on_device_removed)
        self._device_manager.device_connected.connect(self._on_device_connected)
        self._device_manager.device_disconnected.connect(self._on_device_disconnected)
        self._device_manager.device_data_updated.connect(self._on_device_data_updated)
        self._device_manager.device_error.connect(self._on_device_error)
        self._device_manager.device_reconnecting.connect(self._on_device_reconnecting)

    def _setup_alarm_rules(self):
        """设置默认报警规则"""
        # 报警规则现在存储在数据库中
        pass

    def _refresh_device_list(self, search_text: str = ""):
        """刷新设备列表"""
        self.device_tree.clear()

        devices = self._device_manager.get_all_devices()

        connected_count = 0
        disconnected_count = 0

        for device_info in devices:
            name = device_info["name"]
            if search_text and search_text.lower() not in name.lower():
                continue

            device_id = device_info["device_id"]
            status = device_info["status"]

            if status == DeviceStatusEnum.CONNECTED:
                connected_count += 1
            else:
                disconnected_count += 1

            item = QTreeWidgetItem()
            item.setText(0, name)
            item.setText(1, device_info["config"].get("device_number", ""))

            if status == DeviceStatusEnum.CONNECTED:
                item.setText(2, "已连接")
                item.setForeground(2, Qt.green)
            elif status == DeviceStatusEnum.DISCONNECTED:
                item.setText(2, "已断开")
                item.setForeground(2, Qt.red)
            elif status == DeviceStatusEnum.ERROR:
                item.setText(2, "错误")
                item.setForeground(2, Qt.yellow)
            elif status == DeviceStatusEnum.CONNECTING:
                item.setText(2, "连接中")
                item.setForeground(2, Qt.blue)

            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            item.setData(0, Qt.UserRole, device_id)
            self.device_tree.addTopLevelItem(item)

            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet(self._get_action_button_style())
            edit_btn.setFixedHeight(24)
            edit_btn.clicked.connect(lambda checked, did=device_id: self._edit_device_by_id(did))

            if status == DeviceStatusEnum.CONNECTED:
                conn_btn = QPushButton("断开")
                conn_btn.setStyleSheet(self._get_danger_action_button_style())
                conn_btn.setFixedHeight(24)
                conn_btn.clicked.connect(lambda checked, did=device_id: self._disconnect_device_by_id(did))
            else:
                conn_btn = QPushButton("连接")
                conn_btn.setStyleSheet(self._get_primary_action_button_style())
                conn_btn.setFixedHeight(24)
                conn_btn.clicked.connect(lambda checked, did=device_id: self._connect_device_by_id(did))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(conn_btn)
            self.device_tree.setItemWidget(item, 3, action_widget)

        # 更新统计
        self.stats_connected.setText(f"已连接: {connected_count}")
        self.stats_disconnected.setText(f"已断开: {disconnected_count}")

    def _filter_devices(self):
        """过滤设备"""
        search_text = self.search_edit.text()
        self._refresh_device_list(search_text)

    def _add_device(self):
        """添加设备"""
        dialog = AddDeviceDialog(self._device_type_manager, self)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.get_device_config()
            try:
                self._device_manager.add_device(config)
                logger.info(f"添加设备: {config.get('name')}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"添加设备失败: {str(e)}")

    def _remove_device(self):
        """移除设备"""
        item = self.device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.UserRole)

        reply = QMessageBox.question(
            self, "确认删除", "确定要删除该设备吗？\n此操作不可恢复！", QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self._device_manager.remove_device(device_id):
                logger.info(f"删除设备: {device_id}")

    def _connect_device_by_id(self, device_id: str):
        """连接设备"""
        if not self._device_manager.connect_device(device_id):
            QMessageBox.warning(self, "错误", "连接失败，请检查设备配置")

    def _disconnect_device_by_id(self, device_id: str):
        """断开设备"""
        self._device_manager.disconnect_device(device_id)

    def _edit_device_by_id(self, device_id: str):
        """编辑设备"""
        device = self._device_manager.get_device(device_id)
        if not device:
            return

        config = device.get_device_config()
        dialog = AddDeviceDialog(self._device_type_manager, self, edit_mode=True, device_config=config)
        if dialog.exec() == QDialog.Accepted:
            new_config = dialog.get_device_config()
            if self._device_manager.edit_device(device_id, new_config):
                logger.info(f"编辑设备: {device_id}")

    def _update_monitor_page(self, device_id: str):
        """更新监控页面"""
        device = self._device_manager.get_device(device_id)
        if not device:
            return

        config = device.get_device_config()
        status = device.get_status()

        self.device_title_label.setText(f"设备监控 - {config.get('name', '未知设备')}")
        self.device_name_label.setText(f"设备名称: {config.get('name', '-')}")

        if status == DeviceStatusEnum.CONNECTED:
            self.device_status_label.setText("状态: 已连接")
            self.device_status_label.setStyleSheet("color: #1A7F37; font-size: 13px;")
        elif status == DeviceStatusEnum.DISCONNECTED:
            self.device_status_label.setText("状态: 已断开")
            self.device_status_label.setStyleSheet("color: #CF222E; font-size: 13px;")
        elif status == DeviceStatusEnum.CONNECTING:
            self.device_status_label.setText("状态: 连接中...")
            self.device_status_label.setStyleSheet("color: #0969DA; font-size: 13px;")

        self.last_update_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")

        self._update_data_cards(device.get_current_data())
        self._update_register_table(config.get("register_map", []))

    def _update_data_cards(self, data: dict):
        """更新数据卡片"""
        # 清除旧卡片
        while self.data_cards_layout.count():
            item = self.data_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row, col = 0, 0
        max_cols = 3

        for name, info in data.items():
            card = self._create_data_card(name, info)
            self.data_cards_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _create_data_card(self, name: str, info: dict) -> QWidget:
        """创建数据卡片"""
        card = QWidget()
        card.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(135deg, #FFFFFF, #F6F8FA);
                border: 1px solid #D0D7DE;
                border-radius: 12px;
                padding: 8px;
            }
            QWidget:hover {
                border-color: #0969DA;
            }
        """
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        name_label = QLabel(name)
        name_label.setStyleSheet("color: #57606A; font-size: 11px; font-weight: 600;")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        value = info.get("value", 0)
        if isinstance(value, (int, float)):
            value_str = f"{value:.2f}"
        else:
            value_str = str(value)

        value_label = QLabel(value_str)
        value_label.setStyleSheet(
            """
            color: #24292F;
            font-size: 24px;
            font-weight: 700;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
        """
        )
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

        unit = info.get("unit", "")
        if unit:
            unit_label = QLabel(unit)
            unit_label.setStyleSheet("color: #8B949E; font-size: 11px;")
            unit_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(unit_label)

        return card

    def _update_register_table(self, registers: list):
        """更新寄存器表格"""
        self.register_table.setRowCount(len(registers))

        for row, reg in enumerate(registers):
            self.register_table.setItem(row, 0, QTableWidgetItem(str(reg.get("address", ""))))
            self.register_table.setItem(row, 1, QTableWidgetItem(str(reg.get("function_code", ""))))
            self.register_table.setItem(row, 2, QTableWidgetItem(reg.get("name", "")))
            self.register_table.setItem(row, 3, QTableWidgetItem(str(reg.get("value", ""))))
            self.register_table.setItem(row, 4, QTableWidgetItem(reg.get("unit", "")))

            for col in range(5):
                item = self.register_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.register_table.resizeColumnsToContents()

    def _show_device_type_dialog(self):
        """显示设备类型对话框"""
        dialog = DeviceTypeDialog(self._device_type_manager, self)
        dialog.exec()

    def _show_export_dialog(self):
        """显示导出对话框"""
        QMessageBox.information(self, "数据导出", "数据导出功能开发中...")

    def _show_batch_operations(self):
        """显示批量操作对话框"""
        dialog = BatchOperationsDialog(self._device_manager, self)
        dialog.exec()

    def _show_alarm_history(self):
        """显示报警历史"""
        try:
            with self._db_manager.session() as session:
                repo = AlarmRepository(session)
                alarms = repo.get_unacknowledged(limit=50)

                if not alarms:
                    QMessageBox.information(self, "报警历史", "暂无未确认报警")
                    return

                alarm_text = "未确认报警 (最近 50 条):\n\n"
                for alarm in alarms:
                    alarm_dict = alarm.to_dict()
                    alarm_text += (
                        f"{alarm_dict['timestamp']} | {alarm_dict['device_name']} | "
                        f"{alarm_dict['parameter']} | {alarm_dict['level_name']}\n"
                    )

                QMessageBox.information(self, "报警历史", alarm_text)

        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取报警历史失败: {str(e)}")

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            "工业设备管理系统 v2.0\n\n"
            "改进特性:\n"
            "• SQLAlchemy 数据持久化\n"
            "• 结构化日志系统\n"
            "• 指数退避重连机制\n"
            "• 自适应轮询间隔\n"
            "• Pydantic 配置验证\n\n"
            "© 2026 Industrial Equipment Co.",
        )

    def _on_device_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """设备选择事件"""
        if not current:
            self._right_stack.setCurrentIndex(0)
            return

        device_id = current.data(0, Qt.UserRole)
        self._current_monitor_device_id = device_id
        self._update_monitor_page(device_id)
        self._right_stack.setCurrentIndex(1)

    @Slot(str)
    def _on_device_added(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()

    @Slot(str)
    def _on_device_removed(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()
        self._right_stack.setCurrentIndex(0)

    @Slot(str)
    def _on_device_connected(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()
        if self._current_monitor_device_id == device_id:
            self._update_monitor_page(device_id)

    @Slot(str)
    def _on_device_disconnected(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()
        if self._current_monitor_device_id == device_id:
            self._update_monitor_page(device_id)

    @Slot(str, dict)
    def _on_device_data_updated(self, device_id: str, data: dict):
        if self._current_monitor_device_id == device_id:
            self._update_data_cards(data)
            self.last_update_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")

    @Slot(str, str)
    def _on_device_error(self, device_id: str, error: str):
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 错误 [{device_id}]: {error}")

    @Slot(str, int)
    def _on_device_reconnecting(self, device_id: str, attempt: int):
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 设备 {device_id} 正在重连 (第 {attempt} 次)")

    def _update_status_bar(self):
        """更新状态栏"""
        devices = self._device_manager.get_all_devices()
        online_count = sum(1 for d in devices if d["status"] == DeviceStatusEnum.CONNECTED)
        total_count = len(devices)
        self._status_bar.showMessage(f"就绪 | {online_count}/{total_count} 个设备在线")

    def cleanup(self):
        """清理资源"""
        logger.info("主窗口清理资源")
        self._device_manager.cleanup()

    # ========== 样式方法 ==========

    def _get_primary_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #0969DA;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #0550AE; }
            QPushButton:pressed { background-color: #043E8C; }
        """

    def _get_danger_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #CF222E;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #A40E26; }
            QPushButton:pressed { background-color: #8B0820; }
        """

    def _get_primary_action_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #0969DA;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #0550AE; }
        """

    def _get_danger_action_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #CF222E;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #A40E26; }
        """

    def _get_action_button_style(self) -> str:
        return """
            QPushButton {
                background-color: #FFFFFF;
                color: #24292F;
                border: 1px solid #D0D7DE;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #F6F8FA; border-color: #0969DA; }
        """

    def _get_device_tree_style(self) -> str:
        return """
            QTreeWidget {
                background-color: #FFFFFF;
                border: 1px solid #D0D7DE;
                border-radius: 8px;
            }
            QTreeWidget::item { padding: 8px; border: none; }
            QTreeWidget::item:hover { background-color: #F6F8FA; }
            QTreeWidget::item:selected { background-color: #0969DA; color: white; }
            QHeaderView::section {
                background-color: #F6F8FA;
                color: #57606A;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #D0D7DE;
                font-weight: 600;
            }
        """

    def _get_table_style(self) -> str:
        return """
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #D0D7DE;
                border-radius: 8px;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:hover { background-color: #F6F8FA; }
            QHeaderView::section {
                background-color: #F6F8FA;
                color: #57606A;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #D0D7DE;
                font-weight: 600;
            }
        """

    def _get_tab_style(self) -> str:
        return """
            QTabWidget::pane {
                border: 1px solid #D0D7DE;
                border-radius: 8px;
                padding: 12px;
                background-color: #FFFFFF;
            }
            QTabBar::tab {
                background-color: #F6F8FA;
                color: #57606A;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #0969DA;
                border-bottom: 2px solid #0969DA;
            }
        """

    def closeEvent(self, event):
        """关闭事件"""
        self.cleanup()
        event.accept()
