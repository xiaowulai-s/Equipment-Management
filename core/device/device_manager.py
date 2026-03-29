# -*- coding: utf-8 -*-
"""Device manager for runtime and persistence modes."""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from PySide6.QtCore import QObject, QTimer, Signal

from ..data.models import DatabaseManager, DeviceModel
from ..data.repository.device_repository import DeviceRepository
from .device_factory import DeviceFactory
from .device_model import Device, DeviceStatus

logger = logging.getLogger(__name__)


class DeviceManager(QObject):
    """Manage runtime devices or persistent device records."""

    device_added = Signal(str)
    device_removed = Signal(str)
    device_connected = Signal(str)
    device_disconnected = Signal(str)
    device_data_updated = Signal(str, dict)
    device_error = Signal(str, str)

    def __init__(
        self,
        config_file: Union[str, DatabaseManager] = "config.json",
        db_manager: Optional[DatabaseManager] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        if isinstance(config_file, DatabaseManager) and db_manager is None:
            db_manager = config_file
            config_file = "config.json"

        super().__init__(parent)
        self._config_file = str(config_file)
        self._db_manager = db_manager
        self._devices: Dict[str, Device] = {}
        self._poll_interval = 1000
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_all_devices)

        if self._db_manager is None:
            self._load_devices()
            self._poll_timer.start(self._poll_interval)

    def add_device(self, device: Union[Dict[str, Any], DeviceModel]) -> Union[str, bool]:
        """Add a runtime device config or a persistent device model."""
        if isinstance(device, DeviceModel):
            return self._add_persistent_device(device)
        return self._add_runtime_device(device)

    def remove_device(self, device_id: str) -> bool:
        """Remove one device by id."""
        if self._db_manager is not None:
            return self._remove_persistent_device(device_id)
        return self._remove_runtime_device(device_id)

    def update_device(self, device: DeviceModel) -> bool:
        """Update one persistent device record."""
        if self._db_manager is None:
            logger.warning("update_device 仅在数据库模式下可用")
            return False

        try:
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                existing = repo.get_by_id(device.id)
                if existing is None:
                    return False

                existing.name = device.name
                existing.device_type = device.device_type
                existing.device_number = device.device_number
                existing.protocol_type = device.protocol_type
                existing.host = device.host
                existing.port = device.port
                existing.unit_id = device.unit_id
                existing.use_simulator = device.use_simulator
                existing.status = device.status
                repo.update(existing)
            return True
        except Exception:
            logger.exception("更新设备失败: %s", device.id)
            return False

    def list_devices(self) -> List[DeviceModel]:
        """List persistent devices in database mode."""
        if self._db_manager is None:
            return []

        with self._db_manager.session() as session:
            return DeviceRepository(session).get_all()

    def connect_device(self, device_id: str) -> bool:
        """Connect one runtime device."""
        device = self._devices.get(device_id)
        if device is None:
            return False

        connected = bool(device.connect())
        if connected:
            self.device_connected.emit(device_id)
        return connected

    def edit_device(self, device_id: str, new_config: Dict[str, Any]) -> bool:
        """Edit a runtime device by replacing its config."""
        if self._db_manager is not None:
            logger.warning("数据库模式不支持 edit_device，请使用 update_device")
            return False

        current = self._devices.get(device_id)
        if current is None:
            return False

        normalized = self._normalize_runtime_config({**new_config, "device_id": device_id})
        is_valid, error_message = Device.validate_config(normalized)
        if not is_valid:
            logger.error("更新运行时设备失败 [%s]: %s", device_id, error_message)
            self.device_error.emit(device_id, error_message)
            return False

        current.disconnect()
        self._devices[device_id] = self._create_runtime_device(device_id, normalized)
        self._save_devices()
        return True

    def disconnect_device(self, device_id: str) -> bool:
        """Disconnect one runtime device."""
        device = self._devices.get(device_id)
        if device is None:
            return False

        device.disconnect()
        self.device_disconnected.emit(device_id)
        return True

    def get_device(self, device_id: str) -> Optional[Union[Device, DeviceModel]]:
        """Return one runtime or persistent device."""
        if self._db_manager is not None:
            with self._db_manager.session() as session:
                return DeviceRepository(session).get_by_id(device_id)
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Return runtime devices in a UI-friendly structure."""
        devices: List[Dict[str, Any]] = []
        for device_id, device in self._devices.items():
            config = device.get_device_config()
            devices.append(
                {
                    "device_id": device_id,
                    "name": config.get("name", f"设备_{device_id}"),
                    "device_type": config.get("device_type", ""),
                    "status": device.get_status(),
                    "use_simulator": device.is_using_simulator(),
                    "config": config,
                }
            )
        return devices

    def batch_connect_devices(self, device_ids: Iterable[str]) -> Dict[str, bool]:
        """Connect multiple runtime devices."""
        return {device_id: self.connect_device(device_id) for device_id in device_ids}

    def batch_disconnect_devices(self, device_ids: Iterable[str]) -> Dict[str, bool]:
        """Disconnect multiple runtime devices."""
        return {device_id: self.disconnect_device(device_id) for device_id in device_ids}

    def batch_remove_devices(self, device_ids: Iterable[str]) -> Dict[str, bool]:
        """Remove multiple devices."""
        return {device_id: self.remove_device(device_id) for device_id in device_ids}

    def export_devices(self, device_ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Export runtime device configs as a serializable payload."""
        selected_ids = set(device_ids) if device_ids is not None else None
        exported = []
        for device in self._devices.values():
            config = device.get_device_config()
            if selected_ids is None or config.get("device_id") in selected_ids:
                exported.append(config)
        return {"version": "1.0", "devices": exported}

    def get_devices_by_status(self, status: int) -> List[Device]:
        """Return runtime devices that match one status."""
        return [device for device in self._devices.values() if device.get_status() == int(status)]

    def get_connected_devices(self) -> List[Device]:
        """Return connected runtime devices."""
        return self.get_devices_by_status(DeviceStatus.CONNECTED)

    def get_disconnected_devices(self) -> List[Device]:
        """Return disconnected runtime devices."""
        return self.get_devices_by_status(DeviceStatus.DISCONNECTED)

    def set_poll_interval(self, interval_ms: int) -> None:
        """Set runtime polling interval in milliseconds."""
        self._poll_interval = interval_ms
        self._poll_timer.setInterval(interval_ms)

    def get_poll_interval(self) -> int:
        """Return runtime polling interval in milliseconds."""
        return self._poll_interval

    def _add_runtime_device(self, device_config: Dict[str, Any]) -> str:
        normalized = self._normalize_runtime_config(device_config)
        is_valid, error_message = Device.validate_config(normalized)
        if not is_valid:
            raise ValueError(error_message)

        device_id = normalized["device_id"]
        self._devices[device_id] = self._create_runtime_device(device_id, normalized)
        self._save_devices()
        self.device_added.emit(device_id)
        return device_id

    def _create_runtime_device(self, device_id: str, device_config: Dict[str, Any]) -> Device:
        """Instantiate one runtime device and connect its signals."""
        device = DeviceFactory.create_device(device_id, dict(device_config))
        device.status_changed.connect(
            lambda status, current_id=device_id: self._on_device_status_changed(current_id, status)
        )
        device.data_updated.connect(lambda data, current_id=device_id: self._on_device_data_updated(current_id, data))
        device.error_occurred.connect(lambda error, current_id=device_id: self._on_device_error(current_id, error))
        return device

    def _remove_runtime_device(self, device_id: str) -> bool:
        device = self._devices.get(device_id)
        if device is None:
            return False

        device.disconnect()
        del self._devices[device_id]
        self._save_devices()
        self.device_removed.emit(device_id)
        return True

    def _add_persistent_device(self, device: DeviceModel) -> bool:
        if self._db_manager is None:
            raise TypeError("数据库模式未启用，不能传入 DeviceModel")

        try:
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                if repo.get_by_id(device.id) is not None:
                    return False
                repo.create(device)

            self.device_added.emit(device.id)
            return True
        except Exception:
            logger.exception("持久化添加设备失败: %s", getattr(device, "id", "unknown"))
            return False

    def _remove_persistent_device(self, device_id: str) -> bool:
        if self._db_manager is None:
            return False

        try:
            with self._db_manager.session() as session:
                deleted = DeviceRepository(session).delete_with_relations(device_id)

            if deleted:
                self.device_removed.emit(device_id)
            return deleted
        except Exception:
            logger.exception("持久化删除设备失败: %s", device_id)
            return False

    def _normalize_runtime_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize aliases and defaults for runtime device config."""
        normalized = dict(config)
        device_id = str(normalized.get("device_id") or uuid.uuid4().hex[:8])
        normalized["device_id"] = device_id
        normalized["name"] = str(normalized.get("name") or f"设备_{device_id}")
        normalized["device_type"] = str(normalized.get("device_type") or "未分类设备")
        normalized["protocol_type"] = str(
            normalized.get("protocol_type") or normalized.get("protocol") or "modbus_tcp"
        ).lower()
        normalized["protocol"] = normalized["protocol_type"]
        normalized["host"] = normalized.get("host") or normalized.get("ip")
        normalized["ip"] = normalized["host"]

        unit_id = normalized.get("unit_id", normalized.get("slave_id", 1))
        normalized["unit_id"] = int(unit_id)
        normalized["slave_id"] = normalized["unit_id"]

        normalized["use_simulator"] = bool(normalized.get("use_simulator", False))
        normalized["register_map"] = list(normalized.get("register_map", []))
        return normalized

    def _poll_all_devices(self) -> None:
        """Poll all connected runtime devices."""
        for device_id, device in self._devices.items():
            if device.get_status() != DeviceStatus.CONNECTED:
                continue
            try:
                device.poll_data()
            except Exception:
                logger.exception("轮询设备失败: %s", device_id)

    def _on_device_status_changed(self, device_id: str, status: int) -> None:
        """Forward runtime status changes as manager-level signals."""
        if status == DeviceStatus.CONNECTED:
            self.device_connected.emit(device_id)
        elif status == DeviceStatus.DISCONNECTED:
            self.device_disconnected.emit(device_id)

    def _on_device_data_updated(self, device_id: str, data: Dict[str, Any]) -> None:
        """Forward runtime device data updates."""
        self.device_data_updated.emit(device_id, data)

    def _on_device_error(self, device_id: str, error: str) -> None:
        """Forward runtime device errors."""
        logger.error("设备错误 [%s]: %s", device_id, error)
        self.device_error.emit(device_id, error)

    def _load_devices(self) -> None:
        """Load runtime devices from the JSON config file."""
        if not os.path.exists(self._config_file):
            return

        try:
            with open(self._config_file, "r", encoding="utf-8") as file:
                config = json.load(file)
        except Exception:
            logger.exception("加载设备配置失败: %s", self._config_file)
            return

        for raw_config in config.get("devices", []):
            normalized = self._normalize_runtime_config(raw_config)
            device_id = normalized["device_id"]
            self._devices[device_id] = self._create_runtime_device(device_id, normalized)

    def _save_devices(self) -> None:
        """Persist runtime devices to the JSON config file."""
        if self._db_manager is not None:
            return

        config_path = Path(self._config_file)
        if config_path.parent and not config_path.parent.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w", encoding="utf-8") as file:
                json.dump(self.export_devices(), file, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("保存设备配置失败: %s", self._config_file)
