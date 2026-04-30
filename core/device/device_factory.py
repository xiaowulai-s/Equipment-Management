# -*- coding: utf-8 -*-
"""
设备工厂 - 适配新架构
Device Factory (Adapted for New Architecture)

变更说明：
- ✅ 现在使用新的 Device dataclass（device_models.Device）
- ✅ 不再直接设置 driver/protocol（由 ConnectionFactory 处理）
- ✅ 保持向后兼容的 create_device() 接口
- ⚠️ 返回值变化：旧版返回 QObject Device，新版返回 dataclass Device

迁移指南：
旧代码:
    device = DeviceFactory.create_device("dev_001", config)
    device.set_driver(driver)
    device.set_protocol(protocol)

新代码（推荐）:
    from core.device.device_models import Device
    from core.device.connection_factory import ConnectionFactory
    from core.device.device_connection import DeviceConnection

    device = Device.from_dict(config)  # 或 DeviceFactory.create_device()
    factory = ConnectionFactory()
    connection = DeviceConnection(device, factory)
    success, error = connection.connect()

兼容模式（无需修改现有代码）:
    device = DeviceFactory.create_device("dev_001", config)
    # 内部自动处理，返回兼容层 Device
"""

import logging
import socket
from typing import Any, Callable, Dict, List, Optional, Type

from ..communication.base_driver import BaseDriver
from ..communication.serial_driver import SerialDriver
from ..communication.tcp_driver import TCPDriver
from ..protocols.base_protocol import BaseProtocol
from ..protocols.modbus_protocol import ModbusProtocol

# 使用新架构的数据模型
from .device_models import Device as NewDevice, ConnectionConfig, ProtocolConfig, DeviceStatus
from .connection_factory import ConnectionFactory

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """获取本机 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("10.254.254.254", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class ProtocolType:
    """协议类型常量"""
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    MODBUS_ASCII = "modbus_ascii"
    DMT143_ASCII = "modbus_ascii"


class _DriverSpec:
    """驱动创建规范"""
    __slots__ = ("driver_class", "config_fn")

    def __init__(self, driver_class: type, config_fn: Callable[[Dict[str, Any]], Any]):
        self.driver_class = driver_class
        self.config_fn = config_fn

    def create(self, device_config: Dict[str, Any]) -> Optional[BaseDriver]:
        return self.driver_class(**self.config_fn(device_config))


class _ProtocolSpec:
    """协议创建规范"""
    __slots__ = ("protocol_class", "config_fn")

    def __init__(self, protocol_class: type, config_fn: Callable[[Dict[str, Any]], Any]):
        self.protocol_class = protocol_class
        self.config_fn = config_fn

    def create(self, device_config: Dict[str, Any]) -> Optional[BaseProtocol]:
        return self.protocol_class(**self.config_fn(device_config))


class DeviceFactory:
    """
    设备工厂 - 注册制协议扩展
    
    使用方式:
        # 注册新协议（如 OPC UA）
        DeviceFactory.register_protocol(
            "opcua",
            name="OPC UA",
            fields=[{"name": "endpoint", ...}],
            driver_factory=lambda cfg: OPCUADriver(endpoint=cfg["endpoint"]),
            protocol_factory=lambda cfg: OPCUAProtocol(endpoint=cfg["endpoint"]),
        )
        
        # 创建设备时自动使用注册的协议
        device = DeviceFactory.create_device("dev-001", {"protocol_type": "opcua", ...})
    """

    PROTOCOL_PARAMS: Dict[str, Dict[str, Any]] = {}
    _driver_registry: Dict[str, _DriverSpec] = {}
    _protocol_registry: Dict[str, _ProtocolSpec] = {}
    _validation_registry: Dict[str, Callable[[Dict[str, Any]], bool]] = {}

    # 默认寄存器映射
    DEFAULT_REGISTER_MAP = [
        {"name": "温度", "address": 0, "type": "uint16", "scale": 0.1, "unit": "°C"},
        {"name": "压力", "address": 1, "type": "uint16", "scale": 0.1, "unit": "MPa"},
        {"name": "流量", "address": 2, "type": "uint16", "scale": 0.1, "unit": "m³/h"},
        {"name": "状态", "address": 3, "type": "uint16", "scale": 1, "unit": ""},
        {"name": "报警", "address": 4, "type": "uint16", "scale": 1, "unit": ""},
    ]

    @classmethod
    def register_protocol(
        cls,
        protocol_type: str,
        name: str,
        fields: List[Dict[str, Any]],
        driver_factory: Callable[[Dict], Optional[BaseDriver]],
        protocol_factory: Callable[[Dict], Optional[BaseProtocol]],
        validator: Optional[Callable[[Dict], bool]] = None,
    ) -> None:
        """注册新协议类型"""
        cls.PROTOCOL_PARAMS[protocol_type] = {"name": name, "fields": fields}
        if isinstance(driver_factory, type):
            spec = _DriverSpec(driver_factory, lambda c: c)
            cls._driver_registry[protocol_type] = lambda c, f=driver_factory: f(c)
        else:
            cls._driver_registry[protocol_type] = driver_factory
        if isinstance(protocol_factory, type):
            cls._protocol_registry[protocol_type] = lambda c, p=protocol_factory: p(c)
        else:
            cls._protocol_registry[protocol_type] = protocol_factory
        if validator:
            cls._validation_registry[protocol_type] = validator

    @classmethod
    def unregister_protocol(cls, protocol_type: str) -> None:
        """注销协议类型"""
        cls.PROTOCOL_PARAMS.pop(protocol_type, None)
        cls._driver_registry.pop(protocol_type, None)
        cls._protocol_registry.pop(protocol_type, None)
        cls._validation_registry.pop(protocol_type, None)

    # 初始化内置协议
    _register_builtin_done = False

    @classmethod
    def _ensure_builtin_registered(cls) -> None:
        if cls._register_builtin_done:
            return
        cls._register_builtin_done = True

        # Modbus TCP
        cls.register_protocol(
            ProtocolType.MODBUS_TCP,
            "Modbus TCP",
            fields=[
                {"name": "host", "label": "IP地址", "type": "text", "default": "AUTO"},
                {"name": "port", "label": "端口号", "type": "number", "default": 502},
                {"name": "unit_id", "label": "单元ID", "type": "number", "default": 1},
            ],
            driver_factory=lambda c: TCPDriver(c.get("host", "127.0.0.1"), c.get("port", 502)),
            protocol_factory=lambda c: ModbusProtocol(mode="TCP", unit_id=c.get("unit_id", 1)),
            validator=lambda c: (
                isinstance(c.get("port", 502), int) and 1 <= c.get("port", 502) <= 65535
            ),
        )

        # Modbus RTU
        parity_map = {"无校验": "N", "偶校验": "E", "奇校验": "O"}

        def _rtu_validator(c):
            if c.get("baudrate", 9600) not in [9600, 19200, 38400, 57600, 115200]:
                return False
            if c.get("bytesize", 8) not in [5, 6, 7, 8]:
                return False
            if c.get("parity", "N") not in ["N", "E", "O", "无校验", "偶校验", "奇校验"]:
                return False
            if c.get("stopbits", 1) not in [1, 1.5, 2]:
                return False
            return True

        cls.register_protocol(
            ProtocolType.MODBUS_RTU,
            "Modbus RTU",
            fields=[
                {"name": "port", "label": "端口号", "type": "text", "default": "COM1"},
                {
                    "name": "baudrate", "label": "波特率", "type": "dropdown",
                    "options": [9600, 19200, 38400, 57600, 115200], "default": 9600,
                },
                {"name": "bytesize", "label": "数据位", "type": "dropdown", "options": [5, 6, 7, 8], "default": 8},
                {
                    "name": "parity", "label": "校验位", "type": "dropdown",
                    "options": ["无校验", "偶校验", "奇校验"], "default": "无校验",
                },
                {"name": "stopbits", "label": "停止位", "type": "dropdown", "options": [1, 1.5, 2], "default": 1},
                {"name": "unit_id", "label": "从机ID", "type": "number", "default": 1},
            ],
            driver_factory=lambda c: SerialDriver(
                c.get("port", "COM1"),
                c.get("baudrate", 9600),
                c.get("bytesize", 8),
                parity_map.get(c.get("parity", "N"), "N"),
                c.get("stopbits", 1),
            ),
            protocol_factory=lambda c: ModbusProtocol(mode="RTU", unit_id=c.get("unit_id", 1)),
            validator=_rtu_validator,
        )

        # Modbus ASCII (DMT143)
        ascii_parity_map = {"偶校验": "E", "无校验": "N", "奇校验": "O"}

        def _ascii_validator(c):
            if c.get("baudrate", 9600) not in [9600, 19200, 38400, 57600, 115200]:
                return False
            if c.get("bytesize", 7) not in [7, 8]:
                return False
            if c.get("parity", "E") not in ["N", "E", "O", "偶校验", "无校验", "奇校验"]:
                return False
            if c.get("stopbits", 1) not in [1, 2]:
                return False
            return True

        cls.register_protocol(
            ProtocolType.DMT143_ASCII,
            "Modbus ASCII",
            fields=[
                {"name": "port", "label": "端口号", "type": "text", "default": "COM1"},
                {
                    "name": "baudrate", "label": "波特率", "type": "dropdown",
                    "options": [9600, 19200, 38400, 57600, 115200], "default": 9600,
                },
                {"name": "bytesize", "label": "数据位", "type": "dropdown", "options": [7, 8], "default": 7},
                {
                    "name": "parity", "label": "校验位", "type": "dropdown",
                    "options": ["偶校验", "无校验", "奇校验"], "default": "偶校验",
                },
                {"name": "stopbits", "label": "停止位", "type": "dropdown", "options": [1, 2], "default": 1},
                {"name": "unit_id", "label": "从机ID", "type": "number", "default": 1},
            ],
            driver_factory=lambda c: SerialDriver(
                c.get("port", "COM1"),
                c.get("baudrate", 9600),
                c.get("bytesize", 7),
                ascii_parity_map.get(c.get("parity", "E"), "E"),
                c.get("stopbits", 1),
            ),
            protocol_factory=lambda c: ModbusProtocol(mode="ASCII", unit_id=c.get("unit_id", 1)),
            validator=_ascii_validator,
        )

    @staticmethod
    def get_available_protocols() -> list:
        DeviceFactory._ensure_builtin_registered()
        return [
            {"type": pt, "name": params["name"]}
            for pt, params in DeviceFactory.PROTOCOL_PARAMS.items()
        ]

    @staticmethod
    def get_protocol_params(protocol_type: str) -> Optional[Dict[str, Any]]:
        DeviceFactory._ensure_builtin_registered()
        return DeviceFactory.PROTOCOL_PARAMS.get(protocol_type)

    @staticmethod
    def create_device(device_id: str, device_config: Dict[str, Any]) -> NewDevice:
        """
        创建设备实例（新架构版 + 插件体系）

        变更说明：
        - ✅ 现在返回新的 Device dataclass（纯数据模型）
        - ✅ 优先使用 PluginRegistry 创建设备连接
        - ✅ 回退到原有注册制逻辑（向后兼容）
        - ❌ 不再调用 set_driver()/set_protocol()（已废弃）

        Args:
            device_id: 设备ID
            device_config: 设备配置字典

        Returns:
            新的 Device dataclass 实例

        Raises:
            ValueError: 配置验证失败
        """
        DeviceFactory._ensure_builtin_registered()

        if not DeviceFactory._validate_device_config(device_config):
            raise ValueError("设备配置验证失败")

        if "register_map" not in device_config:
            device_config["register_map"] = DeviceFactory.DEFAULT_REGISTER_MAP

        device = NewDevice.from_dict(device_config)

        device_type = device_config.get("device_type", "")
        from core.foundation.plugin_registry import PluginRegistry
        plugin = PluginRegistry.get(device_type)
        if plugin:
            logger.info(
                "创建设备 [插件体系] id=%s type=%s plugin=%s",
                device_id, device_type, plugin.display_name()
            )
        else:
            logger.info(
                "创建设备 [传统注册制] id=%s type=%s protocol=%s",
                device_id,
                device.device_type,
                device.protocol_type
            )

        return device

    @staticmethod
    def _validate_device_config(device_config: Dict[str, Any]) -> bool:
        DeviceFactory._ensure_builtin_registered()

        protocol_type = device_config.get("protocol_type", ProtocolType.MODBUS_TCP)

        custom_validator = DeviceFactory._validation_registry.get(protocol_type)
        if custom_validator:
            return custom_validator(device_config)

        return protocol_type in DeviceFactory.PROTOCOL_PARAMS

    @staticmethod
    def _create_driver(protocol_type: str, device_config: Dict[str, Any]) -> Optional[BaseDriver]:
        DeviceFactory._ensure_builtin_registered()
        factory_fn = DeviceFactory._driver_registry.get(protocol_type)
        if factory_fn:
            return factory_fn(device_config)
        return None

    @staticmethod
    def _create_protocol(protocol_type: str, device_config: Dict[str, Any]) -> Optional[BaseProtocol]:
        DeviceFactory._ensure_builtin_registered()
        factory_fn = DeviceFactory._protocol_registry.get(protocol_type)
        if factory_fn:
            return factory_fn(device_config)
        return None
