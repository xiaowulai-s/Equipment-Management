# -*- coding: utf-8 -*-
"""
通信驱动基类
Base Communication Driver
"""

from typing import Callable, Optional

from PySide6.QtCore import QMutex, QMutexLocker, QObject, Signal


class BaseDriver(QObject):
    """
    通信驱动基类
    Base class for communication drivers
    """

    # 信号定义
    data_received = Signal(bytes)
    data_sent = Signal(bytes)
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_connected = False
        self._buffer = bytearray()
        self._buffer_mutex = QMutex()

    def connect(self) -> bool:
        """
        连接设备
        Connect to device
        """
        raise NotImplementedError("子类必须实现connect方法")

    def disconnect(self):
        """
        断开连接
        Disconnect from device
        """
        raise NotImplementedError("子类必须实现disconnect方法")

    def send_data(self, data: bytes) -> bool:
        """
        发送数据
        Send data to device
        """
        raise NotImplementedError("子类必须实现send_data方法")

    def is_connected(self) -> bool:
        """
        检查连接状态
        Check connection status
        """
        return self._is_connected

    def _append_to_buffer(self, data: bytes):
        """
        追加数据到缓冲区
        Append data to buffer
        """
        locker = QMutexLocker(self._buffer_mutex)
        self._buffer.extend(data)

    def _clear_buffer(self):
        """
        清空缓冲区
        Clear buffer
        """
        locker = QMutexLocker(self._buffer_mutex)
        self._buffer.clear()

    def _get_buffer(self) -> bytes:
        """
        获取缓冲区数据
        Get buffer data
        """
        locker = QMutexLocker(self._buffer_mutex)
        return bytes(self._buffer)

    def _extract_from_buffer(self, length: int) -> Optional[bytes]:
        """
        从缓冲区提取指定长度的数据
        Extract data from buffer
        """
        locker = QMutexLocker(self._buffer_mutex)
        if len(self._buffer) >= length:
            data = bytes(self._buffer[:length])
            del self._buffer[:length]
            return data
        return None
