"""
数据持久化层 - SQLite数据库 + Repository模式

包含:
    - database: 数据库连接管理器 (DatabaseManager, Base, utc_now)
    - models: ORM模型 (Device/Register/History/Alarm/AlarmRule/SystemLog)
    - repository/: 数据仓库
        - BaseRepository: 泛型CRUD基类
        - DeviceRepository: 设备仓库 (运行时模型双向转换)
        - HistoricalDataRepository: 历史数据仓库
        - AlarmRecordRepository: 报警记录仓库
        - AlarmRuleRepository: 报警规则仓库
"""

from .database import Base, DatabaseManager, get_db_manager, init_database, utc_now
from .models import AlarmRecordModel, AlarmRuleModel, DeviceModel, HistoricalDataModel, RegisterMapModel, SystemLogModel
from .repository.alarm_repository import AlarmRecordRepository, AlarmRuleRepository
from .repository.base import BaseRepository
from .repository.device_repository import DeviceRepository
from .repository.historical_repository import HistoricalDataRepository

__all__ = [
    # 数据库
    "Base",
    "DatabaseManager",
    "get_db_manager",
    "init_database",
    "utc_now",
    # ORM模型
    "DeviceModel",
    "RegisterMapModel",
    "HistoricalDataModel",
    "AlarmRecordModel",
    "AlarmRuleModel",
    "SystemLogModel",
    # Repository
    "BaseRepository",
    "DeviceRepository",
    "HistoricalDataRepository",
    "AlarmRecordRepository",
    "AlarmRuleRepository",
]
