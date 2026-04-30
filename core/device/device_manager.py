# -*- coding: utf-8 -*-
"""
设备管理器 (v4.0 网关化重构版)

v4.0 网关化重构（规范控制点④）:
- ✅ 双模式: 旧模式(直接设备连接) + 新模式(网关化连接)
- ✅ GatewayEngine集成: 多网关并发管理，每个网关一个长连接线程
- ✅ devices.json支持: 从JSON加载网关配置，运行时动态增删
- ✅ 指数退避重连: 通过ReconnectPolicy实现
- ✅ 心跳管理: 3次无响应强制重置Socket
- ✅ 死区过滤: 通过DataBus DeadbandFilter优化CPU

v3.1 生产级修复（保留）:
- ✅ Shadow Instance原子操作
- ✅ 调度器迭代安全
- ✅ 写锁保护
"""

import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from ..constants import DEFAULT_GROUP_NAME, ERROR_ENHANCE_PREFIXES
from ..data import DatabaseManager, DeviceRepository, HistoricalDataRepository
from ..engine import GatewayEngine, GatewayConfig, GatewayState
from ..foundation.data_bus import DataBus
from ..utils.logger import get_logger
from .config_importer_exporter import ConfigImporterExporter
from .data_persistence_service import DataPersistenceService
from .device_factory import DeviceFactory, ProtocolType
from .device_group_manager import DeviceGroupManager
from .device_lifecycle_manager import DeviceLifecycleManager
from .device_model import Device, DeviceStatus
from .fault_recovery_manager import FaultRecoveryManager
from .gateway_model import GatewayModel, VariablePoint, GatewayStatus
from .polling import DevicePollInfo, PollPriority, PollingGroup
from .polling_worker import AsyncPollingWorker

logger = get_logger("device_manager")

MAX_POLL_DURATION_MS = 500


class DeviceManager(QObject):
    """
    设备管理器
    - 自适应轮询间隔（异步版本）
    - 指数退避重连
    - 优先级队列
    - 数据持久化
    - 设备分组轮询
    
    v3.0 特性：
    - ✅ 异步轮询：所有Modbus通信在工作线程中执行
    - ✅ UI响应式：主线程永不阻塞，保持流畅交互
    - ✅ 并发优化：多设备并行轮询，总耗时大幅降低
    """

    device_added = Signal(str)
    device_removed = Signal(str)
    device_connected = Signal(str)
    device_disconnected = Signal(str)
    device_data_updated = Signal(str, dict)           # 保留：向后兼容
    device_error = Signal(str, str)
    device_reconnecting = Signal(str, int)

    # ✅ 新增信号：异步轮询结果（带性能数据）
    async_poll_success = Signal(str, dict, float)     # device_id, data, response_time_ms
    async_poll_failed = Signal(str, str, str)        # device_id, error_type, error_msg
    async_poll_timeout = Signal(str, float)           # device_id, elapsed_ms
    batch_poll_completed = Signal(int)                # success_count

    def __init__(self, config_file: str = "config.json", db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self._config_file = config_file
        self._db_manager = db_manager or DatabaseManager()
        self._devices: Dict[str, DevicePollInfo] = {}

        self._write_lock = threading.Lock()

        self._async_worker = AsyncPollingWorker(
            parent=self,
            max_thread_count=4,
        )
        
        self._manually_disconnected: set = set()
        
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._schedule_async_polls)
        self._poll_interval = 100

        self._polling_groups: Dict[str, PollingGroup] = {"default": PollingGroup("default")}
        self._device_groups: Dict[str, str] = {}

        self._fault_recovery_mgr = FaultRecoveryManager(self._devices)
        self._group_mgr = DeviceGroupManager(self._device_groups, self._polling_groups, self._devices)
        self._lifecycle_mgr = DeviceLifecycleManager(self._devices, self._manually_disconnected)
        self._persistence_svc = DataPersistenceService(self._db_manager)
        self._config_svc = ConfigImporterExporter(self._db_manager, self._config_file)

        # v4.0 网关化: GatewayEngine + 网关模型
        self._gateway_engine = GatewayEngine(parent=self)
        self._gateway_models: Dict[str, GatewayModel] = {}
        self._gateway_json_path: Optional[str] = None

        self._load_devices()
        self._start_timers()
        
        self._async_worker.set_dependencies(
            devices=self._devices,
            persistence_svc=self._persistence_svc,
            fault_recovery_mgr=self._fault_recovery_mgr,
        )
        
        self._async_worker.device_data_updated.connect(self._on_async_poll_success)
        self._async_worker.device_poll_failed.connect(self._on_async_poll_failed)
        self._async_worker.device_poll_timeout.connect(self._on_async_poll_timeout)

        self._gateway_engine.gateway_data_updated.connect(self._on_gateway_data)
        self._gateway_engine.gateway_state_changed.connect(self._on_gateway_state_changed)
        self._gateway_engine.gateway_error.connect(self._on_gateway_error)

        logger.info("设备管理器 v4.0 初始化完成 (网关化模式 + 异步轮询)")

    def _start_timers(self):
        self._poll_timer.start(self._poll_interval)
        self._lifecycle_mgr.start()
        self._persistence_svc.start()

    def _load_devices(self):
        self._devices.clear()

        try:
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                devices = repo.get_all_with_registers()

                for device_model in devices:
                    config = repo.to_config(device_model)
                    logger.info(
                        "加载设备: %s, 端口: %s, 配置端口: %s",
                        device_model.name,
                        device_model.port,
                        config.get("port"),
                    )
                    self._create_device_internal(config["device_id"], config)

            logger.info("从数据库加载了 %d 个设备", len(devices))

        except Exception as e:
            logger.error("从数据库加载设备失败", error=str(e))

    def reload_devices(self):
        self._load_devices()
        logger.info("设备配置已重新加载")

    def _create_device_internal(self, device_id: str, config: dict) -> Device:
        # 使用兼容层 Device（QObject版本，带信号）
        # 而非 DeviceFactory.create_device() 返回的 dataclass（无信号）
        device = Device(device_id, config)  # 兼容层 QObject Device

        device.status_changed.connect(lambda s, d=device_id: self._on_device_status_changed(d, s))
        device.data_received.connect(lambda did, data, d=device_id: self._on_device_data_updated(d, data))
        device.error_occurred.connect(lambda error, d=device_id: self._on_device_error(d, error))

        priority = self._determine_priority(config)
        poll_info = DevicePollInfo(device, priority)
        poll_info.poll_interval = config.get("poll_interval", 1000)
        poll_info.auto_reconnect_enabled = config.get("auto_reconnect_enabled", False)

        group_name = config.get("group", "default")
        if group_name not in self._polling_groups:
            group_name = "default"
        self._device_groups[device_id] = group_name
        self._polling_groups[group_name].device_ids.add(device_id)

        self._devices[device_id] = poll_info
        return device

    def _determine_priority(self, config: dict) -> PollPriority:
        device_type = config.get("device_type", "").lower()

        high_priority_types = ["传感器", "变送器", "流量计", "压力计"]
        if any(t in device_type for t in high_priority_types):
            return PollPriority.HIGH

        low_priority_types = [" historian", "记录仪", "存档"]
        if any(t in device_type for t in low_priority_types):
            return PollPriority.LOW

        return PollPriority.NORMAL

    def add_device(self, device_config: Dict) -> str:
        if not device_config.get("device_id"):
            while True:
                device_id = str(uuid.uuid4())[:8]
                if device_id not in self._devices:
                    break
            device_config["device_id"] = device_id
        else:
            device_id = device_config["device_id"]
            if device_id in self._devices:
                logger.error("设备ID已存在", device_id=device_id)
                raise ValueError(f"设备ID已存在: {device_id}")

        is_valid, error_msg = Device.validate_config(device_config)
        if not is_valid:
            logger.error("设备配置验证失败", error=error_msg)
            raise ValueError(f"设备配置验证失败: {error_msg}")

        try:
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                repo.create_from_config(device_config)

            self._create_device_internal(device_id, device_config)

            logger.info("设备添加成功", device_id=device_id, name=device_config.get("name"))
            self.device_added.emit(device_id)
            return device_id

        except Exception as e:
            logger.error("添加设备失败", device_id=device_id, error=str(e))
            raise

    def remove_device(self, device_id: str) -> bool:
        """
        移除设备（生产级原子操作）

        ✅ v3.1 修复：使用写锁保护，防止与调度器迭代并发冲突
        """
        if device_id not in self._devices:
            return False

        # 使用写锁保护整个删除操作
        with self._write_lock:
            try:
                poll_info = self._devices[device_id]

                # 断开设备连接
                try:
                    poll_info.device.disconnect()
                except Exception as e:
                    logger.debug(
                        "断开设备连接时出错（清理阶段）: %s",
                        str(e),
                        device_id=device_id,
                    )

                # 从分组中移除
                self._group_mgr.remove_device(device_id)

                # 从数据库删除
                with self._db_manager.session() as session:
                    repo = DeviceRepository(session)
                    repo.delete_with_relations(device_id)

                # 从内存字典删除（★ 原子操作）
                del self._devices[device_id]

                logger.info("设备移除成功", device_id=device_id)
                self.device_removed.emit(device_id)
                return True

            except Exception as e:
                logger.error("移除设备失败", device_id=device_id, error=str(e), exc_info=True)
                return False

    def connect_device(self, device_id: str) -> tuple[bool, str, str]:
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
                driver = device.get_driver() if hasattr(device, 'get_driver') else None
                if driver and hasattr(driver, 'data_received'):
                    try:
                        driver.data_received.connect(
                            lambda data, did=device_id: DataBus.instance().device_raw_bytes_received.emit(did, data)
                        )
                    except Exception:
                        pass
                return True, "", ""
            else:
                if poll_info.auto_reconnect_enabled:
                    self._lifecycle_mgr.schedule_reconnect(device_id)

                connection_error = device.get_last_connection_error()
                error_msg = connection_error or "设备连接失败"

                error_type, error_msg = self._determine_error_type(error_msg)
                return False, error_type, error_msg

        except Exception as e:
            error_msg = str(e)
            error_type, error_msg = self._determine_error_type(error_msg)

            logger.error("连接设备异常", device_id=device_id, error=error_msg)
            if poll_info.auto_reconnect_enabled:
                self._lifecycle_mgr.schedule_reconnect(device_id)
            return False, error_type, error_msg

    def _determine_error_type(self, error_msg: str) -> tuple[str, str]:
        error_type = "connect_failed"
        msg_lower = error_msg.lower()

        if any(kw in msg_lower for kw in ["timeout", "timed out", "超时"]):
            error_type = "communication_timeout"
            if "tcp" in msg_lower or "socket" in msg_lower:
                prefix_key = "communication_timeout_tcp"
            elif "serial" in msg_lower or "com" in msg_lower:
                prefix_key = "communication_timeout_serial"
            else:
                prefix_key = "communication_timeout"
            error_msg = f"{ERROR_ENHANCE_PREFIXES[prefix_key]}: {error_msg}"
        elif any(kw in msg_lower for kw in ["connection refused", "connect failed", "拒绝连接", "连接失败"]):
            error_type = "connection_refused"
            error_msg = f"{ERROR_ENHANCE_PREFIXES['connection_refused']}: {error_msg}"
        elif any(kw in msg_lower for kw in ["invalid", "wrong", "无效"]):
            error_type = "invalid_response"
            error_msg = f"{ERROR_ENHANCE_PREFIXES['invalid_response']}: {error_msg}"
        elif any(kw in msg_lower for kw in ["offline", "disconnected", "离线", "断开"]):
            error_type = "device_offline"
            error_msg = f"{ERROR_ENHANCE_PREFIXES['device_offline']}: {error_msg}"
        elif any(kw in msg_lower for kw in ["protocol", "modbus", "协议"]):
            error_type = "protocol_error"
            error_msg = f"{ERROR_ENHANCE_PREFIXES['protocol_error']}: {error_msg}"
        elif any(kw in msg_lower for kw in ["port", "端口", "com"]):
            error_type = "port_error"
            error_msg = f"{ERROR_ENHANCE_PREFIXES['port_error']}: {error_msg}"
        elif any(kw in msg_lower for kw in ["host", "ip", "地址"]):
            error_type = "host_error"
            error_msg = f"{ERROR_ENHANCE_PREFIXES['host_error']}: {error_msg}"
        else:
            error_msg = f"{ERROR_ENHANCE_PREFIXES['connect_failed']}: {error_msg}"

        return error_type, error_msg

    def set_device_auto_reconnect(self, device_id: str, enabled: bool) -> bool:
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        poll_info = self._devices[device_id]
        poll_info.auto_reconnect_enabled = enabled
        logger.info("设置设备自动重连状态", device_id=device_id, enabled=enabled)
        return True

    def set_all_devices_auto_reconnect(self, enabled: bool) -> int:
        count = 0
        for device_id, poll_info in self._devices.items():
            poll_info.auto_reconnect_enabled = enabled
            count += 1
        logger.info("批量设置设备自动重连状态", count=count, enabled=enabled)
        return count

    def get_auto_reconnect_status(self) -> tuple[int, int]:
        enabled_count = 0
        disabled_count = 0
        for poll_info in self._devices.values():
            if poll_info.auto_reconnect_enabled:
                enabled_count += 1
            else:
                disabled_count += 1
        return enabled_count, disabled_count

    def disconnect_device(self, device_id: str):
        if device_id in self._devices:
            self._manually_disconnected.add(device_id)
            self._devices[device_id].device.disconnect()
            logger.info("设备断开连接", device_id=device_id)

    def edit_device(self, device_id: str, new_config: Dict) -> bool:
        """
        编辑设备配置（生产级Shadow Instance原子操作）

        ✅ v3.1 重构说明：
        使用阴影实例(Shadow Instance)策略保证原子性，解决以下问题：
        - ❌ 旧版：5步非原子操作，可能导致DB/内存不一致
        - ✅ 新版：要么全部成功，要么全部失败（无中间状态）

        Shadow Instance流程：
        ① 验证新配置（纯计算，无副作用）
        ② 原子性数据库更新（事务保护）
        ③ 创建新设备实例（阴影实例，不影响旧实例）
        ④ 原子性内存替换（写锁保护，调度器下次迭代自动看到新实例）
        ⑤ 断开并清理旧实例（GC回收）

        线程安全：
        - 使用 _write_lock 保护步骤④的内存替换操作
        - 调度器通过快照机制读取设备列表，不会访问到半成品状态
        - 即使在编辑期间有轮询任务执行，也只会操作旧的设备实例

        Args:
            device_id: 设备唯一标识符
            new_config: 新的设备配置字典

        Returns:
            bool: 是否编辑成功
        """
        # ===== 步骤0: 前置检查 =====
        if device_id not in self._devices:
            logger.error("编辑设备失败：设备不存在", device_id=device_id)
            return False

        # 标准化配置
        new_config["device_id"] = device_id

        # ===== 步骤1: 验证新配置（纯计算，无副作用）=====
        is_valid, error_msg = Device.validate_config(new_config)
        if not is_valid:
            logger.error("设备配置验证失败", device_id=device_id, error=error_msg)
            return False

        logger.info("开始编辑设备（Shadow Instance模式）", device_id=device_id)

        # 保存旧配置信息（用于错误日志）
        old_group = self._device_groups.get(device_id, "default")
        old_config_backup = None

        try:
            # ===== 步骤2: 原子性数据库更新（事务保护）=====
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)

                # 备份旧配置（用于诊断日志）
                try:
                    old_config_backup = repo.get_by_id(device_id)
                except Exception as e:
                    logger.warning("备份旧配置失败（非致命）: %s", str(e))

                # 更新数据库（事务内，失败自动回滚）
                repo.update_from_config(device_id, new_config)
                # session退出时自动commit

            logger.debug("数据库更新成功", device_id=device_id)

            # ===== 步骤3: 创建新的设备实例（阴影实例）=====
            # 此时旧实例仍在运行，新实例只是准备好的"影子"
            if "group" not in new_config:
                new_config["group"] = old_group

            # 创建新设备和PollInfo（使用兼容层 QObject Device）
            new_device = Device(device_id, new_config)  # 兼容层 QObject Device（带信号）
            new_priority = self._determine_priority(new_config)
            new_poll_info = DevicePollInfo(new_device, new_priority)
            new_poll_info.poll_interval = new_config.get("poll_interval", 1000)
            new_poll_info.auto_reconnect_enabled = new_config.get("auto_reconnect_enabled", False)

            # 绑定信号（与新实例关联）
            new_device.status_changed.connect(
                lambda s, d=device_id: self._on_device_status_changed(d, s)
            )
            new_device.data_received.connect(
                lambda did, data, d=device_id: self._on_device_data_updated(d, data)
            )
            new_device.error_occurred.connect(
                lambda error, d=device_id: self._on_device_error(d, error)
            )

            # 更新分组信息
            new_group_name = new_config.get("group", "default")
            if new_group_name not in self._polling_groups:
                new_group_name = "default"

            logger.debug("阴影实例创建成功", device_id=device_id)

            # ===== 步骤4: 原子性内存替换（★ 关键步骤 - 写锁保护）=====
            # 此步骤保证：
            # - 调度器不会看到半成品状态
            # - 要么完全替换成功，要么完全不变
            # - 替换后调度器下次迭代自动使用新实例
            with self._write_lock:
                # 获取旧的PollInfo
                old_poll_info = self._devices[device_id]

                # 断开旧设备连接（此时旧实例仍在字典中，但即将被替换）
                try:
                    old_poll_info.device.disconnect()
                    logger.debug("旧设备已断开", device_id=device_id)
                except Exception as e:
                    logger.warning(
                        "断开旧设备时出错（非致命，继续替换）: %s",
                        str(e),
                        device_id=device_id,
                    )

                # 从旧组中移除
                if old_group in self._polling_groups:
                    self._polling_groups[old_group].device_ids.discard(device_id)

                # ★ 原子替换：将新实例放入字典
                self._devices[device_id] = new_poll_info

                # 添加到新组
                self._device_groups[device_id] = new_group_name
                if new_group_name in self._polling_groups:
                    self._polling_groups[new_group_name].device_ids.add(device_id)

                # 此时替换完成！调度器下次迭代会自动看到新实例
                # 旧实例由Python GC回收（无引用后自动清理）

            # ===== 步骤5: 成功通知 =====
            logger.info(
                "设备编辑成功（Shadow Instance原子操作完成）",
                device_id=device_id,
                new_group=new_group_name,
            )
            self.device_added.emit(device_id)
            return True

        except Exception as e:
            # ===== 异常处理：回滚策略 =====
            logger.error(
                "设备编辑失败（正在执行回滚）",
                device_id=device_id,
                error=str(e),
                exc_info=True,
            )

            # 尝试回滚数据库（如果步骤2已执行）
            if old_config_backup is not None:
                try:
                    with self._db_manager.session() as session:
                        repo = DeviceRepository(session)
                        repo.update_from_config(device_id, old_config_backup)
                    logger.info("数据库已回滚到旧配置", device_id=device_id)
                except Exception as rollback_err:
                    logger.error(
                        "数据库回滚也失败（严重！需要手动检查）",
                        device_id=device_id,
                        error=str(rollback_err),
                        exc_info=True,
                    )

            # 注意：不需要回滚内存，因为步骤4在锁内失败时，
            # _devices[device_id]仍然是旧的实例，未受影响
            return False

    def _schedule_async_polls(self):
        """
        ✅ 异步轮询调度器（生产级线程安全版本）

        v3.1 重构说明：
        - 使用快照机制保护迭代安全（避免并发修改字典异常）
        - 在快照上迭代（即使原字典被UI线程修改也不影响）
        - 二次验证设备存在性（防止迭代到已删除的设备）

        此方法在主线程中快速执行（<1ms），仅负责任务筛选和提交。
        实际的阻塞式Modbus通信在工作线程池中并行执行。

        性能提升原理：
        - 旧版：顺序轮询7设备 = 7 × 20ms = 140ms（主线程阻塞）
        - 新版：提交7个任务到线程池 ≈ 0.5ms（主线程立即返回）
        - 线程池并行执行所有任务 < 50ms总耗时

        线程安全保障：
        - 快照机制：O(n)复制设备ID列表，n通常<50
        - 二次检查：每次访问前验证设备仍存在
        - 无锁设计：读操作不需要锁（写操作由_write_lock保护）
        """
        current_time = int(time.time() * 1000)
        devices_to_poll: list = []

        # ★ 关键改进1: 创建设备ID列表的快照
        # 原因：防止在迭代过程中UI线程修改self._devices字典
        # 性能：list()复制50个元素约0.01ms，可忽略不计
        try:
            devices_snapshot = list(self._devices.keys())
        except RuntimeError as e:
            # 极罕见：字典在复制时被修改，记录警告并跳过本次调度
            logger.warning(
                "创建设备快照时发生并发冲突（跳过本轮调度）",
                error=str(e),
            )
            return

        # 在快照上迭代（即使原字典被修改也不影响迭代器）
        for device_id in devices_snapshot:
            # ★ 关键改进2: 二次检查设备是否存在
            # 原因：快照创建后，设备可能已被UI线程删除
            if device_id not in self._devices:
                # 设备已被删除，跳过（正常情况）
                continue

            # 获取设备信息（此时设备保证存在）
            poll_info = self._devices.get(device_id)
            if not poll_info:
                continue

            # 快速筛选需要轮询的设备（主线程操作，无I/O）
            # 注意：这里读取poll_info是安全的，因为：
            # 1. 写操作（edit/remove）使用_write_lock保护
            # 2. 读操作（轮询调度）不需要锁（Python dict读是原子的）
            # 3. 即使读到旧的status也无害（下次迭代会纠正）
            try:
                if poll_info.device.get_status() != DeviceStatus.CONNECTED:
                    continue

                group_name = self._device_groups.get(device_id, "default")
                group = self._polling_groups.get(group_name, None)
                if not group or not group.enabled:
                    continue

                if not poll_info.should_poll(current_time):
                    continue

                devices_to_poll.append(device_id)

            except Exception as e:
                # 单个设备的筛选失败不影响其他设备
                logger.debug(
                    "设备筛选异常（跳过该设备）",
                    device_id=device_id,
                    error=str(e),
                )
                continue

        # 批量提交异步轮询任务（立即返回，不阻塞！）
        if devices_to_poll:
            submitted_count = self._async_worker.submit_batch_poll(devices_to_poll)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "异步轮询调度完成",
                    total_devices=len(devices_snapshot),
                    submitted_devices=submitted_count,
                    active_tasks=self._async_worker.active_task_count,
                )

    def _poll_all_devices(self):
        """
        ⚠️ 旧版同步轮询方法（已弃用，保留向后兼容）
        
        现在由 _schedule_async_polls() 替代此方法。
        如需强制同步模式，可手动调用（不推荐）。
        """
        self._schedule_async_polls()

    # ══════════════════════════════════════════════
    # 异步轮询结果处理槽函数（从工作线程接收Signal）
    # ══════════════════════════════════════════════
    
    def _on_async_poll_success(
        self,
        device_id: str,
        data: dict,
        response_time_ms: float,
    ) -> None:
        """处理异步轮询成功（工作线程→主线程自动排队）"""
        self.device_data_updated.emit(device_id, data)
        DataBus.instance().publish_device_data(device_id, data)
        self.async_poll_success.emit(device_id, data, response_time_ms)
    
    def _on_async_poll_failed(
        self,
        device_id: str,
        error_type: str,
        error_msg: str,
    ) -> None:
        """处理异步轮询失败"""
        self.device_error.emit(device_id, error_msg)
        self.async_poll_failed.emit(device_id, error_type, error_msg)
    
    def _on_async_poll_timeout(
        self,
        device_id: str,
        elapsed_ms: float,
    ) -> None:
        """处理异步轮询超时"""
        self.async_poll_timeout.emit(device_id, elapsed_ms)

    def _on_device_status_changed(self, device_id: str, status: int):
        if status == DeviceStatus.CONNECTED:
            self._manually_disconnected.discard(device_id)
            self.device_connected.emit(device_id)
            DataBus.instance().publish_device_connected(device_id)
        elif status == DeviceStatus.DISCONNECTED:
            self.device_disconnected.emit(device_id)
            DataBus.instance().publish_device_disconnected(device_id)
            if self._lifecycle_mgr.should_auto_reconnect(device_id):
                self._lifecycle_mgr.schedule_reconnect(device_id)
        elif status == DeviceStatus.ERROR:
            if self._lifecycle_mgr.should_auto_reconnect(device_id):
                self._lifecycle_mgr.schedule_reconnect(device_id)
            self.device_error.emit(device_id, "设备状态错误")
            DataBus.instance().publish_comm_error(device_id, "设备状态错误")

    def _on_device_data_updated(self, device_id: str, data: Dict):
        self.device_data_updated.emit(device_id, data)
        DataBus.instance().publish_device_data(device_id, data)

    def _on_device_error(self, device_id: str, error: str):
        logger.error("设备错误", device_id=device_id, error=error)
        self.device_error.emit(device_id, error)
        DataBus.instance().publish_comm_error(device_id, error)

    def get_device(self, device_id: str) -> Optional[Device]:
        if device_id in self._devices:
            return self._devices[device_id].device
        return None

    def get_all_devices(self) -> List[Dict]:
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
        return [
            poll_info.device
            for poll_info in self._devices.values()
            if poll_info.device.get_status() == DeviceStatus.CONNECTED
        ]

    def set_poll_interval(self, interval_ms: int):
        self._poll_interval = max(50, min(interval_ms, 1000))
        self._poll_timer.setInterval(self._poll_interval)

    # ------------------- 故障恢复控制方法 -------------------

    def enable_fault_detection(self, device_id: str, enabled: bool) -> bool:
        return self._fault_recovery_mgr.enable_fault_detection(device_id, enabled)

    def enable_auto_recovery(self, device_id: str, enabled: bool) -> bool:
        return self._fault_recovery_mgr.enable_auto_recovery(device_id, enabled)

    def set_recovery_mode(self, device_id: str, mode: str) -> bool:
        return self._fault_recovery_mgr.set_recovery_mode(device_id, mode)

    def set_max_recovery_attempts(self, device_id: str, max_attempts: int) -> bool:
        return self._fault_recovery_mgr.set_max_recovery_attempts(device_id, max_attempts)

    def get_fault_recovery_status(self, device_id: str) -> Dict:
        return self._fault_recovery_mgr.get_fault_recovery_status(device_id)

    def manual_recovery(self, device_id: str) -> bool:
        return self._fault_recovery_mgr.manual_recovery(device_id)

    def reset_fault(self, device_id: str) -> bool:
        return self._fault_recovery_mgr.reset_fault(device_id)

    # ------------------- 设备分组管理方法 -------------------

    def add_polling_group(
        self, name: str, priority: PollPriority = PollPriority.NORMAL, base_interval: int = 1000, enabled: bool = True
    ) -> bool:
        return self._group_mgr.add_polling_group(name, priority, base_interval, enabled)

    def remove_polling_group(self, name: str) -> bool:
        return self._group_mgr.remove_polling_group(name)

    def assign_device_to_group(self, device_id: str, group_name: str) -> bool:
        return self._group_mgr.assign_device_to_group(device_id, group_name)

    def get_group_devices(self, group_name: str) -> List[str]:
        return self._group_mgr.get_group_devices(group_name)

    def export_devices_config(self, file_path: str, device_ids: List[str] = None) -> bool:
        return self._config_svc.export_devices_config(device_ids, file_path)

    def import_devices_config(self, file_path: str, overwrite: bool = False) -> bool:
        return self._config_svc.import_devices_config(
            file_path, overwrite, self._create_device_internal, self._devices
        )

    def get_device_group(self, device_id: str) -> str:
        return self._group_mgr.get_group(device_id)

    def get_all_groups(self) -> List[Dict]:
        return self._group_mgr.get_all_groups_info()

    def enable_group(self, group_name: str, enabled: bool) -> bool:
        return self._group_mgr.enable_group(group_name, enabled)

    def get_polling_statistics(self) -> Dict:
        stats = {
            "total_devices": len(self._devices),
            "total_groups": len(self._polling_groups),
            "total_polls": sum(p.total_polls for p in self._devices.values()),
            "successful_polls": sum(p.successful_polls for p in self._devices.values()),
            "failed_polls": sum(p.failed_polls for p in self._devices.values()),
            "devices_by_group": {},
        }

        for group_name, group in self._polling_groups.items():
            stats["devices_by_group"][group_name] = {
                "device_count": len(group.device_ids),
                "enabled": group.enabled,
                "priority": group.priority.name,
            }

        return stats

    def cleanup(self):
        logger.info("设备管理器清理资源")

        try:
            self._poll_timer.stop()
        except RuntimeError:
            pass

        self._gateway_engine.shutdown()

        if hasattr(self, '_async_worker'):
            self._async_worker.shutdown(timeout_ms=3000)
            try:
                stats = self._async_worker.get_statistics()
                logger.info(
                    "异步轮询工作器已关闭: 成功=%d 失败=%d 平均耗时=%.1fms",
                    stats.get('success_count', 0) if isinstance(stats, dict) else 0,
                    stats.get('fail_count', 0) if isinstance(stats, dict) else 0,
                    stats.get('avg_response_time_ms', 0.0) if isinstance(stats, dict) else 0.0,
                )
            except (TypeError, AttributeError):
                logger.info("异步轮询工作器已关闭")

        self._lifecycle_mgr.stop()
        self._persistence_svc.flush()
        self._persistence_svc.stop()

        for poll_info in self._devices.values():
            try:
                poll_info.device.disconnect()
            except Exception as e:
                logger.debug("设备断开连接时出错（清理阶段）: %s", str(e))

        DataBus.instance().shutdown()

        self._db_manager = None
        logger.info("设备管理器资源已释放")

    # ══════════════════════════════════════════════
    # v4.0 网关化 API（规范控制点④）
    # ══════════════════════════════════════════════

    def load_gateways_from_json(self, json_path: str = "config/devices.json") -> int:
        """
        从 devices.json 加载网关配置（规范 Step 4）

        Args:
            json_path: JSON配置文件路径

        Returns:
            加载的网关数量
        """
        self._gateway_json_path = json_path

        if not os.path.exists(json_path):
            logger.warning("网关配置文件不存在: %s", json_path)
            return 0

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            gateways_data = config.get("gateways", [])
            loaded_count = 0

            for gw_data in gateways_data:
                try:
                    model = GatewayModel.from_dict(gw_data)
                    self._gateway_models[model.id] = model

                    gw_config = GatewayConfig.from_dict(gw_data)
                    self._gateway_engine.add_gateway(gw_config)

                    for var in model.variables:
                        if var.deadband > 0:
                            DataBus.instance().set_device_deadband(
                                model.id, var.name, var.deadband
                            )

                    loaded_count += 1
                    logger.info(
                        "网关已加载 [%s] %s (%s:%d) 变量=%d",
                        model.id, model.name, model.ip, model.port,
                        len(model.variables),
                    )
                except Exception as e:
                    logger.error("加载网关失败: %s, 错误: %s", gw_data.get("id", "?"), e)

            logger.info("从 %s 加载了 %d 个网关", json_path, loaded_count)
            return loaded_count

        except Exception as e:
            logger.error("加载网关配置失败: %s", e)
            return 0

    def connect_gateway(self, gateway_id: str) -> bool:
        """连接指定网关"""
        return self._gateway_engine.connect_gateway(gateway_id)

    def disconnect_gateway(self, gateway_id: str):
        """断开指定网关"""
        self._gateway_engine.disconnect_gateway(gateway_id)

    def start_all_gateways(self):
        """启动所有网关连接"""
        self._gateway_engine.start_all()

    def stop_all_gateways(self):
        """停止所有网关连接"""
        self._gateway_engine.stop_all()

    def add_gateway(self, gateway_config: dict) -> bool:
        """
        运行时动态添加网关（规范 Step 4 — 支持运行时动态增删）

        Args:
            gateway_config: 网关配置字典（符合 devices.json 格式）

        Returns:
            是否添加成功
        """
        try:
            model = GatewayModel.from_dict(gateway_config)
            gw_config = GatewayConfig.from_dict(gateway_config)

            if not self._gateway_engine.add_gateway(gw_config):
                return False

            self._gateway_models[model.id] = model

            for var in model.variables:
                if var.deadband > 0:
                    DataBus.instance().set_device_deadband(model.id, var.name, var.deadband)

            self._save_gateways_to_json()
            logger.info("网关已动态添加 [%s]", model.id)
            return True

        except Exception as e:
            logger.error("动态添加网关失败: %s", e)
            return False

    def remove_gateway(self, gateway_id: str) -> bool:
        """
        运行时动态移除网关

        Args:
            gateway_id: 网关ID

        Returns:
            是否移除成功
        """
        if gateway_id not in self._gateway_models:
            return False

        result = self._gateway_engine.remove_gateway(gateway_id)
        if result:
            del self._gateway_models[gateway_id]
            DataBus.instance()._deadband_filter.clear_device(gateway_id)
            self._save_gateways_to_json()
            logger.info("网关已动态移除 [%s]", gateway_id)

        return result

    def get_gateway_model(self, gateway_id: str) -> Optional[GatewayModel]:
        """获取网关数据模型"""
        return self._gateway_models.get(gateway_id)

    def get_all_gateway_models(self) -> Dict[str, GatewayModel]:
        """获取所有网关数据模型"""
        return dict(self._gateway_models)

    def get_gateway_ids(self) -> List[str]:
        """获取所有网关ID列表"""
        return self._gateway_engine.get_gateway_ids()

    def is_gateway_connected(self, gateway_id: str) -> bool:
        """检查网关是否已连接"""
        return self._gateway_engine.is_gateway_connected(gateway_id)

    def get_gateway_engine(self) -> GatewayEngine:
        """获取底层网关引擎（高级用途）"""
        return self._gateway_engine

    def _save_gateways_to_json(self):
        """将当前网关配置保存到JSON文件"""
        if not self._gateway_json_path:
            return

        try:
            config = {
                "version": "3.0",
                "gateways": [m.to_dict() for m in self._gateway_models.values()],
            }
            os.makedirs(os.path.dirname(self._gateway_json_path), exist_ok=True)
            with open(self._gateway_json_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.debug("网关配置已保存到 %s", self._gateway_json_path)
        except Exception as e:
            logger.error("保存网关配置失败: %s", e)

    def _on_gateway_data(self, gateway_id: str, data: dict):
        """网关数据更新回调"""
        DataBus.instance().publish_device_data(gateway_id, data)

    def _on_gateway_state_changed(self, gateway_id: str, state: int):
        """网关状态变更回调"""
        gw_state = GatewayState(state)
        model = self._gateway_models.get(gateway_id)
        if model:
            if gw_state == GatewayState.CONNECTED:
                model.status = GatewayStatus.CONNECTED
            elif gw_state == GatewayState.POLLING:
                model.status = GatewayStatus.POLLING
            elif gw_state == GatewayState.RECONNECTING:
                model.status = GatewayStatus.RECONNECTING
            elif gw_state == GatewayState.ERROR:
                model.status = GatewayStatus.ERROR
            elif gw_state == GatewayState.IDLE:
                model.status = GatewayStatus.IDLE

    def _on_gateway_error(self, gateway_id: str, error: str):
        """网关错误回调"""
        DataBus.instance().publish_comm_error(gateway_id, error)

    def __del__(self):
        try:
            self.cleanup()
        except (RuntimeError, AttributeError):
            pass
