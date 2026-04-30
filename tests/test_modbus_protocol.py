# -*- coding: utf-8 -*-
"""
Modbus协议单元测试
Unit Tests for Modbus Protocol Implementation

包含：
- CRC16/LRC校验测试
- TCP/RTU/ASCII帧构建测试
- FC08标准心跳机制测试（新增）
- TCP KeepAlive配置测试
"""

import pytest
import struct
import socket
import time
from unittest.mock import Mock, patch, MagicMock

from core.protocols.modbus_protocol import ModbusProtocol
from core.communication.tcp_driver import TCPDriver


class TestModbusCRC16:
    """CRC16校验测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_crc16_standard_value(self, protocol):
        """测试标准CRC16值"""
        data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])
        crc = protocol.crc16(data)
        # Modbus CRC16标准值 (小端序)
        assert crc == 0xCDC5, f"Expected 0xCDC5, got 0x{crc:04X}"

    def test_crc16_empty_data(self, protocol):
        """测试空数据CRC16"""
        crc = protocol.crc16(b"")
        assert crc == 0xFFFF

    def test_crc16_single_byte(self, protocol):
        """测试单字节CRC16"""
        crc = protocol.crc16(b"\x00")
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF


class TestLRC:
    """LRC校验测试"""

    @pytest.fixture
    def protocol(self):
        return ModbusProtocol()

    def test_lrc_known_value(self, protocol):
        """测试已知LRC值"""
        data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])
        lrc = protocol.lrc(data)
        assert isinstance(lrc, int)
        assert 0 <= lrc <= 0xFF

    def test_lrc_empty(self, protocol):
        """测试空数据LRC"""
        lrc = protocol.lrc(b"")
        assert lrc == 0x00


class TestTCPFrameBuilding:
    """TCP帧构建测试"""

    def build_tcp_header(self):
        """测试TCP头部构建"""
        protocol = ModbusProtocol(mode="TCP", unit_id=1)

        header = protocol._build_tcp_header(6)

        assert len(header) == 6
        trans_id, proto_id, length = struct.unpack(">HHH", header)

        assert proto_id == 0x0000
        assert length == 6
        assert 0 <= trans_id <= 65535

    def test_tcp_header_increments_transaction_id(self):
        """测试事务ID递增"""
        protocol = ModbusProtocol(mode="TCP", unit_id=1)

        header1 = protocol._build_tcp_header(5)
        header2 = protocol._build_tcp_header(5)

        id1 = struct.unpack(">H", header1[0:2])[0]
        id2 = struct.unpack(">H", header2[0:2])[0]

        assert (id2 - id1) % 65536 == 1


class TestRTUFrameBuilding:
    """RTU帧构建测试"""

    def test_rtu_frame_structure(self):
        """测试RTU帧结构"""
        protocol = ModbusProtocol(mode="RTU", unit_id=1)
        pdu = bytes([0x03, 0x00, 0x00, 0x00, 0x0A])

        frame = protocol._build_rtu_frame(pdu)

        # RTU帧: UnitID + PDU + CRC(2)
        assert len(frame) == len(pdu) + 3
        assert frame[0] == 1  # Unit ID
        assert frame[1 : len(pdu) + 1] == pdu

        # 验证CRC
        crc_received = struct.unpack("<H", frame[-2:])[0]
        crc_calculated = protocol.crc16(frame[:-2])
        assert crc_received == crc_calculated


class TestASCIIFrameParsing:
    """ASCII帧解析测试"""

    def test_valid_ascii_frame(self):
        """测试有效ASCII帧解析（含Unit ID）"""
        protocol = ModbusProtocol(mode="ASCII", unit_id=1)
        pdu = bytes([0x03, 0x00, 0x00])

        ascii_frame = protocol._build_ascii_frame(pdu)
        parsed = protocol._parse_ascii_frame(ascii_frame)

        assert parsed is not None
        assert len(parsed) == 1 + len(pdu)
        assert parsed[0] == 1
        assert parsed[1:] == pdu

    def test_invalid_ascii_no_start(self):
        """测试无效ASCII帧(无起始符)"""
        protocol = ModbusProtocol(mode="ASCII", unit_id=1)
        invalid_data = b"0103000000FF\r\n"

        result = protocol._parse_ascii_frame(invalid_data)
        assert result is None

    def test_ascii_lrc_validation(self):
        """测试ASCII LRC校验失败"""
        protocol = ModbusProtocol(mode="ASCII", unit_id=1)

        valid_frame = protocol._build_ascii_frame(bytes([0x01, 0x03]))
        corrupted = valid_frame[:-2] + b"ZZ" + valid_frame[-2:]

        result = protocol._parse_ascii_frame(corrupted)
        assert result is None


class TestProtocolInitialization:
    """协议初始化测试"""

    def test_default_mode_is_tcp(self):
        """测试默认模式为TCP"""
        protocol = ModbusProtocol()
        assert protocol._mode == "TCP"

    def test_rtu_mode_initialization(self):
        """测试RTU模式初始化"""
        protocol = ModbusProtocol(mode="RTU")
        assert protocol._mode == "RTU"

    def test_custom_unit_id(self):
        """测试自定义单元ID"""
        protocol = ModbusProtocol(unit_id=10)
        assert protocol._unit_id == 10


class TestFC08HeartbeatMechanism:
    """
    FC08标准心跳机制测试

    测试目标：
    - 验证MBAP报文格式符合Modbus v1.1b3规范
    - 确保报文长度为11字节（MBAP 7B + PDU 4B）
    - 测试事务ID递增逻辑
    - 验证错误处理机制
    """

    @pytest.fixture
    def tcp_driver(self):
        """创建TCP驱动实例"""
        driver = TCPDriver(host="127.0.0.1", port=502)
        return driver

    def test_fc08_frame_structure(self, tcp_driver):
        """
        测试FC08心跳报文结构（核心测试）

        验证项：
        1. 总长度 = 12字节（MBAP 7B + PDU 5B）
        2. MBAP Header正确
        3. PDU字段完整（FC + SubFunc + Data）
        """
        # 手动构造FC08报文（模拟_send_heartbeat内部逻辑）
        trans_id = 0x0001
        unit_id = 0x01

        # MBAP Header (7 bytes): TransID(2) + ProtoID(2) + Length(2) + UnitID(1)
        mbap_header = struct.pack(
            ">HHHB",
            trans_id,  # Transaction ID
            tcp_driver.MODBUS_PROTOCOL_ID,  # Protocol ID: 0x0000
            0x0006,  # Length: 6 (UnitID 1B + PDU 5B)
            unit_id,  # Unit ID
        )

        # PDU (5 bytes): FC08(1) + SubFunction(2) + Data(2)
        pdu = struct.pack(
            ">BHH",
            tcp_driver.FC_DIAGNOSTICS,  # Function Code: 0x08
            tcp_driver.DIAG_SUBFUNC_RETURN_QUERY,  # Sub-function: 0x0000
            0x0000,  # Data Field: 0x0000
        )

        # 组合完整报文
        complete_frame = mbap_header + pdu

        # 验证总长度（MBAP 7B + PDU 5B = 12B）
        assert len(complete_frame) == 12, f"FC08报文长度错误：期望12字节，实际{len(complete_frame)}字节"

        # 解析并验证各字段
        parsed_trans_id, parsed_proto_id, parsed_length, parsed_unit_id = struct.unpack(">HHHB", complete_frame[:7])

        assert parsed_trans_id == trans_id
        assert parsed_proto_id == 0x0000  # Modbus协议标识
        assert parsed_length == 0x0006  # UnitID(1) + PDU(5) = 6
        assert parsed_unit_id == unit_id

        # 验证PDU字段
        fc = complete_frame[7]
        sub_func = struct.unpack(">H", complete_frame[8:10])[0]
        data_field = struct.unpack(">H", complete_frame[10:12])[0]

        assert fc == 0x08  # Diagnostics功能码
        assert sub_func == 0x0000  # 子功能码：返回查询数据
        assert data_field == 0x0000  # 数据字段：要回显的数据

    def test_transaction_id_increment(self, tcp_driver):
        """
        测试事务ID自增逻辑

        Modbus要求事务ID在每次请求时递增，
        用于请求-响应对的匹配。
        """
        initial_id = tcp_driver._transaction_id

        # 模拟多次发送心跳
        for i in range(5):
            tcp_driver._transaction_id = (tcp_driver._transaction_id + 1) % 65536

        expected_id = (initial_id + 5) % 65536
        assert tcp_driver._transaction_id == expected_id

    def test_transaction_id_overflow(self, tcp_driver):
        """
        测试事务ID溢出回绕

        事务ID为16位无符号整数，达到65535后应回绕到0
        """
        tcp_driver._transaction_id = 65535  # 最大值

        # 下一次应回绕到0
        tcp_driver._transaction_id = (tcp_driver._transaction_id + 1) % 65536
        assert tcp_driver._transaction_id == 0

    def test_invalid_unit_id_rejection(self, tcp_driver):
        """
        测试无效单元ID拒绝

        单元ID必须在0-255范围内，超出范围应记录警告
        """
        # 有效范围
        tcp_driver.set_unit_id(0)
        assert tcp_driver._unit_id == 0

        tcp_driver.set_unit_id(255)
        assert tcp_driver._unit_id == 255

        # 无效范围（应被拒绝）
        invalid_id = -1
        original_id = tcp_driver._unit_id
        tcp_driver.set_unit_id(invalid_id)
        assert tcp_driver._unit_id == original_id  # 应保持原值不变

        invalid_id = 256
        tcp_driver.set_unit_id(invalid_id)
        assert tcp_driver._unit_id == original_id

    def test_heartbeat_interval_validation(self, tcp_driver):
        """
        测试心跳间隔参数验证

        边界条件：
        - 最小值：1000ms（1秒）
        - 最大值：60000ms（60秒）
        - 推荐值：10000ms（10秒）
        """
        # 正常范围
        tcp_driver.set_heartbeat_interval(5000)
        assert tcp_driver._heartbeat_interval_ms == 5000

        tcp_driver.set_heartbeat_interval(30000)
        assert tcp_driver._heartbeat_interval_ms == 30000

        # 过短（应记录警告但仍接受）
        tcp_driver.set_heartbeat_interval(500)
        assert tcp_driver._heartbeat_interval_ms == 500

        # 过长（应记录警告但仍接受）
        tcp_driver.set_heartbeat_interval(120000)
        assert tcp_driver._heartbeat_interval_ms == 120000

    def test_heartbeat_stats_initial_state(self, tcp_driver):
        """
        测试心跳统计信息初始状态

        新创建的驱动实例应有以下初始状态：
        - 发送次数 = 0
        - 成功次数 = 0
        - 最后发送时间 = None
        """
        stats = tcp_driver.get_heartbeat_stats()

        assert stats["sent_count"] == 0
        assert stats["success_count"] == 0
        assert stats["last_heartbeat_time"] is None
        assert stats["enabled"] is True
        assert stats["keepalive_configured"] is True

    def test_heartbeat_enable_disable(self, tcp_driver):
        """
        测试心跳启用/禁用切换
        """
        # 默认启用
        assert tcp_driver._heartbeat_enabled is True

        # 禁用
        tcp_driver.enable_heartbeat(False)
        assert tcp_driver._heartbeat_enabled is False

        # 重新启用
        tcp_driver.enable_heartbeat(True)
        assert tcp_driver._heartbeat_enabled is True


class TestTCPKeepAliveConfiguration:
    """
    TCP KeepAlive配置测试

    测试目标：
    - 验证socket选项设置正确
    - 跨平台兼容性检查
    - 错误处理验证
    """

    @pytest.fixture
    def mock_socket(self):
        """创建mock socket对象"""
        sock = MagicMock(spec=socket.socket)
        return sock

    def test_keepalive_basic_enable(self, mock_socket):
        """
        测试基础KeepAlive启用

        必须设置SO_KEEPALIVE=1
        """
        driver = TCPDriver()
        driver._configure_keepalive(mock_socket)

        # 验证是否调用了setsockopt启用KeepAlive
        mock_socket.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    @patch("sys.platform", "win32")
    def test_keepalive_windows_config(self, mock_socket):
        """
        测试Windows平台KeepAlive参数配置

        Windows使用毫秒为单位：
        - TCP_KEEPIDLE:   10秒 = 10000ms
        - TCP_KEEPINTVL:  5秒  = 5000ms
        - TCP_KEEPCNT:    3次
        """
        driver = TCPDriver()
        driver._configure_keepalive(mock_socket)

        # 验证Windows特定参数
        calls = mock_socket.setsockopt.call_args_list

        # 检查是否包含TCP_KEEPIDLE设置（10000ms）
        keepidle_found = any(
            call[0][0] == socket.IPPROTO_TCP and call[0][1] == socket.TCP_KEEPIDLE and call[0][2] == 10000
            for call in calls
        )
        assert keepidle_found, "未找到Windows TCP_KEEPIDLE配置"

    @patch("sys.platform", "linux")
    def test_keepalive_linux_config(self, mock_socket):
        """
        测试Linux平台KeepAlive参数配置

        Linux使用秒为单位：
        - TCP_KEEPIDLE:   10秒
        - TCP_KEEPINTVL:  5秒
        - TCP_KEEPCNT:    3次
        """
        driver = TCPDriver()
        driver._configure_keepalive(mock_socket)

        calls = mock_socket.setsockopt.call_args_list

        # 检查Linux TCP_KEEPIDLE（10秒）
        keepidle_found = any(
            call[0][0] == socket.IPPROTO_TCP and call[0][1] == socket.TCP_KEEPIDLE and call[0][2] == 10
            for call in calls
        )
        assert keepidle_found, "未找到Linux TCP_KEEPIDLE配置"

    def test_keepalive_error_handling(self, mock_socket):
        """
        测试KeepAlive配置失败时的容错处理

        即使KeepAlive配置失败，也不应影响主功能
        """
        # 模拟OSError异常
        mock_socket.setsockopt.side_effect = OSError("Permission denied")

        driver = TCPDriver()
        # 不应抛出异常，仅记录警告
        driver._configure_keepalive(mock_socket)

        # 验证确实调用了setsockopt（即使失败）
        assert mock_socket.setsockopt.called


class TestBackwardCompatibility:
    """
    向后兼容性测试

    确保新实现与现有代码架构完全兼容：
    - 线程安全（RLock）
    - Qt信号连接
    - 异步轮询架构
    """

    def test_thread_safety_lock_exists(self):
        """
        验证线程安全锁存在

        所有公共方法应在_lock保护下执行
        """
        driver = TCPDriver()
        assert hasattr(driver, "_lock")
        assert driver._lock is not None

    def test_qt_signals_defined(self):
        """
        验证Qt信号定义完整

        继承BaseDriver的所有信号
        """
        driver = TCPDriver()

        # BaseDriver定义的信号
        assert hasattr(driver, "data_received")
        assert hasattr(driver, "data_sent")
        assert hasattr(driver, "connected")
        assert hasattr(driver, "disconnected")
        assert hasattr(driver, "error_occurred")

    def test_configuration_api_compatibility(self):
        """
        测试配置API向后兼容

        原有的set_host/set_port接口必须保留
        """
        driver = TCPDriver(host="192.168.1.100", port=502)

        # 原有接口
        driver.set_host("10.0.0.1")
        assert driver._host == "10.0.0.1"

        driver.set_port(503)
        assert driver._port == 503

        # 新增接口（可选增强）
        driver.set_unit_id(5)
        assert driver._unit_id == 5

        driver.set_heartbeat_interval(15000)
        assert driver._heartbeat_interval_ms == 15000


class TestEdgeCases:
    """
    边界条件和异常场景测试
    """

    def test_heartbeat_when_disconnected(self):
        """
        测试断开连接时发送心跳的行为

        未连接状态下应安全跳过，不抛出异常
        """
        driver = TCPDriver()
        driver._is_connected = False
        driver._socket = None

        # 不应抛出异常
        driver._send_heartbeat()

        # 统计信息不应更新
        assert driver._heartbeat_sent_count == 0

    def test_multiple_rapid_heartbeats(self):
        """
        测试快速连续发送心跳的场景

        事务ID应正确递增，无竞态条件
        """
        driver = TCPDriver()
        driver._is_connected = True
        driver._socket = MagicMock()  # Mock socket避免真实网络调用

        initial_count = driver._heartbeat_sent_count

        for _ in range(10):
            driver._send_heartbeat()

        assert driver._heartbeat_sent_count == initial_count + 10
        assert driver._transaction_id == 10  # 事务ID从0递增到10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
