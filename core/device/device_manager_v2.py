# -*- coding: utf-8 -*-
"""
设备管理器 (重构版)
Device Manager v2 - 改进轮询机制和错误处理
"""

import json
import os
import time
import uuid
from collections import deque
from datetime import datetime
from enum import IntEnum
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from ..data import DatabaseManager, DeviceRepository, HistoricalDataRepository
from ..utils.logger_v2 import get_logger
from .device_factory import DeviceFactory, ProtocolType
from .device_model import Device, DeviceStatus

logger = get_logger("device_manager")


class PollPriority(IntEnum):
    """轮询优先级"""

    HIGH = 0  # 高频数据 (100-500ms)
    NORMAL = 1  # 普通数据 (500-1000ms)
    LOW = 2  # 低频数据 (1000-5000ms)


class DevicePollInfo:
    """设备轮询信息"""

    def __init__(self, device: Device, priority: PollPriority = PollPriority.NORMAL):
        self.device = device
        self.priority = priority
        self.last_poll_time = 0
        self.poll_interval = 1000  # ms
        self.next_poll_time = 0
        self.consecutive_errors = 0
        self.max_errors = 3
        self.backoff_time = 0  # 退避时间

    def should_poll(self, current_time: int) -> bool:
        """是否应该轮询"""
        if self.backoff_time > 0 and current_time < self.backoff_time:
            return False
        return current_time >= self.next_poll_time

    def update_poll_time(self, current_time: int):
        """更新轮询时间"""
        self.last_poll_time = current_time
        # 根据优先级调整间隔
        intervals = {PollPriority.HIGH: 200, PollPriority.NORMAL: 1000, PollPriority.LOW: 5000}
        self.poll_interval = intervals.get(self.priority, 1000)
        self.next_poll_time = current_time + self.poll_interval

    def on_error(self):
        """处理错误 - 指数退避"""
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.max_errors:
            # 指数退避: 1s, 2s, 4s, 8s, max 30s
            backoff_seconds = min(2 ** (self.consecutive_errors - self.max_errors), 30)
            self.backoff_time = int(time.time() * 1000) + (backoff_seconds * 1000)
            logger.warning(
                "设备轮询错误过多，进入退避模式",
                device_id=self.device.get_device_id(),
                consecutive_errors=self.consecutive_errors,
                backoff_seconds=backoff_seconds,
            )

    def on_success(self):
        """处理成功"""
        if self.consecutive_errors > 0:
            logger.info("设备轮询恢复", device_id=self.device.get_device_id(), previous_errors=self.consecutive_errors)
        self.consecutive_errors = 0
        self.backoff_time = 0


class DeviceManagerV2(QObject):
    """
    设备管理器 v2
    - 自适应轮询间隔
    - 指数退避重连
    - 优先级队列
    - 数据持久化
    """

    # 信号定义
    device_added = Signal(str)  # 设备添加信号 (device_id)
    device_removed = Signal(str)  # 设备移除信号 (device_id)
    device_connected = Signal(str)  # 设备连接信号 (device_id)
    device_disconnected = Signal(str)  # 设备断开信号 (device_id)
    device_data_updated = Signal(str, dict)  # 设备数据更新信号 (device_id, data)
    device_error = Signal(str, str)  # 设备错误信号 (device_id, error)
    device_reconnecting = Signal(str, int)  # 设备重连信号 (device_id, attempt)

    def __init__(self, config_file: str = "config.json", db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self._config_file = config_file
        self._db_manager = db_manager or DatabaseManager()
        self._devices: Dict[str, DevicePollInfo] = {}
        self._poll_timer = QTimer()
        self._manually_disconnected: set = set()  # 手动断开的设备集合
        self._poll_timer.timeout.connect(self._poll_all_devices)
        self._poll_interval = 100  # 100ms 基础轮询间隔

        # 重连管理
        self._reconnect_timer = QTimer()
        self._reconnect_timer.timeout.connect(self._check_reconnect)
        self._reconnect_queue: deque = deque()
        self._reconnect_attempts: Dict[str, int] = {}
        self._max_reconnect_attempts = 5
        self._reconnect_interval = 5000  # 5秒基础重连间隔

        # 历史数据批量写入
        self._data_buffer: List[Tuple[str, str, float, str]] = []
        self._buffer_flush_timer = QTimer()
        self._buffer_flush_timer.timeout.connect(self._flush_data_buffer)
        self._buffer_flush_interval = 5000  # 5秒刷新一次

        self._load_devices()
        self._start_timers()

        # 如果没有任何设备，自动添加默认设备
        if not self._devices:
            self._init_default_devices()

        logger.info("设备管理器 v2 初始化完成")

    def _start_timers(self):
        """启动定时器"""
        self._poll_timer.start(self._poll_interval)
        self._reconnect_timer.start(self._reconnect_interval)
        self._buffer_flush_timer.start(self._buffer_flush_interval)

    def _load_devices(self):
        """加载设备配置"""
        if not os.path.exists(self._config_file):
            return

        try:
            # 优先从数据库加载
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                devices = repo.get_all_with_registers()

                for device_model in devices:
                    config = repo.to_config(device_model)
                    self._create_device_internal(config["device_id"], config)

            logger.info(f"从数据库加载了 {len(devices)} 个设备")

        except Exception as e:
            logger.error("从数据库加载设备失败", error=str(e))
            # 回退到从JSON加载
            self._load_from_json()

    def _load_from_json(self):
        """从JSON文件加载（兼容旧版本）"""
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            devices_config = config.get("devices", [])
            for device_config in devices_config:
                device_id = device_config.get("device_id")
                if device_id:
                    self._create_device_internal(device_id, device_config)

            logger.info(f"从JSON加载了 {len(devices_config)} 个设备")

        except Exception as e:
            logger.error("从JSON加载设备失败", error=str(e))

    def _init_default_devices(self):
        """初始化默认设备: 5个Modbus TCP + 5个Modbus RTU"""
        logger.info("未检测到设备，正在创建默认设备...")

        # 5个 Modbus TCP 设备
        for i in range(1, 6):
            config = {
                "device_id": f"tcp_{i:03d}",
                "name": f"Modbus TCP 设备 {i}",
                "device_type": "Modbus TCP",
                "protocol_type": "modbus_tcp",
                "host": "127.0.0.1",
                "port": 502,
                "unit_id": i,
                "use_simulator": True,
            }
            try:
                with self._db_manager.session() as session:
                    repo = DeviceRepository(session)
                    repo.create_from_config(config)
                self._create_device_internal(config["device_id"], config)
                logger.info(f"默认设备已创建: {config['name']}")
            except Exception as e:
                logger.error(f"创建默认TCP设备失败: {config['name']}", error=str(e))

        # 5个 Modbus RTU 设备
        rtu_ports = ["COM1", "COM2", "COM3", "COM4", "COM5"]
        for i in range(1, 6):
            config = {
                "device_id": f"rtu_{i:03d}",
                "name": f"Modbus RTU 设备 {i}",
                "device_type": "Modbus RTU",
                "protocol_type": "modbus_rtu",
                "port": rtu_ports[i - 1],
                "baudrate": 9600,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "unit_id": i,
                "use_simulator": True,
            }
            try:
                with self._db_manager.session() as session:
                    repo = DeviceRepository(session)
                    repo.create_from_config(config)
                self._create_device_internal(config["device_id"], config)
                logger.info(f"默认设备已创建: {config['name']}")
            except Exception as e:
                logger.error(f"创建默认RTU设备失败: {config['name']}", error=str(e))

        self._save_json_config()
        logger.info(f"默认设备创建完成: 共 {len(self._devices)} 个设备")

    def _create_device_internal(self, device_id: str, config: dict) -> Device:
        """内部创建设备"""
        device = DeviceFactory.create_device(device_id, config)

        # 连接信号
        device.status_changed.connect(lambda s, d=device_id: self._on_device_status_changed(d, s))
        device.data_updated.connect(lambda data, d=device_id: self._on_device_data_updated(d, data))
        device.error_occurred.connect(lambda error, d=device_id: self._on_device_error(d, error))

        # 确定优先级
        priority = self._determine_priority(config)
        poll_info = DevicePollInfo(device, priority)
        poll_info.poll_interval = config.get("poll_interval", 1000)

        self._devices[device_id] = poll_info
        return device

    def _determine_priority(self, config: dict) -> PollPriority:
        """根据设备类型确定轮询优先级"""
        device_type = config.get("device_type", "").lower()

        # 高频设备
        high_priority_types = ["传感器", "变送器", "流量计", "压力计"]
        if any(t in device_type for t in high_priority_types):
            return PollPriority.HIGH

        # 低频设备
        low_priority_types = [" historian", "记录仪", "存档"]
        if any(t in device_type for t in low_priority_types):
            return PollPriority.LOW

        return PollPriority.NORMAL

    def add_device(self, device_config: Dict) -> str:
        """添加设备"""
        device_id = device_config.get("device_id") or str(uuid.uuid4())[:8]
        device_config["device_id"] = device_id

        try:
            # 创建数据库记录
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                repo.create_from_config(device_config)

            # 创建设备对象
            self._create_device_internal(device_id, device_config)

            # 保存JSON（兼容）
            self._save_json_config()

            logger.info("设备添加成功", device_id=device_id, name=device_config.get("name"))
            self.device_added.emit(device_id)
            return device_id

        except Exception as e:
            logger.error("添加设备失败", device_id=device_id, error=str(e))
            raise

    def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        if device_id not in self._devices:
            return False

        try:
            # 断开连接
            poll_info = self._devices[device_id]
            poll_info.device.disconnect()

            # 从数据库删除
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                repo.delete_with_relations(device_id)

            # 从内存移除
            del self._devices[device_id]

            # 保存JSON
            self._save_json_config()

            logger.info("设备移除成功", device_id=device_id)
            self.device_removed.emit(device_id)
            return True

        except Exception as e:
            logger.error("移除设备失败", device_id=device_id, error=str(e))
            return False

    def connect_device(self, device_id: str) -> bool:
        """连接设备"""
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        poll_info = self._devices[device_id]
        device = poll_info.device

        try:
            logger.info("正在连接设备", device_id=device_id)
            success = device.connect()

            if success:
                poll_info.on_success()
                # 重置重连计数
                if device_id in self._reconnect_attempts:
                    del self._reconnect_attempts[device_id]
            else:
                # 加入重连队列
                self._schedule_reconnect(device_id)

            return success

        except Exception as e:
            logger.error("连接设备异常", device_id=device_id, error=str(e))
            self._schedule_reconnect(device_id)
            return False

    def disconnect_device(self, device_id: str):
        """断开设备"""
        if device_id in self._devices:
            self._manually_disconnected.add(device_id)  # 标记为手动断开
            self._devices[device_id].device.disconnect()
            logger.info("设备断开连接", device_id=device_id)

    def edit_device(self, device_id: str, new_config: Dict) -> bool:
        """编辑设备"""
        if device_id not in self._devices:
            return False

        try:
            # 断开旧设备
            poll_info = self._devices[device_id]
            poll_info.device.disconnect()

            # 更新数据库
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                repo.update_from_config(device_id, new_config)

            # 重新创建设备
            new_config["device_id"] = device_id
            self._create_device_internal(device_id, new_config)

            # 保存JSON
            self._save_json_config()

            logger.info("设备更新成功", device_id=device_id)
            self.device_added.emit(device_id)
            return True

        except Exception as e:
            logger.error("更新设备失败", device_id=device_id, error=str(e))
            return False

    def _poll_all_devices(self):
        """轮询所有设备"""
        current_time = int(time.time() * 1000)

        for device_id, poll_info in self._devices.items():
            if poll_info.device.get_status() != DeviceStatus.CONNECTED:
                continue

            if not poll_info.should_poll(current_time):
                continue

            try:
                data = poll_info.device.poll_data()
                if data:
                    poll_info.on_success()
                    self._persist_data(device_id, data)
                poll_info.update_poll_time(current_time)

            except Exception as e:
                poll_info.on_error()
                logger.error("轮询设备失败", device_id=device_id, error=str(e))

    def _persist_data(self, device_id: str, data: Dict):
        """持久化数据到缓冲区"""
        for param_name, param_info in data.items():
            if isinstance(param_info, dict) and "value" in param_info:
                self._data_buffer.append(
                    (device_id, param_name, float(param_info["value"]), param_info.get("unit", ""))
                )

    def _flush_data_buffer(self):
        """刷新数据缓冲区到数据库"""
        if not self._data_buffer:
            return

        try:
            with self._db_manager.session() as session:
                repo = HistoricalDataRepository(session)

                # 批量创建
                data_points = [
                    {"device_id": d[0], "parameter_name": d[1], "value": d[2], "unit": d[3]} for d in self._data_buffer
                ]

                count = repo.batch_create(data_points)
                logger.debug(f"批量写入 {count} 条历史数据")

        except Exception as e:
            logger.error("批量写入历史数据失败", error=str(e))
        finally:
            self._data_buffer.clear()

    def _check_reconnect(self):
        """检查并执行重连"""
        if not self._reconnect_queue:
            return

        device_id = self._reconnect_queue.popleft()

        if device_id not in self._devices:
            return

        device = self._devices[device_id].device

        # 如果已经连接，跳过
        if device.get_status() == DeviceStatus.CONNECTED:
            if device_id in self._reconnect_attempts:
                del self._reconnect_attempts[device_id]
            return

        # 检查重连次数
        attempts = self._reconnect_attempts.get(device_id, 0)
        if attempts >= self._max_reconnect_attempts:
            logger.error(
                "设备重连次数超过上限，停止重连", device_id=device_id, max_attempts=self._max_reconnect_attempts
            )
            del self._reconnect_attempts[device_id]
            return

        # 执行重连
        attempts += 1
        self._reconnect_attempts[device_id] = attempts

        logger.info("尝试重连设备", device_id=device_id, attempt=attempts)
        self.device_reconnecting.emit(device_id, attempts)

        try:
            success = device.connect()
            if success:
                logger.info("设备重连成功", device_id=device_id)
                del self._reconnect_attempts[device_id]
                self.device_connected.emit(device_id)
            else:
                # 重新加入队列，使用指数退避
                backoff = min(2**attempts, 60)  # 最大60秒
                QTimer.singleShot(backoff * 1000, lambda: self._schedule_reconnect(device_id))
        except Exception as e:
            logger.error("设备重连失败", device_id=device_id, error=str(e))
            self._schedule_reconnect(device_id)

    def _schedule_reconnect(self, device_id: str):
        """安排重连"""
        if device_id not in self._reconnect_queue:
            self._reconnect_queue.append(device_id)

    def _on_device_status_changed(self, device_id: str, status: int):
        """处理设备状态变化"""
        if status == DeviceStatus.CONNECTED:
            self._manually_disconnected.discard(device_id)  # 连接成功，清除手动断开标记
            self.device_connected.emit(device_id)
        elif status == DeviceStatus.DISCONNECTED:
            self.device_disconnected.emit(device_id)
            # 手动断开的设备不自动重连
            if device_id not in self._manually_disconnected:
                self._schedule_reconnect(device_id)
        elif status == DeviceStatus.ERROR:
            # 错误状态也尝试重连（手动断开后不会进入ERROR状态，此处安全）
            if device_id not in self._manually_disconnected:
                self._schedule_reconnect(device_id)

    def _on_device_data_updated(self, device_id: str, data: Dict):
        """处理设备数据更新"""
        self.device_data_updated.emit(device_id, data)

    def _on_device_error(self, device_id: str, error: str):
        """处理设备错误"""
        logger.error("设备错误", device_id=device_id, error=error)
        self.device_error.emit(device_id, error)

    def _save_json_config(self):
        """保存JSON配置（兼容旧版本）"""
        try:
            devices_config = []
            for device_id, poll_info in self._devices.items():
                devices_config.append(poll_info.device.get_device_config())

            config = {"version": "2.0", "devices": devices_config}

            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error("保存JSON配置失败", error=str(e))

    def get_device(self, device_id: str) -> Optional[Device]:
        """获取设备"""
        if device_id in self._devices:
            return self._devices[device_id].device
        return None

    def get_all_devices(self) -> List[Dict]:
        """获取所有设备列表"""
        result = []
        for device_id, poll_info in self._devices.items():
            device = poll_info.device
            config = device.get_device_config()
            result.append(
                {
                    "device_id": device_id,
                    "name": config.get("name", f"设备_{device_id}"),
                    "status": device.get_status(),
                    "use_simulator": device.is_using_simulator(),
                    "config": config,
                    "priority": poll_info.priority.name,
                    "poll_interval": poll_info.poll_interval,
                }
            )
        return result

    def get_connected_devices(self) -> List[Device]:
        """获取已连接设备"""
        return [
            poll_info.device
            for poll_info in self._devices.values()
            if poll_info.device.get_status() == DeviceStatus.CONNECTED
        ]

    def set_poll_interval(self, interval_ms: int):
        """设置轮询间隔"""
        self._poll_interval = max(50, min(interval_ms, 1000))
        self._poll_timer.setInterval(self._poll_interval)

    def cleanup(self):
        """清理资源"""
        logger.info("设备管理器清理资源")

        # 停止定时器
        self._poll_timer.stop()
        self._reconnect_timer.stop()
        self._buffer_flush_timer.stop()

        # 刷新数据缓冲区
        self._flush_data_buffer()

        # 断开所有设备
        for poll_info in self._devices.values():
            poll_info.device.disconnect()

        # 关闭数据库
        if self._db_manager:
            self._db_manager.close()

    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except RuntimeError:
            # QTimer可能已被Qt删除，忽略此错误
            pass
