# -*- coding: utf-8 -*-
"""Dialog for creating or editing a device configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
)

# 导入旧架构的 DeviceFactory (待迁移)
from core.device.device_factory import DeviceFactory
from core.device.device_type_manager import DeviceTypeManager
from core.utils.serial_utils import test_serial_port

# 新架构导入
from src.protocols import ProtocolType
from ui.register_config_dialog import RegisterConfigDialog

# UI组件库
from ui.widgets import ComboBox, InputWithLabel, LineEdit, PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from ui.widgets import ComboBox as ComboBoxType
    from ui.widgets import LineEdit as LineEditType


class AddDeviceDialog(QDialog):
    """
    添加/编辑设备对话框

    提供设备配置界面，支持：
    - 设备类型选择
    - 协议配置（Modbus TCP/RTU/ASCII）
    - 仿真模式
    - 寄存器地址配置

    Attributes:
        _device_type_manager: 设备类型管理器
        _edit_mode: 是否为编辑模式
        _device_config: 设备配置字典
        _register_map: 寄存器映射列表
        _param_widgets: 协议参数控件字典
    """

    def __init__(
        self,
        device_type_manager: DeviceTypeManager,
        parent: Optional[QWidget] = None,
        edit_mode: bool = False,
        device_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        self._device_type_manager = device_type_manager
        self._edit_mode = edit_mode
        self._device_config = dict(device_config or {})
        self._register_map: List[Dict[str, Any]] = list(self._device_config.get("register_map", []))
        self._param_widgets: Dict[str, QWidget] = {}

        self.setWindowTitle("编辑设备" if edit_mode else "添加设备")
        self.setMinimumWidth(500)
        self._init_ui()

        if self._edit_mode:
            self._fill_edit_data()
        self._update_register_count()

    def _init_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.type_combo = ComboBox()
        for device_type in self._device_type_manager.get_all_device_types():
            self.type_combo.addItem(device_type["name"], device_type)
        layout.addRow(self._label("设备类型:"), self.type_combo)

        self.name_edit = LineEdit("请输入设备名称")
        layout.addRow(self._label("设备名称:"), self.name_edit)

        self.number_edit = LineEdit("请输入设备编号")
        layout.addRow(self._label("设备编号:"), self.number_edit)

        self.protocol_combo = ComboBox()
        for protocol in DeviceFactory.get_available_protocols():
            self.protocol_combo.addItem(protocol["name"], protocol["type"])
        self.protocol_combo.currentIndexChanged.connect(self._on_protocol_changed)
        layout.addRow(self._label("协议类型:"), self.protocol_combo)

        simulator_layout = QHBoxLayout()
        simulator_layout.addStretch()
        self.simulator_check = QCheckBox("启用仿真模式")
        simulator_layout.addWidget(self.simulator_check)
        layout.addRow(simulator_layout)

        register_button_layout = QHBoxLayout()
        register_button_layout.addStretch()
        self.register_config_btn = PrimaryButton("配置寄存器地址")
        self.register_config_btn.clicked.connect(self._show_register_config)
        register_button_layout.addWidget(self.register_config_btn)
        layout.addRow(register_button_layout)

        self.register_count_label = QLabel()
        self.register_count_label.setStyleSheet("color: #57606A; font-size: 12px;")
        layout.addRow("", self.register_count_label)

        self.params_group = QGroupBox("通信参数配置")
        self.params_layout = QFormLayout()
        self.params_layout.setSpacing(12)
        self.params_group.setLayout(self.params_layout)
        layout.addRow(self.params_group)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.ok_btn = PrimaryButton("确定")
        self.cancel_btn = SecondaryButton("取消")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.setSpacing(12)
        layout.addRow(button_layout)

        self._on_protocol_changed(0)

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color: #24292F; font-weight: 500;")
        return label

    def _fill_edit_data(self) -> None:
        config = self._device_config
        device_type_name = config.get("device_type", "")
        for index in range(self.type_combo.count()):
            item_data = self.type_combo.itemData(index)
            if item_data and item_data.get("name") == device_type_name:
                self.type_combo.setCurrentIndex(index)
                break

        self.name_edit.setText(str(config.get("name", "")))
        self.number_edit.setText(str(config.get("device_number", "")))

        protocol_type = config.get("protocol_type")
        for index in range(self.protocol_combo.count()):
            if self.protocol_combo.itemData(index) == protocol_type:
                self.protocol_combo.setCurrentIndex(index)
                break

        self.simulator_check.setChecked(bool(config.get("use_simulator", False)))
        self._populate_protocol_fields(config)

    def _populate_protocol_fields(self, config: Dict[str, Any]) -> None:
        for field_name, widget in self._param_widgets.items():
            if field_name not in config:
                continue
            value = config[field_name]
            if isinstance(widget, QComboBox):
                for index in range(widget.count()):
                    if widget.itemData(index) == value:
                        widget.setCurrentIndex(index)
                        break
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

    def _on_protocol_changed(self, _: int) -> None:
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._param_widgets = {}
        protocol_type = self.protocol_combo.currentData()
        params_info = DeviceFactory.get_protocol_params(protocol_type)
        if not params_info:
            return

        for field in params_info["fields"]:
            field_name = field["name"]
            widget = self._build_param_widget(field)
            self._param_widgets[field_name] = widget

            if field_name == "port" and protocol_type == "modbus_rtu":
                from ui.widgets import SecondaryButton

                layout = QHBoxLayout()
                layout.addWidget(widget)
                test_btn = SecondaryButton("测试")
                test_btn.setFixedWidth(60)
                test_btn.clicked.connect(self._on_test_serial)
                layout.addWidget(test_btn)
                self.params_layout.addRow(f"{field['label']}:", layout)
            else:
                self.params_layout.addRow(f"{field['label']}:", widget)

        if self._edit_mode and self._device_config:
            self._populate_protocol_fields(self._device_config)

    def _build_param_widget(self, field: Dict[str, Any]) -> QWidget:
        field_type = field["type"]
        default_value = field.get("default", "")

        if field_type == "dropdown":
            widget = ComboBox()
            for option in field.get("options", []):
                widget.addItem(str(option), option)
        else:
            widget = LineEdit(str(default_value))

        return widget

    def _show_register_config(self) -> None:
        dialog = RegisterConfigDialog(self._register_map, self)
        dialog.config_updated.connect(self._on_register_config_updated)
        dialog.exec()

    def _on_register_config_updated(self, register_map: List[Dict[str, Any]]) -> None:
        self._register_map = list(register_map)
        self._update_register_count()

    def _update_register_count(self) -> None:
        count = len(self._register_map)
        self.register_count_label.setText(f"已配置 {count} 个寄存器")
        if count > 0:
            self.register_count_label.setStyleSheet("color: #1A7F37; font-size: 12px; font-weight: 500;")
        else:
            self.register_count_label.setStyleSheet("color: #57606A; font-size: 12px;")

    def _on_test_serial(self) -> None:
        port_widget = self._param_widgets.get("port")
        if not isinstance(port_widget, QLineEdit):
            QMessageBox.warning(self, "警告", "未找到串口号配置")
            return

        port = port_widget.text().strip()
        if not port:
            QMessageBox.warning(self, "警告", "请输入串口号")
            return

        baudrate_widget = self._param_widgets.get("baudrate")
        baudrate = 9600
        if isinstance(baudrate_widget, QComboBox):
            baudrate = int(baudrate_widget.currentData())
        elif isinstance(baudrate_widget, QLineEdit):
            try:
                baudrate = int(baudrate_widget.text().strip())
            except Exception:
                baudrate = 9600

        success, message = test_serial_port(port, baudrate)
        if success:
            QMessageBox.information(self, "测试成功", message)
        else:
            QMessageBox.critical(self, "测试失败", message)

    def get_device_config(self) -> Dict[str, Any]:
        """获取设备配置字典 (新架构兼容格式)

        Returns:
            符合 src.device.Device.from_dict() 格式的字典
        """
        selected_type = self.type_combo.currentData()
        protocol_type_str = self.protocol_combo.currentData()

        # 构建新架构兼容的配置
        config: Dict[str, Any] = {
            "device_type": selected_type["name"] if selected_type else "",
            "name": self.name_edit.text().strip() or "未命名设备",
            "device_number": self.number_edit.text().strip(),
            "protocol_type": protocol_type_str,
            "use_simulator": self.simulator_check.isChecked(),
            "register_map": list(self._register_map),  # 保留旧格式，待主窗口迁移时转换为 Register 对象
        }

        # 解析协议特定参数
        tcp_params: Dict[str, Any] = {}
        serial_params: Dict[str, Any] = {}
        poll_params: Dict[str, Any] = {}

        for name, widget in self._param_widgets.items():
            value = None

            if isinstance(widget, QComboBox):
                value = widget.currentData()
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if text == "":
                    continue
                try:
                    value = int(text)
                except ValueError:
                    try:
                        value = float(text)
                    except ValueError:
                        value = text
            else:
                continue

            # 根据协议类型分配参数
            if protocol_type_str == "modbus_tcp":
                if name in ("host", "port", "timeout", "keepalive"):
                    tcp_params[name] = value
                elif name == "timeout":
                    tcp_params["timeout"] = float(value) if isinstance(value, (int, float)) else value
                else:
                    config[name] = value

            elif protocol_type_str in ("modbus_rtu", "modbus_ascii"):
                if name == "port":
                    serial_params["port"] = str(value)
                elif name == "baudrate":
                    serial_params["baud_rate"] = int(value)
                elif name in ("data_bits", "stop_bits", "parity", "timeout"):
                    serial_params[name] = value
                elif name == "flow_control":
                    serial_params["flow_control"] = bool(value)
                else:
                    config[name] = value

            # 通用参数
            if name in ("interval_ms", "retry_count", "retry_interval_ms"):
                poll_params[name] = value

        # 处理 slave_id/unit_id 兼容
        if "unit_id" in config:
            config["slave_id"] = config.pop("unit_id")
        elif "slave_id" not in config:
            config["slave_id"] = 1

        # 添加嵌套参数对象
        if tcp_params:
            # TCP默认值
            tcp_params.setdefault("host", "127.0.0.1")
            tcp_params.setdefault("port", 502)
            tcp_params.setdefault("timeout", 3.0)
            tcp_params.setdefault("keepalive", True)
            config["tcp_params"] = tcp_params

        if serial_params:
            # 串口默认值
            serial_params.setdefault("port", "COM1")
            serial_params.setdefault("baud_rate", 9600)
            serial_params.setdefault("data_bits", 8)
            serial_params.setdefault("stop_bits", 1.0)
            serial_params.setdefault("parity", "none")
            serial_params.setdefault("timeout", 3.0)
            serial_params.setdefault("flow_control", False)
            config["serial_params"] = serial_params

        if poll_params:
            config["poll_config"] = poll_params

        # 兼容旧格式 (主窗口V2使用)
        # 暂时保留 host/ip 映射
        if tcp_params and "host" in tcp_params:
            config["ip"] = tcp_params["host"]

        return config
