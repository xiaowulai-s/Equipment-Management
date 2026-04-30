# -*- coding: utf-8 -*-
"""DeviceConnection decoding tests for MCGS-style Modbus points."""

import math
import struct

from core.device.device_connection import DeviceConnection
from core.device.device_models import Device
from core.enums.data_type_enum import RegisterDataType, RegisterPointConfig


class _DummyFactory:
    """Factory stub used for unit tests that do not connect."""


def _build_connection(byte_order: str = "CDAB") -> DeviceConnection:
    device = Device.from_dict(
        {
            "device_id": "mcgs_gateway_01",
            "name": "MCGS Gateway",
            "device_type": "mcgs_gateway",
            "protocol_type": "modbus_tcp",
            "host": "127.0.0.1",
            "port": 502,
            "unit_id": 1,
            "byte_order": byte_order,
            "register_map": [],
        }
    )
    return DeviceConnection(device, _DummyFactory())


def _encode_float32_registers(value: float, byte_order: str) -> list[int]:
    raw_bytes = struct.pack(">f", value)
    if byte_order == "ABCD":
        ordered = raw_bytes
    elif byte_order == "BADC":
        ordered = bytes([raw_bytes[1], raw_bytes[0], raw_bytes[3], raw_bytes[2]])
    elif byte_order == "CDAB":
        ordered = raw_bytes[2:] + raw_bytes[:2]
    elif byte_order == "DCBA":
        ordered = raw_bytes[::-1]
    else:
        raise ValueError(byte_order)

    return [
        struct.unpack(">H", ordered[0:2])[0],
        struct.unpack(">H", ordered[2:4])[0],
    ]


def _encode_int32_registers(value: int, byte_order: str) -> list[int]:
    raw_bytes = struct.pack(">i", value)
    if byte_order == "ABCD":
        ordered = raw_bytes
    elif byte_order == "BADC":
        ordered = bytes([raw_bytes[1], raw_bytes[0], raw_bytes[3], raw_bytes[2]])
    elif byte_order == "CDAB":
        ordered = raw_bytes[2:] + raw_bytes[:2]
    elif byte_order == "DCBA":
        ordered = raw_bytes[::-1]
    else:
        raise ValueError(byte_order)

    return [
        struct.unpack(">H", ordered[0:2])[0],
        struct.unpack(">H", ordered[2:4])[0],
    ]


def test_format_batch_data_decodes_mcgs_cdab_input_float32():
    conn = _build_connection("CDAB")
    point = RegisterPointConfig(
        name="Hum_in",
        data_type=RegisterDataType.INPUT_FLOAT32,
        address=30002,
        decimal_places=1,
        scale=1.0,
        unit="%RH",
        writable=False,
    )
    registers = _encode_float32_registers(23.6, "CDAB")

    result = conn._format_batch_data([point], registers, 30002)

    assert "Hum_in" in result
    assert math.isclose(result["Hum_in"]["raw"], 23.6, rel_tol=1e-5)
    assert result["Hum_in"]["value"] == "23.6 %RH"
    assert result["Hum_in"]["type"] == "input_float32"
    assert result["Hum_in"]["writable"] is False


def test_format_batch_data_decodes_holding_int32_with_byte_order():
    conn = _build_connection("CDAB")
    point = RegisterPointConfig(
        name="Counter",
        data_type=RegisterDataType.HOLDING_INT32,
        address=40010,
        decimal_places=0,
        scale=1.0,
        writable=True,
    )
    registers = _encode_int32_registers(123456, "CDAB")

    result = conn._format_batch_data([point], registers, 40010)

    assert result["Counter"]["raw"] == 123456
    assert result["Counter"]["value"] == "123456"
    assert result["Counter"]["type"] == "holding_int32"


def test_format_batch_data_returns_empty_when_registers_incomplete():
    conn = _build_connection("CDAB")
    point = RegisterPointConfig(
        name="AT_in",
        data_type=RegisterDataType.INPUT_FLOAT32,
        address=30006,
        decimal_places=1,
        scale=1.0,
        unit="℃",
        writable=False,
    )

    result = conn._format_batch_data([point], [0x1234], 30006)

    assert result == {}
