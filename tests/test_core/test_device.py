# -*- coding: utf-8 -*-
"""
设备管理测试
Device Management Tests
"""

import pytest

from core.device.device_factory import DeviceFactory
from core.device.device_manager import DeviceManager
from core.device.device_model import DeviceStatus


class TestDeviceManager:
    """设备管理器测试类"""

    @pytest.fixture
    def device_manager(self, tmp_path):
        """创建设备管理器实例"""
        config_file = str(tmp_path / "test_config.json")
        return DeviceManager(config_file=config_file)

    def test_add_device(self, device_manager):
        """测试添加设备"""
        device_config = {
            "name": "TestDevice",
            "device_type": "PLC",
            "protocol": "modbus_tcp",
            "ip": "192.168.1.100",
            "port": 502,
            "slave_id": 1,
        }

        device_id = device_manager.add_device(device_config)
        assert device_id is not None
        assert len(device_manager._devices) == 1

    def test_remove_device(self, device_manager):
        """测试移除设备"""
        device_config = {
            "name": "TestDevice",
            "device_type": "PLC",
            "protocol": "modbus_tcp",
            "ip": "192.168.1.100",
            "port": 502,
            "slave_id": 1,
        }

        device_id = device_manager.add_device(device_config)
        success = device_manager.remove_device(device_id)
        assert success is True
        assert len(device_manager._devices) == 0

    def test_get_device(self, device_manager):
        """测试获取设备"""
        device_config = {
            "name": "TestDevice",
            "device_type": "PLC",
            "protocol": "modbus_tcp",
            "ip": "192.168.1.100",
            "port": 502,
            "slave_id": 1,
        }

        device_id = device_manager.add_device(device_config)
        retrieved = device_manager.get_device(device_id)
        assert retrieved is not None
        assert retrieved._device_config["name"] == "TestDevice"

    def test_get_device_not_found(self, device_manager):
        """测试获取不存在的设备"""
        device = device_manager.get_device("nonexistent")
        assert device is None

    def test_device_status(self, device_manager):
        """测试设备状态"""
        device_config = {
            "name": "TestDevice",
            "device_type": "PLC",
            "protocol": "modbus_tcp",
            "ip": "192.168.1.100",
            "port": 502,
            "slave_id": 1,
        }

        device_id = device_manager.add_device(device_config)
        device = device_manager.get_device(device_id)

        # 初始状态应为断开连接
        assert device._status == DeviceStatus.DISCONNECTED


class TestDeviceFactory:
    """设备工厂测试类"""

    def test_create_tcp_device(self):
        """测试创建 TCP 设备"""
        config = {"name": "TCPDevice", "device_type": "PLC", "ip": "192.168.1.100", "port": 502, "slave_id": 1}

        device = DeviceFactory.create_device("device_1", config)
        assert device is not None
        assert device._device_config["name"] == "TCPDevice"

    def test_create_rtu_device(self):
        """测试创建 RTU 设备"""
        config = {"name": "RTUDevice", "device_type": "Sensor", "port": "COM1", "baudrate": 9600, "slave_id": 1}

        device = DeviceFactory.create_device("device_2", config)
        assert device is not None
        assert device._device_config["name"] == "RTUDevice"

    def test_create_invalid_device(self):
        """测试创建无效设备类型"""
        # 即使协议类型无效，工厂方法也会创建设备（只是没有驱动和协议）
        config = {"name": "InvalidDevice", "protocol_type": "invalid_protocol"}

        # 应该成功创建设备，但驱动和协议为 None
        device = DeviceFactory.create_device("device_3", config)
        assert device is not None
        assert device._device_config["name"] == "InvalidDevice"
        # 无效协议类型的设备应该没有驱动和协议
        assert device._driver is None
        assert device._protocol is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
