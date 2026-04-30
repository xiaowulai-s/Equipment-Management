# -*- coding: utf-8 -*-
"""
指数退避重连策略（Exponential Backoff Reconnect Policy）

规范控制点④要求: 实现指数退避重连算法

算法:
    delay = min(initial_delay * (multiplier ^ attempt), max_delay) + jitter

    其中 jitter 为随机抖动，避免多网关同时重连导致的"惊群效应"

使用方式:
    policy = ReconnectPolicy(
        initial_delay_ms=1000,
        max_delay_ms=30000,
        multiplier=2.0,
        max_attempts=10
    )

    while policy.should_retry():
        delay = policy.next_delay()
        time.sleep(delay / 1000.0)
        if try_connect():
            policy.reset()
            break

    if policy.is_exhausted:
        logger.error("重连次数耗尽")
"""

import logging
import random
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ReconnectPolicy:
    """
    指数退避重连策略

    特性:
    1. 指数退避: 每次重连延迟翻倍，避免频繁重连消耗资源
    2. 上限截断: 延迟不超过 max_delay_ms，防止等待过久
    3. 随机抖动: 加入 jitter 避免多网关同时重连（惊群效应）
    4. 最大重试: 超过 max_attempts 后标记为耗尽
    5. 手动重置: 连接成功后调用 reset() 重置计数器
    6. 线程安全: 所有状态操作加锁
    """

    DEFAULT_INITIAL_DELAY_MS = 1000
    DEFAULT_MAX_DELAY_MS = 30000
    DEFAULT_MULTIPLIER = 2.0
    DEFAULT_MAX_ATTEMPTS = 10
    DEFAULT_JITTER_FACTOR = 0.1

    def __init__(
        self,
        initial_delay_ms: int = DEFAULT_INITIAL_DELAY_MS,
        max_delay_ms: int = DEFAULT_MAX_DELAY_MS,
        multiplier: float = DEFAULT_MULTIPLIER,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        jitter_factor: float = DEFAULT_JITTER_FACTOR,
    ):
        if initial_delay_ms <= 0:
            raise ValueError(f"initial_delay_ms 必须大于0, 当前值: {initial_delay_ms}")
        if max_delay_ms < initial_delay_ms:
            raise ValueError(f"max_delay_ms 不能小于 initial_delay_ms")
        if multiplier <= 1.0:
            raise ValueError(f"multiplier 必须大于1.0, 当前值: {multiplier}")
        if max_attempts <= 0:
            raise ValueError(f"max_attempts 必须大于0, 当前值: {max_attempts}")
        if not (0.0 <= jitter_factor < 1.0):
            raise ValueError(f"jitter_factor 必须在 [0, 1) 范围内, 当前值: {jitter_factor}")

        self._initial_delay_ms = initial_delay_ms
        self._max_delay_ms = max_delay_ms
        self._multiplier = multiplier
        self._max_attempts = max_attempts
        self._jitter_factor = jitter_factor

        self._attempt = 0
        self._last_delay_ms = 0
        self._last_attempt_time: Optional[float] = None
        self._total_wait_time_ms = 0
        self._lock = threading.Lock()

    def should_retry(self) -> bool:
        with self._lock:
            return self._attempt < self._max_attempts

    def next_delay(self) -> int:
        """
        计算下一次重连的延迟时间（毫秒）

        算法:
            base_delay = initial_delay * multiplier ^ attempt
            capped_delay = min(base_delay, max_delay)
            jitter = random(-jitter_factor * capped_delay, +jitter_factor * capped_delay)
            final_delay = capped_delay + jitter

        Returns:
            延迟时间（毫秒），如果已耗尽则返回 -1
        """
        with self._lock:
            if self._attempt >= self._max_attempts:
                logger.warning("重连次数已耗尽 (attempt=%d, max=%d)", self._attempt, self._max_attempts)
                return -1

            base_delay = self._initial_delay_ms * (self._multiplier ** self._attempt)
            capped_delay = min(base_delay, self._max_delay_ms)

            jitter = 0.0
            if self._jitter_factor > 0:
                jitter_range = capped_delay * self._jitter_factor
                jitter = random.uniform(-jitter_range, jitter_range)

            final_delay = max(0, int(capped_delay + jitter))

            self._attempt += 1
            self._last_delay_ms = final_delay
            self._last_attempt_time = time.monotonic()
            self._total_wait_time_ms += final_delay

            logger.info(
                "重连策略: 第%d次重试, 延迟=%dms (基数=%.0fms, 上限=%dms, 抖动=%.1fms)",
                self._attempt,
                final_delay,
                base_delay,
                self._max_delay_ms,
                jitter,
            )

            return final_delay

    def reset(self):
        with self._lock:
            if self._attempt > 0:
                logger.info(
                    "重连策略已重置 (之前重试=%d次, 累计等待=%.1fs)",
                    self._attempt,
                    self._total_wait_time_ms / 1000.0,
                )
            self._attempt = 0
            self._last_delay_ms = 0
            self._last_attempt_time = None
            self._total_wait_time_ms = 0

    @property
    def attempt(self) -> int:
        with self._lock:
            return self._attempt

    @property
    def is_exhausted(self) -> bool:
        with self._lock:
            return self._attempt >= self._max_attempts

    @property
    def last_delay_ms(self) -> int:
        with self._lock:
            return self._last_delay_ms

    @property
    def remaining_attempts(self) -> int:
        with self._lock:
            return max(0, self._max_attempts - self._attempt)

    def get_statistics(self) -> dict:
        with self._lock:
            return {
                "attempt": self._attempt,
                "max_attempts": self._max_attempts,
                "remaining_attempts": max(0, self._max_attempts - self._attempt),
                "is_exhausted": self._attempt >= self._max_attempts,
                "last_delay_ms": self._last_delay_ms,
                "total_wait_time_ms": self._total_wait_time_ms,
                "initial_delay_ms": self._initial_delay_ms,
                "max_delay_ms": self._max_delay_ms,
                "multiplier": self._multiplier,
                "jitter_factor": self._jitter_factor,
            }

    @classmethod
    def from_dict(cls, config: dict) -> 'ReconnectPolicy':
        return cls(
            initial_delay_ms=config.get("initial_delay_ms", cls.DEFAULT_INITIAL_DELAY_MS),
            max_delay_ms=config.get("max_delay_ms", cls.DEFAULT_MAX_DELAY_MS),
            multiplier=config.get("multiplier", cls.DEFAULT_MULTIPLIER),
            max_attempts=config.get("max_attempts", cls.DEFAULT_MAX_ATTEMPTS),
            jitter_factor=config.get("jitter_factor", cls.DEFAULT_JITTER_FACTOR),
        )

    def __repr__(self) -> str:
        return (
            f"ReconnectPolicy(attempt={self._attempt}/{self._max_attempts}, "
            f"delay={self._initial_delay_ms}ms*{self._multiplier}^n, "
            f"max={self._max_delay_ms}ms)"
        )
