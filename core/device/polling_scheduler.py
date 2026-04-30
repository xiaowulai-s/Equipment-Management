# -*- coding: utf-8 -*-
"""
轮询调度器 - 管理异步轮询任务
Polling Scheduler - Manages async polling tasks

职责（单一职责原则 SRP）：
- 异步任务提交（QThreadPool）
- 轮询策略（间隔/优先级/分组）
- 性能监控和统计
- 信号发射：轮询结果分发

不属于本类职责：
- 设备CRUD -> DeviceRegistry
- 数据持久化 -> DataPersistenceService
- 故障恢复 -> FaultRecoveryService
- UI更新 -> DeviceManagerFacade
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from core.device.polling import DevicePollInfo, PollPriority, PollingGroup
from core.device.polling_worker import AsyncPollingWorker
from core.utils.logger import get_logger

logger = get_logger("polling_scheduler")


class PollingSchedulerSignals(QObject):
    """轮询调度器信号定义"""

    # 轮询成功（带性能数据）
    poll_success = Signal(str, dict, float)  # device_id, data, response_time_ms

    # 轮询失败
    poll_failed = Signal(str, str, str)  # device_id, error_type, error_msg

    # 轮询超时
    poll_timeout = Signal(str, float)  # device_id, elapsed_ms

    # 批量轮询完成
    batch_poll_completed = Signal(int)  # success_count


class PollingScheduler:
    """
    轮询调度器 - 核心调度组件

    设计要点：
    1. 使用定时器触发调度周期（主线程快速执行）
    2. 实际通信在工作线程池中并行执行
    3. 支持分组轮询和优先级调度
    4. 动态调整轮询间隔（基于响应时间）

    线程模型：
    - 主线程：调度决策（<1ms/周期）
    - 工作线程池：Modbus通信（15-50ms/设备）
    - 通过Qt Signal跨线程安全传递结果
    """

    # 默认配置常量
    DEFAULT_POLL_INTERVAL_MS = 100  # 调度周期（毫秒）
    MIN_POLL_INTERVAL_MS = 50  # 最小调度间隔
    MAX_POLL_INTERVAL_MS = 1000  # 最大调度间隔
    DEFAULT_MAX_THREADS = 4  # 默认最大工作线程数

    def __init__(
        self,
        devices: Dict[str, DevicePollInfo],
        device_groups: Optional[Dict[str, str]] = None,
        polling_groups: Optional[Dict[str, PollingGroup]] = None,
        persistence_svc: Optional[Any] = None,
        fault_recovery_mgr: Optional[Any] = None,
        max_threads: int = DEFAULT_MAX_THREADS,
    ):
        """
        初始化轮询调度器

        Args:
            devices: 设备注册表引用（共享状态）
            device_groups: 设备到分组的映射
            polling_groups: 轮询组配置
            persistence_svc: 数据持久化服务
            fault_recovery_mgr: 故障恢复管理器
            max_threads: 最大工作线程数
        """
        self._devices = devices
        self._device_groups = device_groups or {}
        self._polling_groups = polling_groups or {"default": PollingGroup("default")}
        self._persistence_svc = persistence_svc
        self._fault_recovery_mgr = fault_recovery_mgr

        # 信号对象
        self._signals = PollingSchedulerDevices()

        # 调度定时器
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._schedule_async_polls)
        self._poll_interval = self.DEFAULT_POLL_INTERVAL_MS

        # 异步工作器
        self._async_worker = AsyncPollingWorker(
            parent=None,  # parent稍后设置
            max_thread_count=max_threads,
        )

        # 配置工作器依赖
        self._async_worker.set_dependencies(
            devices=self._devices,
            persistence_svc=self._persistence_svc,
            fault_recovery_mgr=self._fault_recovery_mgr,
        )

        # 连接工作器信号
        self._async_worker.device_data_updated.connect(self._on_poll_success)
        self._async_worker.device_poll_failed.connect(self._on_poll_failed)
        self._async_worker.device_poll_timeout.connect(self._on_poll_timeout)

        # 运行时状态
        self._is_running = False

    # ══════════════════════════════════════════════
    # 属性访问
    # ══════════════════════════════════════════════

    @property
    def signals(self) -> PollingSchedulerSignals:
        """获取信号对象"""
        return self._signals

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    @property
    def poll_interval(self) -> int:
        """当前轮询间隔"""
        return self._poll_interval

    @property
    def active_task_count(self) -> int:
        """当前活跃任务数"""
        return self._async_worker.active_task_count

    # ══════════════════════════════════════════════
    # 生命周期管理
    # ══════════════════════════════════════════════

    def start(self):
        """启动轮询调度器"""
        if self._is_running:
            logger.warning("轮询调度器已在运行")
            return

        self._poll_timer.start(self._poll_interval)
        self._is_running = True
        logger.info(
            "轮询调度器已启动",
            interval_ms=self._poll_interval,
            max_threads=self._async_worker.thread_pool.maxThreadCount(),
        )

    def stop(self):
        """停止轮询调度器"""
        if not self._is_running:
            return

        try:
            self._poll_timer.stop()
        except RuntimeError:
            pass

        self._is_running = False
        logger.info("轮询调度器已停止")

    def set_interval(self, interval_ms: int):
        """
        设置轮询调度间隔

        Args:
            interval_ms: 调度间隔（毫秒），范围 [MIN_POLL_INTERVAL_MS, MAX_POLL_INTERVAL_MS]
        """
        self._poll_interval = max(self.MIN_POLL_INTERVAL_MS, min(interval_ms, self.MAX_POLL_INTERVAL_MS))

        if self._is_running:
            self._poll_timer.setInterval(self._poll_interval)

        logger.debug("轮询间隔已更新", interval_ms=self._poll_interval)

    # ══════════════════════════════════════════════
    # 强制轮询
    # ══════════════════════════════════════════════

    def force_poll(self, device_id: str) -> bool:
        """
        强制立即轮询指定设备（忽略轮询间隔限制）

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 是否成功提交任务
        """
        if device_id not in self._devices:
            return False

        return self._async_worker.submit_poll_task(device_id)

    # ══════════════════════════════════════════════
    # 统计信息
    # ══════════════════════════════════════════════

    def get_statistics(self) -> Dict:
        """
        获取轮询统计信息

        Returns:
            Dict: 包含详细统计数据的字典
        """
        worker_stats = self._async_worker.get_statistics()

        # 汇总所有设备的统计
        total_polls = sum(p.total_polls for p in self._devices.values())
        successful_polls = sum(p.successful_polls for p in self._devices.values())
        failed_polls = sum(p.failed_polls for p in self._devices.values())

        return {
            "scheduler": {
                "is_running": self._is_running,
                "poll_interval_ms": self._poll_interval,
                "total_devices": len(self._devices),
                "total_groups": len(self._polling_groups),
            },
            "worker": worker_stats,
            "aggregated": {
                "total_polls": total_polls,
                "successful_polls": successful_polls,
                "failed_polls": failed_polls,
                "success_rate": (successful_polls / max(total_polls, 1)),
            },
            "devices_by_group": self._get_group_statistics(),
        }

    def _get_group_statistics(self) -> Dict[str, Dict]:
        """获取各分组的统计信息"""
        result = {}
        for group_name, group in self._polling_groups.items():
            result[group_name] = {
                "device_count": len(group.device_ids),
                "enabled": group.enabled,
                "priority": group.priority.name,
            }
        return result

    # ══════════════════════════════════════════════
    # 内部调度逻辑
    # ══════════════════════════════════════════════

    def _schedule_async_polls(self):
        """
        异步轮询调度核心方法

        此方法在主线程中快速执行（<1ms），仅负责任务筛选和提交。
        实际的阻塞式Modbus通信在工作线程池中并行执行。

        性能提升原理：
        - 旧版：顺序轮询7设备 = 7 x 20ms = 140ms（主线程阻塞）
        - 新版：提交7个任务到线程池 ≈ 0.5ms（主线程立即返回）
        - 线程池并行执行所有任务 < 50ms总耗时
        """
        current_time = int(time.time() * 1000)
        devices_to_poll: list = []

        # 快速筛选需要轮询的设备（主线程操作，无I/O）
        for device_id, poll_info in self._devices.items():
            # 1. 检查连接状态
            if poll_info.device.get_status() != DeviceStatus.CONNECTED:
                continue

            # 2. 检查分组状态
            from core.device.device_model import DeviceStatus

            group_name = self._device_groups.get(device_id, "default")
            group = self._polling_groups.get(group_name, None)
            if not group or not group.enabled:
                continue

            # 3. 检查轮询时机
            if not poll_info.should_poll(current_time):
                continue

            devices_to_poll.append(device_id)

        # 批量提交异步轮询任务（立即返回，不阻塞！）
        if devices_to_poll:
            submitted_count = self._async_worker.submit_batch_poll(devices_to_poll)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "异步轮询: 提交 %d 个设备任务 (活跃任务=%d)",
                    submitted_count,
                    self._async_worker.active_task_count,
                )

    # ══════════════════════════════════════════════
    # 结果处理槽函数（从工作线程接收Signal）
    # ══════════════════════════════════════════════

    def _on_poll_success(
        self,
        device_id: str,
        data: dict,
        response_time_ms: float,
    ) -> None:
        """处理轮询成功（转发给外部订阅者）"""
        self._signals.poll_success.emit(device_id, data, response_time_ms)

    def _on_poll_failed(
        self,
        device_id: str,
        error_type: str,
        error_msg: str,
    ) -> None:
        """处理轮询失败（转发给外部订阅者）"""
        self._signals.poll_failed.emit(device_id, error_type, error_msg)

    def _on_poll_timeout(
        self,
        device_id: str,
        elapsed_ms: float,
    ) -> None:
        """处理轮询超时（转发给外部订阅者）"""
        self._signals.poll_timeout.emit(device_id, elapsed_ms)

    # ══════════════════════════════════════════════
    # 清理
    # ══════════════════════════════════════════════

    def cleanup(self, timeout_ms: int = 3000):
        """清理资源"""
        self.stop()

        # 关闭异步工作器
        stats = self._async_worker.shutdown(timeout_ms=timeout_ms)
        logger.info(
            "异步轮询工作器已关闭: 成功=%d 失败=%d 平均耗时=%.1fms",
            stats["success_count"],
            stats["fail_count"],
            stats["avg_response_time_ms"],
        )


# 向后兼容别名
class PollingSchedulerDevices(QObject):
    """轮询调度器信号集合（向后兼容）"""

    poll_success = Signal(str, dict, float)
    poll_failed = Signal(str, str, str)
    poll_timeout = Signal(str, float)
    batch_poll_completed = Signal(int)
