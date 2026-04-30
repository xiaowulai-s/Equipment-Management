# -*- coding: utf-8 -*-
"""
MCGS业务服务 — 封装读取+解析+报警评估+DataBus发布

职责:
1. 连接设备 (委托 MCGSModbusReader)
2. 读取寄存器 (委托 MCGSModbusReader)
3. 解析数据 (委托 ModbusValueParser)
4. 评估报警 (委托 AnomalyService)
5. 存储历史 (委托 HistoryService)
6. 发布事件 (通过 DataBus)

设计原则:
- 纯Python逻辑，无Qt依赖（DataBus除外，但DataBus本身是QObject）
- 可独立测试
- 对外只暴露 read_and_process() 方法
- 所有结果通过 DataBus 发布，不直接回调UI
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.foundation.data_bus import DataBus
from core.foundation.config_store import ConfigStore
from core.communication.modbus_value_parser import ModbusValueParser
from core.protocols.byte_order_config import ByteOrderConfig

logger = logging.getLogger(__name__)


class MCGSReadResult:
    """MCGS单次读取+处理的结果"""

    __slots__ = (
        "device_id", "success", "timestamp", "duration_ms",
        "parsed_data", "raw_data", "alarms", "error_message",
    )

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.success = False
        self.timestamp = datetime.now()
        self.duration_ms = 0.0
        self.parsed_data: Dict[str, Any] = {}
        self.raw_data: Dict[str, Any] = {}
        self.alarms: Dict[str, Optional[str]] = {}
        self.error_message: str = ""

    def __repr__(self):
        status = "OK" if self.success else f"FAIL({self.error_message})"
        return (
            f"MCGSReadResult({self.device_id}, {status}, "
            f"{len(self.parsed_data)}pts, {self.duration_ms:.1f}ms)"
        )


class MCGSService:
    """
    MCGS业务服务 — 完整的读取-解析-报警-存储-发布流水线

    使用方式:
        service = MCGSService(reader, history_svc, anomaly_svc)
        result = service.read_and_process("mcgs_1")
        # 结果自动通过 DataBus 发布

    线程安全:
        - read_and_process() 本身不是线程安全的
        - 由 Controller 层负责线程调度（QThreadPool）
    """

    def __init__(
        self,
        reader=None,
        history_service=None,
        anomaly_service=None,
        config_store: Optional[ConfigStore] = None,
    ):
        self._reader = reader
        self._history_service = history_service
        self._anomaly_service = anomaly_service
        self._config_store = config_store or ConfigStore.instance()
        self._parsers: Dict[str, ModbusValueParser] = {}
        self._stats = {
            "total_reads": 0,
            "successful_reads": 0,
            "failed_reads": 0,
            "total_duration_ms": 0.0,
        }

    def set_reader(self, reader):
        self._reader = reader

    def set_history_service(self, service):
        self._history_service = service

    def set_anomaly_service(self, service):
        self._anomaly_service = service

    def get_parser(self, device_id: str) -> ModbusValueParser:
        """获取或创建设备的解析器（按字节序缓存）"""
        if device_id in self._parsers:
            return self._parsers[device_id]

        byte_order_str = self._get_byte_order(device_id)
        try:
            byte_order = ByteOrderConfig.from_string(byte_order_str)
        except ValueError:
            logger.warning("设备[%s]字节序'%s'无效, 使用ABCD", device_id, byte_order_str)
            byte_order = ByteOrderConfig.ABCD()

        parser = ModbusValueParser(byte_order)
        self._parsers[device_id] = parser
        return parser

    def read_and_process(self, device_id: str) -> MCGSReadResult:
        """
        完整的读取-解析-报警-存储-发布流水线

        流程:
        1. 通过 MCGSModbusReader 读取设备
        2. 通过 ModbusValueParser 统一解析
        3. 通过 AnomalyService 评估异常
        4. 通过 HistoryService 存储历史
        5. 通过 DataBus 发布结果

        Args:
            device_id: 设备ID

        Returns:
            MCGSReadResult 包含所有处理结果
        """
        start_time = time.time()
        result = MCGSReadResult(device_id)

        try:
            if self._reader is None:
                result.error_message = "Reader未初始化"
                logger.error("[%s] %s", device_id, result.error_message)
                self._publish_error(device_id, result.error_message)
                self._update_stats(False, start_time)
                return result

            read_result = self._reader.read_device(device_id)

            if not read_result.success:
                result.error_message = read_result.error_message or "读取失败"
                logger.warning("[%s] 读取失败: %s", device_id, result.error_message)
                self._publish_error(device_id, result.error_message)
                self._update_stats(False, start_time)
                return result

            result.success = True
            result.raw_data = {
                "registers": read_result.raw_registers,
                "register_count": read_result.register_count,
            }

            result.parsed_data = dict(read_result.parsed_data)

            if self._anomaly_service is not None:
                try:
                    result.alarms = self._anomaly_service.check_device_data(
                        device_id, read_result.parsed_data
                    )
                except Exception as e:
                    logger.warning("[%s] 异常检测失败: %s", device_id, e)

            if self._history_service is not None:
                try:
                    self._history_service.save_device_data(
                        device_id, read_result.parsed_data
                    )
                except Exception as e:
                    logger.warning("[%s] 历史存储失败: %s", device_id, e)

            self._publish_data(device_id, result)

            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            self._update_stats(True, start_time)

            logger.info(
                "[%s] 处理完成 [点位=%d, 耗时=%.1fms]",
                device_id, len(result.parsed_data), duration_ms,
            )

        except Exception as e:
            result.error_message = f"处理异常: {str(e)}"
            logger.error("[%s] %s", device_id, result.error_message, exc_info=True)
            self._publish_error(device_id, result.error_message)
            self._update_stats(False, start_time)

        return result

    def connect_device(self, device_id: str) -> bool:
        """连接设备"""
        if self._reader is None:
            logger.error("Reader未初始化")
            return False

        success = self._reader.connect_device(device_id)

        if success:
            DataBus.instance().publish_device_connected(device_id)
            logger.info("[%s] 设备已连接", device_id)
        else:
            DataBus.instance().publish_comm_error(device_id, "连接失败")
            logger.warning("[%s] 设备连接失败", device_id)

        return success

    def disconnect_device(self, device_id: str) -> bool:
        """断开设备连接"""
        if self._reader is None:
            return False

        try:
            if hasattr(self._reader, 'disconnect_device'):
                self._reader.disconnect_device(device_id)
            elif hasattr(self._reader, 'disconnect_all'):
                self._reader.disconnect_all()

            DataBus.instance().publish_device_disconnected(device_id)
            self._parsers.pop(device_id, None)
            logger.info("[%s] 设备已断开", device_id)
            return True
        except Exception as e:
            logger.error("[%s] 断开连接异常: %s", device_id, e)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        stats = dict(self._stats)
        if stats["total_reads"] > 0:
            stats["success_rate"] = (
                stats["successful_reads"] / stats["total_reads"] * 100
            )
        else:
            stats["success_rate"] = 0.0
        return stats

    def _get_byte_order(self, device_id: str) -> str:
        """获取设备的字节序配置"""
        try:
            config = self._config_store.get_device_config(device_id)
            if config and isinstance(config, dict):
                return config.get("byte_order", "CDAB")
        except Exception:
            pass

        if self._reader and hasattr(self._reader, '_devices'):
            device = self._reader._devices.get(device_id)
            if device and hasattr(device, 'byte_order'):
                return device.byte_order

        return "CDAB"

    def _publish_data(self, device_id: str, result: MCGSReadResult):
        """通过 DataBus 发布数据更新"""
        bus = DataBus.instance()

        bus.publish_device_data(device_id, result.parsed_data)

        bus.publish_device_raw(device_id, result.raw_data)

        for param_name, alarm_type in result.alarms.items():
            if alarm_type is not None:
                try:
                    value = 0.0
                    if param_name in result.parsed_data:
                        val_str = result.parsed_data[param_name]
                        if isinstance(val_str, str):
                            try:
                                value = float(val_str.split()[0])
                            except (ValueError, IndexError):
                                pass
                        elif isinstance(val_str, (int, float)):
                            value = float(val_str)

                    bus.publish_alarm(
                        device_id, param_name, alarm_type, value
                    )
                except Exception as e:
                    logger.warning("发布报警失败: %s", e)

    def _publish_error(self, device_id: str, error_msg: str):
        """通过 DataBus 发布通信错误"""
        DataBus.instance().publish_comm_error(device_id, error_msg)

    def _update_stats(self, success: bool, start_time: float):
        """更新统计信息"""
        self._stats["total_reads"] += 1
        if success:
            self._stats["successful_reads"] += 1
        else:
            self._stats["failed_reads"] += 1
        self._stats["total_duration_ms"] += (time.time() - start_time) * 1000
