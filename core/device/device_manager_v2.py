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

        # 动态轮询间隔相关
        self.response_times = deque(maxlen=10)  # 最近10次响应时间
        self.min_interval = 100  # 最小轮询间隔 (ms)
        self.max_interval = 10000  # 最大轮询间隔 (ms)
        self.target_response_time = 50  # 目标响应时间 (ms)
        self.adjustment_factor = 0.1  # 调整因子

        # 轮询统计
        self.total_polls = 0
        self.successful_polls = 0
        self.failed_polls = 0

        # 故障诊断和恢复相关
        self.error_history = deque(maxlen=20)  # 最近20次错误记录
        self.fault_type = None  # 当前故障类型
        self.fault_start_time = None  # 故障开始时间
        self.fault_duration = 0  # 故障持续时间 (ms)
        self.recovery_attempts = 0  # 恢复尝试次数
        self.max_recovery_attempts = 5  # 最大恢复尝试次数
        self.recovery_mode = "auto"  # 恢复模式: auto/manual
        self.recovery_status = "none"  # 恢复状态: none/attempting/succeeded/failed
        self.recovery_history = []  # 恢复历史记录
        self.fault_detection_enabled = True  # 是否启用故障检测
        self.recovery_enabled = True  # 是否启用自动恢复

        # 自动重连开关
        self.auto_reconnect_enabled = False  # 是否启用自动重连

        # 常见故障类型
        self.FAULT_TYPES = {
            "communication_timeout": "通信超时",
            "connection_refused": "连接被拒绝",
            "invalid_response": "无效响应",
            "device_offline": "设备离线",
            "protocol_error": "协议错误",
            "unknown": "未知错误",
        }

    def should_poll(self, current_time: int) -> bool:
        """是否应该轮询"""
        if self.backoff_time > 0 and current_time < self.backoff_time:
            return False
        return current_time >= self.next_poll_time

    def update_poll_time(self, current_time: int, response_time: float = 0):
        """更新轮询时间，支持动态调整

        Args:
            current_time: 当前时间 (ms)
            response_time: 本次轮询响应时间 (ms)
        """
        self.last_poll_time = current_time

        # 记录响应时间
        if response_time > 0:
            self.response_times.append(response_time)
            self._adjust_poll_interval()

        # 如果没有响应时间记录，使用默认优先级间隔
        if not self.response_times:
            intervals = {PollPriority.HIGH: 200, PollPriority.NORMAL: 1000, PollPriority.LOW: 5000}
            self.poll_interval = intervals.get(self.priority, 1000)

        # 确保轮询间隔在合理范围内
        self.poll_interval = max(self.min_interval, min(self.poll_interval, self.max_interval))
        self.next_poll_time = current_time + int(self.poll_interval)

        # 更新统计
        self.total_polls += 1

    def _adjust_poll_interval(self):
        """根据响应时间动态调整轮询间隔"""
        if not self.response_times:
            return

        # 计算平均响应时间
        avg_response = sum(self.response_times) / len(self.response_times)

        # 根据响应时间调整轮询间隔
        if avg_response < self.target_response_time:
            # 响应时间快，可以增加轮询频率（减小间隔）
            self.poll_interval *= 1 - self.adjustment_factor
        elif avg_response > self.target_response_time * 2:
            # 响应时间慢，降低轮询频率（增加间隔）
            self.poll_interval *= 1 + self.adjustment_factor
        # 否则保持不变

        logger.debug(
            "动态调整轮询间隔",
            device_id=self.device.get_device_id(),
            avg_response=avg_response,
            new_interval=self.poll_interval,
            target_response=self.target_response_time,
        )

    def on_success(self):
        """处理成功"""
        if self.consecutive_errors > 0:
            logger.info("设备轮询恢复", device_id=self.device.get_device_id(), previous_errors=self.consecutive_errors)

        # 清除故障状态
        self._clear_fault()

        self.consecutive_errors = 0
        self.backoff_time = 0

    def on_error(self, error_type="unknown", error_msg=""):
        """处理错误 - 指数退避并记录故障信息"""
        self.consecutive_errors += 1

        # 记录错误历史
        error_entry = {
            "timestamp": int(time.time() * 1000),
            "error_type": error_type,
            "error_msg": error_msg,
            "consecutive_errors": self.consecutive_errors,
        }
        self.error_history.append(error_entry)

        # 检测故障
        self._detect_fault(error_type, error_msg)

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

            # 触发恢复流程
            if self.recovery_enabled:
                self._start_recovery()

    def _detect_fault(self, error_type, error_msg):
        """检测并识别故障类型"""
        if not self.fault_detection_enabled:
            return

        # 如果当前没有故障，开始新故障记录
        if not self.fault_type:
            self.fault_type = error_type
            self.fault_start_time = int(time.time() * 1000)
            logger.info(
                "设备故障检测到",
                device_id=self.device.get_device_id(),
                fault_type=self.FAULT_TYPES.get(error_type, error_type),
                error_msg=error_msg,
            )

        # 更新故障持续时间
        self.fault_duration = int(time.time() * 1000) - self.fault_start_time

    def _clear_fault(self):
        """清除故障状态"""
        if self.fault_type:
            # 记录故障恢复
            fault_info = {
                "fault_type": self.fault_type,
                "start_time": self.fault_start_time,
                "duration": self.fault_duration,
                "recovery_attempts": self.recovery_attempts,
                "recovery_status": self.recovery_status,
            }

            logger.info(
                "设备故障恢复",
                device_id=self.device.get_device_id(),
                fault_type=self.FAULT_TYPES.get(self.fault_type, self.fault_type),
                duration=self.fault_duration,
                recovery_attempts=self.recovery_attempts,
            )

            # 重置故障状态
            self.fault_type = None
            self.fault_start_time = None
            self.fault_duration = 0
            self.recovery_attempts = 0
            self.recovery_status = "none"

    def _start_recovery(self):
        """启动恢复流程"""
        if self.recovery_status in ["attempting", "succeeded"]:
            return

        self.recovery_status = "attempting"
        self.recovery_attempts = 0
        logger.info(
            "启动设备故障恢复",
            device_id=self.device.get_device_id(),
            fault_type=self.FAULT_TYPES.get(self.fault_type, self.fault_type),
        )

        # 执行恢复尝试
        self._attempt_recovery()

    def _attempt_recovery(self):
        """执行恢复尝试"""
        if not self.recovery_enabled or self.recovery_status != "attempting":
            return

        self.recovery_attempts += 1

        # 记录恢复尝试
        recovery_entry = {
            "timestamp": int(time.time() * 1000),
            "attempt": self.recovery_attempts,
            "status": "in_progress",
            "fault_type": self.fault_type,
        }

        logger.info(
            "设备恢复尝试",
            device_id=self.device.get_device_id(),
            attempt=self.recovery_attempts,
            fault_type=self.FAULT_TYPES.get(self.fault_type, self.fault_type),
        )

        try:
            # 根据故障类型执行不同的恢复策略
            if self.fault_type in ["communication_timeout", "connection_refused", "device_offline"]:
                # 通信相关故障 - 尝试重新连接
                success = self.device.reconnect() if hasattr(self.device, "reconnect") else self.device.connect()
            elif self.fault_type in ["invalid_response", "protocol_error"]:
                # 协议相关故障 - 尝试重置设备状态
                success = self.device.reset() if hasattr(self.device, "reset") else False
            else:
                # 未知故障 - 尝试重新连接
                success = self.device.reconnect() if hasattr(self.device, "reconnect") else self.device.connect()

            if success:
                # 恢复成功
                recovery_entry["status"] = "succeeded"
                recovery_entry["message"] = "恢复成功"
                self.recovery_status = "succeeded"
                self.recovery_history.append(recovery_entry)
                logger.info("设备恢复成功", device_id=self.device.get_device_id(), attempt=self.recovery_attempts)
            else:
                # 恢复失败
                recovery_entry["status"] = "failed"
                recovery_entry["message"] = "恢复失败"
                self.recovery_history.append(recovery_entry)

                if self.recovery_attempts >= self.max_recovery_attempts:
                    # 达到最大尝试次数，放弃恢复
                    self.recovery_status = "failed"
                    logger.error(
                        "设备恢复失败达到最大尝试次数",
                        device_id=self.device.get_device_id(),
                        max_attempts=self.max_recovery_attempts,
                    )
                else:
                    # 稍后重试，使用指数退避
                    backoff_time = min(2 ** (self.recovery_attempts - 1), 30) * 1000
                    logger.info(
                        "设备恢复失败，稍后重试",
                        device_id=self.device.get_device_id(),
                        attempt=self.recovery_attempts,
                        backoff_time=backoff_time,
                    )
                    # 注意：这里需要在设备管理器中实现定时重试逻辑，因为当前类没有定时器

        except Exception as e:
            # 恢复过程中发生异常
            recovery_entry["status"] = "failed"
            recovery_entry["message"] = f"恢复异常: {str(e)}"
            self.recovery_history.append(recovery_entry)
            logger.error(
                "设备恢复过程异常", device_id=self.device.get_device_id(), attempt=self.recovery_attempts, error=str(e)
            )

            if self.recovery_attempts >= self.max_recovery_attempts:
                self.recovery_status = "failed"


class PollingGroup:
    """轮询组配置"""

    def __init__(
        self, name: str, priority: PollPriority = PollPriority.NORMAL, base_interval: int = 1000, enabled: bool = True
    ):
        self.name = name
        self.priority = priority
        self.base_interval = base_interval
        self.enabled = enabled
        self.device_ids = set()


class DeviceManagerV2(QObject):
    """
    设备管理器 v2
    - 自适应轮询间隔
    - 指数退避重连
    - 优先级队列
    - 数据持久化
    - 设备分组轮询
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

        # 设备分组管理
        self._polling_groups: Dict[str, PollingGroup] = {"default": PollingGroup("default")}
        self._device_groups: Dict[str, str] = {}  # device_id -> group_name

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
                    logger.info(
                        f"加载设备: {device_model.name}, 端口: {device_model.port}, 配置端口: {config.get('port')}"
                    )
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
        # 设置自动重连开关状态
        poll_info.auto_reconnect_enabled = config.get("auto_reconnect_enabled", False)

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

    def connect_device(self, device_id: str) -> tuple[bool, str, str]:
        """连接设备

        Returns:
            tuple: (success, error_type, error_msg)
                success: 连接是否成功
                error_type: 错误类型
                error_msg: 错误消息
        """
        if device_id not in self._devices:
            error_msg = "设备不存在"
            logger.error("设备不存在", device_id=device_id)
            return False, "device_not_found", error_msg

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
                return True, "", ""
            else:
                # 检查是否启用了自动重连
                if poll_info.auto_reconnect_enabled:
                    self._schedule_reconnect(device_id)
                error_msg = "设备连接失败"
                return False, "connect_failed", error_msg

        except Exception as e:
            error_msg = str(e)
            error_type = "unknown"

            # 根据异常类型确定错误类型
            if any(keyword in error_msg.lower() for keyword in ["timeout", "timed out"]):
                error_type = "communication_timeout"
            elif "connection refused" in error_msg.lower() or "connect failed" in error_msg.lower():
                error_type = "connection_refused"
            elif "invalid" in error_msg.lower() or "wrong" in error_msg.lower():
                error_type = "invalid_response"
            elif "offline" in error_msg.lower() or "disconnected" in error_msg.lower():
                error_type = "device_offline"
            elif "protocol" in error_msg.lower() or "modbus" in error_msg.lower():
                error_type = "protocol_error"

            logger.error("连接设备异常", device_id=device_id, error=error_msg)
            # 检查是否启用了自动重连
            if poll_info.auto_reconnect_enabled:
                self._schedule_reconnect(device_id)
            return False, error_type, error_msg

    def set_device_auto_reconnect(self, device_id: str, enabled: bool) -> bool:
        """设置单个设备的自动重连开关

        Args:
            device_id: 设备ID
            enabled: 是否启用自动重连

        Returns:
            bool: 设置是否成功
        """
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        poll_info = self._devices[device_id]
        poll_info.auto_reconnect_enabled = enabled
        logger.info("设置设备自动重连状态", device_id=device_id, enabled=enabled)
        return True

    def set_all_devices_auto_reconnect(self, enabled: bool) -> int:
        """一键设置所有设备的自动重连开关

        Args:
            enabled: 是否启用自动重连

        Returns:
            int: 设置成功的设备数量
        """
        count = 0
        for device_id, poll_info in self._devices.items():
            poll_info.auto_reconnect_enabled = enabled
            count += 1
        logger.info("批量设置设备自动重连状态", count=count, enabled=enabled)
        return count

    def get_auto_reconnect_status(self) -> tuple[int, int]:
        """获取所有设备的自动重连状态

        Returns:
            tuple: (enabled_count, disabled_count)
                enabled_count: 启用自动重连的设备数量
                disabled_count: 禁用自动重连的设备数量
        """
        enabled_count = 0
        disabled_count = 0
        for poll_info in self._devices.values():
            if poll_info.auto_reconnect_enabled:
                enabled_count += 1
            else:
                disabled_count += 1
        return enabled_count, disabled_count

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

            # 检查设备所属组是否启用
            group_name = self._device_groups.get(device_id, "default")
            group = self._polling_groups.get(group_name, None)
            if not group or not group.enabled:
                continue

            if not poll_info.should_poll(current_time):
                continue

            try:
                # 测量响应时间
                start_time = time.time()
                data = poll_info.device.poll_data()
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # 转换为 ms

                if data:
                    poll_info.on_success()
                    poll_info.successful_polls += 1
                    self._persist_data(device_id, data)
                else:
                    poll_info.failed_polls += 1

                # 更新轮询时间，传入响应时间进行动态调整
                poll_info.update_poll_time(current_time, response_time)

            except Exception as e:
                # 根据异常类型确定故障类型
                error_msg = str(e)
                error_type = "unknown"

                if any(keyword in error_msg.lower() for keyword in ["timeout", "timed out"]):
                    error_type = "communication_timeout"
                elif "connection refused" in error_msg.lower() or "connect failed" in error_msg.lower():
                    error_type = "connection_refused"
                elif "invalid" in error_msg.lower() or "wrong" in error_msg.lower():
                    error_type = "invalid_response"
                elif "offline" in error_msg.lower() or "disconnected" in error_msg.lower():
                    error_type = "device_offline"
                elif "protocol" in error_msg.lower() or "modbus" in error_msg.lower():
                    error_type = "protocol_error"

                poll_info.on_error(error_type, error_msg)
                poll_info.failed_polls += 1
                logger.error("轮询设备失败", device_id=device_id, error=error_msg, fault_type=error_type)

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
                poll_info = self._devices[device_id]
                poll_info.on_success()
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
            # 检查是否启用了自动重连，且不是手动断开的设备
            if device_id not in self._manually_disconnected:
                poll_info = self._devices.get(device_id)
                if poll_info and poll_info.auto_reconnect_enabled:
                    self._schedule_reconnect(device_id)
        elif status == DeviceStatus.ERROR:
            # 错误状态也尝试重连（手动断开后不会进入ERROR状态，此处安全）
            if device_id not in self._manually_disconnected:
                poll_info = self._devices.get(device_id)
                if poll_info and poll_info.auto_reconnect_enabled:
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
                    # 故障恢复相关信息
                    "fault_type": poll_info.fault_type,
                    "fault_start_time": poll_info.fault_start_time,
                    "fault_duration": poll_info.fault_duration,
                    "recovery_attempts": poll_info.recovery_attempts,
                    "recovery_status": poll_info.recovery_status,
                    "recovery_mode": poll_info.recovery_mode,
                    "recovery_enabled": poll_info.recovery_enabled,
                    "fault_detection_enabled": poll_info.fault_detection_enabled,
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

    # ------------------- 故障恢复控制方法 -------------------

    def enable_fault_detection(self, device_id: str, enabled: bool) -> bool:
        """启用/禁用设备故障检测"""
        if device_id not in self._devices:
            return False

        self._devices[device_id].fault_detection_enabled = enabled
        logger.info("更新设备故障检测状态", device_id=device_id, enabled=enabled)
        return True

    def enable_auto_recovery(self, device_id: str, enabled: bool) -> bool:
        """启用/禁用设备自动恢复"""
        if device_id not in self._devices:
            return False

        self._devices[device_id].recovery_enabled = enabled
        logger.info("更新设备自动恢复状态", device_id=device_id, enabled=enabled)
        return True

    def set_recovery_mode(self, device_id: str, mode: str) -> bool:
        """设置设备恢复模式 (auto/manual)"""
        if device_id not in self._devices or mode not in ["auto", "manual"]:
            return False

        self._devices[device_id].recovery_mode = mode
        logger.info("更新设备恢复模式", device_id=device_id, mode=mode)
        return True

    def set_max_recovery_attempts(self, device_id: str, max_attempts: int) -> bool:
        """设置设备最大恢复尝试次数"""
        if device_id not in self._devices or max_attempts <= 0:
            return False

        self._devices[device_id].max_recovery_attempts = max_attempts
        logger.info("更新设备最大恢复尝试次数", device_id=device_id, max_attempts=max_attempts)
        return True

    def get_fault_recovery_status(self, device_id: str) -> Dict:
        """获取设备故障恢复状态"""
        if device_id not in self._devices:
            return {}

        poll_info = self._devices[device_id]
        return {
            "fault_type": poll_info.fault_type,
            "fault_start_time": poll_info.fault_start_time,
            "fault_duration": poll_info.fault_duration,
            "recovery_attempts": poll_info.recovery_attempts,
            "max_recovery_attempts": poll_info.max_recovery_attempts,
            "recovery_status": poll_info.recovery_status,
            "recovery_mode": poll_info.recovery_mode,
            "recovery_enabled": poll_info.recovery_enabled,
            "fault_detection_enabled": poll_info.fault_detection_enabled,
            "recovery_history": poll_info.recovery_history[-5:],  # 最近5次恢复尝试
            "error_history": poll_info.error_history[-10:],  # 最近10次错误记录
        }

    def manual_recovery(self, device_id: str) -> bool:
        """手动触发设备恢复"""
        if device_id not in self._devices:
            return False

        poll_info = self._devices[device_id]
        poll_info.recovery_mode = "manual"

        try:
            logger.info("手动触发设备恢复", device_id=device_id)

            # 执行恢复尝试
            poll_info._start_recovery()
            return True
        except Exception as e:
            logger.error("手动恢复设备失败", device_id=device_id, error=str(e))
            return False

    # ------------------- 设备分组管理方法 -------------------

    def add_polling_group(
        self, name: str, priority: PollPriority = PollPriority.NORMAL, base_interval: int = 1000, enabled: bool = True
    ) -> bool:
        """添加轮询组"""
        if name in self._polling_groups:
            logger.error("轮询组已存在", group_name=name)
            return False

        group = PollingGroup(name, priority, base_interval, enabled)
        self._polling_groups[name] = group
        logger.info("添加轮询组成功", group_name=name)
        return True

    def remove_polling_group(self, name: str) -> bool:
        """删除轮询组"""
        if name == "default":
            logger.error("不能删除默认轮询组")
            return False

        if name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=name)
            return False

        # 将组内设备移到默认组
        group = self._polling_groups[name]
        for device_id in group.device_ids:
            self.assign_device_to_group(device_id, "default")

        del self._polling_groups[name]
        logger.info("删除轮询组成功", group_name=name)
        return True

    def assign_device_to_group(self, device_id: str, group_name: str) -> bool:
        """将设备分配到轮询组"""
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        if group_name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=group_name)
            return False

        # 从旧组移除
        old_group = self._device_groups.get(device_id, "default")
        if old_group in self._polling_groups:
            self._polling_groups[old_group].device_ids.discard(device_id)

        # 添加到新组
        self._polling_groups[group_name].device_ids.add(device_id)
        self._device_groups[device_id] = group_name

        # 更新设备优先级
        poll_info = self._devices[device_id]
        poll_info.priority = self._polling_groups[group_name].priority

        logger.info("设备分配到轮询组成功", device_id=device_id, group_name=group_name)
        return True

    def get_group_devices(self, group_name: str) -> List[str]:
        """获取组内设备列表"""
        if group_name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=group_name)
            return []

        return list(self._polling_groups[group_name].device_ids)

    def get_device_group(self, device_id: str) -> str:
        """获取设备所属组"""
        return self._device_groups.get(device_id, "default")

    def get_all_groups(self) -> List[Dict]:
        """获取所有轮询组"""
        result = []
        for group_name, group in self._polling_groups.items():
            result.append(
                {
                    "name": group_name,
                    "priority": group.priority.name,
                    "base_interval": group.base_interval,
                    "enabled": group.enabled,
                    "device_count": len(group.device_ids),
                }
            )
        return result

    def enable_group(self, group_name: str, enabled: bool) -> bool:
        """启用/禁用轮询组"""
        if group_name not in self._polling_groups:
            logger.error("轮询组不存在", group_name=group_name)
            return False

        self._polling_groups[group_name].enabled = enabled
        logger.info("更新轮询组状态成功", group_name=group_name, enabled=enabled)
        return True

    def get_polling_statistics(self) -> Dict:
        """获取轮询统计信息"""
        stats = {
            "total_devices": len(self._devices),
            "total_groups": len(self._polling_groups),
            "total_polls": sum(p.total_polls for p in self._devices.values()),
            "successful_polls": sum(p.successful_polls for p in self._devices.values()),
            "failed_polls": sum(p.failed_polls for p in self._devices.values()),
            "devices_by_group": {},
        }

        # 按组统计
        for group_name, group in self._polling_groups.items():
            stats["devices_by_group"][group_name] = {
                "device_count": len(group.device_ids),
                "enabled": group.enabled,
                "priority": group.priority.name,
            }

        return stats

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
