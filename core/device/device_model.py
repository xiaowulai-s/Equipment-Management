# -*- coding: utf-8 -*-
"""
设备模型
Device Model
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from ..communication.base_driver import BaseDriver
from ..protocols.base_protocol import BaseProtocol
from .simulator import Simulator


class DeviceStatus:
    """设备状态枚举"""

    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3


class Device(QObject):
    """
    设备类
    Device Class
    """

    status_changed = Signal(int)  # 状态变化信号
    data_updated = Signal(dict)  # 数据更新信号
    error_occurred = Signal(str)  # 错误发生信号

    def __init__(self, device_id: str, device_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._device_id = device_id
        self._device_config = device_config
        self._status = DeviceStatus.DISCONNECTED
        self._driver: Optional[BaseDriver] = None
        self._protocol: Optional[BaseProtocol] = None
        self._simulator: Optional[Simulator] = None
        self._use_simulator = device_config.get("use_simulator", False)
        self._register_map: List[Dict[str, Any]] = device_config.get("register_map", [])
        self._current_data: Dict[str, Any] = {}

        # 如果使用模拟器，初始化模拟器
        if self._use_simulator:
            self._init_simulator()

    def _init_simulator(self):
        """
        初始化模拟器
        Initialize simulator
        """
        self._simulator = Simulator(self._device_config)
        self._simulator.data_updated.connect(self._on_simulator_data)
        self._simulator.connected.connect(lambda: self._set_status(DeviceStatus.CONNECTED))
        self._simulator.disconnected.connect(lambda: self._set_status(DeviceStatus.DISCONNECTED))

    def _on_simulator_data(self, data: Dict[str, Any]):
        """
        处理模拟器数据
        Handle simulator data
        """
        self._current_data = data
        self.data_updated.emit(data)

    def set_driver(self, driver: BaseDriver):
        """
        设置通信驱动
        Set communication driver
        """
        self._driver = driver

    def set_protocol(self, protocol: BaseProtocol):
        """
        设置协议
        Set protocol
        """
        self._protocol = protocol
        if self._driver:
            self._protocol.set_driver(self._driver)
        self._protocol.set_register_map(self._register_map)
        self._protocol.data_updated.connect(self._on_protocol_data)
        self._protocol.error_occurred.connect(self._on_protocol_error)

    def _on_protocol_data(self, data: Dict[str, Any]):
        """
        处理协议数据
        Handle protocol data
        """
        self._current_data = data
        self.data_updated.emit(data)

    def _on_protocol_error(self, error: str):
        """
        处理协议错误
        Handle protocol error
        """
        self.error_occurred.emit(error)

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证设备配置

        Validate device configuration

        Args:
            config: 设备配置字典

        Returns:
            tuple[bool, str]: (是否有效，错误信息)
        """
        # 检查必需字段
        required_fields = ["device_id", "name", "device_type", "protocol_type"]
        for field in required_fields:
            if field not in config or not config[field]:
                return False, f"缺少必需字段：{field}"

        # 检查协议类型
        protocol_type = config.get("protocol_type", "").lower()
        if protocol_type not in ["modbus_tcp", "modbus_rtu", "modbus_ascii"]:
            return False, f"不支持的协议类型：{protocol_type}"

        # 根据协议类型验证参数
        if protocol_type in ["modbus_tcp", "modbus_ascii"]:
            if not config.get("host"):
                return False, "缺少主机地址（host）"
            if not config.get("port"):
                return False, "缺少端口号（port）"
            port = config.get("port", 0)
            if not isinstance(port, int) or port < 1 or port > 65535:
                return False, "端口号必须在 1-65535 范围内"

        elif protocol_type == "modbus_rtu":
            if not config.get("port"):
                return False, "缺少串口号（port）"

        # 检查 Unit ID
        unit_id = config.get("unit_id", 1)
        if not isinstance(unit_id, int) or unit_id < 0 or unit_id > 247:
            return False, "Unit ID 必须在 0-247 范围内"

        return True, ""
        self._set_status(DeviceStatus.ERROR)

    def connect(self) -> bool:
        """
        连接设备
        Connect to device
        """
        if self._use_simulator and self._simulator:
            self._set_status(DeviceStatus.CONNECTING)
            return self._simulator.connect()

        if not self._driver:
            self.error_occurred.emit("未设置通信驱动")
            return False

        if not self._protocol:
            self.error_occurred.emit("未设置协议")
            return False

        self._set_status(DeviceStatus.CONNECTING)

        if self._driver.connect():
            if self._protocol.initialize():
                self._set_status(DeviceStatus.CONNECTED)
                return True
            else:
                self._driver.disconnect()
                self._set_status(DeviceStatus.ERROR)
                return False
        else:
            self._set_status(DeviceStatus.ERROR)
            return False

    def disconnect(self):
        """
        断开连接
        Disconnect from device
        """
        if self._use_simulator and self._simulator:
            self._simulator.disconnect()
            self._set_status(DeviceStatus.DISCONNECTED)
            return

        if self._driver and self._driver.is_connected():
            self._driver.disconnect()

        self._set_status(DeviceStatus.DISCONNECTED)

    def read_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        读取寄存器
        Read registers
        """
        if self._use_simulator and self._simulator:
            return self._simulator.read_registers(address, count)

        if self._protocol and self._status == DeviceStatus.CONNECTED:
            return self._protocol.read_registers(address, count)

        return None

    def write_register(self, address: int, value: int) -> bool:
        """
        写入单个寄存器
        Write single register
        """
        if self._use_simulator and self._simulator:
            return self._simulator.write_register(address, value)

        if self._protocol and self._status == DeviceStatus.CONNECTED:
            return self._protocol.write_register(address, value)

        return False

    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        写入多个寄存器
        Write multiple registers
        """
        if self._use_simulator and self._simulator:
            return self._simulator.write_registers(address, values)

        if self._protocol and self._status == DeviceStatus.CONNECTED:
            return self._protocol.write_registers(address, values)

        return False

    def poll_data(self) -> Dict[str, Any]:
        """
        轮询数据
        Poll data
        """
        if self._use_simulator:
            return self._current_data

        if self._protocol and self._status == DeviceStatus.CONNECTED:
            return self._protocol.poll_data()

        return {}

    def get_device_id(self) -> str:
        """
        获取设备ID
        Get device ID
        """
        return self._device_id

    def get_device_config(self) -> Dict[str, Any]:
        """
        获取设备配置
        Get device configuration
        """
        return self._device_config

    def get_status(self) -> int:
        """
        获取设备状态
        Get device status
        """
        return self._status

    def get_current_data(self) -> Dict[str, Any]:
        """
        获取当前数据
        Get current data
        """
        return self._current_data

    def is_using_simulator(self) -> bool:
        """
        是否使用模拟器
        Is using simulator
        """
        return self._use_simulator

    def _set_status(self, status: int):
        """
        设置状态
        Set status
        """
        if self._status != status:
            self._status = status
            self.status_changed.emit(status)
