# -*- coding: utf-8 -*-
"""
寄存器写入对话框
Register Write Dialog - 支持单个寄存器写入操作
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from core.device.device_model import Device


class RegisterWriteDialog(QDialog):
    """寄存器写入对话框 - 向设备写入单个寄存器值"""

    write_completed = Signal(int, int)

    def __init__(self, device: "Device", parent=None) -> None:
        super().__init__(parent)
        self._device = device
        self.setWindowTitle(f"写入寄存器 - {device.device_id}")
        self.setMinimumWidth(350)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._address_spin = QSpinBox()
        self._address_spin.setRange(0, 65535)
        self._address_spin.setValue(0)
        form.addRow("寄存器地址:", self._address_spin)

        self._type_combo = QComboBox()
        self._type_combo.addItem("线圈 (0x01/0x05)", "coil")
        self._type_combo.addItem("保持寄存器 (0x03/0x06)", "holding")
        self._type_combo.addItem("输入寄存器 (只读)", "input")
        form.addRow("寄存器类型:", self._type_combo)

        self._value_spin = QSpinBox()
        self._value_spin.setRange(-32768, 65535)
        self._value_spin.setValue(0)
        form.addRow("写入值:", self._value_spin)

        self._unit_spin = QSpinBox()
        self._unit_spin.setRange(1, 247)
        self._unit_spin.setValue(1)
        form.addRow("从机ID:", self._unit_spin)

        layout.addLayout(form)

        info_label = QLabel("⚠ 写入操作将直接修改设备寄存器，请确认参数正确")
        info_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        layout.addWidget(info_label)

        btn_layout = QHBoxLayout()
        write_btn = QPushButton("写入")
        write_btn.clicked.connect(self._do_write)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(write_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _do_write(self) -> None:
        reg_type = self._type_combo.currentData()
        if reg_type == "input":
            QMessageBox.warning(self, "无法写入", "输入寄存器为只读，无法写入")
            return

        address = self._address_spin.value()
        value = self._value_spin.value()

        if (
            QMessageBox.question(self, "确认写入", f"确认向地址 {address} 写入值 {value}?")
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            protocol = self._device.get_protocol()
            if protocol is None:
                QMessageBox.critical(self, "写入失败", "设备协议未初始化")
                return

            if reg_type == "coil":
                success = protocol.write_single_coil(address, bool(value), self._unit_spin.value())
            else:
                success = protocol.write_single_register(address, value, self._unit_spin.value())

            if success:
                QMessageBox.information(self, "写入成功", f"寄存器 {address} 已写入值 {value}")
                self.write_completed.emit(address, value)
                self.accept()
            else:
                QMessageBox.warning(self, "写入失败", "设备未确认写入操作")
        except Exception as e:
            QMessageBox.critical(self, "写入异常", str(e))
