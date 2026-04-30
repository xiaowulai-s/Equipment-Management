# -*- coding: utf-8 -*-
"""
协议类型定义
Protocol Type Definitions
"""

from enum import Enum


class ProtocolType(str, Enum):
    """协议类型枚举"""

    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    MODBUS_ASCII = "modbus_ascii"
    SIEMENS_S7 = "siemens_s7"
    OPC_UA = "opc_ua"

    def __str__(self) -> str:
        return self.value
