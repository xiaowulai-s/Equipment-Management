# -*- coding: utf-8 -*-
"""
数据仓库模块
Repository Module
"""

from .alarm_repository import AlarmRepository
from .base import BaseRepository
from .device_repository import DeviceRepository
from .historical_repository import HistoricalDataRepository

__all__ = [
    "BaseRepository",
    "DeviceRepository",
    "HistoricalDataRepository",
    "AlarmRepository",
]
