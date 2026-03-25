# -*- coding: utf-8 -*-
"""
数据库模型定义
Database Models
"""

import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

Base = declarative_base()


class DeviceModel(Base):
    """设备模型 - 持久化设备信息"""

    __tablename__ = "devices"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False, index=True)
    device_type = Column(String(64), nullable=False)
    device_number = Column(String(64), nullable=True)
    protocol_type = Column(String(32), nullable=False)
    host = Column(String(64), nullable=True)
    port = Column(Integer, nullable=True)
    unit_id = Column(Integer, default=1)
    use_simulator = Column(Boolean, default=False)
    status = Column(Integer, default=0)  # 0=DISCONNECTED, 1=CONNECTING, 2=CONNECTED, 3=ERROR
    last_connected_at = Column(DateTime, nullable=True)
    connection_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    register_maps = relationship("RegisterMapModel", back_populates="device", cascade="all, delete-orphan")
    historical_data = relationship("HistoricalDataModel", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_device_type", "device_type"),
        Index("idx_device_name", "name"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type,
            "device_number": self.device_number,
            "protocol_type": self.protocol_type,
            "host": self.host,
            "port": self.port,
            "unit_id": self.unit_id,
            "use_simulator": self.use_simulator,
            "status": self.status,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "connection_count": self.connection_count,
            "error_count": self.error_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RegisterMapModel(Base):
    """寄存器映射模型"""

    __tablename__ = "register_maps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    address = Column(Integer, nullable=False)
    function_code = Column(Integer, default=3)
    data_type = Column(String(32), default="uint16")  # uint16, int16, uint32, int32, float32, float64
    read_write = Column(String(8), default="R")  # R, W, RW
    scale = Column(Float, default=1.0)
    unit = Column(String(32), default="")
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)

    # 关系
    device = relationship("DeviceModel", back_populates="register_maps")

    __table_args__ = (
        Index("idx_register_device", "device_id"),
        Index("idx_register_address", "device_id", "address"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "name": self.name,
            "address": self.address,
            "function_code": self.function_code,
            "data_type": self.data_type,
            "read_write": self.read_write,
            "scale": self.scale,
            "unit": self.unit,
            "description": self.description,
            "enabled": self.enabled,
        }


class HistoricalDataModel(Base):
    """历史数据模型"""

    __tablename__ = "historical_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    parameter_name = Column(String(128), nullable=False)
    value = Column(Float, nullable=False)
    raw_value = Column(Integer, nullable=True)  # 原始寄存器值
    unit = Column(String(32), default="")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    quality = Column(Integer, default=0)  # 数据质量: 0=good, 1=uncertain, 2=bad

    # 关系
    device = relationship("DeviceModel", back_populates="historical_data")

    __table_args__ = (
        Index("idx_hist_device_time", "device_id", "timestamp"),
        Index("idx_hist_param_time", "device_id", "parameter_name", "timestamp"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "parameter_name": self.parameter_name,
            "value": self.value,
            "raw_value": self.raw_value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "quality": self.quality,
        }


class AlarmModel(Base):
    """报警记录模型"""

    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), nullable=False)
    device_id = Column(String(64), nullable=False, index=True)
    device_name = Column(String(128), nullable=True)
    parameter = Column(String(128), nullable=False)
    alarm_type = Column(String(32), nullable=False)  # threshold_high, threshold_low, etc.
    level = Column(Integer, nullable=False)  # 0=info, 1=warning, 2=critical
    value = Column(Float, nullable=False)
    threshold_high = Column(Float, nullable=True)
    threshold_low = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(64), nullable=True)

    __table_args__ = (
        Index("idx_alarm_device_time", "device_id", "timestamp"),
        Index("idx_alarm_level", "level"),
        Index("idx_alarm_ack", "acknowledged"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "parameter": self.parameter,
            "alarm_type": self.alarm_type,
            "level": self.level,
            "level_name": ["信息", "警告", "严重"][self.level] if self.level < 3 else "未知",
            "value": self.value,
            "threshold_high": self.threshold_high,
            "threshold_low": self.threshold_low,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
        }


class AlarmRuleModel(Base):
    """报警规则模型"""

    __tablename__ = "alarm_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(64), nullable=False, unique=True, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    device_name = Column(String(128), nullable=False)
    parameter = Column(String(64), nullable=False)
    alarm_type = Column(String(32), nullable=False)  # THRESHOLD_HIGH, THRESHOLD_LOW, DEVICE_OFFLINE, etc.
    level = Column(Integer, nullable=False)  # 0=INFO, 1=WARNING, 2=ERROR, 3=CRITICAL
    threshold_high = Column(Float, nullable=True)
    threshold_low = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_rule_device_param", "device_id", "parameter"),
        Index("idx_rule_enabled", "enabled"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "parameter": self.parameter,
            "alarm_type": self.alarm_type,
            "level": self.level,
            "threshold_high": self.threshold_high,
            "threshold_low": self.threshold_low,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SystemLogModel(Base):
    """系统日志模型"""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(16), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger = Column(String(64), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(128), nullable=True)
    function = Column(String(128), nullable=True)
    line = Column(Integer, nullable=True)
    exception = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (Index("idx_log_level_time", "level", "timestamp"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "exception": self.exception,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class DatabaseManager:
    """数据库管理器 - 单例模式"""

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return

        if db_path is None:
            db_path = os.path.join("data", "equipment_management.db")

        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self._db_path = db_path
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self._session_factory = sessionmaker(bind=self._engine)

        # 创建表
        Base.metadata.create_all(self._engine)

        self._initialized = True

    @contextmanager
    def session(self) -> Session:
        """上下文管理器，自动处理会话生命周期"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_session(self) -> Session:
        """获取新会话（需要手动关闭）"""
        return self._session_factory()

    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()

    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试）"""
        cls._instance = None
        cls._engine = None
        cls._session_factory = None


# 便捷函数
def get_db_manager(db_path: str = None) -> DatabaseManager:
    """获取数据库管理器实例"""
    return DatabaseManager(db_path)


def init_database(db_path: str = None):
    """初始化数据库"""
    return DatabaseManager(db_path)
