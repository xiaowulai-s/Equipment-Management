# -*- coding: utf-8 -*-
"""Alarm management for runtime and persistent modes."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from ..data.models import AlarmRuleModel, DatabaseManager, utc_now
from ..data.repository.alarm_repository import AlarmRepository
from ..data.repository.alarm_rule_repository import AlarmRuleRepository
from .alarm_enums import Alarm, AlarmLevel, AlarmRule, AlarmType

logger = logging.getLogger(__name__)


class AlarmManager(QObject):
    """Manage alarms in runtime mode or against persistent repositories."""

    alarm_triggered = Signal(object)
    alarm_cleared = Signal(str)
    alarm_acknowledged = Signal(str)

    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent: Optional[QObject] = None) -> None:
        if isinstance(db_manager, QObject) and parent is None:
            parent = db_manager
            db_manager = None

        super().__init__(parent)
        self._db_manager = db_manager
        self._rules: Dict[str, AlarmRule] = {}
        self._active_alarms: Dict[str, Alarm] = {}
        self._alarm_history: List[Alarm] = []
        self._alarm_counter = 0
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_all_rules)
        self._check_timer.start(1000)

    def add_rule(self, rule: AlarmRule) -> bool:
        """Add one runtime alarm rule."""
        if rule.rule_id in self._rules:
            return False
        self._rules[rule.rule_id] = rule
        return True

    def remove_rule(self, rule_id: str) -> bool:
        """Remove one runtime alarm rule."""
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        return True

    def get_rule(self, rule_id: str) -> Optional[AlarmRule]:
        """Return one runtime alarm rule."""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[AlarmRule]:
        """Return all runtime alarm rules."""
        return list(self._rules.values())

    def enable_rule(self, rule_id: str, enabled: bool = True) -> None:
        """Enable or disable a runtime rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = enabled

    def check_value(self, device_id: str, parameter: str, value: float) -> None:
        """Evaluate one runtime value against in-memory rules."""
        for rule in self._rules.values():
            if rule.device_id == device_id and rule.parameter == parameter:
                level = rule.check(value)
                if level is not None:
                    self._trigger_alarm(rule, value)

    def add_alarm_rule(self, rule: AlarmRuleModel) -> bool:
        """Persist one alarm rule."""
        if self._db_manager is None:
            raise TypeError("数据库模式未启用，不能传入 AlarmRuleModel")

        try:
            with self._db_manager.session() as session:
                repo = AlarmRuleRepository(session)
                created = repo.create(rule)
                session.flush()
                rule.id = created.id
            return True
        except Exception:
            logger.exception("添加报警规则失败: %s", getattr(rule, "rule_id", "unknown"))
            return False

    def get_alarm_rules(self, device_id: str) -> List[AlarmRuleModel]:
        """Return persistent alarm rules for one device."""
        if self._db_manager is None:
            return []
        with self._db_manager.session() as session:
            repo = AlarmRuleRepository(session)
            return repo.get_by_device(device_id)

    def remove_alarm_rule(self, rule_id: Any) -> bool:
        """Remove a persistent alarm rule by model id or business id."""
        if self._db_manager is None:
            return False
        try:
            with self._db_manager.session() as session:
                repo = AlarmRuleRepository(session)
                if isinstance(rule_id, int):
                    model = repo.get_by_id(rule_id)
                    if model is None:
                        return False
                    repo.delete(model)
                    return True
                return repo.delete_rule(str(rule_id))
        except Exception:
            logger.exception("删除报警规则失败: %s", rule_id)
            return False

    def disable_alarm_rule(self, rule_id: Any) -> bool:
        """Disable one persistent alarm rule."""
        return self._set_alarm_rule_enabled(rule_id, False)

    def enable_alarm_rule(self, rule_id: Any) -> bool:
        """Enable one persistent alarm rule."""
        return self._set_alarm_rule_enabled(rule_id, True)

    def check_alarm(self, device_id: str, register_address: int, value: float) -> bool:
        """Evaluate one device/register value against persistent rules."""
        if self._db_manager is None:
            return False

        parameter = AlarmRuleModel._parameter_from_register(register_address)
        triggered = False

        with self._db_manager.session() as session:
            rule_repo = AlarmRuleRepository(session)
            alarm_repo = AlarmRepository(session)
            rules = [
                rule
                for rule in rule_repo.get_by_device(device_id)
                if rule.enabled and (rule.parameter == parameter or rule.register_address == register_address)
            ]

            for rule in rules:
                if self._rule_matches(rule, value):
                    alarm = alarm_repo.create_alarm(
                        rule_id=rule.rule_id,
                        device_id=rule.device_id,
                        device_name=rule.device_name or rule.device_id,
                        parameter=rule.parameter,
                        alarm_type=rule.alarm_type,
                        level=rule.level,
                        value=value,
                        threshold_high=rule.threshold_high,
                        threshold_low=rule.threshold_low,
                        description=rule.description or "",
                    )
                    triggered = True
                    self.alarm_triggered.emit(alarm)

        return triggered

    def acknowledge_alarm(self, alarm_id: str) -> None:
        """Acknowledge a runtime alarm."""
        if alarm_id in self._active_alarms:
            self._active_alarms[alarm_id].acknowledged = True
            self.alarm_acknowledged.emit(alarm_id)

    def clear_alarm(self, alarm_id: str) -> None:
        """Clear a runtime alarm."""
        if alarm_id in self._active_alarms:
            self._active_alarms[alarm_id].cleared = True
            del self._active_alarms[alarm_id]
            self.alarm_cleared.emit(alarm_id)

    def get_active_alarms(self) -> List[Alarm]:
        """Return active runtime alarms."""
        return list(self._active_alarms.values())

    def get_alarm_history(self, limit: int = 100) -> List[Alarm]:
        """Return runtime alarm history, newest last."""
        return self._alarm_history[-limit:]

    def clear_all_alarms(self) -> None:
        """Clear all runtime alarms."""
        self._active_alarms.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Return runtime alarm statistics."""
        stats = {
            "total": len(self._alarm_history),
            "active": len(self._active_alarms),
            "acknowledged": sum(1 for alarm in self._active_alarms.values() if alarm.acknowledged),
            "by_level": {level.name: 0 for level in AlarmLevel},
        }
        for alarm in self._alarm_history:
            stats["by_level"][alarm.rule.level.name] += 1
        return stats

    def _set_alarm_rule_enabled(self, rule_id: Any, enabled: bool) -> bool:
        """Update persistent rule enabled state."""
        if self._db_manager is None:
            return False
        try:
            with self._db_manager.session() as session:
                repo = AlarmRuleRepository(session)
                model = repo.get_by_id(rule_id) if isinstance(rule_id, int) else repo.get_by_rule_id(str(rule_id))
                if model is None:
                    return False
                model.enabled = enabled
                repo.update(model)
            return True
        except Exception:
            logger.exception("更新报警规则启用状态失败: %s", rule_id)
            return False

    def _rule_matches(self, rule: AlarmRuleModel, value: float) -> bool:
        """Evaluate a persistent rule against one numeric value."""
        alarm_type = (rule.alarm_type or "").lower()
        if "high" in alarm_type or rule.threshold_high is not None:
            return rule.threshold_high is not None and value > rule.threshold_high
        if "low" in alarm_type or rule.threshold_low is not None:
            return rule.threshold_low is not None and value < rule.threshold_low
        return False

    def _trigger_alarm(self, rule: AlarmRule, value: float) -> None:
        """Create and emit a runtime alarm."""
        self._alarm_counter += 1
        alarm = Alarm(
            alarm_id=f"ALM-{self._alarm_counter:06d}",
            rule=rule,
            value=value,
            timestamp=utc_now(),
        )
        self._active_alarms[alarm.alarm_id] = alarm
        self._alarm_history.append(alarm)
        self.alarm_triggered.emit(alarm)

    def _check_all_rules(self) -> None:
        """Timer hook kept for future polling integrations."""
        return None
