# -*- coding: utf-8 -*-
"""
历史数据服务 — 封装 HistoryStorage，提供业务级接口

职责:
1. 保存设备采集数据（自动提取原始值和格式化值）
2. 查询历史趋势数据
3. 获取统计信息
4. 数据清理和导出
5. 通过 DataBus 发布存储事件

设计原则:
- 对外提供业务级接口，隐藏 SQLite 细节
- 接受结构化数据（parse_batch 的输出格式）
- 线程安全（依赖 HistoryStorage 的 check_same_thread=False）
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.foundation.data_bus import DataBus

logger = logging.getLogger(__name__)


class HistoryService:
    """
    历史数据服务

    使用方式:
        svc = HistoryService(db_path="data/equipment.db")
        svc.save_device_data("mcgs_1", {"Hum_in": "23.6 %RH", ...})
        data = svc.query_trend("mcgs_1", "Hum_in", hours=1)
    """

    def __init__(self, db_path: str = "data/equipment_management.db", max_age_days: int = 30):
        self._db_path = db_path
        self._max_age_days = max_age_days
        self._storage = None
        self._initialized = False

    def initialize(self) -> bool:
        """初始化存储（延迟初始化，避免导入时创建DB）"""
        if self._initialized:
            return True

        try:
            from core.utils.history_storage import HistoryStorage

            self._storage = HistoryStorage(self._db_path, self._max_age_days)
            self._initialized = True
            logger.info("HistoryService 初始化完成 [db=%s]", self._db_path)
            return True
        except Exception as e:
            logger.error("HistoryService 初始化失败: %s", e)
            return False

    @property
    def storage(self):
        if not self._initialized:
            self.initialize()
        return self._storage

    def save_device_data(
        self,
        device_id: str,
        parsed_data: Dict[str, Any],
        raw_values: Optional[Dict[str, float]] = None,
        timestamp: Optional[datetime] = None,
    ) -> int:
        """
        保存设备采集数据

        支持两种数据格式:
        1. 旧格式: {param_name: "23.6 %RH"} (字符串)
        2. 新格式: {param_name: {"raw": 23.6, "value": "23.6 %RH", ...}} (结构化)

        Args:
            device_id: 设备ID
            parsed_data: 解析后的数据
            raw_values: 原始数值（可选，新格式时自动提取）
            timestamp: 时间戳

        Returns:
            保存的记录数
        """
        if not self._initialized:
            if not self.initialize():
                return 0

        if timestamp is None:
            timestamp = datetime.now()

        formatted_data = {}
        extracted_raw = {}

        for name, value in parsed_data.items():
            if isinstance(value, dict):
                formatted_data[name] = value.get("value", str(value.get("raw", "")))
                if value.get("raw") is not None and not isinstance(value["raw"], bool):
                    extracted_raw[name] = float(value["raw"])
            else:
                formatted_data[name] = str(value)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    extracted_raw[name] = float(value)

        if raw_values is not None:
            extracted_raw.update(raw_values)

        try:
            count = self._storage.save_read_result(
                device_id=device_id,
                parsed_data=formatted_data,
                raw_data=extracted_raw if extracted_raw else None,
                timestamp=timestamp,
            )
            return count
        except Exception as e:
            logger.error("保存历史数据失败 [%s]: %s", device_id, e)
            return 0

    def query_trend(
        self,
        device_id: str,
        param_name: str,
        hours: float = 1.0,
        limit: int = 10000,
    ) -> List[Tuple[datetime, float]]:
        """
        查询趋势数据（用于图表显示）

        Args:
            device_id: 设备ID
            param_name: 参数名
            hours: 时间范围（小时）
            limit: 最大返回条数

        Returns:
            [(timestamp, value), ...] 时间序列
        """
        if not self._initialized:
            if not self.initialize():
                return []

        try:
            return self._storage.query_range(device_id, param_name, hours=hours, limit=limit)
        except Exception as e:
            logger.error("查询趋势数据失败: %s", e)
            return []

    def query_latest(
        self,
        device_id: str,
        param_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        查询最新数据

        Args:
            device_id: 设备ID
            param_name: 参数名（None=所有参数）

        Returns:
            最新数据字典
        """
        if not self._initialized:
            if not self.initialize():
                return {}

        try:
            return self._storage.query_latest(device_id, param_name)
        except Exception as e:
            logger.error("查询最新数据失败: %s", e)
            return {}

    def get_statistics(
        self,
        device_id: str,
        param_name: str,
        hours: float = 24.0,
    ) -> Dict[str, float]:
        """
        获取统计信息

        Args:
            device_id: 设备ID
            param_name: 参数名
            hours: 统计时间范围

        Returns:
            统计结果 {avg, min, max, std_dev, sample_count, range}
        """
        if not self._initialized:
            if not self.initialize():
                return {}

        try:
            return self._storage.get_statistics(device_id, param_name, hours)
        except Exception as e:
            logger.error("获取统计信息失败: %s", e)
            return {}

    def cleanup(self, max_age_days: Optional[int] = None) -> int:
        """
        清理过期数据

        Args:
            max_age_days: 保留天数

        Returns:
            删除的记录数
        """
        if not self._initialized:
            return 0

        try:
            return self._storage.cleanup_old_data(max_age_days)
        except Exception as e:
            logger.error("清理数据失败: %s", e)
            return 0

    def export_csv(
        self,
        output_path: str,
        device_id: str,
        param_names: Optional[List[str]] = None,
        hours: float = 24.0,
    ) -> bool:
        """
        导出为CSV

        Args:
            output_path: 输出路径
            device_id: 设备ID
            param_names: 参数名列表
            hours: 时间范围

        Returns:
            是否成功
        """
        if not self._initialized:
            if not self.initialize():
                return False

        try:
            return self._storage.export_to_csv(output_path, device_id, param_names, hours)
        except Exception as e:
            logger.error("导出CSV失败: %s", e)
            return False

    def close(self):
        """关闭存储连接"""
        if self._storage:
            self._storage.close()
            self._storage = None
            self._initialized = False
            logger.info("HistoryService 已关闭")
