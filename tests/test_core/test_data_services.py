# -*- coding: utf-8 -*-
"""Tests for data-layer service objects."""

from __future__ import annotations

from datetime import timedelta

from core.data.alarm_rule_persistence import AlarmRulePersistenceManager
from core.data.historical_recorder import HistoricalDataRecorder
from core.data.models import DatabaseManager, DeviceModel, utc_now
from core.utils.alarm_manager import AlarmLevel, AlarmRule, AlarmType


def test_alarm_rule_persistence_roundtrip_and_toggle() -> None:
    DatabaseManager.reset_instance()
    db_manager = DatabaseManager(":memory:")
    manager = AlarmRulePersistenceManager(db_manager)

    rule = AlarmRule(
        rule_id="persist-1",
        device_id="device-1",
        parameter="temperature",
        alarm_type=AlarmType.THRESHOLD_HIGH,
        threshold_high=75.0,
        level=AlarmLevel.ERROR,
        enabled=True,
        description="High temperature",
    )

    assert manager.save_rule(rule) is True

    loaded = manager.load_rule("device-1", "temperature")
    assert loaded is not None
    assert loaded.rule_id == "persist-1"
    assert loaded.alarm_type == AlarmType.THRESHOLD_HIGH
    assert loaded.level == AlarmLevel.ERROR
    assert loaded.threshold_high == 75.0

    assert manager.disable_rule("persist-1") is True
    assert manager.load_all_rules() == []
    assert manager.enable_rule("persist-1") is True
    assert len(manager.load_all_rules()) == 1

    imported = manager.import_rules(
        [
            {
                "rule_id": "persist-2",
                "device_id": "device-2",
                "parameter": "pressure",
                "alarm_type": "threshold_low",
                "threshold_low": 10.0,
                "level": 1,
                "enabled": True,
                "description": "Low pressure",
            }
        ]
    )
    assert imported == 1
    assert len(manager.export_rules()) == 2

    assert manager.delete_rules_by_device("device-1") == 1
    assert manager.load_rule("device-1", "temperature") is None
    manager.close()
    db_manager.close()


def test_historical_data_recorder_flush_and_query() -> None:
    DatabaseManager.reset_instance()
    db_manager = DatabaseManager(":memory:")
    recorder = HistoricalDataRecorder(db_manager)

    with db_manager.session() as session:
        session.add(
            DeviceModel(
                id="device-1",
                name="Recorder Device",
                device_type="PLC",
                protocol_type="modbus_tcp",
                host="127.0.0.1",
                port=502,
                unit_id=1,
            )
        )

    assert recorder.record("device-1", "temperature", 23.5, unit="C", raw_value=235, quality=0) is True
    assert recorder.record("device-1", "pressure", 101.2, unit="kPa", quality=0) is True
    assert recorder.flush() is True

    latest = recorder.get_latest_data("device-1")
    assert latest["temperature"]["value"] == 23.5
    assert latest["pressure"]["unit"] == "kPa"

    count = recorder.record_from_device(
        "device-1",
        {
            "temperature": {"value": 24.0, "unit": "C", "raw_value": 240},
            "humidity": {"value": 48.0, "unit": "%"},
        },
    )
    assert count == 2

    end_time = utc_now() + timedelta(minutes=1)
    start_time = end_time - timedelta(hours=1)
    chart_data = recorder.get_data_for_chart("device-1", "temperature", start_time, end_time)
    assert len(chart_data) >= 2
    assert chart_data[-1]["value"] == 24.0

    assert recorder.cleanup_old_data(days=365) == 0
    recorder.close()
    db_manager.close()
