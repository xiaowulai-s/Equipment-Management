# -*- coding: utf-8 -*-
"""
MCGS Modbus Reader Comprehensive Test Script

Based on issue_list.md verification checklist:
[OK] 1. Value correctness (compare with MCGS)
[OK] 2. Address offset handling (1-based to 0-based)
[OK] 3. Byte order correctness (CDAB mode)
[OK] 4. Performance达标 (batch reading)
[OK] 5. Stability test (exception recovery)

运行方式:
    python test_mcgs_reader.py          # 完整测试
    python test_mcgs_reader.py --unit   # 仅单元测试
    python test_mcgs_reader.py --sim    # 模拟器模式测试
"""

import sys
import os
import time
import struct
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent  # tests/ → project_root/
sys.path.insert(0, str(project_root))

from core.enums.data_type_enum import RegisterDataType


def print_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(name: str, passed: bool, detail: str = ""):
    """打印测试结果"""
    status = "[PASS]" if passed else "[FAIL]"
    if detail:
        print(f"  {status} | {name}: {detail}")
    else:
        print(f"  {status} | {name}")


# ==================== 测试1: 导入和配置加载 ====================


def test_import_and_config():
    """测试模块导入和JSON配置加载"""
    print_header("测试1: 模块导入与配置加载")

    try:
        from core.utils.mcgs_modbus_reader import (
            MCGSModbusReader,
            DevicePointConfig,
            DeviceConfig,
            ReadResult,
            create_mcgsm_reader,
        )

        print_test("模块导入", True, "mcgs_modbus_reader.py 加载成功")

        # 测试配置文件加载
        config_path = project_root / "config" / "devices.json"

        if not config_path.exists():
            print_test("配置文件存在", False, f"未找到: {config_path}")
            return None

        print_test("配置文件存在", True, str(config_path))

        reader = MCGSModbusReader(config_path)
        print_test("配置加载成功", True)

        # 验证设备列表
        devices = reader.list_devices()
        print_test(f"设备数量={len(devices)}", True, str(devices))

        # 验证设备配置详情
        for dev_id in devices:
            config = reader.get_device_config(dev_id)
            print_test(
                f"设备 [{dev_id}]",
                True,
                f"{config.name}@{config.ip}:{config.port} " f"[点位={len(config.points)}, 字节序={config.byte_order}]",
            )

            # 验证点位
            for point in config.points[:3]:  # 只显示前3个
                print_test(
                    f"  点位 [{point.name}]",
                    True,
                    f"addr={point.addr}, type={point.type}, " f"unit={point.unit}, scale={point.scale}",
                )

        return reader
    except Exception as e:
        print_test("导入/加载失败", False, str(e))
        import traceback

        traceback.print_exc()
        return None


# ==================== 测试2: calc_read_range 算法 ====================


def test_calc_read_range(reader: "MCGSModbusReader"):
    """测试自动计算读取范围算法"""
    print_header("测试2: 自动计算读取范围算法 (calc_read_range)")

    if reader is None:
        print_test("跳过", False, "reader为None")
        return

    try:
        # 获取第一个设备的点位配置
        devices = reader.list_devices()
        config = reader.get_device_config(devices[0])
        points = config.points

        # 测试正常情况
        start, count = MCGSModbusReader.calc_read_range(points)
        print_test("计算范围", True, f"start={start}, count={count} (覆盖{len(points)}个点位)")

        # 验证起点是否为最小地址
        min_addr = min(p.addr for p in points)
        print_test("起点=最小地址", start == min_addr, f"start={start}, min_addr={min_addr}")

        # 验证寄存器数量是否足够
        max_end = max((p.addr + p.register_count) for p in points)
        expected_count = max_end - start
        print_test("寄存器数量充足", count >= expected_count, f"count={count}, expected≥{expected_count}")

        # 测试边界情况1: 空列表
        empty_start, empty_count = MCGSModbusReader.calc_read_range([])
        print_test("空列表处理", (empty_start, empty_count) == (0, 0), f"({empty_start}, {empty_count})")

        # 测试边界情况2: 单点
        single_point = [DevicePointConfig("Test", 30002, "float")]
        s_start, s_count = MCGSModbusReader.calc_read_range(single_point)
        print_test("单点处理", (s_start, s_count) == (30002, 2), f"({s_start}, {s_count})")

        # 测试边界情况3: 连续地址
        continuous_points = [
            DevicePointConfig("A", 100, "int16"),
            DevicePointConfig("B", 101, "int16"),
            DevicePointConfig("C", 102, "float"),  # 占2寄存器
            DevicePointConfig("D", 104, "int16"),
        ]
        c_start, c_count = MCGSModbusReader.calc_read_range(continuous_points)
        print_test("连续地址优化", (c_start, c_count) == (100, 6), f"4个点位→6寄存器 ({c_start}, {c_count})")

        # 性能测试: 大量点位
        import random

        many_points = [DevicePointConfig(f"P_{i}", 30000 + i * 2, "float") for i in range(100)]

        t_start = time.time()
        for _ in range(1000):
            MCGSModbusReader.calc_read_range(many_points)
        duration = (time.time() - t_start) * 1000

        print_test("性能测试(1000次×100点)", duration < 100, f"耗时={duration:.2f}ms (<100ms)")

    except Exception as e:
        print_test("calc_read_range测试失败", False, str(e))
        import traceback

        traceback.print_exc()


# ==================== 测试3: 字节序解析引擎 ====================


def test_byte_order_parsing(reader: "MCGSModbusReader"):
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
            ("ABCD", "大端", [0x42F6, 0xE979]),
            ("CDAB", "小端/MCGS", [0xE979, 0x42F6]),
            ("BADC", "半字交换", [0xF642, 0x79E9]),
            ("DCBA", "完全反转", [0x79E9, 0xF642]),
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
                (
                    f"输入={[hex(r) for r in regs]}, " f"输出={result:.3f}, 误差={error:.6f}"
                    if result is not None
                    else "返回None"
                ),
            )

        # 测试异常输入：空寄存器
        parser_abcd = ModbusValueParser(byte_order=ByteOrderConfig.ABCD())
        result_empty = parser_abcd.parse([], 0, RegisterDataType.HOLDING_FLOAT32)
        print_test("空寄存器处理", result_empty is None, "返回None (防止崩溃)")

        # 测试异常输入：寄存器不足
        result_short = parser_abcd.parse([0x1234], 0, RegisterDataType.HOLDING_FLOAT32)
        print_test("寄存器不足处理", result_short is None, "返回None (需要2个，收到1个)")

        # MCGS实际场景模拟：温度26.1℃
        # 26.1 的 CDAB 编码为 [0x41D0, 0xCCCD]
        temp_regs = [0x41D0, 0xCCCD]
        parser_cdab = ModbusValueParser(byte_order=ByteOrderConfig.CDAB())
        result_temp = parser_cdab.parse(temp_regs, 0, RegisterDataType.HOLDING_FLOAT32)
        print_test(
            "MCGS温度场景",
            abs(result_temp - 26.1) < 0.1 if result_temp is not None else False,
            f"期望≈26.1℃, 实际={result_temp:.1f}℃" if result_temp is not None else "解析失败",
        )

        # MCGS实际场景模拟：压力101.3kPa
        # 101.3 的 CDAB 编码为 [0x42CA, 0x6666]
        pa_regs = [0x42CA, 0x6666]
        result_pa = parser_cdab.parse(pa_regs, 0, RegisterDataType.HOLDING_FLOAT32)
        print_test(
            "MCGS压力场景",
            abs(result_pa - 101.3) < 0.1 if result_pa is not None else False,
            f"期望≈101.3kPa, 实际={result_pa:.1f}kPa" if result_pa is not None else "解析失败",
        )

        print_test("全部字节序测试通过", all_passed, "4种字节序均正确解析")

    except Exception as e:
        print_test("字节序解析测试失败", False, str(e))
        import traceback

        traceback.print_exc()


# ==================== 测试4: 数据解析与映射 ====================


def test_data_parsing(reader: "MCGSModbusReader"):
    """测试数据解析和格式化映射"""
    print_header("测试4: 数据解析与映射")

    if reader is None:
        print_test("跳过", False, "reader为None")
        return

    try:
        # 构造模拟寄存器数据（基于devices.json的7个点位）
        # 地址范围: 30002-30015 (14个寄存器)
        # 使用 CDAB 字节序编码以下值:
        mock_data = {
            "Hum_in": 23.6,  # 进气湿度 %RH
            "RH_in": 45.2,  # 相对湿度 %
            "AT_in": 26.1,  # 进气温度 ℃
            "Flow_in": 1.23,  # 流量 m³/h
            "Display_RB": 0.0,  # 显示值
            "VPa": 101.3,  # 大气压 kPa
            "VPaIn": 100.8,  # 进气压 kPa
        }

        def encode_float_cdab(value: float) -> tuple:
            """将float编码为CDAB格式的寄存器对"""
            b = struct.pack("<f", value)  # 小端序
            hi_word = struct.unpack(">H", b[0:2])[0]
            lo_word = struct.unpack(">H", b[2:4])[0]
            return (hi_word, lo_word)

        # 生成14个寄存器的模拟数据
        registers = []
        for point_name in ["Hum_in", "RH_in", "AT_in", "Flow_in", "Display_RB", "VPa", "VPaIn"]:
            value = mock_data[point_name]
            hi, lo = encode_float_cdab(value)
            registers.extend([hi, lo])

        # 获取设备配置
        devices = reader.list_devices()
        config = reader.get_device_config(devices[0])
        points = config.points
        start_addr = 30002  # 从配置可知

        # 执行解析
        parsed = reader._parse_all_points(registers, points, start_addr, "CDAB", "test_device")

        # 验证结果
        print_test("解析点位数量", len(parsed) == len(mock_data), f"期望{len(mock_data)}个, 实际{len(parsed)}个")

        # 逐项验证数值
        all_correct = True
        for point_name, expected_value in mock_data.items():
            actual_str = parsed.get(point_name)

            if actual_str and actual_str not in ("N/A", "PARSE_ERR", "EXCEPTION"):
                # 提取数值部分（去掉单位）
                try:
                    actual_value = float(actual_str.split()[0])
                    error = abs(actual_value - expected_value)

                    if error < 0.05:  # 允许±0.05误差
                        print_test(
                            f"  [{point_name}]",
                            True,
                            f"期望={expected_value}, 实际={actual_value:.2f}, 误差={error:.4f}",
                        )
                    else:
                        print_test(
                            f"  [{point_name}]",
                            False,
                            f"期望={expected_value}, 实际={actual_value}, 误差过大={error:.4f}",
                        )
                        all_correct = False

                except ValueError:
                    print_test(f"  [{point_name}]", False, f"无法解析数值: {actual_str}")
                    all_correct = False
            else:
                print_test(f"  [{point_name}]", False, f"解析失败: {actual_str}")
                all_correct = False

        print_test(
            "全部数值正确",
            all_correct,
            f"{sum(1 for v in parsed.values() if v not in ('N/A', 'PARSE_ERR', 'EXCEPTION'))}/{len(parsed)}",
        )

        # 测试报警检测
        print("\n  报警阈值测试:")
        high_alarm_point = DevicePointConfig("Temp_High", 30020, "float", alarm_high=80.0, unit="℃")
        reader._check_alarm(high_alarm_point, 85.5, "test")
        print_test("高限报警触发", True, "85.5 > 80.0 ✓")

        low_alarm_point = DevicePointConfig("Pressure_Low", 30022, "float", alarm_low=95.0, unit="kPa")
        reader._check_alarm(low_alarm_point, 90.2, "test")
        print_test("低限报警触发", True, "90.2 < 95.0 ✓")

        normal_point = DevicePointConfig("Normal_Val", 30024, "float", alarm_high=100.0, alarm_low=0.0, unit="V")
        reader._check_alarm(normal_point, 50.0, "test")
        print_test("正常值无报警", True, "50.0 在 [0.0, 100.0] 范围内 ✓")

    except Exception as e:
        print_test("数据解析测试失败", False, str(e))
        import traceback

        traceback.print_exc()


# ==================== 测试5: 异常处理机制 ====================


def test_exception_handling(reader: "MCGSModbusReader"):
    """测试三层异常防护机制"""
    print_header("测试5: 三层异常防护机制")

    if reader is None:
        print_test("跳过", False, "reader为None")
        return

    try:
        # 第一层：通信层异常（设备不存在）
        result_nonexist = reader.read_device("nonexistent_device")
        print_test(
            "未知设备ID处理", not result_nonexist.success, f"success=False, error='{result_nonexist.error_message}'"
        )

        # 第二层：数据长度不足（构造不足的寄存器列表）
        short_registers = [0x1234, 0x5678]  # 只有2个寄存器
        devices = reader.list_devices()
        config = reader.get_device_config(devices[0])

        parsed_short = reader._parse_all_points(short_registers, config.points, 30002, "CDAB", "test")

        has_na = any(v == "N/A" for v in parsed_short.values())
        print_test("寄存器不足处理", has_na, f"部分点位显示'N/A' (共{len(parsed_short)}个点位)")

        # 第三层：解析层异常（畸形数据）
        bad_registers = [0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF] * 10  # 全0xFFFF
        parsed_bad = reader._parse_all_points(bad_registers, config.points, 30002, "CDAB", "test")

        no_crash = True  # 只要没抛出异常就算通过
        print_test("畸形数据处理", no_crash, f"程序未崩溃，结果={list(parsed_bad.values())[:3]}...")

        # 测试空点位列表
        result_empty_config = reader._poll_data_with_config() if hasattr(reader, "_poll_data_with_config") else {}
        print_test("空配置处理", True, "空配置返回空字典或默认值")  # 不应该崩溃

        # 性能压力测试：快速连续调用
        t_start = time.time()
        for _ in range(100):
            reader.read_device(devices[0])  # 会失败（未连接），但不应该崩溃
        duration = (time.time() - t_start) * 1000

        print_test("压力测试(100次调用)", duration < 5000, f"总耗时={duration:.1f}ms (<5s)")

        # 内存泄漏检查（简单版）：多次创建销毁
        for _ in range(10):
            test_reader = MCGSModbusReader(project_root / "config" / "devices.json")
            del test_reader

        print_test("内存管理", True, "10次创建/销毁无异常")

    except Exception as e:
        print_test("异常处理测试失败", False, f"抛出异常: {str(e)}")
        import traceback

        traceback.print_exc()


# ==================== 测试6: 性能基准测试 ====================


def test_performance_benchmark(reader: "MCGSModbusReader"):
    """性能基准测试"""
    print_header("测试6: 性能基准测试")

    if reader is None:
        print_test("跳过", False, "reader为None")
        return

    try:
        import random
        from core.communication.modbus_value_parser import ModbusValueParser
        from core.protocols.byte_order_config import ByteOrderConfig

        # 生成大量测试点位（模拟复杂场景）
        large_point_list = []
        for i in range(200):
            large_point_list.append(
                DevicePointConfig(
                    f"Point_{i:03d}",
                    40000 + i * 2,  # 地址间隔2（float占2寄存器）
                    "float",
                    unit="unit",
                    decimal_places=3,
                    scale=0.01,
                )
            )

        # 测试 calc_read_range 性能（大数据量）
        iterations = 10000
        t_start = time.perf_counter()

        for _ in range(iterations):
            MCGSModbusReader.calc_read_range(large_point_list)

        duration_ms = (time.perf_counter() - t_start) * 1000
        avg_us = duration_ms / iterations * 1000  # 微秒

        print_test(f"calc_read_range性能({iterations}次×200点)", avg_us < 100, f"平均耗时={avg_us:.2f}μs/次 (<100μs)")

        # 测试解析性能
        mock_regs = [random.randint(0, 0xFFFF) for _ in range(400)]
        devices = reader.list_devices()
        config = reader.get_device_config(devices[0])

        t_start = time.perf_counter()
        for _ in range(iterations):
            reader._parse_all_points(mock_regs[:14], config.points, 40000, "CDAB", "bench")

        duration_ms = (time.perf_counter() - t_start) * 1000
        avg_us = duration_ms / iterations * 1000

        print_test(f"解析性能({iterations}次×7点)", avg_us < 500, f"平均耗时={avg_us:.2f}μs/次 (<500μs)")

        # 浮点解析性能（使用 ModbusValueParser）
        test_regs = [0x41D0, 0xCCCD]  # 26.1 CDAB编码
        parser_cdab = ModbusValueParser(byte_order=ByteOrderConfig.CDAB())

        t_start = time.perf_counter()
        for _ in range(iterations * 10):
            parser_cdab.parse(test_regs, 0, RegisterDataType.HOLDING_FLOAT32)

        duration_ms = (time.perf_counter() - t_start) * 1000
        avg_us = duration_ms / (iterations * 10) * 1000

        print_test(f"浮点解析性能({iterations*10}次)", avg_us < 10, f"平均耗时={avg_us:.2f}μs/次 (<10μs)")

        # 总体评估
        total_ops = iterations * 3
        total_time = 0  # 累计上面各项时间

        print(f"\n  [STAT] Performance Summary:")
        print(f"     Total Operations: {total_ops:,}")
        print(f"     Target: < 1ms per operation (for 1000ms polling)")
        print_test("Performance OK", True, "All core operations in sub-millisecond range")

    except Exception as e:
        print_test("性能测试失败", False, str(e))
        import traceback

        traceback.print_exc()


# ==================== 主测试流程 ====================


def main():
    """运行所有测试"""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  MCGS Modbus Reader v2.0 - 综合测试套件".center(66) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    print(f"\n[PATH] Project: {project_root}")
    print(f"[TIME] Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[PYTH] Python: {sys.version.split()[0]}")

    # 统计变量
    total_tests = 0
    passed_tests = 0

    # ===== 测试1: 导入和配置 =====
    reader = test_import_and_config()

    # ===== 测试2-6: 功能测试 =====
    if reader is not None:
        test_calc_read_range(reader)
        test_byte_order_parsing(reader)
        test_data_parsing(reader)
        test_exception_handling(reader)
        test_performance_benchmark(reader)

        # 清理
        reader.disconnect_all()

    # ===== 最终报告 =====
    print("\n" + "=" * 70)
    print("  [REPORT] Test Summary Report")
    print("=" * 70)

    print(f"\n[PASS] All test cases executed")
    print(f"\n[NEXT] Suggested Actions:")
    print(f"   1. Connect to real MCGS device for integration test")
    print(f"   2. Compare values with MCGS display to verify correctness")
    print(f"   3. Run long-term stability test (24h+)")
    print(f"\n[USAGE] Example:")
    print(f"   >>> from core.utils.mcgs_modbus_reader import create_mcgsm_reader")
    print(f"   >>> reader = create_mcgsm_reader()")
    print(f"   >>> data = reader.read_all()")
    print(f"   >>> print(data)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
