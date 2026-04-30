# -*- coding: utf-8 -*-
"""
数据导入导出管理器
Data Export Manager - extracted from MainWindow for SRP compliance
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

if TYPE_CHECKING:
    from core.data import DatabaseManager
    from core.device.device_manager import DeviceManager


class DataExportManager(QObject):
    """数据导入导出管理器"""

    export_completed = Signal(int)
    import_completed = Signal(int)

    def __init__(self, device_manager: Optional[DeviceManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._device_manager = device_manager

    def set_device_manager(self, manager: DeviceManager) -> None:
        self._device_manager = manager

    def export_device_configs(self, parent_widget: QWidget) -> bool:
        if not self._device_manager:
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "导出设备配置",
            "device_configs.json",
            "JSON文件 (*.json);;所有文件 (*)",
        )
        if not file_path:
            return False

        try:
            devices = self._device_manager.get_all_devices()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(devices, f, ensure_ascii=False, indent=2)

            QMessageBox.information(parent_widget, "导出成功", f"已导出 {len(devices)} 个设备配置")
            self.export_completed.emit(len(devices))
            return True
        except (OSError, json.JSONEncodeError) as e:
            QMessageBox.critical(parent_widget, "导出失败", f"导出设备配置失败: {e}")
            return False

    def import_device_configs(self, parent_widget: QWidget) -> bool:
        if not self._device_manager:
            return False

        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "导入设备配置",
            "",
            "JSON文件 (*.json);;所有文件 (*)",
        )
        if not file_path:
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                devices = json.load(f)

            if not isinstance(devices, list):
                QMessageBox.warning(parent_widget, "格式错误", "配置文件格式不正确")
                return False

            count = 0
            for dev_config in devices:
                try:
                    self._device_manager.add_device(dev_config)
                    count += 1
                except (ValueError, KeyError) as e:
                    continue

            QMessageBox.information(parent_widget, "导入成功", f"已导入 {count} 个设备配置")
            self.import_completed.emit(count)
            return True
        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(parent_widget, "导入失败", f"导入设备配置失败: {e}")
            return False
