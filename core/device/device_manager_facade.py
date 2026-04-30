# -*- coding: utf-8 -*-
"""
设备管理器外观 - 统一入口（向后兼容）
Device Manager Facade - Unified Entry Point (Backward Compatible)

设计模式：外观模式（Facade Pattern）

职责：
- 组合所有内部模块（DeviceRegistry, PollingScheduler, FaultRecoveryService, ConfigurationService）
- 提供与原 DeviceManager 完全一致的公共API
- 统一信号出口（所有内部信号汇聚到此）
- 协调各模块间的交互逻辑

设计原则保证：
- 向后兼容：main_window.py 等外部代码无需任何修改
- 低耦合：外部只依赖此 Facade，不直接依赖内部模块
- 可测试：可以替换任意内部模块进行单元测试
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from core.constants import ERROR_ENHANCE_PREFIXES
from core.data import DatabaseManager
from core.device.configuration_service import ConfigurationService
from core.device.data_persistence_service import DataPersistenceService
from core.device.device_group_manager import DeviceGroupManager
from core.device.device_lifecycle_manager import DeviceLifecycleManager
from core.device.device_registry import DeviceRegistry
from core.device.fault_recovery_service import FaultRecoveryService
from core.device.polling import PollPriority, PollingGroup
from core.device.polling_scheduler import PollingScheduler
from core.utils.logger import get_logger

logger = get_logger("device_manager_facade")


class DeviceManagerFacade(QObject):
    """
    设备管理器外观 - v4.0 重构版

    架构改进：
    - 原版（v3.0）：657行上帝对象，7大职责耦合在一起
    - 新版（v4.0）：~250行协调器，职责委托给5个独立模块

    公共API（100% 向后兼容）：
    - 所有原方法签名保持不变
    - 所有原信号名称保持不变
    - 外部代码无需修改即可使用

    内部模块组合：
    ┌─────────────────────────────────────────────┐
    │           DeviceManagerFacade               │
    │  (统一入口 / 信号转发 / 模块协调)            │
    ├────────┬────────┬──────────┬───────────────┤
    │ Device │Polling│ Fault   │Configuration  │
    │ Registry│Scheduler│ Recovery │ Service       │
    │        │        │ Service  │               │
    └────────┴────────┴──────────┴───────────────┘
            │         │          │
    ┌───────┴─────────┴──────────┴───────────────┐
    │     LifecycleManager (连接/断开/重连)        │
    │     GroupManager (分组管理)                  │
    │     DataPersistenceService (数据持久化)      │
    └─────────────────────────────────────────────┘
    """

    # ══════════════════════════════════════════════
    # 信号定义（与原 DeviceManager 完全一致）
    # ══════════════════════════════════════════════

    # 基础设备信号
    device_added = Signal(str)
    device_removed = Signal(str)
    device_connected = Signal(str)
    device_disconnected = Signal(str)

    # 数据信号
    device_data_updated = Signal(str, dict)             # 向后兼容
    device_error = Signal(str, str)
    device_reconnecting = Signal(str, int)

    # 异步轮询信号（v3.0新增，保持不变）
    async_poll_success = Signal(str, dict, float)       # device_id, data, response_time_ms
    async_poll_failed = Signal(str, str, str)          # device_id, error_type, error_msg
    async_poll_timeout = Signal(str, float)            # device_id, elapsed_ms
    batch_poll_completed = Signal(int)                 # success_count

    def __init__(
        self,
        config_file: str = "config.json",
        db_manager: Optional[DatabaseManager] = None,
        parent=None,
    ):
        """
        初始化设备管理器外观

        Args:
            config_file: 配置文件路径
            db_manager: 数据库管理器实例
            parent: Qt父对象
        """
        super().__init__(parent)

        self._config_file = config_file
        self._db_manager = db_manager or DatabaseManager()

        # 共享状态字典（各模块共享引用）
        self._devices: Dict[str, Any] = {}
        self._device_groups: Dict[str, str] = {}
        self._polling_groups: Dict[str, PollingGroup] = {
            "default": PollingGroup("default")
        }
        self._manually_disconnected: set = set()

        # ════════════════════════════════════════
        # 阶段1: 创建核心服务模块
        # ════════════════════════════════════════

        # 1.1 设备注册表（CRUD + 状态管理）
        self._registry = DeviceRegistry(
            db_manager=self._db_manager,
        )
        # 同步共享状态引用
        self._devices = self._registry.devices

        # 1.2 数据持久化服务
        self._persistence_svc = DataPersistenceService(self._db_manager)

        # 1.3 故障恢复服务
        self._fault_svc = FaultRecoveryService(devices=self._devices)

        # 1.4 配置服务
        self._config_svc = ConfigurationService(
            db_manager=self._db_manager,
            config_file=self._config_file,
        )

        # 1.5 轮询调度器
        self._scheduler = PollingScheduler(
            devices=self._devices,
            device_groups=self._device_groups,
            polling_groups=self._polling_groups,
            persistence_svc=self._persistence_svc,
            fault_recovery_mgr=self._fault_svc,
        )

        # 1.6 分组管理器
        self._group_mgr = DeviceGroupManager(
            device_groups=self._device_groups,
            polling_groups=self._polling_groups,
            devices=self._devices,
        )

        # 1.7 生命周期管理器
        self._lifecycle_mgr = DeviceLifecycleManager(
            devices=self._devices,
            manually_disconnected=self._manually_disconnected,
        )

        # ════════════════════════════════════════
        # 阶段2: 连接内部信号
        # ════════════════════════════════════════

        self._connect_internal_signals()

        # ════════════════════════════════════════
        # 阶段3: 启动服务
        # ════════════════════════════════════════

        self._start_services()

        logger.info("设备管理器 v4.0 初始化完成 (模块化架构)")

    # ══════════════════════════════════════════════
    # 内部信号连接
    # ══════════════════════════════════════════════

    def _connect_internal_signals(self):
        """连接内部模块信号到 Facade 的统一出口"""

        # DeviceRegistry 信号 -> 转发到 Facade 信号
        self._registry.signals.device_added.connect(self.device_added)
        self._registry.signals.device_removed.connect(self.device_removed)
        self._registry.signals.device_updated.connect(self.device_added)  # 编辑=添加(兼容)

        # PollingScheduler 信号 -> 转发到 Facade 信号
        self._scheduler.signals.poll_success.connect(self._on_async_poll_success)
        self._scheduler.signals.poll_failed.connect(self._on_async_poll_failed)
        self._scheduler.signals.poll_timeout.connect(self._on_async_poll_timeout)

        # 连接设备的内部信号（用于状态跟踪和自动重连）
        for device_id, poll_info in self._devices.items():
            self._connect_device_signals(device_id, poll_info.device)

    def _connect_device_signals(self, device_id: str, device):
        """连接单个设备的信号"""
        device.status_changed.connect(
            lambda s, d=device_id: self._on_device_status_changed(d, s)
        )
        device.data_received.connect(
            lambda did, data, d=device_id: self._on_device_data_updated(d, data)
        )
        device.error_occurred.connect(
            lambda error, d=device_id: self._on_device_error(d, error)
        )

    def _start_services(self):
        """启动所有后台服务"""
        self._scheduler.start()
        self._lifecycle_mgr.start()
        self._persistence_svc.start()

    # ══════════════════════════════════════════════
    # 公共API - 设备CRUD（委托给 DeviceRegistry）
    # ══════════════════════════════════════════════

    def add_device(self, device_config: Dict) -> str:
        """添加设备（委托给 DeviceRegistry）"""
        result = self._registry.add_device(device_config)

        # 新设备需要连接信号
        if result in self._devices:
            self._connect_device_signals(result, self._devices[result].device)

        return result

    def remove_device(self, device_id: str) -> bool:
        """移除设备（委托给 DeviceRegistry + GroupManager）"""
        self._group_mgr.remove_device(device_id)
        return self._registry.remove_device(device_id)

    def get_device(self, device_id: str) -> Optional[Any]:
        """获取设备对象（委托给 DeviceRegistry）"""
        return self._registry.get_device(device_id)

    def get_all_devices(self) -> List[Dict]:
        """获取所有设备信息（委托给 DeviceRegistry）"""
        return self._registry.get_all_devices()

    def get_connected_devices(self) -> List[Any]:
        """获取已连接设备列表（委托给 DeviceRegistry）"""
        return self._registry.get_connected_devices()

    def edit_device(self, device_id: str, new_config: Dict) -> bool:
        """编辑设备配置（委托给 DeviceRegistry）"""
        return self._registry.edit_device(device_id, new_config)

    def reload_devices(self):
        """重新加载设备（委托给 DeviceRegistry）"""
        self._registry.reload_devices()

    # ══════════════════════════════════════════════
    # 公共API - 连接管理（委托给 LifecycleManager）
    # ══════════════════════════════════════════════

    def connect_device(self, device_id: str) -> Tuple[bool, str, str]:
        """
        连接设备

        流程：
        1. 检查设备是否存在
        2. 尝试连接
        3. 处理成功/失败
        4. 根据配置决定是否触发重连

        Returns:
            Tuple[bool, str, str]: (是否成功, 错误类型, 错误消息)
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
                return True, "", ""
            else:
                # 连接失败处理
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

    def disconnect_device(self, device_id: str):
        """断开设备连接"""
        if device_id in self._devices:
            self._manually_disconnected.add(device_id)
            self._devices[device_id].device.disconnect()
            logger.info("设备断开连接", device_id=device_id)

    def _determine_error_type(self, error_msg: str) -> Tuple[str, str]:
        """确定错误类型并增强错误消息"""
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

    # ══════════════════════════════════════════════
    # 公共API - 轮询控制（委托给 PollingScheduler）
    # ══════════════════════════════════════════════

    def set_poll_interval(self, interval_ms: int):
        """设置轮询间隔（委托给 PollingScheduler）"""
        self._scheduler.set_interval(interval_ms)

    # ══════════════════════════════════════════════
    # 公共API - 故障恢复（委托给 FaultRecoveryService）
    # ══════════════════════════════════════════════

    def enable_fault_detection(self, device_id: str, enabled: bool) -> bool:
        return self._fault_svc.enable_fault_detection(device_id, enabled)

    def enable_auto_recovery(self, device_id: str, enabled: bool) -> bool:
        return self._fault_svc.enable_auto_recovery(device_id, enabled)

    def set_recovery_mode(self, device_id: str, mode: str) -> bool:
        return self._fault_svc.set_recovery_mode(device_id, mode)

    def set_max_recovery_attempts(self, device_id: str, max_attempts: int) -> bool:
        return self._fault_svc.set_max_recovery_attempts(device_id, max_attempts)

    def get_fault_recovery_status(self, device_id: str) -> Dict:
        return self._fault_svc.get_fault_recovery_status(device_id)

    def manual_recovery(self, device_id: str) -> bool:
        return self._fault_svc.manual_recovery(device_id)

    def reset_fault(self, device_id: str) -> bool:
        return self._fault_svc.reset_fault(device_id)

    # ══════════════════════════════════════════════
    # 公共API - 自动重连控制
    # ══════════════════════════════════════════════

    def set_device_auto_reconnect(self, device_id: str, enabled: bool) -> bool:
        """设置单个设备的自动重连"""
        if device_id not in self._devices:
            logger.error("设备不存在", device_id=device_id)
            return False

        self._devices[device_id].auto_reconnect_enabled = enabled
        logger.info("设置设备自动重连状态", device_id=device_id, enabled=enabled)
        return True

    def set_all_devices_auto_reconnect(self, enabled: bool) -> int:
        """批量设置所有设备的自动重连"""
        count = 0
        for device_id, poll_info in self._devices.items():
            poll_info.auto_reconnect_enabled = enabled
            count += 1
        logger.info("批量设置设备自动重连状态", count=count, enabled=enabled)
        return count

    def get_auto_reconnect_status(self) -> Tuple[int, int]:
        """获取自动重连统计"""
        enabled_count = 0
        disabled_count = 0
        for poll_info in self._devices.values():
            if poll_info.auto_reconnect_enabled:
                enabled_count += 1
            else:
                disabled_count += 1
        return enabled_count, disabled_count

    # ══════════════════════════════════════════════
    # 公共API - 分组管理（委托给 GroupManager）
    # ══════════════════════════════════════════════

    def add_polling_group(
        self, name: str, priority: PollPriority = PollPriority.NORMAL,
        base_interval: int = 1000, enabled: bool = True,
    ) -> bool:
        return self._group_mgr.add_polling_group(name, priority, base_interval, enabled)

    def remove_polling_group(self, name: str) -> bool:
        return self._group_mgr.remove_polling_group(name)

    def assign_device_to_group(self, device_id: str, group_name: str) -> bool:
        return self._group_mgr.assign_device_to_group(device_id, group_name)

    def get_group_devices(self, group_name: str) -> List[str]:
        return self._group_mgr.get_group_devices(group_name)

    def get_device_group(self, device_id: str) -> str:
        return self._group_mgr.get_group(device_id)

    def get_all_groups(self) -> List[Dict]:
        return self._group_mgr.get_all_groups_info()

    def enable_group(self, group_name: str, enabled: bool) -> bool:
        return self._group_mgr.enable_group(group_name, enabled)

    # ══════════════════════════════════════════════
    # 公共API - 配置管理（委托给 ConfigurationService）
    # ══════════════════════════════════════════════

    def export_devices_config(self, file_path: str, device_ids: List[str] = None) -> bool:
        """导出设备配置（向后兼容接口）"""
        return self._config_svc.export_devices_config(device_ids, file_path)

    def import_devices_config(self, file_path: str, overwrite: bool = False) -> bool:
        """导入设备配置（向后兼容接口）"""
        return self._config_svc.import_devices_config(
            file_path,
            overwrite,
            self._create_device_for_import,
            self._devices,
        )

    def _create_device_for_import(self, device_id: str, config: dict):
        """导入时创建设备的回调函数"""
        from core.device.device_factory import DeviceFactory
        from core.device.polling import DevicePollInfo, PollPriority

        device = DeviceFactory.create_device(device_id, config)

        # 连接信号
        device.status_changed.connect(lambda s, d=device_id: self._on_device_status_changed(d, s))
        device.data_received.connect(lambda did, data, d=device_id: self._on_device_data_updated(d, data))
        device.error_occurred.connect(lambda error, d=device_id: self._on_device_error(d, error))

        priority = self._determine_priority_for_import(config)
        poll_info = DevicePollInfo(device, priority)
        poll_info.poll_interval = config.get("poll_interval", 1000)
        poll_info.auto_reconnect_enabled = config.get("auto_reconnect_enabled", False)

        group_name = config.get("group", "default")
        if group_name not in self._polling_groups:
            group_name = "default"
        self._device_groups[device_id] = group_name
        self._polling_groups[group_name].device_ids.add(device_id)

        self._devices[device_id] = poll_info

    def _determine_priority_for_import(self, config: dict) -> PollPriority:
        """导入时确定优先级"""
        device_type = config.get("device_type", "").lower()
        high_priority_types = ["传感器", "变送器", "流量计", "压力计"]
        if any(t in device_type for t in high_priority_types):
            return PollPriority.HIGH
        low_priority_types = ["historian", "记录仪", "存档"]
        if any(t in device_type for t in low_priority_types):
            return PollPriority.LOW
        return PollPriority.NORMAL

    # ══════════════════════════════════════════════
    # 公共API - 统计信息
    # ══════════════════════════════════════════════

    def get_polling_statistics(self) -> Dict:
        """获取轮询统计信息（聚合多源数据）"""
        scheduler_stats = self._scheduler.get_statistics()
        fault_stats = self._fault_svc.get_global_statistics()

        return {
            **scheduler_stats["aggregated"],
            **{
                "total_groups": scheduler_stats["scheduler"]["total_groups"],
                "devices_by_group": scheduler_stats["devices_by_group"],
            },
            **{
                "fault_stats": fault_stats,
            },
        }

    # ══════════════════════════════════════════════
    # 内部事件处理
    # ══════════════════════════════════════════════

    def _on_device_status_changed(self, device_id: str, status: int):
        """设备状态变更处理"""
        from core.device.device_model import DeviceStatus

        if status == DeviceStatus.CONNECTED:
            self._manually_disconnected.discard(device_id)
            self.device_connected.emit(device_id)
        elif status == DeviceStatus.DISCONNECTED:
            self.device_disconnected.emit(device_id)
            if self._lifecycle_mgr.should_auto_reconnect(device_id):
                self._lifecycle_mgr.schedule_reconnect(device_id)
        elif status == DeviceStatus.ERROR:
            if self._lifecycle_mgr.should_auto_reconnect(device_id):
                self._lifecycle_mgr.schedule_reconnect(device_id)
            self.device_error.emit(device_id, "设备状态错误")

    def _on_device_data_updated(self, device_id: str, data: Dict):
        """设备数据更新处理"""
        self.device_data_updated.emit(device_id, data)

    def _on_device_error(self, device_id: str, error: str):
        """设备错误处理"""
        logger.error("设备错误", device_id=device_id, error=error)
        self.device_error.emit(device_id, error)

    def _on_async_poll_success(self, device_id: str, data: dict, response_time_ms: float):
        """异步轮询成功处理"""
        self.device_data_updated.emit(device_id, data)
        self.async_poll_success.emit(device_id, data, response_time_ms)

    def _on_async_poll_failed(self, device_id: str, error_type: str, error_msg: str):
        """异步轮询失败处理"""
        self.device_error.emit(device_id, error_msg)
        self.async_poll_failed.emit(device_id, error_type, error_msg)

    def _on_async_poll_timeout(self, device_id: str, elapsed_ms: float):
        """异步轮询超时处理"""
        self.async_poll_timeout.emit(device_id, elapsed_ms)

    # ══════════════════════════════════════════════
    # 资源清理
    # ══════════════════════════════════════════════

    def cleanup(self):
        """
        清理所有资源

        清理顺序很重要：
        1. 停止调度器（不再提交新任务）
        2. 关闭工作器（等待进行中的任务完成）
        3. 停止生命周期管理器
        4. 刷新持久化缓冲区
        5. 断开所有设备连接
        """
        logger.info("设备管理器清理资源")

        # 1. 停止调度器
        self._scheduler.stop()

        # 2. 关闭工作器
        self._scheduler.cleanup(timeout_ms=3000)

        # 3. 停止生命周期管理器
        self._lifecycle_mgr.stop()

        # 4. 刷新持久化缓冲区
        self._persistence_svc.flush()
        self._persistence_svc.stop()

        # 5. 断开所有设备
        self._registry.cleanup()

        self._db_manager = None
        logger.info("设备管理器资源已释放")

    def __del__(self):
        try:
            self.cleanup()
        except (RuntimeError, AttributeError):
            pass


# ══════════════════════════════════════════════
# 向后兼容别名
# ══════════════════════════════════════════════

# 允许外部代码继续使用 DeviceManager 名称
DeviceManager = DeviceManagerFacade
