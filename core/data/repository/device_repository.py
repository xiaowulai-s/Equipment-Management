# -*- coding: utf-8 -*-
"""Device repository."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from ..models import DeviceModel, RegisterMapModel, utc_now
from .base import BaseRepository


class DeviceRepository(BaseRepository[DeviceModel]):
    """Repository for persistent devices and register maps."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, DeviceModel)

    def get_by_name(self, name: str) -> Optional[DeviceModel]:
        """Return device by name."""
        return self._session.query(DeviceModel).filter(DeviceModel.name == name).first()

    def get_by_type(self, device_type: str) -> List[DeviceModel]:
        """Return devices by type."""
        return self._session.query(DeviceModel).filter(DeviceModel.device_type == device_type).all()

    def get_with_registers(self, device_id: str) -> Optional[DeviceModel]:
        """Return one device with eager-loaded register maps."""
        return (
            self._session.query(DeviceModel)
            .options(joinedload(DeviceModel.register_maps))
            .filter(DeviceModel.id == device_id)
            .first()
        )

    def get_all_with_registers(self) -> List[DeviceModel]:
        """Return all devices with eager-loaded register maps."""
        return self._session.query(DeviceModel).options(joinedload(DeviceModel.register_maps)).all()

    def search(self, keyword: str) -> List[DeviceModel]:
        """Search devices by name or device number."""
        query = self._session.query(DeviceModel).filter(DeviceModel.name.contains(keyword))
        if keyword:
            query = query.union(self._session.query(DeviceModel).filter(DeviceModel.device_number.contains(keyword)))
        return query.all()

    def create_from_config(self, config: Dict[str, Any]) -> DeviceModel:
        """Create one device and register maps from runtime config."""
        device = DeviceModel(
            id=config.get("device_id"),
            name=config.get("device_type", "未知类型") + "_" + config.get("device_id", ""),
            device_type=config.get("device_type", "未知类型"),
            device_number=config.get("device_number"),
            protocol_type=config.get("protocol_type") or config.get("protocol", "modbus_tcp"),
            host=config.get("host") or config.get("ip"),
            port=config.get("port"),
            unit_id=config.get("unit_id", config.get("slave_id", 1)),
            use_simulator=config.get("use_simulator", False),
        )
        self._replace_register_maps(device, config.get("register_map", []))
        return self.create(device)

    def update_from_config(self, device_id: str, config: Dict[str, Any]) -> Optional[DeviceModel]:
        """Update a persistent device from runtime config."""
        device = self.get_with_registers(device_id)
        if device is None:
            return None

        device.name = config.get("device_type", device.device_type) + "_" + device_id
        device.device_type = config.get("device_type", device.device_type)
        device.device_number = config.get("device_number", device.device_number)
        device.protocol_type = config.get("protocol_type", config.get("protocol", device.protocol_type))
        device.host = config.get("host", config.get("ip", device.host))
        device.port = config.get("port", device.port)
        device.unit_id = config.get("unit_id", config.get("slave_id", device.unit_id))
        device.use_simulator = config.get("use_simulator", device.use_simulator)
        device.updated_at = utc_now()

        if "register_map" in config:
            self._replace_register_maps(device, config.get("register_map", []))

        return self.update(device)

    def to_config(self, device: DeviceModel) -> Dict[str, Any]:
        """Convert a persistent device to runtime config payload."""
        config = device.to_dict()
        config["device_id"] = config["id"]
        config["protocol"] = config["protocol_type"]
        config["ip"] = config["host"]
        config["slave_id"] = config["unit_id"]
        config["register_map"] = [register_map.to_dict() for register_map in device.register_maps]
        # 确保端口信息在配置中
        if device.port is not None:
            config["port"] = device.port
        return config

    def delete_with_relations(self, device_id: str) -> bool:
        """Delete a device and cascaded relations."""
        device = self.get_with_registers(device_id)
        if device is None:
            return False
        self.delete(device)
        return True

    def _replace_register_maps(self, device: DeviceModel, register_configs: List[Dict[str, Any]]) -> None:
        """Replace device register map list from config dictionaries."""
        for existing in list(device.register_maps):
            self._session.delete(existing)
        device.register_maps.clear()

        for register_config in register_configs:
            if not isinstance(register_config, dict):
                continue
            device.register_maps.append(
                RegisterMapModel(
                    name=register_config.get("name", ""),
                    address=register_config.get("address", 0),
                    function_code=register_config.get("function_code", 3),
                    data_type=register_config.get("data_type", register_config.get("type", "uint16")),
                    read_write=register_config.get("read_write", "R"),
                    scale=register_config.get("scale", 1.0),
                    unit=register_config.get("unit", ""),
                    description=register_config.get("description", ""),
                    enabled=register_config.get("enabled", True),
                )
            )
