# -*- coding: utf-8 -*-
"""
设备模型 - 向后兼容层（重构过渡期）
Device Model - Backward Compatibility Layer (Refactoring Transition)

⚠️ 重要说明：
此文件在重构过渡期间提供向后兼容性。

架构变更：
- ❌ 旧版：Device 是上帝对象（数据+连接+协议混杂）
- ✅ 新版：Device 纯数据模型 + DeviceConnection 控制器 + ConnectionFactory 工厂

文件变更：
- 核心代码已迁移至：
  - device_models.py: Device (dataclass), ConnectionConfig, ProtocolConfig
  - device_connection.py: DeviceConnection (连接控制器)
  - connection_factory.py: ConnectionFactory (工厂模式)

本文件内容：
- 从新模块重新导出所有公共类
- 提供兼容别名和废弃警告
- 保持旧代码无需修改即可运行

迁移时间表：
- Phase 1 (当前): 兼容层，旧代码正常工作
- Phase 2 (建议): 逐步迁移到新API
- Phase 3 (未来): 移除此文件，完全使用新模块

使用建议：
✅ 新代码请直接导入：
  from core.device.device_models import Device, DeviceStatus
  from core.device.device_connection import DeviceConnection
  from core.device.connection_factory import ConnectionFactory

❌ 避免继续使用（将在未来版本移除）：
  from core.device.device_model import Device  # 虽然可用但不推荐
"""

from __future__ import annotations

import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

# =====================================================================
# 从新模块导入核心类（重新导出）
# =====================================================================

from .device_models import (
    Device as _DeviceDataclass,
    DeviceStatus,
    ConnectionConfig,
    ProtocolConfig,
)

from .device_connection import (
    DeviceConnection,
    ConnectionError,
    ProtocolError,
    SimulatorError,
)

from .connection_factory import (
    ConnectionFactory,
    get_default_factory,
    ProtocolHandler,
)

logger = logging.getLogger(__name__)

# =====================================================================
# 废弃警告配置
# =====================================================================

_DEPRECATION_MESSAGE = """
{old_method} 已废弃，请使用新API：

旧代码:
    device.{old_method}()

新代码:
    connection = DeviceConnection(device, factory)
    connection.{new_method}()

详细文档请参考:
- core/device/device_models.py (纯数据模型)
- core/device/device_connection.py (连接控制器)
- core/device/connection_factory.py (工厂模式)
""".strip()


def _emit_deprecation_warning(old_method: str, new_method: str = "") -> None:
    """发出废弃警告"""
    warnings.warn(
        _DEPRECATION_MESSAGE.format(
            old_method=old_method,
            new_method=new_method or old_method
        ),
        DeprecationWarning,
        stacklevel=3  # 跳过此函数和调用者
    )


# =====================================================================
# 兼容类：Device (QObject 版本)
# =====================================================================

class Device(QObject):
    """
    设备模型 - 兼容层包装器

    ⚠️ 此类为向后兼容保留，新代码请使用：
    - device_models.Device (纯数据模型 dataclass)
    - device_connection.DeviceConnection (连接控制器)

    设计原理：
    外部看起来还是旧的 Device 类（QObject子类），
    但内部委托给新的 _DeviceDataclass + DeviceConnection。

    行为变化：
    ✅ 保留：get_device_id(), get_device_config(), get_status() 等
    ⚠️ 变更：connect()/disconnect() 现在内部创建 DeviceConnection
    ❌ 移除：set_driver()/set_protocol() （自动由工厂处理）

    迁移示例：

    # ===== 旧代码 =====
    device = Device("dev_001", config)
    device.set_driver(driver)
    device.set_protocol(protocol)
    device.connect()
    data = device.poll_data()

    # ===== 新代码 =====
    device = Device.from_dict(config)  # 或 Device(device_id=..., ...)
    factory = ConnectionFactory()
    connection = DeviceConnection(device, factory)
    success, error = connection.connect()
    if success:
        data = connection.poll_data()
        connection.disconnect()
    """

    # Qt 信号定义（保持与旧版一致）
    status_changed = Signal(int)
    data_received = Signal(str, dict)
    error_occurred = Signal(str)

    def __init__(
        self,
        device_id: str,
        device_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QObject] = None
    ) -> None:
        """
        初始化设备（兼容旧接口）

        Args:
            device_id: 设备ID
            device_config: 设备配置字典（可选）
            parent: Qt父对象

        注意：
        如果提供 device_config，会自动转换为新的 Device 数据模型。
        如果不提供，需要后续调用 update_config() 或从外部设置 _device_data。
        """
        super().__init__(parent)

        # 内部数据模型（新版 dataclass）
        if device_config:
            self._device_data = _DeviceDataclass.from_dict(device_config)
        else:
            # 创建最小化的空设备（用于延迟初始化场景）
            self._device_data = _DeviceDataclass(
                device_id=device_id,
                name=f"设备_{device_id}",
                device_type="unknown"
            )

        # 连接控制器（懒加载，首次 connect 时创建）
        self._connection: Optional[DeviceConnection] = None
        self._factory: Optional[ConnectionFactory] = None

        # 兼容旧属性
        self._device_id = device_id
        self._device_config = dict(device_config) if device_config else {}
        self._status = DeviceStatus.DISCONNECTED

        logger.debug(
            "创建兼容层 Device (id=%s, 建议迁移到新API)",
            device_id
        )

    # ==================== 属性访问器（保持旧接口）====================

    @property
    def device_data(self) -> _DeviceDataclass:
        """获取内部的数据模型实例（新API）"""
        return self._device_data

    @property
    def connection(self) -> Optional[DeviceConnection]:
        """获取内部的连接控制器实例（新API）"""
        return self._connection

    def get_device_id(self) -> str:
        """获取设备ID（兼容旧接口）"""
        return self._device_data.device_id

    def get_device_config(self) -> Dict[str, Any]:
        """获取设备配置字典（兼容旧接口，返回扁平化格式）"""
        return self._device_data.to_dict()

    def get_status(self) -> int:
        """获取状态值（兼容旧接口）"""
        return int(self._device_data.status)

    def get_current_data(self) -> Dict[str, Any]:
        """获取当前数据（兼容旧接口）"""
        if self._connection:
            return self._connection.get_current_data()
        return {}

    def is_using_simulator(self) -> bool:
        """是否使用模拟器（兼容旧接口）"""
        return self._device_data.is_using_simulator

    def get_last_connection_error(self) -> str:
        """获取最后的连接错误（兼容旧接口）"""
        if self._connection:
            return self._connection.get_last_connection_error()
        return ""

    def get_driver(self):
        """获取驱动实例（兼容旧接口）"""
        if self._connection:
            return self._connection.driver
        return None

    # ==================== 配置管理 ====================

    def update_config(self, device_config: Dict[str, Any]) -> None:
        """
        更新设备配置（兼容旧接口）

        会同时更新内部数据模型和连接控制器（如果存在）。
        """
        self._device_config = dict(device_config)
        self._device_data = _DeviceDataclass.from_dict(device_config)

        # 同步更新连接控制器
        if self._connection:
            self._connection.update_device_config(self._device_data)

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证设备配置（兼容旧接口）

        委托给新的 _DeviceDataclass.validate_config()
        """
        return _DeviceDataclass.validate_config(config)

    # ==================== 连接方法（兼容层，内部委托给 DeviceConnection）====================

    def set_driver(self, driver) -> None:
        """
        设置驱动（已废弃）

        ⚠️ 此方法在新架构中不再需要。
        Driver 现在由 ConnectionFactory 自动创建。

        如果调用此方法，会发出废弃警告并忽略操作。
        """
        _emit_deprecation_warning("set_driver()", "使用 ConnectionFactory")
        logger.warning(
            "Device.set_driver() 已废弃，Driver 由 ConnectionFactory 自动创建"
        )
        # 不执行任何操作（保持兼容但无效）

    def set_protocol(self, protocol) -> None:
        """
        设置协议（已废弃）

        ⚠️ 此方法在新架构中不再需要。
        Protocol 现在由 ConnectionFactory 自动创建。

        如果调用此方法，会发出废弃警告并忽略操作。
        """
        _emit_deprecation_warning("set_protocol()", "使用 ConnectionFactory")
        logger.warning(
            "Device.set_protocol() 已废弃，Protocol 由 ConnectionFactory 自动创建"
        )
        # 不执行任何操作（保持兼容但无效）

    def connect(self) -> bool:
        """
        连接设备（兼容旧接口）

        内部实现：
        1. 创建 ConnectionFactory（如果不存在）
        2. 创建 DeviceConnection（如果不存在）
        3. 委托给 DeviceConnection.connect()
        4. 连接信号到本对象的信号

        Returns:
            是否连接成功
        """
        try:
            logger.info(
                "Device.connect() [兼容层] id=%s",
                self._device_data.device_id
            )

            # 懒加载工厂
            if self._factory is None:
                self._factory = ConnectionFactory()

            # 创建或更新连接控制器
            if self._connection is None:
                self._connection = DeviceConnection(
                    device=self._device_data,
                    factory=self._factory,
                    parent=self
                )
                # 连接信号
                self._connection.status_changed.connect(self.status_changed)
                self._connection.data_received.connect(self.data_received)
                self._connection.error_occurred.connect(self.error_occurred)

            # 委托连接
            success, error = self._connection.connect()

            # 同步状态
            self._status = self._device_data.status

            return success

        except Exception as e:
            logger.exception("Device.connect() 异常: %s", str(e))
            self.error_occurred.emit(str(e))
            return False

    def disconnect(self) -> bool:
        """
        断开连接（兼容旧接口）

        委托给 DeviceConnection.disconnect()
        """
        try:
            if self._connection:
                result = self._connection.disconnect()
                self._status = DeviceStatus.DISCONNECTED
                return result

            self._status = DeviceStatus.DISCONNECTED
            return True

        except Exception as e:
            logger.exception("Device.disconnect() 异常: %s", str(e))
            return False

    # ==================== 数据操作方法（兼容层）====================

    def poll_data(self) -> Dict[str, Any]:
        """
        轮询数据（兼容旧接口）

        委托给 DeviceConnection.poll_data()
        """
        if self._connection:
            return self._connection.poll_data()
        return {}

    def read_registers(self, address: int, count: int) -> Optional[List[int]]:
        """读取寄存器（兼容旧接口）"""
        if self._connection:
            return self._connection.read_registers(address, count)
        return None

    def write_register(self, address: int, value: int) -> bool:
        """写入寄存器（兼容旧接口）"""
        if self._connection:
            return self._connection.write_register(address, value)
        return False

    def write_registers(self, address: int, values: List[int]) -> bool:
        """批量写入寄存器（兼容旧接口）"""
        if self._connection:
            return self._connection.write_registers(address, values)
        return False

    def send_raw_data(self, data: bytes) -> bool:
        """发送原始数据（兼容旧接口）"""
        if self._connection:
            return self._connection.send_raw_data(data)
        return False

    # ==================== 字节序API（兼容层）====================

    def set_byte_order(self, config) -> None:
        """设置字节序（兼容旧接口）"""
        self._device_data.set_byte_order(config)
        if self._connection:
            self._connection.set_byte_order(config)

    def get_byte_order(self):
        """获取字节序（兼容旧接口）"""
        return self._device_data.get_byte_order()

    def has_custom_byte_order(self) -> bool:
        """是否有自定义字节序（兼容旧接口）"""
        return self._device_data.has_custom_byte_order()

    def clear_byte_order(self) -> None:
        """清除自定义字节序（兼容旧接口）"""
        self._device_data.clear_byte_order()
        if self._connection:
            self._connection.clear_byte_order()

    # ==================== 兼容属性（旧代码可能直接访问）====================

    @property
    def _config(self) -> Dict[str, Any]:
        """兼容旧代码的 _config 属性"""
        return self._device_config

    @_config.setter
    def _config(self, value: Dict[str, Any]) -> None:
        """兼容旧代码的 _config 设置器"""
        self._device_config = dict(value)
        self._device_data = _DeviceDataclass.from_dict(value)


# =====================================================================
# 导出符号（保持旧的导入路径有效）
# =====================================================================

# 新类（推荐使用）
__all__ = [
    # 核心类（从新模块重新导出）
    'DeviceStatus',
    'ConnectionConfig',
    'ProtocolConfig',
    'Device',              # 兼容层包装器
    'DeviceConnection',    # 连接控制器
    'ConnectionFactory',   # 工厂
    'ConnectionError',
    'ProtocolError',
    'SimulatorError',

    # 辅助函数
    'get_default_factory',
    'ProtocolHandler',
]

# 便捷别名（完全等价）
DeviceModel = Device  # 旧名称别名
_Device = _DeviceDataclass  # 内部使用
