# -*- coding: utf-8 -*-
"""
设备配置数据模型 - 重构版
Device Configuration Data Models (Refactored)

将设备配置从 Device 上帝对象中提取为独立的 dataclass，
实现配置与行为的完全分离。

设计原则:
- 纯数据容器，无副作用
- 可序列化/反序列化（JSON/dict）
- 类型安全（使用 dataclass + 类型注解）
- 不可变性（frozen=True 对于关键配置）

职责范围:
✓ 连接参数（host, port, baudrate等）
✓ 协议参数（unit_id, byte_order等）
✓ 寄存器映射定义
✓ 业务属性（name, type, group等）

排除范围:
✗ connect/disconnect 行为 → DeviceConnection
✗ driver/protocol 实例管理 → DeviceConnection
✗ 轮询逻辑 → DeviceConnection / PollingScheduler
"""

from __future__ import annotations

import copy
import json
import logging
import time
from dataclasses import dataclass, field, asdict, fields
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

from ..protocols.byte_order_config import ByteOrderConfig, DEFAULT_BYTE_ORDER
from ..constants import DEFAULT_GROUP_NAME, PARITY_OPTIONS

logger = logging.getLogger(__name__)


class DeviceStatus(IntEnum):
    """Device connection state."""

    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3


@dataclass
class ConnectionConfig:
    """
    设备连接配置（v3.2 扩展版）

    存储设备连接所需的所有参数，支持多种协议类型。

    Attributes:
        connection_type: 连接类型 ("TCP", "RTU", "OPC-UA", "MQTT")
        host: 主机地址/IP (TCP模式)
        port: 端口号 (TCP模式)
        serial_port: 串口号 (RTU/ASCII模式)
        baudrate: 波特率 (RTU/ASCII模式)
        bytesize: 数据位 (RTU/ASCII模式)
        parity: 校验位 (RTU/ASCII模式)
        stopbits: 停止位 (RTU/ASCII模式)
        timeout: 超时时间(秒)
        retry_count: 重试次数
        register_points: 数据点配置列表 (v3.2 新增)
            - 类型: List[dict] 或 List[RegisterPointConfig]
            - 用于配置驱动的智能轮询
            - 示例: [{"name": "温度", "data_type": "holding_float32", "address": 0, ...}]
        polling_interval_ms: 轮询周期(毫秒) (v3.2 新增)
            - 默认值: 1000ms (1秒)
            - 范围: 100ms ~ 60000ms

    Examples:
        >>> # TCP 模式配置
        >>> tcp_config = ConnectionConfig(
        ...     host="192.168.1.100",
        ...     port=502,
        ...     polling_interval_ms=1000,
        ... )
        >>>
        >>> # RTU 模式配置
        >>> rtu_config = ConnectionConfig(
        ...     serial_port="COM3",
        ...     baudrate=9600,
        ... )

    v3.2 变更说明:
    + 新增 register_points 字段：支持配置驱动的数据点映射
    + 新增 polling_interval_ms 字段：独立于协议的轮询周期控制
    + 向后兼容：新字段均有默认值，不影响现有代码
    """

    connection_type: str = "TCP"  # "TCP", "RTU", "OPC-UA", "MQTT"
    host: str = "127.0.0.1"
    port: int = 502  # TCP端口 或 串口整数标识
    serial_port: str = "COM1"  # 串口设备名（如 "COM1", "/dev/ttyUSB0"）
    baudrate: int = 9600
    timeout: float = 5.0
    retry_count: int = 3
    # 串口专用参数
    bytesize: int = 8
    parity: str = "N"  # "N"=无校验, "E"=偶校验, "O"=奇校验
    stopbits: float = 1.0

    # v3.2 新增字段
    register_points: List[dict] = field(default_factory=list)  # 数据点配置列表
    polling_interval_ms: int = 1000  # 轮询周期(毫秒)，默认1秒

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证连接配置的合法性

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        if self.connection_type not in ("TCP", "RTU", "OPC-UA", "MQTT"):
            errors.append(f"不支持的连接类型: {self.connection_type}")

        if self.connection_type in ("TCP", "OPC-UA"):
            if not self.host:
                errors.append("缺少主机地址(host)")
            elif not isinstance(self.host, str):
                errors.append("主机地址必须是字符串")
            elif "." in self.host and self.host.count(".") == 3:
                parts = self.host.split(".")
                for part in parts:
                    if not part.isdigit() or not 0 <= int(part) <= 255:
                        errors.append("IP地址格式不正确")

            if not isinstance(self.port, int) or not 1 <= self.port <= 65535:
                errors.append(f"端口号必须在 1-65535 范围内，当前值: {self.port}")

        if self.connection_type == "RTU":
            if not self.serial_port:
                errors.append("缺少串口号(serial_port)")

            if self.baudrate not in [9600, 19200, 38400, 57600, 115200]:
                errors.append(f"波特率必须是标准值，当前值: {self.baudrate}")

            if self.bytesize not in [5, 6, 7, 8]:
                errors.append(f"数据位必须是 5-8，当前值: {self.bytesize}")

            if self.parity not in ["N", "E", "O"]:
                errors.append(f"校验位必须是 N/E/O，当前值: {self.parity}")

            if self.stopbits not in [1, 1.5, 2]:
                errors.append(f"停止位必须是 1/1.5/2，当前值: {self.stopbits}")

        if self.timeout <= 0:
            errors.append(f"超时时间必须大于0，当前值: {self.timeout}")

        if self.retry_count < 0:
            errors.append(f"重试次数不能为负数，当前值: {self.retry_count}")

        return len(errors) == 0, errors

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectionConfig":
        """
        从字典创建 ConnectionConfig

        支持从旧格式的 device_config 中提取连接参数。

        Args:
            data: 配置字典

        Returns:
            ConnectionConfig 实例
        """
        # 自动检测连接类型
        protocol_type = str(data.get("protocol_type", "")).lower()
        if protocol_type in ("modbus_tcp", "modbus_ascii"):
            conn_type = "TCP"
        elif protocol_type == "modbus_rtu":
            conn_type = "RTU"
        else:
            conn_type = data.get("connection_type", "TCP")

        # 处理 parity 字段（支持中文和英文）
        parity = data.get("parity", "N")
        parity_map = {"无校验": "N", "偶校验": "E", "奇校验": "O"}
        parity = parity_map.get(parity, parity)

        return cls(
            connection_type=conn_type,
            host=data.get("host", "127.0.0.1"),
            port=data.get("port", 502),
            serial_port=str(data.get("port", data.get("serial_port", "COM1"))),
            baudrate=data.get("baudrate", 9600),
            timeout=float(data.get("timeout", 5.0)),
            retry_count=int(data.get("retry_count", 3)),
            bytesize=data.get("bytesize", 8),
            parity=parity,
            stopbits=float(data.get("stopbits", 1)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return asdict(self)


@dataclass
class ProtocolConfig:
    """
    协议配置 - 从 Device 中提取的协议参数

    设计原则:
    - 封装所有协议层参数
    - 支持多种协议类型（Modbus TCP/RTU/ASCII, OPC-UA, MQTT）
    - 包含字节序配置和寄存器映射

    Attributes:
        protocol_type: 协议类型 ("MODBUS_TCP", "MODBUS_RTU", "MODBUS_ASCII", "OPC-UA")
        unit_id: Modbus单元ID/从机地址
        slave_address: 从机地址（别名）
        byte_order: 字节序配置（可选）
        register_map: 寄存器映射表
        polling_interval_ms: 轮询间隔（毫秒）
        use_simulator: 是否使用模拟器
        auto_reconnect_enabled: 是否自动重连
        namespace: 命名空间（OPC-UA使用）
    """

    protocol_type: str = "MODBUS_TCP"
    unit_id: int = 1
    slave_address: int = 1  # unit_id 的别名
    byte_order: Optional[ByteOrderConfig] = None
    register_map: List[Dict[str, Any]] = field(default_factory=list)
    polling_interval_ms: int = 1000
    use_simulator: bool = False
    auto_reconnect_enabled: bool = False
    namespace: str = ""  # OPC-UA 命名空间

    def __post_init__(self):
        """初始化后处理"""
        # 确保 slave_address 与 unit_id 同步
        if self.slave_address != self.unit_id:
            self.slave_address = self.unit_id

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证协议配置的合法性

        Returns:
            (is_valid, error_messages)
        """
        errors = []
        valid_protocols = {"modbus_tcp", "modbus_rtu", "modbus_ascii", "opc-ua", "mqtt"}

        if self.protocol_type.lower() not in valid_protocols:
            errors.append(f"不支持的协议类型: {self.protocol_type}")

        if not isinstance(self.unit_id, int) or not 0 <= self.unit_id <= 247:
            errors.append(f"Unit ID 必须在 0-247 范围内，当前值: {self.unit_id}")

        if not isinstance(self.polling_interval_ms, int) or self.polling_interval_ms <= 0:
            errors.append(f"轮询间隔必须是正整数，当前值: {self.polling_interval_ms}")

        if not isinstance(self.auto_reconnect_enabled, bool):
            errors.append("自动重连设置必须是布尔值")

        # 验证寄存器映射
        if self.register_map:
            if not isinstance(self.register_map, list):
                errors.append("register_map 必须是列表")
            elif len(self.register_map) > 100:
                errors.append("寄存器映射数量不能超过100个")
            else:
                for i, reg in enumerate(self.register_map):
                    if not isinstance(reg, dict):
                        errors.append(f"register_map[{i}] 必须是字典")
                        continue
                    if "address" not in reg:
                        errors.append(f"register_map[{i}] 缺少 address 字段")
                    if "name" not in reg:
                        errors.append(f"register_map[{i}] 缺少 name 字段")

                    address = reg.get("address")
                    if address is not None and (not isinstance(address, int) or address < 0):
                        errors.append(f"register_map[{i}] 地址必须是非负整数")

                    name = reg.get("name")
                    if name is not None and (not isinstance(name, str) or len(name) > 50):
                        errors.append(f"register_map[{i}] 名称必须是字符串且长度<=50")

                    scale = reg.get("scale", 1.0)
                    if scale is not None and not isinstance(scale, (int, float)):
                        errors.append(f"register_map[{i}] 缩放因子必须是数字")

        return len(errors) == 0, errors

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolConfig":
        """
        从字典创建 ProtocolConfig

        Args:
            data: 配置字典

        Returns:
            ProtocolConfig 实例
        """
        # 转换协议类型为大写格式
        protocol_type = str(data.get("protocol_type", "modbus_tcp")).upper().replace("-", "_")

        # 加载字节序配置
        byte_order = cls._load_byte_order_from_config(data)

        return cls(
            protocol_type=protocol_type,
            unit_id=int(data.get("unit_id", 1)),
            slave_address=int(data.get("unit_id", 1)),
            byte_order=byte_order,
            register_map=list(data.get("register_map", [])),
            polling_interval_ms=int(data.get("poll_interval", 1000)),
            use_simulator=bool(data.get("use_simulator", False)),
            auto_reconnect_enabled=bool(data.get("auto_reconnect_enabled", False)),
            namespace=data.get("namespace", ""),
        )

    @staticmethod
    def _load_byte_order_from_config(config: Dict[str, Any]) -> Optional[ByteOrderConfig]:
        """
        从配置加载字节序设置

        支持格式：
        - "byte_order": "ABCD" （字符串形式）
        - "byte_order": {"byte_order": "big", "word_order": "little"} （字典形式）
        """
        bo_config = config.get("byte_order")
        if bo_config is None:
            return None

        try:
            if isinstance(bo_config, str):
                return ByteOrderConfig.from_string(bo_config)
            elif isinstance(bo_config, dict):
                return ByteOrderConfig(
                    byte_order=bo_config.get("byte_order", "big"), word_order=bo_config.get("word_order", "big")
                )
        except (ValueError, KeyError) as e:
            logger.warning("字节序配置无效: %s", e)

        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        result = asdict(self)
        # 将 ByteOrderConfig 转换为可序列化格式
        if self.byte_order:
            result["byte_order"] = self.byte_order.format_name
        return result


@dataclass
class Device:
    """
    设备数据模型 - 纯数据容器（重构核心）

    设计原则:
    ✅ 单一职责：只负责存储设备属性和配置
    ✅ 无副作用：不包含任何连接、轮询、通信行为
    ✅ 可序列化：支持 JSON/dict 深度转换
    ✅ 线程安全：不可变字段通过 property 保护
    ✅ 可验证：提供完整的配置验证能力

    职责范围（✓ 包含）:
    ✓ 设备标识信息 (device_id, name, device_type)
    ✓ 连接配置 (connection_config)
    ✓ 协议配置 (protocol_config)
    ✓ 运行时状态 (status, last_error)
    ✓ 分组信息 (group)
    ✓ 时间戳 (created_at, updated_at)

    排除范围（✗ 移除到其他类）:
    ✗ connect/disconnect/poll → DeviceConnection
    ✗ driver/protocol 实例 → DeviceConnection
    ✗ 信号发射 → DeviceConnection
    ✗ 模拟器管理 → DeviceConnection

    使用示例:
        >>> config = {
        ...     "device_id": "plc_001",
        ...     "name": "主PLC",
        ...     "device_type": "plc",
        ...     "protocol_type": "modbus_tcp",
        ...     "host": "192.168.1.100",
        ...     "port": 502,
        ... }
        >>> device = Device.from_dict(config)
        >>> device.device_id
        'plc_001'
        >>> device.is_valid()
        True
        >>> cloned = device.clone()
        >>> cloned.name = "备份PLC"  # 深拷贝，互不影响
    """

    # ==================== 必需属性 ====================

    device_id: str
    name: str
    device_type: str  # "sensor", "plc", "rtu", "actuator", etc.

    # ==================== 配置对象（嵌套dataclass）====================

    connection_config: ConnectionConfig = field(default_factory=ConnectionConfig)
    protocol_config: ProtocolConfig = field(default_factory=ProtocolConfig)

    # ==================== 业务属性 ====================

    group: str = DEFAULT_GROUP_NAME
    location: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)

    # ==================== 运行时状态（非持久化）====================

    status: DeviceStatus = DeviceStatus.DISCONNECTED
    last_error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self):
        """初始化后处理"""
        # 确保 device_id 非空
        if not self.device_id:
            raise ValueError("device_id 不能为空")

        # 同步更新时间
        self.updated_at = time.time()

    # ==================== 属性访问器（只读保护）====================

    @property
    def is_connected(self) -> bool:
        """是否已连接（只读）"""
        return self.status == DeviceStatus.CONNECTED

    @property
    def is_using_simulator(self) -> bool:
        """是否使用模拟器（只读）"""
        return self.protocol_config.use_simulator

    @property
    def protocol_type(self) -> str:
        """获取协议类型（便捷属性）"""
        return self.protocol_config.protocol_type

    @property
    def connection_type(self) -> str:
        """获取连接类型（便捷属性）"""
        return self.connection_config.connection_type

    # ==================== 序列化/反序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（深度序列化）

        用于：
        - 数据库持久化
        - JSON 导出/导入
        - 网络传输
        - 日志记录

        Returns:
            完整的设备配置字典（扁平化格式，兼容旧代码）
        """
        # 合并所有配置为扁平化字典（兼容旧的 _config 格式）
        result = {
            # 基本信息
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type,
            # 连接配置（从 ConnectionConfig 提取）
            "protocol_type": self.protocol_config.protocol_type.lower().replace("_", "-"),
            "host": self.connection_config.host,
            "port": self.connection_config.port,
            "baudrate": self.connection_config.baudrate,
            "bytesize": self.connection_config.bytesize,
            "parity": self.connection_config.parity,
            "stopbits": self.connection_config.stopbits,
            "timeout": self.connection_config.timeout,
            "retry_count": self.connection_config.retry_count,
            # 协议配置（从 ProtocolConfig 提取）
            "unit_id": self.protocol_config.unit_id,
            "poll_interval": self.protocol_config.polling_interval_ms,
            "use_simulator": self.protocol_config.use_simulator,
            "auto_reconnect_enabled": self.protocol_config.auto_reconnect_enabled,
            "register_map": self.protocol_config.register_map,
            "namespace": self.protocol_config.namespace,
            # 业务属性
            "group": self.group,
            "location": self.location,
            "description": self.description,
            "tags": self.tags,
            # 运行时状态（可选，通常不持久化）
            "_status": int(self.status),
            "_last_error": self.last_error,
            "_created_at": self.created_at,
            "_updated_at": self.updated_at,
        }

        # 字节序配置（序列化为字符串）
        if self.protocol_config.byte_order:
            result["byte_order"] = self.protocol_config.byte_order.format_name

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """
        从字典创建 Device（反序列化）

        支持：
        - 新格式（包含 connection_config/protocol_config）
        - 旧格式（扁平化的 device_config，向后兼容）

        Args:
            data: 设备配置字典

        Returns:
            Device 实例

        Raises:
            ValueError: 缺少必需字段
        """
        # 验证必需字段
        required_fields = ["device_id"]
        for field_name in required_fields:
            if not data.get(field_name):
                raise ValueError(f"缺少必需字段: {field_name}")

        # 提取嵌套配置对象（如果存在），否则从扁平化字典创建
        connection_config = data.get("connection_config")
        if connection_config and isinstance(connection_config, dict):
            conn_config = ConnectionConfig(**connection_config)
        else:
            conn_config = ConnectionConfig.from_dict(data)

        protocol_config = data.get("protocol_config")
        if protocol_config and isinstance(protocol_config, dict):
            proto_config = ProtocolConfig(**protocol_config)
        else:
            proto_config = ProtocolConfig.from_dict(data)

        return cls(
            device_id=str(data["device_id"]),
            name=data.get("name", f"设备_{data['device_id']}"),
            device_type=data.get("device_type", "unknown"),
            connection_config=conn_config,
            protocol_config=proto_config,
            group=data.get("group", DEFAULT_GROUP_NAME),
            location=data.get("location", ""),
            description=data.get("description", ""),
            tags=list(data.get("tags", [])),
            status=DeviceStatus(int(data.get("_status", 0))),
            last_error=data.get("_last_error"),
            created_at=float(data.get("_created_at", time.time())),
            updated_at=float(data.get("_updated_at", time.time())),
        )

    def to_json(self, indent: int = 2) -> str:
        """
        序列化为 JSON 字符串

        Args:
            indent: 缩进空格数

        Returns:
            JSON 格式的字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "Device":
        """
        从 JSON 字符串创建 Device

        Args:
            json_str: JSON 格式的字符串

        Returns:
            Device 实例
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    # ==================== 验证方法 ====================

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证设备配置的完整性和合法性

        这是合并后的验证入口，会同时检查：
        - Device 基本属性
        - ConnectionConfig 连接参数
        - ProtocolConfig 协议参数

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 验证基本属性
        if not self.device_id:
            errors.append("device_id 不能为空")

        if not self.name:
            errors.append("设备名称不能为空")
        elif not isinstance(self.name, str):
            errors.append("设备名称必须是字符串")
        elif len(self.name) > 50:
            errors.append("设备名称长度不能超过50个字符")

        if not self.device_type:
            errors.append("设备类型不能为空")

        # 验证分组
        if self.group and not isinstance(self.group, str):
            errors.append("分组名称必须是字符串")
        elif self.group and len(self.group) > 50:
            errors.append("分组名称长度不能超过50个字符")

        # 验证连接配置
        conn_valid, conn_errors = self.connection_config.validate()
        if not conn_valid:
            errors.extend([f"连接配置: {e}" for e in conn_errors])

        # 验证协议配置
        proto_valid, proto_errors = self.protocol_config.validate()
        if not proto_valid:
            errors.extend([f"协议配置: {e}" for e in proto_errors])

        return len(errors) == 0, errors

    def is_valid(self) -> bool:
        """快速验证（仅返回bool）"""
        is_valid, _ = self.validate()
        return is_valid

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        静态验证方法（兼容旧接口）

        这是旧 Device.validate_config() 的直接替代。
        保持相同的签名和返回格式，确保向后兼容。

        Args:
            config: 设备配置字典

        Returns:
            (is_valid, error_message)
        """
        try:
            device = Device.from_dict(config)
            is_valid, errors = device.validate()

            if not is_valid:
                return False, "; ".join(errors)

            return True, ""

        except ValueError as e:
            return False, str(e)
        except Exception as e:
            logger.exception("验证设备配置时发生异常")
            return False, f"配置验证异常: {str(e)}"

    # ==================== 克隆与复制 ====================

    def clone(self) -> "Device":
        """
        创建深拷贝（用于模板复制、配置备份等场景）

        深拷贝确保修改副本不影响原始对象。

        Returns:
            新的 Device 实例（完全独立）
        """
        return copy.deepcopy(self)

    def update(self, **kwargs) -> None:
        """
        批量更新属性（用于编辑设备配置）

        支持更新的字段：
        - 基本属性: name, device_type, group, location, description, tags
        - 连接配置: 通过 connection_config 子字典
        - 协议配置: 通过 protocol_config 子字典

        Args:
            **kwargs: 要更新的字段键值对
        """
        # 更新基本属性
        basic_fields = ["name", "device_type", "group", "location", "description", "tags"]
        for field_name in basic_fields:
            if field_name in kwargs:
                setattr(self, field_name, kwargs[field_name])

        # 更新连接配置
        if "connection_config" in kwargs and isinstance(kwargs["connection_config"], dict):
            for key, value in kwargs["connection_config"].items():
                if hasattr(self.connection_config, key):
                    setattr(self.connection_config, key, value)

        # 更新协议配置
        if "protocol_config" in kwargs and isinstance(kwargs["protocol_config"], dict):
            for key, value in kwargs["protocol_config"].items():
                if hasattr(self.protocol_config, key):
                    setattr(self.protocol_config, key, value)

        # 更新时间戳
        self.updated_at = time.time()

    # ==================== 字节序便捷API（兼容旧代码）====================

    def get_byte_order(self) -> ByteOrderConfig:
        """
        获取字节序配置

        Returns:
            当前 ByteOrderConfig 实例，如果未设置则返回默认值 ABCD
        """
        return self.protocol_config.byte_order or DEFAULT_BYTE_ORDER

    def set_byte_order(self, config: ByteOrderConfig) -> None:
        """
        设置字节序配置

        Args:
            config: ByteOrderConfig 实例
        """
        self.protocol_config.byte_order = config
        logger.info("设备 %s 字节序已设置为: %s", self.device_id, config.format_name)

    def has_custom_byte_order(self) -> bool:
        """是否有自定义字节序"""
        return self.protocol_config.byte_order is not None

    def clear_byte_order(self) -> None:
        """清除自定义字节序，恢复默认值"""
        self.protocol_config.byte_order = None
        logger.info("设备 %s 已清除自定义字节序", self.device_id)

    # ==================== 魔术方法 ====================

    def __repr__(self) -> str:
        """开发者友好的字符串表示"""
        return f"Device(id={self.device_id}, name={self.name}, " f"type={self.device_type}, status={self.status.name})"

    def __str__(self) -> str:
        """用户友好的字符串表示"""
        return f"[{self.device_id}] {self.name} ({self.device_type})"

    def __eq__(self, other: object) -> bool:
        """相等性比较（基于 device_id）"""
        if not isinstance(other, Device):
            return False
        return self.device_id == other.device_id

    def __hash__(self) -> int:
        """哈希值（基于 device_id，支持 set/dict 操作）"""
        return hash(self.device_id)
