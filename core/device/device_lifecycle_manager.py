# -*- coding: utf-8 -*-
"""
设备生命周期管理器
Device Lifecycle Manager - extracted from DeviceManager
"""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING, Dict, Optional

from PySide6.QtCore import QTimer

from core.utils.logger import get_logger
from core.device.device_model import DeviceStatus

if TYPE_CHECKING:
    from .device_model import Device
    from .polling import DevicePollInfo

logger = get_logger(__name__)


class DeviceLifecycleManager:
    """设备生命周期管理器 - 管理连接/断开/重连逻辑"""

    def __init__(
        self,
        devices: Dict[str, "DevicePollInfo"],
        manually_disconnected: set,
        max_reconnect_attempts: int = 5,
        reconnect_interval: int = 5000,
    ) -> None:
        self._devices = devices
        self._manually_disconnected = manually_disconnected
        self._reconnect_timer = QTimer()
        self._reconnect_timer.timeout.connect(self._check_reconnect)
        self._reconnect_queue: deque = deque()
        self._reconnect_attempts: Dict[str, int] = {}
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_interval = reconnect_interval

    def start(self) -> None:
        self._reconnect_timer.start(self._reconnect_interval)

    def stop(self) -> None:
        try:
            self._reconnect_timer.stop()
        except RuntimeError:
            pass

    def schedule_reconnect(self, device_id: str) -> None:
        if device_id not in self._reconnect_queue:
            self._reconnect_queue.append(device_id)

    def check_reconnect(self) -> None:
        self._check_reconnect()

    def _check_reconnect(self) -> None:
        if not self._reconnect_queue:
            return

        device_id = self._reconnect_queue.popleft()

        if device_id not in self._devices:
            return

        device = self._devices[device_id].device

        if device.get_status() == DeviceStatus.CONNECTED:
            if device_id in self._reconnect_attempts:
                del self._reconnect_attempts[device_id]
            return

        attempts = self._reconnect_attempts.get(device_id, 0)
        if attempts >= self._max_reconnect_attempts:
            logger.error(
                "设备重连次数超过上限，停止重连",
                device_id=device_id,
                max_attempts=self._max_reconnect_attempts,
            )
            del self._reconnect_attempts[device_id]
            return

        attempts += 1
        self._reconnect_attempts[device_id] = attempts

        logger.info("尝试重连设备", device_id=device_id, attempt=attempts)

        try:
            success = device.connect()
            if success:
                logger.info("设备重连成功", device_id=device_id)
                poll_info = self._devices[device_id]
                poll_info.on_success()
                del self._reconnect_attempts[device_id]
            else:
                backoff = min(2**attempts, 60)
                QTimer.singleShot(backoff * 1000, lambda: self.schedule_reconnect(device_id))
        except Exception as e:
            logger.error("设备重连失败", device_id=device_id, error=str(e))
            self.schedule_reconnect(device_id)

    def should_auto_reconnect(self, device_id: str) -> bool:
        if device_id in self._manually_disconnected:
            return False
        poll_info = self._devices.get(device_id)
        return poll_info is not None and poll_info.auto_reconnect_enabled
