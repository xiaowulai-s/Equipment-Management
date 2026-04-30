# -*- coding: utf-8 -*-
"""
设备故障恢复管理器
Device Fault Recovery Manager - extracted from DeviceManager
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from core.device.device_model import DeviceStatus
from core.utils.logger import get_logger

if TYPE_CHECKING:
    from core.device.device_manager_v2 import DevicePollInfo

logger = get_logger(__name__)


class FaultRecoveryManager:
    """设备故障恢复管理器 - 管理故障检测、恢复策略和状态查询"""

    def __init__(self, devices: Dict[str, "DevicePollInfo"]) -> None:
        self._devices = devices

    def enable_fault_detection(self, device_id: str, enabled: bool) -> bool:
        if device_id not in self._devices:
            return False
        self._devices[device_id].fault_detection_enabled = enabled
        logger.info("更新设备故障检测状态", device_id=device_id, enabled=enabled)
        return True

    def enable_auto_recovery(self, device_id: str, enabled: bool) -> bool:
        if device_id not in self._devices:
            return False
        self._devices[device_id].recovery_enabled = enabled
        logger.info("更新设备自动恢复状态", device_id=device_id, enabled=enabled)
        return True

    def set_recovery_mode(self, device_id: str, mode: str) -> bool:
        if device_id not in self._devices or mode not in ["auto", "manual"]:
            return False
        self._devices[device_id].recovery_mode = mode
        logger.info("更新设备恢复模式", device_id=device_id, mode=mode)
        return True

    def set_max_recovery_attempts(self, device_id: str, max_attempts: int) -> bool:
        if device_id not in self._devices or max_attempts <= 0:
            return False
        self._devices[device_id].max_recovery_attempts = max_attempts
        logger.info("更新设备最大恢复尝试次数", device_id=device_id, max_attempts=max_attempts)
        return True

    def get_fault_recovery_status(self, device_id: str) -> Dict:
        if device_id not in self._devices:
            return {}
        p = self._devices[device_id]
        return {
            "fault_type": p.fault_type,
            "fault_start_time": p.fault_start_time,
            "fault_duration": p.fault_duration,
            "recovery_attempts": p.recovery_attempts,
            "max_recovery_attempts": p.max_recovery_attempts,
            "recovery_status": p.recovery_status,
            "recovery_mode": p.recovery_mode,
            "recovery_enabled": p.recovery_enabled,
            "fault_detection_enabled": p.fault_detection_enabled,
            "recovery_history": p.recovery_history[-5:],
            "error_history": p.error_history[-10:],
        }

    def manual_recovery(self, device_id: str) -> bool:
        if device_id not in self._devices:
            return False
        poll_info = self._devices[device_id]
        poll_info.recovery_mode = "manual"
        try:
            logger.info("手动触发设备恢复", device_id=device_id)
            if poll_info.device.get_status() == DeviceStatus.CONNECTED:
                poll_info.device.disconnect()
            success = poll_info.device.connect()
            if success:
                poll_info.on_success()
                logger.info("手动恢复成功", device_id=device_id)
            else:
                logger.warning("手动恢复失败", device_id=device_id)
            return success
        except Exception as e:
            logger.error("手动恢复异常", device_id=device_id, error=str(e))
            return False

    def reset_fault(self, device_id: str) -> bool:
        if device_id not in self._devices:
            return False
        poll_info = self._devices[device_id]
        poll_info.on_success()
        logger.info("设备故障状态已重置", device_id=device_id)
        return True
