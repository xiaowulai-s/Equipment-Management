# -*- coding: utf-8 -*-
"""
报警数据仓库
Alarm Repository
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import Session

from ..models import AlarmModel
from .base import BaseRepository


class AlarmRepository(BaseRepository[AlarmModel]):
    """报警数据仓库"""

    def __init__(self, session: Session):
        super().__init__(session, AlarmModel)

    def get_by_device(self, device_id: str, limit: int = 100) -> List[AlarmModel]:
        """获取设备的报警记录"""
        return (
            self._session.query(AlarmModel)
            .filter(AlarmModel.device_id == device_id)
            .order_by(desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_level(self, level: int, limit: int = 100) -> List[AlarmModel]:
        """获取指定级别的报警"""
        return (
            self._session.query(AlarmModel)
            .filter(AlarmModel.level == level)
            .order_by(desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_unacknowledged(self, limit: int = 100) -> List[AlarmModel]:
        """获取未确认的报警"""
        return (
            self._session.query(AlarmModel)
            .filter(AlarmModel.acknowledged == False)
            .order_by(desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_time_range(
        self, start_time: datetime, end_time: datetime, device_id: Optional[str] = None
    ) -> List[AlarmModel]:
        """获取时间范围内的报警"""
        query = self._session.query(AlarmModel).filter(
            and_(AlarmModel.timestamp >= start_time, AlarmModel.timestamp <= end_time)
        )

        if device_id:
            query = query.filter(AlarmModel.device_id == device_id)

        return query.order_by(desc(AlarmModel.timestamp)).all()

    def acknowledge_alarm(self, alarm_id: int, acknowledged_by: str = "system") -> Optional[AlarmModel]:
        """确认报警"""
        alarm = self.get_by_id(alarm_id)
        if alarm:
            alarm.acknowledged = True
            alarm.acknowledged_at = datetime.utcnow()
            alarm.acknowledged_by = acknowledged_by
            return self.update(alarm)
        return None

    def acknowledge_all_by_device(self, device_id: str, acknowledged_by: str = "system") -> int:
        """确认设备的所有未确认报警"""
        alarms = (
            self._session.query(AlarmModel)
            .filter(and_(AlarmModel.device_id == device_id, AlarmModel.acknowledged == False))
            .all()
        )

        count = 0
        now = datetime.utcnow()
        for alarm in alarms:
            alarm.acknowledged = True
            alarm.acknowledged_at = now
            alarm.acknowledged_by = acknowledged_by
            count += 1

        self._session.flush()
        return count

    def create_alarm(
        self,
        rule_id: str,
        device_id: str,
        device_name: str,
        parameter: str,
        alarm_type: str,
        level: int,
        value: float,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        description: str = "",
    ) -> AlarmModel:
        """创建报警记录"""
        alarm = AlarmModel(
            rule_id=rule_id,
            device_id=device_id,
            device_name=device_name,
            parameter=parameter,
            alarm_type=alarm_type,
            level=level,
            value=value,
            threshold_high=threshold_high,
            threshold_low=threshold_low,
            description=description,
        )
        return self.create(alarm)

    def get_alarm_statistics(
        self, start_time: datetime, end_time: datetime, device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取报警统计"""
        query = self._session.query(AlarmModel).filter(
            and_(AlarmModel.timestamp >= start_time, AlarmModel.timestamp <= end_time)
        )

        if device_id:
            query = query.filter(AlarmModel.device_id == device_id)

        total = query.count()

        # 按级别统计
        level_counts = {}
        for level in [0, 1, 2]:
            count = query.filter(AlarmModel.level == level).count()
            level_counts[level] = count

        # 未确认数量
        unacknowledged = query.filter(AlarmModel.acknowledged == False).count()

        return {
            "total": total,
            "level_counts": level_counts,
            "unacknowledged": unacknowledged,
            "acknowledged": total - unacknowledged,
        }

    def get_active_alarms(self, limit: int = 100) -> List[AlarmModel]:
        """获取当前活动报警（最近24小时内未确认的）"""
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        return (
            self._session.query(AlarmModel)
            .filter(and_(AlarmModel.timestamp >= one_day_ago, AlarmModel.acknowledged == False))
            .order_by(desc(AlarmModel.level), desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def cleanup_old_alarms(self, days: int = 90) -> int:
        """清理过期报警记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = (
            self._session.query(AlarmModel).filter(AlarmModel.timestamp < cutoff_date).delete(synchronize_session=False)
        )
        return result
