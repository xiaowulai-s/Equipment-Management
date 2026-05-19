# -*- coding: utf-8 -*-
"""
串口通信驱动 (v2.1 线程安全版)
Serial Communication Driver

P0修复: 解决串口多线程竞态问题

问题:
- connect()/disconnect()/_receive_loop() 之间无锁保护
- disconnect 关闭串口时 receive_loop 正在读写

解决方案:
1. RLock 保护所有共享状态
2. 先标记停止再关闭资源（类TCPDriver模式）
3. 所有异常路径保证状态一致性
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
    串口通信驱动 (v2.1 线程安全版)

    线程安全: ✅ RLock 保护所有共享状态
    竞态安全: ✅ 先标记停止、再关闭资源、再等待线程
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
        self._lock = threading.RLock()

        if not SERIAL_AVAILABLE:
            QTimer.singleShot(0, lambda: self.error_occurred.emit("pyserial未安装，串口功能不可用"))

    def connect(self) -> bool:
        """连接设备（线程安全）"""
        if not SERIAL_AVAILABLE:
            self.error_occurred.emit("pyserial未安装，请先安装: pip install pyserial")
            return False

        with self._lock:
            # 预清理：确保无残留资源
            self._safe_cleanup()

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

                self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                self._receive_thread.start()

                self.connected.emit()
                return True
            except Exception as e:
                self._safe_cleanup()
                self.error_occurred.emit(f"串口连接失败: {str(e)}")
                return False

    def disconnect(self):
        """断开连接（线程安全）"""
        # 先标记停止（让 receive_loop 自然退出）
        with self._lock:
            self._is_running = False

        # 强制关闭串口（阻塞 receive_loop 中的 IO）
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
            self._is_connected = False

        # 等待接收线程退出（锁外等待，避免死锁）
        receive_thread = self._receive_thread
        if receive_thread and receive_thread.is_alive():
            receive_thread.join(timeout=2.0)
            if receive_thread.is_alive():
                import logging

                logging.getLogger(__name__).warning("串口接收线程未能在超时内退出")
        with self._lock:
            self._receive_thread = None

        self._clear_buffer()
        self.disconnected.emit()

    def send_data(self, data: bytes) -> bool:
        """发送数据（线程安全）"""
        with self._lock:
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

    def _safe_cleanup(self) -> None:
        """安全清理资源（必须在持锁状态下调用）"""
        self._is_running = False
        self._is_connected = False
        if self._serial is not None:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except Exception:
                pass
            self._serial = None

    def _receive_loop(self):
        """接收循环（仅在启动时持锁获取引用，运行时无锁避免死锁）"""
        # 获取 serial 引用的本地副本
        with self._lock:
            local_serial = self._serial

        while local_serial and local_serial.is_open:
            # 检查运行标志（volatile 读取，不要求精确性）
            if not self._is_running:
                break

            try:
                if local_serial.in_waiting > 0:
                    data = local_serial.read(local_serial.in_waiting)
                    if data:
                        self._append_to_buffer(data)
                        self.data_received.emit(data)
            except Exception:
                # 连接丢失或串口已关闭，正常退出循环
                break

    def set_port(self, port: str):
        """设置端口"""
        with self._lock:
            self._port = port

    def set_baudrate(self, baudrate: int):
        """设置波特率"""
        with self._lock:
            self._baudrate = baudrate

    def set_bytesize(self, bytesize: int):
        """设置数据位"""
        with self._lock:
            self._bytesize = bytesize

    def set_parity(self, parity: str):
        """设置校验位"""
        with self._lock:
            self._parity = parity

    def set_stopbits(self, stopbits: float):
        """设置停止位"""
        with self._lock:
            self._stopbits = stopbits
