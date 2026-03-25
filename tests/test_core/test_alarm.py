# -*- coding: utf-8 -*-
"""
报警系统测试
Alarm System Tests
"""

import pytest

from core.utils.alarm_manager import AlarmLevel, AlarmManager, AlarmRule, AlarmType


class TestAlarmManager:
    """报警管理器测试类"""

    @pytest.fixture
    def alarm_manager(self):
        """创建报警管理器实例"""
        return AlarmManager()

    def test_add_alarm_rule(self, alarm_manager):
        """测试添加报警规则"""
        rule = AlarmRule(
            rule_id="rule_1",
            device_id="device_1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=100,
            level=AlarmLevel.WARNING,
            enabled=True,
        )

        success = alarm_manager.add_rule(rule)
        assert success is True

    def test_remove_alarm_rule(self, alarm_manager):
        """测试移除报警规则"""
        rule = AlarmRule(
            rule_id="rule_1",
            device_id="device_1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=100,
            level=AlarmLevel.WARNING,
            enabled=True,
        )

        alarm_manager.add_rule(rule)
        success = alarm_manager.remove_rule("rule_1")
        assert success is True

    def test_get_alarm_rules(self, alarm_manager):
        """测试获取报警规则"""
        rule = AlarmRule(
            rule_id="rule_1",
            device_id="device_1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=100,
            level=AlarmLevel.WARNING,
            enabled=True,
        )

        alarm_manager.add_rule(rule)
        rules = alarm_manager.get_all_rules()
        assert len(rules) == 1
        assert rules[0].rule_id == "rule_1"

    def test_check_alarm_trigger(self, alarm_manager):
        """测试报警触发检查"""
        rule = AlarmRule(
            rule_id="rule_1",
            device_id="device_1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=100,
            level=AlarmLevel.WARNING,
            enabled=True,
        )

        alarm_manager.add_rule(rule)

        # 测试触发报警（值超过阈值）
        alarm_manager.check_value("device_1", "temperature", 150)
        active_alarms = alarm_manager.get_active_alarms()
        assert len(active_alarms) > 0

        # 测试未触发报警（值低于阈值）
        alarm_manager.check_value("device_1", "temperature", 50)
        # 应该不会新增报警

    def test_enable_disable_alarm(self, alarm_manager):
        """测试启用/禁用报警"""
        rule = AlarmRule(
            rule_id="rule_1",
            device_id="device_1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=100,
            level=AlarmLevel.WARNING,
            enabled=True,
        )

        alarm_manager.add_rule(rule)

        # 禁用规则
        alarm_manager.enable_rule("rule_1", enabled=False)
        rule = alarm_manager.get_rule("rule_1")
        assert rule.enabled is False

        # 启用规则
        alarm_manager.enable_rule("rule_1", enabled=True)
        rule = alarm_manager.get_rule("rule_1")
        assert rule.enabled is True

    def test_alarm_acknowledge_and_clear(self, alarm_manager):
        """测试报警确认和清除"""
        rule = AlarmRule(
            rule_id="rule_1",
            device_id="device_1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=100,
            level=AlarmLevel.WARNING,
            enabled=True,
        )

        alarm_manager.add_rule(rule)

        # 触发报警
        alarm_manager.check_value("device_1", "temperature", 150)
        active_alarms = alarm_manager.get_active_alarms()
        assert len(active_alarms) > 0

        alarm_id = active_alarms[0].alarm_id

        # 确认报警
        alarm_manager.acknowledge_alarm(alarm_id)
        alarm = alarm_manager.get_active_alarms()[0]
        assert alarm.acknowledged is True

        # 清除报警
        alarm_manager.clear_alarm(alarm_id)
        active_alarms = alarm_manager.get_active_alarms()
        assert len(active_alarms) == 0

    def test_alarm_statistics(self, alarm_manager):
        """测试报警统计"""
        rule = AlarmRule(
            rule_id="rule_1",
            device_id="device_1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=100,
            level=AlarmLevel.WARNING,
            enabled=True,
        )

        alarm_manager.add_rule(rule)

        # 触发几次报警
        alarm_manager.check_value("device_1", "temperature", 150)
        alarm_manager.check_value("device_1", "temperature", 160)

        stats = alarm_manager.get_statistics()
        assert stats["total"] > 0
        assert "active" in stats
        assert "by_level" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
