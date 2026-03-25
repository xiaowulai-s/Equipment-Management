# -*- coding: utf-8 -*-
"""
历史数据记录器
Historical Data Recorder
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.utils.logger import get_logger

from .models import DatabaseManager
from .repository.historical_repository import HistoricalDataRepository

logger = get_logger(__name__)


class HistoricalDataRecorder:
    """历史数据记录器 - 负责将设备数据记录到数据库"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化历史数据记录器

        Args:
            db_manager: 数据库管理器实例
        """
        self._db_manager = db_manager
        self._repository: Optional[HistoricalDataRepository] = None
        self._enabled = True
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100  # 缓冲区大小
        self._auto_flush = True  # 自动刷新

    @property
    def enabled(self) -> bool:
        """是否启用记录"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def _get_repository(self) -> HistoricalDataRepository:
        """获取数据仓库实例"""
        if self._repository is None:
            session = self._db_manager.get_session()
            self._repository = HistoricalDataRepository(session)
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
        """
        记录单个数据点

        Args:
            device_id: 设备 ID
            parameter_name: 参数名称
            value: 实际值
            unit: 单位
            raw_value: 原始值（寄存器值）
            quality: 数据质量（0=好，1=一般，2=差）

        Returns:
            bool: 记录成功返回 True
        """
        if not self._enabled:
            return False

        try:
            repo = self._get_repository()

            # 添加到缓冲区
            data_point = {
                "device_id": device_id,
                "parameter_name": parameter_name,
                "value": value,
                "unit": unit,
                "raw_value": raw_value,
                "quality": quality,
            }
            self._buffer.append(data_point)

            # 如果缓冲区满了或启用自动刷新，立即写入数据库
            if self._auto_flush and len(self._buffer) >= self._buffer_size:
                self.flush()

            return True

        except Exception as e:
            logger.error(f"记录历史数据失败：{str(e)}")
            return False

    def record_batch(self, data_points: List[Dict[str, Any]]) -> int:
        """
        批量记录数据

        Args:
            data_points: 数据点列表，每个数据点包含：
                - device_id: 设备 ID
                - parameter_name: 参数名称
                - value: 实际值
                - unit: 单位（可选）
                - raw_value: 原始值（可选）
                - quality: 数据质量（可选）

        Returns:
            int: 成功记录的数据点数量
        """
        if not self._enabled:
            return 0

        try:
            repo = self._get_repository()
            count = repo.batch_create(data_points)

            # 刷新缓冲区
            if self._auto_flush:
                self.flush()

            return count

        except Exception as e:
            logger.error(f"批量记录历史数据失败：{str(e)}")
            return 0

    def record_from_device(self, device_id: str, data: Dict[str, Any]) -> int:
        """
        从设备数据记录

        Args:
            device_id: 设备 ID
            data: 设备数据字典，格式为：
                {
                    "parameter1": {"value": 25.5, "unit": "°C", "raw_value": 255},
                    "parameter2": {"value": 100.0, "unit": "kPa"},
                    ...
                }

        Returns:
            int: 成功记录的数据点数量
        """
        if not self._enabled:
            return 0

        count = 0
        data_points = []

        for parameter_name, param_data in data.items():
            if isinstance(param_data, dict):
                data_point = {
                    "device_id": device_id,
                    "parameter_name": parameter_name,
                    "value": param_data.get("value", 0),
                    "unit": param_data.get("unit", ""),
                    "raw_value": param_data.get("raw_value"),
                    "quality": param_data.get("quality", 0),
                }
                data_points.append(data_point)
                count += 1

        if data_points:
            self.record_batch(data_points)

        return count

    def flush(self) -> bool:
        """
        刷新缓冲区到数据库

        Returns:
            bool: 刷新成功返回 True
        """
        if not self._buffer:
            return True

        try:
            repo = self._get_repository()
            repo.batch_create(self._buffer)
            self._buffer.clear()
            logger.debug(f"刷新 {len(self._buffer)} 条历史数据到数据库")
            return True

        except Exception as e:
            logger.error(f"刷新历史数据失败：{str(e)}")
            return False

        finally:
            # 清理会话
            if self._repository:
                self._repository._session.close()

    def get_latest_data(self, device_id: str) -> Dict[str, Any]:
        """
        获取设备最新数据

        Args:
            device_id: 设备 ID

        Returns:
            Dict: 最新数据字典
        """
        try:
            repo = self._get_repository()
            latest_data = repo.get_latest_by_device(device_id)

            result = {}
            for data in latest_data:
                result[data.parameter_name] = {
                    "value": data.value,
                    "unit": data.unit,
                    "timestamp": data.timestamp,
                    "quality": data.quality,
                }

            return result

        except Exception as e:
            logger.error(f"获取最新数据失败：{str(e)}")
            return {}

    def get_data_for_chart(
        self, device_id: str, parameter: str, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        获取图表数据

        Args:
            device_id: 设备 ID
            parameter: 参数名称
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            List: 数据点列表，适合图表显示
        """
        try:
            repo = self._get_repository()
            data_list = repo.get_by_time_range(device_id, start_time, end_time, parameter)

            return [{"timestamp": data.timestamp, "value": data.value, "unit": data.unit} for data in data_list]

        except Exception as e:
            logger.error(f"获取图表数据失败：{str(e)}")
            return []

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        清理过期数据

        Args:
            days: 保留天数，默认 30 天

        Returns:
            int: 清理的数据条数
        """
        try:
            repo = self._get_repository()
            count = repo.cleanup_old_data(days)
            logger.info(f"清理了 {count} 条过期历史数据（保留{days}天）")
            return count

        except Exception as e:
            logger.error(f"清理过期数据失败：{str(e)}")
            return 0

    def close(self):
        """关闭记录器，刷新缓冲区"""
        try:
            self.flush()
            if self._repository:
                self._repository._session.close()
                self._repository = None
            logger.info("历史数据记录器已关闭")
        except Exception as e:
            logger.error(f"关闭历史数据记录器失败：{str(e)}")
