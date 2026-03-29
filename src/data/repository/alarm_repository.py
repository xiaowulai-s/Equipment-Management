"""
报警记录仓库 + 报警规则仓库

提供报警的持久化、查询、确认和清理。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from ..models import AlarmRecordModel, AlarmRuleModel, DeviceModel, utc_now
from .base import BaseRepository


class AlarmRecordRepository(BaseRepository[AlarmRecordModel]):
    """报警记录仓库"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AlarmRecordModel)

    def get_by_device(self, device_id: str, limit: int = 100) -> List[AlarmRecordModel]:
        return (
            self._session.query(AlarmRecordModel)
            .filter(AlarmRecordModel.device_id == device_id)
            .order_by(desc(AlarmRecordModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_level(self, level: int, limit: int = 100) -> List[AlarmRecordModel]:
        return (
            self._session.query(AlarmRecordModel)
            .filter(AlarmRecordModel.level == level)
            .order_by(desc(AlarmRecordModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_unacknowledged(self, limit: int = 100) -> List[AlarmRecordModel]:
        return (
            self._session.query(AlarmRecordModel)
            .filter(AlarmRecordModel.acknowledged.is_(False))
            .order_by(desc(AlarmRecordModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_time_range(
        self,
        start: datetime,
        end: datetime,
        device_id: Optional[str] = None,
    ) -> List[AlarmRecordModel]:
        query = self._session.query(AlarmRecordModel).filter(
            and_(
                AlarmRecordModel.timestamp >= start,
                AlarmRecordModel.timestamp <= end,
            )
        )
        if device_id:
            query = query.filter(AlarmRecordModel.device_id == device_id)
        return query.order_by(desc(AlarmRecordModel.timestamp)).all()

    def acknowledge(self, alarm_id: int, by: str = "system") -> Optional[AlarmRecordModel]:
        """确认报警"""
        alarm = self.get_by_id(alarm_id)
        if alarm is None:
            return None
        alarm.acknowledged = True
        alarm.acknowledged_at = utc_now()
        alarm.acknowledged_by = by
        return self.update(alarm)

    def acknowledge_all_by_device(self, device_id: str, by: str = "system") -> int:
        """批量确认设备报警"""
        alarms = (
            self._session.query(AlarmRecordModel)
            .filter(
                and_(
                    AlarmRecordModel.device_id == device_id,
                    AlarmRecordModel.acknowledged.is_(False),
                )
            )
            .all()
        )
        count = 0
        now = utc_now()
        for alarm in alarms:
            alarm.acknowledged = True
            alarm.acknowledged_at = now
            alarm.acknowledged_by = by
            count += 1
        self._session.flush()
        return count

    def create_record(
        self,
        rule_id: str,
        device_id: str,
        device_name: str,
        register_name: str,
        alarm_type: str,
        level: int,
        value: float,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        description: str = "",
    ) -> AlarmRecordModel:
        """创建报警记录"""
        return self.create(
            AlarmRecordModel(
                rule_id=rule_id,
                device_id=device_id,
                device_name=device_name,
                register_name=register_name,
                alarm_type=alarm_type,
                level=level,
                value=value,
                threshold_high=threshold_high,
                threshold_low=threshold_low,
                description=description,
            )
        )

    def get_statistics(
        self,
        start: datetime,
        end: datetime,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """报警统计"""
        query = self._session.query(AlarmRecordModel).filter(
            and_(
                AlarmRecordModel.timestamp >= start,
                AlarmRecordModel.timestamp <= end,
            )
        )
        if device_id:
            query = query.filter(AlarmRecordModel.device_id == device_id)

        total = query.count()
        level_counts = {lv: query.filter(AlarmRecordModel.level == lv).count() for lv in range(4)}
        unack = query.filter(AlarmRecordModel.acknowledged.is_(False)).count()
        return {
            "total": total,
            "level_counts": level_counts,
            "unacknowledged": unack,
            "acknowledged": total - unack,
        }

    def get_active(self, limit: int = 100) -> List[AlarmRecordModel]:
        """获取最近24小时未确认报警"""
        cutoff = utc_now() - timedelta(hours=24)
        return (
            self._session.query(AlarmRecordModel)
            .filter(
                and_(
                    AlarmRecordModel.timestamp >= cutoff,
                    AlarmRecordModel.acknowledged.is_(False),
                )
            )
            .order_by(desc(AlarmRecordModel.level), desc(AlarmRecordModel.timestamp))
            .limit(limit)
            .all()
        )

    def cleanup(self, days: int = 90) -> int:
        """清理过期报警"""
        cutoff = utc_now() - timedelta(days=days)
        return (
            self._session.query(AlarmRecordModel)
            .filter(AlarmRecordModel.timestamp < cutoff)
            .delete(synchronize_session=False)
        )


class AlarmRuleRepository(BaseRepository[AlarmRuleModel]):
    """报警规则仓库"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AlarmRuleModel)

    def get_by_device(self, device_id: str) -> List[AlarmRuleModel]:
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.device_id == device_id).all()

    def get_by_rule_id(self, rule_id: str) -> Optional[AlarmRuleModel]:
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.rule_id == rule_id).first()

    def get_by_register(self, device_id: str, register_name: str) -> Optional[AlarmRuleModel]:
        return (
            self._session.query(AlarmRuleModel)
            .filter(
                and_(
                    AlarmRuleModel.device_id == device_id,
                    AlarmRuleModel.register_name == register_name,
                )
            )
            .first()
        )

    def get_enabled(self) -> List[AlarmRuleModel]:
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.enabled.is_(True)).all()

    def create_rule(
        self,
        rule_id: str,
        device_id: str,
        device_name: str,
        register_name: str,
        alarm_type: str,
        level: int,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        description: str = "",
        enabled: bool = True,
    ) -> AlarmRuleModel:
        return self.create(
            AlarmRuleModel(
                rule_id=rule_id,
                device_id=device_id,
                device_name=device_name,
                register_name=register_name,
                alarm_type=alarm_type,
                level=level,
                threshold_high=threshold_high,
                threshold_low=threshold_low,
                description=description,
                enabled=enabled,
            )
        )

    def update_rule(self, rule_id: str, **kwargs: Any) -> Optional[AlarmRuleModel]:
        """更新规则"""
        rule = self.get_by_rule_id(rule_id)
        if rule is None:
            return None
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        return self.update(rule)

    def delete_rule(self, rule_id: str) -> bool:
        rule = self.get_by_rule_id(rule_id)
        if rule is None:
            return False
        self.delete(rule)
        return True

    def enable_rule(self, rule_id: str) -> Optional[AlarmRuleModel]:
        return self.update_rule(rule_id, enabled=True)

    def disable_rule(self, rule_id: str) -> Optional[AlarmRuleModel]:
        return self.update_rule(rule_id, enabled=False)

    def cleanup_invalid(self) -> int:
        """删除引用不存在设备的规则"""
        invalid = (
            self._session.query(AlarmRuleModel)
            .filter(~AlarmRuleModel.device_id.in_(self._session.query(DeviceModel.id)))
            .all()
        )
        count = len(invalid)
        for rule in invalid:
            self.delete(rule)
        return count
