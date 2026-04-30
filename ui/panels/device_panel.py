# -*- coding: utf-8 -*-
"""
设备面板组件
Device Panel - extracted from MainWindow for SRP compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.device.device_manager import DeviceManager


class DevicePanel(QWidget):
    """设备列表面板 - 管理设备树的显示和交互"""

    device_connect_requested = Signal(str)
    device_disconnect_requested = Signal(str)
    device_edit_requested = Signal(str)
    device_remove_requested = Signal(str)
    device_selected = Signal(str)
    add_device_requested = Signal()
    toggle_auto_reconnect_requested = Signal(bool)
    filter_changed = Signal(str)

    STATUS_CONFIG = {
        0: ("离线", "#888888", "secondary"),
        1: ("在线", "#27ae60", "success"),
        2: ("报警", "#e67e22", "warning"),
        3: ("错误", "#e74c3c", "danger"),
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._device_manager: Optional[DeviceManager] = None
        self._auto_reconnect_enabled = False
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = self._create_header()
        layout.addWidget(header)

        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["设备", "状态"])
        self.device_tree.header().setStretchLastSection(False)
        self.device_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.device_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.device_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.device_tree.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self.device_tree)

    def _create_header(self) -> QWidget:
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("设备列表")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        h_layout.addWidget(title)

        h_layout.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索设备...")
        self.search_edit.setMaximumWidth(160)
        self.search_edit.textChanged.connect(self.filter_changed.emit)
        h_layout.addWidget(self.search_edit)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setToolTip("添加设备")
        add_btn.clicked.connect(self.add_device_requested.emit)
        h_layout.addWidget(add_btn)

        return header

    def set_device_manager(self, manager: DeviceManager) -> None:
        self._device_manager = manager

    def refresh(self, search_text: str = "") -> None:
        if not self._device_manager:
            return

        devices = self._device_manager.get_all_devices()
        self.device_tree.clear()

        for dev in devices:
            name = dev.get("name", "")
            dev_id = dev.get("device_id", "")
            dev_type = dev.get("device_type", "")
            status = dev.get("status", 0)

            if search_text and search_text.lower() not in name.lower() and search_text not in dev_id:
                continue

            item = QTreeWidgetItem()
            item.setText(0, f"{name}\n{dev_type}")
            item.setData(0, 0x0100, dev_id)

            status_text, status_color, _ = self.STATUS_CONFIG.get(status, ("未知", "#888", "secondary"))
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")
            item.setText(1, status_text)
            item.setForeground(1, QBrush(QColor(status_color)))

            self.device_tree.addTopLevelItem(item)

    def get_selected_device_id(self) -> Optional[str]:
        current = self.device_tree.currentItem()
        if current:
            return current.data(0, 0x0100)
        return None

    def _on_item_changed(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        if current:
            dev_id = current.data(0, 0x0100)
            if dev_id:
                self.device_selected.emit(dev_id)

    def _show_context_menu(self, pos) -> None:
        item = self.device_tree.itemAt(pos)
        if not item:
            return

        dev_id = item.data(0, 0x0100)
        if not dev_id:
            return

        menu = QMenu(self)
        connect_action = menu.addAction("连接")
        disconnect_action = menu.addAction("断开")
        menu.addSeparator()
        edit_action = menu.addAction("编辑")
        remove_action = menu.addAction("删除")

        action = menu.exec(self.device_tree.mapToGlobal(pos))

        if action == connect_action:
            self.device_connect_requested.emit(dev_id)
        elif action == disconnect_action:
            self.device_disconnect_requested.emit(dev_id)
        elif action == edit_action:
            self.device_edit_requested.emit(dev_id)
        elif action == remove_action:
            self.device_remove_requested.emit(dev_id)

    def update_device_status(self, device_id: str, status: int) -> None:
        for i in range(self.device_tree.topLevelItemCount()):
            item = self.device_tree.topLevelItem(i)
            if item.data(0, 0x0100) == device_id:
                status_text, status_color, _ = self.STATUS_CONFIG.get(status, ("未知", "#888", "secondary"))
                item.setText(1, status_text)
                break
