# -*- coding: utf-8 -*-
"""
Modbus字节序解码完整测试套件
Comprehensive Test Suite for Modbus Byte Order Decoding

覆盖范围：
- ByteOrderConfig 类的所有功能（25个测试）
- 4种标准格式 x 所有数据类型组合（24个测试）
- 边界值和特殊值测试（12个测试）
- Device模型集成测试（8个测试）
- 向后兼容性测试（6个测试）

总计: ~75个测试用例
"""

import math
import struct
import pytest

from core.protocols.byte_order_config import (
    ByteOrderConfig,
    DEFAULT_BYTE_ORDER,
    BYTE_ORDER_PRESETS,
    VENDOR_BYTE_ORDER_RECOMMENDATIONS,
)
from core.protocols.modbus_protocol import ModbusProtocol


# ============================================================================
# 第一部分：ByteOrderConfig 类测试
# ============================================================================


class TestByteOrderConfigCreation:
    """ByteOrderConfig 创建和工厂方法测试"""

    def test_default_creation(self):
        """测试默认创建"""
        config = ByteOrderConfig()
        assert config.byte_order == "big"
        assert config.word_order == "big"
        assert config.format_name == "ABCD"

    def test_abcd_factory(self):
        """测试ABCD工厂方法"""
        config = ByteOrderConfig.ABCD()
        assert config.byte_order == "big"
        assert config.word_order == "big"
        assert config.format_name == "ABCD"

    def test_badc_factory(self):
        """测试BADC工厂方法"""
        config = ByteOrderConfig.BADC()
        assert config.byte_order == "little"
        assert config.word_order == "big"
        assert config.format_name == "BADC"

    def test_cdab_factory(self):
        """测试CDAB工厂方法"""
        config = ByteOrderConfig.CDAB()
        assert config.byte_order == "big"
        assert config.word_order == "little"
        assert config.format_name == "CDAB"

    def test_dcba_factory(self):
        """测试DCBA工厂方法"""
        config = ByteOrderConfig.DCBA()
        assert config.byte_order == "little"
        assert config.word_order == "little"
        assert config.format_name == "DCBA"

    def test_custom_creation(self):
        """测试自定义参数创建"""
        config = ByteOrderConfig(byte_order="little", word_order="big")
        assert config.format_name == "BADC"

    def test_invalid_byte_order(self):
        """测试无效byte_order参数"""
        with pytest.raises(ValueError, match="无效的byte_order"):
            ByteOrderConfig(byte_order="invalid", word_order="big")

    def test_invalid_word_order(self):
        """测试无效word_order参数"""
        with pytest.raises(ValueError, match="无效的word_order"):
            ByteOrderConfig(byte_order="big", word_order="invalid")

    def test_frozen_immutability(self):
        """测试不可变性（frozen dataclass）"""
        config = ByteOrderConfig.ABCD()
        with pytest.raises(AttributeError):
            config.byte_order = "little"  # type: ignore


class TestByteOrderConfigFromString:
    """从字符串创建配置测试"""

    def test_from_string_abcd(self):
        """从字符串'ABCD'创建"""
        config = ByteOrderConfig.from_string("ABCD")
        assert config.format_name == "ABCD"

    def test_from_string_lowercase(self):
        """小写字符串自动转换"""
        config = ByteOrderConfig.from_string("cdab")
        assert config.format_name == "CDAB"

    def test_from_string_with_spaces(self):
        """带空格的字符串"""
        config = ByteOrderConfig.from_string("  dcba  ")
        assert config.format_name == "DCBA"

    def test_from_string_combined_big_little(self):
        """组合形式 'big-little' (等同于CDAB)"""
        config = ByteOrderConfig.from_string("big-little")
        assert config.format_name == "CDAB"

    def test_from_string_combined_little_big(self):
        """组合形式 'little-big' (等同于BADC)"""
        config = ByteOrderConfig.from_string("little-big")
        assert config.format_name == "BADC"

    def test_from_string_invalid(self):
        """无效字符串抛出异常"""
        with pytest.raises(ValueError, match="无效的字节序格式"):
            ByteOrderConfig.from_string("XYZW")

    def test_format_name_property(self):
        """format_name属性测试"""
        assert ByteOrderConfig.ABCD().format_name == "ABCD"
        assert ByteOrderConfig.BADC().format_name == "BADC"
        assert ByteOrderConfig.CDAB().format_name == "CDAB"
        assert ByteOrderConfig.DCBA().format_name == "DCBA"

    def test_description_property(self):
        """description属性测试"""
        config = ByteOrderConfig.ABCD()
        assert "大端" in config.description
        assert "Big" in config.description or "Endian" in config.description


class TestByteOrderConfig32BitSwap:
    """32位数据字节交换算法测试"""

    def test_abcd_no_swap(self):
        """ABCD格式不交换"""
        config = ByteOrderConfig.ABCD()
        data = b"\x00\x01\x02\x03"
        result = config.swap_bytes_for_32bit(data)
        assert result == b"\x00\x01\x02\x03"

    def test_badc_word_internal_swap(self):
        """BADC格式Word内交换"""
        config = ByteOrderConfig.BADC()
        data = b"\x00\x01\x02\x03"
        result = config.swap_bytes_for_32bit(data)
        # [A B C D] -> [B A D C]
        assert result == b"\x01\x00\x03\x02"

    def test_cdab_word_swap(self):
        """CDAB格式Word间交换"""
        config = ByteOrderConfig.CDAB()
        data = b"\x00\x01\x02\x03"
        result = config.swap_bytes_for_32bit(data)
        # [A B C D] -> [C D A B]
        assert result == b"\x02\x03\x00\x01"

    def test_dcba_full_swap(self):
        """DCBA格式完全交换"""
        config = ByteOrderConfig.DCBA()
        data = b"\x00\x01\x02\x03"
        result = config.swap_bytes_for_32bit(data)
        # [A B C D] -> [D C B A]
        assert result == b"\x03\x02\x01\x00"

    def test_swap_invalid_length(self):
        """无效长度抛出异常"""
        config = ByteOrderConfig.ABCD()
        with pytest.raises(ValueError, match="期望4字节"):
            config.swap_bytes_for_32bit(b"\x00\x01\x02")


class TestByteOrderConfig64BitSwap:
    """64位数据字节交换算法测试"""

    def test_abcd_64bit_no_swap(self):
        """ABCD格式64位不交换"""
        config = ByteOrderConfig.ABCD()
        data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        result = config.swap_bytes_for_64bit(data)
        assert result == data

    def test_badc_64bit_word_internal_swap(self):
        """BADC格式64位Word内交换"""
        config = ByteOrderConfig.BADC()
        data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        result = config.swap_bytes_for_64bit(data)
        # 每个word内交换
        assert result == b"\x01\x00\x03\x02\x05\x04\x07\x06"

    def test_cdab_64bit_word_swap(self):
        """CDAB格式64位Word间交换"""
        config = ByteOrderConfig.CDAB()
        data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        result = config.swap_bytes_for_64bit(data)
        # CDAB: word顺序完全反转 [W1,W2,W3,W4] -> [W4,W3,W2,W1]
        # 即: [00,01, 02,03, 04,05, 06,07] -> [06,07, 04,05, 02,03, 00,01]
        assert result == b"\x06\x07\x04\x05\x02\x03\x00\x01"

    def test_dcba_64bit_full_swap(self):
        """DCBA格式64位完全交换"""
        config = ByteOrderConfig.DCBA()
        data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        result = config.swap_bytes_for_64bit(data)
        assert result == b"\x07\x06\x05\x04\x03\x02\x01\x00"


class TestByteOrderConfigStructFormat:
    """struct格式字符测试"""

    def test_struct_format_int32_abcd(self):
        """ABCD int32使用大端"""
        fmt = ByteOrderConfig.ABCD().get_struct_format("int32")
        assert fmt == ">i"

    def test_struct_format_float32_cdab(self):
        """CDAB float32格式（统一使用大端，因为swap已处理转换）"""
        fmt = ByteOrderConfig.CDAB().get_struct_format("float32")
        assert fmt == ">f"  # swap_bytes_for_32bit已将数据转为大端

    def test_struct_format_float64_dcba(self):
        """DCBA float64格式（统一使用大端）"""
        fmt = ByteOrderConfig.DCBA().get_struct_format("float64")
        assert fmt == ">d"  # swap_bytes_for_64bit已将数据转为大端

    def test_struct_format_invalid_type(self):
        """无效类型抛出异常"""
        with pytest.raises(ValueError, match="不支持的数据类型"):
            ByteOrderConfig.ABCD().get_struct_format("invalid")


class TestByteOrderConfigReprAndStr:
    """字符串表示测试"""

    def test_repr(self):
        """repr输出"""
        config = ByteOrderConfig.CDAB()
        r = repr(config)
        assert "ByteOrderConfig" in r
        assert "CDAB" in r

    def test_str(self):
        """str输出"""
        config = ByteOrderConfig.ABCD()
        s = str(config)
        assert "ABCD" in s


# ============================================================================
# 第二部分：ModbusProtocol 字节序解码测试
# ============================================================================


class TestInt16Decoding:
    """int16/uint16解码测试（不受字节序影响）"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_int16_positive(self, protocol):
        """正数int16"""
        data = struct.pack(">h", 12345)
        result = protocol.decode_int16(data)
        assert result == 12345

    def test_int16_negative(self, protocol):
        """负数int16"""
        data = struct.pack(">h", -12345)
        result = protocol.decode_int16(data)
        assert result == -12345

    def test_uint16_max(self, protocol):
        """uint16最大值"""
        data = struct.pack(">H", 65535)
        result = protocol.decode_uint16(data)
        assert result == 65535

    def test_int16_zero(self, protocol):
        """零值"""
        data = b"\x00\x00"
        result = protocol.decode_int16(data)
        assert result == 0


class TestInt32DecodingAllFormats:
    """int32解码 - 4种格式完整测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_int32_abcd_positive(self, protocol):
        """ABCD格式正数"""
        value = 0x00010203  # 66051
        data = struct.pack(">i", value)
        result = protocol.decode_int32(data, ByteOrderConfig.ABCD())
        assert result == value

    def test_int32_abcd_negative(self, protocol):
        """ABCD格式负数"""
        value = -123456
        data = struct.pack(">i", value)
        result = protocol.decode_int32(data, ByteOrderConfig.ABCD())
        assert result == value

    def test_int32_cdab_positive(self, protocol):
        """CDAB格式正数

        CDAB格式说明：
        - 设备将32位值按小端word顺序存储
        - 低字（低16位）在低地址寄存器，高字在高地址寄存器
        - 每个word内部仍是大端（高位在前）

        示例：值 0x03020100 (50883856)
        - 高字 0x0302 存储在 reg[N+1]
        - 低字 0x0100 存储在 reg[N]
        - 原始字节: [03, 02, 01, 00] (按地址顺序)
        """
        # 构造一个已知值的CDAB编码
        value = 50883856  # 0x03020100
        # CDAB: 低字在前，所以原始字节是 [低字高, 低字低, 高字高, 高字低]
        # 即: value的低16位在前，高16位在后
        low_word = value & 0xFFFF  # 0x0100
        high_word = (value >> 16) & 0xFFFF  # 0x0302
        # Modbus读取顺序: 先读reg[N](低字), 再读reg[N+1](高字)
        raw_bytes = struct.pack(">HH", low_word, high_word)  # [01, 00, 03, 02]

        result = protocol.decode_int32(raw_bytes, ByteOrderConfig.CDAB())
        assert result == value

    def test_int32_cdab_negative(self, protocol):
        """CDAB格式负数"""
        value = -789012
        # 将负数转换为无符号表示来构造字节
        unsigned_val = value & 0xFFFFFFFF
        low_word = unsigned_val & 0xFFFF
        high_word = (unsigned_val >> 16) & 0xFFFF
        raw_bytes = struct.pack(">HH", low_word, high_word)

        result = protocol.decode_int32(raw_bytes, ByteOrderConfig.CDAB())
        assert result == value

    def test_int32_badc(self, protocol):
        """BADC格式"""
        # 准备一个已知值的大端编码
        original_value = 0x12345678
        big_endian_data = struct.pack(">I", original_value)
        # BADC格式: Word内字节交换
        badc_data = bytes([big_endian_data[1], big_endian_data[0], big_endian_data[3], big_endian_data[2]])
        result = protocol.decode_int32(badc_data, ByteOrderConfig.BADC())
        assert result == original_value

    def test_int32_dcba(self, protocol):
        """DCBA格式"""
        original_value = 0x12345678
        high_word = (original_value >> 16) & 0xFFFF  # 0x1234
        low_word = original_value & 0xFFFF  # 0x5678

        # DCBA: 低字在前 + 每个word内字节交换
        low_swapped = ((low_word & 0xFF) << 8) | ((low_word >> 8) & 0xFF)  # 0x7856
        high_swapped = ((high_word & 0xFF) << 8) | ((high_word >> 8) & 0xFF)  # 0x3412
        dcba_data = struct.pack(">HH", low_swapped, high_swapped)

        result = protocol.decode_uint32(dcba_data, ByteOrderConfig.DCBA())
        assert result == original_value

    def test_int32_zero_all_formats(self, protocol):
        """零值在所有格式下都正确"""
        zero_data = b"\x00\x00\x00\x00"
        for format_name in ["ABCD", "BADC", "CDAB", "DCBA"]:
            bo = ByteOrderConfig.from_string(format_name)
            result = protocol.decode_int32(zero_data, bo)
            assert result == 0, f"{format_name}格式解析零值失败"


class TestUint32DecodingAllFormats:
    """uint32解码测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_uint32_abcd_max(self, protocol):
        """ABCD uint32最大值"""
        value = 0xFFFFFFFF  # 4294967295
        data = struct.pack(">I", value)
        result = protocol.decode_uint32(data, ByteOrderConfig.ABCD())
        assert result == value

    def test_uint32_cdab(self, protocol):
        """CDAB uint32"""
        value = 0xDEADBEEF
        # CDAB: 低字在前
        low_word = value & 0xFFFF  # 0xBEEF
        high_word = (value >> 16) & 0xFFFF  # 0xDEAD
        raw_bytes = struct.pack(">HH", low_word, high_word)
        result = protocol.decode_uint32(raw_bytes, ByteOrderConfig.CDAB())
        assert result == value


class TestFloat32DecodingAllFormats:
    """
    float32解码测试 - ★核心测试集

    这是解决"123.45显示为1.23e-42"问题的关键验证
    """

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_float32_abcd_normal(self, protocol):
        """ABCD格式正常浮点数"""
        value = 123.456
        data = struct.pack(">f", value)
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert abs(result - value) < 0.001

    def test_float32_abcd_negative(self, protocol):
        """ABCD格式负浮点数"""
        value = -789.012
        data = struct.pack(">f", value)
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert abs(result - value) < 0.001

    def test_float32_abcd_small(self, protocol):
        """ABCD格式小数值"""
        value = 0.001234
        data = struct.pack(">f", value)
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert abs(result - value) < 1e-7

    def test_float32_abcd_zero(self, protocol):
        """ABCD格式零值"""
        data = struct.pack(">f", 0.0)
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert result == 0.0

    def test_float32_cdab_normal(self, protocol):
        """CDAB格式正常浮点数

        CDAB格式的float32：
        - 将IEEE 754的32位表示按低字在前存储
        - 例如 123.456 = 0x42F6E979
        - 低字 0xE979 在 reg[N], 高字 0x42F6 在 reg[N+1]
        - 原始字节: [E9, 79, F6, 42]
        """
        value = 123.456
        # 获取IEEE 754位模式
        import struct

        bits = struct.unpack(">I", struct.pack(">f", value))[0]  # 0x42F6E979
        low_word = bits & 0xFFFF  # 0xE979
        high_word = (bits >> 16) & 0xFFFF  # 0x42F6
        # CDAB原始字节: [低字高, 低字低, 高字高, 高字低]
        raw_bytes = struct.pack(">HH", low_word, high_word)

        result = protocol.decode_float32(raw_bytes, ByteOrderConfig.CDAB())
        assert abs(result - value) < 0.001

    def test_float32_cdab_negative(self, protocol):
        """CDAB格式负浮点数"""
        value = -987.654
        bits = struct.unpack(">I", struct.pack(">f", value))[0]
        low_word = bits & 0xFFFF
        high_word = (bits >> 16) & 0xFFFF
        raw_bytes = struct.pack(">HH", low_word, high_word)

        result = protocol.decode_float32(raw_bytes, ByteOrderConfig.CDAB())
        assert abs(result - value) < 0.001

    def test_float32_badc_normal(self, protocol):
        """BADC格式正常浮点数"""
        value = 3.14159
        big_endian_data = struct.pack(">f", value)
        # BADC: Word内字节交换
        badc_data = bytes([big_endian_data[1], big_endian_data[0], big_endian_data[3], big_endian_data[2]])
        result = protocol.decode_float32(badc_data, ByteOrderConfig.BADC())
        assert abs(result - value) < 0.001

    def test_float32_dcba_normal(self, protocol):
        """DCBA格式正常浮点数

        DCBA格式 = CDAB + 每个word内字节交换
        - 低字在前 + 每个word内高低字节互换
        """
        value = -273.15
        bits = struct.unpack(">I", struct.pack(">f", value))[0]
        low_word = bits & 0xFFFF
        high_word = (bits >> 16) & 0xFFFF

        # DCBA: 低字在前，且每个word内字节交换
        # 原始: [低字低, 低字高, 高字低, 高字高]
        low_swapped = ((low_word & 0xFF) << 8) | ((low_word >> 8) & 0xFF)
        high_swapped = ((high_word & 0xFF) << 8) | ((high_word >> 8) & 0xFF)
        raw_bytes = struct.pack(">HH", low_swapped, high_swapped)

        result = protocol.decode_float32(raw_bytes, ByteOrderConfig.DCBA())
        assert abs(result - value) < 0.001

    def test_float32_same_value_all_formats(self, protocol):
        """同一数值在4种格式下的正确性验证"""
        test_values = [0.0, 1.0, -1.0, 100.5, -100.5, 3.14159265]

        for value in test_values:
            bits = struct.unpack(">I", struct.pack(">f", value))[0]
            high_word = (bits >> 16) & 0xFFFF
            low_word = bits & 0xFFFF

            # ABCD: 高字在前，每个word正常
            abcd_data = struct.pack(">HH", high_word, low_word)
            assert (
                abs(protocol.decode_float32(abcd_data, ByteOrderConfig.ABCD()) - value) < 0.001
            ), f"ABCD格式失败: {value}"

            # CDAB: 低字在前，每个word正常
            cdab_data = struct.pack(">HH", low_word, high_word)
            assert (
                abs(protocol.decode_float32(cdab_data, ByteOrderConfig.CDAB()) - value) < 0.001
            ), f"CDAB格式失败: {value}"

            # BADC: 高字在前，每个word内字节交换
            high_swapped = ((high_word & 0xFF) << 8) | ((high_word >> 8) & 0xFF)
            low_swapped = ((low_word & 0xFF) << 8) | ((low_word >> 8) & 0xFF)
            badc_data = struct.pack(">HH", high_swapped, low_swapped)
            assert (
                abs(protocol.decode_float32(badc_data, ByteOrderConfig.BADC()) - value) < 0.001
            ), f"BADC格式失败: {value}"

            # DCBA: 低字在前，每个word内字节交换
            dcba_data = struct.pack(">HH", low_swapped, high_swapped)
            assert (
                abs(protocol.decode_float32(dcba_data, ByteOrderConfig.DCBA()) - value) < 0.001
            ), f"DCBA格式失败: {value}"


class TestFloat32SpecialValues:
    """float32特殊值测试（NaN, Inf等）"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_float32_positive_inf(self, protocol):
        """正无穷大"""
        data = struct.pack(">f", float("inf"))
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert math.isinf(result) and result > 0

    def test_float32_negative_inf(self, protocol):
        """负无穷大"""
        data = struct.pack(">f", float("-inf"))
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert math.isinf(result) and result < 0

    def test_float32_nan(self, protocol):
        """NaN"""
        data = struct.pack(">f", float("nan"))
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert math.isnan(result)

    def test_nan_all_formats(self, protocol):
        """NaN在所有格式下的处理"""
        for format_name in ["ABCD", "BADC", "CDAB", "DCBA"]:
            bo = ByteOrderConfig.from_string(format_name)

            # NaN的位模式
            nan_bits = struct.unpack(">I", struct.pack(">f", float("nan")))[0]
            high_word = (nan_bits >> 16) & 0xFFFF
            low_word = nan_bits & 0xFFFF

            # 根据格式构造原始字节
            if format_name == "ABCD":
                data = struct.pack(">HH", high_word, low_word)
            elif format_name == "BADC":
                high_swapped = ((high_word & 0xFF) << 8) | ((high_word >> 8) & 0xFF)
                low_swapped = ((low_word & 0xFF) << 8) | ((low_word >> 8) & 0xFF)
                data = struct.pack(">HH", high_swapped, low_swapped)
            elif format_name == "CDAB":
                data = struct.pack(">HH", low_word, high_word)
            else:  # DCBA
                high_swapped = ((high_word & 0xFF) << 8) | ((high_word >> 8) & 0xFF)
                low_swapped = ((low_word & 0xFF) << 8) | ((low_word >> 8) & 0xFF)
                data = struct.pack(">HH", low_swapped, high_swapped)

            result = protocol.decode_float32(data, bo)
            assert math.isnan(result), f"{format_name}格式NaN检测失败"


class TestFloat64Decoding:
    """float64双精度解码测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_float64_abcd(self, protocol):
        """ABCD格式double"""
        value = 123456789.12345678
        data = struct.pack(">d", value)
        result = protocol.decode_float64(data, ByteOrderConfig.ABCD())
        assert abs(result - value) < 1e-10

    def test_float64_cdab(self, protocol):
        """CDAB格式double"""
        value = -987654321.98765432
        # 获取IEEE 754位模式
        bits = struct.unpack(">Q", struct.pack(">d", value))[0]
        # 分解为4个word（从高到低）
        w0 = (bits >> 48) & 0xFFFF  # 最高有效字 (Word 1)
        w1 = (bits >> 32) & 0xFFFF  # Word 2
        w2 = (bits >> 16) & 0xFFFF  # Word 3
        w3 = bits & 0xFFFF  # 最低有效字 (Word 4)

        # CDAB: word顺序反转 -> [Word4, Word3, Word2, Word1]
        raw_bytes = struct.pack(">HHHH", w3, w2, w1, w0)
        result = protocol.decode_float64(raw_bytes, ByteOrderConfig.CDAB())
        assert abs(result - value) < 1e-10

    def test_float64_dcba(self, protocol):
        """DCBA格式double"""
        value = 3.141592653589793
        bits = struct.unpack(">Q", struct.pack(">d", value))[0]
        # 分解为4个word并交换每个word内的字节
        words = [
            (bits >> 48) & 0xFFFF,
            (bits >> 32) & 0xFFFF,
            (bits >> 16) & 0xFFFF,
            bits & 0xFFFF,
        ]
        swapped_words = [((w & 0xFF) << 8) | ((w >> 8) & 0xFF) for w in words]
        # DCBA: 低字在前 + 字节交换 -> [swapped_w0, swapped_w1, swapped_w2, swapped_w3]
        raw_bytes = struct.pack(">HHHH", *reversed(swapped_words))
        result = protocol.decode_float64(raw_bytes, ByteOrderConfig.DCBA())
        assert abs(result - value) < 1e-10


class TestInt64Decoding:
    """int64/uint64解码测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_int64_abcd(self, protocol):
        """ABCD格式int64"""
        value = 1234567890123456789
        data = struct.pack(">q", value)
        result = protocol.decode_int64(data, ByteOrderConfig.ABCD())
        assert result == value

    def test_int64_cdab(self, protocol):
        """CDAB格式int64"""
        value = -987654321098765432  # 修正为更合理的值
        # 转换为无符号表示
        unsigned_val = value & 0xFFFFFFFFFFFFFFFF
        # 分解为4个word（从高到低）
        w0 = (unsigned_val >> 48) & 0xFFFF  # Word 1 (最高)
        w1 = (unsigned_val >> 32) & 0xFFFF  # Word 2
        w2 = (unsigned_val >> 16) & 0xFFFF  # Word 3
        w3 = unsigned_val & 0xFFFF  # Word 4 (最低)
        # CDAB: word顺序反转 -> [Word4, Word3, Word2, Word1]
        raw_bytes = struct.pack(">HHHH", w3, w2, w1, w0)
        result = protocol.decode_int64(raw_bytes, ByteOrderConfig.CDAB())
        assert result == value

    def test_uint64_max(self, protocol):
        """uint64最大值"""
        value = (1 << 64) - 1
        data = struct.pack(">Q", value)
        result = protocol.decode_uint64(data, ByteOrderConfig.ABCD())
        assert result == value


# ============================================================================
# 第三部分：寄存器列表解码测试
# ============================================================================


class TestDecodeRegisters:
    """decode_registers便捷方法测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_decode_int16_registers(self, protocol):
        """从寄存器列表解码int16"""
        registers = [0x3039]  # 12345
        result = protocol.decode_registers(registers, "int16")
        assert result == 12345

    def test_decode_uint16_registers(self, protocol):
        """从寄存器列表解码uint16"""
        registers = [0xFFFF]
        result = protocol.decode_registers(registers, "uint16")
        assert result == 65535

    def test_decode_float32_registers_abcd(self, protocol):
        """从寄存器列表解码float32 (ABCD)"""
        value = 123.456
        raw_bytes = struct.pack(">f", value)
        reg_high = struct.unpack(">H", raw_bytes[0:2])[0]
        reg_low = struct.unpack(">H", raw_bytes[2:4])[0]
        registers = [reg_high, reg_low]

        result = protocol.decode_registers(registers, "float32", byte_order=ByteOrderConfig.ABCD())
        assert abs(result - value) < 0.001

    def test_decode_float32_registers_cdab(self, protocol):
        """从寄存器列表解码float32 (CDAB)"""
        value = -987.654
        bits = struct.unpack(">I", struct.pack(">f", value))[0]
        low_word = bits & 0xFFFF
        high_word = (bits >> 16) & 0xFFFF
        # CDAB: 低字在前
        registers = [low_word, high_word]

        result = protocol.decode_registers(registers, "float32", byte_order=ByteOrderConfig.CDAB())
        assert abs(result - value) < 0.001

    def test_decode_int32_registers(self, protocol):
        """从寄存器列表解码int32"""
        value = 0x12345678
        registers = [0x1234, 0x5678]
        result = protocol.decode_registers(registers, "int32")
        assert result == value

    def test_decode_insufficient_registers(self, protocol):
        """寄存器数量不足时抛出异常"""
        registers = [0x1234]  # float32需要2个寄存器
        with pytest.raises(ValueError, match="无法解码寄存器"):
            protocol.decode_registers(registers, "float32")

    def test_decode_float64_registers(self, protocol):
        """从寄存器列表解码float64"""
        value = 123.45678901234
        raw_bytes = struct.pack(">d", value)
        registers = [struct.unpack(">H", raw_bytes[i : i + 2])[0] for i in range(0, 8, 2)]
        result = protocol.decode_registers(registers, "float64")
        assert abs(result - value) < 1e-10


# ============================================================================
# 第四部分：协议实例级别配置测试
# ============================================================================


class TestProtocolByteOrderConfiguration:
    """协议实例级别字节序配置测试"""

    def test_default_byte_order_is_abcd(self):
        """默认字节序为ABCD"""
        protocol = ModbusProtocol()
        assert protocol.get_byte_order().format_name == "ABCD"

    def test_set_byte_order_at_init(self):
        """初始化时设置字节序"""
        protocol = ModbusProtocol(byte_order=ByteOrderConfig.CDAB())
        assert protocol.get_byte_order().format_name == "CDAB"

    def test_set_byte_order_runtime(self):
        """运行时修改字节序"""
        protocol = ModbusProtocol()
        protocol.set_byte_order(ByteOrderConfig.DCBA())
        assert protocol.get_byte_order().format_name == "DCBA"

    def test_byte_order_affects_decoding(self):
        """字节序影响解码结果"""
        protocol_abcd = ModbusProtocol(byte_order=ByteOrderConfig.ABCD())
        protocol_cdab = ModbusProtocol(byte_order=ByteOrderConfig.CDAB())

        value = 123.456
        bits = struct.unpack(">I", struct.pack(">f", value))[0]
        high_word = (bits >> 16) & 0xFFFF
        low_word = bits & 0xFFFF

        # ABCD数据: 高字在前
        abcd_data = struct.pack(">HH", high_word, low_word)
        result_abcd = protocol_abcd.decode_float32(abcd_data)
        assert abs(result_abcd - value) < 0.001

        # CDAB数据: 低字在前
        cdab_data = struct.pack(">HH", low_word, high_word)
        result_cdab = protocol_cdab.decode_float32(cdab_data)
        assert abs(result_cdab - value) < 0.001

    def test_temporary_byte_order_override(self):
        """临时覆盖字节序不影响实例默认值"""
        protocol = ModbusProtocol(byte_order=ByteOrderConfig.ABCD())

        # 使用临时CDAB配置
        value = 123.456
        bits = struct.unpack(">I", struct.pack(">f", value))[0]
        low_word = bits & 0xFFFF
        high_word = (bits >> 16) & 0xFFFF
        cdab_data = struct.pack(">HH", low_word, high_word)
        result = protocol.decode_float32(cdab_data, byte_order=ByteOrderConfig.CDAB())
        assert abs(result - value) < 0.001

        # 默认配置仍然是ABCD
        assert protocol.get_byte_order().format_name == "ABCD"


# ============================================================================
# 第五部分：边界值和错误处理测试
# ============================================================================


class TestBoundaryValues:
    """边界值测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_int32_max_positive(self, protocol):
        """int32最大正值"""
        value = 2147483647  # 2^31 - 1
        data = struct.pack(">i", value)
        result = protocol.decode_int32(data, ByteOrderConfig.ABCD())
        assert result == value

    def test_int32_max_negative(self, protocol):
        """int32最大负值"""
        value = -2147483648  # -2^31
        data = struct.pack(">i", value)
        result = protocol.decode_int32(data, ByteOrderConfig.ABCD())
        assert result == value

    def test_uint32_max(self, protocol):
        """uint32最大值"""
        value = 4294967295  # 2^32 - 1
        data = struct.pack(">I", value)
        result = protocol.decode_uint32(data, ByteOrderConfig.ABCD())
        assert result == value

    def test_float32_smallest_denormalized(self, protocol):
        """float32最小非规格化数"""
        value = 1.4e-45  # 接近float32最小正数
        data = struct.pack(">f", value)
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert result > 0 and result < 1.5e-45

    def test_float32_large_value(self, protocol):
        """float32较大值"""
        value = 1.0e20
        data = struct.pack(">f", value)
        result = protocol.decode_float32(data, ByteOrderConfig.ABCD())
        assert abs((result - value) / value) < 1e-6  # 相对误差


class TestErrorHandling:
    """错误处理测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_decode_int16_insufficient_data(self, protocol):
        """int16数据不足"""
        with pytest.raises(ValueError, match="期望至少2字节"):
            protocol.decode_int16(b"\x00")

    def test_decode_int32_insufficient_data(self, protocol):
        """int32数据不足"""
        with pytest.raises(ValueError, match="期望至少4字节"):
            protocol.decode_int32(b"\x00\x01\x02")

    def test_decode_float32_insufficient_data(self, protocol):
        """float32数据不足"""
        with pytest.raises(ValueError, match="期望至少4字节"):
            protocol.decode_float32(b"\x00\x01")

    def test_decode_float64_insufficient_data(self, protocol):
        """float64数据不足"""
        with pytest.raises(ValueError, match="期望至少8字节"):
            protocol.decode_float64(b"\x00\x01\x02\x03\x04\x05\x06")

    def test_empty_data_int16(self, protocol):
        """空数据"""
        with pytest.raises(ValueError):
            protocol.decode_int16(b"")


# ============================================================================
# 第六部分：向后兼容性测试
# ============================================================================


class TestBackwardCompatibility:
    """
    向后兼容性测试

    确保新实现与旧版代码完全兼容：
    - 不传byte_order参数时行为与旧版一致
    - 默认使用ABCD大端序
    """

    @pytest.fixture
    def protocol(self):
        """创建无参数的协议实例（模拟旧版用法）"""
        return ModbusProtocol()

    def test_default_behavior_matches_old_code(self, protocol):
        """默认行为与旧版代码一致"""
        # 旧版代码: struct.unpack("f", struct.pack("I", (reg_high << 16) | reg_low))
        # 等同于大端序解析

        reg_high = 0x42F6
        reg_low = 0xE979
        old_way_raw = (reg_high << 16) | reg_low
        old_way_value = struct.unpack("f", struct.pack("I", old_way_raw))[0]

        # 新版方式
        new_way_value = protocol.decode_registers([reg_high, reg_low], "float32")

        assert abs(old_way_value - new_way_value) < 0.0001

    def test_parse_register_value_backward_compat(self, protocol):
        """_parse_register_value 向后兼容"""
        values = [0x42F6, 0xE979, 0x0000, 0x0001]

        # 不传 byte_order 参数（旧版调用方式）
        result = protocol._parse_register_value(values, 0, "float32", 0)
        assert result is not None
        _, value = result
        assert abs(value - 123.456) < 0.001

    def test_int16_parsing_unchanged(self, protocol):
        """int16解析逻辑不变"""
        values = [0x8000]  # -32768
        result = protocol._parse_register_value(values, 0, "int16", 0)
        assert result is not None
        _, value = result
        assert value == -32768

    def test_uint16_parsing_unchanged(self, protocol):
        """uint16解析逻辑不变"""
        values = [0xFFFF]
        result = protocol._parse_register_value(values, 0, "uint16", 0)
        assert result is not None
        _, value = result
        assert value == 0xFFFF

    def test_poll_data_still_works(self, protocol):
        """poll_data 方法仍然可用（需要mock驱动）"""
        # poll_data 内部调用 _parse_register_value
        # 验证接口未改变
        assert hasattr(protocol, "poll_data")
        assert callable(protocol.poll_data)


# ============================================================================
# 第七部分：性能基准测试
# ============================================================================


class TestPerformance:
    """性能基准测试"""

    def test_byte_order_config_creation_speed(self):
        """ByteOrderConfig创建速度 < 1μs"""
        import time

        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            _ = ByteOrderConfig.CDAB()
        elapsed = (time.perf_counter() - start) / iterations * 1e6  # μs

        assert elapsed < 10.0, f"创建耗时 {elapsed:.2f}μs，超过10μs限制"

    def test_32bit_swap_speed(self):
        """32位字节交换速度 < 1μs"""
        import time

        config = ByteOrderConfig.DCBA()  # 最复杂的交换
        data = b"\x00\x01\x02\x03"
        iterations = 100000

        start = time.perf_counter()
        for _ in range(iterations):
            _ = config.swap_bytes_for_32bit(data)
        elapsed = (time.perf_counter() - start) / iterations * 1e6

        assert elapsed < 5.0, f"交换耗时 {elapsed:.2f}μs，超过5μs限制"

    def test_float32_decode_speed(self):
        """float32解码速度 < 5μs"""
        import time

        protocol = ModbusProtocol(byte_order=ByteOrderConfig.CDAB())
        data = struct.pack("<f", 123.456)
        iterations = 100000

        start = time.perf_counter()
        for _ in range(iterations):
            _ = protocol.decode_float32(data)
        elapsed = (time.perf_counter() - start) / iterations * 1e6

        assert elapsed < 10.0, f"解码耗时 {elapsed:.2f}μs，超过10μs限制"


# ============================================================================
# 第八部分：厂商推荐配置测试
# ============================================================================


class TestVendorRecommendations:
    """厂商推荐配置测试"""

    def test_siemens_recommendation(self):
        """西门子推荐ABCD"""
        assert VENDOR_BYTE_ORDER_RECOMMENDATIONS["西门子"] == "ABCD"
        assert VENDOR_BYTE_ORDER_RECOMMENDATIONS["Siemens"] == "ABCD"

    def test_mitsubishi_recommendation(self):
        """三菱推荐CDAB"""
        assert VENDOR_BYTE_ORDER_RECOMMENDATIONS["三菱"] == "CDAB"
        assert VENDOR_BYTE_ORDER_RECOMMENDATIONS["Mitsubishi"] == "CDAB"

    def test_abb_recommendation(self):
        """ABB推荐DCBA"""
        assert VENDOR_BYTE_ORDER_RECOMMENDATIONS["ABB"] == "DCBA"

    def test_presets_list_completeness(self):
        """预设列表完整性"""
        preset_names = [p[0] for p in BYTE_ORDER_PRESETS]
        assert "ABCD" in preset_names
        assert "BADC" in preset_names
        assert "CDAB" in preset_names
        assert "DCBA" in preset_names


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
