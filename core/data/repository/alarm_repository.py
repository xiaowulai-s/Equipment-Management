# -*- coding: utf-8 -*-
"""Alarm repository helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..models import AlarmModel, utc_now
from .base import BaseRepository


class AlarmRepository(BaseRepository[AlarmModel]):
    """Repository for persisted alarm records."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AlarmModel)

    def get_by_device(self, device_id: str, limit: int = 100) -> List[AlarmModel]:
        """Return recent alarms for one device."""
        return (
            self._session.query(AlarmModel)
            .filter(AlarmModel.device_id == device_id)
            .order_by(desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_level(self, level: int, limit: int = 100) -> List[AlarmModel]:
        """Return recent alarms for one severity level."""
        return (
            self._session.query(AlarmModel)
            .filter(AlarmModel.level == level)
            .order_by(desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_unacknowledged(self, limit: int = 100) -> List[AlarmModel]:
        """Return recent unacknowledged alarms."""
        return (
            self._session.query(AlarmModel)
            .filter(AlarmModel.acknowledged.is_(False))
            .order_by(desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_time_range(
        self, start_time: datetime, end_time: datetime, device_id: Optional[str] = None
    ) -> List[AlarmModel]:
        """Return alarms within one time range."""
        query = self._session.query(AlarmModel).filter(
            and_(AlarmModel.timestamp >= start_time, AlarmModel.timestamp <= end_time)
        )
        if device_id:
            query = query.filter(AlarmModel.device_id == device_id)
        return query.order_by(desc(AlarmModel.timestamp)).all()

    def acknowledge_alarm(self, alarm_id: int, acknowledged_by: str = "system") -> Optional[AlarmModel]:
        """Acknowledge one alarm record."""
        alarm = self.get_by_id(alarm_id)
        if alarm is None:
            return None

        alarm.acknowledged = True
        alarm.acknowledged_at = utc_now()
        alarm.acknowledged_by = acknowledged_by
        return self.update(alarm)

    def acknowledge_all_by_device(self, device_id: str, acknowledged_by: str = "system") -> int:
        """Acknowledge all outstanding alarms for one device."""
        alarms = (
            self._session.query(AlarmModel)
            .filter(and_(AlarmModel.device_id == device_id, AlarmModel.acknowledged.is_(False)))
            .all()
        )

        count = 0
        acknowledged_at = utc_now()
        for alarm in alarms:
            alarm.acknowledged = True
            alarm.acknowledged_at = acknowledged_at
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
        """Create and persist one alarm record."""
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
        """Return aggregate alarm statistics for one time range."""
        query = self._session.query(AlarmModel).filter(
            and_(AlarmModel.timestamp >= start_time, AlarmModel.timestamp <= end_time)
        )
        if device_id:
            query = query.filter(AlarmModel.device_id == device_id)

        total = query.count()
        level_counts = {level: query.filter(AlarmModel.level == level).count() for level in range(4)}
        unacknowledged = query.filter(AlarmModel.acknowledged.is_(False)).count()
        return {
            "total": total,
            "level_counts": level_counts,
            "unacknowledged": unacknowledged,
            "acknowledged": total - unacknowledged,
        }

    def get_active_alarms(self, limit: int = 100) -> List[AlarmModel]:
        """Return alarms from the last 24 hours that are still unacknowledged."""
        cutoff = utc_now() - timedelta(hours=24)
        return (
            self._session.query(AlarmModel)
            .filter(and_(AlarmModel.timestamp >= cutoff, AlarmModel.acknowledged.is_(False)))
            .order_by(desc(AlarmModel.level), desc(AlarmModel.timestamp))
            .limit(limit)
            .all()
        )

    def cleanup_old_alarms(self, days: int = 90) -> int:
        """Delete alarms older than the retention window."""
        cutoff = utc_now() - timedelta(days=days)
        return self._session.query(AlarmModel).filter(AlarmModel.timestamp < cutoff).delete(synchronize_session=False)
