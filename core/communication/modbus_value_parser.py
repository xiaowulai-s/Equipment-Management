# -*- coding: utf-8 -*-
"""
ModbusValueParser - 统一寄存器值解析器

替代3处重复实现:
1. mcgs_modbus_reader._parse_float / _parse_int16 / _parse_int32
2. modbus_protocol 中的 float32/int32/uint32 解析
3. device_connection._parse_point_value

特性:
- 统一入口: parse() / parse_batch()
- 支持7种 RegisterDataType
- 支持4种字节序 (通过 ByteOrderConfig)
- NaN/Inf 过滤
- 边界检查
- 线程安全 (无状态 / frozen config)
"""

import struct
import math
import logging
from typing import Any, Dict, List, Optional, Union

from core.protocols.byte_order_config import ByteOrderConfig, DEFAULT_BYTE_ORDER
from core.enums.data_type_enum import RegisterDataType, RegisterPointConfig

logger = logging.getLogger(__name__)


class ModbusValueParser:

    def __init__(self, byte_order: Optional[ByteOrderConfig] = None):
        self._byte_order = byte_order or DEFAULT_BYTE_ORDER

    @property
    def byte_order(self) -> ByteOrderConfig:
        return self._byte_order

    @byte_order.setter
    def byte_order(self, value: ByteOrderConfig):
        self._byte_order = value

    def parse(
        self,
        registers: List[int],
        offset: int,
        data_type: RegisterDataType,
    ) -> Optional[Union[bool, int, float]]:
        """
        统一解析入口

        Args:
            registers: 原始寄存器值列表 (每个元素为0-65535的uint16)
            offset: 在registers中的起始偏移 (0-based)
            data_type: 数据类型枚举

        Returns:
            解析后的值, 失败返回None
            - COIL/DISCRETE_INPUT -> bool
            - HOLDING_INT16/INPUT_INT16 -> int
            - HOLDING_INT32 -> int
            - HOLDING_FLOAT32/INPUT_FLOAT32 -> float
        """
        if not registers:
            logger.warning("空寄存器列表")
            return None

        reg_count = data_type.get_register_count()

        if offset < 0 or offset + reg_count > len(registers):
            logger.warning(
                "偏移越界: offset=%d, need=%d, have=%d",
                offset,
                reg_count,
                len(registers),
            )
            return None

        if data_type in (RegisterDataType.COIL, RegisterDataType.DISCRETE_INPUT):
            return bool(registers[offset])

        if data_type in (RegisterDataType.HOLDING_INT16, RegisterDataType.INPUT_INT16):
            return int(registers[offset])

        if reg_count == 2:
            return self._parse_32bit(registers[offset], registers[offset + 1], data_type)

        logger.warning("不支持的数据类型: %s", data_type.code)
        return None

    def _parse_32bit(
        self,
        reg_high: int,
        reg_low: int,
        data_type: RegisterDataType,
    ) -> Optional[Union[int, float]]:
        """
        解析32位数据 (float32 / int32)

        流程:
        1. 打包为大端4字节
        2. ByteOrderConfig.swap_bytes_for_32bit() 重排
        3. struct.unpack 解析
        4. NaN/Inf 过滤 (仅float)
        """
        try:
            raw_bytes = struct.pack(">HH", int(reg_high), int(reg_low))
            swapped = self._byte_order.swap_bytes_for_32bit(raw_bytes)

            if data_type in (
                RegisterDataType.HOLDING_FLOAT32,
                RegisterDataType.INPUT_FLOAT32,
            ):
                fmt = self._byte_order.get_struct_format("float32")
                value = struct.unpack(fmt, swapped)[0]

                if math.isnan(value) or math.isinf(value):
                    logger.warning(
                        "NaN/Inf检测: regs=[0x%04X, 0x%04X] byte_order=%s",
                        reg_high,
                        reg_low,
                        self._byte_order.format_name,
                    )
                    return None

                return value

            if data_type == RegisterDataType.HOLDING_INT32:
                fmt = self._byte_order.get_struct_format("int32")
                return struct.unpack(fmt, swapped)[0]

            logger.warning("不支持的32位类型: %s", data_type.code)
            return None

        except Exception as e:
            logger.error(
                "32位解析异常: %s [regs=0x%04X,0x%04X type=%s order=%s]",
                e,
                reg_high,
                reg_low,
                data_type.code,
                self._byte_order.format_name,
            )
            return None

    def parse_batch(
        self,
        registers: List[int],
        points: List[RegisterPointConfig],
        start_addr: int,
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量解析 - 输出统一结构化格式

        Args:
            registers: 原始寄存器值列表
            points: 数据点配置列表 (RegisterPointConfig)
            start_addr: 读取起始地址 (0-based 或 1-based, 与point.address一致)

        Returns:
            {
                point_name: {
                    "raw": float/int/bool,    # 原始解析值
                    "value": str,             # 格式化显示值
                    "type": str,              # 数据类型代码
                    "alarm": Optional[str],   # "high"/"low"/None
                    "config": RegisterPointConfig,
                },
                ...
            }
            解析失败的点不会出现在结果中
        """
        result: Dict[str, Dict[str, Any]] = {}

        for point in points:
            offset = point.address - start_addr

            if offset < 0:
                logger.warning(
                    "点[%s]地址%d小于起始地址%d, 跳过",
                    point.name,
                    point.address,
                    start_addr,
                )
                continue

            raw_value = self.parse(registers, offset, point.data_type)

            if raw_value is None:
                logger.debug("点[%s]解析失败, 跳过", point.name)
                continue

            scaled_value = raw_value if isinstance(raw_value, bool) else float(raw_value) * point.scale

            formatted = point.format_value(raw_value)

            alarm = None
            if not isinstance(raw_value, bool) and point.alarm_high is not None or point.alarm_low is not None:
                alarm = point.check_alarm(scaled_value)

            result[point.name] = {
                "raw": raw_value,
                "scaled": scaled_value,
                "value": formatted,
                "type": point.data_type.code,
                "alarm": alarm,
                "config": point,
            }

        return result

    def parse_registers_legacy(
        self,
        registers: List[int],
        points: List[Any],
        start_addr: int,
        byte_order_str: str = "CDAB",
    ) -> Dict[str, str]:
        """
        兼容旧接口 - 返回 {name: formatted_string} 格式

        用于平滑迁移, 逐步替换 mcgs_modbus_reader._parse_all_points()

        Args:
            registers: 原始寄存器列表
            points: DevicePointConfig 列表 (旧格式)
            start_addr: 起始地址
            byte_order_str: 字节序字符串 ("ABCD"/"CDAB"/"BADC"/"DCBA")

        Returns:
            {参数名: 格式化字符串} 字典, 解析失败为 "N/A"
        """
        old_order = self._byte_order
        try:
            self._byte_order = ByteOrderConfig.from_string(byte_order_str)
        except ValueError:
            logger.warning("未知字节序 '%s', 使用当前配置", byte_order_str)

        parsed: Dict[str, str] = {}

        for point in points:
            try:
                offset = point.addr - start_addr
                reg_count = point.register_count

                if offset < 0 or offset + reg_count > len(registers):
                    parsed[point.name] = "N/A"
                    continue

                dtype_str = getattr(point, "type", "float")
                dtype_map = {
                    "float": RegisterDataType.HOLDING_FLOAT32,
                    "float32": RegisterDataType.HOLDING_FLOAT32,
                    "int16": RegisterDataType.HOLDING_INT16,
                    "uint16": RegisterDataType.HOLDING_INT16,
                    "int32": RegisterDataType.HOLDING_INT32,
                    "uint32": RegisterDataType.HOLDING_INT32,
                    "coil": RegisterDataType.COIL,
                    "di": RegisterDataType.DISCRETE_INPUT,
                }
                dtype = dtype_map.get(dtype_str, RegisterDataType.HOLDING_FLOAT32)

                raw_value = self.parse(registers, offset, dtype)

                if raw_value is None:
                    parsed[point.name] = "N/A"
                    continue

                if isinstance(raw_value, bool):
                    parsed[point.name] = "ON" if raw_value else "OFF"
                else:
                    scaled = float(raw_value) * point.scale
                    formatted = f"{scaled:.{point.decimal_places}f}"
                    if point.unit:
                        formatted += f" {point.unit}"
                    parsed[point.name] = formatted

            except Exception as e:
                logger.error("兼容解析异常 [%s]: %s", getattr(point, "name", "?"), e)
                parsed[getattr(point, "name", "?")] = "PARSE_ERR"

        self._byte_order = old_order
        return parsed
