# -*- coding: utf-8 -*-
"""
轮询数据类和调度逻辑
Polling data classes and scheduling logic - extracted from DeviceManager
"""

import time
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Deque, Dict, List, Optional

from core.constants import FAULT_TYPE_NAMES
from core.utils.logger import get_logger

logger = get_logger(__name__)


class PollPriority(IntEnum):
    """轮询优先级"""

    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class PollStatistics:
    """轮询统计信息"""

    total_polls: int = 0
    successful_polls: int = 0
    failed_polls: int = 0
    response_times: Deque[float] = field(default_factory=lambda: deque(maxlen=10))

    def record_success(self, response_time: float = 0):
        self.total_polls += 1
        self.successful_polls += 1
        if response_time > 0:
            self.response_times.append(response_time)

    def record_failure(self):
        self.total_polls += 1
        self.failed_polls += 1

    @property
    def success_rate(self) -> float:
        if self.total_polls == 0:
            return 0.0
        return self.successful_polls / self.total_polls

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)


@dataclass
class FaultInfo:
    """故障诊断信息"""

    fault_type: Optional[str] = None
    fault_start_time: Optional[int] = None
    fault_duration: int = 0
    error_history: Deque[dict] = field(default_factory=lambda: deque(maxlen=20))
    fault_detection_enabled: bool = True

    FAULT_TYPES = FAULT_TYPE_NAMES

    def detect_fault(self, error_type: str, error_msg: str, device_id: str) -> None:
        if not self.fault_detection_enabled:
            return
        if not self.fault_type:
            self.fault_type = error_type
            self.fault_start_time = int(time.time() * 1000)
            logger.info(
                "设备故障检测到",
                device_id=device_id,
                fault_type=self.FAULT_TYPES.get(error_type, error_type),
                error_msg=error_msg,
            )
        self.error_history.append(
            {
                "timestamp": int(time.time() * 1000),
                "error_type": error_type,
                "error_msg": error_msg,
            }
        )
        if self.fault_start_time:
            self.fault_duration = int(time.time() * 1000) - self.fault_start_time

    def clear_fault(self, device_id: str) -> dict:
        if not self.fault_type:
            return {}
        summary = {
            "fault_type": self.fault_type,
            "start_time": self.fault_start_time,
            "duration": self.fault_duration,
        }
        logger.info(
            "设备故障恢复",
            device_id=device_id,
            fault_type=self.FAULT_TYPES.get(self.fault_type, self.fault_type),
            duration=self.fault_duration,
        )
        self.fault_type = None
        self.fault_start_time = None
        self.fault_duration = 0
        return summary


@dataclass
class RecoveryConfig:
    """恢复配置和状态"""

    recovery_mode: str = "auto"
    max_recovery_attempts: int = 5
    auto_reconnect_enabled: bool = False
    recovery_enabled: bool = True
    recovery_status: str = "none"
    recovery_attempts: int = 0
    recovery_history: List[dict] = field(default_factory=list)


class DevicePollInfo:
    """
    设备轮询信息 (精简版)

    职责: 核心调度逻辑、动态间隔调整、退避策略
    统计/故障/恢复逻辑委托给对应的数据类
    """

    def __init__(self, device, priority: PollPriority = PollPriority.NORMAL):
        self.device = device
        self.priority = priority
        self.last_poll_time: int = 0
        self.poll_interval: int = 1000
        self.next_poll_time: int = 0
        self.consecutive_errors: int = 0
        self.max_errors: int = 3
        self.backoff_time: int = 0
        self.min_interval: int = 100
        self.max_interval: int = 10000
        self.target_response_time: float = 50
        self.adjustment_factor: float = 0.1
        self.statistics = PollStatistics()
        self.fault_info = FaultInfo()
        self.recovery_config = RecoveryConfig()

    @property
    def FAULT_TYPES(self):
        return FaultInfo.FAULT_TYPES

    def should_poll(self, current_time: int) -> bool:
        if self.backoff_time > 0 and current_time < self.backoff_time:
            return False
        return current_time >= self.next_poll_time

    def update_poll_time(self, current_time: int, response_time: float = 0):
        self.last_poll_time = current_time
        if response_time > 0:
            self.statistics.record_success(response_time)
            self._adjust_poll_interval()
        if not self.statistics.response_times:
            intervals = {PollPriority.HIGH: 200, PollPriority.NORMAL: 1000, PollPriority.LOW: 5000}
            self.poll_interval = intervals.get(self.priority, 1000)
        self.poll_interval = max(self.min_interval, min(self.poll_interval, self.max_interval))
        self.next_poll_time = current_time + int(self.poll_interval)

    def _adjust_poll_interval(self):
        avg_response = self.statistics.avg_response_time
        if avg_response == 0:
            return
        if avg_response < self.target_response_time:
            self.poll_interval *= 1 - self.adjustment_factor
        elif avg_response > self.target_response_time * 2:
            self.poll_interval *= 1 + self.adjustment_factor
        logger.debug(
            "动态调整轮询间隔",
            device_id=self.device.get_device_id(),
            avg_response=avg_response,
            new_interval=self.poll_interval,
            target_response=self.target_response_time,
        )

    def on_success(self):
        if self.consecutive_errors > 0:
            logger.info(
                "设备轮询恢复",
                device_id=self.device.get_device_id(),
                previous_errors=self.consecutive_errors,
            )
        self.fault_info.clear_fault(self.device.get_device_id())
        self.consecutive_errors = 0
        self.backoff_time = 0
        self.recovery_config.recovery_status = "none"

    def on_error(self, error_type="unknown", error_msg=""):
        self.consecutive_errors += 1
        self.statistics.record_failure()
        self.fault_info.detect_fault(error_type, error_msg, self.device.get_device_id())
        if self.consecutive_errors >= self.max_errors:
            backoff_seconds = min(2 ** (self.consecutive_errors - self.max_errors), 30)
            self.backoff_time = int(time.time() * 1000) + (backoff_seconds * 1000)
            logger.warning(
                "设备轮询错误过多，进入退避模式",
                device_id=self.device.get_device_id(),
                consecutive_errors=self.consecutive_errors,
                backoff_seconds=backoff_seconds,
            )
            if self.recovery_config.recovery_enabled:
                self._start_recovery()

    def _start_recovery(self):
        if self.recovery_config.recovery_status in ["attempting", "succeeded"]:
            return
        self.recovery_config.recovery_status = "attempting"
        self.recovery_config.recovery_attempts = 0
        logger.info(
            "启动设备故障恢复",
            device_id=self.device.get_device_id(),
            fault_type=self.FAULT_TYPES.get(self.fault_info.fault_type, self.fault_info.fault_type),
        )
        self._attempt_recovery()

    def _attempt_recovery(self):
        rc = self.recovery_config
        if not rc.recovery_enabled or rc.recovery_status != "attempting":
            return
        rc.recovery_attempts += 1
        recovery_entry = {
            "timestamp": int(time.time() * 1000),
            "attempt": rc.recovery_attempts,
            "status": "in_progress",
            "fault_type": self.fault_info.fault_type,
        }
        logger.info(
            "设备恢复尝试",
            device_id=self.device.get_device_id(),
            attempt=rc.recovery_attempts,
            fault_type=self.FAULT_TYPES.get(self.fault_info.fault_type, self.fault_info.fault_type),
        )
        try:
            fault = self.fault_info.fault_type or "unknown"
            if fault in ["communication_timeout", "connection_refused", "device_offline"]:
                success = self.device.reconnect() if hasattr(self.device, "reconnect") else self.device.connect()
            elif fault in ["invalid_response", "protocol_error"]:
                success = self.device.reset() if hasattr(self.device, "reset") else False
            else:
                success = self.device.reconnect() if hasattr(self.device, "reconnect") else self.device.connect()
            if success:
                recovery_entry["status"] = "succeeded"
                recovery_entry["message"] = "恢复成功"
                rc.recovery_status = "succeeded"
                rc.recovery_history.append(recovery_entry)
                logger.info("设备恢复成功", device_id=self.device.get_device_id(), attempt=rc.recovery_attempts)
            else:
                recovery_entry["status"] = "failed"
                recovery_entry["message"] = "恢复失败"
                rc.recovery_history.append(recovery_entry)
                if rc.recovery_attempts >= rc.max_recovery_attempts:
                    rc.recovery_status = "failed"
                    logger.error(
                        "设备恢复失败达到最大尝试次数",
                        device_id=self.device.get_device_id(),
                        max_attempts=rc.max_recovery_attempts,
                    )
                else:
                    backoff_time = min(2 ** (rc.recovery_attempts - 1), 30) * 1000
                    logger.info(
                        "设备恢复失败，稍后重试",
                        device_id=self.device.get_device_id(),
                        attempt=rc.recovery_attempts,
                        backoff_time=backoff_time,
                    )
        except Exception as e:
            recovery_entry["status"] = "failed"
            recovery_entry["message"] = f"恢复异常: {str(e)}"
            rc.recovery_history.append(recovery_entry)
            logger.error(
                "设备恢复过程异常",
                device_id=self.device.get_device_id(),
                attempt=rc.recovery_attempts,
                error=str(e),
            )
            if rc.recovery_attempts >= rc.max_recovery_attempts:
                rc.recovery_status = "failed"

    # ==================== 向后兼容属性代理 ====================

    @property
    def fault_type(self) -> Optional[str]:
        return self.fault_info.fault_type

    @property
    def fault_start_time(self) -> Optional[int]:
        return self.fault_info.fault_start_time

    @property
    def fault_duration(self) -> int:
        return self.fault_info.fault_duration

    @property
    def error_history(self):
        return self.fault_info.error_history

    @property
    def fault_detection_enabled(self) -> bool:
        return self.fault_info.fault_detection_enabled

    @fault_detection_enabled.setter
    def fault_detection_enabled(self, value: bool):
        self.fault_info.fault_detection_enabled = value

    @property
    def recovery_attempts(self) -> int:
        return self.recovery_config.recovery_attempts

    @property
    def recovery_status(self) -> str:
        return self.recovery_config.recovery_status

    @property
    def recovery_mode(self) -> str:
        return self.recovery_config.recovery_mode

    @property
    def recovery_enabled(self) -> bool:
        return self.recovery_config.recovery_enabled

    @recovery_enabled.setter
    def recovery_enabled(self, value: bool):
        self.recovery_config.recovery_enabled = value

    @property
    def auto_reconnect_enabled(self) -> bool:
        return self.recovery_config.auto_reconnect_enabled

    @auto_reconnect_enabled.setter
    def auto_reconnect_enabled(self, value: bool):
        self.recovery_config.auto_reconnect_enabled = value

    @property
    def max_recovery_attempts(self) -> int:
        return self.recovery_config.max_recovery_attempts

    @property
    def recovery_history(self):
        return self.recovery_config.recovery_history


class PollingGroup:
    """轮询组配置"""

    def __init__(
        self, name: str, priority: PollPriority = PollPriority.NORMAL, base_interval: int = 1000, enabled: bool = True
    ):
        self.name = name
        self.priority = priority
        self.base_interval = base_interval
        self.enabled = enabled
        self.device_ids: set = set()
