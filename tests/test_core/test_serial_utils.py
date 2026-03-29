# -*- coding: utf-8 -*-
"""Tests for serial utility helpers."""

from __future__ import annotations

import pytest

from core.utils.serial_utils import get_serial_port_details, get_serial_port_status, list_serial_ports, test_serial_port


class TestSerialUtils:
    """Serial utility tests."""

    def test_list_available_serial_ports(self) -> None:
        ports = list_serial_ports()
        assert isinstance(ports, list)
        for port in ports:
            assert isinstance(port, str)

    def test_get_serial_port_details(self) -> None:
        ports = list_serial_ports()
        if ports:
            port_info = get_serial_port_details(ports[0])
            assert port_info is not None
            assert hasattr(port_info, "device")
            assert hasattr(port_info, "description")
            assert hasattr(port_info, "hwid")

    def test_get_serial_port_details_nonexistent(self) -> None:
        assert get_serial_port_details("COM999") is None

    def test_get_serial_port_status_available(self) -> None:
        ports = list_serial_ports()
        if ports:
            status = get_serial_port_status(ports[0])
            assert isinstance(status, dict)
            assert "available" in status
            assert "error" in status

    def test_get_serial_port_status_unavailable(self) -> None:
        status = get_serial_port_status("COM999")
        assert isinstance(status, dict)
        assert status["available"] is False
        assert status["error"] is not None

    def test_test_serial_port_invalid(self) -> None:
        success, message = test_serial_port("COM999", baudrate=9600, timeout=0.1)
        assert success is False
        assert "串口错误" in message or "无法打开" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
