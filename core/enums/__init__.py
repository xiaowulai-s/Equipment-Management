# -*- coding: utf-8 -*-
"""
Modbus寄存器数据类型枚举定义
Register Data Type Enum for Modbus Protocol

支持7种数据类型：
- COIL: 线圈状态（DO/继电器输出）
- DISCRETE_INPUT: 离散输入（DI/开关量采集）
- HOLDING_INT16/INT32/FLOAT32: 保持寄存器（可读写）
- INPUT_INT16/FLOAT32: 输入寄存器（只读）
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Any


class RegisterDataType(Enum):
    """
    Modbus寄存器数据类型枚举

    每个枚举值包含：
    - code: 数据类型代码（用于序列化）
    - display_name: 显示名称（用于UI展示）
    - read_function_code: 读取功能码（FC01/02/03/04）
    - write_function_codes: 支持的写操作功能码列表
    - writable: 是否可写
    """

    COIL = ("coil", "Coil", 1, [5, 15], True)
    DISCRETE_INPUT = ("discrete_input", "Discrete Input", 2, [], False)
    HOLDING_INT16 = ("holding_int16", "Holding Int16", 3, [6, 16], True)
    HOLDING_INT32 = ("holding_int32", "Holding Int32", 3, [6, 16], True)
    HOLDING_FLOAT32 = ("holding_float32", "Holding Float32", 3, [6, 16], True)
    INPUT_INT16 = ("input_int16", "Input Int16", 4, [], False)
    INPUT_FLOAT32 = ("input_float32", "Input Float32", 4, [], False)

    def __init__(
        self, code: str, display_name: str, read_function_code: int, write_function_codes: List[int], writable: bool
    ):
        self.code = code
        self.display_name = display_name
        self.read_function_code = read_function_code
        self.write_function_codes = write_function_codes
        self.writable = writable

    @classmethod
    def choices(cls) -> List[tuple]:
        """返回下拉框选项 [(code, display_name), ...]"""
        return [(item.code, item.display_name) for item in cls]

    @classmethod
    def from_code(cls, code: str) -> "RegisterDataType":
        """根据代码获取枚举值"""
        for item in cls:
            if item.code == code:
                return item
        raise ValueError(f"未知的数据类型代码: {code}")

    def get_register_count(self) -> int:
        """获取该数据类型占用的寄存器数量"""
        if self in (RegisterDataType.HOLDING_INT32, RegisterDataType.HOLDING_FLOAT32, RegisterDataType.INPUT_FLOAT32):
            return 2  # INT32和FLOAT32占用2个寄存器
        return 1


@dataclass
class RegisterPointConfig:
    """
    寄存器点配置数据类

    用于描述单个Modbus数据点的完整配置信息，
    包括数据类型、地址、显示格式、报警阈值等。

    Attributes:
        name: 参数名称（用户自定义显示名）
        data_type: 数据类型枚举值
        address: Modbus协议地址（0-based）
        decimal_places: 小数位数（用于格式化显示）
        scale: 缩放因子（原始值 × scale = 工程值）
        unit: 单位符号（如 ℃、MPa、m³/h 等）
        description: 描述说明
        alarm_high: 报警高限（超过此值触发高限报警）
        alarm_low: 报警低限（低于此值触发低限报警）
        writable: 是否可写（覆盖data_type默认值）
    """

    name: str
    data_type: RegisterDataType
    address: int
    decimal_places: int = 0
    scale: float = 1.0
    unit: str = ""
    description: str = ""
    alarm_high: Optional[float] = None
    alarm_low: Optional[float] = None
    writable: Optional[bool] = None  # None表示使用data_type默认值

    def __post_init__(self):
        """初始化后处理：如果writable为None，则使用data_type的默认值"""
        if self.writable is None:
            self.writable = self.data_type.writable

    def format_value(self, raw_value: Any) -> str:
        """
        根据配置格式化显示值

        处理逻辑：
        1. 布尔类型（COIL/DI）：显示 ON/OFF
        2. 数值类型：应用缩放因子 → 格式化小数位 → 添加单位

        Args:
            raw_value: 原始值（可以是bool/int/float）

        Returns:
            格式化后的字符串

        Examples:
            >>> config = RegisterPointConfig("温度", RegisterDataType.HOLDING_FLOAT32, 0,
            ...                             scale=0.1, unit="℃")
            >>> config.format_value(2560)
            '256.00 ℃'

            >>> config = RegisterPointConfig("阀1", RegisterDataType.COIL, 0)
            >>> config.format_value(True)
            'ON'
        """
        # 处理布尔类型（COIL/DI）
        if isinstance(raw_value, bool):
            return "ON" if raw_value else "OFF"

        # 处理数值类型
        try:
            # 应用缩放因子
            scaled_value = float(raw_value) * self.scale

            # 根据小数位数格式化
            if self.decimal_places > 0:
                formatted = f"{scaled_value:.{self.decimal_places}f}"
            else:
                formatted = f"{int(scaled_value)}"

            # 添加单位
            if self.unit:
                return f"{formatted} {self.unit}"
            return formatted

        except (ValueError, TypeError):
            return str(raw_value)

    def to_dict(self) -> dict:
        """转换为字典（用于序列化/存储）"""
        return {
            "name": self.name,
            "data_type": self.data_type.code,
            "address": self.address,
            "decimal_places": self.decimal_places,
            "scale": self.scale,
            "unit": self.unit,
            "description": self.description,
            "alarm_high": self.alarm_high,
            "alarm_low": self.alarm_low,
            "writable": self.writable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegisterPointConfig":
        """从字典创建实例（用于反序列化）"""
        data_type = RegisterDataType.from_code(data["data_type"])
        return cls(
            name=data["name"],
            data_type=data_type,
            address=data["address"],
            decimal_places=data.get("decimal_places", 0),
            scale=data.get("scale", 1.0),
            unit=data.get("unit", ""),
            description=data.get("description", ""),
            alarm_high=data.get("alarm_high"),
            alarm_low=data.get("alarm_low"),
            writable=data.get("writable"),
        )

    def check_alarm(self, value: float) -> Optional[str]:
        """
        检查值是否触发报警

        Args:
            value: 当前工程值（已应用缩放因子）

        Returns:
            报警类型字符串："high"/"low"/None
        """
        if self.alarm_high is not None and value > self.alarm_high:
            return "high"
        if self.alarm_low is not None and value < self.alarm_low:
            return "low"
        return None
