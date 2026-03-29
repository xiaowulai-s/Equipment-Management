# -*- coding: utf-8 -*-
"""Tests for the batch operations dialog."""

from __future__ import annotations

from typing import Dict, List

from PySide6.QtWidgets import QMessageBox

from core.device.device_model import DeviceStatus
from ui.batch_operations_dialog import BatchOperationsDialog


class FakeDeviceManager:
    """Simple test double for batch dialog interactions."""

    def __init__(self) -> None:
        self.connected_ids: List[str] = []
        self.disconnected_ids: List[str] = []
        self.removed_ids: List[str] = []
        self.devices: List[Dict[str, object]] = [
            {
                "device_id": "dev-1",
                "name": "PLC-1",
                "device_type": "PLC",
                "status": DeviceStatus.DISCONNECTED,
                "config": {"device_id": "dev-1", "name": "PLC-1", "device_type": "PLC"},
            },
            {
                "device_id": "dev-2",
                "name": "Sensor-1",
                "device_type": "Sensor",
                "status": DeviceStatus.CONNECTED,
                "config": {"device_id": "dev-2", "name": "Sensor-1", "device_type": "Sensor"},
            },
        ]

    def get_all_devices(self) -> List[Dict[str, object]]:
        return list(self.devices)

    def connect_device(self, device_id: str) -> bool:
        self.connected_ids.append(device_id)
        return True

    def disconnect_device(self, device_id: str) -> None:
        self.disconnected_ids.append(device_id)

    def remove_device(self, device_id: str) -> bool:
        self.removed_ids.append(device_id)
        self.devices = [device for device in self.devices if device["device_id"] != device_id]
        return True


def test_batch_dialog_filters_devices(qtbot) -> None:
    manager = FakeDeviceManager()
    dialog = BatchOperationsDialog(manager)
    qtbot.addWidget(dialog)

    assert dialog.device_table.rowCount() == 2

    dialog.device_type_filter.setCurrentText("PLC")

    assert dialog.device_table.rowCount() == 1
    assert dialog.device_table.item(0, 2).text() == "dev-1"


def test_batch_dialog_select_and_clear_visible_devices(qtbot) -> None:
    manager = FakeDeviceManager()
    dialog = BatchOperationsDialog(manager)
    qtbot.addWidget(dialog)

    dialog._clear_all_visible()
    assert dialog.selection_summary_label.text() == "已选择 0 / 2 台设备"

    dialog._select_all_visible()
    assert dialog.selection_summary_label.text() == "已选择 2 / 2 台设备"


def test_batch_dialog_executes_async_connect(monkeypatch, qtbot) -> None:
    manager = FakeDeviceManager()
    dialog = BatchOperationsDialog(manager)
    qtbot.addWidget(dialog)

    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)

    dialog.operation_combo.setCurrentIndex(0)

    with qtbot.waitSignal(dialog.operations_completed, timeout=3000) as blocker:
        dialog._execute_operation()

    assert blocker.args == [2, 2]
    assert manager.connected_ids == ["dev-1", "dev-2"]
    assert dialog.progress_bar.value() == 100
