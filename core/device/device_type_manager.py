# -*- coding: utf-8 -*-
"""
设备类型管理器
Device Type Manager
"""

import json
import os
import sys
from typing import Any, Dict, List

from PySide6.QtCore import QObject, Signal


class DeviceTypeManager(QObject):
    """
    设备类型管理器
    Device Type Manager
    """

    # 信号定义
    device_type_added = Signal(str)
    device_type_removed = Signal(str)
    device_types_changed = Signal()

    def __init__(self, config_file: str = "device_types.json", parent=None):
        super().__init__(parent)
        # 获取正确的配置文件路径，支持PyInstaller打包
        self._config_file = self._get_config_path(config_file)
        self._device_types: List[Dict[str, Any]] = []
        self._load_device_types()

    def _get_config_path(self, config_file: str) -> str:
        """
        获取配置文件的正确路径，支持PyInstaller打包
        Get the correct path for the config file, supporting PyInstaller packaging
        """
        # PyInstaller打包后，文件会被放到sys._MEIPASS目录
        if getattr(sys, "frozen", False):
            # 获取临时目录路径
            base_path = sys._MEIPASS
            # 构建完整路径
            return os.path.join(base_path, config_file)
        else:
            # 开发环境，直接使用相对路径
            return config_file

    def _load_device_types(self):
        """
        加载设备类型
        Load device types
        """
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    self._device_types = json.load(f)
            except Exception as e:
                print(f"加载设备类型失败: {e}")
                self._device_types = []
        else:
            # 默认设备类型
            self._device_types = [
                {"name": "泵", "code": "PUMP", "description": "通用泵设备"},
                {"name": "阀门", "code": "VALVE", "description": "通用阀门设备"},
                {"name": "传感器", "code": "SENSOR", "description": "通用传感器设备"},
            ]
            self._save_device_types()

    def _save_device_types(self):
        """
        保存设备类型
        Save device types
        """
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._device_types, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存设备类型失败: {e}")

    def get_all_device_types(self) -> List[Dict[str, Any]]:
        """
        获取所有设备类型
        Get all device types
        """
        return self._device_types

    def get_device_type_by_name(self, name: str) -> Dict[str, Any]:
        """
        根据名称获取设备类型
        Get device type by name
        """
        for device_type in self._device_types:
            if device_type["name"] == name:
                return device_type
        return None

    def add_device_type(self, name: str, code: str, description: str = "") -> bool:
        """
        添加设备类型
        Add device type
        """
        # 检查是否已存在
        for device_type in self._device_types:
            if device_type["name"] == name or device_type["code"] == code:
                return False

        # 添加新设备类型
        new_type = {"name": name, "code": code, "description": description}
        self._device_types.append(new_type)
        self._save_device_types()
        self.device_type_added.emit(name)
        self.device_types_changed.emit()
        return True

    def remove_device_type(self, name: str) -> bool:
        """
        移除设备类型
        Remove device type
        """
        for i, device_type in enumerate(self._device_types):
            if device_type["name"] == name:
                del self._device_types[i]
                self._save_device_types()
                self.device_type_removed.emit(name)
                self.device_types_changed.emit()
                return True
        return False

    def update_device_type(self, old_name: str, new_name: str, new_code: str, new_description: str) -> bool:
        """
        更新设备类型
        Update device type
        """
        for i, device_type in enumerate(self._device_types):
            if device_type["name"] == old_name:
                # 检查新名称或新代码是否已存在
                for j, dt in enumerate(self._device_types):
                    if i != j and (dt["name"] == new_name or dt["code"] == new_code):
                        return False

                # 更新设备类型
                self._device_types[i] = {"name": new_name, "code": new_code, "description": new_description}
                self._save_device_types()
                self.device_types_changed.emit()
                return True
        return False
