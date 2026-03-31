# -*- coding: utf-8 -*-
"""
Modbus 报文生成工具

集成到主窗口的右侧栏目，支持 RTU/ASCII/TCP 三种协议。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import ComboBox, PrimaryButton, SecondaryButton


# ================= CRC16 (Modbus RTU) =================
def crc16(data: bytes) -> bytes:
    """计算 Modbus RTU CRC16 校验"""
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder="little")


# ================= LRC (Modbus ASCII) =================
def lrc(data: bytes) -> int:
    """计算 Modbus ASCII LRC 校验"""
    lrc_val = sum(data) & 0xFF
    lrc_val = (~lrc_val + 1) & 0xFF
    return lrc_val


# ================= 核心生成函数 =================
class ModbusGenerator:
    """Modbus 报文生成器"""

    @staticmethod
    def rtu(slave: int, func: int, addr: int, count: int) -> bytes:
        """生成 RTU 报文"""
        frame = bytes([slave, func, (addr >> 8) & 0xFF, addr & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
        crc_code = crc16(frame)
        return frame + crc_code

    @staticmethod
    def ascii(slave: int, func: int, addr: int, count: int) -> str:
        """生成 ASCII 报文"""
        frame = bytes([slave, func, (addr >> 8) & 0xFF, addr & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
        lrc_code = lrc(frame)
        ascii_str = ":" + "".join(f"{b:02X}" for b in frame) + f"{lrc_code:02X}\r\n"
        return ascii_str

    @staticmethod
    def tcp(slave: int, func: int, addr: int, count: int) -> bytes:
        """生成 TCP 报文 (MBAP 头)"""
        transaction_id = 0x0001
        protocol_id = 0x0000
        length = 6

        frame = [
            (transaction_id >> 8) & 0xFF,
            transaction_id & 0xFF,
            (protocol_id >> 8) & 0xFF,
            protocol_id & 0xFF,
            (length >> 8) & 0xFF,
            length & 0xFF,
            slave,
            func,
            (addr >> 8) & 0xFF,
            addr & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF,
        ]
        return bytes(frame)


class ModbusGeneratorWidget(QWidget):
    """
    Modbus 报文生成工具 Widget

    可嵌入主窗口使用。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(350)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title_label = QLabel("Modbus 报文生成工具")
        title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #24292F;")
        layout.addWidget(title_label)

        # 协议选择
        proto_layout = QHBoxLayout()
        self.rtu_radio = QRadioButton("RTU")
        self.ascii_radio = QRadioButton("ASCII")
        self.tcp_radio = QRadioButton("TCP")
        self.rtu_radio.setChecked(True)

        proto_layout.addWidget(QLabel("协议:"))
        proto_layout.addWidget(self.rtu_radio)
        proto_layout.addWidget(self.ascii_radio)
        proto_layout.addWidget(self.tcp_radio)
        proto_layout.addStretch()
        layout.addLayout(proto_layout)

        # 参数输入
        form = QFormLayout()
        form.setSpacing(8)

        self.slave_input = QLineEdit("0x01")
        self.slave_input.setPlaceholderText("例如: 0x01 或 1")

        self.func_box = ComboBox()
        self.func_box.addItems(
            [
                ("0x01 读线圈", 0x01),
                ("0x02 读离散输入", 0x02),
                ("0x03 读保持寄存器", 0x03),
                ("0x04 读输入寄存器", 0x04),
                ("0x05 写单个线圈", 0x05),
                ("0x06 写单个寄存器", 0x06),
                ("0x0F 写多个线圈", 0x0F),
                ("0x10 写多个寄存器", 0x10),
            ]
        )

        self.addr_input = QLineEdit("0x0000")
        self.addr_input.setPlaceholderText("例如: 0x0000 或 0")

        self.count_input = QLineEdit("1")
        self.count_input.setPlaceholderText("例如: 1")

        form.addRow("从设备ID:", self.slave_input)
        form.addRow("功能码:", self.func_box)
        form.addRow("寄存器地址:", self.addr_input)
        form.addRow("寄存器数量:", self.count_input)

        layout.addLayout(form)

        # 生成按钮
        self.gen_btn = PrimaryButton("生成报文")
        self.gen_btn.setMinimumHeight(32)
        self.gen_btn.clicked.connect(self.generate)
        layout.addWidget(self.gen_btn)

        # 输出
        output_label = QLabel("生成结果:")
        output_label.setStyleSheet("color: #57606A; font-size: 12px;")
        layout.addWidget(output_label)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("点击'生成报文'按钮生成 Modbus 报文...")
        self.output.setStyleSheet(
            """
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 12px;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )
        self.output.setMinimumHeight(100)
        layout.addWidget(self.output)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.copy_btn = SecondaryButton("复制")
        self.copy_btn.setFixedSize(70, 32)
        self.copy_btn.clicked.connect(self.copy_result)

        self.clear_btn = SecondaryButton("清除")
        self.clear_btn.setFixedSize(70, 32)
        self.clear_btn.clicked.connect(self.output.clear)

        btn_layout.addStretch()
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def generate(self) -> None:
        """生成报文"""
        try:
            slave = int(self.slave_input.text(), 0)
            func = self.func_box.currentData()
            addr = int(self.addr_input.text(), 0)
            count = int(self.count_input.text(), 0)

            if self.rtu_radio.isChecked():
                frame = ModbusGenerator.rtu(slave, func, addr, count)
                result = " ".join(f"{b:02X}" for b in frame)
                self.output.setText(f"[RTU] {result}")

            elif self.ascii_radio.isChecked():
                result = ModbusGenerator.ascii(slave, func, addr, count)
                self.output.setText(f"[ASCII] {result}")

            else:  # TCP
                frame = ModbusGenerator.tcp(slave, func, addr, count)
                result = " ".join(f"{b:02X}" for b in frame)
                self.output.setText(f"[TCP] {result}")

        except ValueError as e:
            QMessageBox.warning(self, "输入错误", f"请输入有效的数值:\n{str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成报文失败:\n{str(e)}")

    def copy_result(self) -> None:
        """复制结果到剪贴板"""
        text = self.output.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            # 可选：显示提示
            # QMessageBox.information(self, "复制成功", "报文已复制到剪贴板")
