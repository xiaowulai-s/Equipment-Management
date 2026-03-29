"""
历史数据仓库

提供历史数据点的写入、查询、统计和清理。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func
from sqlalchemy.orm import Session

from ..models import HistoricalDataModel, utc_now
from .base import BaseRepository


class HistoricalDataRepository(BaseRepository[HistoricalDataModel]):
    """历史数据仓库"""

    def __init__(self, session: Session) -> None:
        super().__init__(session, HistoricalDataModel)

    # ═══════════════════════════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════════════════════════

    def get_by_device(self, device_id: str, limit: int = 1000) -> List[HistoricalDataModel]:
        """查询设备最近数据"""
        return (
            self._session.query(HistoricalDataModel)
            .filter(HistoricalDataModel.device_id == device_id)
            .order_by(desc(HistoricalDataModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_register(self, device_id: str, register_name: str, limit: int = 1000) -> List[HistoricalDataModel]:
        """查询设备指定寄存器最近数据"""
        return (
            self._session.query(HistoricalDataModel)
            .filter(
                and_(
                    HistoricalDataModel.device_id == device_id,
                    HistoricalDataModel.register_name == register_name,
                )
            )
            .order_by(desc(HistoricalDataModel.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_time_range(
        self,
        device_id: str,
        start: datetime,
        end: datetime,
        register_name: Optional[str] = None,
    ) -> List[HistoricalDataModel]:
        """查询时间范围内的数据"""
        query = self._session.query(HistoricalDataModel).filter(
            and_(
                HistoricalDataModel.device_id == device_id,
                HistoricalDataModel.timestamp >= start,
                HistoricalDataModel.timestamp <= end,
            )
        )
        if register_name:
            query = query.filter(HistoricalDataModel.register_name == register_name)
        return query.order_by(asc(HistoricalDataModel.timestamp)).all()

    def get_latest_by_device(self, device_id: str) -> List[HistoricalDataModel]:
        """查询每个寄存器的最新值"""
        subquery = (
            self._session.query(
                HistoricalDataModel.register_name,
                func.max(HistoricalDataModel.timestamp).label("max_time"),
            )
            .filter(HistoricalDataModel.device_id == device_id)
            .group_by(HistoricalDataModel.register_name)
            .subquery()
        )
        return (
            self._session.query(HistoricalDataModel)
            .join(
                subquery,
                and_(
                    HistoricalDataModel.register_name == subquery.c.register_name,
                    HistoricalDataModel.timestamp == subquery.c.max_time,
                ),
            )
            .filter(HistoricalDataModel.device_id == device_id)
            .all()
        )

    # ═══════════════════════════════════════════════════════════
    # 写入
    # ═══════════════════════════════════════════════════════════

    def record(
        self,
        device_id: str,
        register_name: str,
        value: float,
        unit: str = "",
        raw_value: Optional[int] = None,
        quality: int = 0,
    ) -> HistoricalDataModel:
        """写入单条数据"""
        point = HistoricalDataModel(
            device_id=device_id,
            register_name=register_name,
            value=value,
            raw_value=raw_value,
            unit=unit,
            quality=quality,
        )
        return self.create(point)

    def batch_record(self, points: List[Dict[str, Any]]) -> int:
        """批量写入数据"""
        count = 0
        for p in points:
            self._session.add(
                HistoricalDataModel(
                    device_id=p["device_id"],
                    register_name=p["register_name"],
                    value=p["value"],
                    raw_value=p.get("raw_value"),
                    unit=p.get("unit", ""),
                    quality=p.get("quality", 0),
                )
            )
            count += 1
        self._session.flush()
        return count

    # ═══════════════════════════════════════════════════════════
    # 统计
    # ═══════════════════════════════════════════════════════════

    def get_statistics(
        self,
        device_id: str,
        register_name: str,
        start: datetime,
        end: datetime,
    ) -> Dict[str, float]:
        """获取统计信息 (min/max/avg/count)"""
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
                    HistoricalDataModel.register_name == register_name,
                    HistoricalDataModel.timestamp >= start,
                    HistoricalDataModel.timestamp <= end,
                )
            )
            .first()
        )
        if result is None:
            return {"min": 0.0, "max": 0.0, "avg": 0.0, "count": 0}
        return {
            "min": result.min if result.min is not None else 0.0,
            "max": result.max if result.max is not None else 0.0,
            "avg": result.avg if result.avg is not None else 0.0,
            "count": result.count if result.count is not None else 0,
        }

    # ═══════════════════════════════════════════════════════════
    # 清理
    # ═══════════════════════════════════════════════════════════

    def cleanup(self, days: int = 30) -> int:
        """清理过期数据"""
        cutoff = utc_now() - timedelta(days=days)
        return (
            self._session.query(HistoricalDataModel)
            .filter(HistoricalDataModel.timestamp < cutoff)
            .delete(synchronize_session=False)
        )

    def get_for_export(
        self,
        device_ids: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """导出数据"""
        query = self._session.query(HistoricalDataModel).filter(HistoricalDataModel.device_id.in_(device_ids))
        if start:
            query = query.filter(HistoricalDataModel.timestamp >= start)
        if end:
            query = query.filter(HistoricalDataModel.timestamp <= end)
        return [row.to_dict() for row in query.order_by(asc(HistoricalDataModel.timestamp)).all()]
