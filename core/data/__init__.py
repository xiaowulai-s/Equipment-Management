# -*- coding: utf-8 -*-
"""
数据层模块
Data Layer Module
"""

from .alarm_rule_persistence import AlarmRulePersistenceManager
from .device_status_sync import DeviceStatusSynchronizer
from .historical_recorder import HistoricalDataRecorder
from .models import (
    AlarmModel,
    AlarmRuleModel,
    Base,
    DatabaseManager,
    DeviceModel,
    HistoricalDataModel,
    RegisterMapModel,
    SystemLogModel,
    get_db_manager,
    init_database,
)
from .repository.alarm_repository import AlarmRepository
from .repository.alarm_rule_repository import AlarmRuleRepository
from .repository.base import BaseRepository
from .repository.device_repository import DeviceRepository
from .repository.historical_repository import HistoricalDataRepository

__all__ = [
    # Models
    "Base",
    "DeviceModel",
    "RegisterMapModel",
    "HistoricalDataModel",
    "AlarmModel",
    "SystemLogModel",
    "AlarmRuleModel",
    "DatabaseManager",
    "get_db_manager",
    "init_database",
    # Repositories
    "BaseRepository",
    "DeviceRepository",
    "HistoricalDataRepository",
    "AlarmRepository",
    "AlarmRuleRepository",
    # Managers
    "HistoricalDataRecorder",
    "AlarmRulePersistenceManager",
    "DeviceStatusSynchronizer",
]
