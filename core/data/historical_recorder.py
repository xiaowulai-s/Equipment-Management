# -*- coding: utf-8 -*-
"""Historical data recorder service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.utils.logger import get_logger

from .models import DatabaseManager
from .repository.historical_repository import HistoricalDataRepository

logger = get_logger(__name__)


class HistoricalDataRecorder:
    """Buffer and persist historical device data points."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db_manager = db_manager
        self._repository: Optional[HistoricalDataRepository] = None
        self._enabled = True
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        self._auto_flush = True

    @property
    def enabled(self) -> bool:
        """Return whether recording is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def _get_repository(self) -> HistoricalDataRepository:
        """Return a lazily created repository instance."""
        if self._repository is None:
            self._repository = HistoricalDataRepository(self._db_manager.get_session())
        return self._repository

    def record(
        self,
        device_id: str,
        parameter_name: str,
        value: float,
        unit: str = "",
        raw_value: Optional[int] = None,
        quality: int = 0,
    ) -> bool:
        """Append one data point to the recorder buffer."""
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

        if self._auto_flush and len(self._buffer) >= self._buffer_size:
            return self.flush()
        return True

    def record_batch(self, data_points: List[Dict[str, Any]]) -> int:
        """Persist a batch of data points immediately."""
        if not self._enabled:
            return 0

        try:
            return self._get_repository().batch_create(data_points)
        except Exception:
            if self._repository is not None:
                self._repository._session.rollback()
            logger.exception("批量记录历史数据失败")
            return 0

    def record_from_device(self, device_id: str, data: Dict[str, Any]) -> int:
        """Convert a device data payload into historical samples."""
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
                    "raw_value": parameter_data.get("raw_value"),
                    "quality": parameter_data.get("quality", 0),
                }
            )

        if not data_points:
            return 0

        return self.record_batch(data_points)

    def flush(self) -> bool:
        """Persist buffered data points."""
        if not self._buffer:
            return True

        buffered = list(self._buffer)
        try:
            self._get_repository().batch_create(buffered)
            self._buffer.clear()
            logger.debug("刷新 %s 条历史数据到数据库", len(buffered))
            return True
        except Exception:
            if self._repository is not None:
                self._repository._session.rollback()
            logger.exception("刷新历史数据失败")
            return False

    def get_latest_data(self, device_id: str) -> Dict[str, Any]:
        """Return the latest sample for each device parameter."""
        try:
            result: Dict[str, Any] = {}
            for data in self._get_repository().get_latest_by_device(device_id):
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
        """Return historical samples formatted for chart rendering."""
        try:
            return [
                {"timestamp": data.timestamp, "value": data.value, "unit": data.unit}
                for data in self._get_repository().get_by_time_range(device_id, start_time, end_time, parameter)
            ]
        except Exception:
            logger.exception("获取图表数据失败: %s %s", device_id, parameter)
            return []

    def cleanup_old_data(self, days: int = 30) -> int:
        """Delete old historical data outside the retention window."""
        try:
            count = self._get_repository().cleanup_old_data(days)
            logger.info("清理了 %s 条过期历史数据，保留天数=%s", count, days)
            return count
        except Exception:
            logger.exception("清理过期数据失败")
            return 0

    def close(self) -> None:
        """Flush pending data and release any cached repository session."""
        self.flush()
        if self._repository is not None:
            self._repository._session.close()
            self._repository = None
        logger.info("历史数据记录器已关闭")
