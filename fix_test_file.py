#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 test_mcgs_reader.py：
1. 删除已废弃的 _parse_float 调用
2. 使用 ModbusValueParser 替代
3. 修复 __import__ 错误用法
"""

import re

filepath = r"d:\下载\app\equipment management\tests\test_mcgs_reader.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 修复1: 替换 __import__ 错误用法为正确的 RegisterDataType 引用
# 在所有函数外部添加导入
if "from core.enums.data_type_enum import RegisterDataType" not in content:
    # 在已有的 import 之后添加
    insert_pos = content.find("from pathlib import Path")
    if insert_pos != -1:
        line_end = content.find("\n", insert_pos)
        content = (
            content[: line_end + 1]
            + "from core.enums.data_type_enum import RegisterDataType\n"
            + content[line_end + 1 :]
        )

# 修复2: 替换 test_byte_order_parsing 函数
# 删除 broken 的 encode_float 辅助函数，使用硬编码测试向量
old_func_start = "# ==================== 测试3: 字节序解析引擎 ====================\n\n"
old_func_start_alt = "# ==================== 测试3: 字节序解析引擎 ====================\n\n"

# 找到函数开始和结束位置
func_start = content.find("# ==================== 测试3")
if func_start == -1:
    print("ERROR: 找不到测试3函数")
    exit(1)

# 找到函数结束位置（下一个 ==== 或文件结束）
next_section = content.find("# ==================== 测试4", func_start)
if next_section == -1:
    print("ERROR: 找不到测试4的开始位置")
    exit(1)

# 新的函数内容
new_func = '''# ==================== 测试3: 字节序解析引擎 ====================

def test_byte_order_parsing(reader: MCGSModbusReader):
    """测试字节序解析引擎（ABCD/BADC/CDAB/DCBA）

    使用 ModbusValueParser 直接测试，替代已删除的私有方法 _parse_float
    """
    print_header("测试3: 字节序解析引擎 (4种模式)")

    if reader is None:
        print_test("跳过", False, "reader为None")
        return

    try:
        from core.communication.modbus_value_parser import ModbusValueParser
        from core.protocols.byte_order_config import ByteOrderConfig
        import math

        test_value = 123.456

        # 已知测试向量：123.456 的4种字节序寄存器表示
        # 由 struct.pack(">f", 123.456) = 0x42F6E979 推导
        test_vectors = [
            ("ABCD", "大端",        [0x42F6, 0xE979]),
            ("CDAB", "小端/MCGS",  [0xE979, 0x42F6]),
            ("BADC", "半字交换",    [0xF642, 0x79E9]),
            ("DCBA", "完全反转",    [0x79E9, 0xF642]),
        ]

        all_passed = True
        for order_str, order_name, regs in test_vectors:
            parser = ModbusValueParser(byte_order=ByteOrderConfig.from_string(order_str))
            result = parser.parse(regs, 0, RegisterDataType.HOLDING_FLOAT32)
            if result is not None and not (math.isnan(result) or math.isinf(result)):
                error = abs(result - test_value)
                passed = error < 0.01
            else:
                result = None
                error = 999
                passed = False
            if not passed:
                all_passed = False
            print_test(
                f"{order_str} ({order_name})",
                passed,
                f"输入={[hex(r) for r in regs]}, "
                f"输出={result:.3f}, 误差={error:.6f}" if result is not None else "返回None"
            )

        # 测试异常输入：空寄存器
        parser_abcd = ModbusValueParser(byte_order=ByteOrderConfig.ABCD())
        result_empty = parser_abcd.parse([], 0, RegisterDataType.HOLDING_FLOAT32)
        print_test(
            "空寄存器处理",
            result_empty is None,
            "返回None (防止崩溃)"
        )

        # 测试异常输入：寄存器不足
        result_short = parser_abcd.parse([0x1234], 0, RegisterDataType.HOLDING_FLOAT32)
        print_test(
            "寄存器不足处理",
            result_short is None,
            "返回None (需要2个，收到1个)"
        )

        # MCGS实际场景模拟：温度26.1℃
        # 26.1 的 CDAB 编码为 [0x41D0, 0xCCCD]
        temp_regs = [0x41D0, 0xCCCD]
        parser_cdab = ModbusValueParser(byte_order=ByteOrderConfig.CDAB())
        result_temp = parser_cdab.parse(temp_regs, 0, RegisterDataType.HOLDING_FLOAT32)
        print_test(
            "MCGS温度场景",
            abs(result_temp - 26.1) < 0.1 if result_temp is not None else False,
            f"期望≈26.1℃, 实际={result_temp:.1f}℃" if result_temp is not None else "解析失败"
        )

        # MCGS实际场景模拟：压力101.3kPa
        # 101.3 的 CDAB 编码为 [0x42CA, 0x6666]
        pa_regs = [0x42CA, 0x6666]
        result_pa = parser_cdab.parse(pa_regs, 0, RegisterDataType.HOLDING_FLOAT32)
        print_test(
            "MCGS压力场景",
            abs(result_pa - 101.3) < 0.1 if result_pa is not None else False,
            f"期望≈101.3kPa, 实际={result_pa:.1f}kPa" if result_pa is not None else "解析失败"
        )

        print_test("全部字节序测试通过", all_passed, "4种字节序均正确解析")

    except Exception as e:
        print_test("字节序解析测试失败", False, str(e))
        import traceback
        traceback.print_exc()

'''

content = content[:func_start] + new_func + content[next_section:]

# 修复3: 替换性能测试中的 reader._parse_float 调用
content = content.replace(
    "            result = parser.parse(regs, 0, __import__('core.enums.data_type_enum', fromlist=['RegisterDataType']).RegisterDataType.HOLDING_FLOAT32)",
    "            result = parser.parse(regs, 0, RegisterDataType.HOLDING_FLOAT32)",
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: 修复完成")
print(f"  文件: {filepath}")
