"""
ModbusRTU协议实现

实现Modbus RTU ADU (Application Data Unit) 封装:
    - RTU帧格式: [地址:1B][功能码:1B][数据:NB][CRC-16:2B]
    - CRC-16校验 (Modbus多项式: 0xA001)
    - 串口通信 (pyserial)
    - 串口参数配置 (波特率/数据位/停止位/校验位)
    - 串口设备枚举

支持功能码:
    读: FC01, FC02, FC03, FC04
    写: FC05, FC06, FC15, FC16

线程模型: 本类所有I/O操作应在QThread中调用，通过信号返回结果到UI线程。
"""

from __future__ import annotations

import struct
import time
from enum import IntEnum
from typing import Any, Optional, Union

from src.protocols.base_protocol import BaseProtocol, ReadResult, WriteResult, _CombinedMeta
from src.protocols.enums import DataType, DeviceStatus, FunctionCode, ProtocolType
from src.utils.exceptions import ProtocolConnectionError, ProtocolError, ProtocolResponseError, ProtocolTimeoutError
from src.utils.logger import get_logger

logger = get_logger("modbus_rtu")

# Modbus CRC-16 多项式 (反转)
_CRC16_POLY = 0xA001
_CRC16_INIT = 0xFFFF

# RTU帧间最小间隔 (1.5个字符时间, 19200bps以下按波特率计算, 以上固定1.75ms)
_RTU_SILENCE_19200 = 0.00175  # 秒


class BaudRate(IntEnum):
    """标准波特率"""

    B_1200 = 1200
    B_2400 = 2400
    B_4800 = 4800
    B_9600 = 9600
    B_19200 = 19200
    B_38400 = 38400
    B_57600 = 57600
    B_115200 = 115200


class DataBits(IntEnum):
    """数据位"""

    BITS_7 = 7
    BITS_8 = 8


class StopBits(float):
    """停止位 (使用float以支持1.5)"""

    ONE = 1.0
    ONE_HALF = 1.5
    TWO = 2.0


class Parity:
    """校验位"""

    NONE = "N"
    EVEN = "E"
    ODD = "O"
    MARK = "M"
    SPACE = "S"


class ModbusRTUProtocol(BaseProtocol, metaclass=_CombinedMeta):
    """ModbusRTU协议实现

    基于pyserial的Modbus RTU客户端。

    Usage:
        proto = ModbusRTUProtocol(port="COM3", baudrate=9600)
        proto.connect_to_device()
        result = proto.read_holding_registers(0, 10)
        proto.disconnect_from_device()

    Attributes:
        port: 串口号 (如 "COM3", "/dev/ttyUSB0")
        baudrate: 波特率 (默认9600)
        data_bits: 数据位 (默认8)
        stop_bits: 停止位 (默认1.0)
        parity: 校验位 (默认"E" 偶校验, RTU推荐)
    """

    def __init__(
        self,
        port: str = "COM1",
        baudrate: int = 9600,
        data_bits: int = 8,
        stop_bits: float = 1.0,
        parity: str = "E",
        timeout: float = 1.0,
        slave_address: int = 1,
        parent: Optional[object] = None,
    ) -> None:
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
        self._frame_gap: float = self._calculate_frame_gap(baudrate)

    # ═══════════════════════════════════════════════════════════
    # 公共属性
    # ═══════════════════════════════════════════════════════════

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.MODBUS_RTU

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

    @staticmethod
    def _calculate_frame_gap(baudrate: int) -> float:
        """计算帧间最小间隔 (3.5个字符时间)

        Modbus RTU规范要求帧间至少保持3.5个字符时间的沉默。
        波特率 <= 19200时: gap = 3.5 * (1 + 8 + 1) / baudrate (11 bits/char)
        波特率 > 19200时: gap = 1.75ms (固定值)

        Args:
            baudrate: 波特率

        Returns:
            帧间间隔秒数
        """
        if baudrate <= 19200:
            # 每字符约11位 (1起始 + 8数据 + 1停止 + 1校验)
            bits_per_char = 11
            return 3.5 * bits_per_char / baudrate
        return _RTU_SILENCE_19200 * 2  # 3.5ms

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
            import serial.tools.list_ports

            ser = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._data_bits,
                stopbits=self._stop_bits,
                parity=self._parity,
                timeout=self._timeout,
                write_timeout=self._timeout,
            )
            # 清空输入输出缓冲区
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            self._serial = ser

            logger.info(f"串口已打开: {self.connection_info} " f"(超时={self._timeout}s)")

        except ImportError:
            raise ProtocolConnectionError(
                message="pyserial库未安装，请执行: pip install pyserial",
                details={"required": "pyserial"},
            )
        except serial.SerialException as e:
            raise ProtocolConnectionError(
                message=f"串口打开失败: {self._port} - {e}",
                details={
                    "port": self._port,
                    "error": str(e),
                },
            )
        except ValueError as e:
            raise ProtocolConnectionError(
                message=f"串口参数错误: {e}",
                details={
                    "port": self._port,
                    "baudrate": self._baudrate,
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
                logger.info(f"串口已关闭: {self.connection_info}")

    # ═══════════════════════════════════════════════════════════
    # CRC-16 校验
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def calculate_crc(data: bytes) -> int:
        """计算Modbus CRC-16校验码

        使用多项式 0xA001 (反转的 0x8005)，初始值 0xFFFF。

        Args:
            data: 待校验的数据

        Returns:
            16位CRC校验码 (低字节在前，高字节在后)
        """
        crc = _CRC16_INIT
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ _CRC16_POLY
                else:
                    crc >>= 1
        return crc

    @staticmethod
    def verify_crc(data: bytes) -> bool:
        """验证CRC-16校验码

        将整个帧 (含CRC) 作为输入计算CRC，结果应为0。

        Args:
            data: 包含CRC的完整帧数据

        Returns:
            校验是否通过
        """
        if len(data) < 3:
            return False
        crc = ModbusRTUProtocol.calculate_crc(data)
        return crc == 0

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
        """构建ModbusRTU请求帧

        RTU帧格式: [地址:1B][功能码:1B][数据:NB][CRC-16:2B]

        Args:
            function_code: Modbus功能码
            start_address: 起始地址
            quantity: 读取数量 (读操作)
            value: 写入值 (写操作)

        Returns:
            完整的RTU帧 (含CRC)
        """
        # 构建PDU数据部分
        pdu_data = self._build_rtu_data(function_code, start_address, quantity, value)

        # 构建帧: 地址 + PDU
        frame = bytearray()
        frame.append(self._slave_address)
        frame.extend(pdu_data)

        # 追加CRC-16 (低字节在前)
        crc = self.calculate_crc(bytes(frame))
        frame.append(crc & 0xFF)  # CRC低字节
        frame.append((crc >> 8) & 0xFF)  # CRC高字节

        result = bytes(frame)
        logger.debug(
            f"构建RTU帧: Slave={self._slave_address} "
            f"FC={function_code:#04x} "
            f"帧长={len(result)}B "
            f"HX={result.hex()}"
        )
        return result

    def _build_rtu_data(
        self,
        function_code: FunctionCode,
        start_address: int,
        quantity: Optional[int] = None,
        value: Any = None,
    ) -> bytes:
        """构建RTU帧的PDU数据部分 (不含地址和CRC)

        格式与TCP的PDU完全一致: [FC:1B][Data:NB]
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
        """发送RTU帧并接收响应

        流程:
            1. 清空输入缓冲区
            2. 发送请求帧
            3. 等待帧间间隔
            4. 读取响应帧 (先读地址+功能码判断长度, 再读剩余)
            5. CRC校验

        Args:
            request_frame: 完整的RTU请求帧 (含CRC)

        Returns:
            响应帧数据 (不含CRC)

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
            # 清空输入缓冲区 (丢弃残留数据)
            self._serial.reset_input_buffer()

            # 发送请求
            self._serial.write(request_frame)
            self._serial.flush()

            logger.debug(f"已发送 {len(request_frame)} 字节 " f"HX={request_frame.hex()}")

            # 帧间间隔等待
            time.sleep(self._frame_gap)

            # 读取响应帧
            response_frame = self._read_response_frame()

            # CRC校验
            if not self.verify_crc(response_frame):
                raise ProtocolResponseError(
                    message=(
                        f"CRC校验失败: "
                        f"帧={response_frame.hex()} "
                        f"期望CRC尾字节=0x0000, "
                        f"实际={self.calculate_crc(response_frame):#06x}"
                    ),
                    function_code=0,
                    details={
                        "frame_hex": response_frame.hex(),
                    },
                )

            # 返回PDU (去掉地址字节和CRC尾2字节)
            pdu = response_frame[1:-2]
            return pdu

        except ProtocolResponseError:
            raise
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise ProtocolTimeoutError(
                    message=f"串口接收超时 ({self._timeout}s): {self._port}",
                    timeout_seconds=self._timeout,
                    details={"port": self._port, "timeout": self._timeout},
                )
            if isinstance(e, ProtocolError):
                raise
            raise ProtocolConnectionError(
                message=f"串口通信错误: {e}",
                details={"port": self._port, "error": str(e)},
            )

    def _read_response_frame(self) -> bytes:
        """读取完整的RTU响应帧

        智能读取策略:
            1. 先读2字节 (地址 + 功能码)
            2. 根据功能码判断响应长度
            3. 继续读取剩余数据 + CRC(2B)

        Returns:
            完整响应帧 (含CRC)
        """
        # 读取地址 + 功能码 (2字节)
        header = self._serial.read(2)
        if len(header) < 2:
            raise ProtocolTimeoutError(
                message="等待响应帧头超时",
                timeout_seconds=self._timeout,
                details={"port": self._port},
            )

        slave_id = header[0]
        resp_fc = header[1]

        # 检查是否为异常响应 (FC | 0x80)
        if resp_fc & 0x80:
            # 异常响应: [地址][FC|0x80][异常码][CRC]
            # 再读 1字节(异常码) + 2字节(CRC) = 3字节
            tail = self._serial.read(3)
            if len(tail) < 3:
                raise ProtocolTimeoutError(
                    message="异常响应帧不完整",
                    timeout_seconds=self._timeout,
                    details={"port": self._port},
                )
            return header + tail

        # 正常响应 - 根据功能码确定数据长度
        remaining = self._calculate_remaining_bytes(resp_fc)
        if remaining > 0:
            tail = self._serial.read(remaining)
            if len(tail) < remaining:
                raise ProtocolTimeoutError(
                    message=(f"响应帧不完整: 期望{remaining + 2}字节, " f"已接收{2 + len(tail)}字节"),
                    timeout_seconds=self._timeout,
                    details={
                        "expected": remaining + 2,
                        "received": 2 + len(tail),
                    },
                )
            return header + tail

        # 如果remaining计算为0但有更多数据, 使用超时机制读取
        time.sleep(self._frame_gap)
        extra = self._serial.read_all()
        return header + extra if extra else header

    def _calculate_remaining_bytes(self, function_code: int) -> int:
        """根据功能码计算响应帧剩余字节数 (不含已读的地址+FC)

        响应格式:
            FC01/02: [地址][FC][字节数][数据...][CRC] → 字节数 + 数据 + CRC
            FC03/04: [地址][FC][字节数][数据...][CRC] → 字节数 + 数据 + CRC
            FC05/06: [地址][FC][地址:2B][值:2B][CRC] → 4 + CRC = 6
            FC15/16: [地址][FC][起始地址:2B][数量:2B][CRC] → 4 + CRC = 6

        Returns:
            剩余需要读取的字节数
        """
        fc = function_code & 0x7F  # 去掉异常标志位

        # 写操作回显: 固定 4字节数据 + 2字节CRC = 6字节
        if fc in (0x05, 0x06, 0x0F, 0x10):
            return 6

        # 读操作: 需要先读1字节(字节数)再读对应数据 + CRC
        # 先只返回需要读取的最小字节数 (后续再处理)
        return 256  # 最大可能的响应 (保守读取，实际会根据byte_count调整)

    # ═══════════════════════════════════════════════════════════
    # 响应解析
    # ═══════════════════════════════════════════════════════════

    def _parse_response_frame(
        self,
        function_code: FunctionCode,
        response_data: bytes,
        start_address: int,
    ) -> ReadResult:
        """解析ModbusRTU读取响应

        response_data 格式 (不含地址和CRC):
            正常: [FC:1B][ByteCount:1B][Data:NB]
            异常: [FC|0x80:1B][ExceptionCode:1B]

        Args:
            function_code: 请求的功能码
            response_data: PDU数据 (不含地址和CRC)
            start_address: 起始地址

        Returns:
            ReadResult
        """
        if len(response_data) < 2:
            raise ProtocolResponseError(
                message=f"RTU响应PDU过短: {len(response_data)}字节",
                function_code=int(function_code),
                details={"length": len(response_data)},
            )

        resp_fc = response_data[0]

        # 异常响应检测
        if resp_fc & 0x80:
            exception_code = response_data[1] if len(response_data) > 1 else 0
            exception_info = self._get_exception_description(exception_code)
            raise ProtocolResponseError(
                message=(
                    f"Modbus RTU异常: FC={function_code:#04x} " f"异常码={exception_code:#04x} ({exception_info})"
                ),
                function_code=int(function_code),
                exception_code=exception_code,
            )

        # 功能码匹配校验
        if resp_fc != int(function_code):
            raise ProtocolResponseError(
                message=(f"功能码不匹配: 期望={function_code:#04x}, " f"实际={resp_fc:#04x}"),
                function_code=int(function_code),
            )

        # 位操作响应: FC01, FC02
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

        # 寄存器操作响应: FC03, FC04
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
        """解析ModbusRTU写入响应

        response_data 格式 (不含地址和CRC):
            FC05/06: [FC:1B][Address:2B][Value:2B]
            FC15/16: [FC:1B][StartAddress:2B][Quantity:2B]
        """
        if len(response_data) < 2:
            raise ProtocolResponseError(
                message=f"RTU写入响应PDU过短: {len(response_data)}字节",
                function_code=int(function_code),
            )

        resp_fc = response_data[0]

        # 异常响应
        if resp_fc & 0x80:
            exception_code = response_data[1] if len(response_data) > 1 else 0
            exception_info = self._get_exception_description(exception_code)
            raise ProtocolResponseError(
                message=(f"RTU写入异常: FC={function_code:#04x} " f"异常码={exception_code:#04x} ({exception_info})"),
                function_code=int(function_code),
                exception_code=exception_code,
            )

        fc = function_code

        # FC05: 写单个线圈
        if fc == FunctionCode.WRITE_SINGLE_COIL:
            if len(response_data) < 5:
                raise ProtocolResponseError(
                    message="FC05响应PDU长度不足",
                    function_code=5,
                )
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_val = struct.unpack(">H", response_data[3:5])[0]
            return WriteResult(
                function_code=5,
                address=resp_addr,
                value=bool(resp_val == 0xFF00),
                success=True,
            )

        # FC06: 写单个寄存器
        if fc == FunctionCode.WRITE_SINGLE_REGISTER:
            if len(response_data) < 5:
                raise ProtocolResponseError(
                    message="FC06响应PDU长度不足",
                    function_code=6,
                )
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_val = struct.unpack(">H", response_data[3:5])[0]
            return WriteResult(
                function_code=6,
                address=resp_addr,
                value=resp_val,
                success=True,
            )

        # FC15: 写多个线圈
        if fc == FunctionCode.WRITE_MULTIPLE_COILS:
            if len(response_data) < 5:
                raise ProtocolResponseError(
                    message="FC15响应PDU长度不足",
                    function_code=15,
                )
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_qty = struct.unpack(">H", response_data[3:5])[0]
            return WriteResult(
                function_code=15,
                address=resp_addr,
                value=resp_qty,
                success=True,
            )

        # FC16: 写多个寄存器
        if fc == FunctionCode.WRITE_MULTIPLE_REGISTERS:
            if len(response_data) < 5:
                raise ProtocolResponseError(
                    message="FC16响应PDU长度不足",
                    function_code=16,
                )
            resp_addr = struct.unpack(">H", response_data[1:3])[0]
            resp_qty = struct.unpack(">H", response_data[3:5])[0]
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

    @staticmethod
    def enumerate_serial_ports() -> list[dict[str, str]]:
        """枚举系统可用的串口设备

        Returns:
            串口设备列表, 每项包含: device, description, hwid
        """
        try:
            import serial.tools.list_ports

            ports = serial.tools.list_ports.comports()
            return [
                {
                    "device": p.device,
                    "description": p.description,
                    "hwid": p.hwid,
                }
                for p in sorted(ports, key=lambda x: x.device)
            ]
        except ImportError:
            logger.warning("pyserial未安装, 无法枚举串口")
            return []
        except Exception as e:
            logger.error(f"枚举串口失败: {e}")
            return []

    def __repr__(self) -> str:
        return (
            f"ModbusRTUProtocol(port='{self._port}', "
            f"baudrate={self._baudrate}, "
            f"slave={self._slave_address}, "
            f"status={self._status.value})"
        )
