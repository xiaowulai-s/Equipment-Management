# -*- coding: utf-8 -*-
"""Helpers for syncing runtime device state into persistent storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from core.device.device_model import DeviceStatus
from core.utils.logger import get_logger

from .models import DatabaseManager, utc_now
from .repository.device_repository import DeviceRepository

logger = get_logger(__name__)


class DeviceStatusSynchronizer:
    """Synchronize runtime device state with persistent device records."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db_manager = db_manager
        self._repository: Optional[DeviceRepository] = None
        self._auto_sync = True
        self._sync_interval = 5
        self._last_sync: Dict[str, datetime] = {}

    @property
    def auto_sync(self) -> bool:
        """Return whether automatic sync is enabled."""
        return self._auto_sync

    @auto_sync.setter
    def auto_sync(self, value: bool) -> None:
        self._auto_sync = value

    @property
    def sync_interval(self) -> int:
        """Return the minimum number of seconds between syncs."""
        return self._sync_interval

    @sync_interval.setter
    def sync_interval(self, value: int) -> None:
        self._sync_interval = max(1, value)

    def _get_repository(self) -> DeviceRepository:
        """Return a lazily created repository instance."""
        if self._repository is None:
            self._repository = DeviceRepository(self._db_manager.get_session())
        return self._repository

    def sync_status(self, device_id: str, status: DeviceStatus) -> bool:
        """Sync one runtime device status marker."""
        if not self._auto_sync:
            return False

        now = utc_now()
        last_sync = self._last_sync.get(device_id)
        if last_sync and (now - last_sync).total_seconds() < self._sync_interval:
            return False

        try:
            repo = self._get_repository()
            device = repo.get_by_id(device_id)
            if device is None:
                logger.warning("设备 %s 不存在，无法同步状态", device_id)
                return False

            device.updated_at = now
            repo.update(device)
            self._last_sync[device_id] = now
            logger.debug("设备 %s 状态已同步: %s", device_id, status.name)
            return True
        except Exception:
            logger.exception("同步设备状态失败: %s", device_id)
            return False

    def sync_connection_info(
        self, device_id: str, last_connected: Optional[datetime] = None, connection_count: int = 0, error_count: int = 0
    ) -> bool:
        """Sync connection-related fields for one device."""
        try:
            repo = self._get_repository()
            device = repo.get_by_id(device_id)
            if device is None:
                return False

            device.last_connected_at = last_connected
            device.connection_count = connection_count
            device.error_count = error_count
            device.updated_at = utc_now()
            repo.update(device)
            logger.debug("设备 %s 连接信息已同步", device_id)
            return True
        except Exception:
            logger.exception("同步设备连接信息失败: %s", device_id)
            return False

    def sync_device_data(self, device_id: str, data: Dict[str, Any]) -> bool:
        """Record that fresh device data was received."""
        try:
            repo = self._get_repository()
            device = repo.get_by_id(device_id)
            if device is None:
                return False

            device.updated_at = utc_now()
            repo.update(device)
            logger.debug("设备 %s 数据已同步，字段数=%s", device_id, len(data))
            return True
        except Exception:
            logger.exception("同步设备数据失败: %s", device_id)
            return False

    def record_connection_event(self, device_id: str, event_type: str, message: str = "") -> bool:
        """Record one device connection event in logs."""
        try:
            logger.info("设备 %s %s: %s", device_id, event_type, message)
            return True
        except Exception:
            logger.exception("记录设备事件失败: %s", device_id)
            return False

    def get_device_status_history(self, device_id: str, start_time: datetime, end_time: datetime) -> list:
        """Placeholder for a future status history persistence model."""
        logger.debug("状态历史尚未实现: %s %s %s", device_id, start_time, end_time)
        return []

    def cleanup_old_events(self, days: int = 30) -> int:
        """Placeholder for future event cleanup support."""
        logger.debug("事件清理尚未实现，days=%s", days)
        return 0

    def close(self) -> None:
        """Release the cached repository session."""
        if self._repository is not None:
            self._repository._session.close()
            self._repository = None
        logger.info("设备状态同步器已关闭")
