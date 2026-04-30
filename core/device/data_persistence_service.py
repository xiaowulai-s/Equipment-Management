# -*- coding: utf-8 -*-
"""
数据持久化服务 (v2.0 DataBus订阅版)

规范控制点⑥: 数据库层通过DataBus订阅获取数据，实现完全解耦

旧模式 (v1.0):
    PollingTask → DataPersistenceService.persist_data() (直接调用)

新模式 (v2.0):
    通信层 → DataBus.publish_device_data() → DataPersistenceService._on_data_updated() (订阅)

数据流:
    通信层 → 解析层 → DataBus → [UI订阅者, DB订阅者, 报警订阅者]
                                    ↑
                            DataPersistenceService
"""

import threading
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QTimer

from core.data import DatabaseManager, HistoricalDataRepository
from core.foundation.data_bus import DataBus
from core.utils.logger import get_logger

logger = get_logger(__name__)

MAX_BUFFER_SIZE = 10000


class DataPersistenceService:
    """
    数据持久化服务 (v2.0 DataBus订阅版)

    核心变更:
    - 不再由 PollingTask 直接调用 persist_data()
    - 通过 DataBus.subscribe('device_data_updated') 自动获取数据
    - 保留 persist_data() 方法作为向后兼容接口（内部仍可用）
    - 启动时自动订阅 DataBus，停止时自动取消订阅
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        flush_interval: int = 5000,
        auto_subscribe: bool = True,
    ) -> None:
        self._db_manager = db_manager
        self._data_buffer: List[Tuple[str, str, float, str]] = []
        self._buffer_flush_timer = QTimer()
        self._buffer_flush_timer.timeout.connect(self.flush)
        self._buffer_flush_interval = flush_interval
        self._auto_subscribe = auto_subscribe
        self._is_subscribed = False
        self._lock = threading.Lock()
        self._record_count = 0
        self._drop_count = 0

    def start(self) -> None:
        self._buffer_flush_timer.start(self._buffer_flush_interval)

        if self._auto_subscribe:
            self.subscribe_to_databus()

        logger.info(
            "数据持久化服务已启动 [订阅模式=%s, 刷新间隔=%dms]",
            self._auto_subscribe, self._buffer_flush_interval,
        )

    def stop(self) -> None:
        try:
            self._buffer_flush_timer.stop()
        except RuntimeError:
            pass

        self.unsubscribe_from_databus()

        logger.info(
            "数据持久化服务已停止 [记录=%d, 丢弃=%d]",
            self._record_count, self._drop_count,
        )

    def subscribe_to_databus(self) -> None:
        """
        订阅 DataBus 数据更新信号（规范控制点⑥核心方法）

        数据流: DataBus.device_data_updated → _on_data_updated → persist_data
        """
        if self._is_subscribed:
            return

        bus = DataBus.instance()
        bus.subscribe('device_data_updated', self._on_data_updated)
        self._is_subscribed = True
        logger.info("已订阅 DataBus.device_data_updated")

    def unsubscribe_from_databus(self) -> None:
        """取消订阅 DataBus"""
        if not self._is_subscribed:
            return

        bus = DataBus.instance()
        bus.unsubscribe('device_data_updated', self._on_data_updated)
        self._is_subscribed = False
        logger.info("已取消订阅 DataBus.device_data_updated")

    def _on_data_updated(self, device_id: str, data: Dict) -> None:
        """
        DataBus 数据更新回调（规范控制点⑥ — DB订阅者）

        此方法由 DataBus 信号触发，运行在发射信号的线程中。
        由于 DataBus Signal 通过 Qt 事件队列跨线程，
        实际执行在主线程（安全操作数据库）。
        """
        try:
            self.persist_data(device_id, data)
        except Exception as e:
            self._drop_count += 1
            if self._drop_count % 100 == 1:
                logger.warning(
                    "持久化数据丢弃 [累计=%d, 原因=%s]",
                    self._drop_count, str(e),
                )

    def persist_data(self, device_id: str, data: Dict) -> None:
        """持久化数据到缓冲区（保留向后兼容接口）"""
        with self._lock:
            for param_name, param_info in data.items():
                if isinstance(param_info, dict) and "value" in param_info:
                    try:
                        value = float(param_info["value"])
                    except (ValueError, TypeError):
                        continue
                    self._data_buffer.append(
                        (device_id, param_name, value, param_info.get("unit", ""))
                    )
                    self._record_count += 1

            if len(self._data_buffer) >= MAX_BUFFER_SIZE:
                self.flush()

    def flush(self) -> None:
        """刷新数据缓冲区到数据库"""
        with self._lock:
            if not self._data_buffer:
                return
            buffer_copy = list(self._data_buffer)
            self._data_buffer.clear()

        try:
            with self._db_manager.session() as session:
                repo = HistoricalDataRepository(session)
                data_points = [
                    {"device_id": d[0], "parameter_name": d[1], "value": d[2], "unit": d[3]}
                    for d in buffer_copy
                ]
                count = repo.batch_create(data_points)
                logger.debug("批量写入 %d 条历史数据", count)

        except Exception as e:
            logger.error("批量写入历史数据失败", error=str(e))

    @property
    def buffer_size(self) -> int:
        return len(self._data_buffer)

    @property
    def is_subscribed(self) -> bool:
        return self._is_subscribed

    def get_statistics(self) -> dict:
        return {
            "record_count": self._record_count,
            "drop_count": self._drop_count,
            "buffer_size": len(self._data_buffer),
            "is_subscribed": self._is_subscribed,
            "flush_interval_ms": self._buffer_flush_interval,
        }
