# -*- coding: utf-8 -*-
"""
Device Plugins Package

设备插件体系 — 实现开闭原则:
- 新增设备类型只需创建插件类并注册
- 无需修改任何核心代码

已注册插件:
- mcgs: MCGS Modbus TCP 触摸屏
- modbus_tcp: 通用 Modbus TCP 设备
- modbus_rtu: 通用 Modbus RTU 设备
- modbus_ascii: Modbus ASCII 设备 (DMT143等)

使用方式:
    from core.plugins import register_all_plugins, MCGSPlugin

    # 注册所有内置插件
    register_all_plugins()

    # 通过 PluginRegistry 创建设备
    from core.foundation.plugin_registry import PluginRegistry
    plugin = PluginRegistry.get("mcgs")
    connection = plugin.create_connection(config)
"""

from core.foundation.plugin_registry import PluginRegistry, DevicePlugin

from .mcgs_plugin import MCGSPlugin
from .modbus_tcp_plugin import ModbusTCPPlugin
from .modbus_rtu_plugin import ModbusRTUPlugin

_all_plugins_registered = False


def register_all_plugins():
    """注册所有内置设备插件"""
    global _all_plugins_registered
    if _all_plugins_registered:
        return
    _all_plugins_registered = True

    PluginRegistry.register(MCGSPlugin())
    PluginRegistry.register(ModbusTCPPlugin())
    PluginRegistry.register(ModbusRTUPlugin())


def is_plugins_registered() -> bool:
    return _all_plugins_registered
