# -*- coding: utf-8 -*-
"""
设备数据仓库
Device Repository
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session, joinedload

from ..models import DeviceModel, RegisterMapModel
from .base import BaseRepository


class DeviceRepository(BaseRepository[DeviceModel]):
    """设备数据仓库"""

    def __init__(self, session: Session):
        super().__init__(session, DeviceModel)

    def get_by_name(self, name: str) -> Optional[DeviceModel]:
        """根据名称获取设备"""
        return self._session.query(DeviceModel).filter(DeviceModel.name == name).first()

    def get_by_type(self, device_type: str) -> List[DeviceModel]:
        """根据类型获取设备列表"""
        return self._session.query(DeviceModel).filter(DeviceModel.device_type == device_type).all()

    def get_with_registers(self, device_id: str) -> Optional[DeviceModel]:
        """获取设备及其寄存器映射"""
        return (
            self._session.query(DeviceModel)
            .options(joinedload(DeviceModel.register_maps))
            .filter(DeviceModel.id == device_id)
            .first()
        )

    def get_all_with_registers(self) -> List[DeviceModel]:
        """获取所有设备及其寄存器映射"""
        return self._session.query(DeviceModel).options(joinedload(DeviceModel.register_maps)).all()

    def search(self, keyword: str) -> List[DeviceModel]:
        """搜索设备"""
        return (
            self._session.query(DeviceModel)
            .filter(DeviceModel.name.contains(keyword) | DeviceModel.device_number.contains(keyword))
            .all()
        )

    def create_from_config(self, config: Dict[str, Any]) -> DeviceModel:
        """从配置创建设备"""
        device = DeviceModel(
            id=config.get("device_id"),
            name=config.get("name", "未命名设备"),
            device_type=config.get("device_type", "未知类型"),
            device_number=config.get("device_number"),
            protocol_type=config.get("protocol_type", "modbus_tcp"),
            host=config.get("host"),
            port=config.get("port"),
            unit_id=config.get("unit_id", 1),
            use_simulator=config.get("use_simulator", False),
        )

        # 创建寄存器映射
        register_maps = config.get("register_map", [])
        for reg_config in register_maps:
            if isinstance(reg_config, dict):
                register_map = RegisterMapModel(
                    name=reg_config.get("name", ""),
                    address=reg_config.get("address", 0),
                    function_code=reg_config.get("function_code", 3),
                    data_type=reg_config.get("data_type", reg_config.get("type", "uint16")),
                    read_write=reg_config.get("read_write", "R"),
                    scale=reg_config.get("scale", 1.0),
                    unit=reg_config.get("unit", ""),
                    description=reg_config.get("description", ""),
                    enabled=reg_config.get("enabled", True),
                )
                device.register_maps.append(register_map)

        return self.create(device)

    def update_from_config(self, device_id: str, config: Dict[str, Any]) -> Optional[DeviceModel]:
        """从配置更新设备"""
        device = self.get_with_registers(device_id)
        if not device:
            return None

        # 更新基本信息
        device.name = config.get("name", device.name)
        device.device_type = config.get("device_type", device.device_type)
        device.device_number = config.get("device_number", device.device_number)
        device.protocol_type = config.get("protocol_type", device.protocol_type)
        device.host = config.get("host", device.host)
        device.port = config.get("port", device.port)
        device.unit_id = config.get("unit_id", device.unit_id)
        device.use_simulator = config.get("use_simulator", device.use_simulator)
        device.updated_at = datetime.utcnow()

        # 更新寄存器映射（简化处理：删除旧的有新的就重建）
        new_registers = config.get("register_map", [])
        if new_registers:
            # 删除旧的寄存器映射
            for old_reg in device.register_maps[:]:
                self._session.delete(old_reg)
            device.register_maps.clear()

            # 创建新的寄存器映射
            for reg_config in new_registers:
                if isinstance(reg_config, dict):
                    register_map = RegisterMapModel(
                        name=reg_config.get("name", ""),
                        address=reg_config.get("address", 0),
                        function_code=reg_config.get("function_code", 3),
                        data_type=reg_config.get("data_type", reg_config.get("type", "uint16")),
                        read_write=reg_config.get("read_write", "R"),
                        scale=reg_config.get("scale", 1.0),
                        unit=reg_config.get("unit", ""),
                        description=reg_config.get("description", ""),
                        enabled=reg_config.get("enabled", True),
                    )
                    device.register_maps.append(register_map)

        return self.update(device)

    def to_config(self, device: DeviceModel) -> Dict[str, Any]:
        """转换为配置格式"""
        config = device.to_dict()
        config["register_map"] = [reg.to_dict() for reg in device.register_maps]
        return config

    def delete_with_relations(self, device_id: str) -> bool:
        """删除设备及其所有关联数据"""
        device = self.get_with_registers(device_id)
        if device:
            self.delete(device)
            return True
        return False
