# -*- coding: utf-8 -*-
"""
寄存器写入对话框
Register Write Dialog - 支持单个寄存器写入操作
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
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

        self._result_label = QLabel("")
        self._result_label.setStyleSheet("font-size: 12px; padding: 4px;")
        layout.addWidget(self._result_label)

        btn_layout = QHBoxLayout()
        self._write_btn = QPushButton("写入")
        self._write_btn.clicked.connect(self._do_write)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self._write_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    class _WriteTaskSignals(QObject):
        finished = Signal(bool, str)

    class _WriteTask(QRunnable):
        def __init__(self, protocol, reg_type, address, value, unit_id):
            super().__init__()
            self._protocol = protocol
            self._reg_type = reg_type
            self._address = address
            self._value = value
            self._unit_id = unit_id
            self.signals = RegisterWriteDialog._WriteTaskSignals()

        def run(self):
            try:
                if self._reg_type == "coil":
                    success = self._protocol.write_single_coil(self._address, bool(self._value), self._unit_id)
                else:
                    success = self._protocol.write_single_register(self._address, self._value, self._unit_id)
                if success:
                    self.signals.finished.emit(True, "")
                else:
                    self.signals.finished.emit(False, "设备未确认写入操作")
            except Exception as e:
                self.signals.finished.emit(False, str(e))

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

        protocol = self._device.get_protocol()
        if protocol is None:
            QMessageBox.critical(self, "写入失败", "设备协议未初始化")
            return

        self._write_btn.setEnabled(False)
        self._result_label.setText(f"⏳ 正在写入寄存器 {address} ...")
        self._result_label.setStyleSheet("font-size: 12px; color: #2196F3; padding: 4px;")

        task = RegisterWriteDialog._WriteTask(protocol, reg_type, address, value, self._unit_spin.value())
        task.signals.finished.connect(self._on_write_result)
        QThreadPool.globalInstance().start(task)

    def _on_write_result(self, success: bool, error_msg: str) -> None:
        self._write_btn.setEnabled(True)
        if success:
            self._result_label.setText(f"✅ 寄存器 {self._address_spin.value()} 已写入值 {self._value_spin.value()}")
            self._result_label.setStyleSheet("font-size: 12px; color: #4CAF50; font-weight: 600; padding: 4px;")
            self.write_completed.emit(self._address_spin.value(), self._value_spin.value())
            self.accept()
        else:
            self._result_label.setText(f"❌ 写入失败: {error_msg}")
            self._result_label.setStyleSheet("font-size: 12px; color: #F44336; padding: 4px;")
