# -*- coding: utf-8 -*-
"""
异步轮询工作器 - 管理设备轮询任务的提交和结果分发
Async Polling Worker - Manages task submission and result dispatch

职责：
- 接收来自DeviceManager的轮询请求
- 将任务提交到QThreadPool
- 转发任务结果信号给DeviceManager
- 统计和监控性能指标
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QThreadPool, Signal

from .polling_task import DevicePollingTask


class AsyncPollingWorker(QObject):
    """
    异步轮询工作器 - 在主线程中运行，管理工作线程池

    设计原则：
    1. 此对象在主线程创建（确保Signal连接安全）
    2. 任务提交到QThreadPool（自动分配工作线程）
    3. 通过Signal/Slot跨线程传递结果（类型安全）
    4. 统一管理所有轮询任务的生命周期
    """

    # ══════════════════════════════════════════════
    # 输出信号（转发给DeviceManager）
    # ══════════════════════════════════════════════

    device_data_updated = Signal(str, dict, float)  # device_id, data, response_time_ms
    device_poll_failed = Signal(str, str, str)  # device_id, error_type, error_msg
    device_poll_timeout = Signal(str, float)  # device_id, elapsed_ms
    batch_poll_completed = Signal(int)  # success_count

    # 内部性能监控信号
    _performance_warning = Signal(str, str)  # device_id, warning_msg

    def __init__(
        self,
        parent: Optional[QObject] = None,
        max_thread_count: int = 4,
    ):
        super().__init__(parent)

        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(max_thread_count)

        # 运行时统计
        self._pending_tasks: int = 0
        self._success_count: int = 0
        self._fail_count: int = 0
        self._total_poll_time_ms: float = 0.0

        # 设备缓存引用（由外部设置）
        self._devices: Dict[str, Any] = {}
        self._persistence_svc: Any = None
        self._fault_recovery_mgr: Any = None

    def set_dependencies(
        self,
        devices: Dict[str, Any],
        persistence_svc: Any,
        fault_recovery_mgr: Any,
    ) -> None:
        """设置依赖项（在DeviceManager初始化后调用）"""
        self._devices = devices
        self._persistence_svc = persistence_svc
        self._fault_recovery_mgr = fault_recovery_mgr

    @property
    def active_task_count(self) -> int:
        """当前正在执行的任务数"""
        return self._pending_tasks

    @property
    def thread_pool(self) -> QThreadPool:
        """获取底层线程池（用于监控）"""
        return self._thread_pool

    def submit_poll_task(self, device_id: str) -> bool:
        """
        提交单个设备的异步轮询任务

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 是否成功提交（False表示设备不存在或已满载）
        """
        if device_id not in self._devices:
            return False

        poll_info = self._devices[device_id]
        if not hasattr(poll_info, "device"):
            return False

        device_obj = poll_info.device
        protocol = getattr(device_obj, "_protocol", None)

        # 创建轮询任务
        task = DevicePollingTask(
            device_id=device_id,
            device_obj=device_obj,
            protocol=protocol,
            persistence_svc=self._persistence_svc,
            fault_recovery_mgr=self._fault_recovery_mgr,
        )

        # 连接任务信号到本对象的槽函数（跨线程）
        task.signals.poll_success.connect(self._on_poll_success)
        task.signals.poll_failed.connect(self._on_poll_failed)
        task.signals.poll_timeout.connect(self._on_poll_timeout)
        task.signals.performance_warning.connect(self._on_performance_warning)

        # 提交到线程池
        self._pending_tasks += 1
        self._thread_pool.start(task)

        return True

    def submit_batch_poll(self, device_ids: list) -> int:
        """
        批量提交多个设备的轮询任务

        Args:
            device_ids: 需要轮询的设备ID列表

        Returns:
            int: 成功提交的任务数量
        """
        submitted = 0
        for device_id in device_ids:
            if self.submit_poll_task(device_id):
                submitted += 1

        return submitted

    # ══════════════════════════════════════════════
    # 槽函数：处理任务结果（在工作线程中触发，转发到主线程）
    # ══════════════════════════════════════════════

    def _on_poll_success(
        self,
        device_id: str,
        data: dict,
        response_time_ms: float,
    ) -> None:
        """处理轮询成功（从工作线程接收）"""
        self._pending_tasks -= 1
        self._success_count += 1
        self._total_poll_time_ms += response_time_ms

        # 更新设备的poll_info统计
        if device_id in self._devices:
            from core.device.polling import DevicePollInfo

            poll_info = self._devices[device_id]
            if isinstance(poll_info, DevicePollInfo):
                current_time = int(time.time() * 1000)
                poll_info.on_success()
                poll_info.update_poll_time(current_time, response_time_ms)
                # 触发故障恢复检查
                if self._fault_recovery_mgr is not None:
                    try:
                        self._fault_recovery_mgr.check_and_recover(device_id)
                    except Exception:
                        pass

        # 转发给DeviceManager（最终到达UI层）
        self.device_data_updated.emit(device_id, data, response_time_ms)

    def _on_poll_failed(
        self,
        device_id: str,
        error_type: str,
        error_msg: str,
    ) -> None:
        """处理轮询失败（从工作线程接收）"""
        self._pending_tasks -= 1
        self._fail_count += 1

        # 更新设备的poll_info错误状态
        if device_id in self._devices:
            from core.device.polling import DevicePollInfo

            poll_info = self._devices[device_id]
            if isinstance(poll_info, DevicePollInfo):
                poll_info.on_error(error_type, error_msg)

        # 转发给DeviceManager
        self.device_poll_failed.emit(device_id, error_type, error_msg)

    def _on_poll_timeout(
        self,
        device_id: str,
        elapsed_ms: float,
    ) -> None:
        """处理轮询超时（从工作线程接收）"""
        self._pending_tasks -= 1
        self._fail_count += 1

        # 更新设备的poll_info超时状态
        if device_id in self._devices:
            from core.device.polling import DevicePollInfo

            poll_info = self._devices[device_id]
            if isinstance(poll_info, DevicePollInfo):
                poll_info.on_error("poll_timeout", "轮询无数据返回")

        # 转发给DeviceManager
        self.device_poll_timeout.emit(device_id, elapsed_ms)

    def _on_performance_warning(
        self,
        device_id: str,
        warning_msg: str,
    ) -> None:
        """性能警告（仅记录日志，不转发到UI）"""
        import logging

        logger = logging.getLogger(__name__)
        logger.warning("[PERF] %s: %s", device_id, warning_msg)

        # 可选：转发给调试模块
        self._performance_warning.emit(device_id, warning_msg)

    def shutdown(self, timeout_ms: int = 3000) -> None:
        """
        关闭工作器，等待所有任务完成

        Args:
            timeout_ms: 最大等待时间（毫秒），0表示不等待
        """
        if timeout_ms > 0:
            self._thread_pool.waitForDone(timeout_ms)
        else:
            self._thread_pool.clear()

        # 打印统计信息
        total = self._success_count + self._fail_count
        avg_time = self._total_poll_time_ms / max(total, 1)

        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            "AsyncPollingWorker关闭: 成功=%d 失败=%d 平均耗时=%.1fms",
            self._success_count,
            self._fail_count,
            avg_time,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取运行时统计信息"""
        return {
            "active_tasks": self._pending_tasks,
            "max_threads": self._thread_pool.maxThreadCount(),
            "success_count": self._success_count,
            "fail_count": self._fail_count,
            "avg_response_time_ms": (self._total_poll_time_ms / max(self._success_count + self._fail_count, 1)),
        }
