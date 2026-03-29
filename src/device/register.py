"""
寄存器数据模型

设计原则:
    1. 单个寄存器的完整描述 (地址/类型/数据类型/名称/单位/报警阈值)
    2. 支持原始值(raw_value)和工程值(engineering_value)的转换
    3. 继承QObject, 支持Qt信号槽 (值变化通知)
    4. 支持JSON序列化/反序列化
    5. 内置缩放系数(linear scaling): eng_value = raw_value * scale + offset
    6. 支持报警阈值: 高高报/高报/低报/低低报

信号体系:
    value_changed(int, float) → (raw_value, engineering_value) 值变化
    alarm_triggered(str)     → 报警触发 (报警级别描述)
    alarm_cleared(str)       → 报警清除
"""

from __future__ import annotations

import logging
import math
import struct
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional, Union

from PySide6.QtCore import QObject, Signal

from src.protocols.enums import DataType, Endian, RegisterType

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 报警阈值配置
# ═══════════════════════════════════════════════════════════════


@dataclass
class AlarmConfig:
    """寄存器报警阈值配置

    支持四级报警: 高高报(HH) > 高报(H) > 低报(L) > 低低报(LL)
    任一阈值设为None表示禁用该级别报警。

    Attributes:
        high_high: 高高报警阈值 (最严重)
        high:      高报警阈值
        low:       低报警阈值
        low_low:   低低报警阈值
        deadband:  死区 (避免在阈值附近频繁触发/清除)
        enabled:   是否启用报警
    """

    high_high: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    low_low: Optional[float] = None
    deadband: float = 0.5
    enabled: bool = True

    def check_alarm(self, value: float) -> Optional[str]:
        """检查给定工程值是否触发报警

        检查顺序: 高高报 > 高报 > 低低报 > 低报
        (当值同时满足多个级别时, 返回最严重的)

        Args:
            value: 工程值

        Returns:
            报警级别字符串, 无报警返回None
        """
        if not self.enabled:
            return None

        # 高阈值 (从严重到轻微)
        if self.high_high is not None and value >= self.high_high:
            return "high_high"
        if self.high is not None and value >= self.high:
            return "high"
        # 低阈值 (从严重到轻微)
        if self.low_low is not None and value <= self.low_low:
            return "low_low"
        if self.low is not None and value <= self.low:
            return "low"
        return None

    def check_alarm_clear(self, value: float, current_alarm: str) -> bool:
        """检查报警是否应清除 (考虑死区)

        报警清除条件: 值回到阈值内部, 且与阈值的距离 >= deadband

        Args:
            value: 当前工程值
            current_alarm: 当前报警级别

        Returns:
            True表示报警应清除
        """
        if not self.enabled:
            return True

        db = self.deadband

        if current_alarm == "high_high" and self.high_high is not None:
            return value < (self.high_high - db)
        if current_alarm == "high" and self.high is not None:
            return value < (self.high - db)
        if current_alarm == "low" and self.low is not None:
            return value > (self.low + db)
        if current_alarm == "low_low" and self.low_low is not None:
            return value > (self.low_low + db)

        return False

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlarmConfig:
        """从字典反序列化"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ═══════════════════════════════════════════════════════════════
# 报警级别
# ═══════════════════════════════════════════════════════════════


class AlarmLevel:
    """报警级别常量"""

    NONE = "none"
    LOW_LOW = "low_low"  # 低低报 (较严重)
    LOW = "low"  # 低报
    HIGH = "high"  # 高报
    HIGH_HIGH = "high_high"  # 高高报 (最严重)

    # 严重程度排序 (数值越大越严重)
    SEVERITY = {
        "none": 0,
        "low": 1,
        "low_low": 2,
        "high": 3,
        "high_high": 4,
    }

    @classmethod
    def severity(cls, level: str) -> int:
        """获取报警严重程度"""
        return cls.SEVERITY.get(level, 0)

    @classmethod
    def display_text(cls, level: str) -> str:
        """获取报警级别显示文本"""
        mapping = {
            "none": "正常",
            "low": "低报",
            "low_low": "低低报",
            "high": "高报",
            "high_high": "高高报",
        }
        return mapping.get(level, "未知")

    @classmethod
    def color(cls, level: str) -> str:
        """获取报警级别对应颜色 (十六进制)"""
        mapping = {
            "none": "#4CAF50",  # 绿色
            "low": "#2196F3",  # 蓝色
            "low_low": "#FFC107",  # 黄色
            "high": "#FF9800",  # 橙色
            "high_high": "#F44336",  # 红色
        }
        return mapping.get(level, "#9E9E9E")


# ═══════════════════════════════════════════════════════════════
# 寄存器模型
# ═══════════════════════════════════════════════════════════════


class Register(QObject):
    """寄存器数据模型

    描述一个Modbus寄存器的完整配置和运行时状态。
    支持原始值→工程值的转换, 报警检测, JSON序列化。

    Attributes:
        name:          寄存器名称 (如: "温度", "压力")
        address:       寄存器起始地址
        register_type: 寄存器类型 (COIL/DISCRETE_INPUT/HOLDING_REGISTER/INPUT_REGISTER)
        data_type:     数据类型 (INT16/UINT16/INT32/FLOAT32等)
        quantity:      寄存器数量 (根据data_type自动计算, 也可手动指定)
        description:   描述信息
        unit:          工程单位 (如: "°C", "MPa", "rpm")
        scale:         缩放系数 (eng_value = raw_value * scale + offset)
        offset:        偏移量
        endianness:    字节序
        alarm_config:  报警阈值配置
        group:         分组名称 (用于UI分组显示)
        read_only:     是否只读
        writable:      是否可写 (综合考虑register_type和read_only)
    """

    # ── 信号 ──────────────────────────────────────────────────
    value_changed = Signal(int, float, object)  # raw_value, eng_value, timestamp
    alarm_triggered = Signal(str, float, str)  # alarm_level, value, message
    alarm_cleared = Signal(str, str)  # old_level, message
    config_changed = Signal(str)  # changed_property_name

    def __init__(
        self,
        name: str = "",
        address: int = 0,
        register_type: RegisterType = RegisterType.HOLDING_REGISTER,
        data_type: DataType = DataType.INT16,
        quantity: Optional[int] = None,
        description: str = "",
        unit: str = "",
        scale: float = 1.0,
        offset: float = 0.0,
        endianness: Endian = Endian.BIG,
        alarm_config: Optional[AlarmConfig] = None,
        group: str = "默认",
        read_only: bool = False,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self._name = name
        self._address = address
        self._register_type = register_type
        self._data_type = data_type
        self._quantity = quantity if quantity is not None else data_type.register_count
        self._description = description
        self._unit = unit
        self._scale = scale
        self._offset = offset
        self._endianness = endianness
        self._alarm_config = alarm_config if alarm_config is not None else AlarmConfig()
        self._group = group
        self._read_only = read_only

        # ── 运行时状态 ──
        self._raw_value: int = 0
        self._engineering_value: float = 0.0
        self._current_alarm: str = AlarmLevel.NONE
        self._last_update: Optional[datetime] = None
        self._quality: str = "good"  # good / uncertain / bad

    # ═══════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.config_changed.emit("name")

    @property
    def address(self) -> int:
        return self._address

    @address.setter
    def address(self, value: int) -> None:
        if value < 0:
            raise ValueError(f"寄存器地址不能为负数: {value}")
        if value > 65535:
            raise ValueError(f"寄存器地址超出范围(0-65535): {value}")
        self._address = value
        self.config_changed.emit("address")

    @property
    def register_type(self) -> RegisterType:
        return self._register_type

    @register_type.setter
    def register_type(self, value: RegisterType) -> None:
        self._register_type = value
        self.config_changed.emit("register_type")

    @property
    def data_type(self) -> DataType:
        return self._data_type

    @data_type.setter
    def data_type(self, value: DataType) -> None:
        self._data_type = value
        # 自动更新quantity (除非用户手动指定过)
        self._quantity = value.register_count
        self.config_changed.emit("data_type")

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: int) -> None:
        if value < 1:
            raise ValueError(f"寄存器数量不能小于1: {value}")
        self._quantity = value
        self.config_changed.emit("quantity")

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value
        self.config_changed.emit("description")

    @property
    def unit(self) -> str:
        return self._unit

    @unit.setter
    def unit(self, value: str) -> None:
        self._unit = value
        self.config_changed.emit("unit")

    @property
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        self._scale = value
        self.config_changed.emit("scale")

    @property
    def offset(self) -> float:
        return self._offset

    @offset.setter
    def offset(self, value: float) -> None:
        self._offset = value
        self.config_changed.emit("offset")

    @property
    def endianness(self) -> Endian:
        return self._endianness

    @endianness.setter
    def endianness(self, value: Endian) -> None:
        self._endianness = value
        self.config_changed.emit("endianness")

    @property
    def alarm_config(self) -> AlarmConfig:
        return self._alarm_config

    @alarm_config.setter
    def alarm_config(self, value: AlarmConfig) -> None:
        self._alarm_config = value
        self.config_changed.emit("alarm_config")

    @property
    def group(self) -> str:
        return self._group

    @group.setter
    def group(self, value: str) -> None:
        self._group = value
        self.config_changed.emit("group")

    @property
    def read_only(self) -> bool:
        return self._read_only

    @read_only.setter
    def read_only(self, value: bool) -> None:
        self._read_only = value
        self.config_changed.emit("read_only")

    @property
    def writable(self) -> bool:
        """是否可写 = register_type支持写 且 非只读"""
        if self._read_only:
            return False
        # 只有COIL和HOLDING_REGISTER支持写操作
        return self._register_type in (
            RegisterType.COIL,
            RegisterType.HOLDING_REGISTER,
        )

    # ═══════════════════════════════════════════════════════════
    # 运行时状态属性 (只读)
    # ═══════════════════════════════════════════════════════════

    @property
    def raw_value(self) -> int:
        """原始寄存器值"""
        return self._raw_value

    @property
    def engineering_value(self) -> float:
        """工程值 (经过缩放转换)"""
        return self._engineering_value

    @property
    def current_alarm(self) -> str:
        """当前报警级别"""
        return self._current_alarm

    @property
    def last_update(self) -> Optional[datetime]:
        """最后更新时间"""
        return self._last_update

    @property
    def quality(self) -> str:
        """数据质量"""
        return self._quality

    @property
    def is_alarmed(self) -> bool:
        """是否处于报警状态"""
        return self._current_alarm != AlarmLevel.NONE

    @property
    def end_address(self) -> int:
        """结束地址 (address + quantity - 1)"""
        return self._address + self._quantity - 1

    # ═══════════════════════════════════════════════════════════
    # 值更新
    # ═══════════════════════════════════════════════════════════

    def update_raw_value(self, raw_value: int) -> None:
        """更新原始值, 自动计算工程值并检测报警

        Args:
            raw_value: 原始寄存器值
        """
        old_raw = self._raw_value
        self._raw_value = raw_value

        # 计算工程值
        self._engineering_value = self._raw_to_engineering(raw_value)

        # 更新时间
        self._last_update = datetime.now()
        self._quality = "good"

        # 报警检测
        self._check_alarm(self._engineering_value)

        # 发射信号 (仅当值变化时)
        if old_raw != raw_value:
            self.value_changed.emit(
                self._raw_value,
                self._engineering_value,
                self._last_update,
            )

    def update_engineering_value(self, eng_value: float) -> None:
        """直接更新工程值 (反向计算原始值)

        Args:
            eng_value: 工程值
        """
        # 反向计算原始值
        if self._scale != 0:
            raw = (eng_value - self._offset) / self._scale
        else:
            raw = eng_value - self._offset
        self._raw_value = int(round(raw))

        self._engineering_value = eng_value
        self._last_update = datetime.now()
        self._quality = "good"

        self._check_alarm(eng_value)

        self.value_changed.emit(
            self._raw_value,
            self._engineering_value,
            self._last_update,
        )

    def set_bad_quality(self) -> None:
        """标记数据质量为bad (通信失败等)"""
        self._quality = "bad"

    def clear_value(self) -> None:
        """清除当前值"""
        self._raw_value = 0
        self._engineering_value = 0.0
        self._last_update = None
        self._quality = "uncertain"

    # ═══════════════════════════════════════════════════════════
    # 值转换
    # ═══════════════════════════════════════════════════════════

    def _raw_to_engineering(self, raw_value: int) -> float:
        """原始值 → 工程值

        公式: engineering_value = raw_value * scale + offset
        """
        return raw_value * self._scale + self._offset

    def engineering_to_raw(self, eng_value: float) -> int:
        """工程值 → 原始值

        公式: raw_value = (eng_value - offset) / scale
        """
        if self._scale == 0:
            return int(round(eng_value - self._offset))
        return int(round((eng_value - self._offset) / self._scale))

    def format_engineering_value(self) -> str:
        """格式化工程值为显示字符串 (带单位)"""
        if self._quality == "bad":
            return "---"
        if self._quality == "uncertain":
            return "?"

        # 根据数据类型决定小数位
        if self._data_type in (
            DataType.FLOAT32,
            DataType.FLOAT64,
        ):
            value_str = f"{self._engineering_value:.2f}"
        elif self._scale != 1.0 or self._offset != 0.0:
            # 有缩放/偏移时显示2位小数
            value_str = f"{self._engineering_value:.2f}"
        else:
            value_str = f"{self._engineering_value}"

        if self._unit:
            return f"{value_str} {self._unit}"
        return value_str

    # ═══════════════════════════════════════════════════════════
    # 报警
    # ═══════════════════════════════════════════════════════════

    def _check_alarm(self, eng_value: float) -> None:
        """检测报警状态"""
        alarm = self._alarm_config.check_alarm(eng_value)

        if alarm is not None and self._current_alarm == AlarmLevel.NONE:
            # 新报警
            self._current_alarm = alarm
            message = f"[{self._name}] {AlarmLevel.display_text(alarm)}: " f"{eng_value:.2f} {self._unit}"
            logger.warning(message)
            self.alarm_triggered.emit(alarm, eng_value, message)

        elif alarm is not None and self._current_alarm != alarm:
            # 报警级别变化
            if AlarmLevel.severity(alarm) > AlarmLevel.severity(self._current_alarm):
                # 升级
                old = self._current_alarm
                self._current_alarm = alarm
                message = (
                    f"[{self._name}] 报警升级 {AlarmLevel.display_text(old)}"
                    f"→{AlarmLevel.display_text(alarm)}: "
                    f"{eng_value:.2f} {self._unit}"
                )
                logger.warning(message)
                self.alarm_triggered.emit(alarm, eng_value, message)
            else:
                # 降级 (保持当前更高级别报警, 不清除)
                pass

        elif alarm is None and self._current_alarm != AlarmLevel.NONE:
            # 检查死区, 判断是否应清除
            if self._alarm_config.check_alarm_clear(eng_value, self._current_alarm):
                old = self._current_alarm
                self._current_alarm = AlarmLevel.NONE
                message = f"[{self._name}] {AlarmLevel.display_text(old)}已清除: " f"{eng_value:.2f} {self._unit}"
                logger.info(message)
                self.alarm_cleared.emit(old, message)

    # ═══════════════════════════════════════════════════════════
    # 字节解析 (原始字节 → 寄存器值)
    # ═══════════════════════════════════════════════════════════

    def parse_bytes(self, data: bytes) -> int:
        """将原始字节解析为寄存器原始值

        Args:
            data: 原始字节数据 (长度应匹配data_type.byte_size)

        Returns:
            解析后的原始值

        Raises:
            ValueError: 数据长度不匹配
        """
        expected_size = self._data_type.byte_size
        if expected_size < 0:
            expected_size = len(data)  # 变长类型(STRING)

        if len(data) < expected_size:
            raise ValueError(f"数据长度不足: 期望{expected_size}字节, 实际{len(data)}字节")

        return self._decode_bytes(data[:expected_size])

    def _decode_bytes(self, data: bytes) -> int:
        """根据字节序解码字节数据"""
        endian_map = {
            Endian.BIG: ">",
            Endian.LITTLE: "<",
            Endian.BIG_SWAP: ">",
            Endian.LITTLE_SWAP: "<",
        }
        prefix = endian_map.get(self._endianness, ">")
        fmt_char = self._data_type.format_char

        if self._data_type == DataType.INT16:
            return struct.unpack(f"{prefix}{fmt_char}", data)[0]
        elif self._data_type == DataType.UINT16:
            return struct.unpack(f"{prefix}{fmt_char}", data)[0]
        elif self._data_type in (DataType.INT32, DataType.UINT32, DataType.FLOAT32):
            return struct.unpack(f"{prefix}{fmt_char}", data)[0]
        elif self._data_type in (DataType.INT64, DataType.UINT64, DataType.FLOAT64):
            return struct.unpack(f"{prefix}{fmt_char}", data)[0]
        elif self._data_type == DataType.BOOL:
            return data[0] & 0x01
        else:
            # STRING或其他: 返回第一个字节
            return data[0]

    # ═══════════════════════════════════════════════════════════
    # 序列化
    # ═══════════════════════════════════════════════════════════

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self._name,
            "address": self._address,
            "register_type": self._register_type.value,
            "data_type": self._data_type.value[0],  # 取元组第一个元素
            "quantity": self._quantity,
            "description": self._description,
            "unit": self._unit,
            "scale": self._scale,
            "offset": self._offset,
            "endianness": self._endianness.value,
            "alarm_config": self._alarm_config.to_dict(),
            "group": self._group,
            "read_only": self._read_only,
            # 运行时状态
            "raw_value": self._raw_value,
            "engineering_value": self._engineering_value,
            "current_alarm": self._current_alarm,
            "last_update": (self._last_update.isoformat() if self._last_update else None),
            "quality": self._quality,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Register:
        """从字典反序列化

        Args:
            data: 寄存器配置字典

        Returns:
            Register实例
        """
        # 解析枚举
        reg_type = RegisterType(data["register_type"])
        data_type = cls._parse_data_type(data.get("data_type", "int16"))
        endian = Endian(data.get("endianness", "big"))

        # 解析报警配置
        alarm_data = data.get("alarm_config")
        alarm_config = AlarmConfig.from_dict(alarm_data) if alarm_data else AlarmConfig()

        register = cls(
            name=data.get("name", ""),
            address=data.get("address", 0),
            register_type=reg_type,
            data_type=data_type,
            quantity=data.get("quantity"),
            description=data.get("description", ""),
            unit=data.get("unit", ""),
            scale=data.get("scale", 1.0),
            offset=data.get("offset", 0.0),
            endianness=endian,
            alarm_config=alarm_config,
            group=data.get("group", "默认"),
            read_only=data.get("read_only", False),
        )

        # 恢复运行时状态 (如果有)
        if "raw_value" in data:
            register._raw_value = data["raw_value"]
        if "engineering_value" in data:
            register._engineering_value = data["engineering_value"]
        if "current_alarm" in data:
            register._current_alarm = data["current_alarm"]
        if data.get("last_update"):
            register._last_update = datetime.fromisoformat(data["last_update"])
        if "quality" in data:
            register._quality = data["quality"]

        return register

    @staticmethod
    def _parse_data_type(value: Any) -> DataType:
        """解析数据类型 (支持字符串和DataType枚举)"""
        if isinstance(value, DataType):
            return value
        if isinstance(value, str):
            for dt in DataType:
                if dt.value[0] == value.lower():
                    return dt
            raise ValueError(f"未知数据类型: '{value}'")
        return DataType.INT16

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        return (
            f"Register(name='{self._name}', addr={self._address}, "
            f"type={self._register_type.value}, "
            f"dtype={self._data_type.value[0]}, "
            f"value={self._engineering_value}"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Register):
            return NotImplemented
        return self._address == other._address and self._register_type == other._register_type

    def __hash__(self) -> int:
        return hash((self._address, self._register_type))

    def overlaps(self, other: Register) -> bool:
        """检查与另一个寄存器是否存在地址重叠

        Args:
            other: 另一个寄存器

        Returns:
            True表示地址范围有重叠
        """
        if self._register_type != other._register_type:
            return False
        return not (self.end_address < other._address or other.end_address < self._address)
