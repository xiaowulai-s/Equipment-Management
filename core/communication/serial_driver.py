# -*- coding: utf-8 -*-
"""
串口通信驱动
Serial Communication Driver
"""

import threading
from typing import Optional

from PySide6.QtCore import QTimer

from .base_driver import BaseDriver

try:
    import serial

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class SerialDriver(BaseDriver):
    """
    串口通信驱动
    Serial Communication Driver
    """

    def __init__(
        self,
        port: str = "COM1",
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: float = 1,
        parent=None,
    ):
        super().__init__(parent)
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._serial: Optional[serial.Serial] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._is_running = False

        if not SERIAL_AVAILABLE:
            self.error_occurred.emit("pyserial未安装，串口功能不可用")

    def connect(self) -> bool:
        """
        连接设备
        Connect to device
        """
        if not SERIAL_AVAILABLE:
            self.error_occurred.emit("pyserial未安装，请先安装: pip install pyserial")
            return False

        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=1.0,
            )
            self._is_connected = True
            self._is_running = True

            # 启动接收线程
            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()

            self.connected.emit()
            return True
        except Exception as e:
            self.error_occurred.emit(f"串口连接失败: {str(e)}")
            return False

    def disconnect(self):
        """
        断开连接
        Disconnect from device
        """
        self._is_running = False

        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None

        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=1.0)

        self._is_connected = False
        self._clear_buffer()
        self.disconnected.emit()

    def send_data(self, data: bytes) -> bool:
        """
        发送数据
        Send data to device
        """
        if not self._is_connected or not self._serial or not self._serial.is_open:
            return False

        try:
            self._serial.write(data)
            self._serial.flush()
            self.data_sent.emit(data)
            return True
        except Exception as e:
            self.error_occurred.emit(f"发送数据失败: {str(e)}")
            return False

    def _receive_loop(self):
        """
        接收循环
        Receive loop
        """
        while self._is_running and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    if data:
                        self._append_to_buffer(data)
                        self.data_received.emit(data)
            except Exception as e:
                if self._is_running:
                    self.error_occurred.emit(f"接收数据失败: {str(e)}")
                break

    def set_port(self, port: str):
        """
        设置端口
        Set port
        """
        self._port = port

    def set_baudrate(self, baudrate: int):
        """
        设置波特率
        Set baudrate
        """
        self._baudrate = baudrate

    def set_bytesize(self, bytesize: int):
        """
        设置数据位
        Set bytesize
        """
        self._bytesize = bytesize

    def set_parity(self, parity: str):
        """
        设置校验位
        Set parity
        """
        self._parity = parity

    def set_stopbits(self, stopbits: float):
        """
        设置停止位
        Set stopbits
        """
        self._stopbits = stopbits
