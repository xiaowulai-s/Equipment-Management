# -*- coding: utf-8 -*-
"""Repository and alarm manager tests."""

from __future__ import annotations

from core.data.models import AlarmRuleModel, DatabaseManager
from core.data.repository.device_repository import DeviceRepository
from core.utils.alarm_manager import AlarmLevel, AlarmManager, AlarmRule, AlarmType


def test_device_repository_roundtrip_config() -> None:
    DatabaseManager.reset_instance()
    db_manager = DatabaseManager(":memory:")

    with db_manager.session() as session:
        repository = DeviceRepository(session)
        created = repository.create_from_config(
            {
                "device_id": "repo-1",
                "name": "Repo Device",
                "device_type": "PLC",
                "protocol": "modbus_tcp",
                "ip": "192.168.0.10",
                "port": 502,
                "slave_id": 3,
                "register_map": [{"name": "温度", "address": 1, "type": "uint16"}],
            }
        )

        payload = repository.to_config(created)

        assert payload["device_id"] == "repo-1"
        assert payload["protocol"] == "modbus_tcp"
        assert payload["ip"] == "192.168.0.10"
        assert payload["slave_id"] == 3
        assert payload["register_map"][0]["name"] == "温度"

    db_manager.close()


def test_alarm_manager_runtime_statistics() -> None:
    manager = AlarmManager()
    manager.add_rule(
        AlarmRule(
            rule_id="rule-1",
            device_id="device-1",
            parameter="temperature",
            alarm_type=AlarmType.THRESHOLD_HIGH,
            threshold_high=10,
            level=AlarmLevel.WARNING,
        )
    )

    manager.check_value("device-1", "temperature", 15)
    manager.check_value("device-1", "temperature", 16)

    stats = manager.get_statistics()

    assert stats["total"] == 2
    assert stats["active"] == 2
    assert stats["by_level"]["WARNING"] == 2


def test_alarm_manager_persistent_rule_enable_disable_and_trigger() -> None:
    DatabaseManager.reset_instance()
    db_manager = DatabaseManager(":memory:")
    manager = AlarmManager(db_manager)

    rule = AlarmRuleModel(
        device_id="device-1",
        register_address=40001,
        condition="greater_than",
        threshold=50,
        alarm_type="high_limit",
        enabled=True,
    )

    assert manager.add_alarm_rule(rule) is True
    assert manager.check_alarm("device-1", 40001, 75) is True
    assert manager.disable_alarm_rule(rule.id) is True
    assert manager.check_alarm("device-1", 40001, 80) is False
    assert manager.enable_alarm_rule(rule.id) is True
    assert manager.check_alarm("device-1", 40001, 90) is True
    assert manager.remove_alarm_rule(rule.id) is True

    db_manager.close()
