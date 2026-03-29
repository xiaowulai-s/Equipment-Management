"""
Repository模式 - 数据访问抽象层

所有仓库继承BaseRepository，实现统一的CRUD接口。
"""

from .alarm_repository import AlarmRecordRepository, AlarmRuleRepository
from .base import BaseRepository
from .device_repository import DeviceRepository
from .historical_repository import HistoricalDataRepository

__all__ = [
    "BaseRepository",
    "DeviceRepository",
    "HistoricalDataRepository",
    "AlarmRecordRepository",
    "AlarmRuleRepository",
]
