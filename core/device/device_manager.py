# -*- coding: utf-8 -*-
"""
设备管理器
Device Manager
"""

import json
import os
import uuid
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from .device_factory import DeviceFactory, ProtocolType
from .device_model import Device, DeviceStatus


class DeviceManager(QObject):
    """
    设备管理器
    Device Manager
    """

    # 信号定义
    device_added = Signal(str)  # 设备添加信号 (device_id)
    device_removed = Signal(str)  # 设备移除信号 (device_id)
    device_connected = Signal(str)  # 设备连接信号 (device_id)
    device_disconnected = Signal(str)  # 设备断开信号 (device_id)
    device_data_updated = Signal(str, dict)  # 设备数据更新信号 (device_id, data)
    device_error = Signal(str, str)  # 设备错误信号 (device_id, error)

    def __init__(self, config_file: str = "config.json", parent=None):
        super().__init__(parent)
        self._config_file = config_file
        self._devices: Dict[str, Device] = {}
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_all_devices)
        self._poll_interval = 1000  # 1秒轮询间隔

        # 加载已有设备
        self._load_devices()

        # 启动轮询
        self._poll_timer.start(self._poll_interval)

    def add_device(self, device_config: Dict) -> str:
        """
        添加设备
        Add device
        """
        device_id = str(uuid.uuid4())[:8]
        device_config["device_id"] = device_id

        # 创建设备
        device = DeviceFactory.create_device(device_id, device_config)

        # 连接信号
        device.status_changed.connect(lambda s, d=device_id: self._on_device_status_changed(d, s))
        device.data_updated.connect(lambda data, d=device_id: self._on_device_data_updated(d, data))
        device.error_occurred.connect(lambda error, d=device_id: self._on_device_error(d, error))

        # 保存设备
        self._devices[device_id] = device

        # 保存配置
        self._save_devices()

        # 发出信号
        self.device_added.emit(device_id)

        return device_id

    def remove_device(self, device_id: str) -> bool:
        """
        移除设备
        Remove device
        """
        if device_id not in self._devices:
            return False

        # 断开设备
        device = self._devices[device_id]
        device.disconnect()

        # 移除设备
        del self._devices[device_id]

        # 保存配置
        self._save_devices()

        # 发出信号
        self.device_removed.emit(device_id)

        return True

    def connect_device(self, device_id: str) -> bool:
        """
        连接设备
        Connect device
        """
        if device_id not in self._devices:
            return False

        device = self._devices[device_id]
        return device.connect()

    def edit_device(self, device_id: str, new_config: Dict) -> bool:
        """
        编辑设备配置
        Edit device configuration
        """
        if device_id not in self._devices:
            return False

        # 断开设备
        device = self._devices[device_id]
        device.disconnect()

        # 更新设备配置
        new_config["device_id"] = device_id
        self._devices[device_id] = DeviceFactory.create_device(device_id, new_config)

        # 连接信号
        self._devices[device_id].status_changed.connect(lambda s, d=device_id: self._on_device_status_changed(d, s))
        self._devices[device_id].data_updated.connect(lambda data, d=device_id: self._on_device_data_updated(d, data))
        self._devices[device_id].error_occurred.connect(lambda error, d=device_id: self._on_device_error(d, error))

        # 保存配置
        self._save_devices()

        # 发出信号
        self.device_added.emit(device_id)  # 使用同一个信号，刷新设备列表
        return True

    def disconnect_device(self, device_id: str):
        """
        断开设备
        Disconnect device
        """
        if device_id in self._devices:
            device = self._devices[device_id]
            device.disconnect()

    def get_device(self, device_id: str) -> Optional[Device]:
        """
        获取设备
        Get device
        """
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[Dict]:
        """
        获取所有设备列表
        Get all device list
        """
        result = []
        for device_id, device in self._devices.items():
            config = device.get_device_config()
            result.append(
                {
                    "device_id": device_id,
                    "name": config.get("name", f"设备_{device_id}"),
                    "status": device.get_status(),
                    "use_simulator": device.is_using_simulator(),
                    "config": config,
                }
            )
        return result

    def _poll_all_devices(self):
        """
        轮询所有设备
        Poll all devices
        """
        for device_id, device in self._devices.items():
            if device.get_status() == DeviceStatus.CONNECTED:
                device.poll_data()

    def _on_device_status_changed(self, device_id: str, status: int):
        """
        处理设备状态变化
        Handle device status change
        """
        if status == DeviceStatus.CONNECTED:
            self.device_connected.emit(device_id)
        elif status == DeviceStatus.DISCONNECTED:
            self.device_disconnected.emit(device_id)

    def _on_device_data_updated(self, device_id: str, data: Dict):
        """
        处理设备数据更新
        Handle device data update
        """
        self.device_data_updated.emit(device_id, data)

    def _on_device_error(self, device_id: str, error: str):
        """
        处理设备错误
        Handle device error
        """
        self.device_error.emit(device_id, error)

    def _load_devices(self):
        """
        加载设备配置
        Load device configuration
        """
        if not os.path.exists(self._config_file):
            return

        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            devices_config = config.get("devices", [])
            for device_config in devices_config:
                device_id = device_config.get("device_id")
                if device_id:
                    device = DeviceFactory.create_device(device_id, device_config)
                    device.status_changed.connect(lambda s, d=device_id: self._on_device_status_changed(d, s))
                    device.data_updated.connect(lambda data, d=device_id: self._on_device_data_updated(d, data))
                    device.error_occurred.connect(lambda error, d=device_id: self._on_device_error(d, error))
                    self._devices[device_id] = device

        except Exception as e:
            print(f"加载设备配置失败: {e}")

    def _save_devices(self):
        """
        保存设备配置
        Save device configuration
        """
        devices_config = []
        for device_id, device in self._devices.items():
            devices_config.append(device.get_device_config())

        config = {"version": "1.0", "devices": devices_config}

        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存设备配置失败: {e}")

    def set_poll_interval(self, interval_ms: int):
        """
        设置轮询间隔
        Set poll interval
        """
        self._poll_interval = interval_ms
        self._poll_timer.setInterval(interval_ms)

    def get_poll_interval(self) -> int:
        """
        获取轮询间隔
        Get poll interval
        """
        return self._poll_interval

    def batch_connect_devices(self, device_ids: List[str]) -> Dict[str, bool]:
        """
        批量连接设备
        Batch connect devices
        """
        results = {}
        for device_id in device_ids:
            results[device_id] = self.connect_device(device_id)
        return results

    def batch_disconnect_devices(self, device_ids: List[str]) -> Dict[str, bool]:
        """
        批量断开设备
        Batch disconnect devices
        """
        results = {}
        for device_id in device_ids:
            self.disconnect_device(device_id)
            results[device_id] = True
        return results

    def batch_remove_devices(self, device_ids: List[str]) -> Dict[str, bool]:
        """
        批量删除设备
        Batch remove devices
        """
        results = {}
        for device_id in device_ids:
            results[device_id] = self.remove_device(device_id)
        return results

    def get_devices_by_status(self, status: DeviceStatus) -> List[Device]:
        """
        根据状态获取设备
        Get devices by status
        """
        return [device for device in self._devices.values() if device.get_status() == status]

    def get_connected_devices(self) -> List[Device]:
        """
        获取已连接的设备
        Get connected devices
        """
        return self.get_devices_by_status(DeviceStatus.CONNECTED)

    def get_disconnected_devices(self) -> List[Device]:
        """
        获取已断开的设备
        Get disconnected devices
        """
        return self.get_devices_by_status(DeviceStatus.DISCONNECTED)
