# -*- coding: utf-8 -*-
"""
异常检测服务 — 封装 AnomalyDetector，提供业务级接口

职责:
1. 检测单个参数值是否异常
2. 批量检测设备所有参数
3. 生成设备健康报告
4. 通过 DataBus 发布异常事件

设计原则:
- 对外提供业务级接口，隐藏算法细节
- 接受旧格式(字符串)和新格式(结构化)数据
- 报警结果通过 DataBus 发布
- 延迟初始化 AnomalyDetector
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.foundation.data_bus import DataBus

logger = logging.getLogger(__name__)


class AnomalyService:
    """
    异常检测服务

    使用方式:
        svc = AnomalyService(history_service)
        alarms = svc.check_device_data("mcgs_1", {"Hum_in": "23.6 %RH", ...})
        # alarms = {"Hum_in": None, "AT_in": "high", ...}
    """

    def __init__(self, history_service=None, config=None):
        self._history_service = history_service
        self._config = config
        self._detector = None
        self._initialized = False

    def initialize(self) -> bool:
        """延迟初始化检测器"""
        if self._initialized:
            return True

        try:
            from core.utils.anomaly_detector import AnomalyDetector, DetectionConfig

            det_config = self._config
            if det_config is None and self._history_service is not None:
                det_config = DetectionConfig()

            storage = None
            if self._history_service is not None:
                storage = self._history_service.storage

            self._detector = AnomalyDetector(
                history_storage=storage,
                config=det_config,
            )
            self._initialized = True
            logger.info("AnomalyService 初始化完成")
            return True
        except Exception as e:
            logger.error("AnomalyService 初始化失败: %s", e)
            return False

    @property
    def detector(self):
        if not self._initialized:
            self.initialize()
        return self._detector

    def check_device_data(
        self,
        device_id: str,
        parsed_data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Optional[str]]:
        """
        批量检测设备数据异常

        支持两种数据格式:
        1. 旧格式: {param_name: "23.6 %RH"} (字符串)
        2. 新格式: {param_name: {"raw": 23.6, "value": "23.6 %RH", ...}} (结构化)

        Args:
            device_id: 设备ID
            parsed_data: 解析后的数据
            timestamp: 时间戳

        Returns:
            {param_name: alarm_type_or_None}
            alarm_type: "high" / "low" / "spike" / "drop" / "constant" / "noise" / "out_of_range"
            None 表示正常
        """
        if not self._initialized:
            if not self.initialize():
                return {}

        if timestamp is None:
            timestamp = datetime.now()

        alarms: Dict[str, Optional[str]] = {}

        for name, value in parsed_data.items():
            try:
                numeric_value = self._extract_numeric(value)
                if numeric_value is None:
                    alarms[name] = None
                    continue

                result = self._detector.check_value(
                    device_id, name, numeric_value, timestamp
                )

                if result.is_anomaly and result.anomaly_type is not None:
                    alarm_type = result.anomaly_type.value
                    alarms[name] = alarm_type

                    try:
                        DataBus.instance().publish_alarm(
                            device_id, name, alarm_type, numeric_value
                        )
                    except Exception:
                        pass
                else:
                    alarms[name] = None

            except Exception as e:
                logger.debug("检测异常[%s.%s]失败: %s", device_id, name, e)
                alarms[name] = None

        return alarms

    def check_single_value(
        self,
        device_id: str,
        param_name: str,
        value: float,
        timestamp: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        检测单个值

        Args:
            device_id: 设备ID
            param_name: 参数名
            value: 数值
            timestamp: 时间戳

        Returns:
            alarm_type 或 None
        """
        if not self._initialized:
            if not self.initialize():
                return None

        try:
            result = self._detector.check_value(
                device_id, param_name, value, timestamp
            )

            if result.is_anomaly and result.anomaly_type is not None:
                return result.anomaly_type.value
            return None

        except Exception as e:
            logger.debug("检测异常失败: %s", e)
            return None

    def get_health_report(self, device_id: str) -> Dict[str, Any]:
        """
        获取设备健康报告

        Args:
            device_id: 设备ID

        Returns:
            健康报告字典
        """
        if not self._initialized:
            if not self.initialize():
                return {
                    "device_id": device_id,
                    "overall_status": "UNKNOWN",
                    "anomaly_count": 0,
                    "parameters": {},
                }

        try:
            return self._detector.get_health_report(device_id)
        except Exception as e:
            logger.error("获取健康报告失败: %s", e)
            return {
                "device_id": device_id,
                "overall_status": "ERROR",
                "anomaly_count": 0,
                "error": str(e),
            }

    def set_physical_ranges(self, ranges: Dict[str, tuple]):
        """
        设置物理范围限制

        Args:
            ranges: {param_name: (min_value, max_value)}
        """
        if not self._initialized:
            self.initialize()

        if self._detector is not None:
            self._detector._config.physical_ranges.update(ranges)
            logger.info("物理范围已更新: %d个参数", len(ranges))

    def _extract_numeric(self, value: Any) -> Optional[float]:
        """从各种格式中提取数值"""
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, dict):
            raw = value.get("raw")
            if raw is not None and not isinstance(raw, bool):
                try:
                    return float(raw)
                except (ValueError, TypeError):
                    return None
            scaled = value.get("scaled")
            if scaled is not None and not isinstance(scaled, bool):
                try:
                    return float(scaled)
                except (ValueError, TypeError):
                    return None
            return None

        if isinstance(value, str):
            try:
                return float(value.split()[0])
            except (ValueError, IndexError):
                return None

        return None
