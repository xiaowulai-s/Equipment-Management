# -*- coding: utf-8 -*-
"""
MCGSController — MCGS异步控制器

职责:
1. 持有 QThreadPool，将 MCGSService 操作放入工作线程
2. 管理 QTimer 轮询调度
3. 通过 DataBus 发射数据更新信号
4. 通过自身 Signal 中转结果给 MainWindow
5. 管理连接/断开/轮询生命周期

设计原则:
- Controller 层只负责异步调度和 Signal 中转
- 不包含业务逻辑（业务逻辑在 Service 层）
- 不直接操作 UI 控件
- 线程安全：所有耗时操作通过 QRunnable 在工作线程执行
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QTimer, Qt

from core.foundation.data_bus import DataBus
from core.services.mcgs_service import MCGSService, MCGSReadResult

logger = logging.getLogger(__name__)


class _ConnectTask(QRunnable):
    """异步连接任务"""

    class Signals(QObject):
        finished = Signal(str, bool, str)

    def __init__(self, service: MCGSService, device_id: str):
        super().__init__()
        self.service = service
        self.device_id = device_id
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self):
        try:
            success = self.service.connect_device(self.device_id)
            msg = "连接成功" if success else "连接失败"
            self.signals.finished.emit(self.device_id, success, msg)
        except Exception as e:
            self.signals.finished.emit(self.device_id, False, str(e))


class _ReadAndProcessTask(QRunnable):
    """异步读取+处理任务"""

    class Signals(QObject):
        finished = Signal(object)

    def __init__(self, service: MCGSService, device_id: str):
        super().__init__()
        self.service = service
        self.device_id = device_id
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self):
        try:
            result = self.service.read_and_process(self.device_id)
            self.signals.finished.emit(result)
        except Exception as e:
            logger.error("[_ReadAndProcessTask] 异常: %s", e)
            result = MCGSReadResult(self.device_id)
            result.error_message = str(e)
            self.signals.finished.emit(result)


class _BatchReadTask(QRunnable):
    """异步批量读取任务（轮询时使用）"""

    class Signals(QObject):
        finished = Signal(list)

    def __init__(self, service: MCGSService, device_ids: List[str]):
        super().__init__()
        self.service = service
        self.device_ids = device_ids
        self.signals = self.Signals()
        self.setAutoDelete(True)

    def run(self):
        results = []
        for device_id in self.device_ids:
            try:
                result = self.service.read_and_process(device_id)
                results.append(result)
            except Exception as e:
                logger.error("[_BatchReadTask] 设备[%s]异常: %s", device_id, e)
                err_result = MCGSReadResult(device_id)
                err_result.error_message = str(e)
                results.append(err_result)
        self.signals.finished.emit(results)


class MCGSController(QObject):
    """
    MCGS异步控制器

    使用方式:
        controller = MCGSController(parent=self)
        controller.connect_device("mcgs_1")
        controller.start_polling(["mcgs_1"], interval_ms=1000)

        # 连接信号
        controller.device_connected.connect(self._on_device_connected)
        controller.device_data_updated.connect(self._on_data_updated)
        controller.device_error.connect(self._on_error)
    """

    device_connected = Signal(str, bool, str)
    device_data_updated = Signal(str, dict)
    device_error = Signal(str, str)
    poll_cycle_completed = Signal(int, int)
    polling_started = Signal()
    polling_stopped = Signal()

    def __init__(
        self,
        mcgs_service: Optional[MCGSService] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self._service = mcgs_service or MCGSService()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll_timeout)

        self._polling_device_ids: List[str] = []
        self._is_polling = False
        self._poll_interval_ms = 1000
        self._poll_cycle_count = 0

        self._stats = {
            "total_reads": 0,
            "successful_reads": 0,
            "failed_reads": 0,
            "anomalies_detected": 0,
            "last_read_time": None,
        }

        self._connect_data_bus()

    def _connect_data_bus(self):
        bus = DataBus.instance()
        bus.subscribe('device_data_updated', self._on_bus_data_updated)
        bus.subscribe('comm_error', self._on_bus_comm_error)
        bus.subscribe('device_connected', self._on_bus_device_connected)
        bus.subscribe('device_disconnected', self._on_bus_device_disconnected)

    @property
    def service(self) -> MCGSService:
        return self._service

    @property
    def is_polling(self) -> bool:
        return self._is_polling

    @property
    def stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def query_history_trend(self, device_id: str, param_name: str, hours: int = 24):
        hs = self._service._history_service if self._service else None
        if hs is None:
            return None
        return hs.query_trend(device_id, param_name, hours=hours)

    def export_history_csv(self, file_path: str, device_id: str, param_names: list) -> bool:
        hs = self._service._history_service if self._service else None
        if hs is None:
            return False
        return hs.export_csv(file_path, device_id, param_names)

    def get_health_report(self, device_id: str) -> Optional[Dict]:
        ans = self._service._anomaly_service if self._service else None
        if ans is None:
            return None
        return ans.get_health_report(device_id)

    def is_history_available(self) -> bool:
        return self._service is not None and self._service._history_service is not None

    def is_anomaly_available(self) -> bool:
        return self._service is not None and self._service._anomaly_service is not None

    def set_service(self, service: MCGSService):
        self._service = service

    def initialize_service(
        self,
        reader=None,
        history_service=None,
        anomaly_service=None,
    ):
        if reader is not None:
            self._service.set_reader(reader)
        if history_service is not None:
            self._service.set_history_service(history_service)
        if anomaly_service is not None:
            self._service.set_anomaly_service(anomaly_service)

    def connect_device(self, device_id: str):
        task = _ConnectTask(self._service, device_id)
        task.signals.finished.connect(self._on_connect_finished)
        self._start_task(task)

    def connect_devices(self, device_ids: List[str]):
        for device_id in device_ids:
            self.connect_device(device_id)

    def disconnect_device(self, device_id: str):
        try:
            success = self._service.disconnect_device(device_id)
            if device_id in self._polling_device_ids:
                self._polling_device_ids.remove(device_id)
            self.device_connected.emit(device_id, False, "已断开")
        except Exception as e:
            logger.error("断开设备[%s]异常: %s", device_id, e)
            self.device_error.emit(device_id, str(e))

    def read_device(self, device_id: str):
        task = _ReadAndProcessTask(self._service, device_id)
        task.signals.finished.connect(self._on_read_finished)
        self._start_task(task)

    def start_polling(self, device_ids: List[str], interval_ms: int = 1000):
        if self._is_polling:
            self.stop_polling()

        self._polling_device_ids = list(device_ids)
        self._poll_interval_ms = interval_ms
        self._is_polling = True
        self._poll_cycle_count = 0

        self._poll_timer.start(interval_ms)
        self.polling_started.emit()
        logger.info(
            "MCGS轮询已启动 [设备=%s, 间隔=%dms]",
            device_ids, interval_ms,
        )

    def stop_polling(self):
        if not self._is_polling:
            return

        self._poll_timer.stop()
        self._is_polling = False
        self.polling_stopped.emit()
        logger.info("MCGS轮询已停止 [周期数=%d]", self._poll_cycle_count)

    def get_reader(self):
        return self._service._reader

    def get_device_config(self, device_id: str):
        reader = self.get_reader()
        if reader and hasattr(reader, 'get_device_config'):
            return reader.get_device_config(device_id)
        return None

    def list_devices(self) -> List[str]:
        reader = self.get_reader()
        if reader and hasattr(reader, 'list_devices'):
            return reader.list_devices()
        return []

    def create_reader(self, config_path: str):
        try:
            from core.utils.mcgs_modbus_reader import MCGSModbusReader
            reader = MCGSModbusReader(config_path)
            self._service.set_reader(reader)
            logger.info("MCGS读取器已创建: %s", config_path)
            return reader
        except Exception as e:
            logger.error("创建MCGS读取器失败: %s", e)
            return None

    def reset_reader(self):
        self._service.set_reader(None)

    def _start_task(self, task: QRunnable):
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(task)

    @Slot(str, bool, str)
    def _on_connect_finished(self, device_id: str, success: bool, msg: str):
        self.device_connected.emit(device_id, success, msg)
        if success:
            logger.info("[%s] 连接完成: %s", device_id, msg)
        else:
            logger.warning("[%s] 连接失败: %s", device_id, msg)

    @Slot(object)
    def _on_read_finished(self, result: MCGSReadResult):
        self._update_stats_from_result(result)
        if result.success:
            self.device_data_updated.emit(result.device_id, result.parsed_data)
        else:
            self.device_error.emit(result.device_id, result.error_message)

    @Slot()
    def _on_poll_timeout(self):
        if not self._polling_device_ids:
            return

        task = _BatchReadTask(self._service, self._polling_device_ids)
        task.signals.finished.connect(self._on_batch_read_finished)
        self._start_task(task)

    @Slot(list)
    def _on_batch_read_finished(self, results: list):
        self._poll_cycle_count += 1
        success_count = 0
        fail_count = 0

        for result in results:
            self._update_stats_from_result(result)
            if result.success:
                success_count += 1
                self.device_data_updated.emit(result.device_id, result.parsed_data)
            else:
                fail_count += 1
                self.device_error.emit(result.device_id, result.error_message)

        self.poll_cycle_completed.emit(success_count, fail_count)

    def _update_stats_from_result(self, result: MCGSReadResult):
        self._stats["total_reads"] += 1
        if result.success:
            self._stats["successful_reads"] += 1
            from datetime import datetime
            self._stats["last_read_time"] = datetime.now()
        else:
            self._stats["failed_reads"] += 1

    @Slot(str, dict)
    def _on_bus_data_updated(self, device_id: str, data: dict):
        self.device_data_updated.emit(device_id, data)

    @Slot(str, str)
    def _on_bus_comm_error(self, device_id: str, error_msg: str):
        self.device_error.emit(device_id, error_msg)

    @Slot(str)
    def _on_bus_device_connected(self, device_id: str):
        pass

    @Slot(str)
    def _on_bus_device_disconnected(self, device_id: str):
        if device_id in self._polling_device_ids:
            self._polling_device_ids.remove(device_id)

    def cleanup(self):
        self.stop_polling()
        if self._service:
            self._service = None
        logger.info("MCGSController 已清理")

    # ══════════════════════════════════════════════
    # v4.0 网关化 API（规范控制点④）
    # ══════════════════════════════════════════════

    def connect_gateway(self, device_manager, gateway_id: str) -> bool:
        """通过 DeviceManager 网关化 API 连接网关"""
        return device_manager.connect_gateway(gateway_id)

    def disconnect_gateway(self, device_manager, gateway_id: str):
        """通过 DeviceManager 网关化 API 断开网关"""
        device_manager.disconnect_gateway(gateway_id)

    def get_gateway_models(self, device_manager) -> dict:
        """获取所有网关模型"""
        return device_manager.get_all_gateway_models()

    def get_gateway_variable_names(self, device_manager, gateway_id: str) -> list:
        """获取网关下的变量名列表"""
        model = device_manager.get_gateway_model(gateway_id)
        return model.get_variable_names() if model else []
