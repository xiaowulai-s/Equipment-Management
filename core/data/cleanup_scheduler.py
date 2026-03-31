# -*- coding: utf-8 -*-
"""
数据清理调度器

定期清理旧数据，防止数据库无限增长:
    - 设备状态历史 (默认保留30天)
    - 系统日志 (默认保留90天)
    - 报警记录 (默认保留180天)
    - 历史数据点 (默认保留365天)

使用方式:
    scheduler = CleanupScheduler(db_manager)
    scheduler.start()  # 启动定时清理
    ...
    scheduler.stop()   # 停止定时清理
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class CleanupScheduler(QObject):
    """数据清理调度器

    定期执行数据库清理任务，防止数据无限增长。
    默认每天执行一次清理。

    Attributes:
        cleanup_interval_hours: 清理执行间隔（小时）
        retention_days: 各类数据的保留天数配置
    """

    DEFAULT_RETENTION_DAYS = {
        "device_status_history": 30,
        "system_logs": 90,
        "alarm_records": 180,
        "historical_data": 365,
    }

    def __init__(
        self,
        db_manager,
        cleanup_interval_hours: int = 24,
        retention_days: Optional[Dict[str, int]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db_manager = db_manager
        self._cleanup_interval_hours = cleanup_interval_hours
        self._retention_days = retention_days or dict(self.DEFAULT_RETENTION_DAYS)
        self._timer: Optional[QTimer] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    def start(self) -> None:
        """启动定时清理任务"""
        if self._is_running:
            logger.warning("清理调度器已在运行")
            return

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._run_cleanup)
        # 转换为毫秒
        interval_ms = self._cleanup_interval_hours * 60 * 60 * 1000
        self._timer.start(interval_ms)
        self._is_running = True

        logger.info(
            "数据清理调度器已启动，间隔=%d小时，数据保留策略=%s",
            self._cleanup_interval_hours,
            self._retention_days,
        )

        # 启动时立即执行一次清理
        self._run_cleanup()

    def stop(self) -> None:
        """停止定时清理任务"""
        if not self._is_running:
            return

        if self._timer:
            self._timer.stop()
            self._timer = None

        self._is_running = False
        logger.info("数据清理调度器已停止")

    def _run_cleanup(self) -> None:
        """执行清理任务"""
        logger.info("开始执行数据清理任务...")
        total_deleted = 0

        try:
            # 清理设备状态历史
            deleted = self._cleanup_device_status_history()
            total_deleted += deleted

            # 清理系统日志
            deleted = self._cleanup_system_logs()
            total_deleted += deleted

            # 清理报警记录
            deleted = self._cleanup_alarm_records()
            total_deleted += deleted

            # 清理历史数据点
            deleted = self._cleanup_historical_data()
            total_deleted += deleted

            logger.info("数据清理完成，共清理 %d 条记录", total_deleted)

        except Exception:
            logger.exception("执行数据清理任务时出错")

    def _cleanup_device_status_history(self) -> int:
        """清理设备状态历史"""
        try:
            from sqlalchemy import delete

            from core.data.models import DeviceStatusHistoryModel

            days = self._retention_days.get("device_status_history", 30)
            cutoff_time = datetime.utcnow() - timedelta(days=days)

            with self._db_manager.session() as session:
                result = session.execute(
                    delete(DeviceStatusHistoryModel).where(DeviceStatusHistoryModel.timestamp < cutoff_time)
                )
                deleted = result.rowcount
                if deleted > 0:
                    logger.info("清理设备状态历史: %d 条记录 (>%d天)", deleted, days)
                return deleted
        except Exception:
            logger.exception("清理设备状态历史失败")
            return 0

    def _cleanup_system_logs(self) -> int:
        """清理系统日志"""
        try:
            from sqlalchemy import delete

            from core.data.models import SystemLogModel

            days = self._retention_days.get("system_logs", 90)
            cutoff_time = datetime.utcnow() - timedelta(days=days)

            with self._db_manager.session() as session:
                result = session.execute(delete(SystemLogModel).where(SystemLogModel.timestamp < cutoff_time))
                deleted = result.rowcount
                if deleted > 0:
                    logger.info("清理系统日志: %d 条记录 (>%d天)", deleted, days)
                return deleted
        except Exception:
            logger.exception("清理系统日志失败")
            return 0

    def _cleanup_alarm_records(self) -> int:
        """清理报警记录"""
        try:
            from sqlalchemy import delete

            from core.data.models import AlarmModel

            days = self._retention_days.get("alarm_records", 180)
            cutoff_time = datetime.utcnow() - timedelta(days=days)

            with self._db_manager.session() as session:
                result = session.execute(delete(AlarmModel).where(AlarmModel.timestamp < cutoff_time))
                deleted = result.rowcount
                if deleted > 0:
                    logger.info("清理报警记录: %d 条记录 (>%d天)", deleted, days)
                return deleted
        except Exception:
            logger.exception("清理报警记录失败")
            return 0

    def _cleanup_historical_data(self) -> int:
        """清理历史数据点"""
        try:
            from sqlalchemy import delete

            from core.data.models import HistoricalDataModel

            days = self._retention_days.get("historical_data", 365)
            cutoff_time = datetime.utcnow() - timedelta(days=days)

            with self._db_manager.session() as session:
                result = session.execute(delete(HistoricalDataModel).where(HistoricalDataModel.timestamp < cutoff_time))
                deleted = result.rowcount
                if deleted > 0:
                    logger.info("清理历史数据点: %d 条记录 (>%d天)", deleted, days)
                return deleted
        except Exception:
            logger.exception("清理历史数据点失败")
            return 0

    def cleanup_now(self) -> Dict[str, int]:
        """立即执行清理，返回各类数据删除数量

        Returns:
            清理结果字典，如:
            {
                "device_status_history": 100,
                "system_logs": 50,
                "alarm_records": 20,
                "historical_data": 1000,
            }
        """
        results = {}

        results["device_status_history"] = self._cleanup_device_status_history()
        results["system_logs"] = self._cleanup_system_logs()
        results["alarm_records"] = self._cleanup_alarm_records()
        results["historical_data"] = self._cleanup_historical_data()

        total = sum(results.values())
        logger.info("手动清理完成，共清理 %d 条记录", total)

        return results

    def update_retention_policy(self, data_type: str, days: int) -> None:
        """更新数据保留策略

        Args:
            data_type: 数据类型，如 'device_status_history', 'system_logs' 等
            days: 保留天数
        """
        if data_type in self._retention_days:
            old_days = self._retention_days[data_type]
            self._retention_days[data_type] = days
            logger.info(
                "更新数据保留策略: %s %d天 -> %d天",
                data_type,
                old_days,
                days,
            )
        else:
            logger.warning("未知的数据类型: %s", data_type)

    def get_retention_policy(self) -> Dict[str, int]:
        """获取当前数据保留策略"""
        return dict(self._retention_days)
