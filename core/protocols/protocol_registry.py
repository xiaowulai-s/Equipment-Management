# -*- coding: utf-8 -*-
"""
协议插件注册表
Protocol Plugin Registry - 支持运行时注册新协议，无需修改 DeviceFactory
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type

from core.utils.logger import get_logger

logger = get_logger(__name__)


class ProtocolPlugin:
    """协议插件描述符"""

    def __init__(
        self,
        protocol_type: str,
        name: str,
        driver_factory: Callable[[Dict[str, Any]], Optional[Any]],
        protocol_factory: Callable[[Dict[str, Any]], Optional[Any]],
        config_validator: Optional[Callable[[Dict[str, Any]], bool]] = None,
        param_fields: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.protocol_type = protocol_type
        self.name = name
        self.driver_factory = driver_factory
        self.protocol_factory = protocol_factory
        self.config_validator = config_validator
        self.param_fields = param_fields or []


class ProtocolRegistry:
    """
    协议插件注册表

    使用方式:
        registry = ProtocolRegistry.instance()
        registry.register(ProtocolPlugin(
            protocol_type="opcua",
            name="OPC UA",
            driver_factory=lambda cfg: OPCUADriver(cfg),
            protocol_factory=lambda cfg: OPCUAProtocol(cfg),
            config_validator=lambda cfg: "endpoint" in cfg,
            param_fields=[{"name": "endpoint", "label": "端点", "type": "text", "default": "opc.tcp://localhost:4840"}],
        ))
    """

    _instance: Optional["ProtocolRegistry"] = None

    def __init__(self) -> None:
        self._plugins: Dict[str, ProtocolPlugin] = {}

    @classmethod
    def instance(cls) -> "ProtocolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, plugin: ProtocolPlugin) -> None:
        self._plugins[plugin.protocol_type] = plugin
        logger.info("协议插件已注册: %s (%s)", plugin.name, plugin.protocol_type)

    def unregister(self, protocol_type: str) -> None:
        if protocol_type in self._plugins:
            del self._plugins[protocol_type]
            logger.info("协议插件已注销: %s", protocol_type)

    def get_plugin(self, protocol_type: str) -> Optional[ProtocolPlugin]:
        return self._plugins.get(protocol_type)

    def get_all_plugins(self) -> Dict[str, ProtocolPlugin]:
        return dict(self._plugins)

    def create_driver(self, protocol_type: str, config: Dict[str, Any]) -> Optional[Any]:
        plugin = self._plugins.get(protocol_type)
        if plugin:
            return plugin.driver_factory(config)
        return None

    def create_protocol(self, protocol_type: str, config: Dict[str, Any]) -> Optional[Any]:
        plugin = self._plugins.get(protocol_type)
        if plugin:
            return plugin.protocol_factory(config)
        return None

    def validate_config(self, protocol_type: str, config: Dict[str, Any]) -> bool:
        plugin = self._plugins.get(protocol_type)
        if plugin and plugin.config_validator:
            return plugin.config_validator(config)
        return protocol_type in self._plugins

    def get_available_protocols(self) -> List[Dict[str, str]]:
        return [{"type": pt, "name": p.name} for pt, p in self._plugins.items()]

    def get_protocol_params(self, protocol_type: str) -> Optional[Dict[str, Any]]:
        plugin = self._plugins.get(protocol_type)
        if plugin:
            return {"name": plugin.name, "fields": plugin.param_fields}
        return None
