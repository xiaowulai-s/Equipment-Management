# -*- coding: utf-8 -*-
"""
设备注册表 - 管理所有设备的CRUD操作
Device Registry - Manages device CRUD operations

职责（单一职责原则 SRP）：
- 设备的增删改查
- 设备状态跟踪
- 设备查找和过滤
- 信号发射：设备添加/移除/更新

不属于本类职责：
- 轮询调度 -> PollingScheduler
- 故障恢复 -> FaultRecoveryService
- 配置导入导出 -> ConfigurationService
- 连接管理 -> LifecycleManager
- 数据持久化 -> DataPersistenceService
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from core.data import DatabaseManager, DeviceRepository
from core.device.device_factory import DeviceFactory
from core.device.device_model import Device, DeviceStatus
from core.device.polling import DevicePollInfo, PollPriority
from core.utils.logger import get_logger

logger = get_logger("device_registry")


class DeviceRegistrySignals(QObject):
    """设备注册表信号定义（分离信号对象，支持多重继承）"""

    device_added = Signal(str)          # device_id
    device_removed = Signal(str)        # device_id
    device_updated = Signal(str)        # device_id


class DeviceRegistry:
    """
    设备注册表 - 核心设备管理组件

    设计要点：
    1. 所有设备存储在 _devices 字典中，key为device_id
    2. 使用线程安全的访问模式（Qt信号槽保证主线程操作）
    3. 数据库操作与内存操作分离，支持事务回滚
    4. 通过信号通知外部组件状态变更
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        create_device_internal_func: Optional[Any] = None,
    ):
        """
        初始化设备注册表

        Args:
            db_manager: 数据库管理器实例
            create_device_internal_func: 设备创建函数（用于内部设备构建）
        """
        self._db_manager = db_manager
        self._devices: Dict[str, DevicePollInfo] = {}
        self._signals = DeviceRegistryDevices()

        # 设备创建函数（可注入，便于测试和解耦）
        self._create_device_internal = (
            create_device_internal_func or self._default_create_device
        )

        # 加载已持久化的设备
        self._load_devices_from_db()

    # ══════════════════════════════════════════════
    # 属性访问
    # ══════════════════════════════════════════════

    @property
    def signals(self) -> DeviceRegistrySignals:
        """获取信号对象"""
        return self._signals

    @property
    def devices(self) -> Dict[str, DevicePollInfo]:
        """获取设备字典（只读副本引用）"""
        return self._devices

    @property
    def device_count(self) -> int:
        """获取设备数量"""
        return len(self._devices)

    # ══════════════════════════════════════════════
    # 公共API - 设备CRUD
    # ══════════════════════════════════════════════

    def add_device(self, device_config: Dict) -> str:
        """
        添加新设备

        流程：
        1. 验证配置有效性
        2. 生成或验证device_id
        3. 持久化到数据库
        4. 创建运行时设备对象
        5. 发射信号通知

        Args:
            device_config: 设备配置字典

        Returns:
            str: 新设备的device_id

        Raises:
            ValueError: 配置无效或ID重复
        """
        # 1. 验证/生成 device_id
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

        # 2. 验证配置
        is_valid, error_msg = Device.validate_config(device_config)
        if not is_valid:
            logger.error("设备配置验证失败", error=error_msg)
            raise ValueError(f"设备配置验证失败: {error_msg}")

        # 3. 持久化到数据库
        try:
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                repo.create_from_config(device_config)
        except Exception as e:
            logger.error("数据库写入失败", device_id=device_id, error=str(e))
            raise

        # 4. 创建运行时设备
        self._create_device_internal(device_id, device_config)

        logger.info(
            "设备添加成功",
            device_id=device_id,
            name=device_config.get("name"),
        )
        self._signals.device_added.emit(device_id)
        return device_id

    def remove_device(self, device_id: str) -> bool:
        """
        移除设备

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 是否成功移除
        """
        if device_id not in self._devices:
            logger.warning("设备不存在，无法移除", device_id=device_id)
            return False

        try:
            poll_info = self._devices[device_id]

            # 断开设备连接
            try:
                poll_info.device.disconnect()
            except Exception as e:
                logger.debug("断开连接时出错", device_id=device_id, error=str(e))

            # 从数据库删除
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                repo.delete_with_relations(device_id)

            # 从内存中移除
            del self._devices[device_id]

            logger.info("设备移除成功", device_id=device_id)
            self._signals.device_removed.emit(device_id)
            return True

        except Exception as e:
            logger.error("移除设备失败", device_id=device_id, error=str(e))
            return False

    def get_device(self, device_id: str) -> Optional[Device]:
        """
        获取设备对象

        Args:
            device_id: 设备唯一标识符

        Returns:
            Optional[Device]: 设备对象，不存在则返回None
        """
        if device_id in self._devices:
            return self._devices[device_id].device
        return None

    def get_all_devices(self) -> List[Dict]:
        """
        获取所有设备详细信息列表

        Returns:
            List[Dict]: 设备信息字典列表，包含配置、状态、统计等
        """
        result = []
        for device_id, poll_info in self._devices.items():
            device = poll_info.device
            config = device.get_device_config()
            result.append({
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
            })
        return result

    def get_connected_devices(self) -> List[Device]:
        """
        获取所有已连接的设备对象

        Returns:
            List[Device]: 已连接设备列表
        """
        return [
            poll_info.device
            for poll_info in self._devices.values()
            if poll_info.device.get_status() == DeviceStatus.CONNECTED
        ]

    def edit_device(self, device_id: str, new_config: Dict) -> bool:
        """
        编辑设备配置

        支持事务回滚：如果重建设备失败，自动恢复旧配置

        Args:
            device_id: 设备唯一标识符
            new_config: 新的设备配置

        Returns:
            bool: 是否编辑成功
        """
        if device_id not in self._devices:
            logger.warning("设备不存在，无法编辑", device_id=device_id)
            return False

        try:
            new_config["device_id"] = device_id

            # 验证新配置
            is_valid, error_msg = Device.validate_config(new_config)
            if not is_valid:
                logger.error("设备配置验证失败", error=error_msg)
                return False

            # 保存旧配置（用于回滚）
            old_config = None
            poll_info = self._devices[device_id]

            # 断开当前设备
            poll_info.device.disconnect()

            # 更新数据库（带回滚）
            try:
                with self._db_manager.session() as session:
                    repo = DeviceRepository(session)
                    old_config = repo.get_by_id(device_id)
                    repo.update_from_config(device_id, new_config)
            except Exception:
                # 数据库更新失败，回滚
                if old_config:
                    try:
                        with self._db_manager.session() as session:
                            repo = DeviceRepository(session)
                            repo.update_from_config(device_id, old_config)
                        logger.warning("数据库更新失败，已回滚设备配置")
                    except Exception:
                        logger.error("回滚设备配置也失败")
                poll_info.device.connect()
                raise

            # 重建设备对象
            try:
                self._create_device_internal(device_id, new_config)
            except Exception:
                logger.warning("重建设备失败，尝试恢复旧配置", device_id=device_id)
                if old_config:
                    try:
                        self._create_device_internal(device_id, old_config)
                    except Exception as e:
                        logger.error("恢复旧配置也失败: %s", str(e), device_id=device_id, exc_info=True)
                raise

            logger.info("设备更新成功", device_id=device_id)
            self._signals.device_updated.emit(device_id)
            return True

        except Exception as e:
            logger.error("更新设备失败", device_id=device_id, error=str(e))
            return False

    def device_exists(self, device_id: str) -> bool:
        """检查设备是否存在"""
        return device_id in self._devices

    def get_device_count(self) -> int:
        """获取设备总数"""
        return len(self._devices)

    # ══════════════════════════════════════════════
    # 内部方法
    # ══════════════════════════════════════════════

    def _default_create_device(self, device_id: str, config: dict) -> Device:
        """
        默认设备创建方法

        Args:
            device_id: 设备ID
            config: 设备配置

        Returns:
            Device: 创建的设备对象
        """
        device = DeviceFactory.create_device(device_id, config)

        # 连接设备信号
        device.status_changed.connect(
            lambda s, d=device_id: self._on_device_status_changed(d, s)
        )
        device.data_received.connect(
            lambda did, data, d=device_id: self._on_device_data_updated(d, data)
        )
        device.error_occurred.connect(
            lambda error, d=device_id: self._on_device_error(d, error)
        )

        # 确定优先级
        priority = self._determine_priority(config)
        poll_info = DevicePollInfo(device, priority)
        poll_info.poll_interval = config.get("poll_interval", 1000)
        poll_info.auto_reconnect_enabled = config.get("auto_reconnect_enabled", False)

        self._devices[device_id] = poll_info
        return device

    def _determine_priority(self, config: dict) -> PollPriority:
        """根据设备类型确定轮询优先级"""
        device_type = config.get("device_type", "").lower()

        high_priority_types = ["传感器", "变送器", "流量计", "压力计"]
        if any(t in device_type for t in high_priority_types):
            return PollPriority.HIGH

        low_priority_types = ["historian", "记录仪", "存档"]
        if any(t in device_type for t in low_priority_types):
            return PollPriority.LOW

        return PollPriority.NORMAL

    def _load_devices_from_db(self):
        """从数据库加载已持久化的设备"""
        self._devices.clear()

        try:
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)
                devices = repo.get_all_with_registers()

                for device_model in devices:
                    config = repo.to_config(device_model)
                    logger.info(
                        "加载设备: %s, 端口: %s",
                        device_model.name,
                        device_model.port,
                    )
                    self._default_create_device(config["device_id"], config)

            logger.info("从数据库加载了 %d 个设备", len(devices))

        except Exception as e:
            logger.error("从数据库加载设备失败", error=str(e))

    def reload_devices(self):
        """重新从数据库加载设备"""
        self._load_devices_from_db()
        logger.info("设备配置已重新加载")

    # ══════════════════════════════════════════════
    # 设备事件处理（内部回调）
    # ══════════════════════════════════════════════

    def _on_device_status_changed(self, device_id: str, status: int):
        """设备状态变更回调（由外部LifecycleManager订阅）"""
        # 此方法仅作为日志记录点，实际逻辑由LifecycleManager处理
        logger.debug("设备状态变更", device_id=device_id, status=status)

    def _on_device_data_updated(self, device_id: str, data: Dict):
        """设备数据更新回调"""
        logger.debug("设备数据更新", device_id=device_id, params=list(data.keys()))

    def _on_device_error(self, device_id: str, error: str):
        """设备错误回调"""
        logger.error("设备错误", device_id=device_id, error=error)

    # ══════════════════════════════════════════════
    # 清理
    # ══════════════════════════════════════════════

    def cleanup(self):
        """清理资源，断开所有设备连接"""
        for poll_info in self._devices.values():
            try:
                poll_info.device.disconnect()
            except Exception as e:
                logger.debug("设备断开连接时出错（清理阶段）: %s", str(e))

        self._devices.clear()
        logger.info("设备注册表资源已释放")


# 向后兼容别名：允许外部代码通过此名访问信号
class DeviceRegistryDevices(QObject):
    """设备注册表信号集合（向后兼容）"""

    device_added = Signal(str)
    device_removed = Signal(str)
    device_updated = Signal(str)
