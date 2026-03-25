# -*- coding: utf-8 -*-
"""
Modbus 协议测试
Modbus Protocol Tests
"""

from unittest.mock import Mock

import pytest

from core.protocols.modbus_protocol import ModbusProtocol


class TestModbusProtocol:
    """Modbus 协议测试类"""

    @pytest.fixture
    def mock_driver(self):
        """创建模拟驱动"""
        driver = Mock()
        driver.unit_id = 1
        return driver

    @pytest.fixture
    def modbus_rtu(self, mock_driver):
        """创建 Modbus RTU 协议实例"""
        return ModbusProtocol(driver=mock_driver, mode="RTU")

    def test_crc_calculation(self, modbus_rtu):
        """测试 CRC 校验计算"""
        data = b"\x01\x03\x00\x00\x00\x01"
        crc = modbus_rtu.crc16(data)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_lrc_calculation(self, modbus_rtu):
        """测试 LRC 校验计算（Modbus ASCII）"""
        data = b"\x01\x03\x00\x00\x00\x01"
        lrc = modbus_rtu.lrc(data)
        assert isinstance(lrc, int)
        assert 0 <= lrc <= 0xFF

    def test_protocol_mode(self, mock_driver):
        """测试协议模式"""
        tcp_protocol = ModbusProtocol(driver=mock_driver, mode="TCP")
        assert tcp_protocol._mode == "TCP"

        rtu_protocol = ModbusProtocol(driver=mock_driver, mode="RTU")
        assert rtu_protocol._mode == "RTU"

    def test_unit_id(self, mock_driver):
        """测试从站 ID"""
        protocol = ModbusProtocol(driver=mock_driver, mode="TCP", unit_id=5)
        assert protocol._unit_id == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
