# -*- coding: utf-8 -*-
"""
DeviceController — 通用设备控制器

职责:
1. 封装 DeviceManagerFacade 的异步操作
2. 通过 QThreadPool 将设备连接/断开/轮询放入工作线程
3. 通过 Signal 中转结果给 MainWindow
4. 管理 DataBus 订阅
5. 提供命令终端的原始数据收发（不暴露 Driver 给 UI）

设计原则:
- Controller 层只负责异步调度和 Signal 中转
- 不包含业务逻辑
- 不直接操作 UI 控件
- 可与 MCGSController 并行使用
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from core.foundation.data_bus import DataBus

logger = logging.getLogger(__name__)


class _DeviceConnectTask(QRunnable):
    """异步设备连接任务"""

    class Signals(QObject):
        finished = Signal(str, bool, str)

    def __init__(self, device_manager, device_id: str):
        super().__init__()
        self.device_manager = device_manager
        self.device_id = device_id
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self):
        try:
            success = self.device_manager.connect_device(self.device_id)
            msg = "连接成功" if success else "连接失败"
            self.signals.finished.emit(self.device_id, success, msg)
        except Exception as e:
            self.signals.finished.emit(self.device_id, False, str(e))


class _DeviceDisconnectTask(QRunnable):
    """异步设备断开任务"""

    class Signals(QObject):
        finished = Signal(str, bool, str)

    def __init__(self, device_manager, device_id: str):
        super().__init__()
        self.device_manager = device_manager
        self.device_id = device_id
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self):
        try:
            self.device_manager.disconnect_device(self.device_id)
            self.signals.finished.emit(self.device_id, True, "已断开")
        except Exception as e:
            self.signals.finished.emit(self.device_id, False, str(e))


class _RawSendTask(QRunnable):
    """异步原始数据发送任务"""

    class Signals(QObject):
        finished = Signal(str, bool, str)

    def __init__(self, device_manager, device_id: str, data: bytes):
        super().__init__()
        self.device_manager = device_manager
        self.device_id = device_id
        self.data = data
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self):
        try:
            device = self.device_manager.get_device(self.device_id)
            if not device:
                self.signals.finished.emit(self.device_id, False, "Device not found")
                return
            success = device.send_raw_data(self.data)
            msg = "" if success else "Send failed"
            self.signals.finished.emit(self.device_id, success, msg)
        except Exception as e:
            self.signals.finished.emit(self.device_id, False, str(e))


class DeviceController(QObject):
    """
    通用设备控制器

    使用方式:
        controller = DeviceController(device_manager, parent=self)
        controller.connect_device("device_1")

        # 连接信号
        controller.device_connected.connect(self._on_device_connected)
        controller.device_disconnected.connect(self._on_device_disconnected)
        controller.device_error.connect(self._on_device_error)
    """

    device_connected = Signal(str, bool, str)
    device_disconnected = Signal(str, bool, str)
    device_error = Signal(str, str)
    device_status_changed = Signal(str, str)

    raw_data_received = Signal(str, bytes)
    raw_send_result = Signal(str, bool, str)

    def __init__(
        self,
        device_manager=None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self._device_manager = device_manager
        self._connect_data_bus()

    def _connect_data_bus(self):
        bus = DataBus.instance()
        bus.subscribe("device_status_changed", self._on_bus_status_changed)
        bus.subscribe("comm_error", self._on_bus_comm_error)
        bus.subscribe("device_data_updated", self._on_bus_data_updated)

    @property
    def device_manager(self):
        return self._device_manager

    def set_device_manager(self, device_manager):
        self._device_manager = device_manager

    def connect_device(self, device_id: str):
        if self._device_manager is None:
            self.device_error.emit(device_id, "设备管理器未初始化")
            return

        task = _DeviceConnectTask(self._device_manager, device_id)
        task.signals.finished.connect(self._on_connect_finished)
        self._start_task(task)

    def disconnect_device(self, device_id: str):
        if self._device_manager is None:
            self.device_error.emit(device_id, "设备管理器未初始化")
            return

        task = _DeviceDisconnectTask(self._device_manager, device_id)
        task.signals.finished.connect(self._on_disconnect_finished)
        self._start_task(task)

    def send_raw_command(self, device_id: str, data: bytes):
        if self._device_manager is None:
            self.raw_send_result.emit(device_id, False, "设备管理器未初始化")
            return

        task = _RawSendTask(self._device_manager, device_id, data)
        task.signals.finished.connect(self._on_raw_send_finished)
        self._start_task(task)

    def get_device_list(self) -> List[Dict]:
        if self._device_manager is None:
            return []
        return self._device_manager.get_all_devices()

    def is_device_connected(self, device_id: str) -> bool:
        if self._device_manager is None:
            return False
        device = self._device_manager.get_device(device_id)
        if device is None:
            return False
        return device.get_status() == 2  # DeviceStatus.CONNECTED

    def _start_task(self, task: QRunnable):
        from PySide6.QtCore import QThreadPool

        QThreadPool.globalInstance().start(task)

    @Slot(str, bool, str)
    def _on_connect_finished(self, device_id: str, success: bool, msg: str):
        self.device_connected.emit(device_id, success, msg)

    @Slot(str, bool, str)
    def _on_disconnect_finished(self, device_id: str, success: bool, msg: str):
        self.device_disconnected.emit(device_id, success, msg)

    @Slot(str, bool, str)
    def _on_raw_send_finished(self, device_id: str, success: bool, msg: str):
        self.raw_send_result.emit(device_id, success, msg)

    @Slot(str, str)
    def _on_bus_status_changed(self, device_id: str, status: str):
        self.device_status_changed.emit(device_id, status)

    @Slot(str, str)
    def _on_bus_comm_error(self, device_id: str, error_msg: str):
        self.device_error.emit(device_id, error_msg)

    @Slot(str, dict)
    def _on_bus_data_updated(self, device_id: str, data: dict):
        pass

    def export_data(self, export_data: list, file_path: str, format: str = "csv") -> bool:
        from core.utils.data_exporter import DataExporter

        if format == "csv":
            return DataExporter.export_to_csv(export_data, file_path)
        elif format == "excel":
            return DataExporter.export_to_excel(export_data, file_path)
        elif format == "json":
            return DataExporter.export_to_json(export_data, file_path)
        return False

    @staticmethod
    def format_undo_value(value) -> str:
        from core.utils.operation_undo_manager import UndoRecord

        return UndoRecord._format_value(value)

    def cleanup(self):
        logger.info("DeviceController 已清理")
