# -*- coding: utf-8 -*-
"""
Modbus RTU Device Plugin

通用 Modbus RTU 设备插件 — 封装标准 Modbus RTU 串口连接/解析逻辑

职责:
- 实现 DevicePlugin 接口
- 创建 SerialDriver + ModbusProtocol(RTU) 组合
- 提供标准 Modbus RTU 的连接参数和默认配置
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.plugin_registry import DevicePlugin

logger = logging.getLogger(__name__)

PARITY_MAP = {"无校验": "N", "偶校验": "E", "奇校验": "O"}


class ModbusRTUPlugin(DevicePlugin):
    """
    通用 Modbus RTU 设备插件

    支持所有标准 Modbus RTU 从站设备:
    - 温湿度传感器
    - 压力变送器
    - 流量计
    - DMT143 露点仪
    """

    def device_type(self) -> str:
        return "modbus_rtu"

    def display_name(self) -> str:
        return "Modbus RTU"

    def create_connection(self, config: Dict) -> Any:
        """
        创建 Modbus RTU 连接 (Driver + Protocol)

        Args:
            config: 设备配置字典

        Returns:
            {"driver": SerialDriver, "protocol": ModbusProtocol} 字典
        """
        try:
            from core.communication.serial_driver import SerialDriver
            from core.protocols.modbus_protocol import ModbusProtocol

            port = config.get("port", "COM1")
            baudrate = config.get("baudrate", 9600)
            bytesize = config.get("bytesize", 8)
            parity_str = config.get("parity", "无校验")
            parity = PARITY_MAP.get(parity_str, "N")
            stopbits = config.get("stopbits", 1)
            unit_id = config.get("unit_id", 1)

            driver = SerialDriver(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
            )
            protocol = ModbusProtocol(
                driver=driver,
                mode="RTU",
                unit_id=unit_id,
            )

            logger.info(
                "Modbus RTU插件: 创建连接 [port=%s, baudrate=%d, unit_id=%d]",
                port, baudrate, unit_id
            )

            return {"driver": driver, "protocol": protocol}

        except Exception as e:
            logger.error("Modbus RTU插件: 创建连接失败: %s", e)
            return None

    def create_parser(self, config: Dict) -> Any:
        """创建 ModbusValueParser"""
        try:
            from core.protocols.modbus_value_parser import ModbusValueParser
            from core.protocols.byte_order_config import ByteOrderConfig

            byte_order_str = config.get("byte_order", "ABCD")
            byte_order = ByteOrderConfig.from_string(byte_order_str)

            return ModbusValueParser(byte_order=byte_order)

        except Exception as e:
            logger.error("Modbus RTU插件: 创建解析器失败: %s", e)
            return None

    def default_config(self) -> Dict:
        return {
            "device_type": "modbus_rtu",
            "port": "COM1",
            "baudrate": 9600,
            "bytesize": 8,
            "parity": "无校验",
            "stopbits": 1,
            "unit_id": 1,
            "byte_order": "ABCD",
            "protocol_type": "modbus_rtu",
        }

    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        port = config.get("port")
        if not port:
            return False, "缺少必填字段: port"

        baudrate = config.get("baudrate", 9600)
        valid_baudrates = [9600, 19200, 38400, 57600, 115200]
        if baudrate not in valid_baudrates:
            return False, f"无效的波特率: {baudrate} (支持: {valid_baudrates})"

        unit_id = config.get("unit_id", 1)
        if not isinstance(unit_id, int) or not (0 <= unit_id <= 255):
            return False, f"无效的单元ID: {unit_id} (0-255)"

        return True, "配置验证通过"

    def get_config_fields(self) -> List[Dict]:
        return [
            {
                "name": "port",
                "label": "串口号",
                "type": "text",
                "default": "COM1",
                "required": True,
            },
            {
                "name": "baudrate",
                "label": "波特率",
                "type": "dropdown",
                "options": [9600, 19200, 38400, 57600, 115200],
                "default": 9600,
                "required": False,
            },
            {
                "name": "bytesize",
                "label": "数据位",
                "type": "dropdown",
                "options": [5, 6, 7, 8],
                "default": 8,
                "required": False,
            },
            {
                "name": "parity",
                "label": "校验位",
                "type": "dropdown",
                "options": ["无校验", "偶校验", "奇校验"],
                "default": "无校验",
                "required": False,
            },
            {
                "name": "stopbits",
                "label": "停止位",
                "type": "dropdown",
                "options": [1, 1.5, 2],
                "default": 1,
                "required": False,
            },
            {
                "name": "unit_id",
                "label": "从机ID",
                "type": "number",
                "default": 1,
                "required": False,
            },
        ]
