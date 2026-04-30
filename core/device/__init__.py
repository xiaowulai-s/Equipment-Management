# -*- coding: utf-8 -*-
"""
设备管理服务层 (v4.0 模块化架构)
Device Service Layer

模块化重构说明：
- v3.0: DeviceManager (657行上帝对象)
- v4.0: 拆分为5个独立模块 + 1个外观类

架构层次：
├── DeviceManagerFacade (统一入口，向后兼容)
│   ├── DeviceRegistry (设备CRUD)
│   ├── PollingScheduler (轮询调度)
│   ├── FaultRecoveryService (故障恢复)
│   ├── ConfigurationService (配置管理)
│   └── [GroupManager, LifecycleManager] (已有模块)
"""

from .device_factory import DeviceFactory, ProtocolType
from .device_manager import DeviceManager
from .device_manager_facade import DeviceManagerFacade
from .device_model import Device, DeviceStatus
from .device_registry import DeviceRegistry
from .device_type_manager import DeviceTypeManager
from .fault_recovery_service import FaultRecoveryService
from .configuration_service import ConfigurationService
from .polling_scheduler import PollingScheduler
from .interfaces import (
    IDeviceRegistry,
    IPollingScheduler,
    IFaultRecoveryService,
    IConfigurationService,
    IGroupManager,
    ILifecycleManager,
)
from .polling import PollPriority
from .simulator import Simulator

__all__ = [
    # 核心模型
    "Device",
    "DeviceStatus",
    "PollPriority",
    # 设备管理（向后兼容）
    "DeviceManager",  # 原版（保留）
    "DeviceManagerFacade",  # 新版外观类
    # 独立模块（可直接使用）
    "DeviceRegistry",
    "PollingScheduler",
    "FaultRecoveryService",
    "ConfigurationService",
    # 接口定义（用于依赖注入）
    "IDeviceRegistry",
    "IPollingScheduler",
    "IFaultRecoveryService",
    "IConfigurationService",
    "IGroupManager",
    "ILifecycleManager",
    # 辅助类
    "DeviceFactory",
    "ProtocolType",
    "DeviceTypeManager",
    "Simulator",
]
