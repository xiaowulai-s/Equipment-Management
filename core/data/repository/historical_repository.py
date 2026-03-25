# -*- coding: utf-8 -*-
"""
历史数据仓库
Historical Data Repository
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import Session

from ..models import HistoricalDataModel
from .base import BaseRepository


class HistoricalDataRepository(BaseRepository[HistoricalDataModel]):
    """历史数据仓库"""

    def __init__(self, session: Session):
        super().__init__(session, HistoricalDataModel)

    def get_by_device(self, device_id: str, limit: int = 1000) -> List[HistoricalDataModel]:
        """获取设备的历史数据"""
        return (
            self._session.query(HistoricalDataModel)
            .filter(HistoricalDataModel.device_id == device_id)
            .order_by(desc(HistoricalDataModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_device_and_parameter(
        self, device_id: str, parameter: str, limit: int = 1000
    ) -> List[HistoricalDataModel]:
        """获取设备特定参数的历史数据"""
        return (
            self._session.query(HistoricalDataModel)
            .filter(and_(HistoricalDataModel.device_id == device_id, HistoricalDataModel.parameter_name == parameter))
            .order_by(desc(HistoricalDataModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_time_range(
        self, device_id: str, start_time: datetime, end_time: datetime, parameter: Optional[str] = None
    ) -> List[HistoricalDataModel]:
        """获取时间范围内的历史数据"""
        query = self._session.query(HistoricalDataModel).filter(
            and_(
                HistoricalDataModel.device_id == device_id,
                HistoricalDataModel.timestamp >= start_time,
                HistoricalDataModel.timestamp <= end_time,
            )
        )

        if parameter:
            query = query.filter(HistoricalDataModel.parameter_name == parameter)

        return query.order_by(asc(HistoricalDataModel.timestamp)).all()

    def get_latest_by_device(self, device_id: str) -> List[HistoricalDataModel]:
        """获取设备最新的一条数据（每个参数）"""
        subquery = (
            self._session.query(
                HistoricalDataModel.parameter_name, func.max(HistoricalDataModel.timestamp).label("max_time")
            )
            .filter(HistoricalDataModel.device_id == device_id)
            .group_by(HistoricalDataModel.parameter_name)
            .subquery()
        )

        return (
            self._session.query(HistoricalDataModel)
            .join(
                subquery,
                and_(
                    HistoricalDataModel.parameter_name == subquery.c.parameter_name,
                    HistoricalDataModel.timestamp == subquery.c.max_time,
                ),
            )
            .filter(HistoricalDataModel.device_id == device_id)
            .all()
        )

    def create_data_point(
        self,
        device_id: str,
        parameter_name: str,
        value: float,
        unit: str = "",
        raw_value: Optional[int] = None,
        quality: int = 0,
    ) -> HistoricalDataModel:
        """创建单个数据点"""
        data = HistoricalDataModel(
            device_id=device_id,
            parameter_name=parameter_name,
            value=value,
            raw_value=raw_value,
            unit=unit,
            quality=quality,
        )
        return self.create(data)

    def batch_create(self, data_points: List[Dict[str, Any]]) -> int:
        """批量创建数据点"""
        count = 0
        for point in data_points:
            data = HistoricalDataModel(
                device_id=point["device_id"],
                parameter_name=point["parameter_name"],
                value=point["value"],
                raw_value=point.get("raw_value"),
                unit=point.get("unit", ""),
                quality=point.get("quality", 0),
            )
            self._session.add(data)
            count += 1

        self._session.flush()
        return count

    def get_statistics(
        self, device_id: str, parameter: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, float]:
        """获取统计数据"""
        result = (
            self._session.query(
                func.min(HistoricalDataModel.value).label("min"),
                func.max(HistoricalDataModel.value).label("max"),
                func.avg(HistoricalDataModel.value).label("avg"),
                func.count(HistoricalDataModel.id).label("count"),
            )
            .filter(
                and_(
                    HistoricalDataModel.device_id == device_id,
                    HistoricalDataModel.parameter_name == parameter,
                    HistoricalDataModel.timestamp >= start_time,
                    HistoricalDataModel.timestamp <= end_time,
                )
            )
            .first()
        )

        return {
            "min": result.min if result.min else 0.0,
            "max": result.max if result.max else 0.0,
            "avg": result.avg if result.avg else 0.0,
            "count": result.count if result.count else 0,
        }

    def cleanup_old_data(self, days: int = 30) -> int:
        """清理过期数据"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = (
            self._session.query(HistoricalDataModel)
            .filter(HistoricalDataModel.timestamp < cutoff_date)
            .delete(synchronize_session=False)
        )
        return result

    def get_data_for_export(
        self, device_ids: List[str], start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取导出数据"""
        query = self._session.query(HistoricalDataModel).filter(HistoricalDataModel.device_id.in_(device_ids))

        if start_time:
            query = query.filter(HistoricalDataModel.timestamp >= start_time)
        if end_time:
            query = query.filter(HistoricalDataModel.timestamp <= end_time)

        data = query.order_by(asc(HistoricalDataModel.timestamp)).all()
        return [d.to_dict() for d in data]
