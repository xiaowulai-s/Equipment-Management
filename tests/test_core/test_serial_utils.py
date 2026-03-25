# -*- coding: utf-8 -*-
"""
串口工具测试
Serial Utils Tests
"""

import pytest

from core.utils.serial_utils import get_serial_port_details, get_serial_port_status, list_serial_ports, test_serial_port


class TestSerialUtils:
    """串口工具测试类"""

    def test_list_available_serial_ports(self):
        """测试列出可用串口"""
        ports = list_serial_ports()
        assert isinstance(ports, list)
        for port in ports:
            assert isinstance(port, str)

    def test_get_serial_port_details(self):
        """测试获取串口详情"""
        ports = list_serial_ports()
        if ports:
            port_info = get_serial_port_details(ports[0])
            assert port_info is not None
            assert hasattr(port_info, "device")
            assert hasattr(port_info, "description")
            assert hasattr(port_info, "hwid")

    def test_get_serial_port_details_nonexistent(self):
        """测试获取不存在的串口详情"""
        port_info = get_serial_port_details("COM999")
        assert port_info is None

    def test_get_serial_port_status_available(self):
        """测试获取可用串口状态"""
        ports = list_serial_ports()
        if ports:
            status = get_serial_port_status(ports[0])
            assert isinstance(status, dict)
            assert "available" in status
            assert "error" in status

    def test_get_serial_port_status_unavailable(self):
        """测试获取不可用串口状态"""
        status = get_serial_port_status("COM999")
        assert isinstance(status, dict)
        assert status["available"] is False
        assert status["error"] is not None

    def test_test_serial_port_invalid(self):
        """测试测试无效串口"""
        success, message = test_serial_port("COM999", baudrate=9600, timeout=0.1)
        assert success is False
        assert "串口错误" in message or "无法打开" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
