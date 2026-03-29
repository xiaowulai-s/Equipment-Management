"""
设备管理器

设计原则:
    1. 继承QObject, 全面支持Qt信号槽
    2. 管理所有Device实例的CRUD生命周期
    3. 自动聚合/转发Device的信号 (状态/值/报警)
    4. 支持按名称/ID/标签/协议类型等多维度搜索
    5. 支持批量操作 (导入/导出/启停/状态查询)
    6. 线程安全: QMutex保护设备字典
    7. 支持JSON持久化 (save/load)
    8. 设备ID冲突检测 + 名称唯一性约束

信号体系:
    device_added(Device)          → 设备添加
    device_removed(str)           → 设备移除 (device_id)
    device_updated(str)           → 设备配置更新 (device_id)
    device_status_changed(str, DeviceStatus) → 设备状态变更 (device_id, status)
    device_value_changed(str, str, int, float) → 寄存器值变更 (dev_id, reg_name, raw, eng)
    device_alarm_triggered(str, str, float, str) → 设备报警 (dev_id, reg_name, value, level)
    device_alarm_cleared(str, str, str) → 报警清除 (dev_id, reg_name, level)
    error_occurred(str)           → 全局错误通知
    device_count_changed(int)     → 设备总数变化
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Optional

from PySide6.QtCore import QMutex, QMutexLocker, QObject, Signal

from src.device.device import Device
from src.device.register import Register
from src.protocols.enums import DeviceStatus, ProtocolType
from src.utils.exceptions import DeviceConfigError, DeviceDuplicateError, DeviceError, DeviceNotFoundError

logger = logging.getLogger(__name__)


class DeviceManager(QObject):
    """设备管理器

    集中管理所有设备的生命周期: 添加/移除/更新/查询。
    自动转发设备状态/值/报警信号, 提供搜索和批量操作能力。

    Attributes:
        parent: QObject父对象
    """

    # ── 信号 ──────────────────────────────────────────────────
    device_added = Signal(object)  # Device
    device_removed = Signal(str)  # device_id
    device_updated = Signal(str)  # device_id
    device_status_changed = Signal(str, object)  # device_id, DeviceStatus
    device_value_changed = Signal(str, str, int, float)  # dev_id, reg_name, raw, eng
    device_alarm_triggered = Signal(str, str, float, str)  # dev_id, reg_name, value, level
    device_alarm_cleared = Signal(str, str, str)  # dev_id, reg_name, level
    error_occurred = Signal(str)  # error_message
    device_count_changed = Signal(int)  # count

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._devices: dict[str, Device] = {}  # device_id → Device
        self._name_index: dict[str, str] = {}  # name → device_id (名称索引)
        self._mutex = QMutex()

    # ═══════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════

    @property
    def device_count(self) -> int:
        return len(self._devices)

    @property
    def device_ids(self) -> list[str]:
        """所有设备ID列表"""
        return list(self._devices.keys())

    @property
    def device_names(self) -> list[str]:
        """所有设备名称列表"""
        return list(self._name_index.keys())

    @property
    def devices(self) -> dict[str, Device]:
        """设备字典 (只读副本)"""
        return dict(self._devices)

    # ═══════════════════════════════════════════════════════════
    # CRUD 操作
    # ═══════════════════════════════════════════════════════════

    def add_device(self, device: Device) -> None:
        """添加设备

        Args:
            device: Device实例

        Raises:
            DeviceDuplicateError: 设备ID或名称已存在
            DeviceConfigError: 设备配置无效
        """
        locker = QMutexLocker(self._mutex)

        # 校验
        if not device.name:
            raise DeviceConfigError("设备名称不能为空")

        if device.id in self._devices:
            raise DeviceDuplicateError(
                f"设备ID已存在: {device.id}",
                device_id=device.id,
            )

        if device.name in self._name_index:
            raise DeviceDuplicateError(
                f"设备名称已存在: {device.name}",
                device_id=device.id,
            )

        # 注册设备
        device.setParent(self)
        self._devices[device.id] = device
        self._name_index[device.name] = device.id

        # 连接信号
        self._connect_device_signals(device)

        # 发射信号
        self.device_added.emit(device)
        self.device_count_changed.emit(len(self._devices))

        logger.info(f"添加设备: {device.name} (ID: {device.id}, " f"协议: {device.protocol_type.value})")

    def remove_device(self, device_id: str) -> Device:
        """移除设备

        Args:
            device_id: 设备唯一标识

        Returns:
            被移除的Device实例

        Raises:
            DeviceNotFoundError: 设备不存在
        """
        locker = QMutexLocker(self._mutex)

        if device_id not in self._devices:
            raise DeviceNotFoundError(
                f"设备不存在: {device_id}",
                device_id=device_id,
            )

        device = self._devices.pop(device_id)

        # 断开信号
        self._disconnect_device_signals(device)

        # 清理名称索引
        if device.name in self._name_index:
            del self._name_index[device.name]

        device.setParent(None)

        # 发射信号
        self.device_removed.emit(device_id)
        self.device_count_changed.emit(len(self._devices))

        logger.info(f"移除设备: {device.name} (ID: {device_id})")
        return device

    def update_device(self, device_id: str, **kwargs: Any) -> None:
        """更新设备属性

        Args:
            device_id: 设备ID
            **kwargs: 要更新的属性 (name, description, tags, slave_id, ...)

        Raises:
            DeviceNotFoundError: 设备不存在
            DeviceDuplicateError: 新名称与其他设备冲突
            DeviceConfigError: 配置值无效
        """
        locker = QMutexLocker(self._mutex)

        if device_id not in self._devices:
            raise DeviceNotFoundError(
                f"设备不存在: {device_id}",
                device_id=device_id,
            )

        device = self._devices[device_id]

        # 如果修改名称, 检查唯一性
        new_name = kwargs.get("name")
        if new_name and new_name != device.name:
            if new_name in self._name_index:
                raise DeviceDuplicateError(
                    f"设备名称已存在: {new_name}",
                    device_id=device_id,
                )

        # 应用更新
        old_name = device.name
        for key, value in kwargs.items():
            if hasattr(device, key):
                try:
                    setattr(device, key, value)
                except (ValueError, TypeError) as e:
                    raise DeviceConfigError(
                        f"无效的{key}值: {e}",
                        field=key,
                    ) from e
            else:
                logger.warning(f"设备无属性: {key}")

        # 更新名称索引
        if new_name and new_name != old_name:
            if old_name in self._name_index:
                del self._name_index[old_name]
            self._name_index[new_name] = device_id

        self.device_updated.emit(device_id)
        logger.info(f"更新设备: {device.name} (ID: {device_id}), " f"字段: {list(kwargs.keys())}")

    def get_device(self, device_id: str) -> Optional[Device]:
        """获取设备 (按ID)"""
        return self._devices.get(device_id)

    def get_device_by_name(self, name: str) -> Optional[Device]:
        """获取设备 (按名称)"""
        device_id = self._name_index.get(name)
        if device_id:
            return self._devices.get(device_id)
        return None

    def has_device(self, device_id: str) -> bool:
        """检查设备是否存在"""
        return device_id in self._devices

    def has_device_name(self, name: str) -> bool:
        """检查设备名称是否已存在"""
        return name in self._name_index

    # ═══════════════════════════════════════════════════════════
    # 搜索与过滤
    # ═══════════════════════════════════════════════════════════

    def find_devices(
        self,
        *,
        name: Optional[str] = None,
        protocol: Optional[ProtocolType] = None,
        status: Optional[DeviceStatus] = None,
        tag: Optional[str] = None,
        location: Optional[str] = None,
        enabled_only: bool = False,
    ) -> list[Device]:
        """多条件搜索设备

        Args:
            name: 名称关键词 (模糊匹配, 不区分大小写)
            protocol: 协议类型 (精确匹配)
            status: 设备状态 (精确匹配)
            tag: 标签 (设备必须包含此标签)
            location: 位置关键词 (模糊匹配)
            enabled_only: 仅返回已启用设备

        Returns:
            匹配的设备列表
        """
        results: list[Device] = []

        for device in self._devices.values():
            # 启用状态过滤
            if enabled_only and not device.enabled:
                continue

            # 名称过滤
            if name and name.lower() not in device.name.lower():
                continue

            # 协议过滤
            if protocol and device.protocol_type != protocol:
                continue

            # 状态过滤
            if status and device.device_status != status:
                continue

            # 标签过滤
            if tag and not device.has_tag(tag):
                continue

            # 位置过滤
            if location and location.lower() not in device.location.lower():
                continue

            results.append(device)

        return results

    def get_devices_by_protocol(self, protocol: ProtocolType) -> list[Device]:
        """获取指定协议类型的所有设备"""
        return [d for d in self._devices.values() if d.protocol_type == protocol]

    def get_devices_by_status(self, status: DeviceStatus) -> list[Device]:
        """获取指定状态的所有设备"""
        return [d for d in self._devices.values() if d.device_status == status]

    def get_devices_by_tag(self, tag: str) -> list[Device]:
        """获取包含指定标签的所有设备"""
        return [d for d in self._devices.values() if d.has_tag(tag)]

    def get_connected_devices(self) -> list[Device]:
        """获取所有已连接设备"""
        return [d for d in self._devices.values() if d.is_connected]

    def get_alarmed_devices(self) -> list[Device]:
        """获取所有有活跃报警的设备"""
        return [d for d in self._devices.values() if d.alarm_count > 0]

    def get_enabled_devices(self) -> list[Device]:
        """获取所有已启用设备"""
        return [d for d in self._devices.values() if d.enabled]

    # ═══════════════════════════════════════════════════════════
    # 批量操作
    # ═══════════════════════════════════════════════════════════

    def add_devices(self, devices: list[Device]) -> tuple[int, list[str]]:
        """批量添加设备

        Args:
            devices: Device实例列表

        Returns:
            (成功数量, 失败原因列表)
        """
        success = 0
        errors: list[str] = []

        for device in devices:
            try:
                self.add_device(device)
                success += 1
            except (DeviceDuplicateError, DeviceConfigError) as e:
                errors.append(f"{device.name}: {e.message}")

        return success, errors

    def remove_devices(self, device_ids: list[str]) -> tuple[int, list[str]]:
        """批量移除设备

        Args:
            device_ids: 设备ID列表

        Returns:
            (成功数量, 失败原因列表)
        """
        success = 0
        errors: list[str] = []

        for dev_id in device_ids:
            try:
                self.remove_device(dev_id)
                success += 1
            except DeviceNotFoundError as e:
                errors.append(e.message)

        return success, errors

    def enable_all(self) -> int:
        """启用所有设备, 返回受影响数量"""
        count = 0
        for device in self._devices.values():
            if not device.enabled:
                device.enabled = True
                count += 1
        return count

    def disable_all(self) -> int:
        """禁用所有设备, 返回受影响数量"""
        count = 0
        for device in self._devices.values():
            if device.enabled:
                device.enabled = False
                count += 1
        return count

    def set_all_status(self, status: DeviceStatus) -> int:
        """批量设置设备状态, 返回受影响数量"""
        count = 0
        for device in self._devices.values():
            if device.device_status != status:
                device.set_status(status)
                count += 1
        return count

    def reset_all_statistics(self) -> None:
        """重置所有设备的统计信息"""
        for device in self._devices.values():
            device.reset_statistics()

    def clear_all_values(self) -> None:
        """清除所有设备的寄存器值"""
        for device in self._devices.values():
            device.clear_all_values()

    # ═══════════════════════════════════════════════════════════
    # 统计信息
    # ═══════════════════════════════════════════════════════════

    def get_statistics(self) -> dict[str, Any]:
        """获取全局统计信息"""
        total = len(self._devices)
        if total == 0:
            return {
                "total": 0,
                "enabled": 0,
                "connected": 0,
                "error": 0,
                "alarmed": 0,
                "by_protocol": {},
                "by_status": {},
                "total_registers": 0,
                "total_polls": 0,
                "total_failed": 0,
            }

        by_protocol: dict[str, int] = {}
        by_status: dict[str, int] = {}
        enabled = 0
        connected = 0
        error_count = 0
        alarmed = 0
        total_registers = 0
        total_polls = 0
        total_failed = 0

        for device in self._devices.values():
            # 协议统计
            p = device.protocol_type.value
            by_protocol[p] = by_protocol.get(p, 0) + 1

            # 状态统计
            s = device.device_status.value
            by_status[s] = by_status.get(s, 0) + 1

            if device.enabled:
                enabled += 1
            if device.is_connected:
                connected += 1
            if device.is_error:
                error_count += 1
            if device.alarm_count > 0:
                alarmed += 1

            total_registers += device.register_count
            total_polls += device.total_polls
            total_failed += device.failed_polls

        return {
            "total": total,
            "enabled": enabled,
            "connected": connected,
            "error": error_count,
            "alarmed": alarmed,
            "by_protocol": by_protocol,
            "by_status": by_status,
            "total_registers": total_registers,
            "total_polls": total_polls,
            "total_failed": total_failed,
        }

    def get_overall_success_rate(self) -> float:
        """全局采集成功率 (%)"""
        total_polls = sum(d.total_polls for d in self._devices.values())
        total_failed = sum(d.failed_polls for d in self._devices.values())
        if total_polls == 0:
            return 100.0
        return (1.0 - total_failed / total_polls) * 100.0

    # ═══════════════════════════════════════════════════════════
    # 寄存器操作 (通过Device管理器访问)
    # ═══════════════════════════════════════════════════════════

    def add_register_to_device(self, device_id: str, register: Register) -> None:
        """向设备添加寄存器

        Args:
            device_id: 设备ID
            register: 寄存器实例

        Raises:
            DeviceNotFoundError: 设备不存在
        """
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceNotFoundError(
                f"设备不存在: {device_id}",
                device_id=device_id,
            )
        device.add_register(register)

    def remove_register_from_device(self, device_id: str, register_name: str) -> None:
        """从设备移除寄存器

        Args:
            device_id: 设备ID
            register_name: 寄存器名称

        Raises:
            DeviceNotFoundError: 设备不存在
        """
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceNotFoundError(
                f"设备不存在: {device_id}",
                device_id=device_id,
            )
        device.remove_register(register_name)

    def get_register(self, device_id: str, register_name: str) -> Optional[Register]:
        """获取设备中的寄存器"""
        device = self._devices.get(device_id)
        if device is None:
            return None
        return device.get_register(register_name)

    # ═══════════════════════════════════════════════════════════
    # 信号连接/断开
    # ═══════════════════════════════════════════════════════════

    def _connect_device_signals(self, device: Device) -> None:
        """连接设备信号到管理器 (自动转发)"""
        device.status_changed.connect(self._on_device_status_changed)
        device.value_changed.connect(self._on_device_value_changed)
        device.alarm_triggered.connect(self._on_device_alarm_triggered)
        device.alarm_cleared.connect(self._on_device_alarm_cleared)

    def _disconnect_device_signals(self, device: Device) -> None:
        """断开设备信号"""
        try:
            device.status_changed.disconnect(self._on_device_status_changed)
        except RuntimeError:
            pass
        try:
            device.value_changed.disconnect(self._on_device_value_changed)
        except RuntimeError:
            pass
        try:
            device.alarm_triggered.disconnect(self._on_device_alarm_triggered)
        except RuntimeError:
            pass
        try:
            device.alarm_cleared.disconnect(self._on_device_alarm_cleared)
        except RuntimeError:
            pass

    def _on_device_status_changed(self, status: DeviceStatus) -> None:
        """转发设备状态变化"""
        sender = self.sender()
        if isinstance(sender, Device):
            self.device_status_changed.emit(sender.id, status)

    def _on_device_value_changed(self, reg_name: str, raw: int, eng: float, timestamp: object) -> None:
        """转发寄存器值变化"""
        sender = self.sender()
        if isinstance(sender, Device):
            self.device_value_changed.emit(sender.id, reg_name, raw, eng)

    def _on_device_alarm_triggered(self, dev_name: str, reg_name: str, value: float, level: str) -> None:
        """转发报警触发"""
        sender = self.sender()
        if isinstance(sender, Device):
            self.device_alarm_triggered.emit(sender.id, reg_name, value, level)

    def _on_device_alarm_cleared(self, dev_name: str, reg_name: str, level: str) -> None:
        """转发报警清除"""
        sender = self.sender()
        if isinstance(sender, Device):
            self.device_alarm_cleared.emit(sender.id, reg_name, level)

    # ═══════════════════════════════════════════════════════════
    # 持久化
    # ═══════════════════════════════════════════════════════════

    def save_to_file(self, filepath: str) -> None:
        """保存所有设备配置到JSON文件

        Args:
            filepath: 文件路径
        """
        data = {
            "version": "2.0",
            "saved_at": datetime.now().isoformat(),
            "devices": [device.to_dict() for device in self._devices.values()],
        }

        # 确保目录存在
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"保存 {self.device_count} 个设备到: {filepath}")

    def load_from_file(self, filepath: str, merge: bool = False) -> tuple[int, int]:
        """从JSON文件加载设备配置

        Args:
            filepath: 文件路径
            merge: True=合并到现有设备; False=清空后加载

        Returns:
            (成功加载数量, 跳过数量)

        Raises:
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"配置文件不存在: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not merge:
            # 清空现有设备
            self.clear()

        loaded = 0
        skipped = 0

        for dev_data in data.get("devices", []):
            try:
                device = Device.from_dict(dev_data)
                self.add_device(device)
                loaded += 1
            except (DeviceDuplicateError, DeviceConfigError) as e:
                logger.warning(f"跳过设备 {dev_data.get('name')}: {e}")
                skipped += 1

        logger.info(f"从 {filepath} 加载: 成功{loaded}, 跳过{skipped}")
        return loaded, skipped

    def export_to_json(self) -> str:
        """导出所有设备配置为JSON字符串"""
        data = {
            "version": "2.0",
            "exported_at": datetime.now().isoformat(),
            "devices": [device.to_dict() for device in self._devices.values()],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_from_json(self, json_str: str, merge: bool = False) -> tuple[int, int]:
        """从JSON字符串导入设备

        Args:
            json_str: JSON字符串
            merge: True=合并; False=替换

        Returns:
            (成功数量, 跳过数量)
        """
        data = json.loads(json_str)

        if not merge:
            self.clear()

        loaded = 0
        skipped = 0

        for dev_data in data.get("devices", []):
            try:
                device = Device.from_dict(dev_data)
                self.add_device(device)
                loaded += 1
            except (DeviceDuplicateError, DeviceConfigError) as e:
                logger.warning(f"跳过设备: {e}")
                skipped += 1

        return loaded, skipped

    # ═══════════════════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════════════════

    def clear(self) -> int:
        """清空所有设备, 返回移除数量"""
        locker = QMutexLocker(self._mutex)
        count = len(self._devices)

        for device in list(self._devices.values()):
            self._disconnect_device_signals(device)
            device.setParent(None)

        self._devices.clear()
        self._name_index.clear()

        if count > 0:
            self.device_count_changed.emit(0)
            logger.info(f"清空所有设备 (共{count}个)")

        return count

    def __repr__(self) -> str:
        return f"DeviceManager(devices={self.device_count})"

    def __len__(self) -> int:
        return self.device_count

    def __contains__(self, device_id: str) -> bool:
        return device_id in self._devices

    def __iter__(self):
        """迭代所有设备"""
        return iter(self._devices.values())
