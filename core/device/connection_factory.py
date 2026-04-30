# -*- coding: utf-8 -*-
"""
连接工厂 - 重构版
Connection Factory (Refactored)

从 DeviceFactory 中提取的连接创建职责。

设计原则:
- 工厂模式（封装对象创建复杂性）
- 策略模式（不同类型用不同创建逻辑）
- 开闭原则（新增协议只需添加新方法，不修改已有代码）
- 注册制（支持运行时注册自定义协议处理器）

对比旧版改进：
❌ 旧版：DeviceFactory.create_device() 直接调用 device.set_driver()/set_protocol()
✅ 新版：ConnectionFactory.create() 返回 (driver, protocol) 元组，由 DeviceConnection 组合

支持的连接类型:
- TCP: TCPIPDriver + ModbusProtocol(mode="TCP")
- RTU: SerialDriver + ModbusProtocol(mode="RTU")
- ASCII: SerialDriver + ModbusProtocol(mode="ASCII")
- OPC-UA: OpcUaClient + OpcuaProtocol (未来扩展)
- MQTT: MqttClient + MqttProtocol (未来扩展)

使用示例:
    >>> factory = ConnectionFactory()
    >>>
    >>> # 基本使用
    >>> driver, protocol = factory.create(conn_config, proto_config)
    >>>
    >>> # 注册自定义协议（插件式扩展）
    >>> factory.register_protocol_handler(
    ...     "OPC-UA",
    ...     create_opcua_connection
    ... )
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple, Type

from .device_models import ConnectionConfig, ProtocolConfig
from ..communication.base_driver import BaseDriver
from ..communication.tcp_driver import TCPDriver
from ..communication.serial_driver import SerialDriver
from ..protocols.base_protocol import BaseProtocol
from ..protocols.modbus_protocol import ModbusProtocol

logger = logging.getLogger(__name__)


# 类型别名：协议处理器函数
ProtocolHandler = Callable[
    [ConnectionConfig, ProtocolConfig],
    Tuple[BaseDriver, BaseProtocol]
]


class ConnectionFactory:
    """
    连接工厂 - 根据配置创建 Driver + Protocol 组合

    设计原则:
    ✅ 单一职责：只负责创建 Driver 和 Protocol 实例
    ✅ 开闭原则：新增协议通过 register_protocol_handler()，不修改源码
    ✅ 依赖倒置：面向接口编程（BaseDriver/BaseProtocol），不依赖具体实现
    ✅ 可测试性：可轻松 Mock，无需真实硬件

    架构位置:
        DeviceConnection
              │
              ▼
        ConnectionFactory  ◄─── 注册新协议处理器
              │
              ├──► TCPDriver + ModbusProtocol(TCP)
              ├──► SerialDriver + ModbusProtocol(RTU)
              ├──► SerialDriver + ModbusProtocol(ASCII)
              └──► [自定义协议] (运行时注册)

    扩展示例（添加 OPC-UA）:

        def create_opcua(
            conn_config: ConnectionConfig,
            proto_config: ProtocolConfig
        ) -> Tuple[OpcUaClient, OpcUaProtocol]:
            from opcua import Client
            from .opcua_protocol import OpcUaProtocol
            client = Client(f"opc.tcp://{conn_config.host}:{conn_config.port}")
            protocol = OpcUaProtocol(namespace=proto_config.namespace)
            return client, protocol

        factory.register_protocol_handler("OPC-UA", create_opcua)
    """

    def __init__(self):
        """初始化工厂，注册内置协议处理器"""
        # 协议处理器注册表 {protocol_type: handler_function}
        self._handlers: Dict[str, ProtocolHandler] = {}

        # 注册内置协议
        self._register_builtin_protocols()

    # ==================== 核心工厂方法 ====================

    def create(
        self,
        connection_config: ConnectionConfig,
        protocol_config: ProtocolConfig,
    ) -> Tuple[Optional[BaseDriver], Optional[BaseProtocol]]:
        """
        创建 (driver, protocol) 元组

        这是工厂的核心方法，根据配置自动选择对应的创建策略。

        Args:
            connection_config: 连接配置
            protocol_config: 协议配置

        Returns:
            (driver_instance, protocol_instance)
            失败时返回 (None, None)

        Raises:
            ValueError: 不支持的连接/协议类型
            ImportError: 缺少依赖库（如 opcua 库未安装）

        使用示例:
            >>> factory = ConnectionFactory()
            >>> conn_cfg = ConnectionConfig(connection_type="TCP", host="192.168.1.1")
            >>> proto_cfg = ProtocolConfig(protocol_type="MODBUS_TCP")
            >>> driver, protocol = factory.create(conn_cfg, proto_cfg)
            >>> assert driver is not None
            >>> assert protocol is not None
        """
        try:
            # 确定协议类型（优先使用 protocol_config，回退到 connection_config）
            protocol_type = self._resolve_protocol_type(
                connection_config, protocol_config
            )

            logger.debug(
                "创建连接 [%s] driver=%s protocol=%s",
                protocol_type,
                connection_config.connection_type,
                protocol_config.protocol_type
            )

            # 查找处理器
            handler = self._get_handler(protocol_type)

            if handler is None:
                raise ValueError(
                    f"不支持的协议类型: {protocol_type}。"
                    f"支持的类型: {list(self._handlers.keys())}"
                )

            # 调用处理器创建实例
            driver, protocol = handler(connection_config, protocol_config)

            if driver is None:
                logger.warning("驱动创建返回 None: %s", protocol_type)

            if protocol is None:
                logger.warning("协议创建返回 None: %s", protocol_type)

            return driver, protocol

        except Exception as e:
            logger.exception(
                "创建连接失败 [type=%s]: %s",
                protocol_config.protocol_type,
                str(e)
            )
            raise

    # ==================== 协议处理器注册 ====================

    def register_protocol_handler(
        self,
        protocol_type: str,
        handler: ProtocolHandler,
        overwrite: bool = False
    ) -> None:
        """
        注册自定义协议处理器（插件式扩展）

        这是实现开闭原则的关键方法。
        新增协议支持只需调用此方法，无需修改工厂源码。

        Args:
            protocol_type: 协议类型标识（如 "OPC-UA", "MQTT"）
            handler: 处理器函数，签名为:
                    (conn_config, proto_config) -> (driver, protocol)
            overwrite: 是否覆盖已存在的处理器（默认False）

        Raises:
            ValueError: 协议类型已存在且 overwrite=False
            TypeError: handler 不是可调用对象

        示例:
            >>> def my_custom_handler(
            ...     conn_cfg: ConnectionConfig,
            ...     proto_cfg: ProtocolConfig
            ... ) -> Tuple[BaseDriver, BaseProtocol]:
            ...     driver = MyCustomDriver(host=conn_cfg.host)
            ...     protocol = MyCustomProtocol(unit_id=proto_cfg.unit_id)
            ...     return driver, protocol
            >>>
            >>> factory.register_protocol_handler("CUSTOM", my_custom_handler)
        """
        if not callable(handler):
            raise TypeError(f"handler 必须是可调用对象，收到: {type(handler)}")

        protocol_type_upper = protocol_type.upper().strip()

        if protocol_type_upper in self._handlers and not overwrite:
            raise ValueError(
                f"协议类型 '{protocol_type}' 已存在。"
                f"如需覆盖请设置 overwrite=True"
            )

        self._handlers[protocol_type_upper] = handler

        logger.info(
            "已注册协议处理器: %s (当前共 %d 个)",
            protocol_type_upper,
            len(self._handlers)
        )

    def unregister_protocol(self, protocol_type: str) -> bool:
        """
        注销协议处理器

        Args:
            protocol_type: 要注销的协议类型

        Returns:
            是否注销成功（如果不存在则返回 False）
        """
        protocol_type_upper = protocol_type.upper().strip()

        if protocol_type_upper in self._handlers:
            del self._handlers[protocol_type_upper]
            logger.info("已注销协议处理器: %s", protocol_type_upper)
            return True

        logger.warning("尝试注销不存在的协议处理器: %s", protocol_type_upper)
        return False

    def get_registered_protocols(self) -> List[str]:
        """
        获取所有已注册的协议类型列表

        Returns:
            协议类型名称列表
        """
        return list(self._handlers.keys())

    def has_protocol(self, protocol_type: str) -> bool:
        """检查是否支持指定协议类型"""
        return protocol_type.upper().strip() in self._handlers

    def create_from_plugin(
        self,
        device_type: str,
        config: Dict,
    ) -> Optional[Any]:
        """
        通过 PluginRegistry 创建设备连接

        Step 6 新增: 支持插件体系创建连接

        Args:
            device_type: 设备类型标识 (如 "mcgs", "modbus_tcp")
            config: 设备配置字典

        Returns:
            插件创建的连接对象，未注册的设备类型返回 None
        """
        from core.foundation.plugin_registry import PluginRegistry

        plugin = PluginRegistry.get(device_type)
        if plugin is None:
            return None

        connection = plugin.create_connection(config)
        if connection is not None:
            logger.info(
                "通过插件创建连接 [type=%s, plugin=%s]",
                device_type, plugin.display_name()
            )
        return connection

    # ==================== 内置协议创建方法 ====================

    def _register_builtin_protocols(self) -> None:
        """注册内置协议处理器（TCP, RTU, ASCII）"""

        # Modbus TCP
        self.register_protocol_handler(
            "MODBUS_TCP",
            self._create_tcp_connection
        )

        # Modbus RTU
        self.register_protocol_handler(
            "MODBUS_RTU",
            self._create_rtu_connection
        )

        # Modbus ASCII
        self.register_protocol_handler(
            "MODBUS_ASCII",
            self._create_ascii_connection
        )

    @staticmethod
    def _create_tcp_connection(
        conn_config: ConnectionConfig,
        proto_config: ProtocolConfig
    ) -> Tuple[TCPDriver, ModbusProtocol]:
        """
        创建 Modbus TCP 连接

        组合: TCPDriver + ModbusProtocol(mode="TCP")

        Args:
            conn_config: 连接配置（需要 host, port）
            proto_config: 协议配置（需要 unit_id）

        Returns:
            (TCPDriver实例, ModbusProtocol实例)
        """
        logger.debug(
            "创建TCP连接 host=%s port=%d unit_id=%d",
            conn_config.host,
            conn_config.port,
            proto_config.unit_id
        )

        driver = TCPDriver(
            host=conn_config.host,
            port=conn_config.port
        )

        protocol = ModbusProtocol(
            mode="TCP",
            unit_id=proto_config.unit_id
        )

        return driver, protocol

    @staticmethod
    def _create_rtu_connection(
        conn_config: ConnectionConfig,
        proto_config: ProtocolConfig
    ) -> Tuple[SerialDriver, ModbusProtocol]:
        """
        创建 Modbus RTU 连接

        组合: SerialDriver + ModbusProtocol(mode="RTU")

        Args:
            conn_config: 连接配置（需要 serial_port, baudrate, bytesize, parity, stopbits）
            proto_config: 协议配置（需要 unit_id）

        Returns:
            (SerialDriver实例, ModbusProtocol实例)
        """
        logger.debug(
            "创建RTU连接 port=%s baudrate=%d unit_id=%d",
            conn_config.serial_port,
            conn_config.baudrate,
            proto_config.unit_id
        )

        driver = SerialDriver(
            port=conn_config.serial_port,
            baudrate=conn_config.baudrate,
            bytesize=conn_config.bytesize,
            parity=conn_config.parity,
            stopbits=conn_config.stopbits
        )

        protocol = ModbusProtocol(
            mode="RTU",
            unit_id=proto_config.unit_id
        )

        return driver, protocol

    @staticmethod
    def _create_ascii_connection(
        conn_config: ConnectionConfig,
        proto_config: ProtocolConfig
    ) -> Tuple[SerialDriver, ModbusProtocol]:
        """
        创建 Modbus ASCII 连接

        组合: SerialDriver + ModbusProtocol(mode="ASCII")

        注意: ASCII 模式通常使用不同的串口参数（7数据位，偶校验）

        Args:
            conn_config: 连接配置
            proto_config: 协议配置

        Returns:
            (SerialDriver实例, ModbusProtocol实例)
        """
        logger.debug(
            "创建ASCII连接 port=%s baudrate=%d unit_id=%d",
            conn_config.serial_port,
            conn_config.baudrate,
            proto_config.unit_id
        )

        driver = SerialDriver(
            port=conn_config.serial_port,
            baudrate=conn_config.baudrate,
            bytesize=conn_config.bytesize,  # 通常为 7
            parity=conn_config.parity,       # 通常为 "E"
            stopbits=conn_config.stopbits    # 通常为 1 或 2
        )

        protocol = ModbusProtocol(
            mode="ASCII",
            unit_id=proto_config.unit_id
        )

        return driver, protocol

    # ==================== 辅助方法 ====================

    @staticmethod
    def _resolve_protocol_type(
        connection_config: ConnectionConfig,
        protocol_config: ProtocolConfig
    ) -> str:
        """
        解析协议类型（处理多种输入格式）

        支持格式：
        - protocol_config.protocol_type: "MODBUS_TCP"
        - connection_config.connection_type: "TCP"
        - 自动映射关系: TCP→MODBUS_TCP, RTU→MODBUS_RTU

        Returns:
            标准化的协议类型（大写）
        """
        # 优先使用显式指定的协议类型
        if protocol_config.protocol_type:
            return protocol_config.protocol_type.upper().replace("-", "_")

        # 回退到连接类型并自动映射
        conn_type = connection_config.connection_type.upper()

        type_mapping = {
            "TCP": "MODBUS_TCP",
            "RTU": "MODBUS_RTU",
            "ASCII": "MODBUS_ASCII",
            "OPC-UA": "OPC_UA",
            "MQTT": "MQTT",
        }

        return type_mapping.get(conn_type, conn_type)

    def _get_handler(
        self, protocol_type: str
    ) -> Optional[ProtocolHandler]:
        """获取协议处理器（支持大小写不敏感查找）"""
        return self._handlers.get(protocol_type.upper().strip())

    # ==================== 魔术方法 ====================

    def __repr__(self) -> str:
        return (
            f"ConnectionFactory(registered_protocols="
            f"{list(self._handlers.keys())})"
        )

    def __len__(self) -> int:
        """已注册的协议数量"""
        return len(self._handlers)


# ==================== 全局默认工厂实例 =================###

# 模块级单例（可选使用）
_default_factory: Optional[ConnectionFactory] = None


def get_default_factory() -> ConnectionFactory:
    """
    获取全局默认工厂实例（懒加载单例）

    使用场景：
    - 快速原型开发
    - 简化代码（不需要手动传递 factory）
    - 向后兼容旧代码

    Returns:
        全局 ConnectionFactory 实例

    示例:
        >>> factory = get_default_factory()
        >>> driver, protocol = factory.create(conn_config, proto_config)
    """
    global _default_factory

    if _default_factory is None:
        _default_factory = ConnectionFactory()

    return _default_factory


def reset_default_factory() -> None:
    """
    重置全局默认工厂（主要用于测试）

    在单元测试中调用此方法确保测试隔离。
    """
    global _default_factory
    _default_factory = None
