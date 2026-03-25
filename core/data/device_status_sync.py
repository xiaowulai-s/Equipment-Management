# -*- coding: utf-8 -*-
"""
设备状态同步器
Device Status Synchronizer
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.device.device_model import DeviceStatus
from core.utils.logger import get_logger

from .models import DatabaseManager
from .repository.device_repository import DeviceRepository

logger = get_logger(__name__)


class DeviceStatusSynchronizer:
    """设备状态同步器 - 负责将设备状态同步到数据库"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化设备状态同步器

        Args:
            db_manager: 数据库管理器实例
        """
        self._db_manager = db_manager
        self._repository: Optional[DeviceRepository] = None
        self._auto_sync = True  # 自动同步
        self._sync_interval = 5  # 同步间隔（秒）
        self._last_sync: Dict[str, datetime] = {}  # 最后同步时间

    @property
    def auto_sync(self) -> bool:
        """是否启用自动同步"""
        return self._auto_sync

    @auto_sync.setter
    def auto_sync(self, value: bool):
        self._auto_sync = value

    @property
    def sync_interval(self) -> int:
        """同步间隔（秒）"""
        return self._sync_interval

    @sync_interval.setter
    def sync_interval(self, value: int):
        self._sync_interval = max(1, value)  # 最小 1 秒

    def _get_repository(self) -> DeviceRepository:
        """获取数据仓库实例"""
        if self._repository is None:
            session = self._db_manager.get_session()
            self._repository = DeviceRepository(session)
        return self._repository

    def sync_status(self, device_id: str, status: DeviceStatus) -> bool:
        """
        同步设备状态到数据库

        Args:
            device_id: 设备 ID
            status: 设备状态

        Returns:
            bool: 同步成功返回 True
        """
        if not self._auto_sync:
            return False

        try:
            # 检查同步频率
            now = datetime.utcnow()
            last_sync = self._last_sync.get(device_id)

            if last_sync and (now - last_sync).total_seconds() < self._sync_interval:
                # 距离上次同步时间太短，跳过
                return False

            repo = self._get_repository()
            device = repo.get_by_id(device_id)

            if not device:
                logger.warning(f"设备 {device_id} 不存在，无法同步状态")
                return False

            # 更新状态字段（需要先在 DeviceModel 中添加 status 字段）
            # 由于 DeviceModel 目前没有 status 字段，我们使用扩展字段方式
            # 在实际项目中，建议在 DeviceModel 中添加 status 字段

            # 这里我们通过更新 updated_at 来标记状态变化
            device.updated_at = now

            # 如果需要，可以添加自定义字段存储状态
            # 这需要在 DeviceModel 中添加额外的列或使用 JSON 字段

            repo.update(device)
            self._last_sync[device_id] = now

            logger.debug(f"设备 {device_id} 状态已同步：{status.name}")
            return True

        except Exception as e:
            logger.error(f"同步设备状态失败：{str(e)}")
            return False

    def sync_connection_info(
        self, device_id: str, last_connected: Optional[datetime] = None, connection_count: int = 0, error_count: int = 0
    ) -> bool:
        """
        同步设备连接信息

        Args:
            device_id: 设备 ID
            last_connected: 最后连接时间
            connection_count: 连接次数
            error_count: 错误次数

        Returns:
            bool: 同步成功返回 True
        """
        try:
            repo = self._get_repository()
            device = repo.get_by_id(device_id)

            if not device:
                return False

            # 更新连接信息
            # 注意：这需要在 DeviceModel 中添加相应字段
            # 如：last_connected_at, connection_count, error_count

            device.updated_at = datetime.utcnow()
            repo.update(device)

            logger.debug(f"设备 {device_id} 连接信息已同步")
            return True

        except Exception as e:
            logger.error(f"同步设备连接信息失败：{str(e)}")
            return False

    def sync_device_data(self, device_id: str, data: Dict[str, Any]) -> bool:
        """
        同步设备数据到数据库

        Args:
            device_id: 设备 ID
            data: 设备数据字典

        Returns:
            bool: 同步成功返回 True
        """
        try:
            repo = self._get_repository()
            device = repo.get_by_id(device_id)

            if not device:
                return False

            # 更新设备数据
            # 可以在 DeviceModel 中添加 JSON 字段存储最新数据
            # 或者使用单独的表存储

            device.updated_at = datetime.utcnow()
            repo.update(device)

            logger.debug(f"设备 {device_id} 数据已同步")
            return True

        except Exception as e:
            logger.error(f"同步设备数据失败：{str(e)}")
            return False

    def record_connection_event(
        self, device_id: str, event_type: str, message: str = ""  # 'connected', 'disconnected', 'error'
    ) -> bool:
        """
        记录设备连接事件

        Args:
            device_id: 设备 ID
            event_type: 事件类型
            message: 事件描述

        Returns:
            bool: 记录成功返回 True
        """
        try:
            # 这里可以创建一个 DeviceEventModel 来记录事件
            # 或者使用 SystemLogModel

            logger.info(f"设备 {device_id} {event_type}: {message}")
            return True

        except Exception as e:
            logger.error(f"记录设备事件失败：{str(e)}")
            return False

    def get_device_status_history(self, device_id: str, start_time: datetime, end_time: datetime) -> list:
        """
        获取设备状态历史

        Args:
            device_id: 设备 ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            list: 状态历史列表
        """
        try:
            # 这需要创建 DeviceStatusHistoryModel
            # 目前返回空列表
            return []

        except Exception as e:
            logger.error(f"获取设备状态历史失败：{str(e)}")
            return []

    def cleanup_old_events(self, days: int = 30) -> int:
        """
        清理过期事件记录

        Args:
            days: 保留天数

        Returns:
            int: 清理的记录数
        """
        try:
            # 这需要 DeviceEventModel 支持
            return 0

        except Exception as e:
            logger.error(f"清理过期事件失败：{str(e)}")
            return 0

    def close(self):
        """关闭同步器，释放资源"""
        try:
            if self._repository:
                self._repository._session.close()
                self._repository = None
            logger.info("设备状态同步器已关闭")
        except Exception as e:
            logger.error(f"关闭同步器失败：{str(e)}")
