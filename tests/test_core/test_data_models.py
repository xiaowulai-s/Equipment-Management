# -*- coding: utf-8 -*-
"""Tests for data models and database manager."""

from __future__ import annotations

import pytest

from core.data.models import AlarmModel, DatabaseManager, DeviceModel


def test_device_model_alias_mapping() -> None:
    device = DeviceModel(
        name="Alias Device",
        device_type="PLC",
        protocol="modbus_tcp",
        ip="127.0.0.1",
        port=502,
        slave_id=3,
    )

    payload = device.to_dict()

    assert payload["protocol_type"] == "modbus_tcp"
    assert payload["host"] == "127.0.0.1"
    assert payload["unit_id"] == 3
    assert device.protocol == "modbus_tcp"
    assert device.ip == "127.0.0.1"
    assert device.slave_id == 3


def test_alarm_model_level_name_mapping() -> None:
    alarm = AlarmModel(
        rule_id="rule-1",
        device_id="device-1",
        device_name="Device 1",
        parameter="temperature",
        alarm_type="threshold_high",
        level=3,
        value=88.5,
    )

    assert alarm.to_dict()["level_name"] == "严重"


def test_database_manager_rolls_back_failed_transaction() -> None:
    DatabaseManager.reset_instance()
    db_manager = DatabaseManager(":memory:")

    with pytest.raises(Exception):
        with db_manager.session() as session:
            session.add(
                DeviceModel(
                    id="device-rollback",
                    name="Rollback Device",
                    device_type="PLC",
                    protocol="modbus_tcp",
                )
            )
            session.add(
                DeviceModel(
                    id="device-rollback",
                    name="Duplicate Device",
                    device_type="PLC",
                    protocol="modbus_tcp",
                )
            )

    with db_manager.session() as session:
        assert session.query(DeviceModel).count() == 0

    db_manager.close()
