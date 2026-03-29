"""
自定义异常层次 - 工业设备管理系统

设计原则:
    1. 所有业务异常继承自 EquipmentManagementError 基类
    2. 按架构层级划分异常子类: 协议层 / 通信层 / 设备层 / 数据层 / 报警层 / UI层
    3. 每个异常必须携带上下文信息 (device_id, register_address 等)
    4. 异常必须在 catch 后记录日志，严禁静默吞掉异常
    5. UI层禁止直接 try/except 基础异常，必须通过信号槽获取错误信息

使用示例:
    try:
        protocol.connect()
    except ProtocolConnectionError as e:
        logger.error(f"设备 {e.device_id} 连接失败: {e}")
        # 通过信号通知UI层
        self.error_occurred.emit(str(e))
"""

from __future__ import annotations

from typing import Any, Optional

# ═══════════════════════════════════════════════════════════════
# 基类
# ═══════════════════════════════════════════════════════════════


class EquipmentManagementError(Exception):
    """工业设备管理系统异常基类

    所有自定义异常的根。携带结构化上下文，支持链式异常 (__cause__)。

    Attributes:
        message: 人类可读的错误描述
        error_code: 机器可读的错误码 (如 "PROTOCOL_TIMEOUT")
        details: 额外的结构化上下文信息
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"[{self.error_code}] {self.message} ({detail_str})"
        return f"[{self.error_code}] {self.message}"


# ═══════════════════════════════════════════════════════════════
# 第一层: 协议层异常
# ═══════════════════════════════════════════════════════════════


class ProtocolError(EquipmentManagementError):
    """协议层异常基类"""

    pass


class ProtocolConnectionError(ProtocolError):
    """协议连接失败

    Attributes:
        device_id: 目标设备ID
        host: 目标地址 (IP或串口)
    """

    def __init__(
        self,
        message: str = "协议连接失败",
        device_id: Optional[str] = None,
        host: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"device_id": device_id, "host": host}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="PROTOCOL_CONNECTION_ERROR",
            details=details,
        )


class ProtocolTimeoutError(ProtocolError):
    """协议通信超时"""

    def __init__(
        self,
        message: str = "通信超时",
        timeout_seconds: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"timeout": timeout_seconds}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="PROTOCOL_TIMEOUT",
            details=details,
        )


class ProtocolResponseError(ProtocolError):
    """协议响应解析错误（功能码异常/数据校验失败）"""

    def __init__(
        self,
        message: str = "协议响应错误",
        function_code: Optional[int] = None,
        exception_code: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {
            "function_code": function_code,
            "exception_code": exception_code,
        }
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="PROTOCOL_RESPONSE_ERROR",
            details=details,
        )


class ProtocolCRCError(ProtocolError):
    """CRC/LRC校验失败"""

    def __init__(
        self,
        message: str = "数据校验失败",
        expected: Optional[int] = None,
        actual: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"expected": expected, "actual": actual}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="PROTOCOL_CRC_ERROR",
            details=details,
        )


# ═══════════════════════════════════════════════════════════════
# 第二层: 通信驱动层异常
# ═══════════════════════════════════════════════════════════════


class DriverError(EquipmentManagementError):
    """通信驱动层异常基类"""

    pass


class DriverOpenError(DriverError):
    """驱动打开失败（端口占用/权限不足/设备不存在）"""

    def __init__(
        self,
        message: str = "驱动打开失败",
        port: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"port": port}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DRIVER_OPEN_ERROR",
            details=details,
        )


class DriverWriteError(DriverError):
    """数据写入失败"""

    def __init__(
        self,
        message: str = "数据写入失败",
        bytes_written: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"bytes_written": bytes_written}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DRIVER_WRITE_ERROR",
            details=details,
        )


class DriverReadError(DriverError):
    """数据读取失败"""

    def __init__(
        self,
        message: str = "数据读取失败",
        bytes_expected: Optional[int] = None,
        bytes_received: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {
            "expected": bytes_expected,
            "received": bytes_received,
        }
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DRIVER_READ_ERROR",
            details=details,
        )


# ═══════════════════════════════════════════════════════════════
# 第三层: 设备管理层异常
# ═══════════════════════════════════════════════════════════════


class DeviceError(EquipmentManagementError):
    """设备管理层异常基类"""

    pass


class DeviceNotFoundError(DeviceError):
    """设备不存在"""

    def __init__(
        self,
        message: str = "设备不存在",
        device_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"device_id": device_id}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DEVICE_NOT_FOUND",
            details=details,
        )


class DeviceDuplicateError(DeviceError):
    """设备ID重复"""

    def __init__(
        self,
        message: str = "设备ID已存在",
        device_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"device_id": device_id}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DEVICE_DUPLICATE",
            details=details,
        )


class DeviceConfigError(DeviceError):
    """设备配置错误"""

    def __init__(
        self,
        message: str = "设备配置错误",
        field: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"field": field}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DEVICE_CONFIG_ERROR",
            details=details,
        )


class RegisterError(DeviceError):
    """寄存器相关异常"""

    def __init__(
        self,
        message: str = "寄存器错误",
        address: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"address": address}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="REGISTER_ERROR",
            details=details,
        )


# ═══════════════════════════════════════════════════════════════
# 数据持久化层异常
# ═══════════════════════════════════════════════════════════════


class DataError(EquipmentManagementError):
    """数据持久化层异常基类"""

    pass


class DatabaseError(DataError):
    """数据库操作异常"""

    def __init__(
        self,
        message: str = "数据库操作失败",
        table: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"table": table, "operation": operation}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
        )


class DatabaseConnectionError(DataError):
    """数据库连接失败"""

    def __init__(
        self,
        message: str = "数据库连接失败",
        db_path: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"db_path": db_path}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="DATABASE_CONNECTION_ERROR",
            details=details,
        )


# ═══════════════════════════════════════════════════════════════
# 报警系统异常
# ═══════════════════════════════════════════════════════════════


class AlarmError(EquipmentManagementError):
    """报警系统异常基类"""

    pass


class AlarmRuleError(AlarmError):
    """报警规则配置错误"""

    def __init__(
        self,
        message: str = "报警规则配置错误",
        rule_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"rule_id": rule_id}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="ALARM_RULE_ERROR",
            details=details,
        )


# ═══════════════════════════════════════════════════════════════
# UI层异常
# ═══════════════════════════════════════════════════════════════


class UIError(EquipmentManagementError):
    """UI层异常基类"""

    pass


class ValidationError(UIError):
    """用户输入校验失败"""

    def __init__(
        self,
        message: str = "输入验证失败",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"field": field, "value": str(value)}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ExportError(UIError):
    """数据导出失败"""

    def __init__(
        self,
        message: str = "数据导出失败",
        format_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details: dict[str, Any] = {"format": format_type}
        details.update(kwargs)
        super().__init__(
            message=message,
            error_code="EXPORT_ERROR",
            details=details,
        )
