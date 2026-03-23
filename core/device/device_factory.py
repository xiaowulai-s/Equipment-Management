# -*- coding: utf-8 -*-
"""
设备工厂
Device Factory
"""

from typing import Dict, Any, Optional
from ..communication.tcp_driver import TCPDriver
from ..communication.serial_driver import SerialDriver
from ..protocols.modbus_protocol import ModbusProtocol
from .device_model import Device


class ProtocolType:
    """协议类型"""
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    DMT143_ASCII = "dmt143_ascii"


class DeviceFactory:
    """
    设备工厂
    Device Factory
    """

    # 协议参数模板
    PROTOCOL_PARAMS = {
        ProtocolType.MODBUS_TCP: {
            "name": "Modbus TCP",
            "fields": [
                {"name": "host", "label": "IP地址", "type": "text", "default": "127.0.0.1"},
                {"name": "port", "label": "端口号", "type": "number", "default": 502},
                {"name": "unit_id", "label": "单元ID", "type": "number", "default": 1}
            ]
        },
        ProtocolType.MODBUS_RTU: {
            "name": "Modbus RTU",
            "fields": [
                {"name": "port", "label": "端口号", "type": "text", "default": "COM1"},
                {"name": "baudrate", "label": "波特率", "type": "dropdown",
                 "options": [9600, 19200, 38400, 57600, 115200], "default": 9600},
                {"name": "bytesize", "label": "数据位", "type": "dropdown",
                 "options": [5, 6, 7, 8], "default": 8},
                {"name": "parity", "label": "校验位", "type": "dropdown",
                 "options": ["N", "E", "O"], "default": "N"},
                {"name": "stopbits", "label": "停止位", "type": "dropdown",
                 "options": [1, 1.5, 2], "default": 1},
                {"name": "unit_id", "label": "从机ID", "type": "number", "default": 1}
            ]
        }
    }

    # 默认寄存器映射
    DEFAULT_REGISTER_MAP = [
        {"name": "温度", "address": 0, "type": "uint16", "scale": 0.1, "unit": "°C"},
        {"name": "压力", "address": 1, "type": "uint16", "scale": 0.1, "unit": "MPa"},
        {"name": "流量", "address": 2, "type": "uint16", "scale": 0.1, "unit": "m³/h"},
        {"name": "状态", "address": 3, "type": "uint16", "scale": 1, "unit": ""},
        {"name": "报警", "address": 4, "type": "uint16", "scale": 1, "unit": ""}
    ]

    @staticmethod
    def get_available_protocols() -> list:
        """
        获取可用协议列表
        Get available protocol list
        """
        return [
            {"type": ProtocolType.MODBUS_TCP, "name": DeviceFactory.PROTOCOL_PARAMS[ProtocolType.MODBUS_TCP]["name"]},
            {"type": ProtocolType.MODBUS_RTU, "name": DeviceFactory.PROTOCOL_PARAMS[ProtocolType.MODBUS_RTU]["name"]}
        ]

    @staticmethod
    def get_protocol_params(protocol_type: str) -> Optional[Dict[str, Any]]:
        """
        获取协议参数模板
        Get protocol parameter template
        """
        return DeviceFactory.PROTOCOL_PARAMS.get(protocol_type)

    @staticmethod
    def create_device(device_id: str, device_config: Dict[str, Any]) -> Device:
        """
        创建设备
        Create device
        """
        # 确保配置中有寄存器映射
        if "register_map" not in device_config:
            device_config["register_map"] = DeviceFactory.DEFAULT_REGISTER_MAP

        # 创建设备实例
        device = Device(device_id, device_config)

        # 如果不使用模拟器，创建驱动和协议
        if not device_config.get("use_simulator", False):
            protocol_type = device_config.get("protocol_type", ProtocolType.MODBUS_TCP)

            # 创建驱动
            driver = DeviceFactory._create_driver(protocol_type, device_config)
            if driver:
                device.set_driver(driver)

            # 创建协议
            protocol = DeviceFactory._create_protocol(protocol_type, device_config)
            if protocol:
                device.set_protocol(protocol)

        return device

    @staticmethod
    def _create_driver(protocol_type: str, device_config: Dict[str, Any]):
        """
        创建通信驱动
        Create communication driver
        """
        if protocol_type == ProtocolType.MODBUS_TCP:
            host = device_config.get("host", "127.0.0.1")
            port = device_config.get("port", 502)
            return TCPDriver(host, port)

        elif protocol_type == ProtocolType.MODBUS_RTU:
            port = device_config.get("port", "COM1")
            baudrate = device_config.get("baudrate", 9600)
            bytesize = device_config.get("bytesize", 8)
            parity = device_config.get("parity", "N")
            stopbits = device_config.get("stopbits", 1)
            return SerialDriver(port, baudrate, bytesize, parity, stopbits)

        return None

    @staticmethod
    def _create_protocol(protocol_type: str, device_config: Dict[str, Any]):
        """
        创建协议
        Create protocol
        """
        if protocol_type in [ProtocolType.MODBUS_TCP, ProtocolType.MODBUS_RTU]:
            mode = "TCP" if protocol_type == ProtocolType.MODBUS_TCP else "RTU"
            unit_id = device_config.get("unit_id", 1)
            return ModbusProtocol(mode=mode, unit_id=unit_id)

        return None
