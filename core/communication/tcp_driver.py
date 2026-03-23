# -*- coding: utf-8 -*-
"""
TCP通信驱动
TCP Communication Driver
"""

import socket
import threading
from typing import Optional
from PySide6.QtCore import QTimer, Signal
from .base_driver import BaseDriver


class TCPDriver(BaseDriver):
    """
    TCP通信驱动
    TCP Communication Driver
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 502, parent=None):
        super().__init__(parent)
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)

    def connect(self) -> bool:
        """
        连接设备
        Connect to device
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((self._host, self._port))
            self._is_connected = True
            self._is_running = True

            # 启动接收线程
            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()

            # 启动心跳
            self._heartbeat_timer.start(10000)  # 10秒心跳

            self.connected.emit()
            return True
        except Exception as e:
            self.error_occurred.emit(f"TCP连接失败: {str(e)}")
            return False

    def disconnect(self):
        """
        断开连接
        Disconnect from device
        """
        self._is_running = False
        self._heartbeat_timer.stop()

        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None

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
        if not self._is_connected or not self._socket:
            return False

        try:
            self._socket.sendall(data)
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
        while self._is_running and self._socket:
            try:
                data = self._socket.recv(4096)
                if data:
                    self._append_to_buffer(data)
                    self.data_received.emit(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self._is_running:
                    self.error_occurred.emit(f"接收数据失败: {str(e)}")
                break

    def _send_heartbeat(self):
        """
        发送心跳
        Send heartbeat
        """
        if self._is_connected:
            # 简单的心跳实现，可以根据实际协议调整
            pass

    def set_host(self, host: str):
        """
        设置主机地址
        Set host address
        """
        self._host = host

    def set_port(self, port: int):
        """
        设置端口
        Set port
        """
        self._port = port
