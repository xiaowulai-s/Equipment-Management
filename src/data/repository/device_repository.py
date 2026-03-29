"""
设备数据仓库

提供设备+寄存器的持久化CRUD, 与运行时Device模型双向转换。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from ..models import DeviceModel, RegisterMapModel, utc_now
from .base import BaseRepository


class DeviceRepository(BaseRepository[DeviceModel]):
    """设备仓库"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, DeviceModel)

    # ═══════════════════════════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════════════════════════

    def get_by_name(self, name: str) -> Optional[DeviceModel]:
        """按名称查询"""
        return self._session.query(DeviceModel).filter(DeviceModel.name == name).first()

    def get_by_group(self, group_name: str) -> List[DeviceModel]:
        """按分组查询"""
        return self._session.query(DeviceModel).filter(DeviceModel.group_name == group_name).all()

    def get_with_registers(self, device_id: str) -> Optional[DeviceModel]:
        """查询设备 (预加载寄存器)"""
        return (
            self._session.query(DeviceModel)
            .options(joinedload(DeviceModel.register_maps))
            .filter(DeviceModel.id == device_id)
            .first()
        )

    def get_all_with_registers(self) -> List[DeviceModel]:
        """查询全部设备 (预加载寄存器)"""
        return self._session.query(DeviceModel).options(joinedload(DeviceModel.register_maps)).all()

    def get_enabled(self) -> List[DeviceModel]:
        """查询所有已启用设备"""
        return self._session.query(DeviceModel).filter(DeviceModel.enabled.is_(True)).all()

    def search(self, keyword: str) -> List[DeviceModel]:
        """模糊搜索 (名称/编号/分组)"""
        like = f"%{keyword}%"
        return (
            self._session.query(DeviceModel)
            .filter(
                DeviceModel.name.ilike(like)
                | DeviceModel.device_number.ilike(like)
                | DeviceModel.group_name.ilike(like)
            )
            .all()
        )

    # ═══════════════════════════════════════════════════════════
    # 写入 (运行时模型转换)
    # ═══════════════════════════════════════════════════════════

    def save_device(self, device: Any) -> DeviceModel:
        """保存运行时Device到数据库 (新增或更新)

        Args:
            device: src.device.device.Device 实例
        """
        existing = self.get_with_registers(device.id)

        if existing is not None:
            # 更新设备基本信息
            existing.name = device.name
            existing.protocol_type = device.protocol_type.value
            existing.slave_id = device.slave_id
            existing.enabled = device.enabled
            existing.status = device.device_status.value
            existing.description = getattr(device, "description", "")
            existing.location = getattr(device, "location", None)
            existing.group_name = getattr(device, "group_name", None)

            tp = device.tcp_params
            if tp:
                existing.host = tp.host
                existing.port = tp.port

            sp = device.serial_params
            if sp:
                existing.serial_port = sp.port
                existing.baud_rate = sp.baud_rate

            pc = device.poll_config
            if pc:
                existing.poll_interval_ms = pc.interval_ms
                existing.poll_timeout_ms = pc.timeout_ms
                existing.poll_retry_count = pc.retry_count
                existing.poll_retry_interval_ms = pc.retry_interval_ms

            # 替换寄存器
            self._replace_registers(existing, list(device.registers.values()))
            existing.updated_at = utc_now()

            return self.update(existing)
        else:
            # 新增
            model = DeviceModel.from_domain(device)
            return self.create(model)

    def delete_device(self, device_id: str) -> bool:
        """删除设备 (级联删除寄存器)"""
        device = self.get_with_registers(device_id)
        if device is None:
            return False
        self.delete(device)
        return True

    def _replace_registers(
        self,
        device: DeviceModel,
        registers: list,
    ) -> None:
        """替换设备的寄存器列表"""
        # 删除旧的
        for existing in list(device.register_maps):
            self._session.delete(existing)
        device.register_maps.clear()

        # 创建新的
        for reg in registers:
            device.register_maps.append(RegisterMapModel.from_domain(reg))
