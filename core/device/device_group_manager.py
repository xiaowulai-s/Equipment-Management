# -*- coding: utf-8 -*-
"""
设备分组管理器
Device Group Manager - extracted from DeviceManager
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from core.utils.logger import get_logger

if TYPE_CHECKING:
    from core.device.polling import DevicePollInfo, PollingGroup, PollPriority

logger = get_logger(__name__)


class DeviceGroupManager:
    """设备分组管理器 - 管理设备分组、轮询组和批量操作"""

    def __init__(
        self,
        device_groups: Dict[str, str],
        polling_groups: Dict[str, "PollingGroup"],
        devices: Dict[str, "DevicePollInfo"],
    ) -> None:
        self._device_groups = device_groups
        self._polling_groups = polling_groups
        self._devices = devices

    def get_group(self, device_id: str) -> str:
        return self._device_groups.get(device_id, "default")

    def set_group(self, device_id: str, group: str) -> bool:
        self._device_groups[device_id] = group
        logger.info("设备分组已更新", device_id=device_id, group=group)
        return True

    def remove_device(self, device_id: str) -> None:
        group_name = self._device_groups.pop(device_id, None)
        if group_name and group_name in self._polling_groups:
            self._polling_groups[group_name].device_ids.discard(device_id)

    def get_devices_in_group(self, group: str) -> List[str]:
        return [did for did, g in self._device_groups.items() if g == group]

    def get_all_groups(self) -> List[str]:
        return list(set(self._device_groups.values()))

    def get_group_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for group in self._device_groups.values():
            summary[group] = summary.get(group, 0) + 1
        return summary

    def rename_group(self, old_name: str, new_name: str) -> int:
        count = 0
        for did, group in self._device_groups.items():
            if group == old_name:
                self._device_groups[did] = new_name
                count += 1
        if count > 0:
            logger.info("分组重命名", old_name=old_name, new_name=new_name, count=count)
        return count

    def add_polling_group(
        self, name: str, priority: "PollPriority", base_interval: int = 1000, enabled: bool = True
    ) -> bool:
        from core.device.polling import PollingGroup

        if name in self._polling_groups:
            logger.error("轮询组已存在", group_name=name)
            return False

        group = PollingGroup(name, priority, base_interval, enabled)
        self._polling_groups[name] = group
        logger.info("添加轮询组成功", group_name=name)
        return True

    def remove_polling_group(self, name: str) -> bool:
        if name == "default":
            logger.error("不能删除默认轮询组")
            return False

        if name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=name)
            return False

        group = self._polling_groups[name]
        for device_id in list(group.device_ids):
            self.assign_device_to_group(device_id, "default")

        del self._polling_groups[name]
        logger.info("删除轮询组成功", group_name=name)
        return True

    def assign_device_to_group(self, device_id: str, group_name: str) -> bool:
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        if group_name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=group_name)
            return False

        old_group = self._device_groups.get(device_id, "default")
        if old_group in self._polling_groups:
            self._polling_groups[old_group].device_ids.discard(device_id)

        self._polling_groups[group_name].device_ids.add(device_id)
        self._device_groups[device_id] = group_name

        poll_info = self._devices[device_id]
        poll_info.priority = self._polling_groups[group_name].priority

        logger.info("设备分配到轮询组成功", device_id=device_id, group_name=group_name)
        return True

    def get_group_devices(self, group_name: str) -> List[str]:
        if group_name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=group_name)
            return []
        return list(self._polling_groups[group_name].device_ids)

    def enable_group(self, group_name: str, enabled: bool) -> bool:
        if group_name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=group_name)
            return False

        self._polling_groups[group_name].enabled = enabled
        logger.info("更新轮询组状态成功", group_name=group_name, enabled=enabled)
        return True

    def get_all_groups_info(self) -> List[Dict]:
        result = []
        for group_name, group in self._polling_groups.items():
            result.append(
                {
                    "name": group_name,
                    "priority": group.priority.name,
                    "base_interval": group.base_interval,
                    "enabled": group.enabled,
                    "device_count": len(group.device_ids),
                }
            )
        return result
