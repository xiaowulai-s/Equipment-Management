# -*- coding: utf-8 -*-
"""
报警系统模块
Alarm System Module
"""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal


class AlarmLevel(Enum):
    """报警级别"""

    INFO = 0  # 信息
    WARNING = 1  # 警告
    ERROR = 2  # 错误
    CRITICAL = 3  # 严重


class AlarmType(Enum):
    """报警类型"""

    THRESHOLD_HIGH = "threshold_high"  # 阈值过高
    THRESHOLD_LOW = "threshold_low"  # 阈值过低
    DEVICE_OFFLINE = "device_offline"  # 设备离线
    COMMUNICATION_ERROR = "communication_error"  # 通信错误
    CUSTOM = "custom"  # 自定义


class AlarmRule:
    """报警规则"""

    def __init__(
        self,
        rule_id: str,
        device_id: str,
        parameter: str,
        alarm_type: AlarmType,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        level: AlarmLevel = AlarmLevel.WARNING,
        enabled: bool = True,
        description: str = "",
    ):
        self.rule_id = rule_id
        self.device_id = device_id
        self.parameter = parameter
        self.alarm_type = alarm_type
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low
        self.level = level
        self.enabled = enabled
        self.description = description

    def check(self, value: float) -> Optional[AlarmLevel]:
        """
        检查值是否触发报警
        Args:
            value: 当前值
        Returns:
            报警级别，如果不触发则返回 None
        """
        if not self.enabled:
            return None

        if self.alarm_type == AlarmType.THRESHOLD_HIGH:
            if self.threshold_high is not None and value > self.threshold_high:
                return self.level

        elif self.alarm_type == AlarmType.THRESHOLD_LOW:
            if self.threshold_low is not None and value < self.threshold_low:
                return self.level

        elif self.alarm_type in [AlarmType.THRESHOLD_HIGH, AlarmType.THRESHOLD_LOW]:
            # 双向阈值检查
            if self.threshold_high is not None and value > self.threshold_high:
                return self.level
            if self.threshold_low is not None and value < self.threshold_low:
                return self.level

        return None


class Alarm:
    """报警实例"""

    def __init__(self, alarm_id: str, rule: AlarmRule, value: float, timestamp: datetime = None):
        self.alarm_id = alarm_id
        self.rule = rule
        self.value = value
        self.timestamp = timestamp or datetime.now()
        self.acknowledged = False
        self.cleared = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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


class AlarmManager(QObject):
    """报警管理器"""

    # 信号定义
    alarm_triggered = Signal(Alarm)  # 报警触发
    alarm_cleared = Signal(str)  # 报警清除 (alarm_id)
    alarm_acknowledged = Signal(str)  # 报警确认 (alarm_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: Dict[str, AlarmRule] = {}
        self._active_alarms: Dict[str, Alarm] = {}
        self._alarm_history: List[Alarm] = []
        self._alarm_counter = 0
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_all_rules)
        self._check_timer.start(1000)  # 每秒检查一次

    def add_rule(self, rule: AlarmRule) -> bool:
        """
        添加报警规则
        Args:
            rule: 报警规则
        Returns:
            bool: 是否成功添加
        """
        if rule.rule_id in self._rules:
            return False
        self._rules[rule.rule_id] = rule
        return True

    def remove_rule(self, rule_id: str) -> bool:
        """移除报警规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AlarmRule]:
        """获取报警规则"""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[AlarmRule]:
        """获取所有规则"""
        return list(self._rules.values())

    def enable_rule(self, rule_id: str, enabled: bool = True):
        """启用/禁用规则"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = enabled

    def check_value(self, device_id: str, parameter: str, value: float):
        """
        检查值是否触发报警
        Args:
            device_id: 设备 ID
            parameter: 参数名
            value: 值
        """
        for rule in self._rules.values():
            if rule.device_id == device_id and rule.parameter == parameter:
                level = rule.check(value)
                if level:
                    self._trigger_alarm(rule, value)

    def _trigger_alarm(self, rule: AlarmRule, value: float):
        """触发报警"""
        self._alarm_counter += 1
        alarm_id = f"ALM-{self._alarm_counter:06d}"
        alarm = Alarm(alarm_id, rule, value)

        self._active_alarms[alarm_id] = alarm
        self._alarm_history.append(alarm)

        self.alarm_triggered.emit(alarm)

    def acknowledge_alarm(self, alarm_id: str):
        """确认报警"""
        if alarm_id in self._active_alarms:
            self._active_alarms[alarm_id].acknowledged = True
            self.alarm_acknowledged.emit(alarm_id)

    def clear_alarm(self, alarm_id: str):
        """清除报警"""
        if alarm_id in self._active_alarms:
            alarm = self._active_alarms[alarm_id]
            alarm.cleared = True
            del self._active_alarms[alarm_id]
            self.alarm_cleared.emit(alarm_id)

    def get_active_alarms(self) -> List[Alarm]:
        """获取活动报警"""
        return list(self._active_alarms.values())

    def get_alarm_history(self, limit: int = 100) -> List[Alarm]:
        """获取报警历史"""
        return self._alarm_history[-limit:]

    def clear_all_alarms(self):
        """清除所有报警"""
        self._active_alarms.clear()

    def _check_all_rules(self):
        """定期检查所有规则（用于设备状态等）"""
        # 这里可以添加定期检查逻辑
        pass

    def get_statistics(self) -> Dict[str, int]:
        """获取报警统计"""
        stats = {
            "total": len(self._alarm_history),
            "active": len(self._active_alarms),
            "acknowledged": sum(1 for a in self._active_alarms.values() if a.acknowledged),
            "by_level": {level.name: 0 for level in AlarmLevel},
        }

        for alarm in self._alarm_history:
            stats["by_level"][alarm.rule.level.name] += 1

        return stats
