# -*- coding: utf-8 -*-
"""Helpers for syncing runtime device state into persistent storage.

Features:
    - Device status synchronization
    - Connection info tracking
    - Status change history recording
    - Old event cleanup
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.utils.logger import get_logger

from .models import DatabaseManager, DeviceStatusHistoryModel, utc_now
from .repository.device_repository import DeviceRepository

if TYPE_CHECKING:
    from core.device.device_model import DeviceStatus

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

    def record_status_change(
        self,
        device_id: str,
        status: str,
        status_code: Optional[int] = None,
        message: Optional[str] = None,
        ip_address: Optional[str] = None,
        port: Optional[int] = None,
    ) -> bool:
        """记录设备状态变化到历史表"""
        try:
            session = self._db_manager.get_session()
            history_record = DeviceStatusHistoryModel(
                device_id=device_id,
                status=status,
                status_code=status_code,
                message=message,
                ip_address=ip_address,
                port=port,
            )
            session.add(history_record)
            session.commit()
            logger.debug("设备 %s 状态变化已记录: %s", device_id, status)
            return True
        except Exception:
            logger.exception("记录设备状态变化失败: %s", device_id)
            return False

    def get_device_status_history(
        self,
        device_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """查询设备状态历史

        Args:
            device_id: 设备ID，为None则查询所有设备
            start_time: 开始时间，为None则不限制
            end_time: 结束时间，为None则不限制
            status: 状态过滤，为None则不限制
            limit: 最大返回记录数

        Returns:
            状态历史记录列表
        """
        try:
            from sqlalchemy import desc

            session = self._db_manager.get_session()
            query = session.query(DeviceStatusHistoryModel)

            if device_id:
                query = query.filter(DeviceStatusHistoryModel.device_id == device_id)
            if start_time:
                query = query.filter(DeviceStatusHistoryModel.timestamp >= start_time)
            if end_time:
                query = query.filter(DeviceStatusHistoryModel.timestamp <= end_time)
            if status:
                query = query.filter(DeviceStatusHistoryModel.status == status)

            records = query.order_by(desc(DeviceStatusHistoryModel.timestamp)).limit(limit).all()

            result = [record.to_dict() for record in records]
            logger.debug("查询到 %d 条状态历史记录", len(result))
            return result
        except Exception:
            logger.exception("查询设备状态历史失败")
            return []

    def cleanup_old_events(self, days: int = 30) -> int:
        """清理旧的状态历史记录

        Args:
            days: 保留最近几天的记录，默认30天

        Returns:
            删除的记录数
        """
        try:
            from sqlalchemy import delete

            session = self._db_manager.get_session()
            cutoff_time = utc_now() - timedelta(days=days)

            result = session.execute(
                delete(DeviceStatusHistoryModel).where(DeviceStatusHistoryModel.timestamp < cutoff_time)
            )
            session.commit()
            deleted_count = result.rowcount
            logger.info("清理了 %d 条 %d 天前的状态历史记录", deleted_count, days)
            return deleted_count
        except Exception:
            logger.exception("清理旧状态历史记录失败")
            return 0

    def get_device_status_statistics(
        self,
        device_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """获取设备状态统计信息

        Args:
            device_id: 设备ID
            days: 统计最近几天的数据

        Returns:
            统计信息字典
        """
        try:
            from sqlalchemy import func

            session = self._db_manager.get_session()
            start_time = utc_now() - timedelta(days=days)

            stats = (
                session.query(
                    DeviceStatusHistoryModel.status,
                    func.count(DeviceStatusHistoryModel.id).label("count"),
                )
                .filter(
                    DeviceStatusHistoryModel.device_id == device_id,
                    DeviceStatusHistoryModel.timestamp >= start_time,
                )
                .group_by(DeviceStatusHistoryModel.status)
                .all()
            )

            total = sum(s.count for s in stats)
            status_distribution = {s.status: s.count for s in stats}

            return {
                "device_id": device_id,
                "days": days,
                "total_records": total,
                "status_distribution": status_distribution,
                "start_time": start_time.isoformat(),
                "end_time": utc_now().isoformat(),
            }
        except Exception:
            logger.exception("获取设备状态统计失败: %s", device_id)
            return {}

    def close(self) -> None:
        """Release the cached repository session."""
        if self._repository is not None:
            self._repository._session.close()
            self._repository = None
        logger.info("设备状态同步器已关闭")
