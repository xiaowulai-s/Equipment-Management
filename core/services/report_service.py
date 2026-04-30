# -*- coding: utf-8 -*-
"""
报表生成服务
Report Generation Service - 日报/月报/统计报表
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.utils.logger import get_logger

logger = get_logger(__name__)


class ReportService:
    """报表生成服务 - 支持日报、月报、统计报表"""

    def __init__(self, db_manager=None) -> None:
        self._db_manager = db_manager

    def generate_daily_report(self, date: Optional[str] = None, output_dir: str = "reports") -> Optional[str]:
        """生成日报"""
        if date is None:
            target_date = datetime.now(timezone.utc)
        else:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        os.makedirs(output_dir, exist_ok=True)
        filename = f"daily_report_{start_time.strftime('%Y%m%d')}.csv"
        filepath = os.path.join(output_dir, filename)

        try:
            data = self._collect_report_data(start_time, end_time)
            self._write_csv(filepath, data)

            logger.info("日报生成成功", filepath=filepath)
            return filepath
        except Exception as e:
            logger.error("日报生成失败", error=str(e))
            return None

    def generate_monthly_report(self, year: int, month: int, output_dir: str = "reports") -> Optional[str]:
        """生成月报"""
        start_time = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_time = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_time = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        os.makedirs(output_dir, exist_ok=True)
        filename = f"monthly_report_{year}{month:02d}.csv"
        filepath = os.path.join(output_dir, filename)

        try:
            data = self._collect_report_data(start_time, end_time)
            self._write_csv(filepath, data)

            logger.info("月报生成成功", filepath=filepath)
            return filepath
        except Exception as e:
            logger.error("月报生成失败", error=str(e))
            return None

    def generate_statistics_report(self, days: int = 30, output_dir: str = "reports") -> Optional[str]:
        """生成统计报表"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        os.makedirs(output_dir, exist_ok=True)
        filename = f"statistics_report_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.csv"
        filepath = os.path.join(output_dir, filename)

        try:
            data = self._collect_report_data(start_time, end_time)
            self._write_csv(filepath, data)

            logger.info("统计报表生成成功", filepath=filepath)
            return filepath
        except Exception as e:
            logger.error("统计报表生成失败", error=str(e))
            return None

    def _collect_report_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """收集报表数据"""
        rows = []

        if self._db_manager is None:
            return rows

        try:
            from core.data.models import AlarmModel, HistoricalDataModel
            from core.data.repository.alarm_repository import AlarmRepository
            from core.data.repository.historical_repository import HistoricalDataRepository
            from sqlalchemy import and_, func

            with self._db_manager.session() as session:
                alarm_stats = (
                    session.query(
                        AlarmModel.level,
                        func.count(AlarmModel.id),
                    )
                    .filter(and_(AlarmModel.timestamp >= start_time, AlarmModel.timestamp <= end_time))
                    .group_by(AlarmModel.level)
                    .all()
                )

                for level, count in alarm_stats:
                    level_names = {0: "信息", 1: "警告", 2: "错误", 3: "严重"}
                    rows.append(
                        {
                            "category": "报警统计",
                            "item": level_names.get(level, f"级别{level}"),
                            "count": count,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                        }
                    )

                device_stats = (
                    session.query(
                        HistoricalDataModel.device_id,
                        func.count(HistoricalDataModel.id),
                        func.avg(HistoricalDataModel.value),
                        func.min(HistoricalDataModel.value),
                        func.max(HistoricalDataModel.value),
                    )
                    .filter(
                        and_(HistoricalDataModel.timestamp >= start_time, HistoricalDataModel.timestamp <= end_time)
                    )
                    .group_by(HistoricalDataModel.device_id)
                    .all()
                )

                for device_id, count, avg_val, min_val, max_val in device_stats:
                    rows.append(
                        {
                            "category": "设备数据",
                            "item": device_id,
                            "count": count,
                            "avg_value": round(avg_val or 0, 2),
                            "min_value": round(min_val or 0, 2),
                            "max_value": round(max_val or 0, 2),
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                        }
                    )

        except Exception as e:
            logger.error("收集报表数据失败", error=str(e))

        return rows

    def _write_csv(self, filepath: str, data: List[Dict[str, Any]]) -> None:
        """写入CSV文件"""
        if not data:
            return

        fieldnames = list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
