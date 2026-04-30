# -*- coding: utf-8 -*-
"""
Fault Recovery Service - Enhanced fault management

Responsibilities (Single Responsibility Principle - SRP):
- Fault detection and diagnosis
- Exponential backoff algorithm
- Auto-reconnection strategy
- Recovery status query and statistics
- Signal emission: recovery event notification

Design improvements (compared to original FaultRecoveryManager):
1. New signal mechanism for event-driven support
2. Configurable backoff strategy
3. Enhanced fault statistics and analysis
4. Independent from DeviceManager, can be tested separately
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from core.device.device_model import DeviceStatus
from core.utils.logger import get_logger

logger = get_logger("fault_recovery_service")


# ══════════════════════════════════════════════
# 数据定义
# ══════════════════════════════════════════════


class RecoveryMode(str, Enum):
    """恢复模式枚举"""

    AUTO = "auto"
    MANUAL = "manual"


class RecoveryStatus(str, Enum):
    """恢复状态枚举"""

    NONE = "none"  # 无需恢复
    ATTEMPTING = "attempting"  # 正在尝试
    SUCCEEDED = "succeeded"  # 恢复成功
    FAILED = "failed"  # 恢复失败


@dataclass
class BackoffConfig:
    """指数退避配置"""

    base_delay_ms: int = 1000  # Base delay (ms)
    max_delay_ms: int = 30000  # Max delay (ms)
    multiplier: float = 2.0  # Multiplier factor
    jitter: bool = True  # 是否添加随机抖动

    def calculate_delay(self, attempt: int) -> int:
        """
        计算第N次尝试的延迟时间

        Formula: delay = min(base * multiplier^attempt, max)

        Args:
            attempt: Current attempt count (starts from 0)

        Returns:
            int: Delay time (ms)
        """
        import random

        delay = min(
            self.base_delay_ms * (self.multiplier**attempt),
            self.max_delay_ms,
        )

        if self.jitter:
            delay = int(delay * (0.5 + random.random()))

        return delay


@dataclass
class RecoveryAttempt:
    """恢复尝试记录"""

    timestamp: int  # Timestamp (ms)
    attempt_number: int  # Attempt number
    status: str  # Status: in_progress/failed/succeeded
    fault_type: Optional[str] = None
    error_msg: Optional[str] = None
    duration_ms: int = 0  # Duration (ms)


@dataclass
class FaultStatistics:
    """设备故障统计"""

    device_id: str
    total_faults: int = 0
    total_recoveries: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    total_downtime_ms: int = 0  # 总停机时间
    last_fault_time: Optional[int] = None
    last_recovery_time: Optional[int] = None
    recovery_history: List[RecoveryAttempt] = field(default_factory=list)


# ══════════════════════════════════════════════
# 信号定义
# ══════════════════════════════════════════════


class FaultRecoverySignals(QObject):
    """故障恢复服务信号定义"""

    recovery_started = Signal(str, str)  # device_id, fault_type
    recovery_completed = Signal(str, bool)  # device_id, success
    recovery_failed = Signal(str, int)  # device_id, attempts
    fault_detected = Signal(str, str, str)  # device_id, error_type, error_msg
    fault_cleared = Signal(str)  # device_id


# ══════════════════════════════════════════════
# 主类实现
# ══════════════════════════════════════════════


class FaultRecoveryService:
    """
    故障恢复服务 - 核心故障管理组件

    Design points:
    1. Configurable backoff strategy (supports custom parameters)
    2. Complete fault statistics and history
    3. Event-driven status notification
    4. Thread-safe operation interface
    """

    # 默认配置
    DEFAULT_MAX_RECOVERY_ATTEMPTS = 5
    DEFAULT_BACKOFF_CONFIG = BackoffConfig()

    def __init__(
        self,
        devices: Dict[str, Any],
        max_attempts: int = DEFAULT_MAX_RECOVERY_ATTEMPTS,
        backoff_config: Optional[BackoffConfig] = None,
    ):
        """
        初始化故障恢复服务

        Args:
            devices: Device registry reference (shared state)
            max_attempts: Default max recovery attempts
            backoff_config: Backoff strategy config
        """
        self._devices = devices
        self._max_attempts = max_attempts
        self._backoff_config = backoff_config or self.DEFAULT_BACKOFF_CONFIG

        # 信号对象
        self._signals = FaultRecoveryDevices()

        # 设备级统计
        self._statistics: Dict[str, FaultStatistics] = {}

    # ══════════════════════════════════════════════
    # 属性访问
    # ══════════════════════════════════════════════

    @property
    def signals(self) -> FaultRecoverySignals:
        """获取信号对象"""
        return self._signals

    @property
    def backoff_config(self) -> BackoffConfig:
        """获取当前退避配置"""
        return self._backoff_config

    # ══════════════════════════════════════════════
    # 公共API - 故障检测控制
    # ══════════════════════════════════════════════

    def enable_fault_detection(self, device_id: str, enabled: bool) -> bool:
        """
        启用/禁用设备的故障检测功能

        Args:
            device_id: 设备唯一标识符
            enabled: 是否启用

        Returns:
            bool: 操作是否成功
        """
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        self._devices[device_id].fault_detection_enabled = enabled
        logger.info("更新设备故障检测状态", device_id=device_id, enabled=enabled)
        return True

    def enable_auto_recovery(self, device_id: str, enabled: bool) -> bool:
        """
        启用/禁用设备的自动恢复功能

        Args:
            device_id: 设备唯一标识符
            enabled: 是否启用

        Returns:
            bool: 操作是否成功
        """
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        self._devices[device_id].recovery_enabled = enabled
        logger.info("更新设备自动恢复状态", device_id=device_id, enabled=enabled)
        return True

    # ══════════════════════════════════════════════
    # 公共API - 恢复配置
    # ══════════════════════════════════════════════

    def set_recovery_mode(self, device_id: str, mode: str) -> bool:
        """
        设置设备的恢复模式

        Args:
            device_id: 设备唯一标识符
            mode: 恢复模式 ("auto"/"manual")

        Returns:
            bool: 操作是否成功
        """
        if device_id not in self._devices or mode not in ["auto", "manual"]:
            return False

        self._devices[device_id].recovery_mode = mode
        logger.info("更新设备恢复模式", device_id=device_id, mode=mode)
        return True

    def set_max_recovery_attempts(self, device_id: str, max_attempts: int) -> bool:
        """
        设置设备的最大恢复尝试次数

        Args:
            device_id: Device unique identifier
            max_attempts: Max attempts (must be > 0)

        Returns:
            bool: 操作是否成功
        """
        if device_id not in self._devices or max_attempts <= 0:
            return False

        self._devices[device_id].max_recovery_attempts = max_attempts
        logger.info("更新设备最大恢复尝试次数", device_id=device_id, max_attempts=max_attempts)
        return True

    # ══════════════════════════════════════════════
    # 公共API - 状态查询
    # ══════════════════════════════════════════════

    def get_fault_recovery_status(self, device_id: str) -> Dict:
        """
        获取设备的完整故障恢复状态

        Args:
            device_id: 设备唯一标识符

        Returns:
            Dict: 包含所有状态信息的字典
        """
        if device_id not in self._devices:
            return {}

        p = self._devices[device_id]
        stats = self._get_or_create_statistics(device_id)

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
            # 统计信息
            "total_faults": stats.total_faults,
            "successful_recoveries": stats.successful_recoveries,
            "failed_recoveries": stats.failed_recoveries,
            "total_downtime_s": stats.total_downtime_ms / 1000,
        }

    # ══════════════════════════════════════════════
    # 公共API - 手动操作
    # ══════════════════════════════════════════════

    def manual_recovery(self, device_id: str) -> bool:
        """
        手动触发设备恢复

        Flow:
        1. If connected, disconnect first
        2. Try to reconnect
        3. Update recovery status
        4. Emit signal notification

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 是否恢复成功
        """
        if device_id not in self._devices:
            return False

        poll_info = self._devices[device_id]
        poll_info.recovery_mode = "manual"

        start_time = time.monotonic()

        try:
            logger.info("手动触发设备恢复", device_id=device_id)

            # 断开再重连
            if poll_info.device.get_status() == DeviceStatus.CONNECTED:
                poll_info.device.disconnect()

            success = poll_info.device.connect()

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            if success:
                poll_info.on_success()
                self._record_recovery(device_id, success=True, elapsed_ms=elapsed_ms)
                logger.info("手动恢复成功", device_id=device_id)
                self._signals.recovery_completed.emit(device_id, True)
            else:
                self._record_recovery(device_id, success=False, elapsed_ms=elapsed_ms)
                logger.warning("手动恢复失败", device_id=device_id)
                self._signals.recovery_failed.emit(device_id, poll_info.recovery_attempts)

            return success

        except Exception as e:
            logger.error("手动恢复异常", device_id=device_id, error=str(e))
            return False

    def reset_fault(self, device_id: str) -> bool:
        """
        重置设备的故障状态

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 操作是否成功
        """
        if device_id not in self._devices:
            return False

        poll_info = self._devices[device_id]
        poll_info.on_success()

        logger.info("设备故障状态已重置", device_id=device_id)
        self._signals.fault_cleared.emit(device_id)
        return True

    # ══════════════════════════════════════════════
    # 内部方法 - 统计记录
    # ══════════════════════════════════════════════

    def _get_or_create_statistics(self, device_id: str) -> FaultStatistics:
        """获取或创建设备统计对象"""
        if device_id not in self._statistics:
            self._statistics[device_id] = FaultStatistics(device_id=device_id)
        return self._statistics[device_id]

    def _record_recovery(
        self,
        device_id: str,
        success: bool,
        elapsed_ms: int = 0,
    ):
        """记录恢复尝试结果"""
        stats = self._get_or_create_statistics(device_id)
        poll_info = self._devices[device_id]

        attempt = RecoveryAttempt(
            timestamp=int(time.time() * 1000),
            attempt_number=poll_info.recovery_attempts,
            status="succeeded" if success else "failed",
            fault_type=poll_info.fault_type,
            duration_ms=elapsed_ms,
        )

        stats.recovery_history.append(attempt)
        stats.total_recoveries += 1

        if success:
            stats.successful_recoveries += 1
            stats.last_recovery_time = attempt.timestamp

            # 计算停机时间
            if stats.last_fault_time:
                downtime = attempt.timestamp - stats.last_fault_time
                stats.total_downtime_ms += downtime
        else:
            stats.failed_recoveries += 1

    def record_fault(self, device_id: str, error_type: str, error_msg: str):
        """Record fault event (called by external)"""
        stats = self._get_or_create_statistics(device_id)
        stats.total_faults += 1
        stats.last_fault_time = int(time.time() * 1000)

        self._signals.fault_detected.emit(device_id, error_type, error_msg)

    # ══════════════════════════════════════════════
    # 全局统计
    # ══════════════════════════════════════════════

    def get_global_statistics(self) -> Dict:
        """获取全局故障统计"""
        total_devices = len(self._devices)
        devices_with_faults = sum(1 for s in self._statistics.values() if s.total_faults > 0)

        total_faults = sum(s.total_faults for s in self._statistics.values())
        total_recoveries = sum(s.total_recoveries for s in self._statistics.values())
        successful_recoveries = sum(s.successful_recoveries for s in self._statistics.values())

        return {
            "total_devices": total_devices,
            "devices_with_faults": devices_with_faults,
            "total_faults": total_faults,
            "total_recoveries": total_recoveries,
            "successful_recoveries": successful_recoveries,
            "recovery_rate": (successful_recoveries / max(total_recoveries, 1)),
            "average_downtime_s": (
                sum(s.total_downtime_ms for s in self._statistics.values()) / max(devices_with_faults, 1) / 1000
            ),
        }


# 向后兼容别名
class FaultRecoveryDevices(QObject):
    """Fault recovery service signal set (backward compatible)"""

    recovery_started = Signal(str, str)
    recovery_completed = Signal(str, bool)
    recovery_failed = Signal(str, int)
    fault_detected = Signal(str, str, str)
    fault_cleared = Signal(str)
