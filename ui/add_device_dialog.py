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
from core.device.device_factory import ProtocolType
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

        # 自动重连开关
        self.auto_reconnect_check = QCheckBox("启用自动重连")
        self.auto_reconnect_check.setChecked(False)  # 默认禁用
        auto_reconnect_layout = QHBoxLayout()
        auto_reconnect_layout.addWidget(self.auto_reconnect_check)
        layout.addRow(auto_reconnect_layout)

        register_button_layout = QHBoxLayout()
        self.register_count_label = QLabel()
        self.register_count_label.setStyleSheet("color: #000000; font-size: 12px;")
        register_button_layout.addWidget(self.register_count_label)
        register_button_layout.addStretch()
        self.register_config_btn = PrimaryButton("配置寄存器地址")
        self.register_config_btn.clicked.connect(self._show_register_config)
        register_button_layout.addWidget(self.register_config_btn)
        layout.addRow(register_button_layout)

        self.params_group = QGroupBox("通信参数配置")
        self.params_layout = QFormLayout()
        self.params_layout.setSpacing(12)

        # 本机 IP 显示标签（仅用于 TCP 设备）
        self._local_ip_label = QLabel()
        self._local_ip_label.setStyleSheet("color: #2196F3; font-size: 12px;")
        self.params_layout.addRow(self._local_ip_label)

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
        # 设置自动重连开关状态
        self.auto_reconnect_check.setChecked(bool(config.get("auto_reconnect_enabled", False)))
        self._populate_protocol_fields(config)

    def _populate_protocol_fields(self, config: Dict[str, Any]) -> None:
        for field_name, widget in self._param_widgets.items():
            if field_name not in config:
                continue
            value = config[field_name]
            if isinstance(widget, QComboBox):
                # 对于串口下拉框，如果配置中的串口不在列表中，先添加它
                if field_name == "port":
                    found = False
                    for index in range(widget.count()):
                        if widget.itemData(index) == value:
                            widget.setCurrentIndex(index)
                            found = True
                            break
                    if not found and value:
                        # 添加配置中的串口到列表（可能是当前未连接的设备）
                        widget.addItem(value, value)
                        widget.setCurrentIndex(widget.count() - 1)
                else:
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

        # 获取本机 IP 地址（用于 TCP 设备默认值）
        local_ip = None
        if protocol_type == "modbus_tcp":
            from core.device.device_factory import get_local_ip

            local_ip = get_local_ip()

        for field in params_info["fields"]:
            field_name = field["name"]

            # RTU/ASCII 协议的串口字段使用 ComboBox
            if field_name == "port" and protocol_type in ("modbus_rtu", "modbus_ascii"):
                widget = self._build_serial_port_combo()
            # TCP 设备的 host 字段，将 AUTO 替换为本机 IP
            elif field_name == "host" and protocol_type == "modbus_tcp" and local_ip:
                field = dict(field)  # 复制字段配置
                if field.get("default") == "AUTO":
                    field["default"] = local_ip
                widget = self._build_param_widget(field)
            else:
                widget = self._build_param_widget(field)

            self._param_widgets[field_name] = widget

            if field_name == "port" and protocol_type in ("modbus_rtu", "modbus_ascii"):
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

        # 填充可用串口列表
        if protocol_type in ("modbus_rtu", "modbus_ascii"):
            self._refresh_serial_port_list()

        # 更新本机 IP 显示
        if protocol_type == "modbus_tcp" and local_ip:
            self._local_ip_label.setText(f"本机 IP: {local_ip}")
            self._local_ip_label.show()
        else:
            self._local_ip_label.hide()

        if self._edit_mode and self._device_config:
            self._populate_protocol_fields(self._device_config)

    def _build_serial_port_combo(self) -> ComboBox:
        """创建串口下拉框"""
        widget = ComboBox()
        widget.setMinimumWidth(150)
        return widget

    def _refresh_serial_port_list(self) -> None:
        """刷新可用串口列表，不自动选择"""
        port_widget = self._param_widgets.get("port")
        if not isinstance(port_widget, ComboBox):
            return

        from core.utils.serial_utils import list_serial_ports

        available_ports = list_serial_ports()

        # 保存当前选择（如果有）
        current_port = port_widget.currentData()

        # 清空并重新填充
        port_widget.clear()

        if available_ports:
            for port in available_ports:
                port_widget.addItem(port, port)

            # 仅恢复之前的选择，不自动选择第一个
            if current_port and current_port in available_ports:
                index = available_ports.index(current_port)
                port_widget.setCurrentIndex(index)
            else:
                # 不自动选择，显示提示项
                port_widget.setCurrentIndex(-1)
        else:
            port_widget.addItem("未检测到串口", "")

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
        # 统一使用黑色字体
        self.register_count_label.setStyleSheet("color: #000000; font-size: 12px;")

    def _on_test_serial(self) -> None:
        """测试串口连接，刷新串口列表并填充默认参数"""
        port_widget = self._param_widgets.get("port")
        if not isinstance(port_widget, ComboBox):
            QMessageBox.warning(self, "警告", "未找到串口号配置")
            return

        # 刷新串口列表（检测新接入的设备）
        self._refresh_serial_port_list()

        port = port_widget.currentData()

        # 检查是否有可用串口
        if not port:
            QMessageBox.warning(self, "警告", "未检测到可用串口")
            return

        # 设置默认参数（如果未设置）
        self._set_default_serial_params()

        # 获取测试参数
        baudrate = self._get_serial_param("baudrate", 9600)
        data_bits = self._get_serial_param("bytesize", 8)
        parity = self._get_serial_param("parity", "无校验")
        stop_bits = self._get_serial_param("stopbits", 1)

        # 执行测试
        success, message = test_serial_port(port, baudrate)

        # 获取当前可用串口列表用于显示
        from core.utils.serial_utils import list_serial_ports

        available_ports = list_serial_ports()

        # 构建详细信息
        detail_msg = (
            f"{message}\n\n"
            f"测试参数：\n"
            f"  串口：{port}\n"
            f"  波特率：{baudrate} bit/s\n"
            f"  数据位：{data_bits}\n"
            f"  校验位：{parity}\n"
            f"  停止位：{stop_bits}\n"
            f"\n可用串口：{', '.join(available_ports) if available_ports else '无'}"
        )

        if success:
            QMessageBox.information(self, "测试成功", detail_msg)
        else:
            QMessageBox.critical(self, "测试失败", detail_msg)

    def _set_default_serial_params(self) -> None:
        """设置串口默认参数（如果未设置）"""
        defaults = {
            "baudrate": ("9600", 9600),
            "bytesize": ("8", 8),
            "parity": ("无校验", "无校验"),
            "stopbits": ("1", 1),
        }

        for field_name, (text_value, data_value) in defaults.items():
            widget = self._param_widgets.get(field_name)
            if widget is None:
                continue

            if isinstance(widget, QComboBox):
                # 下拉框：检查是否已选择，未选择则设置为默认值
                if widget.currentIndex() < 0 or not widget.currentData():
                    for index in range(widget.count()):
                        if widget.itemData(index) == data_value or widget.itemText(index) == text_value:
                            widget.setCurrentIndex(index)
                            break
            elif isinstance(widget, QLineEdit):
                # 输入框：如果为空则填充默认值
                if not widget.text().strip():
                    widget.setText(text_value)

    def _get_serial_param(self, field_name: str, default: Any) -> Any:
        """获取串口参数值"""
        widget = self._param_widgets.get(field_name)
        if widget is None:
            return default

        if isinstance(widget, QComboBox):
            data = widget.currentData()
            return data if data is not None else default
        elif isinstance(widget, QLineEdit):
            text = widget.text().strip()
            if not text:
                return default
            try:
                return int(text)
            except ValueError:
                try:
                    return float(text)
                except ValueError:
                    return text
        return default

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
            "auto_reconnect_enabled": self.auto_reconnect_check.isChecked(),  # 自动重连开关
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
            # 兼容旧格式：将端口信息直接放在config顶层
            config["port"] = tcp_params["port"]

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
            # 兼容旧格式：将端口信息直接放在config顶层
            config["port"] = serial_params["port"]

        if poll_params:
            config["poll_config"] = poll_params

        # 兼容旧格式 (主窗口V2使用)
        # 暂时保留 host/ip 映射
        if tcp_params and "host" in tcp_params:
            config["ip"] = tcp_params["host"]
            config["host"] = tcp_params["host"]

        return config
