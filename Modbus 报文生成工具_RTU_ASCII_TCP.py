import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *


# ================= CRC16 (Modbus RTU) =================
def crc16(data: bytes):
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
def lrc(data: bytes):
    lrc_val = sum(data) & 0xFF
    lrc_val = (~lrc_val + 1) & 0xFF
    return lrc_val


# ================= 核心生成函数 =================
class ModbusGenerator:

    @staticmethod
    def rtu(slave, func, addr, count):
        frame = bytes([slave, func, (addr >> 8) & 0xFF, addr & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
        crc_code = crc16(frame)
        return frame + crc_code

    @staticmethod
    def ascii(slave, func, addr, count):
        frame = bytes([slave, func, (addr >> 8) & 0xFF, addr & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
        lrc_code = lrc(frame)
        ascii_str = ":" + "".join(f"{b:02X}" for b in frame) + f"{lrc_code:02X}\r\n"
        return ascii_str

    @staticmethod
    def tcp(slave, func, addr, count):
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


# ================= UI =================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modbus报文生成工具")
        self.resize(600, 400)

        layout = QVBoxLayout()

        # 协议选择
        self.rtu_radio = QRadioButton("Modbus-RTU")
        self.ascii_radio = QRadioButton("Modbus-ASCII")
        self.tcp_radio = QRadioButton("Modbus-TCP")
        self.rtu_radio.setChecked(True)

        proto_layout = QHBoxLayout()
        proto_layout.addWidget(self.rtu_radio)
        proto_layout.addWidget(self.ascii_radio)
        proto_layout.addWidget(self.tcp_radio)
        layout.addLayout(proto_layout)

        # 参数输入
        form = QFormLayout()

        self.slave_input = QLineEdit("0x01")
        self.func_box = QComboBox()
        self.func_box.addItems(
            [
                "0x01 读线圈",
                "0x02 读离散输入",
                "0x03 读保持寄存器",
                "0x04 读输入寄存器",
                "0x05 写单个线圈",
                "0x06 写单个寄存器",
                "0x0f 写多个线圈",
                "0x10 写多个寄存器",
            ]
        )

        self.addr_input = QLineEdit("0x0000")
        self.count_input = QLineEdit("1")

        form.addRow("从设备ID:", self.slave_input)
        form.addRow("功能码:", self.func_box)
        form.addRow("寄存器地址:", self.addr_input)
        form.addRow("寄存器数量:", self.count_input)

        layout.addLayout(form)

        # 输出
        self.output = QTextEdit()
        layout.addWidget(self.output)

        # 按钮
        btn_layout = QHBoxLayout()

        self.gen_btn = QPushButton("更新")
        self.copy_btn = QPushButton("复制")
        self.clear_btn = QPushButton("清除")
        self.send_btn = QPushButton("发送")

        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.send_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 绑定事件
        self.gen_btn.clicked.connect(self.generate)
        self.copy_btn.clicked.connect(self.copy)
        self.clear_btn.clicked.connect(self.output.clear)

    # ================= 功能实现 =================
    def generate(self):
        try:
            slave = int(self.slave_input.text(), 0)
            func = int(self.func_box.currentText().split()[0], 16)
            addr = int(self.addr_input.text(), 0)
            count = int(self.count_input.text(), 0)

            if self.rtu_radio.isChecked():
                frame = ModbusGenerator.rtu(slave, func, addr, count)
                result = " ".join(f"{b:02X}" for b in frame)

            elif self.ascii_radio.isChecked():
                result = ModbusGenerator.ascii(slave, func, addr, count)

            else:
                frame = ModbusGenerator.tcp(slave, func, addr, count)
                result = " ".join(f"{b:02X}" for b in frame)

            self.output.setText(result)

        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output.toPlainText())


# ================= 运行 =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
