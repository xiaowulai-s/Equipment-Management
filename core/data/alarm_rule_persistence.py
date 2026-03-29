# -*- coding: utf-8 -*-
"""Persistence helper for runtime alarm rules."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from core.utils.alarm_manager import AlarmLevel, AlarmRule, AlarmType
from core.utils.logger import get_logger

from .models import DatabaseManager
from .repository.alarm_rule_repository import AlarmRuleRepository

logger = get_logger(__name__)


class AlarmRulePersistenceManager:
    """Persist and restore runtime alarm rules."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db_manager = db_manager
        self._repository: Optional[AlarmRuleRepository] = None

    def _get_repository(self) -> AlarmRuleRepository:
        """Return a lazily created repository instance."""
        if self._repository is None:
            self._repository = AlarmRuleRepository(self._db_manager.get_session())
        return self._repository

    def save_rule(self, rule: AlarmRule) -> bool:
        """Insert or update one runtime alarm rule."""
        try:
            repo = self._get_repository()
            existing_rule = repo.get_by_parameter(rule.device_id, rule.parameter)
            alarm_type = self._normalize_alarm_type(rule.alarm_type)
            level = self._normalize_level(rule.level)

            if existing_rule is not None:
                return (
                    repo.update_rule(
                        existing_rule.rule_id,
                        alarm_type=alarm_type,
                        level=level,
                        threshold_high=rule.threshold_high,
                        threshold_low=rule.threshold_low,
                        description=rule.description,
                        enabled=rule.enabled,
                    )
                    is not None
                )

            rule_id = rule.rule_id or uuid.uuid4().hex[:8]
            return (
                repo.create_rule(
                    rule_id=rule_id,
                    device_id=rule.device_id,
                    device_name=rule.device_id,
                    parameter=rule.parameter,
                    alarm_type=alarm_type,
                    level=level,
                    threshold_high=rule.threshold_high,
                    threshold_low=rule.threshold_low,
                    description=rule.description,
                    enabled=rule.enabled,
                )
                is not None
            )
        except Exception:
            logger.exception("保存报警规则失败: %s", getattr(rule, "rule_id", "unknown"))
            return False

    def load_rule(self, device_id: str, parameter: str) -> Optional[AlarmRule]:
        """Load one runtime alarm rule by device and parameter."""
        try:
            model = self._get_repository().get_by_parameter(device_id, parameter)
            return None if model is None else self._model_to_rule(model)
        except Exception:
            logger.exception("加载报警规则失败: %s %s", device_id, parameter)
            return None

    def load_all_rules(self) -> List[AlarmRule]:
        """Load all enabled runtime alarm rules."""
        try:
            return [self._model_to_rule(model) for model in self._get_repository().get_enabled_rules()]
        except Exception:
            logger.exception("加载所有报警规则失败")
            return []

    def load_rules_by_device(self, device_id: str) -> List[AlarmRule]:
        """Load all runtime alarm rules for one device."""
        try:
            return [self._model_to_rule(model) for model in self._get_repository().get_by_device(device_id)]
        except Exception:
            logger.exception("加载设备报警规则失败: %s", device_id)
            return []

    def delete_rule(self, rule_id: str) -> bool:
        """Delete one rule by business rule id."""
        try:
            return self._get_repository().delete_rule(rule_id)
        except Exception:
            logger.exception("删除报警规则失败: %s", rule_id)
            return False

    def delete_rules_by_device(self, device_id: str) -> int:
        """Delete all rules for one device."""
        count = 0
        for rule in self.load_rules_by_device(device_id):
            if self.delete_rule(rule.rule_id):
                count += 1
        return count

    def enable_rule(self, rule_id: str) -> bool:
        """Enable one persisted rule."""
        try:
            return self._get_repository().enable_rule(rule_id) is not None
        except Exception:
            logger.exception("启用报警规则失败: %s", rule_id)
            return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable one persisted rule."""
        try:
            return self._get_repository().disable_rule(rule_id) is not None
        except Exception:
            logger.exception("禁用报警规则失败: %s", rule_id)
            return False

    def export_rules(self) -> List[Dict[str, Any]]:
        """Export all persisted rules as dictionaries."""
        try:
            return self._get_repository().get_all_rules_with_devices()
        except Exception:
            logger.exception("导出报警规则失败")
            return []

    def import_rules(self, rules_data: List[Dict[str, Any]]) -> int:
        """Import runtime rules from serialized dictionaries."""
        count = 0
        for rule_data in rules_data:
            try:
                rule = AlarmRule(
                    rule_id=rule_data.get("rule_id") or uuid.uuid4().hex[:8],
                    device_id=str(rule_data.get("device_id") or ""),
                    parameter=str(rule_data.get("parameter") or ""),
                    alarm_type=self._deserialize_alarm_type(rule_data.get("alarm_type")),
                    threshold_high=rule_data.get("threshold_high"),
                    threshold_low=rule_data.get("threshold_low"),
                    level=self._deserialize_level(rule_data.get("level")),
                    enabled=bool(rule_data.get("enabled", True)),
                    description=str(rule_data.get("description") or ""),
                )
                if self.save_rule(rule):
                    count += 1
            except Exception:
                logger.exception("导入报警规则失败: %s", rule_data.get("rule_id"))
        return count

    def close(self) -> None:
        """Release any cached repository session."""
        if self._repository is not None:
            self._repository._session.close()
            self._repository = None
        logger.info("报警规则持久化管理器已关闭")

    @staticmethod
    def _model_to_rule(model: Any) -> AlarmRule:
        """Convert one ORM model into a runtime alarm rule."""
        return AlarmRule(
            rule_id=model.rule_id,
            device_id=model.device_id,
            parameter=model.parameter,
            alarm_type=AlarmRulePersistenceManager._deserialize_alarm_type(model.alarm_type),
            threshold_high=model.threshold_high,
            threshold_low=model.threshold_low,
            level=AlarmRulePersistenceManager._deserialize_level(model.level),
            enabled=model.enabled,
            description=model.description or "",
        )

    @staticmethod
    def _normalize_alarm_type(alarm_type: Any) -> str:
        """Normalize runtime alarm type values into persistence format."""
        if isinstance(alarm_type, AlarmType):
            return alarm_type.value
        return str(alarm_type or AlarmType.CUSTOM.value)

    @staticmethod
    def _normalize_level(level: Any) -> int:
        """Normalize runtime alarm levels into persistence format."""
        if isinstance(level, AlarmLevel):
            return int(level.value)
        return int(level)

    @staticmethod
    def _deserialize_alarm_type(value: Any) -> AlarmType:
        """Deserialize one persisted alarm type into the runtime enum."""
        try:
            return AlarmType(str(value))
        except ValueError:
            return AlarmType.CUSTOM

    @staticmethod
    def _deserialize_level(value: Any) -> AlarmLevel:
        """Deserialize one persisted level into the runtime enum."""
        try:
            return AlarmLevel(int(value))
        except ValueError:
            return AlarmLevel.WARNING
