"""
ModbusASCII协议实现

实现Modbus ASCII ADU (Application Data Unit) 封装:
    - ASCII帧格式: [:起始][地址:2HEX][功能码:2HEX][数据:2NHEX][LRC:2HEX][CR][LF]
    - LRC校验 (Longitudinal Redundancy Check)
    - 串口通信 (pyserial)
    - ASCII编码/解码

支持功能码:
    读: FC01, FC02, FC03, FC04
    写: FC05, FC06, FC15, FC16

线程模型: 本类所有I/O操作应在QThread中调用，通过信号返回结果到UI线程。
"""

from __future__ import annotations

import struct
import time
from typing import Any, Optional, Union

from src.protocols.base_protocol import BaseProtocol, ReadResult, WriteResult, _CombinedMeta
from src.protocols.enums import DeviceStatus, FunctionCode, ProtocolType
from src.utils.exceptions import ProtocolConnectionError, ProtocolError, ProtocolResponseError, ProtocolTimeoutError
from src.utils.logger import get_logger

logger = get_logger("modbus_ascii")

# ASCII帧界定符
_ASCII_START = b":"
_ASCII_CR = b"\r"
_ASCII_LF = b"\n"
_ASCII_END = _ASCII_CR + _ASCII_LF


class ModbusASCIIProtocol(BaseProtocol, metaclass=_CombinedMeta):
    """ModbusASCII协议实现

    基于pyserial的Modbus ASCII客户端。

    ASCII帧格式:
        : A A F C D D D D ... L L C R LF
        其中 AA=地址(2HEX), FC=功能码(2HEX), DD=数据(2N HEX),
        LL=LRC(2HEX), CR=回车(0x0D), LF=换行(0x0A)

    Usage:
        proto = ModbusASCIIProtocol(port="COM3", baudrate=9600)
        proto.connect_to_device()
        result = proto.read_holding_registers(0, 10)
        proto.disconnect_from_device()

    Attributes:
        port: 串口号
        baudrate: 波特率 (默认9600)
    """

    def __init__(
        self,
        port: str = "COM1",
        baudrate: int = 9600,
        data_bits: int = 7,
        stop_bits: float = 1.0,
        parity: str = "E",
        timeout: float = 1.0,
        slave_address: int = 1,
        parent: Optional[object] = None,
    ) -> None:
        """初始化ModbusASCII协议

        注意: ASCII模式推荐使用 7数据位 + 偶校验 (7E1)。

        Args:
            port: 串口号
            baudrate: 波特率 (默认9600)
            data_bits: 数据位 (默认7, ASCII模式推荐)
            stop_bits: 停止位 (默认1.0)
            parity: 校验位 (默认"E" 偶校验, ASCII模式推荐)
            timeout: 超时时间 (秒)
            slave_address: 从站地址 (1-247)
            parent: Qt父对象
        """
        super().__init__(
            timeout=timeout,
            slave_address=slave_address,
            parent=parent,  # type: ignore[arg-type]
        )
        self._port = port
        self._baudrate = baudrate
        self._data_bits = data_bits
        self._stop_bits = stop_bits
        self._parity = parity
        self._serial: Any = None  # serial.Serial (延迟导入)

    # ═══════════════════════════════════════════════════════════
    # 公共属性
    # ═══════════════════════════════════════════════════════════

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.MODBUS_ASCII

    @property
    def port(self) -> str:
        return self._port

    @property
    def baudrate(self) -> int:
        return self._baudrate

    @property
    def connection_info(self) -> str:
        parity_name = {
            "N": "None",
            "E": "Even",
            "O": "Odd",
            "M": "Mark",
            "S": "Space",
        }.get(self._parity, self._parity)
        return f"{self._port} @ {self._baudrate}bps " f"({self._data_bits}{parity_name}{self._stop_bits})"

    # ═══════════════════════════════════════════════════════════
    # 串口连接管理
    # ═══════════════════════════════════════════════════════════

    def _do_connect(self) -> None:
        """打开串口连接

        Raises:
            ProtocolConnectionError: 串口打开失败
        """
        try:
            import serial

            ser = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._data_bits,
                stopbits=self._stop_bits,
                parity=self._parity,
                timeout=self._timeout,
                write_timeout=self._timeout,
            )
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            self._serial = ser

            logger.info(f"串口已打开(ASCII): {self.connection_info}")

        except ImportError:
            raise ProtocolConnectionError(
                message="pyserial库未安装，请执行: pip install pyserial",
                details={"required": "pyserial"},
            )
        except serial.SerialException as e:
            raise ProtocolConnectionError(
                message=f"串口打开失败: {self._port} - {e}",
                details={"port": self._port, "error": str(e)},
            )
        except ValueError as e:
            raise ProtocolConnectionError(
                message=f"串口参数错误: {e}",
                details={
                    "port": self._port,
                    "error": str(e),
                },
            )

    def _do_disconnect(self) -> None:
        """关闭串口连接"""
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
            finally:
                self._serial = None
                logger.info(f"串口已关闭(ASCII): {self.connection_info}")

    # ═══════════════════════════════════════════════════════════
    # LRC 校验
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def calculate_lrc(data: bytes) -> int:
        """计算LRC校验码 (Longitudinal Redundancy Check)

        算法: 将所有字节相加, 取反加1 (即补码)

        Args:
            data: 待校验的原始字节数据

        Returns:
            8位LRC校验码 (0x00-0xFF)
        """
        lrc = 0
        for byte in data:
            lrc = (lrc + byte) & 0xFF
        lrc = ((~lrc) + 1) & 0xFF
        return lrc

    @staticmethod
    def verify_lrc(data: bytes, lrc_byte: int) -> bool:
        """验证LRC校验码

        将数据(含LRC)重新计算LRC，结果应为0。

        Args:
            data: 原始数据 (不含LRC)
            lrc_byte: 接收到的LRC值

        Returns:
            校验是否通过
        """
        combined = data + bytes([lrc_byte])
        result = ModbusASCIIProtocol.calculate_lrc(combined)
        return result == 0

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
        """构建ModbusASCII请求帧

        ASCII帧格式:
            :[地址2HEX][功能码2HEX][数据2N HEX][LRC 2HEX]\\r\\n

        Args:
            function_code: Modbus功能码
            start_address: 起始地址
            quantity: 读取数量 (读操作)
            value: 写入值 (写操作)

        Returns:
            完整的ASCII帧 (字节串, 含冒号和CRLF)
        """
        # 构建PDU数据部分 (二进制)
        pdu_data = self._build_ascii_data(function_code, start_address, quantity, value)

        # 构建待LRC校验的数据: 地址 + PDU (二进制)
        lrc_input = bytes([self._slave_address]) + pdu_data
        lrc = self.calculate_lrc(lrc_input)

        # 编码为ASCII十六进制字符串
        # : + 地址(2HEX) + 数据(2N HEX) + LRC(2HEX) + \\r\\n
        hex_string = f"{self._slave_address:02X}" f"{pdu_data.hex().upper()}" f"{lrc:02X}"

        frame = _ASCII_START + hex_string.encode("ascii") + _ASCII_END

        logger.debug(
            f"构建ASCII帧: Slave={self._slave_address} "
            f"FC={function_code:#04x} "
            f"LRC={lrc:#04x} "
            f"帧='{frame.decode('ascii')}'"
        )
        return frame

    def _build_ascii_data(
        self,
        function_code: FunctionCode,
        start_address: int,
        quantity: Optional[int] = None,
        value: Any = None,
    ) -> bytes:
        """构建ASCII帧的PDU数据部分 (二进制, 不含地址和LRC)

        格式与RTU的PDU完全一致: [FC:1B][Data:NB]
        """
        fc = function_code

        # 读操作: FC01, FC02, FC03, FC04
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

        # FC05: 写单个线圈
        if fc == FunctionCode.WRITE_SINGLE_COIL:
            coil_value = 0xFF00 if value else 0x0000
            return struct.pack(">BHH", int(fc), start_address, coil_value)

        # FC06: 写单个寄存器
        if fc == FunctionCode.WRITE_SINGLE_REGISTER:
            reg_value = int(value) & 0xFFFF
            return struct.pack(">BHH", int(fc), start_address, reg_value)

        # FC15: 写多个线圈
        if fc == FunctionCode.WRITE_MULTIPLE_COILS:
            if not isinstance(value, list):
                raise ProtocolError(
                    message="FC15需要list[bool]类型的value参数",
                    error_code="INVALID_PARAMETER",
                    details={"function_code": 15},
                )
            coil_values: list[bool] = value
            qty = len(coil_values)
            byte_count = (qty + 7) // 8
            coils_bytes = bytearray(byte_count)
            for i, bit_val in enumerate(coil_values):
                if bit_val:
                    byte_idx = i // 8
                    bit_idx = i % 8
                    coils_bytes[byte_idx] |= 1 << bit_idx
            pdu = struct.pack(">BHHB", int(fc), start_address, qty, byte_count)
            pdu += bytes(coils_bytes)
            return pdu

        # FC16: 写多个寄存器
        if fc == FunctionCode.WRITE_MULTIPLE_REGISTERS:
            if isinstance(value, (bytes, bytearray)):
                raw_bytes = bytes(value)
            elif isinstance(value, list):
                raw_bytes = bytes(value)
            else:
                raise ProtocolError(
                    message="FC16需要bytes或list类型的value参数",
                    error_code="INVALID_PARAMETER",
                    details={"function_code": 16},
                )
            register_count = len(raw_bytes) // 2
            pdu = struct.pack(">BHHB", int(fc), start_address, register_count, len(raw_bytes))
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
        """发送ASCII帧并接收响应

        流程:
            1. 清空输入缓冲区
            2. 发送ASCII帧
            3. 读取直到遇到CRLF
            4. 去掉帧界定符(:和CRLF)
            5. 解码HEX为二进制
            6. LRC校验

        Args:
            request_frame: 完整的ASCII请求帧

        Returns:
            响应PDU二进制数据 (不含地址和LRC)

        Raises:
            ProtocolTimeoutError: 接收超时
            ProtocolConnectionError: 串口未打开
        """
        if not self._serial or not self._serial.is_open:
            raise ProtocolConnectionError(
                message="串口未打开",
                details={"port": self._port},
            )

        try:
            self._serial.reset_input_buffer()

            # 发送ASCII帧
            self._serial.write(request_frame)
            self._serial.flush()

            logger.debug(f"已发送ASCII帧: '{request_frame.decode('ascii', errors='replace')}'")

            # 读取响应直到CRLF
            response_ascii = self._read_ascii_response()

            # 解码ASCII HEX为二进制
            # 格式: :AABBCCCCCC...LL\\r\\n
            # 去掉冒号和CRLF
            hex_body = response_ascii.strip(_ASCII_CR + _ASCII_LF)
            if hex_body.startswith(_ASCII_START):
                hex_body = hex_body[1:]  # 去掉冒号

            # HEX字符串长度必须为偶数
            if len(hex_body) % 2 != 0:
                raise ProtocolResponseError(
                    message=f"ASCII HEX数据长度为奇数: {len(hex_body)}",
                    function_code=0,
                    details={"hex_length": len(hex_body)},
                )

            # 解码为二进制
            binary_data = bytes.fromhex(hex_body.decode("ascii"))

            if len(binary_data) < 2:
                raise ProtocolResponseError(
                    message="ASCII响应数据过短",
                    function_code=0,
                    details={"binary_length": len(binary_data)},
                )

            # 分离: 地址(1B) + PDU(NB) + LRC(1B)
            slave_id = binary_data[0]
            lrc_received = binary_data[-1]
            pdu_data = binary_data[1:-1]

            # LRC校验 (验证地址+PDU+LRC整体)
            if not self.verify_lrc(binary_data[:-1], lrc_received):
                raise ProtocolResponseError(
                    message=(
                        f"LRC校验失败: "
                        f"接收LRC={lrc_received:#04x}, "
                        f"期望={self.calculate_lrc(binary_data[:-1]):#04x}"
                    ),
                    function_code=0,
                    details={
                        "received_lrc": lrc_received,
                        "hex_body": hex_body.decode("ascii"),
                    },
                )

            return pdu_data

        except ProtocolResponseError:
            raise
        except UnicodeDecodeError as e:
            raise ProtocolResponseError(
                message=f"ASCII响应包含非ASCII字符: {e}",
                function_code=0,
            )
        except ValueError as e:
            raise ProtocolResponseError(
                message=f"ASCII HEX解码失败: {e}",
                function_code=0,
            )
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise ProtocolTimeoutError(
                    message=f"串口接收超时 ({self._timeout}s): {self._port}",
                    timeout_seconds=self._timeout,
                    details={"port": self._port},
                )
            if isinstance(e, ProtocolError):
                raise
            raise ProtocolConnectionError(
                message=f"串口通信错误: {e}",
                details={"port": self._port, "error": str(e)},
            )

    def _read_ascii_response(self) -> bytes:
        """读取完整的ASCII响应帧 (直到CRLF)

        Returns:
            原始ASCII字节 (含:起始和\\r\\n结束)
        """
        buffer = bytearray()

        # 等待起始符 ':'
        while True:
            char = self._serial.read(1)
            if not char:
                raise ProtocolTimeoutError(
                    message="等待ASCII起始符':'超时",
                    timeout_seconds=self._timeout,
                    details={"port": self._port},
                )
            if char == _ASCII_START:
                buffer.extend(char)
                break
            # 跳过非起始字符 (帧间填充)

        # 读取直到CRLF
        while True:
            char = self._serial.read(1)
            if not char:
                raise ProtocolTimeoutError(
                    message="读取ASCII帧数据超时",
                    timeout_seconds=self._timeout,
                    details={"port": self._port},
                )
            buffer.extend(char)

            # 检测结束符 \\r\\n
            if len(buffer) >= 2 and buffer[-2:] == _ASCII_END:
                break
            # 单独的\\r后可能跟\\n, 也可能是旧设备只用\\r
            if char == _ASCII_CR:
                # 再读一个看是否是\\n
                pass

        return bytes(buffer)

    # ═══════════════════════════════════════════════════════════
    # 响应解析
    # ═══════════════════════════════════════════════════════════

    def _parse_response_frame(
        self,
        function_code: FunctionCode,
        response_data: bytes,
        start_address: int,
    ) -> ReadResult:
        """解析ModbusASCII读取响应

        response_data 格式 (二进制PDU, 不含地址和LRC):
            正常: [FC:1B][ByteCount:1B][Data:NB]
            异常: [FC|0x80:1B][ExceptionCode:1B]

        注意: 解析逻辑与RTU相同 (PDU格式一致), 只是帧封装不同。
        """
        if len(response_data) < 2:
            raise ProtocolResponseError(
                message=f"ASCII响应PDU过短: {len(response_data)}字节",
                function_code=int(function_code),
                details={"length": len(response_data)},
            )

        resp_fc = response_data[0]

        # 异常响应
        if resp_fc & 0x80:
            exception_code = response_data[1] if len(response_data) > 1 else 0
            exception_info = self._get_exception_description(exception_code)
            raise ProtocolResponseError(
                message=(
                    f"Modbus ASCII异常: FC={function_code:#04x} " f"异常码={exception_code:#04x} ({exception_info})"
                ),
                function_code=int(function_code),
                exception_code=exception_code,
            )

        # 功能码匹配
        if resp_fc != int(function_code):
            raise ProtocolResponseError(
                message=(f"功能码不匹配: 期望={function_code:#04x}, " f"实际={resp_fc:#04x}"),
                function_code=int(function_code),
            )

        # 位操作: FC01, FC02
        if function_code.is_bit_access:
            byte_count = response_data[1]
            coil_bytes = response_data[2 : 2 + byte_count]
            values = self._unpack_bits(coil_bytes, byte_count * 8)
            return ReadResult(
                function_code=int(function_code),
                start_address=start_address,
                values=values,
                raw_data=coil_bytes,
                success=True,
            )

        # 寄存器操作: FC03, FC04
        byte_count = response_data[1]
        register_bytes = response_data[2 : 2 + byte_count]
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
        """解析ModbusASCII写入响应

        PDU格式与RTU一致。
        """
        if len(response_data) < 2:
            raise ProtocolResponseError(
                message=f"ASCII写入响应PDU过短: {len(response_data)}字节",
                function_code=int(function_code),
            )

        resp_fc = response_data[0]

        # 异常响应
        if resp_fc & 0x80:
            exception_code = response_data[1] if len(response_data) > 1 else 0
            exception_info = self._get_exception_description(exception_code)
            raise ProtocolResponseError(
                message=(f"ASCII写入异常: FC={function_code:#04x} " f"异常码={exception_code:#04x} ({exception_info})"),
                function_code=int(function_code),
                exception_code=exception_code,
            )

        fc = function_code

        if fc == FunctionCode.WRITE_SINGLE_COIL:
            if len(response_data) < 5:
                raise ProtocolResponseError(message="FC05响应PDU不足", function_code=5)
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_val = struct.unpack(">H", response_data[3:5])[0]
            return WriteResult(function_code=5, address=resp_addr, value=bool(resp_val == 0xFF00), success=True)

        if fc == FunctionCode.WRITE_SINGLE_REGISTER:
            if len(response_data) < 5:
                raise ProtocolResponseError(message="FC06响应PDU不足", function_code=6)
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_val = struct.unpack(">H", response_data[3:5])[0]
            return WriteResult(function_code=6, address=resp_addr, value=resp_val, success=True)

        if fc == FunctionCode.WRITE_MULTIPLE_COILS:
            if len(response_data) < 5:
                raise ProtocolResponseError(message="FC15响应PDU不足", function_code=15)
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_qty = struct.unpack(">H", response_data[3:5])[0]
            return WriteResult(function_code=15, address=resp_addr, value=resp_qty, success=True)

        if fc == FunctionCode.WRITE_MULTIPLE_REGISTERS:
            if len(response_data) < 5:
                raise ProtocolResponseError(message="FC16响应PDU不足", function_code=16)
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_qty = struct.unpack(">H", response_data[3:5])[0]
            return WriteResult(function_code=16, address=resp_addr, value=resp_qty, success=True)

        raise ProtocolResponseError(
            message=f"未知的写入功能码: {function_code:#04x}",
            function_code=int(function_code),
        )

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _unpack_registers(data: bytes) -> list[int]:
        """将寄存器字节数据解包为UINT16值列表"""
        if len(data) % 2 != 0:
            raise ProtocolResponseError(
                message=f"寄存器数据长度不是偶数: {len(data)}",
                function_code=0,
            )
        return list(struct.unpack(f">{len(data) // 2}H", data))

    @staticmethod
    def _unpack_bits(data: bytes, max_bits: int) -> list[bool]:
        """将位数据解包为bool列表 (LSB first)"""
        values: list[bool] = []
        for byte_val in data:
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

    def __repr__(self) -> str:
        return (
            f"ModbusASCIIProtocol(port='{self._port}', "
            f"baudrate={self._baudrate}, "
            f"slave={self._slave_address}, "
            f"status={self._status.value})"
        )
