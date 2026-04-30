# -*- coding: utf-8 -*-
"""
Historical data recorder service (v2.0 DataBus订阅版)

规范控制点⑥: 数据库层通过DataBus订阅获取数据，实现完全解耦

旧模式:
    直接调用 record_from_device() / record()

新模式:
    通信层 → DataBus.publish_device_data() → _on_data_updated() → record_from_device()
"""

import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.foundation.data_bus import DataBus
from core.utils.logger import get_logger

from .models import DatabaseManager
from .repository.historical_repository import HistoricalDataRepository

logger = get_logger(__name__)


class HistoricalDataRecorder:
    """
    Buffer and persist historical device data points (v2.0 DataBus订阅版)

    核心变更:
    - 新增 subscribe_to_databus() / unsubscribe_from_databus()
    - 通过 DataBus 信号自动获取数据，无需直接调用
    - 保留 record() / record_from_device() 作为向后兼容接口
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db_manager = db_manager
        self._enabled = True
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        self._auto_flush = True
        self._lock: threading.Lock = threading.Lock()
        self._is_subscribed = False
        self._record_count = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def is_subscribed(self) -> bool:
        return self._is_subscribed

    def subscribe_to_databus(self) -> None:
        """订阅 DataBus 数据更新信号（规范控制点⑥）"""
        if self._is_subscribed:
            return

        bus = DataBus.instance()
        bus.subscribe('device_data_updated', self._on_data_updated)
        self._is_subscribed = True
        logger.info("HistoricalDataRecorder 已订阅 DataBus.device_data_updated")

    def unsubscribe_from_databus(self) -> None:
        """取消订阅 DataBus"""
        if not self._is_subscribed:
            return

        bus = DataBus.instance()
        bus.unsubscribe('device_data_updated', self._on_data_updated)
        self._is_subscribed = False
        logger.info("HistoricalDataRecorder 已取消订阅 DataBus")

    def _on_data_updated(self, device_id: str, data: Dict) -> None:
        """DataBus 数据更新回调"""
        try:
            if self._enabled:
                self.record_from_device(device_id, data)
        except Exception as e:
            logger.debug("HistoricalDataRecorder 数据记录异常: %s", e)

    def _with_repository(self, fn):
        with self._lock:
            repo = HistoricalDataRepository(self._db_manager.get_session())
            try:
                result = fn(repo)
                return result
            finally:
                repo.close_session()

    def record(
        self,
        device_id: str,
        parameter_name: str,
        value: float,
        unit: str = "",
        raw_value: Optional[int] = None,
        quality: int = 0,
    ) -> bool:
        if not self._enabled:
            return False

        self._buffer.append(
            {
                "device_id": device_id,
                "parameter_name": parameter_name,
                "value": value,
                "unit": unit,
                "raw_value": raw_value,
                "quality": quality,
            }
        )
        self._record_count += 1

        if self._auto_flush and len(self._buffer) >= self._buffer_size:
            return self.flush()
        return True

    def record_batch(self, data_points: List[Dict[str, Any]]) -> int:
        if not self._enabled:
            return 0

        try:
            return self._with_repository(lambda r: r.batch_create(data_points))
        except Exception:
            logger.exception("批量记录历史数据失败")
            return 0

    def record_from_device(self, device_id: str, data: Dict[str, Any]) -> int:
        if not self._enabled:
            return 0

        data_points = []
        for parameter_name, parameter_data in data.items():
            if not isinstance(parameter_data, dict):
                continue
            data_points.append(
                {
                    "device_id": device_id,
                    "parameter_name": parameter_name,
                    "value": parameter_data.get("value", 0),
                    "unit": parameter_data.get("unit", ""),
                    "raw_value": parameter_data.get("raw"),
                    "quality": parameter_data.get("quality", 0),
                }
            )

        if not data_points:
            return 0

        return self.record_batch(data_points)

    def flush(self) -> bool:
        if not self._buffer:
            return True

        buffered = list(self._buffer)
        try:
            self._with_repository(lambda r: r.batch_create(buffered))
            self._buffer.clear()
            logger.debug("刷新 %s 条历史数据到数据库", len(buffered))
            return True
        except Exception:
            logger.exception("刷新历史数据失败")
            return False

    def get_latest_data(self, device_id: str) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = {}
            for data in self._with_repository(lambda r: r.get_latest_by_device(device_id)):
                result[data.parameter_name] = {
                    "value": data.value,
                    "unit": data.unit,
                    "timestamp": data.timestamp,
                    "quality": data.quality,
                }
            return result
        except Exception:
            logger.exception("获取最新数据失败: %s", device_id)
            return {}

    def get_data_for_chart(
        self, device_id: str, parameter: str, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        try:
            return [
                {"timestamp": data.timestamp, "value": data.value, "unit": data.unit}
                for data in self._with_repository(
                    lambda r: r.get_by_time_range(device_id, start_time, end_time, parameter)
                )
            ]
        except Exception:
            logger.exception("获取图表数据失败: %s %s", device_id, parameter)
            return []

    def cleanup_old_data(self, days: int = 30) -> int:
        try:
            count = self._with_repository(lambda r: r.cleanup_old_data(days))
            logger.info("清理了 %s 条过期历史数据，保留天数=%s", count, days)
            return count
        except Exception:
            logger.exception("清理过期数据失败")
            return 0

    def close(self) -> None:
        self.unsubscribe_from_databus()
        self.flush()
        logger.info("历史数据记录器已关闭 [记录总数=%d]", self._record_count)
