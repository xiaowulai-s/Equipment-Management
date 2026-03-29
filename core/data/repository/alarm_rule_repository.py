# -*- coding: utf-8 -*-
"""Alarm rule repository helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ..models import AlarmRuleModel, DeviceModel
from .base import BaseRepository


class AlarmRuleRepository(BaseRepository[AlarmRuleModel]):
    """Repository for persisted alarm rules."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AlarmRuleModel)

    def get_by_device(self, device_id: str) -> List[AlarmRuleModel]:
        """Return all rules configured for one device."""
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.device_id == device_id).all()

    def get_by_rule_id(self, rule_id: str) -> Optional[AlarmRuleModel]:
        """Return one rule by business rule id."""
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.rule_id == rule_id).first()

    def get_by_parameter(self, device_id: str, parameter: str) -> Optional[AlarmRuleModel]:
        """Return one device rule for a specific parameter."""
        return (
            self._session.query(AlarmRuleModel)
            .filter(and_(AlarmRuleModel.device_id == device_id, AlarmRuleModel.parameter == parameter))
            .first()
        )

    def get_enabled_rules(self) -> List[AlarmRuleModel]:
        """Return all enabled rules."""
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.enabled.is_(True)).all()

    def get_rules_by_level(self, level: int) -> List[AlarmRuleModel]:
        """Return all rules for a specific alarm level."""
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.level == level).all()

    def create_rule(
        self,
        rule_id: str,
        device_id: str,
        device_name: str,
        parameter: str,
        alarm_type: str,
        level: int,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        description: str = "",
        enabled: bool = True,
    ) -> AlarmRuleModel:
        """Create and persist one alarm rule."""
        return self.create(
            AlarmRuleModel(
                rule_id=rule_id,
                device_id=device_id,
                device_name=device_name,
                parameter=parameter,
                alarm_type=alarm_type,
                level=level,
                threshold_high=threshold_high,
                threshold_low=threshold_low,
                description=description,
                enabled=enabled,
            )
        )

    def update_rule(self, rule_id: str, **kwargs: Any) -> Optional[AlarmRuleModel]:
        """Update one rule by business rule id."""
        rule = self.get_by_rule_id(rule_id)
        if rule is None:
            return None

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        return self.update(rule)

    def delete_rule(self, rule_id: str) -> bool:
        """Delete one rule by business rule id."""
        rule = self.get_by_rule_id(rule_id)
        if rule is None:
            return False
        self.delete(rule)
        return True

    def enable_rule(self, rule_id: str) -> Optional[AlarmRuleModel]:
        """Enable one rule."""
        return self.update_rule(rule_id, enabled=True)

    def disable_rule(self, rule_id: str) -> Optional[AlarmRuleModel]:
        """Disable one rule."""
        return self.update_rule(rule_id, enabled=False)

    def get_all_rules_with_devices(self) -> List[Dict[str, Any]]:
        """Return all rules serialized for UI or export use."""
        return [rule.to_dict() for rule in self.get_all()]

    def cleanup_invalid_rules(self) -> int:
        """Delete rules whose device no longer exists."""
        invalid_rules = (
            self._session.query(AlarmRuleModel)
            .filter(~AlarmRuleModel.device_id.in_(self._session.query(DeviceModel.id)))
            .all()
        )

        for rule in invalid_rules:
            self.delete(rule)

        return len(invalid_rules)
