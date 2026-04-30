# -*- coding: utf-8 -*-
"""
心跳管理器（Heartbeat Manager）

规范控制点④要求: 增加应用层心跳包（Keep-alive），
若3次心跳无响应则强制重置Socket链路。

设计思路:
- 与 TCPDriver 的 FC08 心跳协同工作
- TCPDriver 负责发送心跳报文和接收响应
- HeartbeatManager 负责跟踪连续失败次数并决定是否重置连接
- 解耦：HeartbeatManager 不直接操作 Socket，通过信号通知上层

状态机:
    HEALTHY → (1次失败) → WARNING → (2次失败) → CRITICAL → (3次失败) → RESET_REQUIRED
                                                                      ↓
                                                              上层调用 force_reset()
                                                                      ↓
                                                               重建 Socket 连接

使用方式:
    mgr = HeartbeatManager(
        gateway_id="mcgs_gw_1",
        max_failures=3,
        check_interval_ms=10000
    )
    mgr.connection_reset_required.connect(self._on_reset_connection)
    mgr.start()

    # 在心跳响应回调中
    mgr.on_heartbeat_success()

    # 在心跳发送失败回调中
    mgr.on_heartbeat_failure("发送失败")

    # 停止
    mgr.stop()
"""

import logging
import threading
import time
from enum import IntEnum
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class HeartbeatState(IntEnum):
    HEALTHY = 0
    WARNING = 1
    CRITICAL = 2
    RESET_REQUIRED = 3


class HeartbeatManager(QObject):
    """
    应用层心跳管理器

    职责:
    1. 跟踪心跳连续失败次数
    2. 达到阈值时发射 connection_reset_required 信号
    3. 提供心跳健康状态查询
    4. 定时检查心跳超时（即使心跳报文发出但无响应也计数）

    不负责:
    - 发送心跳报文（由 TCPDriver._send_heartbeat() 负责）
    - 重置 Socket（由上层 GatewayEngine 负责）
    """

    DEFAULT_MAX_FAILURES = 3
    DEFAULT_CHECK_INTERVAL_MS = 10000
    DEFAULT_RESPONSE_TIMEOUT_MS = 5000

    connection_reset_required = Signal(str, int)
    heartbeat_state_changed = Signal(str, int)
    heartbeat_timeout = Signal(str, int)

    def __init__(
        self,
        gateway_id: str,
        max_failures: int = DEFAULT_MAX_FAILURES,
        check_interval_ms: int = DEFAULT_CHECK_INTERVAL_MS,
        response_timeout_ms: int = DEFAULT_RESPONSE_TIMEOUT_MS,
        parent=None,
    ):
        super().__init__(parent)

        self._gateway_id = gateway_id
        self._max_failures = max(1, max_failures)
        self._check_interval_ms = max(1000, check_interval_ms)
        self._response_timeout_ms = max(1000, response_timeout_ms)

        self._consecutive_failures = 0
        self._state = HeartbeatState.HEALTHY
        self._last_success_time: Optional[float] = None
        self._last_failure_time: Optional[float] = None
        self._last_send_time: Optional[float] = None
        self._total_successes = 0
        self._total_failures = 0
        self._is_running = False

        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_timeout)

        self._lock = threading.Lock()

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    @property
    def state(self) -> HeartbeatState:
        with self._lock:
            return self._state

    @property
    def consecutive_failures(self) -> int:
        with self._lock:
            return self._consecutive_failures

    @property
    def is_healthy(self) -> bool:
        with self._lock:
            return self._state == HeartbeatState.HEALTHY

    @property
    def is_reset_required(self) -> bool:
        with self._lock:
            return self._state == HeartbeatState.RESET_REQUIRED

    def start(self):
        if self._is_running:
            return

        self._is_running = True
        self._consecutive_failures = 0
        self._state = HeartbeatState.HEALTHY
        self._last_success_time = time.monotonic()

        self._check_timer.start(self._check_interval_ms)
        logger.info(
            "心跳管理器已启动 [%s] 检查间隔=%dms 最大失败=%d",
            self._gateway_id, self._check_interval_ms, self._max_failures,
        )

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False
        self._check_timer.stop()
        logger.info("心跳管理器已停止 [%s]", self._gateway_id)

    def on_heartbeat_sent(self):
        with self._lock:
            self._last_send_time = time.monotonic()

    def on_heartbeat_success(self):
        with self._lock:
            old_state = self._state
            self._consecutive_failures = 0
            self._total_successes += 1
            self._last_success_time = time.monotonic()

            if self._state != HeartbeatState.HEALTHY:
                self._state = HeartbeatState.HEALTHY
                logger.info(
                    "心跳恢复正常 [%s] 之前状态=%s",
                    self._gateway_id, old_state.name,
                )

        if old_state != HeartbeatState.HEALTHY:
            self.heartbeat_state_changed.emit(self._gateway_id, int(HeartbeatState.HEALTHY))

    def on_heartbeat_failure(self, reason: str = ""):
        with self._lock:
            self._consecutive_failures += 1
            self._total_failures += 1
            self._last_failure_time = time.monotonic()

            old_state = self._state
            self._state = self._compute_state()

            logger.warning(
                "心跳失败 [%s] 连续失败=%d/%d 状态=%s→%s 原因=%s",
                self._gateway_id,
                self._consecutive_failures,
                self._max_failures,
                old_state.name,
                self._state.name,
                reason,
            )

        if old_state != self._state:
            self.heartbeat_state_changed.emit(self._gateway_id, int(self._state))

        if self._state == HeartbeatState.RESET_REQUIRED:
            logger.error(
                "心跳连续失败达到阈值 [%s] 连续=%d次 → 需要重置Socket连接",
                self._gateway_id, self._consecutive_failures,
            )
            self.connection_reset_required.emit(self._gateway_id, self._consecutive_failures)

    def _compute_state(self) -> HeartbeatState:
        if self._consecutive_failures >= self._max_failures:
            return HeartbeatState.RESET_REQUIRED
        elif self._consecutive_failures >= self._max_failures - 1:
            return HeartbeatState.CRITICAL
        elif self._consecutive_failures >= 1:
            return HeartbeatState.WARNING
        return HeartbeatState.HEALTHY

    def _check_timeout(self):
        if not self._is_running:
            return

        with self._lock:
            if self._last_send_time is None:
                return

            elapsed = (time.monotonic() - self._last_send_time) * 1000
            if elapsed > self._response_timeout_ms + self._check_interval_ms:
                logger.warning(
                    "心跳超时检测 [%s] 距上次发送已过%.0fms (超时阈值=%dms)",
                    self._gateway_id, elapsed, self._response_timeout_ms,
                )
                self.heartbeat_timeout.emit(self._gateway_id, int(elapsed))

    def reset(self):
        with self._lock:
            self._consecutive_failures = 0
            self._state = HeartbeatState.HEALTHY
            self._last_success_time = time.monotonic()

        self.heartbeat_state_changed.emit(self._gateway_id, int(HeartbeatState.HEALTHY))
        logger.info("心跳管理器已重置 [%s]", self._gateway_id)

    def get_statistics(self) -> dict:
        with self._lock:
            return {
                "gateway_id": self._gateway_id,
                "state": self._state.name,
                "consecutive_failures": self._consecutive_failures,
                "max_failures": self._max_failures,
                "total_successes": self._total_successes,
                "total_failures": self._total_failures,
                "success_rate": (
                    f"{self._total_successes / (self._total_successes + self._total_failures) * 100:.1f}%"
                    if (self._total_successes + self._total_failures) > 0 else "N/A"
                ),
                "last_success_time": self._last_success_time,
                "last_failure_time": self._last_failure_time,
                "is_running": self._is_running,
                "check_interval_ms": self._check_interval_ms,
                "response_timeout_ms": self._response_timeout_ms,
            }

    def __repr__(self) -> str:
        return (
            f"HeartbeatManager(gateway={self._gateway_id}, "
            f"state={self._state.name}, "
            f"failures={self._consecutive_failures}/{self._max_failures})"
        )
