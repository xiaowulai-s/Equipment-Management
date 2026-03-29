"""
ModbusTCP协议实现

实现ModbusTCP ADU (Application Data Unit) 封装:
    - MBAP头: Transaction ID + Protocol ID (0x0000) + Length + Unit ID
    - PDU: Function Code + Data
    - 事务ID管理 (线程安全循环递增)
    - 连接状态监控

支持功能码:
    读: FC01, FC02, FC03, FC04
    写: FC05, FC06, FC15, FC16

通信方式: Python原生socket (非PySide6 QTcpSocket)
线程模型: 本类所有I/O操作应在QThread中调用，通过信号返回结果到UI线程。
"""

from __future__ import annotations

import ipaddress
import socket
import struct
import time
from typing import Any, Optional, Union

from src.protocols.base_protocol import BaseProtocol, ReadResult, WriteResult, _CombinedMeta
from src.protocols.enums import DataType, DeviceStatus, Endian, FunctionCode, ProtocolType
from src.utils.exceptions import (
    ProtocolConnectionError,
    ProtocolCRCError,
    ProtocolError,
    ProtocolResponseError,
    ProtocolTimeoutError,
)
from src.utils.logger import get_logger

logger = get_logger("modbus_tcp")

# ModbusTCP固定常量
_MODBUS_PROTOCOL_ID = 0x0000  # Modbus协议标识 (固定为0)
_MAX_ADU_LENGTH = 260  # MBAP(7) + PDU(253)


class ModbusTCPProtocol(BaseProtocol, metaclass=_CombinedMeta):
    """ModbusTCP协议实现

    基于 Python socket 的 Modbus TCP 客户端。

    Usage:
        proto = ModbusTCPProtocol(host="192.168.1.100", port=502)
        proto.connect_to_device()
        result = proto.read_holding_registers(0, 10)
        proto.disconnect_from_device()

    Attributes:
        host: 目标设备IP地址
        port: 目标设备端口 (默认502)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 502,
        timeout: float = 3.0,
        slave_address: int = 1,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(
            timeout=timeout,
            slave_address=slave_address,
            parent=parent,  # type: ignore[arg-type]
        )
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None

        # 连接参数校验
        self._validate_connection_params(host, port)

    # ═══════════════════════════════════════════════════════════
    # 公共属性
    # ═══════════════════════════════════════════════════════════

    @property
    def protocol_type(self) -> ProtocolType:
        """协议类型"""
        return ProtocolType.MODBUS_TCP

    @property
    def host(self) -> str:
        """目标IP地址"""
        return self._host

    @host.setter
    def host(self, value: str) -> None:
        """设置IP地址 (含合法性校验)"""
        self._validate_host(value)
        self._host = value

    @property
    def port(self) -> int:
        """目标端口号"""
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        """设置端口号 (含合法性校验)"""
        if not 1 <= value <= 65535:
            raise ValueError(f"端口号必须在 1-65535 范围内，当前值: {value}")
        self._port = value

    @property
    def connection_info(self) -> str:
        """连接描述信息"""
        return f"{self._host}:{self._port}"

    # ═══════════════════════════════════════════════════════════
    # 连接管理
    # ═══════════════════════════════════════════════════════════

    def _do_connect(self) -> None:
        """建立TCP连接

        Raises:
            ProtocolConnectionError: 连接失败
        """
        try:
            # 创建TCP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)

            # 启用TCP Keepalive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Windows: 设置keepalive参数
            if hasattr(socket, "TCP_KEEPIDLE"):
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPIDLE,
                    10,  # 10秒后开始探测
                )
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPINTVL,
                    3,  # 每3秒探测一次
                )
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPCNT,
                    3,  # 3次失败后判定断开
                )

            sock.connect((self._host, self._port))
            self._socket = sock

            logger.info(f"TCP连接建立: {self._host}:{self._port} " f"(超时={self._timeout}s)")

        except socket.timeout:
            raise ProtocolConnectionError(
                message=(f"连接超时 ({self._timeout}s): " f"{self._host}:{self._port}"),
                details={
                    "host": self._host,
                    "port": self._port,
                    "timeout": self._timeout,
                },
            )
        except ConnectionRefusedError:
            raise ProtocolConnectionError(
                message=(f"连接被拒绝: {self._host}:{self._port} " f"(目标设备可能未运行或端口未监听)"),
                details={
                    "host": self._host,
                    "port": self._port,
                },
            )
        except OSError as e:
            raise ProtocolConnectionError(
                message=f"TCP连接失败: {e}",
                details={
                    "host": self._host,
                    "port": self._port,
                    "os_error": str(e),
                },
            )

    def _do_disconnect(self) -> None:
        """断开TCP连接"""
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                self._socket.close()
                self._socket = None
                logger.info(f"TCP连接已断开: {self.connection_info}")

    # ═══════════════════════════════════════════════════════════
    # 帧构建
    # ═══════════════════════════════════════════════════════════

    def _build_request_frame(
        self,
        function_code: FunctionCode,
        start_address: int,
        quantity: Optional[int] = None,
        value: Any = None,
    ) -> bytes:
        """构建ModbusTCP ADU请求帧

        ADU结构:
            [Transaction ID: 2B][Protocol ID: 2B][Length: 2B][Unit ID: 1B]
            [Function Code: 1B][Data: NB]

        Args:
            function_code: Modbus功能码
            start_address: 起始地址
            quantity: 读取数量 (读操作)
            value: 写入值 (写操作)

        Returns:
            完整的ModbusTCP ADU帧
        """
        transaction_id = self._next_transaction_id()
        unit_id = self._slave_address

        # 构建PDU (Protocol Data Unit)
        pdu = self._build_pdu(function_code, start_address, quantity, value)

        # 构建MBAP头
        length = len(pdu) + 1  # PDU长度 + Unit ID
        mbap_header = struct.pack(
            ">HHHB",
            transaction_id,
            _MODBUS_PROTOCOL_ID,
            length,
            unit_id,
        )

        frame = mbap_header + pdu

        logger.debug(
            f"构建请求帧: TID={transaction_id} "
            f"FC={function_code:#04x} "
            f"Addr={start_address:#06x} "
            f"帧长={len(frame)}B "
            f"HEX={frame.hex()}"
        )

        return frame

    def _build_pdu(
        self,
        function_code: FunctionCode,
        start_address: int,
        quantity: Optional[int] = None,
        value: Any = None,
    ) -> bytes:
        """构建PDU (Protocol Data Unit)

        PDU结构: [Function Code: 1B][Data: NB]
        """
        fc = function_code

        # ── 读操作: FC01, FC02, FC03, FC04 ──
        if fc in (
            FunctionCode.READ_COILS,
            FunctionCode.READ_DISCRETE_INPUTS,
            FunctionCode.READ_HOLDING_REGISTERS,
            FunctionCode.READ_INPUT_REGISTERS,
        ):
            if quantity is None:
                raise ProtocolError(
                    message=f"{fc.description}需要quantity参数",
                    error_code="MISSING_PARAMETER",
                    details={"function_code": int(fc)},
                )
            return struct.pack(">BHH", int(fc), start_address, quantity)

        # ── 写单个线圈: FC05 ──
        if fc == FunctionCode.WRITE_SINGLE_COIL:
            coil_value = 0xFF00 if value else 0x0000
            return struct.pack(">BHH", int(fc), start_address, coil_value)

        # ── 写单个寄存器: FC06 ──
        if fc == FunctionCode.WRITE_SINGLE_REGISTER:
            reg_value = int(value) & 0xFFFF
            return struct.pack(">BHH", int(fc), start_address, reg_value)

        # ── 写多个线圈: FC15 ──
        if fc == FunctionCode.WRITE_MULTIPLE_COILS:
            if not isinstance(value, list):
                raise ProtocolError(
                    message="FC15需要list[bool]类型的value参数",
                    error_code="INVALID_PARAMETER",
                    details={"function_code": 15},
                )
            coil_values: list[bool] = value
            quantity = len(coil_values)
            # 将bool列表打包为字节数组
            byte_count = (quantity + 7) // 8
            coils_bytes = bytearray(byte_count)
            for i, bit_val in enumerate(coil_values):
                if bit_val:
                    byte_idx = i // 8
                    bit_idx = i % 8
                    coils_bytes[byte_idx] |= 1 << bit_idx
            pdu = struct.pack(">BHHB", int(fc), start_address, quantity, byte_count)
            pdu += bytes(coils_bytes)
            return pdu

        # ── 写多个寄存器: FC16 ──
        if fc == FunctionCode.WRITE_MULTIPLE_REGISTERS:
            if isinstance(value, (bytes, bytearray)):
                raw_bytes = bytes(value)
            elif isinstance(value, list):
                # 将值列表编码为原始字节 (调用方已编码)
                raw_bytes = bytes(value)
            else:
                raise ProtocolError(
                    message="FC16需要bytes或list类型的value参数",
                    error_code="INVALID_PARAMETER",
                    details={"function_code": 16},
                )
            register_count = len(raw_bytes) // 2
            pdu = struct.pack(
                ">BHHB",
                int(fc),
                start_address,
                register_count,
                len(raw_bytes),
            )
            pdu += raw_bytes
            return pdu

        raise ProtocolError(
            message=f"不支持的功能码: {fc:#04x}",
            error_code="UNSUPPORTED_FUNCTION_CODE",
            details={"function_code": int(fc)},
        )

    # ═══════════════════════════════════════════════════════════
    # 通信收发
    # ═══════════════════════════════════════════════════════════

    def _send_and_receive(self, request_frame: bytes) -> bytes:
        """发送请求帧并接收响应

        流程:
            1. 通过socket发送完整的ADU帧
            2. 读取MBAP头 (7字节) 获取后续数据长度
            3. 读取剩余数据
            4. 校验事务ID匹配

        Args:
            request_frame: 完整的ModbusTCP ADU请求帧

        Returns:
            响应PDU数据 (不含MBAP头)

        Raises:
            ProtocolTimeoutError: 接收超时
            ProtocolConnectionError: 连接断开
            ProtocolResponseError: 响应异常
        """
        if not self._socket:
            raise ProtocolConnectionError(
                message="socket未建立，无法发送数据",
                details={"connection_info": self.connection_info},
            )

        try:
            # 提取请求帧的事务ID (用于响应校验)
            request_tid = struct.unpack(">H", request_frame[0:2])[0]

            # 发送请求
            self._socket.sendall(request_frame)
            logger.debug(f"已发送 {len(request_frame)} 字节 " f"TID={request_tid}")

            # 接收MBAP头 (7字节)
            mbap_header = self._recv_exact(7)
            (
                response_tid,
                protocol_id,
                length,
                unit_id,
            ) = struct.unpack(">HHHB", mbap_header)

            # 校验事务ID
            if response_tid != request_tid:
                raise ProtocolResponseError(
                    message=(f"事务ID不匹配: 期望={request_tid}, " f"实际={response_tid}"),
                    function_code=0,
                    details={
                        "expected_tid": request_tid,
                        "actual_tid": response_tid,
                    },
                )

            # 校验协议ID
            if protocol_id != _MODBUS_PROTOCOL_ID:
                raise ProtocolResponseError(
                    message=(f"协议ID不匹配: 期望=0x0000, " f"实际={protocol_id:#06x}"),
                    function_code=0,
                    details={
                        "expected_pid": _MODBUS_PROTOCOL_ID,
                        "actual_pid": protocol_id,
                    },
                )

            # 校验长度合理性
            if length < 1 or length > _MAX_ADU_LENGTH - 6:
                raise ProtocolResponseError(
                    message=f"响应长度异常: {length}",
                    function_code=0,
                    details={"length": length},
                )

            # 接收PDU数据 (length - 1, 因为unit_id已包含在header中)
            pdu_length = length - 1
            pdu_data = self._recv_exact(pdu_length) if pdu_length > 0 else b""

            # 合并unit_id + pdu_data作为完整响应数据
            response_data = bytes([unit_id]) + pdu_data

            logger.debug(f"已接收 TID={response_tid} " f"UnitID={unit_id} " f"PDU={pdu_data.hex()}")

            return response_data

        except socket.timeout:
            raise ProtocolTimeoutError(
                message=(f"接收响应超时 ({self._timeout}s): " f"{self.connection_info}"),
                timeout_seconds=self._timeout,
                details={
                    "host": self._host,
                    "port": self._port,
                    "timeout": self._timeout,
                },
            )
        except (ConnectionResetError, BrokenPipeError) as e:
            self.set_status(DeviceStatus.DISCONNECTED)
            self.disconnected.emit()
            raise ProtocolConnectionError(
                message=f"连接被重置: {e}",
                details={
                    "host": self._host,
                    "port": self._port,
                },
            )
        except OSError as e:
            # socket关闭等底层错误
            self.set_status(DeviceStatus.DISCONNECTED)
            self.disconnected.emit()
            raise ProtocolConnectionError(
                message=f"通信错误: {e}",
                details={
                    "host": self._host,
                    "port": self._port,
                    "os_error": str(e),
                },
            )

    def _recv_exact(self, expected_length: int) -> bytes:
        """精确接收指定长度的数据

        Args:
            expected_length: 期望接收的字节数

        Returns:
            接收到的字节数据

        Raises:
            ProtocolTimeoutError: 超时
            ProtocolConnectionError: 连接断开
        """
        if not self._socket:
            raise ProtocolConnectionError(
                message="socket未建立",
                details={"connection_info": self.connection_info},
            )

        data = bytearray()
        remaining = expected_length
        deadline = time.monotonic() + self._timeout

        while remaining > 0:
            elapsed = time.monotonic() - deadline
            if elapsed >= 0:
                raise ProtocolTimeoutError(
                    message=(f"接收数据不完整: " f"期望{expected_length}字节, " f"已接收{len(data)}字节"),
                    timeout_seconds=self._timeout,
                    details={
                        "expected": expected_length,
                        "received": len(data),
                    },
                )

            # 动态调整剩余超时
            remaining_timeout = max(deadline - time.monotonic(), 0.1)
            self._socket.settimeout(remaining_timeout)

            try:
                chunk = self._socket.recv(remaining)
                if not chunk:
                    # 连接已关闭
                    raise ProtocolConnectionError(
                        message=(f"连接已关闭 (接收中断): " f"期望{expected_length}字节, " f"已接收{len(data)}字节"),
                        details={
                            "expected": expected_length,
                            "received": len(data),
                        },
                    )
                data.extend(chunk)
                remaining -= len(chunk)
            except socket.timeout:
                raise ProtocolTimeoutError(
                    message=(f"接收超时: 期望{expected_length}字节, " f"已接收{len(data)}字节"),
                    timeout_seconds=self._timeout,
                    details={
                        "expected": expected_length,
                        "received": len(data),
                    },
                )

        return bytes(data)

    # ═══════════════════════════════════════════════════════════
    # 响应解析
    # ═══════════════════════════════════════════════════════════

    def _parse_response_frame(
        self,
        function_code: FunctionCode,
        response_data: bytes,
        start_address: int,
    ) -> ReadResult:
        """解析ModbusTCP读取响应帧

        响应PDU格式:
            正常响应: [FC: 1B][Byte Count: 1B][Data: NB]
            异常响应: [FC|0x80: 1B][Exception Code: 1B]

        Args:
            function_code: 请求的功能码
            response_data: 响应数据 (unit_id + pdu)
            start_address: 起始地址

        Returns:
            ReadResult 解析结果
        """
        if len(response_data) < 2:
            raise ProtocolResponseError(
                message=f"响应数据过短: {len(response_data)}字节",
                function_code=int(function_code),
                details={"length": len(response_data)},
            )

        # 跳过Unit ID (第1字节)
        pdu = response_data[1:]
        response_fc = pdu[0]

        # ── 异常响应检测 ──
        if response_fc & 0x80:
            exception_code = pdu[1] if len(pdu) > 1 else 0
            exception_info = self._get_exception_description(exception_code)
            raise ProtocolResponseError(
                message=(
                    f"Modbus异常响应: "
                    f"FC={function_code:#04x} "
                    f"异常码={exception_code:#04x} "
                    f"({exception_info})"
                ),
                function_code=int(function_code),
                exception_code=exception_code,
                details={
                    "function_code": int(function_code),
                    "exception_code": exception_code,
                    "exception_description": exception_info,
                },
            )

        # 校验功能码匹配
        if response_fc != int(function_code):
            raise ProtocolResponseError(
                message=(f"功能码不匹配: 期望={function_code:#04x}, " f"实际={response_fc:#04x}"),
                function_code=int(function_code),
                details={
                    "expected_fc": int(function_code),
                    "actual_fc": response_fc,
                },
            )

        # ── 正常响应解析 ──
        if function_code.is_bit_access:
            # 位操作响应: FC01, FC02
            # 格式: [FC][Byte Count][Coil Status bytes]
            byte_count = pdu[1]
            coil_bytes = pdu[2 : 2 + byte_count]
            values = self._unpack_bits(coil_bytes, byte_count * 8)

            return ReadResult(
                function_code=int(function_code),
                start_address=start_address,
                values=values,
                raw_data=coil_bytes,
                success=True,
            )

        # 寄存器操作响应: FC03, FC04
        # 格式: [FC][Byte Count][Register Data bytes]
        byte_count = pdu[1]
        register_bytes = pdu[2 : 2 + byte_count]
        values = self._unpack_registers(register_bytes)

        return ReadResult(
            function_code=int(function_code),
            start_address=start_address,
            values=values,
            raw_data=register_bytes,
            success=True,
        )

    def _parse_write_response(
        self,
        function_code: FunctionCode,
        response_data: bytes,
        address: int,
    ) -> WriteResult:
        """解析ModbusTCP写入响应帧

        写入响应PDU格式:
            FC05/FC06 (写单个): [FC: 1B][Address: 2B][Value: 2B]
            FC15/FC16 (写多个): [FC: 1B][Start Address: 2B][Quantity: 2B]

        Args:
            function_code: 请求的功能码
            response_data: 响应数据 (unit_id + pdu)
            address: 写入地址

        Returns:
            WriteResult 解析结果
        """
        if len(response_data) < 2:
            raise ProtocolResponseError(
                message=f"写入响应数据过短: {len(response_data)}字节",
                function_code=int(function_code),
                details={"length": len(response_data)},
            )

        pdu = response_data[1:]
        response_fc = pdu[0]

        # 异常响应检测
        if response_fc & 0x80:
            exception_code = pdu[1] if len(pdu) > 1 else 0
            exception_info = self._get_exception_description(exception_code)
            raise ProtocolResponseError(
                message=(f"写入异常: FC={function_code:#04x} " f"异常码={exception_code:#04x} " f"({exception_info})"),
                function_code=int(function_code),
                exception_code=exception_code,
                details={
                    "exception_code": exception_code,
                    "exception_description": exception_info,
                },
            )

        # FC05: 写单个线圈 → 回显 [FC][Address][Value(0xFF00/0x0000)]
        if function_code == FunctionCode.WRITE_SINGLE_COIL:
            if len(pdu) < 5:
                raise ProtocolResponseError(
                    message="FC05响应帧长度不足",
                    function_code=5,
                    details={"pdu_length": len(pdu)},
                )
            resp_addr = struct.unpack(">H", pdu[1:3])[0]
            resp_value = struct.unpack(">H", pdu[3:5])[0]
            return WriteResult(
                function_code=5,
                address=resp_addr,
                value=bool(resp_value == 0xFF00),
                success=True,
            )

        # FC06: 写单个寄存器 → 回显 [FC][Address][Value]
        if function_code == FunctionCode.WRITE_SINGLE_REGISTER:
            if len(pdu) < 5:
                raise ProtocolResponseError(
                    message="FC06响应帧长度不足",
                    function_code=6,
                    details={"pdu_length": len(pdu)},
                )
            resp_addr = struct.unpack(">H", pdu[1:3])[0]
            resp_value = struct.unpack(">H", pdu[3:5])[0]
            return WriteResult(
                function_code=6,
                address=resp_addr,
                value=resp_value,
                success=True,
            )

        # FC15: 写多个线圈 → 回显 [FC][Start Address][Quantity]
        if function_code == FunctionCode.WRITE_MULTIPLE_COILS:
            if len(pdu) < 5:
                raise ProtocolResponseError(
                    message="FC15响应帧长度不足",
                    function_code=15,
                    details={"pdu_length": len(pdu)},
                )
            resp_addr = struct.unpack(">H", pdu[1:3])[0]
            resp_qty = struct.unpack(">H", pdu[3:5])[0]
            return WriteResult(
                function_code=15,
                address=resp_addr,
                value=resp_qty,
                success=True,
            )

        # FC16: 写多个寄存器 → 回显 [FC][Start Address][Quantity]
        if function_code == FunctionCode.WRITE_MULTIPLE_REGISTERS:
            if len(pdu) < 5:
                raise ProtocolResponseError(
                    message="FC16响应帧长度不足",
                    function_code=16,
                    details={"pdu_length": len(pdu)},
                )
            resp_addr = struct.unpack(">H", pdu[1:3])[0]
            resp_qty = struct.unpack(">H", pdu[3:5])[0]
            return WriteResult(
                function_code=16,
                address=resp_addr,
                value=resp_qty,
                success=True,
            )

        raise ProtocolResponseError(
            message=f"未知的写入功能码: {function_code:#04x}",
            function_code=int(function_code),
        )

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _unpack_registers(data: bytes) -> list[int]:
        """将寄存器字节数据解包为UINT16值列表

        Args:
            data: 原始字节数据 (长度必须为偶数)

        Returns:
            UINT16值列表
        """
        if len(data) % 2 != 0:
            raise ProtocolResponseError(
                message=f"寄存器数据长度不是偶数: {len(data)}",
                function_code=0,
                details={"length": len(data)},
            )
        return list(struct.unpack(f">{len(data) // 2}H", data))

    @staticmethod
    def _unpack_bits(data: bytes, max_bits: int) -> list[bool]:
        """将位数据解包为bool列表

        Modbus位操作中，每个字节的低位(LSB)对应较低地址的位。

        Args:
            data: 位数据字节
            max_bits: 最大位数 (通常为 quantity 参数)

        Returns:
            bool值列表
        """
        values: list[bool] = []
        for byte_idx, byte_val in enumerate(data):
            for bit_idx in range(8):
                if len(values) >= max_bits:
                    break
                values.append(bool(byte_val & (1 << bit_idx)))
        return values

    @staticmethod
    def _get_exception_description(code: int) -> str:
        """获取Modbus异常码描述"""
        descriptions = {
            0x01: "非法功能码 (Illegal Function)",
            0x02: "非法数据地址 (Illegal Data Address)",
            0x03: "非法数据值 (Illegal Data Value)",
            0x04: "从站设备故障 (Slave Device Failure)",
            0x05: "确认 (Acknowledge)",
            0x06: "从站设备忙 (Slave Device Busy)",
            0x08: "存储奇偶错误 (Memory Parity Error)",
            0x0A: "网关路径不可用 (Gateway Path Unavailable)",
            0x0B: "网关目标设备无响应 (Gateway Target No Response)",
        }
        return descriptions.get(code, f"未知异常码 (Unknown: {code:#04x})")

    @staticmethod
    def _validate_connection_params(host: str, port: int) -> None:
        """校验连接参数

        Args:
            host: IP地址
            port: 端口号

        Raises:
            ValueError: 参数不合法
        """
        ModbusTCPProtocol._validate_host(host)
        if not 1 <= port <= 65535:
            raise ValueError(f"端口号必须在 1-65535 范围内，当前值: {port}")

    @staticmethod
    def _validate_host(host: str) -> None:
        """校验IP地址合法性

        允许:
            - 合法的IPv4/IPv6地址
            - 合法的主机名 (非空, 长度<=253)

        Args:
            host: IP地址或主机名

        Raises:
            ValueError: 地址不合法
        """
        if not host or len(host) > 253:
            raise ValueError(f"主机地址不合法: '{host}'")

        try:
            ipaddress.ip_address(host)
        except ValueError:
            # 不是合法IP，检查是否为合法主机名
            # 主机名规则: 只允许字母数字和连字符，且不以连字符开头/结尾
            labels = host.split(".")
            if len(labels) < 1:
                raise ValueError(f"主机地址不合法: '{host}'")
            for label in labels:
                if not label:
                    raise ValueError(f"主机名包含空标签: '{host}'")
                if label.startswith("-") or label.endswith("-"):
                    raise ValueError(f"主机名标签不能以连字符开头/结尾: '{host}'")
                if not label.replace("-", "").isalnum():
                    raise ValueError(f"主机名包含非法字符: '{host}'")

    def __repr__(self) -> str:
        return (
            f"ModbusTCPProtocol(host='{self._host}', "
            f"port={self._port}, "
            f"slave={self._slave_address}, "
            f"status={self._status.value})"
        )
