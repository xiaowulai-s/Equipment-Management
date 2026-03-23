# -*- coding: utf-8 -*-
"""
工业设备管理系统 - 新版本
Industrial Equipment Management System - New Version
基于四层解耦架构
Based on 4-layer decoupled architecture
"""

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
                               QPushButton, QLabel, QStackedWidget, QMessageBox,
                               QDialog, QFormLayout, QComboBox, QCheckBox, QLineEdit,
                               QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon, QFont

# 导入核心模块
from core.device.device_manager import DeviceManager
from core.device.device_factory import DeviceFactory, ProtocolType
from core.device.device_model import DeviceStatus


class AddDeviceDialog(QDialog):
    """添加设备对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加设备")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout()

        # 设备名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入设备名称")
        layout.addRow("设备名称:", self.name_edit)

        # 协议类型
        self.protocol_combo = QComboBox()
        for protocol in DeviceFactory.get_available_protocols():
            self.protocol_combo.addItem(protocol["name"], protocol["type"])
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_changed)
        layout.addRow("协议类型:", self.protocol_combo)

        # 使用模拟器
        self.simulator_check = QCheckBox("启用仿真模式")
        layout.addRow("", self.simulator_check)

        # 动态参数字段容器
        self.params_group = QGroupBox("参数配置")
        self.params_layout = QFormLayout()
        self.params_group.setLayout(self.params_layout)
        layout.addRow(self.params_group)

        # 按钮
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

        # 初始化参数
        self._on_protocol_changed(0)

    def _on_protocol_changed(self, index):
        """协议变化时更新参数表单"""
        # 清除现有字段
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取新协议的参数
        protocol_type = self.protocol_combo.currentData()
        params_info = DeviceFactory.get_protocol_params(protocol_type)

        if params_info:
            self._param_widgets = {}
            for field in params_info["fields"]:
                field_name = field["name"]
                field_label = field["label"]
                field_type = field["type"]
                default_value = field["default"]

                if field_type == "text":
                    widget = QLineEdit(str(default_value))
                elif field_type == "number":
                    widget = QLineEdit(str(default_value))
                elif field_type == "dropdown":
                    widget = QComboBox()
                    for opt in field["options"]:
                        widget.addItem(str(opt), opt)
                else:
                    widget = QLineEdit(str(default_value))

                self._param_widgets[field_name] = widget
                self.params_layout.addRow(field_label + ":", widget)

    def get_device_config(self) -> dict:
        """获取设备配置"""
        config = {
            "name": self.name_edit.text() or "未命名设备",
            "protocol_type": self.protocol_combo.currentData(),
            "use_simulator": self.simulator_check.isChecked()
        }

        # 获取参数
        for name, widget in self._param_widgets.items():
            if isinstance(widget, QComboBox):
                config[name] = widget.currentData()
            else:
                text = widget.text()
                try:
                    config[name] = int(text)
                except ValueError:
                    try:
                        config[name] = float(text)
                    except ValueError:
                        config[name] = text

        return config


class DeviceMonitorWidget(QWidget):
    """设备监控组件"""

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self._device_manager = device_manager
        self._current_device_id = None
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout()

        # 标题
        title = QLabel("设备监控")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        # 数据卡片区域
        self.cards_layout = QGridLayout()
        self.cards_group = QGroupBox("实时数据")
        self.cards_group.setLayout(self.cards_layout)
        layout.addWidget(self.cards_group)

        # 状态信息
        self.status_label = QLabel("请选择设备")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setLayout(layout)

    def _connect_signals(self):
        """连接信号"""
        self._device_manager.device_data_updated.connect(self._on_data_updated)
        self._device_manager.device_connected.connect(self._on_device_connected)
        self._device_manager.device_disconnected.connect(self._on_device_disconnected)

    def set_current_device(self, device_id: str):
        """设置当前设备"""
        self._current_device_id = device_id
        self._update_ui()

    def _update_ui(self):
        """更新UI"""
        if not self._current_device_id:
            self.status_label.setText("请选择设备")
            return

        device = self._device_manager.get_device(self._current_device_id)
        if not device:
            return

        status = device.get_status()
        if status == DeviceStatus.CONNECTED:
            self.status_label.setText(f"设备已连接: {device.get_device_config().get('name', '')}")
            self.status_label.setStyleSheet("color: #4CAF50;")
        elif status == DeviceStatus.DISCONNECTED:
            self.status_label.setText(f"设备已断开: {device.get_device_config().get('name', '')}")
            self.status_label.setStyleSheet("color: #F44336;")
        elif status == DeviceStatus.ERROR:
            self.status_label.setText(f"设备错误: {device.get_device_config().get('name', '')}")
            self.status_label.setStyleSheet("color: #FFC107;")

        # 更新数据卡片
        self._update_data_cards(device.get_current_data())

    def _update_data_cards(self, data: dict):
        """更新数据卡片"""
        # 清除现有卡片
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新卡片
        row, col = 0, 0
        for name, info in data.items():
            card = self._create_data_card(name, info)
            self.cards_layout.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _create_data_card(self, name: str, info: dict) -> QWidget:
        """创建数据卡片"""
        card = QGroupBox(name)
        layout = QVBoxLayout()

        value = info.get("value", 0)
        unit = info.get("unit", "")

        value_label = QLabel(f"{value:.2f} {unit}")
        value_label.setFont(QFont("Arial", 20, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

        raw_label = QLabel(f"原始值: {info.get('raw', 0)}")
        raw_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(raw_label)

        card.setLayout(layout)
        return card

    @Slot(str, dict)
    def _on_data_updated(self, device_id: str, data: dict):
        """数据更新"""
        if device_id == self._current_device_id:
            self._update_data_cards(data)

    @Slot(str)
    def _on_device_connected(self, device_id: str):
        """设备连接"""
        if device_id == self._current_device_id:
            self._update_ui()

    @Slot(str)
    def _on_device_disconnected(self, device_id: str):
        """设备断开"""
        if device_id == self._current_device_id:
            self._update_ui()


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._device_manager = DeviceManager("config.json")
        self._init_ui()
        self._connect_signals()
        self._refresh_device_list()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("工业设备管理系统 v2.0")
        self.setMinimumSize(1200, 800)

        # 主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧 - 设备列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 设备列表标题和按钮
        title_layout = QHBoxLayout()
        title_label = QLabel("设备列表")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self.add_device_btn = QPushButton("+")
        self.add_device_btn.setMaximumWidth(40)
        self.add_device_btn.clicked.connect(self._add_device)
        title_layout.addWidget(self.add_device_btn)

        left_layout.addLayout(title_layout)

        # 设备树
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabel("设备")
        self.device_tree.currentItemChanged.connect(self._on_device_selected)
        left_layout.addWidget(self.device_tree)

        # 设备操作按钮
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self._connect_device)
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.clicked.connect(self._disconnect_device)
        self.remove_btn = QPushButton("删除")
        self.remove_btn.clicked.connect(self._remove_device)

        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)
        btn_layout.addWidget(self.remove_btn)
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_widget)

        # 右侧 - 监控区域
        self.stack_widget = QStackedWidget()

        # 欢迎页面
        welcome_page = QWidget()
        welcome_layout = QVBoxLayout(welcome_page)
        welcome_label = QLabel("欢迎使用工业设备管理系统")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setFont(QFont("Arial", 18, QFont.Bold))
        welcome_layout.addWidget(welcome_label)
        welcome_layout.addStretch()
        self.stack_widget.addWidget(welcome_page)

        # 设备监控页面
        self.monitor_widget = DeviceMonitorWidget(self._device_manager)
        self.stack_widget.addWidget(self.monitor_widget)

        splitter.addWidget(self.stack_widget)

        # 设置分割器比例
        splitter.setSizes([300, 900])

        # 状态栏
        self.statusBar().showMessage("就绪")

    def _connect_signals(self):
        """连接信号"""
        self._device_manager.device_added.connect(self._on_device_added)
        self._device_manager.device_removed.connect(self._on_device_removed)
        self._device_manager.device_connected.connect(self._on_device_connected)
        self._device_manager.device_disconnected.connect(self._on_device_disconnected)

    def _refresh_device_list(self):
        """刷新设备列表"""
        self.device_tree.clear()

        for device_info in self._device_manager.get_all_devices():
            item = QTreeWidgetItem()
            item.setText(0, device_info["name"])
            item.setData(0, Qt.UserRole, device_info["device_id"])

            # 设置状态图标
            status = device_info["status"]
            if status == DeviceStatus.CONNECTED:
                item.setForeground(0, Qt.green)
            elif status == DeviceStatus.ERROR:
                item.setForeground(0, Qt.red)

            self.device_tree.addTopLevelItem(item)

    def _add_device(self):
        """添加设备"""
        dialog = AddDeviceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.get_device_config()
            self._device_manager.add_device(config)

    def _remove_device(self):
        """删除设备"""
        item = self.device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.UserRole)
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该设备吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._device_manager.remove_device(device_id)

    def _connect_device(self):
        """连接设备"""
        item = self.device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.UserRole)
        if self._device_manager.connect_device(device_id):
            self.statusBar().showMessage("正在连接...")
        else:
            QMessageBox.warning(self, "错误", "连接失败")

    def _disconnect_device(self):
        """断开设备"""
        item = self.device_tree.currentItem()
        if not item:
            return

        device_id = item.data(0, Qt.UserRole)
        self._device_manager.disconnect_device(device_id)

    def _on_device_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """设备选中"""
        if not current:
            self.stack_widget.setCurrentIndex(0)
            return

        device_id = current.data(0, Qt.UserRole)
        self.monitor_widget.set_current_device(device_id)
        self.stack_widget.setCurrentIndex(1)

    @Slot(str)
    def _on_device_added(self, device_id: str):
        """设备添加"""
        self._refresh_device_list()
        self.statusBar().showMessage(f"设备已添加: {device_id}")

    @Slot(str)
    def _on_device_removed(self, device_id: str):
        """设备移除"""
        self._refresh_device_list()
        self.stack_widget.setCurrentIndex(0)
        self.statusBar().showMessage(f"设备已删除: {device_id}")

    @Slot(str)
    def _on_device_connected(self, device_id: str):
        """设备连接"""
        self._refresh_device_list()
        self.statusBar().showMessage(f"设备已连接: {device_id}")

    @Slot(str)
    def _on_device_disconnected(self, device_id: str):
        """设备断开"""
        self._refresh_device_list()
        self.statusBar().showMessage(f"设备已断开: {device_id}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("工业设备管理系统")
    app.setApplicationVersion("2.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
