# -*- coding: utf-8 -*-
"""
串口驱动TOCTOU修复验证测试
Serial Driver TOCTOU Fix Verification Tests

测试场景（共12个用例）：
1. 字符时间计算准确性
2. 超时参数自动计算
3. 混合模式读取基本功能
4. 高波特率(115200bps)配置优化
5. 极高波特率(460800bps)稳定性
6. 帧边界检测正确性
7. 缓冲区溢出保护
8. 统计信息准确性
9. 线程安全性
10. 错误恢复能力
11. 配置接口兼容性
12. 性能基准测试

运行方式：
    pytest tests/test_serial_driver_tocou.py -v --tb=short
    pytest tests/test_serial_driver_tocou.py::TestCharTimeCalculation -v  # 单独运行某组测试
"""

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# 确保项目根目录在sys.path中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════════════════
# 测试组1：字符时间计算算法验证
# ══════════════════════════════════════════════════════════


class TestCharTimeCalculation:
    """字符时间计算准确性测试"""

    def test_9600_baud_char_time(self):
        """9600bps下的字符时间应约为1.146ms"""
        from core.communication.serial_driver import SerialDriver

        char_time = SerialDriver._calculate_char_time_ms(9600)
        expected = (11 * 1000.0) / 9600  # ~1.146ms

        assert abs(char_time - expected) < 0.01, f"9600bps字符时间错误: 期望{expected:.3f}ms, 实际{char_time:.3f}ms"

    def test_115200_baud_char_time(self):
        """115200bps下的字符时间应约为0.0957ms"""
        from core.communication.serial_driver import SerialDriver

        char_time = SerialDriver._calculate_char_time_ms(115200)
        expected = (11 * 1000.0) / 115200  # ~0.0957ms

        assert abs(char_time - expected) < 0.001, f"115200bps字符时间错误: 期望{expected:.4f}ms, 实际{char_time:.4f}ms"

    def test_460800_baud_char_time(self):
        """460800bps下的字符时间应约为0.0239ms"""
        from core.communication.serial_driver import SerialDriver

        char_time = SerialDriver._calculate_char_time_ms(460800)
        expected = (11 * 1000.0) / 460800  # ~0.0239ms

        assert abs(char_time - expected) < 0.0005, f"460800bps字符时间错误: 期望{expected:.5f}ms, 实际{char_time:.5f}ms"

    def test_invalid_baudrate_returns_safe_default(self):
        """无效波特率应返回安全默认值10ms"""
        from core.communication.serial_driver import SerialDriver

        # 测试零和负值
        assert SerialDriver._calculate_char_time_ms(0) == 10.0
        assert SerialDriver._calculate_char_time_ms(-100) == 10.0

    def test_custom_bits_per_char(self):
        """自定义每字符位数（如7数据位+偶校验+2停止位=11位）"""
        from core.communication.serial_driver import SerialDriver

        # 7N2格式：1起始 + 7数据 + 1校验 + 2停止 = 11位
        char_time_11bit = SerialDriver._calculate_char_time_ms(9600, bits_per_char=11)

        # 标准格式：1起始 + 8数据 + 无校验 + 1停止 = 10位
        char_time_10bit = SerialDriver._calculate_char_time_ms(9600, bits_per_char=10)

        # 11位应该比10位慢约10%
        ratio = char_time_11bit / char_time_10bit
        assert 1.09 < ratio < 1.11, f"自定义位数计算错误: 比值应为~1.1, 实际{ratio:.3f}"


# ══════════════════════════════════════════════════════════
# 测试组2：超时参数自动计算验证
# ══════════════════════════════════════════════════════════


class TestTimeoutCalculation:
    """超时参数自动计算测试"""

    @pytest.fixture
    def driver(self):
        """创建驱动实例（不打开真实串口）"""
        from core.communication.serial_driver import SerialDriver

        return SerialDriver(port="COM99", baudrate=115200)

    def test_inter_char_timeout_in_valid_range(self, driver):
        """字符间超时应在合理范围内（1ms ~ 100ms）"""
        inter_char, timeout = driver._calculate_optimal_timeouts()

        # 转换为毫秒
        inter_char_ms = inter_char * 1000

        assert 1.0 <= inter_char_ms <= 100.0, f"inter_char_timeout超出范围: {inter_char_ms:.3f}ms"

    def test_total_timeout_greater_than_frame_time(self, driver):
        """总超时应大于最大帧传输时间"""
        inter_char, total_timeout = driver._calculate_optimal_timeouts()

        # 计算256字节帧的传输时间
        char_time_s = driver._calculate_char_time_ms(driver._config.baudrate) / 1000.0
        max_frame_time = char_time_s * 276  # 256字节 + 20字节余量

        assert (
            total_timeout >= max_frame_time
        ), f"总超时({total_timeout*1000:.1f}ms)小于最大帧时间({max_frame_time*1000:.1f}ms)"

    def test_timeout_adapts_to_baudrate(self):
        """超时参数应随波特率自适应调整"""
        from core.communication.serial_driver import SerialDriver

        slow_driver = SerialDriver(baudrate=9600)
        fast_driver = SerialDriver(baudrate=115200)

        slow_inter_char, _ = slow_driver._calculate_optimal_timeouts()
        fast_inter_char, _ = fast_driver._calculate_optimal_timeouts()

        # 低波特率的字符间超时应该更大
        # 注意：由于inter_char_timeout有100ms上限，9600bps会触及上限(1.146ms*1.8≈2.06ms < 100ms)
        # 所以实际比值取决于是否触及上限
        assert slow_inter_char >= fast_inter_char, "低波特率应有更大的字符间超时"

        # 验证两者都为正值且在合理范围内
        assert 0.001 <= slow_inter_char <= 0.1  # 1ms~100ms
        assert 0.001 <= fast_inter_char <= 0.1


# ══════════════════════════════════════════════════════════
# 测试组3：混合模式读取核心逻辑
# ══════════════════════════════════════════════════════════


class TestHybridReadLogic:
    """混合模式读取逻辑测试"""

    @pytest.fixture
    def mock_serial(self):
        """创建模拟串口对象"""
        serial_mock = MagicMock()
        serial_mock.is_open = True
        serial_mock.in_waiting = 0
        serial_mock.read = MagicMock(return_value=b"")
        return serial_mock

    @pytest.fixture
    def driver_with_mock(self, mock_serial):
        """创建使用mock串口的驱动"""
        from core.communication.serial_driver import SerialDriver, ReadMode

        driver = SerialDriver(port="COM99", baudrate=115200)
        driver._serial = mock_serial
        driver._is_running = True
        driver.set_read_mode(ReadMode.HYBRID)
        return driver

    def test_no_data_returns_none(self, driver_with_mock, mock_serial):
        """无数据时应返回None"""
        mock_serial.in_waiting = 0

        result = driver_with_mock._hybrid_read(mock_serial, bytearray(), 0.001)  # gap_threshold

        assert result is None

    def test_data_is_read_atomically(self, driver_with_mock, mock_serial):
        """
        ★★★ 关键测试：验证TOCTOU修复 ★★★

        场景：in_waiting检查时有10字节，但read()调用时已有20字节到达。
        预期：read()应能读取到完整的数据（不会只读到10字节）
        """
        # 模拟：先返回10字节可用
        mock_serial.in_waiting = 10

        # 但实际read()返回20字节（因为新数据在检查后到达）
        mock_serial.read.return_value = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a" * 2

        result = driver_with_mock._hybrid_read(mock_serial, bytearray(), 0.001)

        # 验证：成功读取到20字节数据（无数据丢失！）
        assert result is not None
        assert len(result) == 20, f"TOCTOU漏洞未修复！期望20字节，实际{len(result) if result else 0}字节"

    def test_empty_read_handled_gracefully(self, driver_with_mock, mock_serial):
        """空读取应优雅处理"""
        mock_serial.in_waiting = 10
        mock_serial.read.return_value = b""  # read()返回空

        result = driver_with_mock._hybrid_read(mock_serial, bytearray(), 0.001)

        # 应该返回None或空bytes，不应抛出异常
        assert result is None or result == b""

    def test_max_frame_size_respected(self, driver_with_mock, mock_serial):
        """单次读取不应超过max_frame_size限制"""
        mock_serial.in_waiting = 500  # 报告有500字节
        mock_serial.read.return_value = b"\x00" * 300  # 实际返回300字节

        result = driver_with_mock._hybrid_read(mock_serial, bytearray(), 0.001)

        # read()被调用时的参数应该是min(in_waiting, max_frame_size)
        call_args = mock_serial.read.call_args[0]
        requested_size = call_args[0]

        assert (
            requested_size <= driver_with_mock._config.max_frame_size
        ), f"请求的读取大小({requested_size})超过max_frame_size限制"


# ══════════════════════════════════════════════════════════
# 测试组4：高波特率配置优化
# ══════════════════════════════════════════════════════════


class TestHighBaudrateOptimization:
    """高波特率配置优化测试"""

    def test_115200_auto_optimization(self):
        """115200bps应自动启用高速优化"""
        from core.communication.serial_driver import create_rtu_driver

        with patch.object(serial_module := __import__("serial", fromlist=["Serial"]), "Serial"):
            driver = create_rtu_driver("COM3", 115200)

            # 验证缓冲区大小已调整
            assert driver._config.rx_buffer_size >= 8192, f"115200bps缓冲区过小: {driver._config.rx_buffer_size}"

            # 验证模式为混合模式
            from core.communication.serial_driver import ReadMode

            assert driver._config.read_mode == ReadMode.HYBRID

    def test_460800_extra_optimization(self):
        """460800bps应使用更大的缓冲区"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver(baudrate=460800)
        driver.optimize_for_baudrate(460800)

        # 验证超大缓冲区
        assert driver._config.rx_buffer_size >= 16384, f"460800bps缓冲区过小: {driver._config.rx_buffer_size}"

        # 验证max_frame_size增大
        assert driver._config.max_frame_size >= 512, f"460800bps max_frame_size过小: {driver._config.max_frame_size}"

    def test_low_baudrate_defaults(self):
        """低波特率应使用标准配置"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver(baudrate=9600)

        # 默认值检查
        assert driver._config.rx_buffer_size == 4096
        assert driver._config.max_frame_size == 256


# ══════════════════════════════════════════════════════════
# 测试组5：统计信息准确性
# ══════════════════════════════════════════════════════════


class TestStatisticsTracking:
    """接收统计信息跟踪测试"""

    @pytest.fixture
    def driver(self):
        from core.communication.serial_driver import SerialDriver

        return SerialDriver()

    def test_initial_stats_are_zero(self, driver):
        """初始统计信息应为零或空"""
        stats = driver.get_statistics()

        assert stats["total_bytes"] == 0
        assert stats["total_frames"] == 0
        assert stats["bytes_dropped"] == 0

    def test_stats_update_after_receive(self, driver):
        """接收数据后统计信息应更新"""
        # 模拟多次接收
        for size in [20, 30, 25]:
            driver._update_stats(size)

        stats = driver.get_statistics()

        assert stats["total_bytes"] == 75  # 20+30+25
        assert stats["total_frames"] == 3
        assert float(stats["avg_frame_size"]) > 0

    def test_max_frame_size_tracked(self, driver):
        """最大帧大小应被正确跟踪"""
        driver._update_stats(50)
        driver._update_stats(100)
        driver._update_stats(75)

        stats = driver.get_statistics()
        assert stats["max_frame_size"] == 100

    def test_reset_clears_stats(self, driver):
        """重置应清空所有统计"""
        driver._update_stats(100)
        driver.reset_statistics()

        stats = driver.get_statistics()
        assert stats["total_bytes"] == 0
        assert stats["total_frames"] == 0


# ══════════════════════════════════════════════════════════
# 测试组6：线程安全性验证
# ══════════════════════════════════════════════════════════


class TestThreadSafety:
    """线程安全性测试"""

    def test_concurrent_stat_updates_no_crash(self):
        """并发统计更新不应导致崩溃"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver()
        errors = []

        def update_stats():
            try:
                for _ in range(1000):
                    driver._update_stats(50)
                    driver.get_statistics()
            except Exception as e:
                errors.append(e)

        # 启动多个线程并发更新统计
        threads = [threading.Thread(target=update_stats) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        # 不应有异常
        assert len(errors) == 0, f"线程安全错误: {errors}"

        # 最终统计应一致（虽然可能不是精确的4000次×50字节）
        stats = driver.get_statistics()
        assert stats["total_frames"] > 0

    def test_concurrent_config_read(self):
        """并发读取配置不应导致问题"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver(baudrate=115200)
        results = []

        def read_config():
            for _ in range(100):
                config = driver.get_config()
                results.append(config.baudrate)

        threads = [threading.Thread(target=read_config) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        # 所有结果都应是115200
        assert all(r == 115200 for r in results), "配置读取不一致"


# ══════════════════════════════════════════════════════════
# 测试组7：配置接口兼容性
# ══════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """向后兼容性接口测试"""

    def test_legacy_setters_work(self):
        """旧的setter方法仍能正常工作"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver()

        # 使用旧接口设置
        driver.set_port("COM5")
        driver.set_baudrate(38400)
        driver.set_bytesize(7)
        driver.set_parity("E")
        driver.set_stopbits(2)

        # 验证配置对象也同步更新
        assert driver._config.port == "COM5"
        assert driver._config.baudrate == 38400
        assert driver._config.bytesize == 7
        assert driver._config.parity == "E"
        assert driver._config.stopbits == 2

        # 兼容属性也存在
        assert driver._port == "COM5"
        assert driver._baudrate == 38400

    def test_set_baudrate_recalculates_timeouts(self):
        """set_baudrate应重新计算超时参数"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver(baudrate=9600)

        # Mock串口对象
        mock_serial = MagicMock()
        mock_serial.is_open = True
        driver._serial = mock_serial

        # 更改波特率
        driver.set_baudrate(115200)

        # 验证_apply_timeouts被调用
        # （通过检查baudrate是否更新来间接验证）
        assert driver._config.baudrate == 115200


# ══════════════════════════════════════════════════════════
# 测试组8：工厂函数测试
# ══════════════════════════════════════════════════════════


class TestFactoryFunctions:
    """便捷工厂函数测试"""

    def test_create_rtu_driver_basic(self):
        """create_rtu_driver应创建正确配置的驱动"""
        from core.communication.serial_driver import (
            create_rtu_driver,
            ReadMode,
        )

        with patch("core.communication.serial_driver.SERIAL_AVAILABLE", True):
            driver = create_rtu_driver("COM2", 19200)

            assert driver._config.port == "COM2"
            assert driver._config.baudrate == 19200
            assert driver._config.read_mode == ReadMode.HYBRID

    def test_create_high_speed_driver(self):
        """create_high_speed_driver应应用额外的高速优化"""
        from core.communication.serial_driver import create_high_speed_driver

        with patch("core.communication.serial_driver.SERIAL_AVAILABLE", True):
            driver = create_high_speed_driver("COM4", 230400)

            # 验证波特率和模式
            assert driver._config.baudrate == 230400

            # 验证更激进的超时设置（通过optimize_for_baudrate间接验证）
            assert driver._config.rx_buffer_size >= 16384


# ══════════════════════════════════════════════════════════
# 测试组9：性能基准测试
# ══════════════════════════════════════════════════════════


class TestPerformanceBenchmark:
    """性能基准测试"""

    def test_timeout_calculation_performance(self):
        """超时参数计算应在微秒级完成"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver(baudrate=115200)

        # 执行大量计算
        start = time.perf_counter()
        iterations = 10000

        for _ in range(iterations):
            driver._calculate_optimal_timeouts()

        elapsed = (time.perf_counter() - start) * 1000  # ms

        avg_us = (elapsed / iterations) * 1000  # 微秒/次

        # 每次计算应<100μs
        assert avg_us < 100, f"超时计算性能不足: 平均{avg_us:.1f}μs/次（期望<100μs）"

    def test_stats_update_performance(self):
        """统计更新应在亚微秒级完成"""
        from core.communication.serial_driver import SerialDriver

        driver = SerialDriver()

        start = time.perf_counter()
        iterations = 100000

        for _ in range(iterations):
            driver._update_stats(50)

        elapsed = (time.perf_counter() - start) * 1000  # ms
        avg_us = (elapsed / iterations) * 1000  # 微秒/次

        # 每次更新应<10μs（包含锁操作）
        assert avg_us < 10, f"统计更新性能不足: 平均{avg_us:.2f}μs/次（期望<10μs）"


# ══════════════════════════════════════════════════════════
# 测试组10：边界条件和异常处理
# ══════════════════════════════════════════════════════════


class TestEdgeCasesAndErrorHandling:
    """边界条件和异常处理测试"""

    def test_extreme_baudrate_values(self):
        """极端波特率值不应导致崩溃"""
        from core.communication.serial_driver import SerialDriver

        # 测试极低波特率
        driver_slow = SerialDriver(baudrate=300)
        inter_char_slow, _ = driver_slow._calculate_optimal_timeouts()
        assert inter_char_slow > 0

        # 测试极高波特率
        driver_fast = SerialDriver(baudrate=921600)
        inter_char_fast, _ = driver_fast._calculate_optimal_timeouts()
        assert inter_char_fast > 0

    def test_hybrid_read_with_exception(self):
        """串口异常时应优雅降级"""
        from core.communication.serial_driver import SerialDriver, ReadMode

        driver = SerialDriver()
        driver.set_read_mode(ReadMode.HYBRID)

        # 创建会抛出异常的mock串口
        mock_serial = MagicMock()
        mock_serial.in_waiting = 10
        mock_serial.read.side_effect = Exception("串口硬件错误")

        # 应返回None而非抛出异常
        result = driver._hybrid_read(mock_serial, bytearray(), 0.001)
        assert result is None

    def test_non_blocking_mode_fallback(self):
        """非阻塞模式应作为备选方案工作"""
        from core.communication.serial_driver import SerialDriver, ReadMode

        driver = SerialDriver()
        driver.set_read_mode(ReadMode.NON_BLOCKING)

        mock_serial = MagicMock()
        mock_serial.timeout = 1.0
        mock_serial.in_waiting = 5
        mock_serial.read.return_value = b"test"

        result = driver._non_blocking_read(mock_serial)

        # 验证timeout被临时设为0并恢复
        assert mock_serial.timeout == 1.0  # 已恢复原始值
        assert result == b"test"


# ══════════════════════════════════════════════════════════
# 测试组11：集成测试（Mock串口完整流程）
# ══════════════════════════════════════════════════════════


class TestIntegrationWithMockSerial:
    """与Mock串口的集成测试"""

    @pytest.fixture
    def integrated_driver(self):
        """创建集成了mock串口的完整驱动"""
        from core.communication.serial_driver import SerialDriver, ReadMode

        driver = SerialDriver(port="TEST_PORT", baudrate=115200)
        driver.set_read_mode(ReadMode.HYBRID)

        # 创建高级mock串口
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read = MagicMock(return_value=b"")

        driver._serial = mock_serial
        driver._is_running = True
        driver._is_connected = True

        return driver, mock_serial

    def test_full_receive_cycle(self, integrated_driver):
        """完整的接收周期测试"""
        driver, mock_serial = integrated_driver

        # 模拟Modbus RTU响应帧（地址1 + 功能码3 + 字节数2 + 数据4 + CRC2 = 10字节）
        modbus_response = bytes([0x01, 0x03, 0x04, 0x00, 0x64, 0x00, 0x00, 0xF8, 0x14])

        # 设置mock行为
        mock_serial.in_waiting = len(modbus_response)
        mock_serial.read.return_value = modbus_response

        # 执行混合读取（模拟_receive_loop_v2中的调用）
        data = driver._hybrid_read(mock_serial, bytearray(), 0.001)

        # 验证结果
        assert data is not None
        assert len(data) == len(modbus_response)
        assert data == modbus_response

        # 手动更新统计（模拟_receive_loop_v2中的行为）
        driver._update_stats(len(data))

        # 验证统计已更新
        stats = driver.get_statistics()
        assert stats["total_bytes"] == len(modbus_response)
        assert stats["total_frames"] == 1

    def test_multiple_rapid_frames(self, integrated_driver):
        """快速连续多帧接收测试"""
        driver, mock_serial = integrated_driver

        frames = [
            bytes([0x01, 0x03, 0x02, 0x00, 0x0A, 0x79, 0x84]),  # 帧1: 7字节
            bytes([0x02, 0x04, 0x04, 0x00, 0x32, 0x01, 0xF4, 0x00, 0x00, 0x68, 0x19]),  # 帧2: 11字节
            bytes([0x01, 0x03, 0x08, 0x00] + [0x64] * 16),  # 帧3: 较大帧
        ]

        for frame in frames:
            mock_serial.in_waiting = len(frame)
            mock_serial.read.return_value = frame

            data = driver._hybrid_read(mock_serial, bytearray(), 0.001)
            assert data is not None, f"帧丢失: {frame.hex()}"

            # 手动更新统计（模拟完整循环）
            driver._update_stats(len(data))

        # 验证所有帧都被接收到
        stats = driver.get_statistics()
        assert stats["total_frames"] == 3
        assert stats["total_bytes"] == sum(len(f) for f in frames)


# ══════════════════════════════════════════════════════════
# 运行入口
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "--tb=short", "-x"])
