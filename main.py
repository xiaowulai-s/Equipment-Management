# -*- coding: utf-8 -*-
"""
工业设备管理系统
Industrial Equipment Management System
基于四层解耦架构
Based on 4-layer decoupled architecture
"""

import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
                               QPushButton, QLabel, QStackedWidget, QMessageBox,
                               QHeaderView, QMenuBar, QMenu, QLineEdit, QToolBar,
                               QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
                               QGridLayout, QFileDialog, QDialog, QSizePolicy)
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QIcon, QFont, QAction, QPainter, QPixmap

from core.device.device_manager import DeviceManager
from core.device.device_model import DeviceStatus
from core.device.device_type_manager import DeviceTypeManager
from core.utils.logger import get_logger
from core.utils.alarm_manager import AlarmManager, AlarmRule, AlarmType, AlarmLevel
from core.utils.data_exporter import DataExporter
from ui.styles import AppStyles
from ui.device_type_dialogs import DeviceTypeDialog
from ui.add_device_dialog import AddDeviceDialog
from ui.batch_operations_dialog import BatchOperationsDialog
from ui.alarm_config_dialog import AlarmRuleConfigDialog


logger = get_logger("main")


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._device_manager = DeviceManager("config.json")
        self._device_type_manager = DeviceTypeManager("device_types.json")
        self._alarm_manager = AlarmManager()
        self._sort_order = Qt.AscendingOrder
        self._sort_column = 0
        self._init_ui()
        self._connect_signals()
        self._refresh_device_list()
        self._apply_stylesheet()
        self._setup_alarm_rules()
        logger.info("应用程序启动")

    def _init_ui(self):
        self.setWindowTitle("工业设备管理系统 v1.1")
        self.setMinimumSize(1600, 900)

        self._create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_tool_bar()

        # 主分割器：左侧设备列表 + 右侧内容区
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # === 左侧面板：设备列表 ===
        left_widget = QWidget()
        left_widget.setMinimumWidth(400)
        left_widget.setMaximumWidth(600)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        left_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("设备列表")
        title_label.setFont(QFont("Inter", 16, QFont.Bold))
        title_label.setStyleSheet("color: #24292F;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self.add_device_btn = QPushButton("+ 添加设备")
        self.add_device_btn.setStyleSheet(self._get_primary_button_style())
        self.add_device_btn.setFixedHeight(36)
        self.add_device_btn.clicked.connect(self._add_device)
        title_layout.addWidget(self.add_device_btn)

        left_layout.addLayout(title_layout)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索设备名称...")
        self.search_edit.setStyleSheet(AppStyles.LINE_EDIT)
        self.search_edit.setFixedHeight(36)
        self.search_edit.textChanged.connect(self._filter_devices)
        left_layout.addWidget(self.search_edit)

        # 设备树
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["设备名称", "设备编号", "设备状态", "操作"])
        self.device_tree.currentItemChanged.connect(self._on_device_selected)
        self.device_tree.setSortingEnabled(True)
        self.device_tree.sortByColumn(0, self._sort_order)
        # 设置列宽比例
        header = self.device_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 设备名称：自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 设备编号：根据内容
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 设备状态：根据内容
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # 操作：固定宽度
        self.device_tree.setColumnWidth(3, 140)  # 操作列固定 140px（容纳两个文字按钮）
        header.setDefaultAlignment(Qt.AlignCenter)
        self.device_tree.setStyleSheet(self._get_device_tree_style())
        self.device_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.device_tree, 1)  # stretch=1

        # 底部按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.remove_btn = QPushButton("删除设备")
        self.remove_btn.setStyleSheet(self._get_danger_button_style())
        self.remove_btn.setFixedHeight(36)
        self.remove_btn.clicked.connect(self._remove_device)

        btn_layout.addStretch()
        btn_layout.addWidget(self.remove_btn)
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_widget)

        # === 右侧面板：内容区 ===
        self.stack_widget = QStackedWidget()
        self.stack_widget.setStyleSheet(AppStyles.STACKED_WIDGET)
        self.stack_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 欢迎页面
        welcome_page = QWidget()
        welcome_layout = QVBoxLayout(welcome_page)
        welcome_layout.setContentsMargins(40, 40, 40, 40)
        welcome_layout.setSpacing(20)

        welcome_label = QLabel("欢迎使用工业设备管理系统")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setFont(QFont("Inter", 24, QFont.Bold))
        welcome_label.setStyleSheet("color: #24292F;")
        welcome_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        welcome_layout.addWidget(welcome_label)

        welcome_sub_label = QLabel("请从左侧设备列表选择设备进行监控")
        welcome_sub_label.setAlignment(Qt.AlignCenter)
        welcome_sub_label.setFont(QFont("Inter", 14))
        welcome_sub_label.setStyleSheet("color: #57606A;")
        welcome_sub_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        welcome_layout.addWidget(welcome_sub_label)
        welcome_layout.addStretch()
        self.stack_widget.addWidget(welcome_page)

        # 监控页面
        monitor_page = self._create_monitor_page()
        self.stack_widget.addWidget(monitor_page)

        splitter.addWidget(self.stack_widget)

        # 设置初始分割比例：左侧 20%，右侧 80%
        splitter.setStretchFactor(0, 20)
        splitter.setStretchFactor(1, 80)
        splitter.setSizes([400, 1200])
        splitter.setStyleSheet(AppStyles.SPLITTER)

        self.statusBar().showMessage("就绪 | 0 个设备在线")
        self.statusBar().setStyleSheet(AppStyles.STATUSBAR)

    def _create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件 (&F)")

        device_type_action = QAction("设备类型管理 (&T)", self)
        device_type_action.triggered.connect(self._show_device_type_dialog)
        file_menu.addAction(device_type_action)

        file_menu.addSeparator()

        alarm_config_action = QAction("报警规则配置 (&C)", self)
        alarm_config_action.triggered.connect(self._show_alarm_config_dialog)
        file_menu.addAction(alarm_config_action)

        alarm_action = QAction("报警设置 (&A)", self)
        alarm_action.triggered.connect(self._show_alarm_dialog)
        file_menu.addAction(alarm_action)

        export_action = QAction("数据导出 (&E)", self)
        export_action.triggered.connect(self._show_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        batch_action = QAction("批量操作 (&B)", self)
        batch_action.triggered.connect(self._show_batch_operations)
        file_menu.addAction(batch_action)

        file_menu.addSeparator()

        exit_action = QAction("退出 (&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu("工具 (&T)")

        alarm_history_action = QAction("报警历史 (&H)", self)
        alarm_history_action.triggered.connect(self._show_alarm_history)
        tools_menu.addAction(alarm_history_action)

        help_menu = menubar.addMenu("帮助 (&H)")

        about_action = QAction("关于 (&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_tool_bar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(AppStyles.TOOLBAR)
        self.addToolBar(toolbar)

    def _apply_stylesheet(self):
        self.setStyleSheet(AppStyles.MAIN_WINDOW)

    def _connect_signals(self):
        self._device_manager.device_added.connect(self._on_device_added)
        self._device_manager.device_removed.connect(self._on_device_removed)
        self._device_manager.device_connected.connect(self._on_device_connected)
        self._device_manager.device_disconnected.connect(self._on_device_disconnected)
        self._device_manager.device_data_updated.connect(self._on_device_data_updated)

        self._alarm_manager.alarm_triggered.connect(self._on_alarm_triggered)

    def _setup_alarm_rules(self):
        """设置默认报警规则"""
        default_rules = [
            AlarmRule(
                rule_id="TEMP_HIGH",
                device_id="*",
                parameter="温度",
                alarm_type=AlarmType.THRESHOLD_HIGH,
                threshold_high=80.0,
                level=AlarmLevel.WARNING,
                description="温度过高报警"
            ),
            AlarmRule(
                rule_id="PRESSURE_HIGH",
                device_id="*",
                parameter="压力",
                alarm_type=AlarmType.THRESHOLD_HIGH,
                threshold_high=2.0,
                level=AlarmLevel.WARNING,
                description="压力过高报警"
            ),
        ]

        for rule in default_rules:
            self._alarm_manager.add_rule(rule)

    def _on_device_data_updated(self, device_id: str, data: dict):
        """设备数据更新时检查报警"""
        for param_name, param_info in data.items():
            if isinstance(param_info, dict) and "value" in param_info:
                self._alarm_manager.check_value(device_id, param_name, param_info["value"])

    def _on_alarm_triggered(self, alarm):
        """报警触发处理"""
        alarm_dict = alarm.to_dict()
        self.log_text.append(
            f"[{alarm_dict['timestamp']}] ⚠️ 报警：{alarm_dict['device_id']} - "
            f"{alarm_dict['parameter']} ({alarm_dict['level_name']}): "
            f"{alarm_dict['value']} {alarm_dict.get('threshold_high', '')}"
        )

        QMessageBox.warning(
            self,
            "报警提示",
            f"设备：{alarm_dict['device_id']}\n"
            f"参数：{alarm_dict['parameter']}\n"
            f"级别：{alarm_dict['level_name']}\n"
            f"值：{alarm_dict['value']}\n"
            f"描述：{alarm_dict['description']}"
        )
        self._device_type_manager.device_types_changed.connect(self._refresh_device_list)

    def _refresh_device_list(self, search_text: str = ""):
        self.device_tree.clear()

        for device_info in self._device_manager.get_all_devices():
            name = device_info["name"]
            if search_text and search_text.lower() not in name.lower():
                continue

            device_id = device_info["device_id"]
            item = QTreeWidgetItem()
            item.setText(0, name)
            item.setText(1, device_info["config"].get("device_number", ""))

            status = device_info["status"]
            if status == DeviceStatus.CONNECTED:
                item.setText(2, "已连接")
                item.setForeground(2, Qt.green)
            elif status == DeviceStatus.DISCONNECTED:
                item.setText(2, "已断开")
                item.setForeground(2, Qt.red)
            elif status == DeviceStatus.ERROR:
                item.setText(2, "错误")
                item.setForeground(2, Qt.yellow)
            elif status == DeviceStatus.CONNECTING:
                item.setText(2, "连接中")
                item.setForeground(2, Qt.blue)

            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            item.setData(0, Qt.UserRole, device_id)
            self.device_tree.addTopLevelItem(item)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(4)

            # 编辑按钮（文字）
            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet(self._get_action_button_style())
            edit_btn.setFixedHeight(28)
            edit_btn.setToolTip("编辑设备")
            edit_btn.clicked.connect(lambda checked, did=device_id: self._edit_device_by_id(did))

            # 连接/断开按钮（文字）
            if status == DeviceStatus.CONNECTED:
                conn_btn = QPushButton("断开")
                conn_btn.setStyleSheet(self._get_danger_action_button_style())
                conn_btn.setFixedHeight(28)
                conn_btn.setToolTip("断开连接")
                conn_btn.clicked.connect(lambda checked, did=device_id: self._disconnect_device_by_id(did))
            else:
                conn_btn = QPushButton("连接")
                conn_btn.setStyleSheet(self._get_primary_action_button_style())
                conn_btn.setFixedHeight(28)
                conn_btn.setToolTip("连接设备")
                conn_btn.clicked.connect(lambda checked, did=device_id: self._connect_device_by_id(did))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(conn_btn)

            self.device_tree.setItemWidget(item, 3, action_widget)

    def _filter_devices(self):
        search_text = self.search_edit.text()
        self._refresh_device_list(search_text)

    def _on_header_clicked(self, logical_index):
        if self._sort_column == logical_index:
            self._sort_order = Qt.DescendingOrder if self._sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self._sort_column = logical_index
            self._sort_order = Qt.AscendingOrder

        self.device_tree.sortByColumn(self._sort_column, self._sort_order)

    def _add_device(self):
        logger.debug("打开添加设备对话框")
        dialog = AddDeviceDialog(self._device_type_manager, self)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.get_device_config()
            self._device_manager.add_device(config)
            logger.info(f"添加设备: {config.get('name', '未命名')}")

    def _remove_device(self):
        item = self.device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.UserRole)
        self._remove_device_by_id(device_id)

    def _remove_device_by_id(self, device_id: str):
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该设备吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._device_manager.remove_device(device_id)
            logger.info(f"删除设备: {device_id}")

    def _connect_device(self):
        item = self.device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.UserRole)
        self._connect_device_by_id(device_id)

    def _connect_device_by_id(self, device_id: str):
        if self._device_manager.connect_device(device_id):
            self.statusBar().showMessage("正在连接...")
            logger.info(f"正在连接设备: {device_id}")
        else:
            QMessageBox.warning(self, "错误", "连接失败")
            logger.error(f"连接设备失败: {device_id}")

    def _disconnect_device(self):
        item = self.device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.UserRole)
        self._disconnect_device_by_id(device_id)

    def _disconnect_device_by_id(self, device_id: str):
        self._device_manager.disconnect_device(device_id)
        logger.info(f"断开设备: {device_id}")

    def _edit_device(self):
        item = self.device_tree.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要编辑的设备")
            return

        device_id = item.data(0, Qt.UserRole)
        self._edit_device_by_id(device_id)

    def _edit_device_by_id(self, device_id: str):
        device = self._device_manager.get_device(device_id)
        if not device:
            return

        config = device.get_device_config()
        dialog = AddDeviceDialog(self._device_type_manager, self, edit_mode=True, device_config=config)
        if dialog.exec() == QDialog.Accepted:
            new_config = dialog.get_device_config()
            self._device_manager.edit_device(device_id, new_config)
            logger.info(f"编辑设备: {device_id}")

    def _create_monitor_page(self) -> QWidget:
        """创建设备监控页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.device_title_label = QLabel("设备监控")
        self.device_title_label.setFont(QFont("Inter", 20, QFont.Bold))
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

        self.monitor_tabs = QTabWidget()
        self.monitor_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #D0D7DE;
                border-radius: 8px;
                padding: 12px;
                background-color: #FFFFFF;
            }
            QTabBar::tab {
                background-color: #F6F8FA;
                color: #57606A;
                padding: 10px 20px;
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
            QTabBar::tab:hover:!selected {
                background-color: #EAEFF2;
            }
        """)

        self.data_tab = self._create_data_tab()
        self.register_tab = self._create_register_tab()
        self.log_tab = self._create_log_tab()

        self.monitor_tabs.addTab(self.data_tab, "实时数据")
        self.monitor_tabs.addTab(self.register_tab, "寄存器")
        self.monitor_tabs.addTab(self.log_tab, "通信日志")

        layout.addWidget(self.monitor_tabs)

        return page

    def _create_data_tab(self) -> QWidget:
        """创建数据监控标签页"""
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
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D0D7DE;
                border-radius: 8px;
                color: #24292F;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)

        return tab

    def _update_monitor_page(self, device_id: str):
        """更新监控页面"""
        device = self._device_manager.get_device(device_id)
        if not device:
            return

        config = device.get_device_config()
        status = device.get_status()

        self.device_title_label.setText(f"设备监控 - {config.get('name', '未知设备')}")
        self.device_name_label.setText(f"设备名称: {config.get('name', '-')}")

        if status == DeviceStatus.CONNECTED:
            self.device_status_label.setText("状态: 已连接")
            self.device_status_label.setStyleSheet("color: #1A7F37; font-size: 13px;")
        elif status == DeviceStatus.DISCONNECTED:
            self.device_status_label.setText("状态: 已断开")
            self.device_status_label.setStyleSheet("color: #CF222E; font-size: 13px;")
        elif status == DeviceStatus.CONNECTING:
            self.device_status_label.setText("状态: 连接中...")
            self.device_status_label.setStyleSheet("color: #0969DA; font-size: 13px;")

        from datetime import datetime
        self.last_update_label.setText(f"最后更新：{datetime.now().strftime('%H:%M:%S')}")

        self._update_data_cards(device.get_current_data())
        self._update_register_table(device.get_device_config().get("register_map", []))

        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 设备 {config.get('name')} 已选中")

    def _update_data_cards(self, data: dict):
        """更新数据卡片"""
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
        """创建单个数据卡片"""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: qlineargradient(135deg, #FFFFFF, #F6F8FA);
                border: 1px solid #D0D7DE;
                border-radius: 12px;
            }
            QWidget:hover {
                border-color: #0969DA;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        name_label = QLabel(name)
        name_label.setStyleSheet("""
            color: #57606A;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        """)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        value = info.get("value", 0)
        unit = info.get("unit", "")

        value_label = QLabel(f"{value:.2f}")
        value_label.setStyleSheet("""
            color: #24292F;
            font-size: 28px;
            font-weight: 700;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            line-height: 1;
        """)
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color: #8B949E; font-size: 12px;")
        unit_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(unit_label)

        return card

    def _update_register_table(self, registers: list):
        """更新寄存器表格"""
        self.register_table.setRowCount(len(registers))

        for row, reg in enumerate(registers):
            self.register_table.setItem(row, 0, QTableWidgetItem(reg.get("address", "")))
            self.register_table.setItem(row, 1, QTableWidgetItem(reg.get("function_code", "")))
            self.register_table.setItem(row, 2, QTableWidgetItem(reg.get("name", "")))
            self.register_table.setItem(row, 3, QTableWidgetItem(str(reg.get("value", ""))))
            self.register_table.setItem(row, 4, QTableWidgetItem(reg.get("unit", "")))

            for col in range(5):
                item = self.register_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.register_table.resizeColumnsToContents()

    def _show_device_type_dialog(self):
        logger.debug("打开设备类型管理对话框")
        dialog = DeviceTypeDialog(self._device_type_manager, self)
        dialog.exec()

    def _show_alarm_config_dialog(self):
        """显示报警规则配置对话框"""
        dialog = AlarmRuleConfigDialog(self._alarm_manager, self)
        dialog.rules_updated.connect(self._on_alarm_rules_updated)
        dialog.exec()

    def _on_alarm_rules_updated(self):
        """报警规则更新处理"""
        self.statusBar().showMessage("报警规则已更新", 3000)
        logger.info("报警规则已更新")

    def _show_alarm_dialog(self):
        """显示报警设置对话框"""
        QMessageBox.information(self, "报警设置", "报警设置功能开发中...\n\n当前已启用默认报警规则：\n- 温度过高 (>80°C)\n- 压力过高 (>2.0MPa)\n\n请使用'报警规则配置'功能进行详细配置。")

    def _show_export_dialog(self):
        """显示数据导出对话框"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出数据",
            "",
            "CSV 文件 (*.csv);;Excel 文件 (*.xlsx);;JSON 文件 (*.json)"
        )

        if file_path:
            devices = self._device_manager.get_all_devices()
            export_data = []

            for device in devices:
                config = device.get_device_config()
                data = device.get_current_data()

                row = {
                    "设备 ID": device.get_device_id(),
                    "设备名称": config.get("name", ""),
                    "设备类型": config.get("type", ""),
                    "状态": "已连接" if device.get_status() == DeviceStatus.CONNECTED else "已断开",
                    "IP 地址": config.get("ip_address", ""),
                    "端口": config.get("port", ""),
                }

                for param_name, param_info in data.items():
                    if isinstance(param_info, dict):
                        row[f"{param_name}({param_info.get('unit', '')})"] = param_info.get("value", "")

                row["导出时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                QMessageBox.information(self, "导出成功", f"数据已成功导出到:\n{file_path}")
            else:
                QMessageBox.warning(self, "导出失败", "数据导出失败，请检查文件格式或权限。")

    def _show_alarm_history(self):
        """显示报警历史"""
        alarms = self._alarm_manager.get_alarm_history(100)

        if not alarms:
            QMessageBox.information(self, "报警历史", "暂无报警记录")
            return

        alarm_text = "报警历史 (最近 100 条):\n\n"
        for alarm in alarms[-20:]:
            alarm_dict = alarm.to_dict()
            alarm_text += (
                f"{alarm_dict['timestamp']} | {alarm_dict['device_id']} | "
                f"{alarm_dict['parameter']} | {alarm_dict['level_name']} | "
                f"值:{alarm_dict['value']}\n"
            )

        QMessageBox.information(self, "报警历史", alarm_text)

    def _show_batch_operations(self):
        """显示批量操作对话框"""
        dialog = BatchOperationsDialog(self._device_manager, self)
        dialog.operations_completed.connect(self._on_batch_operations_completed)
        dialog.exec()

    def _on_batch_operations_completed(self, success_count: int, total_count: int):
        """批量操作完成处理"""
        self._refresh_device_list()
        self._update_status_bar()
        logger.info(f"批量操作完成：成功{success_count}/{total_count}")

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            "工业设备管理系统 v1.1\n\n"
            "基于 PySide6 Widgets 构建\n"
            "采用四层解耦架构\n\n"
            "功能特性:\n"
            "• 设备管理 (增删改查)\n"
            "• 实时监控\n"
            "• 报警系统\n"
            "• 数据导出\n"
            "• 设备类型管理\n"
            "• 批量操作\n"
            "• 寄存器配置\n\n"
            "© 2026 Industrial Equipment Co."
        )

    def _on_device_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if not current:
            self.stack_widget.setCurrentIndex(0)
            return

        device_id = current.data(0, Qt.UserRole)
        self._current_monitor_device_id = device_id
        self._update_monitor_page(device_id)
        self.stack_widget.setCurrentIndex(1)

    @Slot(str)
    def _on_device_added(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()
        self.statusBar().showMessage(f"设备已添加: {device_id}")

    @Slot(str)
    def _on_device_removed(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()
        self.stack_widget.setCurrentIndex(0)
        self.statusBar().showMessage(f"设备已删除: {device_id}")

    @Slot(str)
    def _on_device_connected(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()
        self.statusBar().showMessage(f"设备已连接: {device_id}")
        logger.info(f"设备已连接: {device_id}")
        if hasattr(self, '_current_monitor_device_id') and device_id == self._current_monitor_device_id:
            self._update_monitor_page(device_id)

    @Slot(str)
    def _on_device_disconnected(self, device_id: str):
        self._refresh_device_list(self.search_edit.text())
        self._update_status_bar()
        self.statusBar().showMessage(f"设备已断开: {device_id}")
        logger.info(f"设备已断开: {device_id}")
        if hasattr(self, '_current_monitor_device_id') and device_id == self._current_monitor_device_id:
            self._update_monitor_page(device_id)

    def _update_status_bar(self):
        """更新状态栏设备统计"""
        all_devices = self._device_manager.get_all_devices()
        online_count = sum(1 for d in all_devices if d["status"] == DeviceStatus.CONNECTED)
        total_count = len(all_devices)
        self.statusBar().showMessage(f"就绪 | {online_count}/{total_count} 个设备在线")

    def closeEvent(self, event):
        logger.info("应用程序关闭")
        event.accept()

    def _create_icon(self, icon_type: str) -> QIcon:
        """创建图标"""
        from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QBrush, QPolygon
        from PySide6.QtCore import QPoint
        
        # 使用更大的 pixmap 确保图标完整
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        if icon_type == "edit":
            # 铅笔图标
            painter.setPen(QPen(QColor("#57606A"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(QBrush(QColor("#57606A")))
            # 铅笔主体
            points = [QPoint(8, 20), QPoint(12, 20), QPoint(24, 8), QPoint(20, 4)]
            polygon = QPolygon(points)
            painter.drawPolygon(polygon)
            # 铅笔尾部
            painter.drawLine(8, 20, 8, 24)
            painter.drawLine(12, 20, 12, 24)
        elif icon_type == "connect":
            # 连接图标（链条）
            pen = QPen(QColor("#0969DA"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            # 左链环
            painter.drawRoundedRect(5, 10, 10, 10, 5, 5)
            # 右链环
            painter.drawRoundedRect(17, 10, 10, 10, 5, 5)
        elif icon_type == "disconnect":
            # 断开图标（断开的链条）
            pen = QPen(QColor("#CF222E"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            # 左链环
            painter.drawRoundedRect(4, 10, 9, 9, 4.5, 4.5)
            # 右链环（偏移表示断开）
            painter.drawRoundedRect(19, 11, 9, 9, 4.5, 4.5)
            # 斜线表示断开
            painter.drawLine(15, 8, 17, 22)
        elif icon_type == "delete":
            # 删除图标（垃圾桶）
            pen = QPen(QColor("#CF222E"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            # 桶身
            painter.drawRect(8, 10, 16, 14)
            # 桶盖
            painter.drawLine(6, 10, 26, 10)
            # 竖线
            painter.drawLine(12, 12, 12, 22)
            painter.drawLine(20, 12, 20, 22)
        
        painter.end()
        return QIcon(pixmap)
    
    def _get_primary_button_style(self) -> str:
        """获取主要按钮样式"""
        return """
            QPushButton {
                background-color: #0969DA;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0550AE;
            }
            QPushButton:pressed {
                background-color: #043E8C;
            }
        """
    
    def _get_danger_button_style(self) -> str:
        """获取危险按钮样式"""
        return """
            QPushButton {
                background-color: #CF222E;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #A40E26;
            }
            QPushButton:pressed {
                background-color: #8B0820;
            }
        """
    
    def _get_primary_action_button_style(self) -> str:
        """获取操作按钮样式（主要）"""
        return """
            QPushButton {
                background-color: #0969DA;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 500;
                font-size: 12px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #0550AE;
            }
            QPushButton:pressed {
                background-color: #043E8C;
            }
        """
    
    def _get_danger_action_button_style(self) -> str:
        """获取操作按钮样式（危险）"""
        return """
            QPushButton {
                background-color: #CF222E;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 500;
                font-size: 12px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #A40E26;
            }
            QPushButton:pressed {
                background-color: #8B0820;
            }
        """
    
    def _get_action_button_style(self) -> str:
        """获取操作按钮样式（次要）"""
        return """
            QPushButton {
                background-color: #FFFFFF;
                color: #24292F;
                border: 1px solid #D0D7DE;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 500;
                font-size: 12px;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #F6F8FA;
                border-color: #0969DA;
            }
            QPushButton:pressed {
                background-color: #EAEFF2;
            }
        """
    
    def _get_icon_button_style(self, primary=False) -> str:
        """获取图标按钮样式"""
        if primary:
            return """
                QPushButton {
                    background-color: #0969DA;
                    border: none;
                    border-radius: 16px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #0550AE;
                }
                QPushButton:pressed {
                    background-color: #043E8C;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #D0D7DE;
                    border-radius: 16px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #F6F8FA;
                    border-color: #0969DA;
                }
                QPushButton:pressed {
                    background-color: #EAEFF2;
                }
            """
    
    def _get_device_tree_style(self) -> str:
        """获取设备树样式"""
        return """
            QTreeWidget {
                background-color: #FFFFFF;
                border: 1px solid #D0D7DE;
                border-radius: 8px;
                gridline-color: #EAEFF2;
                outline: none;
            }
            QTreeWidget::item {
                padding: 10px;
                border: none;
            }
            QTreeWidget::item:hover {
                background-color: #F6F8FA;
            }
            QTreeWidget::item:selected {
                background-color: #0969DA;
                color: white;
            }
            QHeaderView::section {
                background-color: #F6F8FA;
                color: #57606A;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #D0D7DE;
                font-weight: 600;
                font-size: 13px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #EAEFF2;
            }
            QHeaderView::section:pressed {
                background-color: #D0D7DE;
            }
        """

    def _get_table_style(self) -> str:
        """获取表格通用样式"""
        return """
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #D0D7DE;
                border-radius: 8px;
                gridline-color: #EAEFF2;
                selection-background-color: rgba(9, 105, 218, 0.15);
            }
            QTableWidget::item {
                padding: 10px;
                border: none;
            }
            QTableWidget::item:hover {
                background-color: #F6F8FA;
            }
            QTableWidget::item:selected {
                background-color: rgba(9, 105, 218, 0.2);
                color: #24292F;
            }
            QHeaderView::section {
                background-color: #F6F8FA;
                color: #57606A;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #D0D7DE;
                font-weight: 600;
                font-size: 13px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #EAEFF2;
            }
            QHeaderView::section:pressed {
                background-color: #D0D7DE;
            }
        """


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("工业设备管理系统")
    app.setApplicationVersion("2.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
