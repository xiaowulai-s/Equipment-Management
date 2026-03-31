"""
ORM 数据模型

定义7张数据表:
    1. devices           — 设备持久化 (与新Device模型双向转换)
    2. register_maps     — 寄存器映射 (与新Register模型双向转换)
    3. historical_data   — 历史数据点
    4. alarms            — 报警记录
    5. alarm_rules       — 报警规则
    6. system_logs       — 系统日志

设计要点:
    - DeviceModel/RegisterMapModel 与 src.device.device.Device/Register
      提供双向转换方法: from_domain() / to_domain()
    - 所有表使用 UTC 时间戳
    - 级联删除: 删除设备自动删除关联寄存器和历史数据
    - 索引优化: 按查询场景建立复合索引
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base, utc_now


def _now() -> datetime:
    """UTC时间戳 (简写)"""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════
# 设备模型
# ═══════════════════════════════════════════════════════════════


class DeviceModel(Base):
    """设备持久化模型

    对应 src.device.device.Device 的数据库表示。
    通过 from_domain()/to_domain() 与运行时模型双向转换。
    """

    __tablename__ = "devices"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    device_type = Column(String(64), nullable=False)
    device_number = Column(String(64), nullable=True)
    protocol_type = Column(String(32), nullable=False)
    host = Column(String(256), nullable=True)
    port = Column(Integer, nullable=True)
    slave_id = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    status = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    location = Column(String(256), nullable=True)
    group_name = Column(String(128), nullable=True)
    # 串口参数 (RTU/ASCII设备)
    serial_port = Column(String(64), nullable=True)
    baud_rate = Column(Integer, nullable=True)
    data_bits = Column(Integer, nullable=True)
    stop_bits = Column(Integer, nullable=True)
    parity = Column(String(8), nullable=True)
    # 轮询配置
    poll_interval_ms = Column(Integer, default=1000)
    poll_timeout_ms = Column(Integer, default=3000)
    poll_retry_count = Column(Integer, default=3)
    poll_retry_interval_ms = Column(Integer, default=500)
    # 连接统计
    last_connected_at = Column(DateTime, nullable=True)
    connection_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    # 时间戳
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    # 关系
    register_maps = relationship(
        "RegisterMapModel",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    historical_data = relationship(
        "HistoricalDataModel",
        back_populates="device",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_device_type", "device_type"),
        Index("idx_device_name", "name"),
        Index("idx_device_group", "group_name"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4().hex[:12])
        kwargs.setdefault("protocol_type", "modbus_tcp")
        kwargs.setdefault("slave_id", 1)
        kwargs.setdefault("enabled", True)
        kwargs.setdefault("status", 0)
        kwargs.setdefault("poll_interval_ms", 1000)
        kwargs.setdefault("poll_timeout_ms", 3000)
        kwargs.setdefault("poll_retry_count", 3)
        kwargs.setdefault("poll_retry_interval_ms", 500)
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "device_number": self.device_number,
            "protocol_type": self.protocol_type,
            "host": self.host,
            "port": self.port,
            "slave_id": self.slave_id,
            "enabled": self.enabled,
            "status": self.status,
            "description": self.description,
            "location": self.location,
            "group_name": self.group_name,
            "serial_port": self.serial_port,
            "baud_rate": self.baud_rate,
            "data_bits": self.data_bits,
            "stop_bits": self.stop_bits,
            "parity": self.parity,
            "poll_interval_ms": self.poll_interval_ms,
            "poll_timeout_ms": self.poll_timeout_ms,
            "poll_retry_count": self.poll_retry_count,
            "poll_retry_interval_ms": self.poll_retry_interval_ms,
            "last_connected_at": (self.last_connected_at.isoformat() if self.last_connected_at else None),
            "connection_count": self.connection_count,
            "error_count": self.error_count,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
        }

    @classmethod
    def from_domain(cls, device: Any) -> DeviceModel:
        """从运行时 Device 创建持久化模型

        Args:
            device: src.device.device.Device 实例
        """
        tp = device.tcp_params
        sp = device.serial_params
        pc = device.poll_config

        model = cls(
            id=device.id,
            name=device.name,
            device_type=getattr(device, "device_type", "modbus"),
            device_number=getattr(device, "device_number", None),
            protocol_type=device.protocol_type.value,
            host=tp.host if tp else None,
            port=tp.port if tp else None,
            slave_id=device.slave_id,
            enabled=device.enabled,
            status=device.device_status.value,
            description=getattr(device, "description", ""),
            location=getattr(device, "location", None),
            group_name=getattr(device, "group_name", None),
            serial_port=sp.port if sp else None,
            baud_rate=sp.baud_rate if sp else None,
            data_bits=sp.data_bits if sp else None,
            stop_bits=sp.stop_bits if sp else None,
            parity=sp.parity if sp else None,
            poll_interval_ms=pc.interval_ms if pc else 1000,
            poll_timeout_ms=pc.timeout_ms if pc else 3000,
            poll_retry_count=pc.retry_count if pc else 3,
            poll_retry_interval_ms=pc.retry_interval_ms if pc else 500,
        )

        # 转换寄存器
        for reg in device.registers.values():
            model.register_maps.append(RegisterMapModel.from_domain(reg))

        return model

    def to_domain(self) -> Any:
        """转换为运行时 Device 对象

        Returns:
            src.device.device.Device 实例
        """
        from src.device.device import Device, PollConfig, SerialParams, TcpParams
        from src.protocols.enums import DeviceStatus, ProtocolType

        tp = (
            TcpParams(
                host=self.host or "127.0.0.1",
                port=self.port or 502,
            )
            if self.protocol_type in (ProtocolType.MODBUS_TCP.value, "modbus_tcp")
            else None
        )

        sp = (
            SerialParams(
                port=self.serial_port or "COM1",
                baud_rate=self.baud_rate or 9600,
                data_bits=self.data_bits or 8,
                stop_bits=self.stop_bits or 1,
                parity=self.parity or "N",
            )
            if self.protocol_type
            in (
                ProtocolType.MODBUS_RTU.value,
                "modbus_rtu",
                ProtocolType.MODBUS_ASCII.value,
                "modbus_ascii",
            )
            else None
        )

        pc = PollConfig(
            interval_ms=self.poll_interval_ms or 1000,
            timeout_ms=self.poll_timeout_ms or 3000,
            retry_count=self.poll_retry_count or 3,
            retry_interval_ms=self.poll_retry_interval_ms or 500,
        )

        # 解析协议类型
        try:
            pt = ProtocolType(self.protocol_type)
        except (ValueError, AttributeError):
            pt = ProtocolType.MODBUS_TCP

        # 解析状态
        try:
            status = DeviceStatus(self.status)
        except (ValueError, AttributeError):
            status = DeviceStatus.DISCONNECTED

        device = Device(
            name=self.name,
            protocol_type=pt,
            slave_id=self.slave_id or 1,
            tcp_params=tp,
            serial_params=sp,
            poll_config=pc,
        )
        device._id = self.id  # 设置ID
        device._enabled = self.enabled
        device._device_status = status

        # 恢复寄存器
        for rm in self.register_maps:
            if rm.enabled:
                device.add_register(rm.to_domain())

        return device


# ═══════════════════════════════════════════════════════════════
# 寄存器映射模型
# ═══════════════════════════════════════════════════════════════


class RegisterMapModel(Base):
    """寄存器映射持久化模型

    对应 src.device.register.Register 的数据库表示。
    """

    __tablename__ = "register_maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(
        String(64),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(128), nullable=False)
    address = Column(Integer, nullable=False)
    register_type = Column(String(32), default="holding_register")
    data_type = Column(String(32), default="uint16")
    quantity = Column(Integer, default=1)
    scale = Column(Float, default=1.0)
    offset = Column(Float, default=0.0)
    unit = Column(String(32), default="")
    description = Column(Text, nullable=True)
    read_only = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)

    device = relationship("DeviceModel", back_populates="register_maps")

    __table_args__ = (
        Index("idx_register_device", "device_id"),
        Index("idx_register_address", "device_id", "address"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "name": self.name,
            "address": self.address,
            "register_type": self.register_type,
            "data_type": self.data_type,
            "quantity": self.quantity,
            "scale": self.scale,
            "offset": self.offset,
            "unit": self.unit,
            "description": self.description,
            "read_only": self.read_only,
            "enabled": self.enabled,
        }

    @classmethod
    def from_domain(cls, register: Any) -> RegisterMapModel:
        """从运行时 Register 创建"""
        dt = register.data_type
        dt_val = dt.value[0] if isinstance(dt.value, tuple) else str(dt)
        rt = register.register_type
        rt_val = rt.value if isinstance(rt.value, str) else str(rt)
        return cls(
            name=register.name,
            address=register.address,
            register_type=rt_val,
            data_type=dt_val,
            quantity=register.quantity,
            scale=register.scale,
            offset=getattr(register, "offset", 0.0),
            unit=register.unit,
            description=getattr(register, "description", ""),
            read_only=register.read_only,
            enabled=True,
        )

    def to_domain(self) -> Any:
        """转换为运行时 Register"""
        from src.device.register import Register
        from src.protocols.enums import DataType, RegisterType

        # 解析 register_type (value 是字符串)
        rt_val = self.register_type
        try:
            rt = RegisterType(rt_val) if isinstance(rt_val, str) else RegisterType.HOLDING_REGISTER
        except (ValueError, AttributeError):
            rt = RegisterType.HOLDING_REGISTER

        # 解析 data_type (value 是字符串, 枚举值可能是tuple)
        dt_val = self.data_type
        try:
            dt = DataType(dt_val) if isinstance(dt_val, str) else DataType.UINT16
        except (ValueError, AttributeError):
            dt = DataType.UINT16

        reg = Register(
            name=self.name,
            address=self.address,
            register_type=rt,
            data_type=dt,
            quantity=self.quantity or 1,
            scale=self.scale or 1.0,
            offset=self.offset or 0.0,
            unit=self.unit or "",
            description=self.description or "",
            read_only=self.read_only,
        )

        # 恢复报警配置
        from src.device.register import AlarmConfig, AlarmLevel

        ac = getattr(reg, "_alarm_config", None)
        if ac is None:
            # alarm 在 Register 上可能通过不同方式设置
            pass

        return reg


# ═══════════════════════════════════════════════════════════════
# 历史数据模型
# ═══════════════════════════════════════════════════════════════


class HistoricalDataModel(Base):
    """历史数据点"""

    __tablename__ = "historical_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(
        String(64),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    register_name = Column(String(128), nullable=False)
    value = Column(Float, nullable=False)
    raw_value = Column(Integer, nullable=True)
    unit = Column(String(32), default="")
    quality = Column(Integer, default=0)
    timestamp = Column(DateTime, default=_now, index=True)

    device = relationship("DeviceModel", back_populates="historical_data")

    __table_args__ = (
        Index("idx_hist_device_time", "device_id", "timestamp"),
        Index("idx_hist_reg_time", "device_id", "register_name", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "register_name": self.register_name,
            "value": self.value,
            "raw_value": self.raw_value,
            "unit": self.unit,
            "quality": self.quality,
            "timestamp": (self.timestamp.isoformat() if self.timestamp else None),
        }


# ═══════════════════════════════════════════════════════════════
# 报警记录模型
# ═══════════════════════════════════════════════════════════════


class AlarmRecordModel(Base):
    """报警历史记录"""

    __tablename__ = "alarm_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), nullable=False)
    device_id = Column(String(64), nullable=False, index=True)
    device_name = Column(String(128), nullable=True)
    register_name = Column(String(128), nullable=False)
    alarm_type = Column(String(32), nullable=False)
    level = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)
    threshold_high = Column(Float, nullable=True)
    threshold_low = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_now, index=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(64), nullable=True)

    __table_args__ = (
        Index("idx_alarm_device_time", "device_id", "timestamp"),
        Index("idx_alarm_level", "level"),
        Index("idx_alarm_ack", "acknowledged"),
    )

    _LEVEL_NAMES = {0: "信息", 1: "警告", 2: "错误", 3: "严重"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "register_name": self.register_name,
            "alarm_type": self.alarm_type,
            "level": self.level,
            "level_name": self._LEVEL_NAMES.get(self.level, "未知"),
            "value": self.value,
            "threshold_high": self.threshold_high,
            "threshold_low": self.threshold_low,
            "description": self.description,
            "timestamp": (self.timestamp.isoformat() if self.timestamp else None),
            "acknowledged": self.acknowledged,
            "acknowledged_at": (self.acknowledged_at.isoformat() if self.acknowledged_at else None),
            "acknowledged_by": self.acknowledged_by,
        }


# ═══════════════════════════════════════════════════════════════
# 报警规则模型
# ═══════════════════════════════════════════════════════════════


class AlarmRuleModel(Base):
    """报警规则"""

    __tablename__ = "alarm_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), nullable=False, unique=True, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    device_name = Column(String(128), nullable=False)
    register_name = Column(String(128), nullable=False)
    alarm_type = Column(String(32), nullable=False)
    level = Column(Integer, nullable=False)
    threshold_high = Column(Float, nullable=True)
    threshold_low = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (
        Index("idx_rule_device_reg", "device_id", "register_name"),
        Index("idx_rule_enabled", "enabled"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("rule_id", uuid.uuid4().hex[:12])
        kwargs.setdefault("level", 1)
        kwargs.setdefault("alarm_type", "high_limit")
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "register_name": self.register_name,
            "alarm_type": self.alarm_type,
            "level": self.level,
            "threshold_high": self.threshold_high,
            "threshold_low": self.threshold_low,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
        }


# ═══════════════════════════════════════════════════════════════
# 系统日志模型
# ═══════════════════════════════════════════════════════════════


class SystemLogModel(Base):
    """系统日志"""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(16), nullable=False, index=True)
    logger_name = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(128), nullable=True)
    function_name = Column(String(128), nullable=True)
    line_number = Column(Integer, nullable=True)
    exception = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_now, index=True)

    __table_args__ = (Index("idx_log_level_time", "level", "timestamp"),)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "module": self.module,
            "function_name": self.function_name,
            "line_number": self.line_number,
            "exception": self.exception,
            "timestamp": (self.timestamp.isoformat() if self.timestamp else None),
        }


# ═══════════════════════════════════════════════════════════════
# 设备状态历史模型
# ═══════════════════════════════════════════════════════════════


class DeviceStatusHistoryModel(Base):
    """设备状态历史记录

    记录设备的状态变化历史，用于状态追踪和趋势分析。
    """

    __tablename__ = "device_status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)  # connected, disconnected, error
    status_code = Column(Integer, nullable=True)  # 数字状态码
    message = Column(Text, nullable=True)  # 状态描述或错误信息
    ip_address = Column(String(64), nullable=True)  # 连接时的IP
    port = Column(Integer, nullable=True)  # 连接时的端口
    duration_ms = Column(Integer, nullable=True)  # 状态持续时间(毫秒)
    timestamp = Column(DateTime, default=_now, nullable=False, index=True)

    # 关联关系
    device = relationship("DeviceModel", backref="status_history")

    __table_args__ = (
        Index("idx_status_history_device_time", "device_id", "timestamp"),
        Index("idx_status_history_status_time", "status", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "status": self.status,
            "status_code": self.status_code,
            "message": self.message,
            "ip_address": self.ip_address,
            "port": self.port,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_event(
        cls,
        device_id: str,
        status: str,
        status_code: int = None,
        message: str = None,
        ip_address: str = None,
        port: int = None,
    ) -> "DeviceStatusHistoryModel":
        """从状态事件创建设备状态历史记录"""
        return cls(
            device_id=device_id,
            status=status,
            status_code=status_code,
            message=message,
            ip_address=ip_address,
            port=port,
        )
