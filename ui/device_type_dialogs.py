# -*- coding: utf-8 -*-
"""
MCGS Device Type Management Dialogs

Refactored for MCGS-based device type management:
- Device types are templates stored in config/device_types.json
- Each type defines default connection parameters and register points
- Adding a device can copy from existing device or use a type template
"""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ui.widgets import DangerButton, LineEdit, PrimaryButton, SecondaryButton

DEVICE_TYPES_PATH = Path(__file__).parent.parent / "config" / "device_types.json"
DEVICES_CONFIG_PATH = Path(__file__).parent.parent / "config" / "devices.json"


class MCGSDeviceTypeManager:
    """Manages MCGS device type templates"""

    def __init__(self):
        self._types_file = DEVICE_TYPES_PATH
        self._types: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if self._types_file.exists():
            try:
                with open(self._types_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._types = data.get("device_types", {})
            except Exception:
                self._types = {}
        self._ensure_default_type()

    def _save(self):
        self._types_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._types_file, "w", encoding="utf-8") as f:
            json.dump({"device_types": self._types}, f, ensure_ascii=False, indent=2)

    def _ensure_default_type(self):
        if "MCGS触摸屏" not in self._types:
            self._types["MCGS触摸屏"] = {
                "protocol": "Modbus TCP",
                "port": 502,
                "unit_id": 1,
                "byte_order": "ABCD",
                "address_base": 40001,
                "polling_interval_ms": 1000,
                "default_points": [
                    {"name": "Data0", "addr": 40001, "type": "uint16"},
                    {"name": "Data1", "addr": 40002, "type": "uint16"},
                    {"name": "Data2", "addr": 40003, "type": "uint16"},
                    {"name": "Data3", "addr": 40004, "type": "uint16"},
                ],
            }
            self._save()

    def get_all_types(self) -> List[str]:
        return list(self._types.keys())

    def get_type_config(self, type_name: str) -> Optional[Dict]:
        return self._types.get(type_name)

    def add_type(self, name: str, config: Dict) -> bool:
        if name in self._types:
            return False
        self._types[name] = config
        self._save()
        return True

    def update_type(self, name: str, config: Dict) -> bool:
        if name not in self._types:
            return False
        self._types[name] = config
        self._save()
        return True

    def remove_type(self, name: str) -> bool:
        if name not in self._types:
            return False
        del self._types[name]
        self._save()
        return True

    def rename_type(self, old_name: str, new_name: str, new_config: Dict, affected_devices: List[Dict]) -> bool:
        if old_name not in self._types:
            return False
        del self._types[old_name]
        self._types[new_name] = new_config
        for dev in affected_devices:
            if dev.get("device_type") == old_name or dev.get("type") == old_name:
                dev["device_type"] = new_name
            if dev.get("_type_template") == old_name:
                dev["_type_template"] = new_name
        self._save()
        if DEVICES_CONFIG_PATH.exists():
            try:
                with open(DEVICES_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                devices = data.get("devices", [])
                updated = False
                for dev in devices:
                    if (
                        dev.get("device_type") == old_name
                        or dev.get("type") == old_name
                        or dev.get("_type_template") == old_name
                    ):
                        dev["device_type"] = new_name
                        updated = True
                if updated:
                    with open(DEVICES_CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning("同步设备类型到配置文件失败: %s", e)
        return True

    def get_existing_devices(self) -> List[Dict]:
        """Get all existing devices from devices.json for copy functionality"""
        if DEVICES_CONFIG_PATH.exists():
            try:
                with open(DEVICES_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("devices", [])
            except Exception:
                pass
        return []


class DeviceTypeEditDialog(QDialog):
    """Add/Edit MCGS device type dialog"""

    def __init__(self, parent=None, edit_name: str = None, edit_config: Dict = None):
        super().__init__(parent)
        self._is_edit = edit_name is not None
        self.setWindowTitle("编辑设备类型" if self._is_edit else "添加设备类型")
        self.setMinimumWidth(500)
        self._init_ui(edit_name, edit_config or {})

    def _init_ui(self, name: str, config: Dict):
        layout = QFormLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.name_edit = LineEdit(name)
        self.name_edit.setPlaceholderText("例如: MCGS触摸屏、PLC设备")
        layout.addRow("类型名称 *:", self.name_edit)

        self.protocol_edit = LineEdit(config.get("protocol", "Modbus TCP"))
        layout.addRow("协议类型 *:", self.protocol_edit)

        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItems(["ABCD", "BADC", "CDAB", "DCBA"])
        idx = self.byte_order_combo.findText(config.get("byte_order", "ABCD"))
        if idx >= 0:
            self.byte_order_combo.setCurrentIndex(idx)
        layout.addRow("字节序 *:", self.byte_order_combo)

        self.description_edit = LineEdit(config.get("description", ""))
        self.description_edit.setPlaceholderText("类型描述（可选，如：用于温湿度采集的MCGS触摸屏）")
        layout.addRow("类型描述:", self.description_edit)

        btn_layout = QHBoxLayout()
        self.ok_btn = PrimaryButton("确定")
        self.cancel_btn = SecondaryButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
        self.setLayout(layout)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入类型名称")
            return
        protocol = self.protocol_edit.text().strip()
        if not protocol:
            QMessageBox.warning(self, "提示", "请输入协议类型")
            return
        self.accept()

    def get_result(self) -> tuple:
        return (
            self.name_edit.text().strip(),
            {
                "protocol": self.protocol_edit.text().strip() or "Modbus TCP",
                "byte_order": self.byte_order_combo.currentText(),
                "description": self.description_edit.text().strip(),
                "port": 502,
                "unit_id": 1,
                "address_base": 40001,
                "polling_interval_ms": 1000,
                "default_points": [],
            },
        )


class DeviceTypeDialog(QDialog):
    """MCGS Device Type Manager Dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = MCGSDeviceTypeManager()
        self.setWindowTitle("MCGS设备类型管理")
        self.setMinimumWidth(650)
        self.setMinimumHeight(450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        hint = QLabel("管理MCGS设备类型模板。添加设备时可选择类型，自动填充默认配置。")
        hint.setStyleSheet("color: #6B7280; font-size: 13px;")
        layout.addWidget(hint)

        self.type_table = QTableWidget()
        self.type_table.setColumnCount(4)
        self.type_table.setHorizontalHeaderLabels(["类型名称", "协议类型", "字节序", "类型描述"])
        self.type_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.type_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.type_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.type_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.type_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.type_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.type_table)

        btn_layout = QHBoxLayout()

        self.add_btn = PrimaryButton("添加类型")
        self.add_btn.clicked.connect(self._add_type)

        self.edit_btn = SecondaryButton("编辑类型")
        self.edit_btn.clicked.connect(self._edit_type)

        self.remove_btn = DangerButton("删除类型")
        self.remove_btn.clicked.connect(self._remove_type)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch()

        self.close_btn = SecondaryButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self._refresh()

    def _refresh(self):
        self.type_table.setRowCount(0)
        for tname, tconfig in self._manager._types.items():
            row = self.type_table.rowCount()
            self.type_table.insertRow(row)
            self.type_table.setItem(row, 0, QTableWidgetItem(tname))
            self.type_table.setItem(row, 1, QTableWidgetItem(tconfig.get("protocol", "")))
            self.type_table.setItem(row, 2, QTableWidgetItem(tconfig.get("byte_order", "")))
            desc = tconfig.get("description", "")
            self.type_table.setItem(row, 3, QTableWidgetItem(desc if desc else "-"))

    def _add_type(self):
        dialog = DeviceTypeEditDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, config = dialog.get_result()
            if self._manager.add_type(name, config):
                self._refresh()
            else:
                QMessageBox.warning(self, "错误", f"类型 '{name}' 已存在")

    def _edit_type(self):
        row = self.type_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要编辑的类型")
            return
        tname = self.type_table.item(row, 0).text()
        tconfig = self._manager.get_type_config(tname) or {}
        dialog = DeviceTypeEditDialog(self, tname, tconfig)
        if dialog.exec() == QDialog.Accepted:
            new_name, new_config = dialog.get_result()

            if new_name != tname:
                existing_devices = self._manager.get_existing_devices()
                devices_using_type = [
                    dev
                    for dev in existing_devices
                    if dev.get("device_type") == tname
                    or dev.get("type") == tname
                    or dev.get("_type_template", "") == tname
                ]
                if devices_using_type:
                    device_names = [d.get("name", d.get("id", "?")) for d in devices_using_type]
                    msg_lines = [f'当前类型 "{tname}" 下已有 {len(devices_using_type)} 个设备：', ""]
                    msg_lines += [f"  • {n}" for n in device_names[:10]]
                    if len(device_names) > 10:
                        msg_lines.append(f"  ... 等共 {len(device_names)} 个设备")
                    msg_lines.append("")
                    msg_lines.append(f'是否将所有设备的类型更改为 "{new_name}"？')
                    msg = "\n".join(msg_lines)
                    reply = QMessageBox.question(
                        self,
                        "确认重命名类型",
                        msg,
                        QMessageBox.StandardButton.Yes
                        | QMessageBox.StandardButton.No
                        | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Yes,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

                self._manager.rename_type(tname, new_name, new_config, devices_using_type)
            else:
                self._manager.update_type(new_name, new_config)

            self._refresh()

    def _remove_type(self):
        row = self.type_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的类型")
            return
        tname = self.type_table.item(row, 0).text()

        # 检查是否有设备使用此类型
        existing_devices = self._manager.get_existing_devices()
        devices_using_type = [
            dev.get("name", dev.get("id", "?"))
            for dev in existing_devices
            if dev.get("device_type") == tname or dev.get("type") == tname
        ]

        if devices_using_type:
            # 有设备使用此类型，禁止删除
            device_list = "\n".join([f"  • {name}" for name in devices_using_type[:5]])
            if len(devices_using_type) > 5:
                device_list += f"\n  ... 等共 {len(devices_using_type)} 个设备"
            QMessageBox.warning(
                self,
                "无法删除",
                f'设备类型 "{tname}" 正被以下设备使用，无法删除：\n\n{device_list}\n\n'
                f"请先删除或修改这些设备的类型后再试。",
            )
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f'确定删除设备类型 "{tname}" 吗？',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._manager.remove_type(tname)
            self._refresh()


class AddMCGSDeviceDialog(QDialog):
    """
    Simplified Add MCGS Device Dialog

    Features:
    - Select device type (auto-fills defaults)
    - Copy from existing device
    - Custom device ID (unique per type)
    - Duplicate config detection
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = MCGSDeviceTypeManager()
        self.setWindowTitle("添加MCGS设备")
        self.setMinimumWidth(550)
        self._result = None
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.type_combo = QComboBox()
        self.type_combo.addItem("-- 选择设备类型 --")
        for tname in self._manager.get_all_types():
            self.type_combo.addItem(tname)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("设备类型 *:", self.type_combo)

        self.copy_combo = QComboBox()
        self.copy_combo.addItem("-- 复制现有设备（可选） --")
        for dev in self._manager.get_existing_devices():
            label = f"{dev.get('name', dev.get('id', '?'))} @ {dev.get('ip', '?')}"
            self.copy_combo.addItem(label, copy.deepcopy(dev))
        self.copy_combo.currentIndexChanged.connect(self._on_copy_changed)
        layout.addRow("复制自:", self.copy_combo)

        self.device_id_edit = LineEdit()
        self.device_id_edit.setPlaceholderText("例如: mcgs_2, plc_1（唯一标识）")
        layout.addRow("设备ID *:", self.device_id_edit)

        self.device_name_edit = LineEdit()
        self.device_name_edit.setPlaceholderText("显示名称")
        layout.addRow("设备名称:", self.device_name_edit)

        self.description_edit = LineEdit()
        self.description_edit.setPlaceholderText("设备描述（可选，如：车间A-温度采集）")
        layout.addRow("设备描述:", self.description_edit)

        self.ip_edit = LineEdit("192.168.31.239")
        layout.addRow("IP地址 *:", self.ip_edit)

        self.port_edit = LineEdit("502")
        layout.addRow("端口:", self.port_edit)

        self.unit_id_edit = LineEdit("1")
        layout.addRow("从站ID:", self.unit_id_edit)

        btn_layout = QHBoxLayout()
        self.ok_btn = PrimaryButton("确定添加")
        self.cancel_btn = SecondaryButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
        self.setLayout(layout)

    def _on_type_changed(self, index):
        if index <= 0:
            return
        tname = self.type_combo.currentText()
        config = self._manager.get_type_config(tname)
        if config:
            self.port_edit.setText(str(config.get("port", 502)))
            self.unit_id_edit.setText(str(config.get("unit_id", 1)))

    def _on_copy_changed(self, index):
        if index <= 0:
            return
        dev = self.copy_combo.currentData()
        if dev:
            self.ip_edit.setText(dev.get("ip", ""))
            self.port_edit.setText(str(dev.get("port", 502)))
            self.unit_id_edit.setText(str(dev.get("unit_id", 1)))
            if not self.device_name_edit.text():
                self.device_name_edit.setText(dev.get("name", ""))
            if not self.description_edit.text():
                self.description_edit.setText(dev.get("description", ""))
            tid = dev.get("id", "")
            if tid and not self.device_id_edit.text():
                base = tid.rsplit("_", 1)[0] if "_" in tid else tid
                self.device_id_edit.setText(f"{base}_copy")

    def _on_ok(self):
        did = self.device_id_edit.text().strip()
        if not did:
            QMessageBox.warning(self, "提示", "请输入设备ID")
            return
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "提示", "请输入IP地址")
            return

        try:
            check_port = int(self.port_edit.text().strip() or 502)
        except ValueError:
            QMessageBox.warning(self, "错误", "端口号必须为数字")
            return

        for dev in self._manager.get_existing_devices():
            if dev.get("id") == did:
                QMessageBox.warning(self, "错误", f"设备ID '{did}' 已存在，请使用不同的ID")
                return
            if dev.get("ip") == ip and dev.get("port", 502) == check_port:
                reply = QMessageBox.question(
                    self,
                    "配置重复",
                    f"已存在相同IP+端口配置的设备 [{dev.get('name', dev.get('id'))}]。\n是否继续添加？",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

        try:
            _port = int(self.port_edit.text().strip() or 502)
        except ValueError:
            QMessageBox.warning(self, "错误", "端口号必须为数字")
            return
        try:
            _unit_id = int(self.unit_id_edit.text().strip() or 1)
        except ValueError:
            QMessageBox.warning(self, "错误", "单元ID必须为数字")
            return

        self._result = {
            "id": did,
            "name": self.device_name_edit.text().strip() or did,
            "description": self.description_edit.text().strip(),
            "ip": ip,
            "port": _port,
            "unit_id": _unit_id,
            "byte_order": "ABCD",
            "polling_interval_ms": 1000,
            "address_base": 40001,
            "points": copy.deepcopy(
                [
                    {"name": "Data0", "addr": 40001, "type": "uint16"},
                    {"name": "Data1", "addr": 40002, "type": "uint16"},
                    {"name": "Data2", "addr": 40003, "type": "uint16"},
                    {"name": "Data3", "addr": 40004, "type": "uint16"},
                ]
            ),
        }
        self.accept()

    def get_device_config(self) -> Optional[Dict]:
        return self._result


class DataPointEditDialog(QDialog):
    """单个数据点编辑对话框"""

    def __init__(self, point_data: Dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑数据点")
        self.setMinimumWidth(400)
        self._point_data = point_data or {
            "name": "",
            "addr": "",
            "type": "int16",
            "unit": "",
            "description": "",
            "alarm_high": None,
            "alarm_low": None,
        }
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: Temp_in, Hum_in")
        layout.addRow("名称 *:", self.name_edit)

        self.addr_edit = QLineEdit()
        self.addr_edit.setPlaceholderText("例如: 40001")
        layout.addRow("地址 *:", self.addr_edit)

        self.type_combo = QComboBox()
        type_options = [
            ("float / float32 (浮点数)", "float"),
            ("int16 / uint16 (16位整数)", "int16"),
            ("int32 / uint32 (32位整数)", "int32"),
            ("coil (线圈/布尔输出)", "coil"),
            ("discrete_input (DI/开关量)", "di"),
            ("string (字符串)", "string"),
        ]
        for text, data in type_options:
            self.type_combo.addItem(text, data)
        layout.addRow("类型:", self.type_combo)

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("℃, %RH, kPa...")
        layout.addRow("单位:", self.unit_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("用途说明...")
        layout.addRow("描述:", self.desc_edit)

        self.alarm_high_edit = QLineEdit()
        self.alarm_high_edit.setPlaceholderText("留空表示不限")
        layout.addRow("报警高:", self.alarm_high_edit)

        self.alarm_low_edit = QLineEdit()
        self.alarm_low_edit.setPlaceholderText("留空表示不限")
        layout.addRow("报警低:", self.alarm_low_edit)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("确定")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _load_data(self):
        self.name_edit.setText(self._point_data.get("name", ""))
        self.addr_edit.setText(str(self._point_data.get("addr", "")))
        # 通过 itemData 匹配类型（支持别名：uint16→int16, uint32→int32, float32→float）
        current_type = self._point_data.get("type", "int16")
        type_alias = {"uint16": "int16", "uint32": "int32", "float32": "float"}
        match_type = type_alias.get(current_type, current_type)
        idx = self.type_combo.findData(match_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.unit_edit.setText(self._point_data.get("unit", ""))
        self.desc_edit.setText(self._point_data.get("description", ""))
        high = self._point_data.get("alarm_high")
        self.alarm_high_edit.setText(str(high) if high is not None else "")
        low = self._point_data.get("alarm_low")
        self.alarm_low_edit.setText(str(low) if low is not None else "")

    def get_point_data(self) -> Dict:
        result = dict(self._point_data)
        result.update(
            {
                "name": self.name_edit.text().strip(),
                "addr": self.addr_edit.text().strip(),
                "type": self.type_combo.currentData() or "int16",
                "unit": self.unit_edit.text().strip(),
                "description": self.desc_edit.text().strip(),
            }
        )
        high_text = self.alarm_high_edit.text().strip()
        result["alarm_high"] = float(high_text) if high_text else None
        low_text = self.alarm_low_edit.text().strip()
        result["alarm_low"] = float(low_text) if low_text else None
        return result


class EditMCGSDeviceDialog(QDialog):
    """
    MCGS 设备连接参数编辑对话框

    功能：
    - 加载已有设备的完整配置（IP/端口/从站ID/超时/字节序）
    - 可视化编辑连接参数
    - 显示当前数据点列表（只读展示）
    - 保存后更新 devices.json 中对应设备
    """

    def __init__(self, device_config: Dict, parent=None):
        super().__init__(parent)
        self._original_config = copy.deepcopy(device_config)
        self._device_id = device_config.get("id", "")
        self._result = None
        self._changed = False
        self._deleted_points_stack: List[Tuple[int, Dict]] = []
        self.setWindowTitle(f"编辑设备连接参数 - [{self._device_id}]")
        self.setMinimumWidth(580)
        self._init_ui()
        self._load_from_config(device_config)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 16)
        main_layout.setSpacing(16)

        info_label = QLabel(f"设备 ID: {self._device_id}")
        info_label.setStyleSheet("font-size: 13px; color: #6B7280; font-weight: 600;")
        main_layout.addWidget(info_label)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        self.device_type_combo = QComboBox()
        self.device_type_combo.setToolTip("选择设备类型以应用预设参数")
        type_manager = MCGSDeviceTypeManager()
        for type_name in type_manager.get_all_types():
            self.device_type_combo.addItem(type_name)
        self.device_type_combo.currentIndexChanged.connect(self._on_device_type_changed)
        form.addRow("设备类型 *:", self.device_type_combo)

        self.name_edit = LineEdit()
        form.addRow("设备名称:", self.name_edit)

        self.description_edit = LineEdit()
        form.addRow("设备描述:", self.description_edit)

        ip_layout = QHBoxLayout()
        ip_layout.setSpacing(8)
        self.ip_edit = LineEdit()
        self.ip_edit.setMinimumWidth(200)
        self.ip_edit.setToolTip("设备的 IP 地址，更换环境时修改此项")
        self.test_conn_btn = QPushButton("🔗 测试")
        self.test_conn_btn.setFixedHeight(36)
        self.test_conn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_conn_btn.setStyleSheet(
            """
            QPushButton {
                background: #E3F2FD;
                color: #1565C0;
                border: 1px solid #90CAF9;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: #BBDEFB; }
            QPushButton:pressed { background: #90CAF9; }
        """
        )
        self.test_conn_btn.clicked.connect(self._test_connection)
        ip_layout.addWidget(self.ip_edit, 1)
        ip_layout.addWidget(self.test_conn_btn)
        form.addRow("IP 地址 *:", ip_layout)

        self.port_edit = LineEdit("502")
        self.port_edit.setMaximumWidth(100)
        self.port_edit.setToolTip("Modbus TCP 端口，默认 502")
        form.addRow("端 口:", self.port_edit)

        uid_layout = QHBoxLayout()
        uid_layout.setSpacing(8)
        self.unit_id_edit = LineEdit("1")
        self.unit_id_edit.setMaximumWidth(80)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(500, 30000)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setValue(3000)
        self.timeout_spin.setSingleStep(500)
        uid_layout.addWidget(self.unit_id_edit)
        uid_layout.addWidget(QLabel("超时:"))
        uid_layout.addWidget(self.timeout_spin)
        uid_layout.addStretch()
        form.addRow("从站ID / 超时:", uid_layout)

        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItems(["ABCD", "CDAB", "BADC", "DCBA"])
        form.addRow("字节序:", self.byte_order_combo)

        self.address_base_spin = QSpinBox()
        self.address_base_spin.setRange(0, 65535)
        self.address_base_spin.setValue(40001)
        self.address_base_spin.setToolTip("Modbus地址基数（通常为40001或1）")
        form.addRow("地址基数:", self.address_base_spin)

        main_layout.addLayout(form)

        points_group = QGroupBox("数据点配置")
        points_layout = QVBoxLayout(points_group)

        points_toolbar = QHBoxLayout()
        self.add_point_btn = QPushButton("+ 添加点位")
        self.add_point_btn.setStyleSheet(
            "background-color: #3B82F6; color: white; padding: 6px 14px; border-radius: 6px;"
        )
        self.add_point_btn.clicked.connect(self._add_new_point)
        points_toolbar.addWidget(self.add_point_btn)

        self.remove_point_btn = QPushButton("- 删除选中")
        self.remove_point_btn.setEnabled(False)
        self.remove_point_btn.clicked.connect(self._remove_selected_point)
        points_toolbar.addWidget(self.remove_point_btn)

        self.edit_point_btn = QPushButton("✏ 编辑选中")
        self.edit_point_btn.setEnabled(False)
        self.edit_point_btn.clicked.connect(self._edit_selected_point)
        points_toolbar.addWidget(self.edit_point_btn)

        self.undo_delete_btn = QPushButton("↩ 撤销删除")
        self.undo_delete_btn.setEnabled(False)
        self.undo_delete_btn.clicked.connect(self._undo_delete)
        points_toolbar.addWidget(self.undo_delete_btn)

        self.preset_data_btn = QPushButton("📋 预设数据")
        self.preset_data_btn.setToolTip("快速填充常用数据点配置")
        self.preset_data_btn.clicked.connect(self._show_preset_menu)
        points_toolbar.addWidget(self.preset_data_btn)

        points_toolbar.addStretch()
        points_layout.addLayout(points_toolbar)

        self.points_table = QTableWidget()
        self.points_table.setColumnCount(6)
        self.points_table.setHorizontalHeaderLabels(["名称", "地址", "类型", "单位", "描述", "操作"])
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.points_table.setAlternatingRowColors(True)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.points_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.points_table.currentCellChanged.connect(self._on_point_selection_changed)
        self.points_table.doubleClicked.connect(self._edit_selected_point)
        self.points_table.setMinimumHeight(120)
        self.points_table.setStyleSheet(
            """
            QTableWidget {
                background: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                gridline-color: #F0F2F5;
                font-size: 12px;
            }
            QTableWidget::item { padding: 4px 8px; }
            QHeaderView::section {
                background: #F6F8FA;
                color: #57606A;
                padding: 6px;
                font-weight: 600;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid #E5E7EB;
            }
        """
        )
        points_layout.addWidget(self.points_table)
        main_layout.addWidget(points_group)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        main_layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = PrimaryButton("💾 保存修改")
        self.cancel_btn = SecondaryButton("取消")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self._on_cancel)

        for widget in [self.name_edit, self.description_edit, self.ip_edit, self.port_edit, self.unit_id_edit]:
            widget.textChanged.connect(self._mark_changed)

        self.timeout_spin.valueChanged.connect(self._mark_changed)
        self.byte_order_combo.currentIndexChanged.connect(self._mark_changed)
        self.address_base_spin.valueChanged.connect(self._mark_changed)
        self.device_type_combo.currentIndexChanged.connect(self._mark_changed)

    def _mark_changed(self):
        """标记配置已被修改"""
        self._changed = True

    def _has_changes(self) -> bool:
        """检查是否有未保存的更改"""
        return self._changed

    def _on_cancel(self):
        """处理取消/关闭操作"""
        if self._has_changes():
            reply = QMessageBox.question(
                self,
                "未保存的更改",
                "检测到有未保存的修改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
                return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.reject()

    def closeEvent(self, event):
        """重写关闭事件"""
        if self._has_changes():
            reply = QMessageBox.question(
                self,
                "未保存的更改",
                "检测到有未保存的修改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._on_save()
                event.accept()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            else:
                event.accept()
        else:
            event.accept()

    def _on_device_type_changed(self, index: int):
        """当设备类型改变时，自动填充默认参数"""
        type_name = self.device_type_combo.currentText()
        if not type_name:
            return

        type_manager = MCGSDeviceTypeManager()
        type_config = type_manager.get_type_config(type_name)
        if not type_config:
            return

        if not self.port_edit.text():
            self.port_edit.setText(str(type_config.get("port", 502)))

        if self.byte_order_combo.findText(type_config.get("byte_order", "ABCD")) >= 0:
            self.byte_order_combo.setCurrentText(type_config.get("byte_order", "ABCD"))

        if not self.unit_id_edit.text() or self.unit_id_edit.text() == "1":
            self.unit_id_edit.setText(str(type_config.get("unit_id", 1)))

        if hasattr(self, "status_label"):
            self.status_label.setText(f"已加载 [{type_name}] 默认参数")
            self.status_label.setStyleSheet("font-size: 12px; color: #10B981;")

    def _load_from_config(self, cfg: Dict):
        self.name_edit.setText(cfg.get("name", ""))
        self.description_edit.setText(cfg.get("description", ""))
        self.ip_edit.setText(cfg.get("ip", ""))
        self.port_edit.setText(str(cfg.get("port", 502)))
        self.unit_id_edit.setText(str(cfg.get("unit_id", 1)))
        self.timeout_ms = cfg.get("timeout_ms", 3000)
        self.timeout_spin.setValue(self.timeout_ms)
        idx = self.byte_order_combo.findText(cfg.get("byte_order", "ABCD"))
        if idx >= 0:
            self.byte_order_combo.setCurrentIndex(idx)

        device_type = cfg.get("device_type", "MCGS触摸屏")
        idx = self.device_type_combo.findText(device_type)
        if idx >= 0:
            self.device_type_combo.setCurrentIndex(idx)

        addr_base = cfg.get("address_base", 40001)
        if isinstance(addr_base, int):
            self.address_base_spin.setValue(addr_base)
        elif isinstance(addr_base, str):
            try:
                self.address_base_spin.setValue(int(addr_base))
            except ValueError:
                pass

        points = cfg.get("points", [])
        self.points_table.setRowCount(len(points))
        for row, pt in enumerate(points):
            self._fill_point_row(row, pt)

    def _on_point_selection_changed(self, current_row, current_col, previous_row, previous_col):
        """数据点选择变化时更新按钮状态"""
        has_selection = current_row >= 0
        self.remove_point_btn.setEnabled(has_selection)
        self.edit_point_btn.setEnabled(has_selection)

    def _add_new_point(self):
        """添加新的数据点"""
        dialog = DataPointEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_point_data()
            row = self.points_table.rowCount()
            self.points_table.insertRow(row)
            self._fill_point_row(row, new_data)
            self._mark_changed()
            self.status_label.setText(f"已添加数据点: {new_data['name']}")
            self.status_label.setStyleSheet("font-size: 12px; color: #10B981;")

    def _edit_selected_point(self):
        """编辑选中的数据点（独立窗口）"""
        current_row = self.points_table.currentRow()
        if current_row < 0:
            return

        point_data = {
            "name": self.points_table.item(current_row, 0).text() if self.points_table.item(current_row, 0) else "",
            "addr": self.points_table.item(current_row, 1).text() if self.points_table.item(current_row, 1) else "",
            "type": (
                self.points_table.item(current_row, 2).text() if self.points_table.item(current_row, 2) else "int16"
            ),
            "unit": self.points_table.item(current_row, 3).text() if self.points_table.item(current_row, 3) else "",
            "description": (
                self.points_table.item(current_row, 4).text() if self.points_table.item(current_row, 4) else ""
            ),
        }

        dialog = DataPointEditDialog(point_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_point_data()
            self._fill_point_row(current_row, new_data)
            self._mark_changed()
            self.status_label.setText(f"已更新数据点: {new_data['name']}")
            self.status_label.setStyleSheet("font-size: 12px; color: #10B981;")

    def _remove_selected_point(self):
        """删除选中的数据点"""
        current_row = self.points_table.currentRow()
        if current_row < 0:
            return
        self._remove_point(current_row)

    def _remove_point(self, row: int):
        """删除数据点（支持撤销）"""
        deleted_data = {
            "name": self.points_table.item(row, 0).text() if self.points_table.item(row, 0) else "",
            "addr": self.points_table.item(row, 1).text() if self.points_table.item(row, 1) else "",
            "type": self.points_table.item(row, 2).text() if self.points_table.item(row, 2) else "",
            "unit": self.points_table.item(row, 3).text() if self.points_table.item(row, 3) else "",
            "description": self.points_table.item(row, 4).text() if self.points_table.item(row, 4) else "",
        }

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除数据点 '{deleted_data['name']}' 吗？\n\n提示：删除后可通过[撤销删除]按钮恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._deleted_points_stack.append((row, deleted_data))
            self.points_table.removeRow(row)
            self._mark_changed()
            self.undo_delete_btn.setEnabled(True)
            self.status_label.setText(f"已删除: {deleted_data['name']} (可撤销)")
            self.status_label.setStyleSheet("font-size: 12px; color: #F59E0B;")

    def _undo_delete(self):
        """撤销最近的删除操作"""
        if not self._deleted_points_stack:
            return

        row, data = self._deleted_points_stack.pop()

        insert_row = min(row, self.points_table.rowCount())
        self.points_table.insertRow(insert_row)
        self._fill_point_row(insert_row, data)

        del_btn = QPushButton("删除")
        del_btn.setStyleSheet(
            """
            QPushButton { color: #F44336; border: none; background: transparent; font-size: 11px; padding: 2px 8px; border-radius: 4px; }
            QPushButton:hover { background: #FFEBEE; }
        """
        )
        del_btn.clicked.connect(lambda _, r=insert_row: self._remove_point(r))
        self.points_table.setCellWidget(insert_row, 5, del_btn)

        if not self._deleted_points_stack:
            self.undo_delete_btn.setEnabled(False)

        self.status_label.setText(f"已恢复: {data['name']}")
        self.status_label.setStyleSheet("font-size: 12px; color: #10B981;")

    def _show_preset_menu(self):
        """显示预设数据选项菜单"""
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)

        action1 = menu.addAction("六路通用数据 (40001-40006)")
        action1.triggered.connect(lambda: self._apply_preset_6points())

        action2 = menu.addAction("四路传感器 (40001-40004)")
        action2.triggered.connect(lambda: self._apply_preset_4points())

        menu.exec_(self.mapToGlobal(self.preset_data_btn.geometry().bottomLeft()))

    def _apply_preset_6points(self):
        """应用设备1的6个数据点预设（40001-40006）"""
        preset_points = [
            {"name": "通讯状态", "addr": "40001", "type": "int16"},
            {"name": "DevPoint_读写4W0001", "addr": "40002", "type": "int16"},
            {"name": "DevPointAtm_读写4W0002", "addr": "40003", "type": "int16"},
            {"name": "H2Oppm_读写4W0003", "addr": "40004", "type": "int16"},
            {"name": "Data0_读写4W0004", "addr": "40005", "type": "int16"},
            {"name": "Data1_读写4W0005", "addr": "40006", "type": "int16"},
        ]
        self._fill_preset_points(preset_points)

    def _apply_preset_4points(self):
        """应用4路数据点预设"""
        preset_points = [
            {"name": "Data0", "addr": "40001", "type": "uint16"},
            {"name": "Data1", "addr": "40002", "type": "uint16"},
            {"name": "Data2", "addr": "40003", "type": "uint16"},
            {"name": "Data3", "addr": "40004", "type": "uint16"},
        ]
        self._fill_preset_points(preset_points)

    def _fill_preset_points(self, points: List[Dict]):
        """填充预设数据点到表格"""
        self.points_table.setRowCount(0)

        for i, pt in enumerate(points):
            self.points_table.insertRow(i)
            self._fill_point_row(i, pt)

        self._mark_changed()
        self.status_label.setText(f"已填充 {len(points)} 个预设数据点")
        self.status_label.setStyleSheet("font-size: 12px; color: #10B981;")

    def _fill_point_row(self, row: int, point_data: Dict):
        """填充单行数据点到表格"""
        self.points_table.setItem(row, 0, QTableWidgetItem(point_data.get("name", "")))
        self.points_table.setItem(row, 1, QTableWidgetItem(str(point_data.get("addr", ""))))
        self.points_table.setItem(row, 2, QTableWidgetItem(point_data.get("type", "int16")))
        self.points_table.setItem(row, 3, QTableWidgetItem(point_data.get("unit", "")))
        self.points_table.setItem(row, 4, QTableWidgetItem(point_data.get("description", "")))

        del_btn = QPushButton("删除")
        del_btn.setStyleSheet(
            """
            QPushButton { color: #F44336; border: none; background: transparent; font-size: 11px; padding: 2px 8px; border-radius: 4px; }
            QPushButton:hover { background: #FFEBEE; }
        """
        )
        del_btn.clicked.connect(lambda _, r=row: self._remove_point(r))
        self.points_table.setCellWidget(row, 5, del_btn)

    class _ConnectionTestWorkerSignals(QObject):
        result = Signal(bool, str, str, float)

    class _ConnectionTestWorker(QRunnable):
        def __init__(self, ip, port, timeout):
            super().__init__()
            self.ip = ip
            self.port = port
            self.timeout = timeout
            self.signals = EditMCGSDeviceDialog._ConnectionTestWorkerSignals()

        def run(self):
            import socket

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                start = time.time()
                result_code = sock.connect_ex((self.ip, self.port))
                elapsed = (time.time() - start) * 1000
                sock.close()
                if result_code == 0:
                    self.signals.result.emit(True, self.ip, str(self.port), elapsed)
                else:
                    self.signals.result.emit(False, self.ip, str(self.port), 0.0)
            except socket.timeout:
                self.signals.result.emit(False, self.ip, str(self.port), -1.0)
            except Exception:
                self.signals.result.emit(False, self.ip, str(self.port), -2.0)

    def _test_connection(self):
        ip = self.ip_edit.text().strip()
        port_str = self.port_edit.text().strip()
        if not ip or not port_str:
            self.status_label.setText("❌ 请先填写 IP 和端口")
            self.status_label.setStyleSheet("font-size: 12px; color: #F44336;")
            return
        try:
            port = int(port_str)
        except ValueError:
            self.status_label.setText("❌ 端口号格式错误")
            self.status_label.setStyleSheet("font-size: 12px; color: #F44336;")
            return

        self.test_conn_btn.setEnabled(False)
        self.test_conn_btn.setText("测试中...")
        self.status_label.setText(f"⏳ 正在连接 {ip}:{port} ...")
        self.status_label.setStyleSheet("font-size: 12px; color: #2196F3;")

        worker = EditMCGSDeviceDialog._ConnectionTestWorker(ip, port, self.timeout_spin.value() / 1000.0)
        worker.signals.result.connect(self._on_test_result)
        QThreadPool.globalInstance().start(worker)

    def _on_test_result(self, success, ip, port, elapsed_ms):
        if success:
            self.status_label.setText(f"✅ 连接成功！{ip}:{port} 延迟 {elapsed_ms:.0f}ms")
            self.status_label.setStyleSheet("font-size: 12px; color: #4CAF50; font-weight: 600;")
        elif elapsed_ms == -1.0:
            self.status_label.setText(f"❌ 连接超时 ({self.timeout_spin.value()}ms)")
            self.status_label.setStyleSheet("font-size: 12px; color: #F44336;")
        else:
            self.status_label.setText(f"❌ 连接失败：无法到达 {ip}:{port}")
            self.status_label.setStyleSheet("font-size: 12px; color: #F44336;")
        self.test_conn_btn.setEnabled(True)
        self.test_conn_btn.setText("🔗 测试")

    def _on_save(self):
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "提示", "请输入 IP 地址")
            return
        port_str = self.port_edit.text().strip()
        try:
            port = int(port_str) if port_str else 502
        except ValueError:
            QMessageBox.warning(self, "提示", "端口号必须为数字")
            return
        uid_str = self.unit_id_edit.text().strip()
        try:
            unit_id = int(uid_str) if uid_str else 1
        except ValueError:
            QMessageBox.warning(self, "提示", "从站 ID 必须为数字")
            return

        points = []
        for row in range(self.points_table.rowCount()):
            name_item = self.points_table.item(row, 0)
            addr_item = self.points_table.item(row, 1)
            type_item = self.points_table.item(row, 2)
            if name_item and addr_item and type_item:
                unit_item = self.points_table.item(row, 3)
                desc_item = self.points_table.item(row, 4)
                point_data = {
                    "name": name_item.text(),
                    "addr": addr_item.text(),
                    "type": type_item.text(),
                }
                if unit_item and unit_item.text():
                    point_data["unit"] = unit_item.text()
                if desc_item and desc_item.text():
                    point_data["description"] = desc_item.text()
                points.append(point_data)

        self._result = copy.deepcopy(self._original_config)
        self._result.update(
            {
                "device_type": self.device_type_combo.currentText(),
                "name": self.name_edit.text().strip() or self._device_id,
                "description": self.description_edit.text().strip(),
                "ip": ip,
                "port": port,
                "unit_id": unit_id,
                "timeout_ms": self.timeout_spin.value(),
                "byte_order": self.byte_order_combo.currentText(),
                "address_base": self.address_base_spin.value(),
                "points": points,
            }
        )
        self.accept()

    def get_device_config(self) -> Optional[Dict]:
        return self._result
