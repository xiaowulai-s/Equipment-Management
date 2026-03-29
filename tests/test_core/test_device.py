# -*- coding: utf-8 -*-
"""Device and device manager tests."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from core.device.device_factory import DeviceFactory
from core.device.device_manager import DeviceManager
from core.device.device_model import Device, DeviceStatus


@pytest.fixture
def device_manager() -> DeviceManager:
    temp_dir = Path(tempfile.mkdtemp(prefix="device_manager_test_"))
    config_file = str(temp_dir / "test_config.json")
    manager = DeviceManager(config_file=config_file)
    yield manager
    shutil.rmtree(temp_dir, ignore_errors=True)


def build_device_config(**overrides):
    config = {
        "name": "TestDevice",
        "device_type": "PLC",
        "protocol": "modbus_tcp",
        "ip": "192.168.1.100",
        "port": 502,
        "slave_id": 1,
    }
    config.update(overrides)
    return config


class TestDeviceManager:
    def test_add_device(self, device_manager: DeviceManager) -> None:
        device_id = device_manager.add_device(build_device_config())

        assert device_id is not None
        assert len(device_manager._devices) == 1

    def test_add_device_normalizes_config(self, device_manager: DeviceManager) -> None:
        device_id = device_manager.add_device(build_device_config())

        stored = device_manager.get_device(device_id)

        assert stored is not None
        assert stored.get_device_config()["protocol_type"] == "modbus_tcp"
        assert stored.get_device_config()["host"] == "192.168.1.100"
        assert stored.get_device_config()["unit_id"] == 1

    def test_remove_device(self, device_manager: DeviceManager) -> None:
        device_id = device_manager.add_device(build_device_config())

        success = device_manager.remove_device(device_id)

        assert success is True
        assert len(device_manager._devices) == 0

    def test_get_device(self, device_manager: DeviceManager) -> None:
        device_id = device_manager.add_device(build_device_config())

        retrieved = device_manager.get_device(device_id)

        assert retrieved is not None
        assert retrieved.get_device_config()["name"] == "TestDevice"

    def test_get_device_not_found(self, device_manager: DeviceManager) -> None:
        assert device_manager.get_device("nonexistent") is None

    def test_device_status(self, device_manager: DeviceManager) -> None:
        device_id = device_manager.add_device(build_device_config())
        device = device_manager.get_device(device_id)

        assert device is not None
        assert device.get_status() == DeviceStatus.DISCONNECTED

    def test_disconnect_missing_device_returns_false(self, device_manager: DeviceManager) -> None:
        assert device_manager.disconnect_device("missing-device") is False

    def test_batch_disconnect_reports_per_device_result(self, device_manager: DeviceManager) -> None:
        first = device_manager.add_device(build_device_config(name="Device A"))
        second = device_manager.add_device(build_device_config(name="Device B", ip="192.168.1.101"))

        results = device_manager.batch_disconnect_devices([first, second, "missing"])

        assert results == {first: True, second: True, "missing": False}

    def test_edit_device_replaces_runtime_config(self, device_manager: DeviceManager) -> None:
        device_id = device_manager.add_device(build_device_config())

        edited = device_manager.edit_device(
            device_id,
            build_device_config(name="Edited Device", ip="10.0.0.1", slave_id=9),
        )

        updated = device_manager.get_device(device_id)
        assert edited is True
        assert updated is not None
        assert updated.get_device_config()["name"] == "Edited Device"
        assert updated.get_device_config()["host"] == "10.0.0.1"
        assert updated.get_device_config()["unit_id"] == 9

    def test_export_devices_returns_selected_configs(self, device_manager: DeviceManager) -> None:
        first = device_manager.add_device(build_device_config(name="Device A"))
        second = device_manager.add_device(build_device_config(name="Device B", ip="192.168.1.101"))

        payload = device_manager.export_devices([first])

        assert payload["version"] == "1.0"
        assert len(payload["devices"]) == 1
        assert payload["devices"][0]["device_id"] == first
        assert payload["devices"][0]["name"] == "Device A"
        assert second != first


class TestDeviceFactory:
    def test_create_tcp_device(self) -> None:
        config = {"name": "TCPDevice", "device_type": "PLC", "ip": "192.168.1.100", "port": 502, "slave_id": 1}

        device = DeviceFactory.create_device("device_1", config)

        assert device is not None
        assert device.get_device_config()["name"] == "TCPDevice"

    def test_create_rtu_device(self) -> None:
        config = {"name": "RTUDevice", "device_type": "Sensor", "port": "COM1", "baudrate": 9600, "slave_id": 1}

        device = DeviceFactory.create_device("device_2", config)

        assert device is not None
        assert device.get_device_config()["name"] == "RTUDevice"

    def test_create_invalid_device(self) -> None:
        config = {"name": "InvalidDevice", "protocol_type": "invalid_protocol"}

        device = DeviceFactory.create_device("device_3", config)

        assert device is not None
        assert device.get_device_config()["name"] == "InvalidDevice"
        assert device._driver is None
        assert device._protocol is None


class TestDeviceModel:
    def test_validate_config_requires_protocol_fields(self) -> None:
        valid, error = Device.validate_config({"device_id": "dev-1", "name": "X", "device_type": "PLC"})

        assert valid is False
        assert "protocol_type" in error

    def test_disconnect_without_driver_is_safe(self) -> None:
        device = Device("dev-1", build_device_config(protocol_type="modbus_tcp", host="127.0.0.1", unit_id=1))

        assert device.disconnect() is True
        assert device.get_status() == DeviceStatus.DISCONNECTED
