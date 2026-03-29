# -*- coding: utf-8 -*-
"""Runtime device wrapper."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from ..communication.base_driver import BaseDriver
from ..protocols.base_protocol import BaseProtocol
from .simulator import Simulator

logger = logging.getLogger(__name__)


class DeviceStatus(IntEnum):
    """Device connection state."""

    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3


class Device(QObject):
    """Runtime device wrapper around driver, protocol, and simulator."""

    status_changed = Signal(int)
    data_updated = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, device_id: str, device_config: Dict[str, Any], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._device_id = device_id
        self._device_config = dict(device_config)
        self._status = DeviceStatus.DISCONNECTED
        self._driver: Optional[BaseDriver] = None
        self._protocol: Optional[BaseProtocol] = None
        self._simulator: Optional[Simulator] = None
        self._register_map: List[Dict[str, Any]] = list(self._device_config.get("register_map", []))
        self._current_data: Dict[str, Any] = {}
        self._use_simulator = bool(self._device_config.get("use_simulator", False))

        if self._use_simulator:
            self._init_simulator()

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate minimal runtime config requirements."""
        required_fields = ("device_id", "name", "device_type", "protocol_type")
        for field in required_fields:
            if not config.get(field):
                return False, f"缺少必需字段: {field}"

        protocol_type = str(config.get("protocol_type", "")).lower()
        if protocol_type not in {"modbus_tcp", "modbus_rtu", "modbus_ascii"}:
            return False, f"不支持的协议类型: {protocol_type}"

        if protocol_type in {"modbus_tcp", "modbus_ascii"}:
            if not config.get("host"):
                return False, "缺少主机地址(host)"
            port = config.get("port")
            if port is None:
                return False, "缺少端口号(port)"
            if not isinstance(port, int) or not 1 <= port <= 65535:
                return False, "端口号必须在 1-65535 范围内"

        if protocol_type == "modbus_rtu" and not config.get("port"):
            return False, "缺少串口号(port)"

        unit_id = config.get("unit_id", 1)
        if not isinstance(unit_id, int) or not 0 <= unit_id <= 247:
            return False, "Unit ID 必须在 0-247 范围内"

        return True, ""

    def _init_simulator(self) -> None:
        """Initialize simulator mode and connect simulator signals."""
        self._simulator = Simulator(self._device_config)
        self._simulator.data_updated.connect(self._on_simulator_data)
        self._simulator.connected.connect(lambda: self._set_status(DeviceStatus.CONNECTED))
        self._simulator.disconnected.connect(lambda: self._set_status(DeviceStatus.DISCONNECTED))

    def _on_simulator_data(self, data: Dict[str, Any]) -> None:
        """Forward simulator data into runtime state."""
        self._current_data = dict(data)
        self.data_updated.emit(dict(data))

    def set_driver(self, driver: BaseDriver) -> None:
        """Attach a communication driver."""
        self._driver = driver
        if self._protocol is not None:
            self._protocol.set_driver(driver)

    def set_protocol(self, protocol: BaseProtocol) -> None:
        """Attach a protocol implementation."""
        self._protocol = protocol
        if self._driver is not None:
            self._protocol.set_driver(self._driver)
        self._protocol.set_register_map(self._register_map)
        self._protocol.data_updated.connect(self._on_protocol_data)
        self._protocol.error_occurred.connect(self._on_protocol_error)

    def _on_protocol_data(self, data: Dict[str, Any]) -> None:
        """Forward protocol data into runtime state."""
        self._current_data = dict(data)
        self.data_updated.emit(dict(data))

    def _on_protocol_error(self, error: str) -> None:
        """Forward protocol errors."""
        logger.error("设备协议错误 [%s]: %s", self._device_id, error)
        self.error_occurred.emit(error)

    def connect(self) -> bool:
        """Connect the device."""
        if self._use_simulator and self._simulator is not None:
            self._set_status(DeviceStatus.CONNECTING)
            if self._simulator.connect():
                return True
            self._set_status(DeviceStatus.ERROR)
            return False

        if self._driver is None:
            self.error_occurred.emit("未设置通信驱动")
            self._set_status(DeviceStatus.ERROR)
            return False

        if self._protocol is None:
            self.error_occurred.emit("未设置协议")
            self._set_status(DeviceStatus.ERROR)
            return False

        self._set_status(DeviceStatus.CONNECTING)
        if not self._driver.connect():
            self._set_status(DeviceStatus.ERROR)
            return False

        if self._protocol.initialize():
            self._set_status(DeviceStatus.CONNECTED)
            return True

        self._driver.disconnect()
        self._set_status(DeviceStatus.ERROR)
        return False

    def disconnect(self) -> bool:
        """Disconnect the device."""
        if self._use_simulator and self._simulator is not None:
            self._simulator.disconnect()
            self._set_status(DeviceStatus.DISCONNECTED)
            return True

        if self._driver is not None and self._driver.is_connected():
            self._driver.disconnect()

        self._set_status(DeviceStatus.DISCONNECTED)
        return True

    def read_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Read a register block."""
        if self._use_simulator and self._simulator is not None:
            return self._simulator.read_registers(address, count)
        if self._protocol is not None and self._status == DeviceStatus.CONNECTED:
            return self._protocol.read_registers(address, count)
        return None

    def write_register(self, address: int, value: int) -> bool:
        """Write one register."""
        if self._use_simulator and self._simulator is not None:
            return self._simulator.write_register(address, value)
        if self._protocol is not None and self._status == DeviceStatus.CONNECTED:
            return self._protocol.write_register(address, value)
        return False

    def write_registers(self, address: int, values: List[int]) -> bool:
        """Write multiple registers."""
        if self._use_simulator and self._simulator is not None:
            return self._simulator.write_registers(address, values)
        if self._protocol is not None and self._status == DeviceStatus.CONNECTED:
            return self._protocol.write_registers(address, values)
        return False

    def poll_data(self) -> Dict[str, Any]:
        """Poll data from the underlying simulator or protocol."""
        if self._use_simulator:
            return dict(self._current_data)
        if self._protocol is not None and self._status == DeviceStatus.CONNECTED:
            return self._protocol.poll_data()
        return {}

    def get_device_id(self) -> str:
        """Return the runtime device id."""
        return self._device_id

    def get_device_config(self) -> Dict[str, Any]:
        """Return a copy of the runtime config."""
        return dict(self._device_config)

    def get_status(self) -> int:
        """Return the current device status."""
        return int(self._status)

    def get_current_data(self) -> Dict[str, Any]:
        """Return the latest observed device data."""
        return dict(self._current_data)

    def is_using_simulator(self) -> bool:
        """Return whether simulator mode is enabled."""
        return self._use_simulator

    def update_config(self, device_config: Dict[str, Any]) -> None:
        """Replace runtime config and refresh dependent state."""
        self._device_config = dict(device_config)
        self._register_map = list(self._device_config.get("register_map", []))
        self._use_simulator = bool(self._device_config.get("use_simulator", False))
        if self._protocol is not None:
            self._protocol.set_register_map(self._register_map)

    def _set_status(self, status: DeviceStatus) -> None:
        """Update status and emit when it changes."""
        if self._status != status:
            self._status = status
            self.status_changed.emit(int(status))
