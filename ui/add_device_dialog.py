# -*- coding: utf-8 -*-
"""
添加设备对话框
Add Device Dialog
"""

from typing import Dict, Any, List
from PySide6.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QLabel,
                               QComboBox, QLineEdit, QCheckBox, QGroupBox,
                               QPushButton, QMessageBox)
from core.device.device_type_manager import DeviceTypeManager
from core.device.device_factory import DeviceFactory
from ui.styles import AppStyles
from ui.register_config_dialog import RegisterConfigDialog


class AddDeviceDialog(QDialog):
    """添加设备对话框"""

    def __init__(self, device_type_manager: DeviceTypeManager, parent=None, edit_mode=False, device_config=None):
        super().__init__(parent)
        self._device_type_manager = device_type_manager
        self._edit_mode = edit_mode
        self._device_config = device_config
        self._register_map: List[Dict] = device_config.get("register_map", []) if device_config else []
        self.setWindowTitle("编辑设备" if edit_mode else "添加设备")
        self.setMinimumWidth(500)
        self.setStyleSheet(AppStyles.DIALOG)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        type_label = QLabel("设备类型:")
        type_label.setStyleSheet("color: #24292F; font-weight: 500;")
        self.type_combo = QComboBox()
        for device_type in self._device_type_manager.get_all_device_types():
            self.type_combo.addItem(device_type["name"], device_type)
        self.type_combo.setStyleSheet(AppStyles.COMBO_BOX)
        layout.addRow(type_label, self.type_combo)

        name_label = QLabel("设备名称:")
        name_label.setStyleSheet("color: #24292F; font-weight: 500;")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入设备名称")
        self.name_edit.setStyleSheet(AppStyles.LINE_EDIT)
        layout.addRow(name_label, self.name_edit)

        number_label = QLabel("设备编号:")
        number_label.setStyleSheet("color: #24292F; font-weight: 500;")
        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("请输入设备编号")
        self.number_edit.setStyleSheet(AppStyles.LINE_EDIT)
        layout.addRow(number_label, self.number_edit)

        protocol_label = QLabel("协议类型:")
        protocol_label.setStyleSheet("color: #24292F; font-weight: 500;")
        self.protocol_combo = QComboBox()
        for protocol in DeviceFactory.get_available_protocols():
            self.protocol_combo.addItem(protocol["name"], protocol["type"])
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_changed)
        self.protocol_combo.setStyleSheet(AppStyles.COMBO_BOX)
        layout.addRow(protocol_label, self.protocol_combo)

        simulator_layout = QHBoxLayout()
        simulator_layout.addStretch()
        self.simulator_check = QCheckBox("启用仿真模式")
        self.simulator_check.setStyleSheet(AppStyles.CHECK_BOX)
        simulator_layout.addWidget(self.simulator_check)
        layout.addRow(simulator_layout)

        # 寄存器配置按钮
        register_btn_layout = QHBoxLayout()
        register_btn_layout.addStretch()
        self.register_config_btn = QPushButton("⚙️ 配置寄存器地址")
        self.register_config_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(135deg, #0969DA, #0550AE);
                color: white;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(135deg, #0550AE, #043E8C);
            }
        """)
        self.register_config_btn.clicked.connect(self._show_register_config)
        register_btn_layout.addWidget(self.register_config_btn)
        layout.addRow(register_btn_layout)
        
        # 寄存器数量标签
        self.register_count_label = QLabel("已配置 0 个寄存器")
        self.register_count_label.setStyleSheet("color: #57606A; font-size: 12px;")
        layout.addRow("", self.register_count_label)

        self.params_group = QGroupBox("通信参数配置")
        self.params_group.setStyleSheet(AppStyles.GROUP_BOX)
        self.params_layout = QFormLayout()
        self.params_layout.setSpacing(12)
        self.params_group.setLayout(self.params_layout)
        layout.addRow(self.params_group)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setStyleSheet(AppStyles.get_button_primary_with_padding(24))
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(AppStyles.get_button_secondary_with_padding(24))
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.setSpacing(12)
        layout.addRow(btn_layout)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.setLayout(layout)

        self._on_protocol_changed(0)

        if self._edit_mode and self._device_config:
            self._fill_edit_data()
            self._update_register_count()

    def _fill_edit_data(self):
        config = self._device_config
        device_type = config.get("device_type", "")
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i)["name"] == device_type:
                self.type_combo.setCurrentIndex(i)
                break

        self.name_edit.setText(config.get("name", ""))
        self.number_edit.setText(config.get("device_number", ""))

        protocol_type = config.get("protocol_type")
        for i in range(self.protocol_combo.count()):
            if self.protocol_combo.itemData(i) == protocol_type:
                self.protocol_combo.setCurrentIndex(i)
                break

        self.simulator_check.setChecked(config.get("use_simulator", False))

        self._param_widgets = {}
        protocol_type = self.protocol_combo.currentData()
        params_info = DeviceFactory.get_protocol_params(protocol_type)
        if params_info:
            for field in params_info["fields"]:
                field_name = field["name"]
                if field_name in config:
                    if field_name in self._param_widgets:
                        widget = self._param_widgets[field_name]
                        if isinstance(widget, QLineEdit):
                            widget.setText(str(config[field_name]))
                        elif isinstance(widget, QComboBox):
                            for i in range(widget.count()):
                                if widget.itemData(i) == config[field_name]:
                                    widget.setCurrentIndex(i)
                                    break

    def _on_protocol_changed(self, index):
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

                widget.setStyleSheet("""
                    QLineEdit, QComboBox {
                        background-color: #FFFFFF;
                        color: #24292F;
                        border: 1px solid #D0D7DE;
                        border-radius: 6px;
                        padding: 8px 12px;
                        font-size: 12px;
                        font-family: 'Inter', 'Segoe UI', sans-serif;
                    }
                """)

                self._param_widgets[field_name] = widget
                self.params_layout.addRow(field_label + ":", widget)
    
    def _show_register_config(self):
        """显示寄存器配置对话框"""
        dialog = RegisterConfigDialog(self._register_map, self)
        dialog.config_updated.connect(self._on_register_config_updated)
        dialog.exec()
    
    def _on_register_config_updated(self, register_map: list):
        """寄存器配置更新"""
        self._register_map = register_map
        self._update_register_count()
    
    def _update_register_count(self):
        """更新寄存器数量显示"""
        count = len(self._register_map)
        self.register_count_label.setText(f"已配置 {count} 个寄存器")
        if count > 0:
            self.register_count_label.setStyleSheet("color: #1A7F37; font-size: 12px; font-weight: 500;")

    def get_device_config(self) -> Dict[str, Any]:
        selected_type = self.type_combo.currentData()
        config = {
            "device_type": selected_type["name"] if selected_type else "",
            "name": self.name_edit.text() or "未命名设备",
            "device_number": self.number_edit.text() or "",
            "protocol_type": self.protocol_combo.currentData(),
            "use_simulator": self.simulator_check.isChecked(),
            "register_map": self._register_map
        }

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
