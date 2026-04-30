# -*- coding: utf-8 -*-
"""
MCGS Device Plugin

MCGS Modbus TCP 触摸屏设备插件 — 封装 MCGSModbusReader 的连接/解析逻辑

职责:
- 实现 DevicePlugin 接口
- 封装 MCGSModbusReader 的创建和配置
- 提供 MCGS 特有的连接参数和默认配置
- 验证 MCGS 设备配置

设计原则:
- 开闭原则: 新增设备类型只需创建新插件，无需修改核心代码
- 依赖倒置: 面向 DevicePlugin 接口编程
- 单一职责: 只负责 MCGS 设备的创建逻辑
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.plugin_registry import DevicePlugin

logger = logging.getLogger(__name__)


class MCGSPlugin(DevicePlugin):
    """
    MCGS Modbus TCP 触摸屏设备插件

    支持 MCGS TPC/TP 系列触摸屏通过 Modbus TCP 协议通信。
    特点:
    - JSON 配置驱动 (devices.json)
    - 批量读取优化 (单次 FC03 请求)
    - CDAB 字节序 (MCGS 默认)
    - 自动地址转换 (1-based -> 0-based)
    """

    def device_type(self) -> str:
        return "mcgs"

    def display_name(self) -> str:
        return "MCGS Modbus TCP"

    def create_connection(self, config: Dict) -> Any:
        """
        创建 MCGSModbusReader 实例

        Args:
            config: 设备配置字典，必须包含 config_path 字段

        Returns:
            MCGSModbusReader 实例，失败返回 None
        """
        try:
            from core.utils.mcgs_modbus_reader import MCGSModbusReader

            config_path = config.get("config_path")
            mode = config.get("mode", "auto")

            if not config_path:
                logger.error("MCGS插件: 缺少 config_path 配置")
                return None

            reader = MCGSModbusReader(config_path, mode=mode)
            logger.info("MCGS插件: 创建读取器成功 [path=%s, mode=%s]", config_path, mode)
            return reader

        except Exception as e:
            logger.error("MCGS插件: 创建连接失败: %s", e)
            return None

    def create_parser(self, config: Dict) -> Any:
        """
        创建 MCGS 数据解析器

        MCGS 使用内置的 _parse_all_points 方法，
        这里返回 ModbusValueParser 作为替代

        Args:
            config: 包含 byte_order 的配置字典

        Returns:
            ModbusValueParser 实例
        """
        try:
            from core.protocols.modbus_value_parser import ModbusValueParser
            from core.protocols.byte_order_config import ByteOrderConfig

            byte_order_str = config.get("byte_order", "CDAB")
            byte_order = ByteOrderConfig.from_string(byte_order_str)

            parser = ModbusValueParser(byte_order=byte_order)
            return parser

        except Exception as e:
            logger.error("MCGS插件: 创建解析器失败: %s", e)
            return None

    def default_config(self) -> Dict:
        """返回 MCGS 设备的默认配置模板"""
        return {
            "device_type": "mcgs",
            "config_path": "config/devices.json",
            "mode": "auto",
            "byte_order": "CDAB",
            "polling_interval_ms": 1000,
            "timeout_ms": 3000,
            "address_base": 1,
        }

    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        """
        验证 MCGS 设备配置

        必填字段: config_path
        可选字段: mode, byte_order, polling_interval_ms, timeout_ms
        """
        config_path = config.get("config_path")
        if not config_path:
            return False, "缺少必填字段: config_path"

        from pathlib import Path
        path = Path(config_path)
        if not path.exists():
            return False, f"配置文件不存在: {config_path}"

        mode = config.get("mode", "auto")
        if mode not in ("auto", "pymodbus", "builtin"):
            return False, f"无效的 mode 值: {mode} (支持: auto/pymodbus/builtin)"

        byte_order = config.get("byte_order", "CDAB")
        if byte_order.upper() not in ("ABCD", "BADC", "CDAB", "DCBA"):
            return False, f"无效的字节序: {byte_order}"

        return True, "配置验证通过"

    def get_config_fields(self) -> List[Dict]:
        """返回 MCGS 设备的配置字段定义（用于 UI 表单生成）"""
        return [
            {
                "name": "config_path",
                "label": "配置文件路径",
                "type": "file",
                "default": "config/devices.json",
                "required": True,
                "description": "devices.json 配置文件路径",
            },
            {
                "name": "mode",
                "label": "通信模式",
                "type": "dropdown",
                "options": ["auto", "pymodbus", "builtin"],
                "default": "auto",
                "required": False,
                "description": "auto=自动检测, pymodbus=强制pymodbus, builtin=内置协议栈",
            },
            {
                "name": "byte_order",
                "label": "字节序",
                "type": "dropdown",
                "options": ["CDAB", "ABCD", "BADC", "DCBA"],
                "default": "CDAB",
                "required": False,
                "description": "MCGS默认CDAB(字交换)",
            },
            {
                "name": "polling_interval_ms",
                "label": "轮询间隔(ms)",
                "type": "number",
                "default": 1000,
                "required": False,
                "description": "数据采集轮询间隔",
            },
            {
                "name": "timeout_ms",
                "label": "超时时间(ms)",
                "type": "number",
                "default": 3000,
                "required": False,
                "description": "通信超时时间",
            },
        ]
