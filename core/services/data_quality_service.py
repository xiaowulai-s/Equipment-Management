# -*- coding: utf-8 -*-
"""
数据质量标记服务
Data Quality Service - 为采集数据标记质量等级
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Dict, Optional

from core.utils.logger import get_logger

logger = get_logger(__name__)


class QualityCode(IntEnum):
    """数据质量代码 (OPC UA 兼容)"""

    GOOD = 0
    UNCERTAIN = 1
    BAD_COMMUNICATION_FAILURE = 2
    BAD_OUT_OF_RANGE = 3
    BAD_SENSOR_FAILURE = 4
    BAD_LAST_KNOWN_VALUE = 5
    BAD_NOT_CONNECTED = 6


QUALITY_DESCRIPTIONS = {
    QualityCode.GOOD: "良好",
    QualityCode.UNCERTAIN: "不确定",
    QualityCode.BAD_COMMUNICATION_FAILURE: "通信失败",
    QualityCode.BAD_OUT_OF_RANGE: "超量程",
    QualityCode.BAD_SENSOR_FAILURE: "传感器故障",
    QualityCode.BAD_LAST_KNOWN_VALUE: "最后已知值",
    QualityCode.BAD_NOT_CONNECTED: "未连接",
}


class DataQualityService:
    """数据质量标记服务 - 评估和标记采集数据的质量"""

    def __init__(self) -> None:
        self._range_limits: Dict[str, Dict[str, tuple]] = {}
        self._stale_threshold_ms: int = 5000

    def set_range_limits(self, device_id: str, parameter: str, low: float, high: float) -> None:
        """设置参数的合理范围"""
        if device_id not in self._range_limits:
            self._range_limits[device_id] = {}
        self._range_limits[device_id][parameter] = (low, high)

    def evaluate_quality(
        self,
        device_id: str,
        parameter: str,
        value: float,
        is_connected: bool = True,
        response_time_ms: float = 0,
        last_update_age_ms: float = 0,
    ) -> QualityCode:
        """评估数据质量"""
        if not is_connected:
            return QualityCode.BAD_NOT_CONNECTED

        if response_time_ms > 2000:
            return QualityCode.BAD_COMMUNICATION_FAILURE

        if last_update_age_ms > self._stale_threshold_ms:
            return QualityCode.BAD_LAST_KNOWN_VALUE

        limits = self._range_limits.get(device_id, {}).get(parameter)
        if limits:
            low, high = limits
            if value < low or value > high:
                return QualityCode.BAD_OUT_OF_RANGE

        if response_time_ms > 1000 or last_update_age_ms > 2000:
            return QualityCode.UNCERTAIN

        return QualityCode.GOOD

    def mark_data_quality(self, device_id: str, data: Dict[str, Any], device_status: int = 1) -> Dict[str, Any]:
        """为设备数据批量标记质量"""
        is_connected = device_status == 1
        marked_data = {}

        for param_name, param_info in data.items():
            if not isinstance(param_info, dict):
                continue

            value = param_info.get("value", 0)
            quality = self.evaluate_quality(
                device_id=device_id,
                parameter=param_name,
                value=float(value) if value is not None else 0,
                is_connected=is_connected,
            )

            marked_info = dict(param_info)
            marked_info["quality"] = quality.value
            marked_info["quality_description"] = QUALITY_DESCRIPTIONS.get(quality, "未知")
            marked_data[param_name] = marked_info

        return marked_data

    @staticmethod
    def quality_to_string(quality_code: int) -> str:
        return QUALITY_DESCRIPTIONS.get(QualityCode(quality_code), "未知")
