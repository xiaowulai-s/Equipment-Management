"""
设备数据模型

设计原则:
    1. 设备的完整描述 (ID/名称/协议/通信参数/寄存器列表)
    2. 聚合管理多个Register实例
    3. 继承QObject, 支持Qt信号槽 (状态变化/值更新/报警)
    4. 支持JSON序列化/反序列化
    5. 内置通信参数配置 (TCP/串口)
    6. 线程安全: QMutex保护寄存器值更新

信号体系:
    status_changed(DeviceStatus)  → 设备状态变化
    value_changed(str, int, float) → 寄存器值变化 (register_name, raw, eng)
    alarm_triggered(str, str, float, str) → 报警 (device_name, register_name, value, level)
    alarm_cleared(str, str, str)  → 报警清除 (device_name, register_name, level)
    register_added(str)           → 寄存器添加 (register_name)
    register_removed(str)         → 寄存器移除 (register_name)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from PySide6.QtCore import QMutex, QMutexLocker, QObject, Signal

from src.device.register import AlarmConfig, Register
from src.protocols.enums import DataType, DeviceStatus, Endian, ProtocolType, RegisterType

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 通信参数
# ═══════════════════════════════════════════════════════════════


@dataclass
class TcpParams:
    """TCP通信参数"""

    host: str = "127.0.0.1"
    port: int = 502
    timeout: float = 3.0
    ssl_enabled: bool = False
    ssl_cert: str = ""
    keepalive_enabled: bool = True
    keepalive_interval: float = 30.0
    reconnect_enabled: bool = True
    reconnect_interval: float = 5.0
    reconnect_max_attempts: int = 10
    bind_address: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TcpParams:
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class SerialParams:
    """串口通信参数"""

    port: str = "COM1"
    baud_rate: int = 9600
    data_bits: int = 8
    stop_bits: float = 1.0
    parity: str = "none"
    timeout: float = 3.0
    flow_control: bool = False
    rts: bool = True
    dtr: bool = True
    hotplug_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SerialParams:
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ═══════════════════════════════════════════════════════════════
# 设备轮询配置
# ═══════════════════════════════════════════════════════════════


@dataclass
class PollConfig:
    """数据采集轮询配置"""

    enabled: bool = True
    interval_ms: int = 1000  # 轮询间隔 (毫秒)
    timeout_ms: int = 3000  # 单次请求超时
    retry_count: int = 3  # 失败重试次数
    retry_interval_ms: int = 500  # 重试间隔

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PollConfig:
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ═══════════════════════════════════════════════════════════════
# 设备模型
# ═══════════════════════════════════════════════════════════════


class Device(QObject):
    """设备数据模型

    描述一个工业设备的完整配置和运行时状态。
    聚合管理多个Register, 支持状态跟踪和信号通知。

    Attributes:
        id:              设备唯一标识 (UUID)
        name:            设备名称
        protocol_type:   协议类型 (TCP/RTU/ASCII)
        device_status:   当前设备状态
        description:     设备描述
        location:        安装位置
        tcp_params:      TCP通信参数
        serial_params:   串口通信参数
        poll_config:     轮询配置
        slave_id:        Modbus从站ID (1-247)
        tags:            标签列表 (用于搜索/分类)
        enabled:         是否启用
        icon:            图标标识
    """

    # ── 信号 ──────────────────────────────────────────────────
    status_changed = Signal(object)  # DeviceStatus
    value_changed = Signal(str, int, float, object)  # reg_name, raw, eng, timestamp
    alarm_triggered = Signal(str, str, float, str)  # dev_name, reg_name, value, level
    alarm_cleared = Signal(str, str, str)  # dev_name, reg_name, level
    register_added = Signal(str)  # register_name
    register_removed = Signal(str)  # register_name
    connection_info_changed = Signal()  # 通信参数变更
    config_changed = Signal(str)  # changed_property

    def __init__(
        self,
        name: str = "",
        protocol_type: ProtocolType = ProtocolType.MODBUS_TCP,
        slave_id: int = 1,
        description: str = "",
        location: str = "",
        tcp_params: Optional[TcpParams] = None,
        serial_params: Optional[SerialParams] = None,
        poll_config: Optional[PollConfig] = None,
        device_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        enabled: bool = True,
        icon: str = "",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        # 生成唯一ID
        self._id = device_id if device_id else str(uuid.uuid4())

        # 基本信息
        self._name = name
        self._protocol_type = protocol_type
        self._slave_id = slave_id
        self._description = description
        self._location = location
        self._tags = tags if tags is not None else []
        self._enabled = enabled
        self._icon = icon

        # 通信参数
        self._tcp_params = tcp_params if tcp_params else TcpParams()
        self._serial_params = serial_params if serial_params else SerialParams()
        self._poll_config = poll_config if poll_config else PollConfig()

        # 运行时状态
        self._device_status = DeviceStatus.DISCONNECTED
        self._registers: dict[str, Register] = {}  # name → Register
        self._last_online: Optional[datetime] = None
        self._last_error: str = ""
        self._error_count: int = 0
        self._total_polls: int = 0
        self._failed_polls: int = 0

        # 线程安全
        self._mutex = QMutex()

    # ═══════════════════════════════════════════════════════════
    # 基本属性
    # ═══════════════════════════════════════════════════════════

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value:
            raise ValueError("设备名称不能为空")
        self._name = value
        self.config_changed.emit("name")

    @property
    def protocol_type(self) -> ProtocolType:
        return self._protocol_type

    @protocol_type.setter
    def protocol_type(self, value: ProtocolType) -> None:
        self._protocol_type = value
        self.config_changed.emit("protocol_type")

    @property
    def slave_id(self) -> int:
        return self._slave_id

    @slave_id.setter
    def slave_id(self, value: int) -> None:
        if not (0 <= value <= 247):
            raise ValueError(f"从站ID必须在0-247范围内: {value}")
        self._slave_id = value
        self.config_changed.emit("slave_id")

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value
        self.config_changed.emit("description")

    @property
    def location(self) -> str:
        return self._location

    @location.setter
    def location(self, value: str) -> None:
        self._location = value
        self.config_changed.emit("location")

    @property
    def tags(self) -> list[str]:
        return list(self._tags)  # 返回副本

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self._tags = list(value)
        self.config_changed.emit("tags")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        self.config_changed.emit("enabled")

    @property
    def icon(self) -> str:
        return self._icon

    @icon.setter
    def icon(self, value: str) -> None:
        self._icon = value
        self.config_changed.emit("icon")

    # ═══════════════════════════════════════════════════════════
    # 通信参数
    # ═══════════════════════════════════════════════════════════

    @property
    def tcp_params(self) -> TcpParams:
        return self._tcp_params

    @tcp_params.setter
    def tcp_params(self, value: TcpParams) -> None:
        self._tcp_params = value
        self.connection_info_changed.emit()

    @property
    def serial_params(self) -> SerialParams:
        return self._serial_params

    @serial_params.setter
    def serial_params(self, value: SerialParams) -> None:
        self._serial_params = value
        self.connection_info_changed.emit()

    @property
    def poll_config(self) -> PollConfig:
        return self._poll_config

    @poll_config.setter
    def poll_config(self, value: PollConfig) -> None:
        self._poll_config = value
        self.config_changed.emit("poll_config")

    @property
    def connection_params(self) -> Union[TcpParams, SerialParams]:
        """根据协议类型返回对应的通信参数"""
        if self._protocol_type == ProtocolType.MODBUS_TCP:
            return self._tcp_params
        else:
            return self._serial_params

    # ═══════════════════════════════════════════════════════════
    # 设备状态
    # ═══════════════════════════════════════════════════════════

    @property
    def device_status(self) -> DeviceStatus:
        return self._device_status

    @property
    def is_connected(self) -> bool:
        return self._device_status == DeviceStatus.CONNECTED

    @property
    def is_error(self) -> bool:
        return self._device_status == DeviceStatus.ERROR

    def set_status(self, status: DeviceStatus) -> None:
        """设置设备状态, 仅在状态变化时发射信号

        Args:
            status: 新的设备状态
        """
        if self._device_status != status:
            old = self._device_status
            self._device_status = status

            if status == DeviceStatus.CONNECTED:
                self._last_online = datetime.now()
                self._last_error = ""
                self._error_count = 0

            if status == DeviceStatus.ERROR:
                self._error_count += 1

            logger.info(f"设备[{self._name}] 状态变更: " f"{old.display_text} → {status.display_text}")
            self.status_changed.emit(status)

    def set_error(self, error_msg: str) -> None:
        """设置错误状态

        Args:
            error_msg: 错误描述
        """
        self._last_error = error_msg
        self.set_status(DeviceStatus.ERROR)
        logger.error(f"设备[{self._name}] 错误: {error_msg}")

    # ═══════════════════════════════════════════════════════════
    # 运行时统计
    # ═══════════════════════════════════════════════════════════

    @property
    def last_online(self) -> Optional[datetime]:
        return self._last_online

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def total_polls(self) -> int:
        return self._total_polls

    @property
    def failed_polls(self) -> int:
        return self._failed_polls

    @property
    def success_rate(self) -> float:
        """采集成功率 (%)"""
        if self._total_polls == 0:
            return 100.0
        return (1.0 - self._failed_polls / self._total_polls) * 100.0

    def record_poll_success(self) -> None:
        """记录一次成功的轮询"""
        self._total_polls += 1

    def record_poll_failure(self) -> None:
        """记录一次失败的轮询"""
        self._total_polls += 1
        self._failed_polls += 1

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self._error_count = 0
        self._total_polls = 0
        self._failed_polls = 0

    # ═══════════════════════════════════════════════════════════
    # 寄存器管理
    # ═══════════════════════════════════════════════════════════

    @property
    def registers(self) -> dict[str, Register]:
        """返回寄存器字典 (只读副本)"""
        return dict(self._registers)

    @property
    def register_count(self) -> int:
        return len(self._registers)

    @property
    def register_names(self) -> list[str]:
        return list(self._registers.keys())

    @property
    def alarmed_registers(self) -> list[Register]:
        """返回所有处于报警状态的寄存器"""
        return [r for r in self._registers.values() if r.is_alarmed]

    @property
    def alarm_count(self) -> int:
        return len(self.alarmed_registers)

    def add_register(self, register: Register) -> None:
        """添加寄存器

        Args:
            register: 寄存器实例

        Raises:
            ValueError: 同名寄存器已存在或地址重叠
        """
        if register.name in self._registers:
            raise ValueError(f"寄存器'{register.name}'已存在")

        # 检查地址重叠
        for existing in self._registers.values():
            if register.overlaps(existing):
                raise ValueError(
                    f"寄存器'{register.name}'(地址{register.address}-{register.end_address}) "
                    f"与'{existing.name}'(地址{existing.address}-{existing.end_address})地址重叠"
                )

        # 连接信号
        register.setParent(self)
        register.value_changed.connect(self._on_register_value_changed)
        register.alarm_triggered.connect(self._on_register_alarm_triggered)
        register.alarm_cleared.connect(self._on_register_alarm_cleared)

        self._registers[register.name] = register
        self.register_added.emit(register.name)
        logger.debug(f"设备[{self._name}] 添加寄存器: {register.name}")

    def remove_register(self, name: str) -> None:
        """移除寄存器

        Args:
            name: 寄存器名称

        Raises:
            KeyError: 寄存器不存在
        """
        if name not in self._registers:
            raise KeyError(f"寄存器'{name}'不存在")

        register = self._registers.pop(name)

        # 断开信号
        try:
            register.value_changed.disconnect(self._on_register_value_changed)
            register.alarm_triggered.disconnect(self._on_register_alarm_triggered)
            register.alarm_cleared.disconnect(self._on_register_alarm_cleared)
        except RuntimeError:
            pass  # 信号可能已断开

        register.setParent(None)
        self.register_removed.emit(name)
        logger.debug(f"设备[{self._name}] 移除寄存器: {name}")

    def get_register(self, name: str) -> Optional[Register]:
        """获取寄存器 (按名称)"""
        return self._registers.get(name)

    def get_register_by_address(self, address: int, reg_type: RegisterType) -> Optional[Register]:
        """获取寄存器 (按地址和类型)"""
        for reg in self._registers.values():
            if reg.address == address and reg.register_type == reg_type:
                return reg
        return None

    def get_registers_by_group(self, group: str) -> list[Register]:
        """获取指定分组的所有寄存器"""
        return [r for r in self._registers.values() if r.group == group]

    def get_register_groups(self) -> list[str]:
        """获取所有寄存器分组名称"""
        groups = set()
        for reg in self._registers.values():
            groups.add(reg.group)
        return sorted(groups)

    def update_register_value(self, name: str, raw_value: int) -> None:
        """更新寄存器原始值 (线程安全)

        Args:
            name: 寄存器名称
            raw_value: 原始值
        """
        locker = QMutexLocker(self._mutex)
        register = self._registers.get(name)
        if register is None:
            logger.warning(f"设备[{self._name}] 未知寄存器: {name}")
            return
        register.update_raw_value(raw_value)

    def batch_update_values(self, values: dict[str, int]) -> int:
        """批量更新寄存器值 (线程安全)

        Args:
            values: {寄存器名称: 原始值}

        Returns:
            成功更新的数量
        """
        locker = QMutexLocker(self._mutex)
        count = 0
        for name, raw_value in values.items():
            register = self._registers.get(name)
            if register is not None:
                register.update_raw_value(raw_value)
                count += 1
            else:
                logger.warning(f"设备[{self._name}] 批量更新: 未知寄存器: {name}")
        return count

    def clear_all_values(self) -> None:
        """清除所有寄存器的值"""
        for reg in self._registers.values():
            reg.clear_value()

    # ═══════════════════════════════════════════════════════════
    # 信号槽
    # ═══════════════════════════════════════════════════════════

    def _on_register_value_changed(self, raw: int, eng: float, timestamp: object) -> None:
        """寄存器值变化 → 转发"""
        sender = self.sender()
        if isinstance(sender, Register):
            self.value_changed.emit(sender.name, raw, eng, timestamp)

    def _on_register_alarm_triggered(self, level: str, value: float, message: str) -> None:
        """寄存器报警 → 转发"""
        sender = self.sender()
        if isinstance(sender, Register):
            self.alarm_triggered.emit(self._name, sender.name, value, level)

    def _on_register_alarm_cleared(self, old_level: str, message: str) -> None:
        """寄存器报警清除 → 转发"""
        sender = self.sender()
        if isinstance(sender, Register):
            self.alarm_cleared.emit(self._name, sender.name, old_level)

    # ═══════════════════════════════════════════════════════════
    # 批量操作 (读写优化)
    # ═══════════════════════════════════════════════════════════

    def get_read_requests(self) -> list[dict[str, Any]]:
        """生成所有可读寄存器的读取请求列表

        返回合并后的请求, 连续地址的同类寄存器合并为一个请求。

        Returns:
            请求列表, 每个请求包含:
            - register_type: RegisterType
            - start_address: int
            - count: int
            - register_names: list[str] (涉及的寄存器名称)
        """
        # 按类型分组
        by_type: dict[RegisterType, list[Register]] = {}
        for reg in self._registers.values():
            by_type.setdefault(reg.register_type, []).append(reg)

        requests: list[dict[str, Any]] = []

        for reg_type, regs in by_type.items():
            # 按地址排序
            sorted_regs = sorted(regs, key=lambda r: r.address)

            # 合并连续地址的寄存器 (间隔<=1个寄存器地址)
            current_start = sorted_regs[0].address
            current_end = sorted_regs[0].end_address
            current_names = [sorted_regs[0].name]

            for reg in sorted_regs[1:]:
                # 检查是否与当前区间连续 (间隔<=1寄存器地址)
                if reg.address <= current_end + 1:
                    current_end = max(current_end, reg.end_address)
                    current_names.append(reg.name)
                else:
                    # 输出当前区间
                    requests.append(
                        {
                            "register_type": reg_type,
                            "start_address": current_start,
                            "count": current_end - current_start + 1,
                            "register_names": current_names,
                        }
                    )
                    # 开始新区间
                    current_start = reg.address
                    current_end = reg.end_address
                    current_names = [reg.name]

            # 输出最后一个区间
            requests.append(
                {
                    "register_type": reg_type,
                    "start_address": current_start,
                    "count": current_end - current_start + 1,
                    "register_names": current_names,
                }
            )

        return requests

    # ═══════════════════════════════════════════════════════════
    # 序列化
    # ═══════════════════════════════════════════════════════════

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self._id,
            "name": self._name,
            "protocol_type": self._protocol_type.value,
            "slave_id": self._slave_id,
            "description": self._description,
            "location": self._location,
            "tags": self._tags,
            "enabled": self._enabled,
            "icon": self._icon,
            "tcp_params": self._tcp_params.to_dict(),
            "serial_params": self._serial_params.to_dict(),
            "poll_config": self._poll_config.to_dict(),
            "registers": [reg.to_dict() for reg in self._registers.values()],
            # 运行时状态
            "device_status": self._device_status.value,
            "last_online": (self._last_online.isoformat() if self._last_online else None),
            "last_error": self._last_error,
            "error_count": self._error_count,
            "total_polls": self._total_polls,
            "failed_polls": self._failed_polls,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        """从字典反序列化

        Args:
            data: 设备配置字典

        Returns:
            Device实例
        """
        # 解析协议类型
        protocol = ProtocolType(data.get("protocol_type", "modbus_tcp"))

        # 解析通信参数
        tcp_data = data.get("tcp_params", {})
        serial_data = data.get("serial_params", {})
        poll_data = data.get("poll_config", {})

        device = cls(
            name=data.get("name", ""),
            protocol_type=protocol,
            slave_id=data.get("slave_id", 1),
            description=data.get("description", ""),
            location=data.get("location", ""),
            tcp_params=TcpParams.from_dict(tcp_data),
            serial_params=SerialParams.from_dict(serial_data),
            poll_config=PollConfig.from_dict(poll_data),
            device_id=data.get("id"),
            tags=data.get("tags", []),
            enabled=data.get("enabled", True),
            icon=data.get("icon", ""),
        )

        # 恢复寄存器
        for reg_data in data.get("registers", []):
            try:
                register = Register.from_dict(reg_data)
                device.add_register(register)
            except Exception as e:
                logger.error(f"设备[{device.name}] 恢复寄存器失败: {e}")

        # 恢复运行时状态
        status_str = data.get("device_status", "disconnected")
        try:
            device._device_status = DeviceStatus(status_str)
        except ValueError:
            device._device_status = DeviceStatus.DISCONNECTED

        if data.get("last_online"):
            try:
                device._last_online = datetime.fromisoformat(data["last_online"])
            except (ValueError, TypeError):
                pass

        device._last_error = data.get("last_error", "")
        device._error_count = data.get("error_count", 0)
        device._total_polls = data.get("total_polls", 0)
        device._failed_polls = data.get("failed_polls", 0)

        return device

    def to_json(self, indent: int = 2) -> str:
        """序列化为JSON字符串"""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> Device:
        """从JSON字符串反序列化"""
        import json

        return cls.from_dict(json.loads(json_str))

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag not in self._tags:
            self._tags.append(tag)
            self.config_changed.emit("tags")

    def remove_tag(self, tag: str) -> None:
        """移除标签"""
        if tag in self._tags:
            self._tags.remove(tag)
            self.config_changed.emit("tags")

    def has_tag(self, tag: str) -> bool:
        """检查是否包含标签"""
        return tag in self._tags

    def __repr__(self) -> str:
        return (
            f"Device(name='{self._name}', "
            f"protocol={self._protocol_type.value}, "
            f"slave={self._slave_id}, "
            f"registers={self.register_count}, "
            f"status={self._device_status.value})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Device):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def get_summary(self) -> dict[str, Any]:
        """获取设备摘要信息"""
        return {
            "name": self._name,
            "status": self._device_status.display_text,
            "registers": self.register_count,
            "alarms": self.alarm_count,
            "success_rate": f"{self.success_rate:.1f}%",
            "last_online": (self._last_online.strftime("%Y-%m-%d %H:%M:%S") if self._last_online else "从未"),
            "errors": self._error_count,
        }
