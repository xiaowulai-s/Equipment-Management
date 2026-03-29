"""
Modbus协议枚举定义

包含:
    - ProtocolType: 协议类型 (TCP / RTU / ASCII)
    - FunctionCode: Modbus标准功能码
    - DeviceStatus: 设备连接状态
    - RegisterType: 寄存器类型
    - DataType: 数据类型 (用于寄存器解析)
    - Endian: 字节序
"""

from __future__ import annotations

from enum import Enum, IntEnum

# ═══════════════════════════════════════════════════════════════
# 协议类型
# ═══════════════════════════════════════════════════════════════


class ProtocolType(Enum):
    """Modbus协议类型"""

    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    MODBUS_ASCII = "modbus_ascii"

    @classmethod
    def from_string(cls, value: str) -> "ProtocolType":
        """从字符串解析协议类型，忽略大小写和连字符"""
        normalized = value.lower().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"未知协议类型: '{value}'，" f"有效值: {[m.value for m in cls]}")

    def __str__(self) -> str:
        return self.value


# ═══════════════════════════════════════════════════════════════
# Modbus功能码 (Function Code)
# ═══════════════════════════════════════════════════════════════


class FunctionCode(IntEnum):
    """Modbus标准功能码

    位操作 (Bit Access):
        FC01: 读线圈 (Read Coils)
        FC02: 读离散输入 (Read Discrete Inputs)
        FC05: 写单个线圈 (Write Single Coil)
        FC15: 写多个线圈 (Write Multiple Coils)

    寄存器操作 (Register Access):
        FC03: 读保持寄存器 (Read Holding Registers)
        FC04: 读输入寄存器 (Read Input Registers)
        FC06: 写单个寄存器 (Write Single Register)
        FC16: 写多个寄存器 (Write Multiple Registers)
    """

    # 位操作
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    WRITE_SINGLE_COIL = 0x05
    WRITE_MULTIPLE_COILS = 0x0F

    # 寄存器操作
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_REGISTERS = 0x10

    @property
    def is_read(self) -> bool:
        """是否为读操作"""
        return self in (
            FunctionCode.READ_COILS,
            FunctionCode.READ_DISCRETE_INPUTS,
            FunctionCode.READ_HOLDING_REGISTERS,
            FunctionCode.READ_INPUT_REGISTERS,
        )

    @property
    def is_write(self) -> bool:
        """是否为写操作"""
        return self in (
            FunctionCode.WRITE_SINGLE_COIL,
            FunctionCode.WRITE_MULTIPLE_COILS,
            FunctionCode.WRITE_SINGLE_REGISTER,
            FunctionCode.WRITE_MULTIPLE_REGISTERS,
        )

    @property
    def is_bit_access(self) -> bool:
        """是否为位操作（线圈/离散输入）"""
        return self in (
            FunctionCode.READ_COILS,
            FunctionCode.READ_DISCRETE_INPUTS,
            FunctionCode.WRITE_SINGLE_COIL,
            FunctionCode.WRITE_MULTIPLE_COILS,
        )

    @property
    def is_register_access(self) -> bool:
        """是否为寄存器操作"""
        return not self.is_bit_access

    @property
    def description(self) -> str:
        """功能码中文描述"""
        descriptions = {
            FunctionCode.READ_COILS: "读线圈",
            FunctionCode.READ_DISCRETE_INPUTS: "读离散输入",
            FunctionCode.READ_HOLDING_REGISTERS: "读保持寄存器",
            FunctionCode.READ_INPUT_REGISTERS: "读输入寄存器",
            FunctionCode.WRITE_SINGLE_COIL: "写单个线圈",
            FunctionCode.WRITE_MULTIPLE_COILS: "写多个线圈",
            FunctionCode.WRITE_SINGLE_REGISTER: "写单个寄存器",
            FunctionCode.WRITE_MULTIPLE_REGISTERS: "写多个寄存器",
        }
        return descriptions.get(self, "未知功能码")


# ═══════════════════════════════════════════════════════════════
# 设备状态
# ═══════════════════════════════════════════════════════════════


class DeviceStatus(Enum):
    """设备连接状态"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

    @property
    def display_text(self) -> str:
        """显示文本"""
        texts = {
            DeviceStatus.DISCONNECTED: "已断开",
            DeviceStatus.CONNECTING: "连接中",
            DeviceStatus.CONNECTED: "已连接",
            DeviceStatus.RECONNECTING: "重连中",
            DeviceStatus.ERROR: "错误",
        }
        return texts.get(self, "未知")

    @property
    def is_connected(self) -> bool:
        return self == DeviceStatus.CONNECTED


# ═══════════════════════════════════════════════════════════════
# 寄存器类型
# ═══════════════════════════════════════════════════════════════


class RegisterType(Enum):
    """寄存器类型，对应Modbus功能码"""

    COIL = "coil"  # 线圈 (FC01/FC05/FC15)
    DISCRETE_INPUT = "discrete_input"  # 离散输入 (FC02)
    HOLDING_REGISTER = "holding_register"  # 保持寄存器 (FC03/FC06/FC16)
    INPUT_REGISTER = "input_register"  # 输入寄存器 (FC04)

    @property
    def read_function_code(self) -> FunctionCode:
        """对应的读功能码"""
        mapping = {
            RegisterType.COIL: FunctionCode.READ_COILS,
            RegisterType.DISCRETE_INPUT: FunctionCode.READ_DISCRETE_INPUTS,
            RegisterType.HOLDING_REGISTER: FunctionCode.READ_HOLDING_REGISTERS,
            RegisterType.INPUT_REGISTER: FunctionCode.READ_INPUT_REGISTERS,
        }
        return mapping[self]

    @property
    def write_function_code(self) -> FunctionCode:
        """对应的写功能码"""
        mapping = {
            RegisterType.COIL: FunctionCode.WRITE_SINGLE_COIL,
            RegisterType.HOLDING_REGISTER: FunctionCode.WRITE_SINGLE_REGISTER,
        }
        return mapping.get(self, FunctionCode.READ_HOLDING_REGISTERS)


# ═══════════════════════════════════════════════════════════════
# 数据类型 (用于寄存器值解析)
# ═══════════════════════════════════════════════════════════════


class DataType(Enum):
    """寄存器数据类型

    每种类型定义了占用的寄存器数量和字节大小。
    """

    INT16 = ("int16", 1, 2)
    UINT16 = ("uint16", 1, 2)
    INT32 = ("int32", 2, 4)
    UINT32 = ("uint32", 2, 4)
    FLOAT32 = ("float32", 2, 4)
    INT64 = ("int64", 4, 8)
    UINT64 = ("uint64", 4, 8)
    FLOAT64 = ("float64", 4, 8)
    BOOL = ("bool", 1, 2)
    STRING = ("string", -1, -1)  # 变长, 由配置指定

    def __init__(self, name: str, register_count: int, byte_size: int) -> None:
        self._name = name
        self.register_count = register_count
        self.byte_size = byte_size

    @property
    def format_char(self) -> str:
        """struct模块的格式字符"""
        mapping = {
            DataType.INT16: "h",
            DataType.UINT16: "H",
            DataType.INT32: "i",
            DataType.UINT32: "I",
            DataType.FLOAT32: "f",
            DataType.INT64: "q",
            DataType.UINT64: "Q",
            DataType.FLOAT64: "d",
        }
        return mapping.get(self, "H")


# ═══════════════════════════════════════════════════════════════
# 字节序
# ═══════════════════════════════════════════════════════════════


class Endian(Enum):
    """字节序"""

    BIG = "big"  # 大端 (ABCD)
    LITTLE = "little"  # 小端 (DCBA)
    BIG_SWAP = "big_swap"  # 大端字交换 (BADC) — Modbus常见
    LITTLE_SWAP = "little_swap"  # 小端字交换 (CDAB)
