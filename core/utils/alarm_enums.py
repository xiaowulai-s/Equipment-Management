# -*- coding: utf-8 -*-
"""Alarm enumeration types.

This module contains alarm-related enumerations to avoid circular imports.
These enums are used by both alarm_manager and UI components.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class AlarmLevel(Enum):
    """Alarm severity levels."""

    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


class AlarmType(Enum):
    """Alarm types."""

    THRESHOLD_HIGH = "threshold_high"
    THRESHOLD_LOW = "threshold_low"
    DEVICE_OFFLINE = "device_offline"
    COMMUNICATION_ERROR = "communication_error"
    CUSTOM = "custom"


@dataclass
class AlarmRule:
    """In-memory alarm rule used by runtime mode."""

    rule_id: str
    device_id: str
    parameter: str
    alarm_type: AlarmType
    threshold_high: Optional[float] = None
    threshold_low: Optional[float] = None
    level: AlarmLevel = AlarmLevel.WARNING
    enabled: bool = True
    description: str = ""

    def check(self, value: float) -> Optional[AlarmLevel]:
        """Return triggered level when the rule matches a value."""
        if not self.enabled:
            return None
        if (
            self.alarm_type == AlarmType.THRESHOLD_HIGH
            and self.threshold_high is not None
            and value > self.threshold_high
        ):
            return self.level
        if self.alarm_type == AlarmType.THRESHOLD_LOW and self.threshold_low is not None and value < self.threshold_low:
            return self.level
        return None


@dataclass
class Alarm:
    """In-memory alarm instance."""

    alarm_id: str
    rule: AlarmRule
    value: float
    timestamp: datetime
    acknowledged: bool = False
    cleared: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the in-memory alarm."""
        return {
            "alarm_id": self.alarm_id,
            "device_id": self.rule.device_id,
            "parameter": self.rule.parameter,
            "alarm_type": self.rule.alarm_type.value,
            "level": self.rule.level.value,
            "level_name": self.rule.level.name,
            "value": self.value,
            "threshold_high": self.rule.threshold_high,
            "threshold_low": self.rule.threshold_low,
            "description": self.rule.description,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "acknowledged": self.acknowledged,
            "cleared": self.cleared,
        }
