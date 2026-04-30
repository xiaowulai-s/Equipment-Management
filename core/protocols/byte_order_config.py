# -*- coding: utf-8 -*-
"""
Modbus字节序配置模块
Modbus Byte Order Configuration Module

支持4种标准Modbus字节序格式：
- ABCD: 大端序（Big-Endian） - 标准Modbus, 西门子
- BADC: 字节交换大端 - 某些日本设备
- CDAB: 小端序（Little-Endian） - Intel x86, 三菱
- DCBA: 字节交换小端 - 某些专用控制器

技术说明：
对于32位数据（如float32, int32），Modbus使用2个16位寄存器存储。
字节序配置决定了这4个字节的排列方式：

  地址递增方向 →
+------+------+------+------+
|  A   |  B   |  C   |  D   |    原始字节序列
+------+------+------+------+

ABCD (Big-Endian):     [A][B][C][D] → struct.unpack(">f", data)
BADC (Byte-Swap Big):  [B][A][D][C] → 字节交换后大端解析
CDAB (Little-Endian):  [C][D][A][B] → struct.unpack("<f", data)
DCBA (Byte-Swap Little):[D][C][B][A] → 字节交换后小端解析
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ByteOrderConfig:
    """
    字节序配置（不可变对象，线程安全）

    Attributes:
        byte_order: 字节序 ("big" 或 "little")
        word_order: 字序 ("big" 或 "little")

    线程安全：
    - 使用 frozen=True 使其成为不可变对象
    - 可在多线程环境中安全共享
    - 无需锁保护

    性能：
    - 创建开销 < 1μs
    - 属性访问 O(1)
    """

    byte_order: str = "big"  # 字节序: "big" 或 "little"
    word_order: str = "big"  # 字序: "big" 或 "little"

    def __post_init__(self):
        """验证参数有效性"""
        valid_byte_orders = {"big", "little"}
        if self.byte_order not in valid_byte_orders:
            raise ValueError(f"无效的byte_order: '{self.byte_order}'，" f"必须是 {valid_byte_orders} 之一")
        if self.word_order not in valid_byte_orders:
            raise ValueError(f"无效的word_order: '{self.word_order}'，" f"必须是 {valid_byte_orders} 之一")

    # ==================== 预设格式工厂方法 ====================

    @classmethod
    def ABCD(cls) -> "ByteOrderConfig":
        """
        ABCD格式: 大端序（Big-Endian）- 默认格式

        字节排列: [A][B][C][D]
        适用厂商: 标准Modbus设备, 西门子PLC

        示例（float32值123.456）:
        原始字节: 0x42 F6 E9 79
        解析为: 123.456
        """
        return cls(byte_order="big", word_order="big")

    @classmethod
    def BADC(cls) -> "ByteOrderConfig":
        """
        BADC格式: 字节交换大端（Mid-Big-Endian）

        字节排列: [B][A][D][C]
        适用厂商: 某些日本设备（如欧姆龙部分型号）

        说明:
        - Word内字节交换，但Word顺序保持大端
        - 每个16位字内部高低字节互换

        示例（float32值123.456）:
        原始字节: 0xF6 42 79 E9
        交换后:   0x42 F6 E9 79 → 123.456
        """
        return cls(byte_order="little", word_order="big")

    @classmethod
    def CDAB(cls) -> "ByteOrderConfig":
        """
        CDAB格式: 小端序（Little-Endian）

        字节排列: [C][D][A][B]
        适用厂商: Intel x86架构, 三菱PLC, 大多数PC软件

        示例（float32值123.456）:
        原始字节: 0xE9 79 F6 42
        解析为: 123.456
        """
        return cls(byte_order="big", word_order="little")

    @classmethod
    def DCBA(cls) -> "ByteOrderConfig":
        """
        DCBA格式: 字节交换小端（Mid-Little-Endian）

        字节排列: [D][C][B][A]
        适用厂商: 某些专用控制器（如ABB部分驱动器）

        说明:
        - Word内字节交换，但Word顺序保持小端
        - 每个16位字内部高低字节互换

        示例（float32值123.456）:
        原始字节: 0x79 E9 42 F6
        交换后:   0xE9 79 F6 42 → 123.456
        """
        return cls(byte_order="little", word_order="little")

    # ==================== 字符串转换 ====================

    @classmethod
    def from_string(cls, format_str: str) -> "ByteOrderConfig":
        """
        从字符串创建字节序配置

        Args:
            format_str: 格式名称 ("ABCD", "BADC", "CDAB", "DCBA")
                       或组合形式 ("big-big", "little-little" 等)

        Returns:
            对应的ByteOrderConfig实例

        Raises:
            ValueError: 格式字符串无效

        Examples:
            >>> config = ByteOrderConfig.from_string("ABCD")
            >>> config = ByteOrderConfig.from_string("CDAB")
            >>> config = ByteOrderConfig.from_string("big-little")  # 等同于CDAB
        """
        format_str = format_str.upper().strip()

        # 直接匹配预设格式
        preset_map = {
            "ABCD": cls.ABCD(),
            "BADC": cls.BADC(),
            "CDAB": cls.CDAB(),
            "DCBA": cls.DCBA(),
        }

        if format_str in preset_map:
            return preset_map[format_str]

        # 尝试解析组合形式 "byte_order-word_order"
        if "-" in format_str:
            parts = format_str.split("-")
            if len(parts) == 2:
                bo, wo = parts
                if bo in ("BIG", "LITTLE") and wo in ("BIG", "LITTLE"):
                    return cls(byte_order=bo.lower(), word_order=wo.lower())

        raise ValueError(
            f"无效的字节序格式: '{format_str}'\n"
            f"支持的格式: ABCD, BADC, CDAB, DCBA\n"
            f"或组合形式: big-big, big-little, little-big, little-little"
        )

    @property
    def format_name(self) -> str:
        """
        返回格式名称

        Returns:
            "ABCD", "BADC", "CDAB" 或 "DCBA"
        """
        format_names = {
            ("big", "big"): "ABCD",
            ("little", "big"): "BADC",
            ("big", "little"): "CDAB",
            ("little", "little"): "DCBA",
        }
        return format_names.get((self.byte_order, self.word_order), "UNKNOWN")

    @property
    def description(self) -> str:
        """返回格式的中文描述"""
        descriptions = {
            "ABCD": "大端序（Big-Endian）",
            "BADC": "字节交换大端",
            "CDAB": "小端序（Little-Endian）",
            "DCBA": "字节交换小端",
        }
        return descriptions.get(self.format_name, "未知格式")

    # ==================== 实用方法 ====================

    def swap_bytes_for_32bit(self, data: bytes) -> bytes:
        """
        根据32位数据的字节序配置进行字节交换

        对于32位数据（4字节），根据配置返回正确排序的字节。
        返回的数据始终使用大端序（可直接用">f"等格式解析）

        Args:
            data: 原始4字节数据（从Modbus寄存器按地址顺序读取的字节）

        Returns:
            重新排序后的4字节数据，可直接用于struct.unpack(">f")等

        算法说明（基于Modbus规范）：
        输入: [A, B, C, D] （A=reg[N]高字节, B=reg[N]低字节, C=reg[N+1]高字节, D=reg[N+1]低字节）

        ABCD (big-big):     不交换 → [A, B, C, D]
        BADC (little-big):  Word内交换 → [B, A, D, C]
        CDAB (big-little):  Word间交换 → [C, D, A, B]
        DCBA (little-little):两者都交换 → [D, C, B, A]

        所有格式最终都转换为大端序，统一使用">"前缀解析
        """
        if len(data) != 4:
            raise ValueError(f"期望4字节数据，收到{len(data)}字节")

        b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

        if self.format_name == "ABCD":
            # 大端序: [A][B][C][D] - 不需要交换
            return data
        elif self.format_name == "BADC":
            # 字节交换大端: [B][A][D][C] - 每个word内高低字节互换
            return bytes([b1, b0, b3, b2])
        elif self.format_name == "CDAB":
            # 小端序: [C][D][A][B] - word顺序反转（低字在前）
            return bytes([b2, b3, b0, b1])
        else:  # DCBA
            # 字节交换小端: [D][C][B][A] - 完全反转
            return bytes([b3, b2, b1, b0])

    def swap_bytes_for_64bit(self, data: bytes) -> bytes:
        """
        根据64位数据的字节序配置进行字节交换

        64位数据由4个16位字组成: [W1, W2, W3, W4]
        每个word 2字节: Wi = [Hi, Li]

        Args:
            data: 原始8字节数据

        Returns:
            重新排序后的8字节数据（大端序）
        """
        if len(data) != 8:
            raise ValueError(f"期望8字节数据，收到{len(data)}字节")

        # 将8字节分解为4个word
        w0_h, w0_l = data[0], data[1]  # Word 1
        w1_h, w1_l = data[2], data[3]  # Word 2
        w2_h, w2_l = data[4], data[5]  # Word 3
        w3_h, w3_l = data[6], data[7]  # Word 4

        if self.format_name == "ABCD":
            # 不交换
            return data
        elif self.format_name == "BADC":
            # Word内字节交换（每个word的高低字节互换）
            return bytes(
                [
                    w0_l,
                    w0_h,
                    w1_l,
                    w1_h,
                    w2_l,
                    w2_h,
                    w3_l,
                    w3_h,
                ]
            )
        elif self.format_name == "CDAB":
            # Word间交换（反转word顺序：低字在前）
            # 原始: [W1, W2, W3, W4] -> [W4, W3, W2, W1]
            return bytes(
                [
                    w3_h,
                    w3_l,  # Word 4 (最低有效字) 移到最前
                    w2_h,
                    w2_l,  # Word 3
                    w1_h,
                    w1_l,  # Word 2
                    w0_h,
                    w0_l,  # Word 1 (最高有效字)
                ]
            )
        else:  # DCBA
            # 两者都交换（先反转word顺序，再每个word内字节交换）
            # 原始: [W1, W2, W3, W4] -> [~W4, ~W3, ~W2, ~W1]
            return bytes(
                [
                    w3_l,
                    w3_h,  # Word 4 字节交换后移到最前
                    w2_l,
                    w2_h,  # Word 3 字节交换
                    w1_l,
                    w1_h,  # Word 2 字节交换
                    w0_l,
                    w0_h,  # Word 1 字节交换
                ]
            )

    def get_struct_format(self, dtype: str) -> str:
        """
        获取用于struct.unpack的格式字符

        由于 swap_bytes_for_32bit/64bit 已经将数据转换为大端序，
        此方法始终返回大端格式。

        Args:
            dtype: 数据类型 ("int32", "uint32", "float32", "float64", "int64", "uint64")

        Returns:
            struct格式字符串（如 ">i", ">f" 等）
        """
        type_chars = {
            "int32": "i",
            "uint32": "I",
            "float32": "f",
            "float64": "d",
            "int64": "q",
            "uint64": "Q",
        }

        char = type_chars.get(dtype)
        if char is None:
            raise ValueError(f"不支持的数据类型: {dtype}")

        # 统一使用大端序解析（swap_bytes方法已处理字节序转换）
        return ">" + char

    def __repr__(self) -> str:
        return f"ByteOrderConfig({self.format_name})"

    def __str__(self) -> str:
        return f"{self.format_name} ({self.description})"


# 全局默认配置
DEFAULT_BYTE_ORDER = ByteOrderConfig.ABCD()


# 预设格式列表（用于UI下拉框）
BYTE_ORDER_PRESETS: List[Tuple[str, str, str]] = [
    ("ABCD", "大端序（Big-Endian）", "标准Modbus, 西门子"),
    ("BADC", "字节交换大端", "某些日本设备"),
    ("CDAB", "小端序（Little-Endian）", "Intel x86, 三菱"),
    ("DCBA", "字节交换小端", "某些专用控制器"),
]


# 常见厂商设备推荐配置
VENDOR_BYTE_ORDER_RECOMMENDATIONS: Dict[str, str] = {
    # PLC厂商
    "西门子": "ABCD",
    "Siemens": "ABCD",
    "三菱": "CDAB",
    "Mitsubishi": "CDAB",
    "欧姆龙": "BADC",  # 部分型号
    "Omron": "BADC",
    "罗克韦尔": "ABCD",
    "Rockwell": "ABCD",
    "施耐德": "ABCD",
    "Schneider": "ABCD",
    # 仪表厂商
    "横河": "ABCD",
    "Yokogawa": "ABCD",
    "E+H": "ABCD",
    "Endress+Hauser": "ABCD",
    # 驱动器/变频器
    "ABB": "DCBA",  # 部分型号
    "丹纳赫": "CDAB",
    "Danaher": "CDAB",
    # 通用
    "默认": "ABCD",
    "Default": "ABCD",
}
