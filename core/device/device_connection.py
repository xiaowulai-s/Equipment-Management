# -*- coding: utf-8 -*-
"""
设备连接控制器 - 重构版（v3.2 配置驱动轮询）
Device Connection Controller (Refactored)

从 Device 上帝对象中提取的连接管理职责。

设计原则:
- 组合模式（has-a Device, not is-a Device）
- 控制反转（通过 Factory 获取 Driver 和 Protocol）
- 观察者模式（信号通知状态变化）
- 策略模式（不同协议类型的连接策略）
- 配置驱动轮询（基于 RegisterPointConfig 自动分组批量读取）

v3.2 新增特性:
✅ 支持配置驱动的智能轮询（按功能码分组 + 连续地址合并）
✅ 线圈写操作安全网关（require_confirm 机制）
✅ 完整的写操作审计日志
✅ 与 RegisterPointConfig 数据类型深度集成

职责范围:
✓ 建立/断开连接
✓ 管理 driver 和 protocol 生命周期
✓ 执行数据轮询 (poll_data) - 配置驱动版本
✓ 寄存器读写操作
✓ 线圈写操作（带确认机制）
✓ 连接健康检查和错误处理
✓ 模拟器管理

排除范围:
✗ 设备属性存储 → Device (dataclass)
✗ 配置验证 → Device.validate()
✗ 数据持久化 → DatabaseManager
✗ 轮询调度 → PollingScheduler

架构关系:
    Device (dataclass) ◄─── DeviceConnection (controller)
                              │
                              ├──► ConnectionFactory (创建 driver/protocol)
                              │
                              ├──► BaseDriver (通信层)
                              │       └── TCPDriver / SerialDriver
                              │
                              └──► BaseProtocol (协议层)
                                      └── ModbusProtocol

使用示例:
    >>> device = Device.from_dict(config)
    >>> factory = ConnectionFactory()
    >>> conn = DeviceConnection(device, factory)
    >>> success, error = conn.connect()
    >>> if success:
    ...     data = conn.poll_data()  # 自动按FC分组批量读取
    ...     conn.write_coil("进水阀", True, require_confirm=True)  # 带确认的写操作
    ...     conn.disconnect()
"""

from __future__ import annotations

import logging
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from .device_models import Device, DeviceStatus
from ..communication.base_driver import BaseDriver
from ..protocols.base_protocol import BaseProtocol
from ..protocols.byte_order_config import ByteOrderConfig, DEFAULT_BYTE_ORDER
from ..enums.data_type_enum import RegisterDataType, RegisterPointConfig
from .simulator import Simulator

logger = logging.getLogger(__name__)


class DeviceConnection(QObject):
    """
    设备连接控制器 - 管理通信生命周期（v3.2 配置驱动版本）

    设计原则:
    ✅ 单一职责：只负责连接管理和数据通信
    ✅ 组合优于继承：组合 Device 对象，而非继承
    ✅ 依赖注入：通过 Factory 注入 Driver/Protocol
    ✅ 观察者模式：使用 Qt Signal 通知状态变化
    ✅ 错误隔离：连接错误不影响数据模型
    ✅ 配置驱动：基于 RegisterPointConfig 智能轮询

    生命周期:
        create → connect → [poll_data / read/write] → disconnect → destroy

    信号 (Signals):
        connected(str): 连接成功，参数为 device_id
        disconnected(str): 断开完成，参数为 device_id
        connection_error(str, str): 连接错误，参数为 (device_id, error_msg)
        data_received(str, dict): 收到数据，参数为 (device_id, data)
        status_changed(int): 状态变化，参数为 DeviceStatus 值
        write_confirmation_required(str, int, bool, object): 写操作需要确认
            参数: (param_name, address, value, RegisterPointConfig)
        coil_written(str, int, bool): 线圈写入完成
            参数: (param_name, address, success)
    """

    # ==================== Qt 信号定义 ====================

    connected = Signal(str)                    # device_id
    disconnected = Signal(str)                 # device_id
    connection_error = Signal(str, str)        # device_id, error_message
    data_received = Signal(str, dict)          # device_id, data_dict
    status_changed = Signal(int)               # DeviceStatus value

    error_occurred = Signal(str)               # error_message (兼容旧接口)

    # v3.2 新增信号：写操作相关
    write_confirmation_required = Signal(str, int, bool, object)  # param_name, address, value, config
    coil_written = Signal(str, int, bool)      # param_name, address, success

    def __init__(
        self,
        device: Device,
        factory: 'ConnectionFactory',
        parent: Optional[QObject] = None
    ) -> None:
        """
        初始化设备连接控制器（v3.2 配置驱动版本）

        Args:
            device: 设备数据模型（只读引用，不修改原始对象）
            factory: 连接工厂（用于创建 Driver 和 Protocol）
            parent: Qt 父对象
        """
        super().__init__(parent)

        # 只读引用设备数据（不持有所有权）
        self._device = device

        # 工厂引用（用于延迟创建 driver/protocol）
        self._factory = factory

        # 运行时组件（懒加载，首次 connect 时创建）
        self._driver: Optional[BaseDriver] = None
        self._protocol: Optional[BaseProtocol] = None
        self._simulator: Optional[Simulator] = None

        # 连接状态
        self._is_connected = False
        self._connection_error = ""

        # 当前数据缓存
        self._current_data: Dict[str, Any] = {}

        # v3.2 新增：寄存器点配置列表（从 Device 配置中解析）
        # 类型: List[RegisterPointConfig]
        # 用于配置驱动的智能轮询和写操作
        self._register_points: List[RegisterPointConfig] = []
        self._parse_register_points_from_config()

        # 如果配置了模拟器，初始化模拟器
        if device.is_using_simulator:
            self._init_simulator()

    # ==================== 属性访问器 ====================

    @property
    def device(self) -> Device:
        """获取关联的设备数据模型（只读）"""
        return self._device

    @property
    def device_id(self) -> str:
        """获取设备ID（便捷属性）"""
        return self._device.device_id

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected

    @property
    def driver(self) -> Optional[BaseDriver]:
        """获取当前驱动实例（用于高级操作）"""
        return self._driver

    @property
    def protocol(self) -> Optional[BaseProtocol]:
        """获取当前协议实例（用于高级操作）"""
        return self._protocol

    def get_status(self) -> int:
        """获取当前状态值（兼容旧接口）"""
        if self._is_connected:
            return int(DeviceStatus.CONNECTED)
        return int(DeviceStatus.DISCONNECTED)

    def get_last_connection_error(self) -> str:
        """获取最后的连接错误信息"""
        return self._connection_error

    def get_current_data(self) -> Dict[str, Any]:
        """获取当前缓存的设备数据"""
        return dict(self._current_data)

    def is_using_simulator(self) -> bool:
        """是否使用模拟器"""
        return self._device.is_using_simulator and self._simulator is not None

    @property
    def register_points(self) -> List[RegisterPointConfig]:
        """获取寄存器点配置列表（v3.2 新增）"""
        return list(self._register_points)

    def get_register_point_by_name(self, name: str) -> Optional[RegisterPointConfig]:
        """
        根据参数名称查找寄存器点配置（v3.2 新增）

        Args:
            name: 参数名称（如 "进水阀"、"温度传感器"）

        Returns:
            RegisterPointConfig 实例，未找到返回 None
        """
        for rp in self._register_points:
            if rp.name == name:
                return rp
        return None

    # ==================== 核心方法：连接管理 ====================

    def connect(self) -> Tuple[bool, str]:
        """
        建立设备连接（重构后的核心方法）

        流程（清晰的三步走）：
        1. 从 Device 读取配置（只读，不修改）
        2. 通过 Factory 创建 Driver + Protocol 组合
        3. 执行连接并初始化协议

        对比旧版改进：
        ❌ 旧版：在 Device.connect() 内部硬编码 if/elif 判断协议类型
        ✅ 新版：委托给 ConnectionFactory，支持开闭原则

        Returns:
            (success, error_message)
            - success: 是否连接成功
            - error_message: 失败时的错误信息（成功时为空字符串）
        """
        try:
            # 重置错误信息
            self._connection_error = ""

            logger.info(
                "正在连接设备 %s [%s://%s:%s]",
                self.device_id,
                self._device.connection_type,
                self._device.connection_config.host,
                self._device.connection_config.port
            )

            # ===== 步骤1: 检查是否使用模拟器 =====
            if self._device.is_using_simulator:
                return self._connect_simulator()

            # ===== 步骤2: 从Device读取配置（只读）=====
            conn_config = self._device.connection_config
            proto_config = self._device.protocol_config

            # 更新状态为"正在连接"
            self._update_status(DeviceStatus.CONNECTING)

            # ===== 步骤3: 通过Factory创建Driver+Protocol =====
            self._driver, self._protocol = self._factory.create(
                conn_config, proto_config
            )

            if self._driver is None or self._protocol is None:
                raise RuntimeError("工厂未能创建驱动或协议实例")

            # 连接驱动的错误信号到本对象的处理器
            self._driver.error_occurred.connect(self._on_driver_error)

            # 配置协议层
            self._protocol.set_driver(self._driver)
            self._protocol.set_register_map(proto_config.register_map)
            self._protocol.data_updated.connect(self._on_protocol_data)
            self._protocol.error_occurred.connect(self._on_protocol_error)

            # 同步字节序配置到协议层
            if proto_config.byte_order:
                if hasattr(self._protocol, 'set_byte_order'):
                    self._protocol.set_byte_order(proto_config.byte_order)

            # ===== 步骤4: 执行实际连接 =====
            if not self._driver.connect():
                raise ConnectionError(f"驱动连接失败: {conn_config.connection_type}")

            # 初始化协议
            if not self._protocol.initialize():
                self._driver.disconnect()
                raise ProtocolError("协议初始化失败")

            # ===== 步骤5: 更新状态，发射信号 =====
            self._is_connected = True
            self._update_status(DeviceStatus.CONNECTED)
            self.connected.emit(self.device_id)

            logger.info("设备 %s 连接成功", self.device_id)
            return True, ""

        except Exception as e:
            error_msg = f"连接异常: {str(e)}"
            logger.exception("设备 %s 连接失败", self.device_id)

            self._connection_error = error_msg
            self._update_status(DeviceStatus.ERROR)
            self.connection_error.emit(self.device_id, error_msg)
            self.error_occurred.emit(error_msg)  # 兼容旧信号

            return False, error_msg

    def connect_async(self, callback=None) -> None:
        """
        异步连接设备（不阻塞调用线程）

        Args:
            callback: 可选回调函数，签名为 callback(success: bool, error_msg: str)
        """
        from PySide6.QtCore import QThreadPool, QRunnable

        conn = self

        class _AsyncConnectTask(QRunnable):
            def __init__(self, connection, cb):
                super().__init__()
                self._conn = connection
                self._cb = cb
                self.setAutoDelete(True)

            def run(self):
                success, error_msg = self._conn.connect()
                if self._cb:
                    self._cb(success, error_msg)

        QThreadPool.globalInstance().start(_AsyncConnectTask(conn, callback))

    def _connect_simulator(self) -> Tuple[bool, str]:
        """连接模拟器（内部方法）"""
        try:
            self._update_status(DeviceStatus.CONNECTING)

            if self._simulator is None:
                self._init_simulator()

            if self._simulator is None or not self._simulator.connect():
                raise SimulatorError("模拟器连接失败")

            self._is_connected = True
            self._update_status(DeviceStatus.CONNECTED)
            self.connected.emit(self.device_id)

            logger.info("设备 %s 模拟器连接成功", self.device_id)
            return True, ""

        except Exception as e:
            error_msg = f"模拟器异常: {str(e)}"
            self._connection_error = error_msg
            self._update_status(DeviceStatus.ERROR)
            self.connection_error.emit(self.device_id, error_msg)
            return False, error_msg

    def disconnect(self) -> bool:
        """
        断开设备连接

        流程：
        1. 如果使用模拟器，断开模拟器
        2. 如果有协议实例，清理协议资源
        3. 如果有驱动实例，断开驱动连接
        4. 清空运行时状态
        5. 发射断开信号

        Returns:
            是否断开成功
        """
        try:
            logger.info("正在断开设备 %s", self.device_id)

            # 断开模拟器
            if self._simulator is not None:
                self._simulator.disconnect()

            # 断开协议
            if self._protocol is not None:
                try:
                    # 断开信号连接
                    if hasattr(self._protocol, 'data_updated'):
                        try:
                            self._protocol.data_updated.disconnect(self._on_protocol_data)
                        except (TypeError, RuntimeError):
                            pass
                    if hasattr(self._protocol, 'error_occurred'):
                        try:
                            self._protocol.error_occurred.disconnect(self._on_protocol_error)
                        except (TypeError, RuntimeError):
                            pass
                except Exception as e:
                    logger.debug("断开协议信号时出错: %s", e)

            # 断开驱动
            if self._driver is not None and self._driver.is_connected():
                try:
                    # 断开错误信号
                    try:
                        self._driver.error_occurred.disconnect(self._on_driver_error)
                    except (TypeError, RuntimeError):
                        pass

                    self._driver.disconnect()
                except Exception as e:
                    logger.warning("断开驱动时出错: %s", e)

            # 清空运行时状态
            self._is_connected = False
            self._driver = None
            self._protocol = None
            self._current_data.clear()
            self._connection_error = ""

            # 更新状态
            self._update_status(DeviceStatus.DISCONNECTED)
            self.disconnected.emit(self.device_id)

            logger.info("设备 %s 已断开连接", self.device_id)
            return True

        except Exception as e:
            logger.error("断开设备 %s 时发生异常: %s", self.device_id, str(e))
            # 强制更新状态
            self._is_connected = False
            self._update_status(DeviceStatus.DISCONNECTED)
            return False

    # ==================== 数据操作方法 ====================

    def poll_data(self) -> Dict[str, Any]:
        """
        执行数据轮询（v3.2 配置驱动版本 - 智能批量读取）

        新逻辑流程（配置驱动）:
        1. 遍历 self._register_points
        2. 按 read_function_code 分组 (FC01一组, FC02一组, FC03一组...)
        3. 组内按地址连续性合并批次
        4. 批量调用 protocol.read_coils() / read_discrete_inputs() / _read_registers()
        5. 将结果按 RegisterPointConfig.name 格式化
        6. emit data_updated({name: {raw, value, type, writable, config}})

        性能优化:
        - 连续地址合并：减少通信次数（如8个连续Coil只需1次FC01）
        - 功能码分组：避免混合不同类型的读取请求

        Returns:
            轮询到的数据字典 {参数名: {raw, value, type, writable, config}}
            如果未连接或出错则返回空字典
        """
        try:
            # 模拟器模式
            if self.is_using_simulator() and self._simulator is not None:
                data = self._current_data  # 模拟器数据通过信号更新
                self.data_received.emit(self.device_id, data)
                return dict(data)

            # 正常通信模式
            if not self._is_connected or self._protocol is None:
                logger.warning(
                    "设备 %s 未连接或协议未初始化，无法轮询",
                    self.device_id
                )
                return {}

            # v3.2 新增：如果没有配置寄存器点，使用旧的协议轮询方式（向后兼容）
            if not self._register_points:
                logger.debug(
                    "设备 %s 未配置寄存器点，使用协议默认轮询方式",
                    self.device_id
                )
                data = self._protocol.poll_data()
                if data:
                    self._current_data = dict(data)
                    self.data_received.emit(self.device_id, data)
                return dict(data) if data else {}

            # ===== v3.2 核心：配置驱动的智能轮询 =====
            result = self._poll_data_with_config()

            if result:
                self._current_data = dict(result)
                self.data_received.emit(self.device_id, result)

            return result

        except Exception as e:
            error_msg = f"轮询数据异常: {str(e)}"
            logger.error("设备 %s %s", self.device_id, error_msg)
            self._connection_error = error_msg
            self.connection_error.emit(self.device_id, error_msg)
            return {}

    def read_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        读取寄存器块

        Args:
            address: 起始地址
            count: 寄存器数量

        Returns:
            寄存器值列表，失败返回 None
        """
        try:
            if self.is_using_simulator() and self._simulator is not None:
                return self._simulator.read_registers(address, count)

            if self._protocol is not None and self._is_connected:
                return self._protocol.read_registers(address, count)

            return None

        except Exception as e:
            logger.error(
                "设备 %s 读取寄存器 [addr=%d, count=%d] 失败: %s",
                self.device_id, address, count, str(e)
            )
            return None

    def write_register(self, address: int, value: int) -> bool:
        """
        写入单个寄存器

        Args:
            address: 寄存器地址
            value: 写入值

        Returns:
            是否写入成功
        """
        try:
            if self.is_using_simulator() and self._simulator is not None:
                return self._simulator.write_register(address, value)

            if self._protocol is not None and self._is_connected:
                return self._protocol.write_register(address, value)

            return False

        except Exception as e:
            logger.error(
                "设备 %s 写入寄存器 [addr=%d, value=%d] 失败: %s",
                self.device_id, address, value, str(e)
            )
            return False

    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        写入多个寄存器

        Args:
            address: 起始地址
            values: 写入值列表

        Returns:
            是否写入成功
        """
        try:
            if self.is_using_simulator() and self._simulator is not None:
                return self._simulator.write_registers(address, values)

            if self._protocol is not None and self._is_connected:
                return self._protocol.write_registers(address, values)

            return False

        except Exception as e:
            logger.error(
                "设备 %s 批量写入寄存器 [addr=%d, count=%d] 失败: %s",
                self.device_id, address, len(values), str(e)
            )
            return False

    # ==================== 新增：批量写操作（FC15/FC16优化）====================

    def batch_write_coils(
        self,
        operations: List[Dict[str, Any]],
        require_confirm: bool = True
    ) -> str:
        """
        批量写入多个线圈（FC15优化版本）

        智能地将多个线圈写操作合并为最少数量的 FC15 调用，
        显著减少通信次数，提高效率。

        优化策略：
        1. 验证所有参数名是否在 register_points 中
        2. 按 address 排序并分组（连续地址合并为一次 FC15 调用）
        3. 如果 require_confirm=True → 发射确认信号
        4. 用户确认后 → protocol.write_multiple_coils()

        Args:
            operations: 操作列表
                [{"name": "进水阀", "value": True}, ...]
                或 [{"address": 0, "value": True}, ...]
            require_confirm: 是否需要确认

        Returns:
            req_id: 请求ID（用于跟踪）

        Raises:
            ValueError: 参数名无效或不可写

        Examples:
            >>> # 一次性写入8个线圈（未优化前需8次通信）
            >>> ops = [
            ...     {"name": "阀1", "value": True},
            ...     {"name": "阀2", "value": False},
            ...     {"name": "阀3", "value": True},
            ... ]
            >>> req_id = conn.batch_write_coils(ops)
        """
        if not operations:
            raise ValueError("操作列表不能为空")

        # 步骤1：验证并解析操作列表
        validated_ops = []
        for op in operations:
            # 支持按名称或地址指定
            if "name" in op:
                config = self.get_register_point_by_name(op["name"])
                if config is None:
                    raise ValueError(f"未找到参数: {op['name']}")
                if not config.writable:
                    raise ValueError(f"参数 '{op['name']}' 不可写")
                if config.data_type != RegisterDataType.COIL:
                    raise ValueError(
                        f"参数 '{op['name']}' 不是线圈类型 "
                        f"(当前: {config.data_type.display_name})"
                    )
                address = config.address
            elif "address" in op:
                address = op["address"]
            else:
                raise ValueError("操作必须包含 'name' 或 'address' 字段")

            value = op.get("value", False)
            validated_ops.append({
                "name": op.get("name", f"@{address}"),
                "address": address,
                "value": bool(value),
            })

        # 步骤2：按地址排序
        validated_ops.sort(key=lambda x: x["address"])

        logger.info(
            "设备 %s 批量线圈写请求 [操作数=%d, 需确认=%s]",
            self.device_id, len(validated_ops), require_confirm
        )

        # 如果需要确认，发射信号
        if require_confirm:
            # 发射第一个操作的确认信号（UI层可扩展为批量确认对话框）
            first_op = validated_ops[0]
            self.write_confirmation_required.emit(
                first_op["name"],
                first_op["address"],
                first_op["value"],
                {
                    "type": "batch_coils",
                    "operations": validated_ops,
                    "total_count": len(validated_ops),
                }
            )
            return f"batch_{id(self)}"

        # 直接执行模式
        return self._execute_batch_coils(validated_ops)

    def batch_write_registers(
        self,
        operations: List[Dict[str, Any]],
        require_confirm: bool = True
    ) -> str:
        """
        批量写入多个寄存器（FC16优化版本）

        智能地将多个寄存器写操作合并为最少数量的 FC16 调用。

        Args:
            operations: 操作列表
                [{"name": "温度设定值", "value": 2500}, ...]
                或 [{"address": 0, "value": 2500}, ...]
            require_confirm: 是否需要确认

        Returns:
            req_id: 请求ID

        Raises:
            ValueError: 参数名无效或不可写

        Examples:
            >>> ops = [
            ...     {"name": "温度设定", "value": 25600},
            ...     {"name": "压力设定", "value": 1000},
            ... ]
            >>> req_id = conn.batch_write_registers(ops)
        """
        if not operations:
            raise ValueError("操作列表不能为空")

        # 验证并解析操作列表
        validated_ops = []
        for op in operations:
            if "name" in op:
                config = self.get_register_point_by_name(op["name"])
                if config is None:
                    raise ValueError(f"未找到参数: {op['name']}")
                if not config.writable:
                    raise ValueError(f"参数 '{op['name']}' 不可写")
                address = config.address
            elif "address" in op:
                address = op["address"]
            else:
                raise ValueError("操作必须包含 'name' 或 'address' 字段")

            value = op.get("value", 0)
            validated_ops.append({
                "name": op.get("name", f"@{address}"),
                "address": address,
                "value": int(value),
            })

        # 按地址排序
        validated_ops.sort(key=lambda x: x["address"])

        logger.info(
            "设备 %s 批量寄存器写请求 [操作数=%d, 需确认=%s]",
            self.device_id, len(validated_ops), require_confirm
        )

        if require_confirm:
            first_op = validated_ops[0]
            self.write_confirmation_required.emit(
                first_op["name"],
                first_op["address"],
                first_op["value"],
                {
                    "type": "batch_registers",
                    "operations": validated_ops,
                    "total_count": len(validated_ops),
                }
            )
            return f"batch_{id(self)}"

        return self._execute_batch_registers(validated_ops)

    def _execute_batch_coils(self, operations: List[Dict[str, Any]]) -> str:
        """
        执行批量线圈写入的内部方法

        将连续地址的操作合并为一次 FC15 调用。

        Args:
            operations: 已验证的操作列表（已按地址排序）

        Returns:
            结果信息字符串
        """
        success_count = 0
        fail_count = 0
        errors = []

        # 合并连续地址
        batches = self._merge_consecutive_operations(operations)

        for batch in batches:
            start_addr = batch[0]["address"]
            values = [op["value"] for op in batch]

            try:
                if self.is_using_simulator() and self._simulator is not None:
                    # 模拟器模式：逐个写入
                    for i, op in enumerate(batch):
                        int_val = 0xFF00 if op["value"] else 0x0000
                        if self._simulator.write_register(start_addr + i, int_val):
                            success_count += 1
                        else:
                            fail_count += 1
                            errors.append(f"地址 {start_addr + i} 写入失败")
                elif self._protocol is not None and hasattr(self._protocol, 'write_multiple_coils'):
                    # 真实设备：使用 FC15 批量写入
                    if self._protocol.write_multiple_coils(start_addr, values):
                        success_count += len(batch)
                        logger.info(
                            "批量写线圈成功 [起始=%d, 数量=%d]",
                            start_addr, len(values)
                        )
                    else:
                        fail_count += len(batch)
                        errors.append(f"FC15写入失败 [起始地址={start_addr}]")
                else:
                    fail_count += len(batch)
                    errors.append("协议不支持批量写线圈")

            except Exception as e:
                fail_count += len(batch)
                errors.append(f"异常: {str(e)}")
                logger.error("批量写线圈异常 [起始=%d]: %s", start_addr, str(e))

        # 记录审计日志
        total = success_count + fail_count
        logger.info(
            "设备 %s 批量线圈写入完成 [成功=%d, 失败=%d, 总计=%d]",
            self.device_id, success_count, fail_count, total
        )

        if fail_count > 0:
            self.coil_written.emit(
                f"批量({success_count}/{total})",
                -1,
                fail_count == 0
            )

        return f"batch_complete:{success_count}/{total}"

    def _execute_batch_registers(self, operations: List[Dict[str, Any]]) -> str:
        """
        执行批量寄存器写入的内部方法

        将连续地址的操作合并为一次 FC16 调用。

        Args:
            operations: 已验证的操作列表（已按地址排序）

        Returns:
            结果信息字符串
        """
        success_count = 0
        fail_count = 0
        errors = []

        # 合并连续地址
        batches = self._merge_consecutive_operations(operations)

        for batch in batches:
            start_addr = batch[0]["address"]
            values = [op["value"] for op in batch]

            try:
                if self.is_using_simulator() and self._simulator is not None:
                    # 模拟器模式
                    for i, op in enumerate(batch):
                        if self._simulator.write_register(start_addr + i, op["value"]):
                            success_count += 1
                        else:
                            fail_count += 1
                            errors.append(f"地址 {start_addr + i} 写入失败")
                elif self._protocol is not None:
                    # 真实设备：使用 FC16 批量写入
                    if self._protocol.write_registers(start_addr, values):
                        success_count += len(batch)
                        logger.info(
                            "批量写寄存器成功 [起始=%d, 数量=%d]",
                            start_addr, len(values)
                        )
                    else:
                        fail_count += len(batch)
                        errors.append(f"FC16写入失败 [起始地址={start_addr}]")
                else:
                    fail_count += len(batch)
                    errors.append("协议不可用")

            except Exception as e:
                fail_count += len(batch)
                errors.append(f"异常: {str(e)}")
                logger.error("批量写寄存器异常 [起始=%d]: %s", start_addr, str(e))

        total = success_count + fail_count
        logger.info(
            "设备 %s 批量寄存器写入完成 [成功=%d, 失败=%d, 总计=%d]",
            self.device_id, success_count, fail_count, total
        )

        return f"batch_complete:{success_count}/{total}"

    @staticmethod
    def _merge_consecutive_operations(operations: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        将操作列表按连续地址分组

        合并策略：如果相邻操作地址差=1，则合并到同一批。

        Args:
            operations: 操作列表（必须已按地址排序）

        Returns:
            分组后的批次列表
        """
        if not operations:
            return []

        batches = [[operations[0]]]

        for i in range(1, len(operations)):
            prev_addr = batches[-1][-1]["address"]
            curr_addr = operations[i]["address"]

            if curr_addr == prev_addr + 1:
                # 连续地址：合并到当前批次
                batches[-1].append(operations[i])
            else:
                # 不连续：开始新批次
                batches.append([operations[i]])

        # 记录合并统计
        original_count = len(operations)
        batch_count = len(batches)
        if batch_count > 1:
            logger.debug(
                "批量操作地址合并: %d 个操作 → %d 次通信 (减少 %d 次)",
                original_count, batch_count, original_count - batch_count
            )

        return batches

    # ==================== v3.2 新增：配置驱动的写操作 ====================

    def write_coil(self, param_name: str, value: bool, require_confirm: bool = True) -> None:
        """
        写入线圈（带确认机制的安全网关）

        处理流程：
        1. 根据参数名查找 RegisterPointConfig
        2. 如果 require_confirm=True，发射确认信号等待用户响应
        3. 如果 require_confirm=False，直接执行写入

        Args:
            param_name: 参数名称（如 "进水阀"、"出水阀"）
            value: 写入值（True=ON/闭合, False=OFF/断开）
            require_confirm: 是否需要用户确认（默认True，安全模式）

        Raises:
            ValueError: 参数名称未找到或不可写

        Examples:
            >>> # 安全模式：先弹出确认框，用户确认后才写入
            >>> conn.write_coil("进水阀", True, require_confirm=True)
            >>>
            >>> # 直接模式：跳过确认，立即写入（用于自动化脚本）
            >>> conn.write_coil("进水阀", False, require_confirm=False)
        """
        # 查找配置点
        config = self.get_register_point_by_name(param_name)
        if config is None:
            raise ValueError(f"未找到参数: {param_name}")

        # 检查是否可写
        if not config.writable:
            raise ValueError(f"参数 '{param_name}' 不可写（只读属性）")

        # 检查数据类型是否为COIL
        if config.data_type != RegisterDataType.COIL:
            raise ValueError(
                f"参数 '{param_name}' 不是线圈类型 "
                f"(当前类型: {config.data_type.display_name})"
            )

        # 记录审计日志
        logger.info(
            "设备 %s 发起线圈写请求 [参数=%s, 地址=%d, 值=%s, 需确认=%s]",
            self.device_id, param_name, config.address,
            "ON" if value else "OFF", require_confirm
        )

        if require_confirm:
            # 模式1：需要确认 → 发射信号，等待用户响应
            self.write_confirmation_required.emit(
                param_name,
                config.address,
                value,
                config  # 传递完整配置对象供UI使用
            )
        else:
            # 模式2：不需要确认 → 直接执行
            self.confirm_write(param_name, value)

    def confirm_write(self, param_name: str, value: bool) -> bool:
        """
        确认后的实际写操作入口（由 UI 确认回调调用）

        这是 write_coil(require_confirm=True) 的后续执行入口。
        当用户在确认对话框中点击"Yes"后，MainWindow 会调用此方法。

        Args:
            param_name: 参数名称
            value: 写入值

        Returns:
            是否写入成功

        Examples:
            >>> # 在 MainWindow 的槽函数中调用
            >>> def _on_write_confirmed(self, param_name, value):
            ...     success = self._current_connection.confirm_write(param_name, value)
            ...     if success:
            ...         print(f"{param_name} 已写入")
        """
        # 查找配置点
        config = self.get_register_point_by_name(param_name)
        if config is None:
            logger.error("确认写操作失败：未找到参数 '%s'", param_name)
            self.coil_written.emit(param_name, -1, False)
            return False

        # 执行实际的协议层写入
        success = self._execute_coil_write(config.address, value)

        # 发射完成信号
        self.coil_written.emit(param_name, config.address, success)

        # 记录审计日志
        if success:
            logger.info(
                "设备 %s 线圈写入成功 [参数=%s, 地址=%d, 值=%s]",
                self.device_id, param_name, config.address,
                "ON" if value else "OFF"
            )
        else:
            logger.error(
                "设备 %s 线圈写入失败 [参数=%s, 地址=%d, 值=%s]",
                self.device_id, param_name, config.address,
                "ON" if value else "OFF"
            )

        return success

    def send_raw_data(self, data: bytes) -> bool:
        """
        发送原始字节数据（底层通信）

        用于特殊协议扩展或调试目的。

        Args:
            data: 要发送的字节数据

        Returns:
            是否发送成功
        """
        if self._driver is not None and self._is_connected:
            return self._driver.send_data(data)
        return False

    # ==================== 配置更新方法 ====================

    def update_device_config(self, new_device: Device) -> None:
        """
        更新设备配置（热更新，无需重建连接）

        使用场景：
        - 用户编辑设备参数后实时生效
        - 动态调整轮询间隔
        - 修改字节序配置

        Args:
            new_device: 新的设备数据模型
        """
        old_device = self._device
        self._device = new_device

        logger.info(
            "设备 %s 配置已更新",
            self.device_id
        )

        # 如果协议存在，同步更新寄存器映射
        if self._protocol is not None:
            self._protocol.set_register_map(new_device.protocol_config.register_map)

            # 同步字节序配置
            if new_device.protocol_config.byte_order:
                if hasattr(self._protocol, 'set_byte_order'):
                    self._protocol.set_byte_order(new_device.protocol_config.byte_order)

        # 处理模拟器状态变化
        if new_device.is_using_simulator and self._simulator is None:
            self._init_simulator()
        elif not new_device.is_using_simulator and self._simulator is not None:
            self._simulator.disconnect()
            self._simulator = None

    # ==================== 字节序API（委托给Device）====================

    def set_byte_order(self, config: ByteOrderConfig) -> None:
        """设置字节序（同时更新Device和Protocol）"""
        self._device.set_byte_order(config)

        if self._protocol is not None and hasattr(self._protocol, 'set_byte_order'):
            self._protocol.set_byte_order(config)

    def get_byte_order(self) -> ByteOrderConfig:
        """获取当前字节序配置"""
        return self._device.get_byte_order()

    def has_custom_byte_order(self) -> bool:
        """是否有自定义字节序"""
        return self._device.has_custom_byte_order()

    def clear_byte_order(self) -> None:
        """清除自定义字节序"""
        self._device.clear_byte_order()

        if self._protocol is not None and hasattr(self._protocol, 'set_byte_order'):
            from ..protocols.byte_order_config import DEFAULT_BYTE_ORDER
            self._protocol.set_byte_order(DEFAULT_BYTE_ORDER)

    # ==================== 内部辅助方法 ====================

    def _parse_register_points_from_config(self) -> None:
        """
        从 Device 配置中解析寄存器点列表（v3.2 新增）

        解析逻辑：
        1. 从 device.protocol_config.register_map 读取配置列表
        2. 将每个字典转换为 RegisterPointConfig 对象
        3. 存储到 self._register_points 供轮询使用

        支持的格式：
        - 新格式: {"name": "温度", "data_type": "holding_float32", "address": 0, ...}
        - 旧格式: {"name": "Temp", "type": "float32", "address": 0, ...} (向后兼容)
        """
        try:
            register_map = self._device.protocol_config.register_map

            if not register_map:
                logger.debug(
                    "设备 %s 未配置寄存器映射表",
                    self.device_id
                )
                return

            self._register_points = []

            for reg_config in register_map:
                try:
                    # 尝试新格式解析（使用 data_type 字段）
                    if "data_type" in reg_config:
                        rp = RegisterPointConfig.from_dict(reg_config)
                        self._register_points.append(rp)
                    # 尝试旧格式兼容（使用 type 字段）
                    elif "type" in reg_config:
                        # 旧版 type → 新版 data_type 映射
                        type_mapping = {
                            "coil": "coil",
                            "discrete_input": "discrete_input",
                            "int16": "holding_int16",
                            "int32": "holding_int32",
                            "float32": "holding_float32",
                            "input_int16": "input_int16",
                            "input_float32": "input_float32",
                        }

                        old_type = reg_config.get("type", "")
                        new_type = type_mapping.get(old_type, old_type)

                        # 转换为新格式
                        new_config = dict(reg_config)
                        new_config["data_type"] = new_type
                        if "type" in new_config:
                            del new_config["type"]

                        rp = RegisterPointConfig.from_dict(new_config)
                        self._register_points.append(rp)
                    else:
                        logger.warning(
                            "设备 %s 寄存器配置缺少数据类型字段: %s",
                            self.device_id, reg_config.get("name", "未知")
                        )

                except Exception as e:
                    logger.warning(
                        "设备 %s 解析寄存器点配置失败 [name=%s]: %s",
                        self.device_id,
                        reg_config.get("name", "未知"),
                        str(e)
                    )

            logger.info(
                "设备 %s 已加载 %d 个寄存器点配置",
                self.device_id,
                len(self._register_points)
            )

        except Exception as e:
            logger.error(
                "设备 %s 解析寄存器映射表失败: %s",
                self.device_id, str(e)
            )
            self._register_points = []

    def _poll_data_with_config(self) -> Dict[str, Any]:
        """
        配置驱动的智能轮询核心实现（v3.2 新增）

        这是 poll_data() 的实际执行方法，
        实现了按功能码分组 + 连续地址合并的高效读取策略。

        Returns:
            格式化的数据字典 {参数名: {raw, value, type, writable, config}}
        """
        result = {}

        try:
            # 步骤1：按功能码分组
            grouped_by_fc = self._group_points_by_fc()

            # 步骤2：遍历每个功能码组
            for fc_code, points_in_group in grouped_by_fc.items():
                # 步骤3：组内按地址连续性合并批次
                batches = self._merge_consecutive(points_in_group)

                # 步骤4：对每个批次执行批量读取
                for batch in batches:
                    batch_data = self._read_batch(fc_code, batch)

                    # 步骤5：将结果格式化并合并到result
                    if batch_data:
                        result.update(batch_data)

            return result

        except Exception as e:
            logger.error(
                "设备 %s 配置驱动轮询失败: %s",
                self.device_id, str(e)
            )
            return {}

    def _group_points_by_fc(self) -> Dict[int, List[RegisterPointConfig]]:
        """
        将寄存器点按读取功能码分组（v3.2 新增）

        分组规则：
        - COIL → FC01 (读线圈)
        - DISCRETE_INPUT → FC02 (读离散输入)
        - HOLDING_INT16/INT32/FLOAT32 → FC03 (读保持寄存器)
        - INPUT_INT16/FLOAT32 → FC04 (读输入寄存器)

        Returns:
            {功能码: [RegisterPointConfig 列表]}

        Examples:
            >>> # 3个Coil + 2个HoldingInt + 4个DI
            >>> # 返回: {1: [coil1, coil2, coil3], 2: [di1, di2, di3, di4], 3: [int1, int2]}
        """
        groups: Dict[int, List[RegisterPointConfig]] = {}

        for rp in self._register_points:
            fc = rp.data_type.read_function_code

            if fc not in groups:
                groups[fc] = []

            groups[fc].append(rp)

        # 记录分组统计（调试用）
        for fc, points in groups.items():
            logger.debug(
                "设备 %s 功能码 FC%02d 分组: %d 个点",
                self.device_id, fc, len(points)
            )

        return groups

    @staticmethod
    def _merge_consecutive(points: List[RegisterPointConfig]) -> List[List[RegisterPointConfig]]:
        """
        合并连续地址为批次以减少通信次数（v3.2 新增）

        合并策略：
        - 按地址排序
        - 如果相邻点的地址差 <= 该点占用的寄存器数，则合并到同一批
        - 不同数据类型的寄存器占用数不同（COIL=1, FLOAT32=2）

        Args:
            points: 同一功能码组的寄存器点列表

        Returns:
            批次列表 [[point1, point2], [point3, ...]]

        Examples:
            >>> # 地址 0,1,2,3 连续 → 1个批次
            >>> # 地址 5,7 不连续 → 2个批次
            >>> # 结果: [[addr0, addr1, addr2, addr3], [addr5], [addr7]]
        """
        if not points:
            return []

        # 按地址排序
        sorted_points = sorted(points, key=lambda p: p.address)

        batches = []
        current_batch = [sorted_points[0]]

        for i in range(1, len(sorted_points)):
            prev_point = current_batch[-1]
            curr_point = sorted_points[i]

            # 计算前一个点结束地址
            prev_end_addr = prev_point.address + prev_point.data_type.get_register_count()

            # 检查是否连续（当前点地址 == 前一个点结束地址）
            if curr_point.address == prev_end_addr:
                # 连续：合并到当前批次
                current_batch.append(curr_point)
            else:
                # 不连续：保存当前批次，开始新批次
                batches.append(current_batch)
                current_batch = [curr_point]

        # 添加最后一个批次
        batches.append(current_batch)

        # 记录合并统计
        logger.debug(
            "地址连续性合并: %d 个点 → %d 个批次（减少 %d 次通信）",
            len(points), len(batches),
            len(points) - len(batches)
        )

        return batches

    def _read_batch(self, fc_code: int, batch: List[RegisterPointConfig]) -> Optional[Dict[str, Any]]:
        """
        读取单个批次的寄存器数据（v3.2 新增）

        根据功能码选择对应的协议读取方法：
        - FC01: protocol.read_coils()
        - FC02: protocol.read_discrete_inputs()
        - FC03: protocol.read_registers() (保持寄存器)
        - FC04: protocol.read_input_registers() (输入寄存器)

        Args:
            fc_code: 功能码
            batch: 一个批次的寄存器点列表（地址连续）

        Returns:
            格式化的数据字典，失败返回 None
        """
        if not batch:
            return None

        # 获取批次起始地址和总数量
        start_addr = batch[0].address
        last_point = batch[-1]
        end_addr = last_point.address + last_point.data_type.get_register_count()
        count = end_addr - start_addr

        logger.debug(
            "读取批次 [FC%02d, 起始=%d, 数量=%d]",
            fc_code, start_addr, count
        )

        try:
            raw_data = None

            # 根据功能码选择读取方法
            if fc_code == 0x01:  # FC01: 读线圈
                raw_data = self._protocol.read_coils(start_addr, count)

            elif fc_code == 0x02:  # FC02: 读离散输入
                raw_data = self._protocol.read_discrete_inputs(start_addr, count)

            elif fc_code == 0x03:  # FC03: 读保持寄存器
                raw_data = self._protocol.read_registers(start_addr, count)

            elif fc_code == 0x04:  # FC04: 读输入寄存器
                raw_data = self._protocol.read_input_registers(start_addr, count)

            else:
                logger.error("不支持的功能码: FC%02d", fc_code)
                return None

            # 处理原始数据
            if raw_data is None:
                logger.warning(
                    "读取失败 [FC%02d, addr=%d, count=%d]",
                    fc_code, start_addr, count
                )
                return None

            # 将原始数据按 RegisterPointConfig 格式化
            return self._format_batch_data(batch, raw_data, start_addr)

        except Exception as e:
            logger.error(
                "读取批次异常 [FC%02d, addr=%d]: %s",
                fc_code, start_addr, str(e)
            )
            return None

    def _format_batch_data(
        self,
        batch: List[RegisterPointConfig],
        raw_data: Union[List[Any], List[int]],
        start_addr: int
    ) -> Dict[str, Any]:
        """
        将批量读取的原始数据按配置格式化（v3.2 新增）

        Args:
            batch: 寄存器点配置列表
            raw_data: 原始数据（布尔列表或整数列表）
            start_addr: 批次起始地址

        Returns:
            格式化后的数据字典 {参数名: {raw, value, type, writable, config}}
        """
        result = {}

        for rp in batch:
            try:
                # 计算在原始数据中的索引偏移
                index_offset = rp.address - start_addr

                # 提取该点的原始值
                decoded_value = self._decode_point_value(rp, raw_data, index_offset)
                if decoded_value is not None:
                    result[rp.name] = {
                        "raw": decoded_value,
                        "value": rp.format_value(decoded_value),
                        "type": rp.data_type.code,
                        "writable": rp.writable,
                        "config": rp,  # 浼犻€掑畬鏁撮厤缃璞′緵UI浣跨敤
                    }
                else:
                    logger.warning(
                        "数据索引越界 [参数=%s, 偏移=%d, 数据长度=%d]",
                        rp.name, index_offset,
                        len(raw_data) if isinstance(raw_data, list) else 0
                    )

            except Exception as e:
                logger.error(
                    "格式化数据失败 [参数=%s]: %s",
                    rp.name, str(e)
                )
                continue

        return result

    def _decode_point_value(
        self,
        point: RegisterPointConfig,
        raw_data: Union[List[Any], List[int]],
        index_offset: int,
    ) -> Optional[Union[bool, int, float]]:
        """Decode a single configured point from a batched Modbus read.
        
        Step 8: Delegated to ModbusValueParser
        """
        try:
            from core.communication.modbus_value_parser import ModbusValueParser
            from core.protocols.byte_order_config import ByteOrderConfig, DEFAULT_BYTE_ORDER

            byte_order = self.get_byte_order() if hasattr(self, "get_byte_order") else DEFAULT_BYTE_ORDER
            parser = ModbusValueParser(byte_order=byte_order)
            return parser.parse(raw_data, index_offset, point.data_type)

        except Exception as e:
            logger.error("_decode_point_value exception: %s", e)
            return None

    def _execute_coil_write(self, address: int, value: bool) -> bool:
        """
        执行实际的线圈写入操作（v3.2 新增）

        这是底层的协议调用封装，支持模拟器和真实设备。

        Args:
            address: 线圈地址
            value: 写入值

        Returns:
            是否写入成功
        """
        try:
            # 模拟器模式
            if self.is_using_simulator() and self._simulator is not None:
                # 模拟器可能不支持线圈写操作，尝试使用通用写寄存器
                int_val = 0xFF00 if value else 0x0000
                return self._simulator.write_register(address, int_val)

            # 真实设备模式
            if self._protocol is not None and hasattr(self._protocol, 'write_single_coil'):
                return self._protocol.write_single_coil(address, value)

            logger.error("协议层不支持写线圈操作")
            return False

        except Exception as e:
            logger.error(
                "执行线圈写入失败 [地址=%d, 值=%s]: %s",
                address, "ON" if value else "OFF", str(e)
            )
            return False

    def _init_simulator(self) -> None:
        """初始化模拟器"""
        try:
            device_config = self._device.to_dict()
            self._simulator = Simulator(device_config)
            self._simulator.data_updated.connect(self._on_simulator_data)
            self._simulator.connected.connect(lambda: self._update_status(DeviceStatus.CONNECTED))
            self._simulator.disconnected.connect(lambda: self._update_status(DeviceStatus.DISCONNECTED))

            logger.debug("设备 %s 模拟器已初始化", self.device_id)

        except Exception as e:
            logger.error("初始化设备 %s 的模拟器失败: %s", self.device_id, str(e))
            self._simulator = None

    def _update_status(self, status: DeviceStatus) -> None:
        """
        更新连接状态（内部方法）

        同时更新 Device.status 和发射信号。
        """
        # 更新 Device 的状态字段（允许修改运行时状态）
        object.__setattr__(self._device, 'status', status)

        # 发射状态变化信号
        self.status_changed.emit(int(status))

    def _on_simulator_data(self, data: Dict[str, Any]) -> None:
        self._current_data = dict(data)
        self.data_received.emit(self.device_id, data)

    def _on_protocol_data(self, data: Dict[str, Any]) -> None:
        self._current_data = dict(data)
        self.data_received.emit(self.device_id, data)

    def _on_protocol_error(self, error: str) -> None:
        """处理协议错误"""
        logger.error("设备协议错误 [%s]: %s", self.device_id, error)
        self._connection_error = error
        enhanced_error = f"协议错误: {error}"
        self.connection_error.emit(self.device_id, enhanced_error)
        self.error_occurred.emit(enhanced_error)  # 兼容旧信号

    def _on_driver_error(self, error_msg: str) -> None:
        """处理驱动错误"""
        logger.error("设备驱动错误 [%s]: %s", self.device_id, error_msg)
        self._connection_error = error_msg
        enhanced_error = f"驱动错误: {error_msg}"
        self.connection_error.emit(self.device_id, enhanced_error)
        self.error_occurred.emit(enhanced_error)  # 兼容旧信号

    # ==================== 魔术方法 ====================

    def __repr__(self) -> str:
        return (
            f"DeviceConnection(device_id={self.device_id}, "
            f"connected={self._is_connected})"
        )

    def __del__(self):
        """析构时确保断开连接"""
        try:
            if self._is_connected:
                self.disconnect()
        except Exception:
            pass


# ==================== 自定义异常类 ====================

class ConnectionError(Exception):
    """连接错误"""
    pass


class ProtocolError(Exception):
    """协议错误"""
    pass


class SimulatorError(Exception):
    """模拟器错误"""
    pass
