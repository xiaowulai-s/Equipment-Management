# -*- coding: utf-8 -*-
"""
PluginRegistry - 设备插件注册表

支持运行时注册/发现设备插件，实现开闭原则:
- 新增设备类型只需创建插件类并注册
- 无需修改任何核心代码

使用方式:
    # 注册插件
    PluginRegistry.register(MCGSPlugin())

    # 获取插件
    plugin = PluginRegistry.get("mcgs")

    # 创建连接
    connection = plugin.create_connection(config)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DevicePlugin(ABC):

    @abstractmethod
    def device_type(self) -> str: ...

    @abstractmethod
    def display_name(self) -> str: ...

    @abstractmethod
    def create_connection(self, config: Dict) -> Any: ...

    @abstractmethod
    def create_parser(self, config: Dict) -> Any: ...

    @abstractmethod
    def default_config(self) -> Dict: ...

    @abstractmethod
    def validate_config(self, config: Dict) -> Tuple[bool, str]: ...


class PluginRegistry:
    _plugins: Dict[str, DevicePlugin] = {}

    @classmethod
    def register(cls, plugin: DevicePlugin) -> None:
        dtype = plugin.device_type()
        cls._plugins[dtype] = plugin
        logger.info("设备插件已注册: %s (%s)", dtype, plugin.display_name())

    @classmethod
    def get(cls, device_type: str) -> Optional[DevicePlugin]:
        return cls._plugins.get(device_type)

    @classmethod
    def list_types(cls) -> List[str]:
        return list(cls._plugins.keys())

    @classmethod
    def list_plugins(cls) -> List[DevicePlugin]:
        return list(cls._plugins.values())

    @classmethod
    def is_registered(cls, device_type: str) -> bool:
        return device_type in cls._plugins

    @classmethod
    def clear(cls) -> None:
        cls._plugins.clear()
