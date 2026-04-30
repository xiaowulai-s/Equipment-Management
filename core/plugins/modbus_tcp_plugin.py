# -*- coding: utf-8 -*-
"""
Modbus TCP Device Plugin

通用 Modbus TCP 设备插件 — 封装标准 Modbus TCP 连接/解析逻辑

职责:
- 实现 DevicePlugin 接口
- 创建 TCPDriver + ModbusProtocol(TCP) 组合
- 提供标准 Modbus TCP 的连接参数和默认配置
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.plugin_registry import DevicePlugin

logger = logging.getLogger(__name__)


class ModbusTCPPlugin(DevicePlugin):
    """
    通用 Modbus TCP 设备插件

    支持所有标准 Modbus TCP 从站设备:
    - PLC (Siemens, Mitsubishi, Omron 等)
    - 变频器
    - 仪表
    - IO 模块
    """

    def device_type(self) -> str:
        return "modbus_tcp"

    def display_name(self) -> str:
        return "Modbus TCP"

    def create_connection(self, config: Dict) -> Any:
        """
        创建 Modbus TCP 连接 (Driver + Protocol)

        Args:
            config: 设备配置字典

        Returns:
            {"driver": TcpDriver, "protocol": ModbusProtocol} 字典
        """
        try:
            from core.communication.tcp_driver import TCPDriver
            from core.protocols.modbus_protocol import ModbusProtocol

            host = config.get("host", "127.0.0.1")
            port = config.get("port", 502)
            unit_id = config.get("unit_id", 1)
            timeout = config.get("timeout", 5.0)

            driver = TCPDriver(host=host, port=port)
            protocol = ModbusProtocol(
                driver=driver,
                mode="TCP",
                unit_id=unit_id,
            )

            logger.info(
                "Modbus TCP插件: 创建连接 [host=%s, port=%d, unit_id=%d]",
                host, port, unit_id
            )

            return {"driver": driver, "protocol": protocol}

        except Exception as e:
            logger.error("Modbus TCP插件: 创建连接失败: %s", e)
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
            logger.error("Modbus TCP插件: 创建解析器失败: %s", e)
            return None

    def default_config(self) -> Dict:
        return {
            "device_type": "modbus_tcp",
            "host": "127.0.0.1",
            "port": 502,
            "unit_id": 1,
            "timeout": 5.0,
            "byte_order": "ABCD",
            "protocol_type": "modbus_tcp",
        }

    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        host = config.get("host")
        if not host:
            return False, "缺少必填字段: host"

        port = config.get("port", 502)
        if not isinstance(port, int) or not (1 <= port <= 65535):
            return False, f"无效的端口号: {port} (1-65535)"

        unit_id = config.get("unit_id", 1)
        if not isinstance(unit_id, int) or not (0 <= unit_id <= 255):
            return False, f"无效的单元ID: {unit_id} (0-255)"

        return True, "配置验证通过"

    def get_config_fields(self) -> List[Dict]:
        return [
            {
                "name": "host",
                "label": "IP地址",
                "type": "text",
                "default": "127.0.0.1",
                "required": True,
            },
            {
                "name": "port",
                "label": "端口号",
                "type": "number",
                "default": 502,
                "required": True,
            },
            {
                "name": "unit_id",
                "label": "单元ID",
                "type": "number",
                "default": 1,
                "required": False,
            },
            {
                "name": "byte_order",
                "label": "字节序",
                "type": "dropdown",
                "options": ["ABCD", "CDAB", "BADC", "DCBA"],
                "default": "ABCD",
                "required": False,
            },
        ]
