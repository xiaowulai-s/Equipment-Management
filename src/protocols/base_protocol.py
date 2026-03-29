"""
Modbus协议抽象基类

设计原则:
    1. 继承QObject，全面支持Qt信号槽
    2. 定义协议通用接口: connect / disconnect / read / write
    3. 使用模板方法模式: 子类实现具体帧构建/解析
    4. 内置事务ID管理 (TCP用)
    5. 所有I/O方法由子类在QThread中实现, 通过信号返回结果
    6. 超时机制统一管理

信号体系:
    connected()           → 连接成功
    disconnected()        → 连接断开
    data_received(dict)   → 数据接收 (含function_code, address, values)
    error_occurred(str)   → 错误通知 (人类可读)
    status_changed(DeviceStatus) → 状态变更
"""

from __future__ import annotations

import struct
import threading

# 解决 QObject 与 ABC 的元类冲突:
# PySide6 的 QObject 使用 Shiboken.ObjectType 元类,
# ABC 使用 abc.ABCMeta。需要创建一个兼容的联合元类。
from abc import ABCMeta as _ABCMeta
from abc import abstractmethod
from typing import Any, Optional, Union

from PySide6.QtCore import QObject, Signal

_qobject_meta = type(QObject)

if issubclass(_qobject_meta, _ABCMeta):
    # PySide6 的元类已继承 ABCMeta (新版本)
    _CombinedMeta = _qobject_meta
else:

    class _CombinedMeta(_ABCMeta, _qobject_meta):  # type: ignore[misc, misc]
        """联合元类: 同时支持 ABC 抽象方法和 QObject 信号"""

        pass


from src.protocols.enums import DataType, DeviceStatus, Endian, FunctionCode, ProtocolType, RegisterType
from src.utils.exceptions import (
    ProtocolConnectionError,
    ProtocolCRCError,
    ProtocolError,
    ProtocolResponseError,
    ProtocolTimeoutError,
)
from src.utils.logger import get_logger

logger = get_logger("protocol")


# ═══════════════════════════════════════════════════════════════
# 读取结果容器
# ═══════════════════════════════════════════════════════════════


class ReadResult:
    """协议读取结果

    Attributes:
        function_code: Modbus功能码
        start_address: 起始地址
        values: 解析后的值列表
        raw_data: 原始字节数据
        success: 是否成功
        error_message: 失败时的错误信息
    """

    __slots__ = (
        "function_code",
        "start_address",
        "values",
        "raw_data",
        "success",
        "error_message",
    )

    def __init__(
        self,
        function_code: int,
        start_address: int,
        values: Optional[list[Union[int, float, bool]]] = None,
        raw_data: Optional[bytes] = None,
        success: bool = True,
        error_message: str = "",
    ) -> None:
        self.function_code = function_code
        self.start_address = start_address
        self.values = values or []
        self.raw_data = raw_data or b""
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于信号传递)"""
        return {
            "function_code": self.function_code,
            "start_address": self.start_address,
            "values": self.values,
            "raw_data": self.raw_data.hex() if self.raw_data else "",
            "success": self.success,
            "error_message": self.error_message,
        }

    @classmethod
    def error(cls, message: str, function_code: int = 0, address: int = 0) -> "ReadResult":
        """创建一个错误结果"""
        return cls(
            function_code=function_code,
            start_address=address,
            success=False,
            error_message=message,
        )


# ═══════════════════════════════════════════════════════════════
# 写入结果容器
# ═══════════════════════════════════════════════════════════════


class WriteResult:
    """协议写入结果

    Attributes:
        function_code: Modbus功能码
        address: 写入地址
        value: 写入值
        success: 是否成功
        error_message: 失败时的错误信息
    """

    __slots__ = ("function_code", "address", "value", "success", "error_message")

    def __init__(
        self,
        function_code: int,
        address: int,
        value: Union[int, float, bool, list] = 0,
        success: bool = True,
        error_message: str = "",
    ) -> None:
        self.function_code = function_code
        self.address = address
        self.value = value
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        return {
            "function_code": self.function_code,
            "address": self.address,
            "value": self.value,
            "success": self.success,
            "error_message": self.error_message,
        }


# ═══════════════════════════════════════════════════════════════
# 协议抽象基类
# ═══════════════════════════════════════════════════════════════


class BaseProtocol(QObject, metaclass=_CombinedMeta):
    """Modbus协议抽象基类

    所有协议实现 (TCP/RTU/ASCII) 必须继承此类。

    子类必须实现:
        - _build_request_frame(): 构建协议请求帧
        - _parse_response_frame(): 解析协议响应帧
        - _do_connect(): 执行连接
        - _do_disconnect(): 执行断开

    生命周期:
        connect() → _do_connect() → connected信号
        read_registers() → _send_request() → _parse_response_frame() → data_received信号
        disconnect() → _do_disconnect() → disconnected信号
    """

    # ── Qt信号 ──
    connected = Signal()  # 连接成功
    disconnected = Signal()  # 连接断开
    data_received = Signal(dict)  # 数据接收 (ReadResult.to_dict())
    write_completed = Signal(dict)  # 写入完成 (WriteResult.to_dict())
    error_occurred = Signal(str)  # 错误通知
    status_changed = Signal(object)  # 状态变更 (DeviceStatus)

    def __init__(
        self,
        timeout: float = 3.0,
        slave_address: int = 1,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._timeout = timeout
        self._slave_address = slave_address
        self._status = DeviceStatus.DISCONNECTED
        self._transaction_lock = threading.Lock()

        # TCP事务ID (RTU/ASCII不用)
        self._transaction_id = 0

    # ═══════════════════════════════════════════════════════════
    # 公共属性
    # ═══════════════════════════════════════════════════════════

    @property
    @abstractmethod
    def protocol_type(self) -> ProtocolType:
        """协议类型 (子类必须实现)"""
        ...

    @property
    def status(self) -> DeviceStatus:
        """当前连接状态"""
        return self._status

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._status.is_connected

    @property
    def timeout(self) -> float:
        """超时时间(秒)"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        self._timeout = max(0.1, min(value, 60.0))

    @property
    def slave_address(self) -> int:
        """从站地址"""
        return self._slave_address

    @slave_address.setter
    def slave_address(self, value: int) -> None:
        if not 1 <= value <= 247:
            raise ValueError(f"从站地址必须在 1-247 范围内，当前值: {value}")
        self._slave_address = value

    # ═══════════════════════════════════════════════════════════
    # 连接管理 (模板方法)
    # ═══════════════════════════════════════════════════════════

    def set_status(self, new_status: DeviceStatus) -> None:
        """设置状态并发射信号"""
        if self._status != new_status:
            old = self._status
            self._status = new_status
            logger.info(f"状态变更: {old.display_text} → {new_status.display_text}")
            self.status_changed.emit(new_status)

    def connect_to_device(self) -> None:
        """连接设备 (模板方法)

        流程: 设置状态→执行连接→发射信号
        子类通过 _do_connect() 实现具体连接逻辑。
        """
        if self.is_connected:
            logger.warning("设备已连接，跳过重复连接")
            return

        self.set_status(DeviceStatus.CONNECTING)
        try:
            self._do_connect()
            self.set_status(DeviceStatus.CONNECTED)
            self.connected.emit()
            logger.info(f"[{self.protocol_type.value}] 连接成功")
        except ProtocolError as e:
            self.set_status(DeviceStatus.ERROR)
            self.error_occurred.emit(str(e))
            logger.error(f"[{self.protocol_type.value}] 连接失败: {e}")
            raise
        except Exception as e:
            self.set_status(DeviceStatus.ERROR)
            error = ProtocolConnectionError(
                message=f"未知连接错误: {e}",
                details={"raw_error": str(e)},
            )
            self.error_occurred.emit(str(error))
            logger.error(f"[{self.protocol_type.value}] 未知错误: {error}")
            raise error from e

    def disconnect_from_device(self) -> None:
        """断开连接"""
        if not self.is_connected and self._status != DeviceStatus.ERROR:
            return

        try:
            self._do_disconnect()
            self.set_status(DeviceStatus.DISCONNECTED)
            self.disconnected.emit()
            logger.info(f"[{self.protocol_type.value}] 已断开连接")
        except Exception as e:
            logger.warning(f"[{self.protocol_type.value}] 断开时异常: {e}")
            self.set_status(DeviceStatus.DISCONNECTED)

    # ═══════════════════════════════════════════════════════════
    # 读取操作
    # ═══════════════════════════════════════════════════════════

    def read_coils(
        self,
        start_address: int,
        quantity: int,
    ) -> ReadResult:
        """读线圈 (FC01)

        Args:
            start_address: 起始地址 (0x0000-0xFFFF)
            quantity: 读取数量 (1-2000)
        """
        self._validate_address_range(start_address, quantity, 2000)
        return self._execute_read(
            FunctionCode.READ_COILS,
            start_address,
            quantity,
        )

    def read_discrete_inputs(
        self,
        start_address: int,
        quantity: int,
    ) -> ReadResult:
        """读离散输入 (FC02)"""
        self._validate_address_range(start_address, quantity, 2000)
        return self._execute_read(
            FunctionCode.READ_DISCRETE_INPUTS,
            start_address,
            quantity,
        )

    def read_holding_registers(
        self,
        start_address: int,
        quantity: int,
        data_type: DataType = DataType.UINT16,
        endian: Endian = Endian.BIG,
    ) -> ReadResult:
        """读保持寄存器 (FC03)

        Args:
            start_address: 起始地址
            quantity: 读取的寄存器数量
            data_type: 数据类型 (用于解析)
            endian: 字节序
        """
        self._validate_address_range(start_address, quantity, 125)
        result = self._execute_read(
            FunctionCode.READ_HOLDING_REGISTERS,
            start_address,
            quantity,
        )
        if result.success and data_type != DataType.UINT16:
            result.values = self._decode_registers(result.raw_data, quantity, data_type, endian)
        return result

    def read_input_registers(
        self,
        start_address: int,
        quantity: int,
        data_type: DataType = DataType.UINT16,
        endian: Endian = Endian.BIG,
    ) -> ReadResult:
        """读输入寄存器 (FC04)"""
        self._validate_address_range(start_address, quantity, 125)
        result = self._execute_read(
            FunctionCode.READ_INPUT_REGISTERS,
            start_address,
            quantity,
        )
        if result.success and data_type != DataType.UINT16:
            result.values = self._decode_registers(result.raw_data, quantity, data_type, endian)
        return result

    # ═══════════════════════════════════════════════════════════
    # 写入操作
    # ═══════════════════════════════════════════════════════════

    def write_single_coil(
        self,
        address: int,
        value: bool,
    ) -> WriteResult:
        """写单个线圈 (FC05)

        Args:
            address: 线圈地址
            value: True=ON(0xFF00), False=OFF(0x0000)
        """
        self._validate_address(address)
        coil_value = 0xFF00 if value else 0x0000
        return self._execute_write(FunctionCode.WRITE_SINGLE_COIL, address, coil_value)

    def write_single_register(
        self,
        address: int,
        value: int,
    ) -> WriteResult:
        """写单个寄存器 (FC06)"""
        self._validate_address(address)
        value = int(value) & 0xFFFF
        return self._execute_write(FunctionCode.WRITE_SINGLE_REGISTER, address, value)

    def write_multiple_coils(
        self,
        start_address: int,
        values: list[bool],
    ) -> WriteResult:
        """写多个线圈 (FC15)"""
        quantity = len(values)
        self._validate_address_range(start_address, quantity, 1968)
        return self._execute_write(FunctionCode.WRITE_MULTIPLE_COILS, start_address, values)

    def write_multiple_registers(
        self,
        start_address: int,
        values: list[Union[int, float]],
        data_type: DataType = DataType.UINT16,
        endian: Endian = Endian.BIG,
    ) -> WriteResult:
        """写多个寄存器 (FC16)"""
        quantity = len(values)
        self._validate_address_range(start_address, quantity, 123)
        raw_bytes = self._encode_registers(values, data_type, endian)
        return self._execute_write(
            FunctionCode.WRITE_MULTIPLE_REGISTERS,
            start_address,
            raw_bytes,
        )

    # ═══════════════════════════════════════════════════════════
    # 数据编解码工具
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _decode_registers(
        raw_data: bytes,
        quantity: int,
        data_type: DataType,
        endian: Endian = Endian.BIG,
    ) -> list[Union[int, float, bool]]:
        """将原始字节数据解码为指定类型的值列表

        Args:
            raw_data: 原始字节数据
            quantity: 寄存器数量
            data_type: 目标数据类型
            endian: 字节序

        Returns:
            解码后的值列表
        """
        if not raw_data:
            return []

        # 单寄存器类型
        if data_type in (DataType.UINT16, DataType.INT16, DataType.BOOL):
            fmt_char = data_type.format_char
            byte_order = ">" if endian in (Endian.BIG, Endian.BIG_SWAP) else "<"
            values = []
            for i in range(0, len(raw_data), 2):
                chunk = raw_data[i : i + 2]
                if len(chunk) < 2:
                    break
                val = struct.unpack(f"{byte_order}{fmt_char}", chunk)[0]
                if data_type == DataType.BOOL:
                    values.append(bool(val))
                else:
                    values.append(val)
            return values

        # 多寄存器类型 (INT32, UINT32, FLOAT32 等)
        if data_type.register_count > 0:
            reg_bytes = data_type.byte_size
            fmt_char = data_type.format_char
            byte_order = ">" if endian in (Endian.BIG, Endian.BIG_SWAP) else "<"
            values = []
            for i in range(0, len(raw_data), reg_bytes):
                chunk = raw_data[i : i + reg_bytes]
                if len(chunk) < reg_bytes:
                    break
                # 处理字交换 (BIG_SWAP / LITTLE_SWAP)
                if endian in (Endian.BIG_SWAP, Endian.LITTLE_SWAP):
                    swapped = bytearray(chunk)
                    for j in range(0, len(swapped) - 1, 2):
                        swapped[j], swapped[j + 1] = swapped[j + 1], swapped[j]
                    chunk = bytes(swapped)
                val = struct.unpack(f"{byte_order}{fmt_char}", chunk)[0]
                values.append(val)
            return values

        return list(struct.unpack(f">{len(raw_data) // 2}H", raw_data))

    @staticmethod
    def _encode_registers(
        values: list[Union[int, float]],
        data_type: DataType,
        endian: Endian = Endian.BIG,
    ) -> bytes:
        """将值列表编码为字节数据

        Args:
            values: 值列表
            data_type: 数据类型
            endian: 字节序

        Returns:
            编码后的字节数据
        """
        result = bytearray()
        byte_order = ">" if endian in (Endian.BIG, Endian.BIG_SWAP) else "<"
        fmt_char = data_type.format_char

        for val in values:
            if data_type.register_count > 0 and data_type.byte_size > 0:
                encoded = struct.pack(f"{byte_order}{fmt_char}", val)
                if endian in (Endian.BIG_SWAP, Endian.LITTLE_SWAP):
                    swapped = bytearray(encoded)
                    for j in range(0, len(swapped) - 1, 2):
                        swapped[j], swapped[j + 1] = swapped[j + 1], swapped[j]
                    encoded = bytes(swapped)
                result.extend(encoded)
            else:
                result.extend(struct.pack(">H", int(val) & 0xFFFF))

        return bytes(result)

    # ═══════════════════════════════════════════════════════════
    # 事务ID管理 (TCP用)
    # ═══════════════════════════════════════════════════════════

    def _next_transaction_id(self) -> int:
        """获取下一个事务ID (线程安全, 循环递增)"""
        with self._transaction_lock:
            self._transaction_id = (self._transaction_id % 65535) + 1
            return self._transaction_id

    # ═══════════════════════════════════════════════════════════
    # 参数校验
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _validate_address(address: int) -> None:
        """校验地址范围"""
        if not 0 <= address <= 0xFFFF:
            raise ProtocolError(
                message=f"地址超出范围: {address}",
                error_code="INVALID_ADDRESS",
                details={"address": address, "max": 0xFFFF},
            )

    @staticmethod
    def _validate_address_range(start: int, quantity: int, max_quantity: int) -> None:
        """校验地址范围和数量"""
        if not 0 <= start <= 0xFFFF:
            raise ProtocolError(
                message=f"起始地址超出范围: {start}",
                error_code="INVALID_ADDRESS",
                details={"address": start},
            )
        if quantity < 1 or quantity > max_quantity:
            raise ProtocolError(
                message=f"数量超出范围: {quantity} (最大{max_quantity})",
                error_code="INVALID_QUANTITY",
                details={"quantity": quantity, "max": max_quantity},
            )
        if start + quantity > 0x10000:
            raise ProtocolError(
                message=f"地址+数量溢出: {start}+{quantity} > 65536",
                error_code="ADDRESS_OVERFLOW",
                details={"start": start, "quantity": quantity},
            )

    # ═══════════════════════════════════════════════════════════
    # 内部读写执行 (模板方法核心)
    # ═══════════════════════════════════════════════════════════

    def _execute_read(
        self,
        function_code: FunctionCode,
        start_address: int,
        quantity: int,
    ) -> ReadResult:
        """执行读取操作 (模板方法)

        流程: 构建请求帧 → 发送 → 接收 → 解析 → 返回结果
        """
        if not self.is_connected:
            error = ReadResult.error(
                "设备未连接",
                function_code=function_code,
                address=start_address,
            )
            self.error_occurred.emit(error.error_message)
            return error

        try:
            request_frame = self._build_request_frame(
                function_code=function_code,
                start_address=start_address,
                quantity=quantity,
            )
            logger.debug(f"发送请求: FC={function_code:#04x} " f"Addr={start_address:#06x} Qty={quantity}")

            response_data = self._send_and_receive(request_frame)

            result = self._parse_response_frame(function_code, response_data, start_address)
            self.data_received.emit(result.to_dict())
            return result

        except ProtocolTimeoutError as e:
            result = ReadResult.error(str(e), function_code, start_address)
            self.error_occurred.emit(str(e))
            return result
        except ProtocolError as e:
            result = ReadResult.error(str(e), function_code, start_address)
            self.error_occurred.emit(str(e))
            return result
        except Exception as e:
            error_msg = f"读取异常: {e}"
            result = ReadResult.error(error_msg, function_code, start_address)
            self.error_occurred.emit(error_msg)
            logger.error(error_msg, exc_info=True)
            return result

    def _execute_write(
        self,
        function_code: FunctionCode,
        address: int,
        value: Any,
    ) -> WriteResult:
        """执行写入操作 (模板方法)"""
        if not self.is_connected:
            result = WriteResult(
                function_code=function_code,
                address=address,
                success=False,
                error_message="设备未连接",
            )
            self.error_occurred.emit(result.error_message)
            return result

        try:
            request_frame = self._build_request_frame(
                function_code=function_code,
                start_address=address,
                value=value,
            )
            logger.debug(f"发送写入: FC={function_code:#04x} Addr={address:#06x}")

            response_data = self._send_and_receive(request_frame)
            result = self._parse_write_response(function_code, response_data, address)
            if result.success:
                self.write_completed.emit(result.to_dict())
            else:
                self.error_occurred.emit(result.error_message)
            return result

        except ProtocolError as e:
            result = WriteResult(
                function_code=function_code,
                address=address,
                success=False,
                error_message=str(e),
            )
            self.error_occurred.emit(str(e))
            return result
        except Exception as e:
            error_msg = f"写入异常: {e}"
            result = WriteResult(
                function_code=function_code,
                address=address,
                success=False,
                error_message=error_msg,
            )
            self.error_occurred.emit(error_msg)
            logger.error(error_msg, exc_info=True)
            return result

    # ═══════════════════════════════════════════════════════════
    # 抽象方法 (子类必须实现)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def _do_connect(self) -> None:
        """执行连接 (子类实现)"""
        ...

    @abstractmethod
    def _do_disconnect(self) -> None:
        """执行断开 (子类实现)"""
        ...

    @abstractmethod
    def _build_request_frame(
        self,
        function_code: FunctionCode,
        start_address: int,
        quantity: Optional[int] = None,
        value: Any = None,
    ) -> bytes:
        """构建协议请求帧 (子类实现)"""
        ...

    @abstractmethod
    def _send_and_receive(self, request_frame: bytes) -> bytes:
        """发送请求帧并接收响应 (子类实现)"""
        ...

    @abstractmethod
    def _parse_response_frame(
        self,
        function_code: FunctionCode,
        response_data: bytes,
        start_address: int,
    ) -> ReadResult:
        """解析响应帧 (子类实现)"""
        ...

    @abstractmethod
    def _parse_write_response(
        self,
        function_code: FunctionCode,
        response_data: bytes,
        address: int,
    ) -> WriteResult:
        """解析写入响应帧 (子类实现)"""
        ...
