# -*- coding: utf-8 -*-
"""Batch operations dialog."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import Checkbox, ComboBox, DataTable, PrimaryButton, SecondaryButton

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.device.device_manager import DeviceManager


@dataclass(frozen=True)
class DeviceRow:
    """Normalized device row for the dialog."""

    device_id: str
    name: str
    device_type: str
    status: str
    status_text: str
    config: Dict[str, Any]


class BatchOperationWorker(QObject):
    """Execute batch operations in a worker thread."""

    progress_changed = Signal(int, int, str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        device_manager: Any,
        operation_key: str,
        devices: Sequence[DeviceRow],
        export_path: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._device_manager = device_manager
        self._operation_key = operation_key
        self._devices = list(devices)
        self._export_path = export_path

    def run(self) -> None:
        """Run the selected operation."""
        total = len(self._devices)
        succeeded = 0
        failed_devices: List[str] = []

        try:
            if self._operation_key == "export":
                export_count = self._export_selected_devices()
                message = f"已导出 {export_count} 台设备的配置。"
                self.progress_changed.emit(total, total, message)
                self.finished.emit(
                    {
                        "success_count": export_count,
                        "total_count": total,
                        "failed_devices": failed_devices,
                        "message": message,
                    }
                )
                return

            for index, device in enumerate(self._devices, start=1):
                success = self._execute_for_device(device)
                if success:
                    succeeded += 1
                else:
                    failed_devices.append(device.device_id)

                self.progress_changed.emit(index, total, f"正在处理 {device.name} ({device.device_id})")

            self.finished.emit(
                {
                    "success_count": succeeded,
                    "total_count": total,
                    "failed_devices": failed_devices,
                    "message": self._build_result_message(succeeded, total, failed_devices),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive UI guard
            logger.exception("批量操作执行失败")
            self.failed.emit(str(exc))

    def _execute_for_device(self, device: DeviceRow) -> bool:
        if self._operation_key == "connect":
            return bool(self._device_manager.connect_device(device.device_id))
        if self._operation_key == "disconnect":
            self._device_manager.disconnect_device(device.device_id)
            return True
        if self._operation_key == "remove":
            return bool(self._device_manager.remove_device(device.device_id))

        raise ValueError(f"Unsupported batch operation: {self._operation_key}")

    def _export_selected_devices(self) -> int:
        if not self._export_path:
            raise ValueError("缺少导出路径")

        payload = {
            "version": "1.0",
            "devices": [device.config for device in self._devices],
        }
        export_file = Path(self._export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)
        export_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(self._devices)

    @staticmethod
    def _build_result_message(success_count: int, total_count: int, failed_devices: Sequence[str]) -> str:
        if not failed_devices:
            return f"批量操作完成，成功 {success_count}/{total_count}。"
        failed_text = "、".join(failed_devices)
        return f"批量操作完成，成功 {success_count}/{total_count}，失败设备: {failed_text}"


class BatchOperationsDialog(QDialog):
    """Batch operations dialog for device management."""

    operations_completed = Signal(int, int)

    OPERATION_OPTIONS = (
        ("批量连接设备", "connect"),
        ("批量断开设备", "disconnect"),
        ("批量删除设备", "remove"),
        ("批量导出配置", "export"),
    )

    def __init__(self, device_manager: DeviceManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._device_manager = device_manager
        self._all_devices: List[DeviceRow] = []
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[BatchOperationWorker] = None
        self._init_ui()
        self._load_devices()

    def _init_ui(self) -> None:
        self.setWindowTitle("批量操作")
        self.resize(920, 680)
        self.setMinimumSize(820, 620)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(16)

        root_layout.addWidget(self._build_device_group())
        root_layout.addWidget(self._build_operation_group())
        root_layout.addWidget(self._build_result_group())
        root_layout.addLayout(self._build_action_buttons())

    def _build_device_group(self) -> QGroupBox:
        group = QGroupBox("设备选择")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        filter_label = QLabel("设备类型")
        self.device_type_filter = ComboBox()
        self.device_type_filter.currentIndexChanged.connect(self._apply_filters)

        self.select_all_btn = SecondaryButton("全选")
        self.select_all_btn.clicked.connect(self._select_all_visible)

        self.clear_selection_btn = SecondaryButton("清空")
        self.clear_selection_btn.clicked.connect(self._clear_all_visible)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.device_type_filter, 1)
        filter_layout.addStretch()
        filter_layout.addWidget(self.select_all_btn)
        filter_layout.addWidget(self.clear_selection_btn)
        layout.addLayout(filter_layout)

        self.device_table = DataTable(columns=["选择", "设备名称", "设备 ID", "类型", "状态"])
        self.device_table.setAlternatingRowColors(False)
        self.device_table.verticalHeader().setVisible(False)
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setSelectionMode(QTableWidget.NoSelection)
        self.device_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.device_table)

        self.selection_summary_label = QLabel("已选择 0 / 0 台设备")
        self.selection_summary_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.selection_summary_label)
        return group

    def _build_operation_group(self) -> QGroupBox:
        group = QGroupBox("操作配置")
        layout = QFormLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)

        self.operation_combo = ComboBox()
        for label, operation_key in self.OPERATION_OPTIONS:
            self.operation_combo.addItem(label, operation_key)
        self.operation_combo.currentIndexChanged.connect(self._update_operation_ui)

        self.export_path_label = QLabel("导出路径")
        self.export_path_value = QLabel("未设置")
        self.export_path_value.setWordWrap(True)

        self.export_browse_btn = SecondaryButton("选择文件")
        self.export_browse_btn.clicked.connect(self._choose_export_path)

        export_path_layout = QHBoxLayout()
        export_path_layout.addWidget(self.export_path_value, 1)
        export_path_layout.addWidget(self.export_browse_btn)

        self.progress_label = QLabel("等待执行")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        layout.addRow("操作类型", self.operation_combo)
        layout.addRow(self.export_path_label, export_path_layout)
        layout.addRow("执行进度", self.progress_bar)
        layout.addRow("当前状态", self.progress_label)

        self._update_operation_ui()
        return group

    def _build_result_group(self) -> QGroupBox:
        group = QGroupBox("执行结果")
        layout = QHBoxLayout(group)
        layout.setSpacing(12)

        self.success_card = self._create_result_card("成功", "0")
        self.failure_card = self._create_result_card("失败", "0")
        self.total_card = self._create_result_card("总数", "0")

        layout.addWidget(self.success_card["widget"])
        layout.addWidget(self.failure_card["widget"])
        layout.addWidget(self.total_card["widget"])
        return group

    def _build_action_buttons(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addStretch()

        self.execute_btn = PrimaryButton("执行操作")
        self.execute_btn.clicked.connect(self._execute_operation)

        self.close_btn = SecondaryButton("关闭")
        self.close_btn.clicked.connect(self.reject)

        layout.addWidget(self.close_btn)
        layout.addWidget(self.execute_btn)
        return layout

    def _create_result_card(self, title: str, value: str) -> Dict[str, Any]:
        card = QGroupBox()
        card.setObjectName("DataCard")
        card
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-size: 24px; font-weight: 700;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return {"widget": card, "value_label": value_label}

    def _load_devices(self) -> None:
        # 兼容新旧架构
        if hasattr(self._device_manager, "devices"):
            # 新架构: DeviceManager.devices 是 dict[str, Device]
            devices = list(self._device_manager.devices.values())
        else:
            # 旧架构: DeviceManagerV2.get_all_devices() 返回 list[dict]
            devices = self._device_manager.get_all_devices()

        self._all_devices = self._normalize_devices(devices)
        self.device_type_filter.blockSignals(True)
        self.device_type_filter.clear()
        self.device_type_filter.addItem("全部", None)
        for device_type in sorted({device.device_type for device in self._all_devices if device.device_type}):
            self.device_type_filter.addItem(device_type, device_type)
        self.device_type_filter.blockSignals(False)
        self._apply_filters()

    def _normalize_devices(self, devices: Sequence[Any]) -> List[DeviceRow]:
        rows: List[DeviceRow] = []
        for device in devices:
            if isinstance(device, dict):
                # 旧架构格式
                config = dict(device.get("config", {}))
                device_id = str(device.get("device_id") or device.get("id") or config.get("device_id") or "")
                name = str(device.get("name") or config.get("name") or device_id)
                device_type = str(device.get("device_type") or config.get("device_type") or "")
                status_raw = device.get("status", "disconnected")
                status = (
                    str(status_raw) if not isinstance(status_raw, int) else self._int_status_to_str(int(status_raw))
                )
                normalized_config = dict(config)
            elif hasattr(device, "device_status"):
                # 新架构格式: src.device.Device 对象
                config = device.to_dict()
                device_id = str(device.id)
                name = str(device.name)
                device_type = str(config.get("device_type", ""))
                status = str(
                    device.device_status.value if hasattr(device.device_status, "value") else device.device_status
                )
                normalized_config = config
            elif hasattr(device, "get_device_config"):
                # 旧 Device 类
                config = dict(device.get_device_config())
                device_id = str(device.get_device_id())
                name = str(config.get("name") or device_id)
                device_type = str(config.get("device_type") or "")
                status_raw = device.get_status()
                status = (
                    str(status_raw) if not isinstance(status_raw, int) else self._int_status_to_str(int(status_raw))
                )
                normalized_config = config
            else:
                continue

            normalized_config.setdefault("device_id", device_id)
            rows.append(
                DeviceRow(
                    device_id=device_id,
                    name=name,
                    device_type=device_type,
                    status=status,
                    status_text=self._status_text(status),
                    config=normalized_config,
                )
            )
        return rows

    def _apply_filters(self) -> None:
        filter_value = self.device_type_filter.currentData()
        filtered = [device for device in self._all_devices if filter_value in (None, "", device.device_type)]
        self.device_table.setRowCount(len(filtered))

        for row, device in enumerate(filtered):
            checkbox = Checkbox()
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._update_selection_summary)

            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.addWidget(checkbox)
            self.device_table.setCellWidget(row, 0, checkbox_container)

            self._set_centered_item(row, 1, device.name)
            self._set_centered_item(row, 2, device.device_id)
            self._set_centered_item(row, 3, device.device_type)

            status_item = QTableWidgetItem(device.status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setData(Qt.UserRole, device.device_id)
            status_item.setForeground(self._status_brush(device.status))
            self.device_table.setItem(row, 4, status_item)

        self._update_selection_summary()
        self._update_result_cards(success=0, failure=0, total=len(filtered))

    def _set_centered_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.device_table.setItem(row, column, item)

    def _select_all_visible(self) -> None:
        for row in range(self.device_table.rowCount()):
            checkbox = self._row_checkbox(row)
            if checkbox is not None:
                checkbox.setChecked(True)

    def _clear_all_visible(self) -> None:
        for row in range(self.device_table.rowCount()):
            checkbox = self._row_checkbox(row)
            if checkbox is not None:
                checkbox.setChecked(False)

    def _row_checkbox(self, row: int) -> Optional[QCheckBox]:
        cell_widget = self.device_table.cellWidget(row, 0)
        if cell_widget is None:
            return None
        return cell_widget.findChild(QCheckBox)

    def _update_selection_summary(self) -> None:
        total = self.device_table.rowCount()
        selected = len(self._selected_devices())
        self.selection_summary_label.setText(f"已选择 {selected} / {total} 台设备")

    def _selected_devices(self) -> List[DeviceRow]:
        selected: List[DeviceRow] = []
        visible_rows: Dict[str, int] = {}
        for row in range(self.device_table.rowCount()):
            item = self.device_table.item(row, 4)
            if item is not None:
                visible_rows[item.data(Qt.ItemDataRole.UserRole)] = row
        device_index = {device.device_id: device for device in self._all_devices}

        for device_id, row in visible_rows.items():
            checkbox = self._row_checkbox(row)
            if checkbox is not None and checkbox.isChecked() and device_id in device_index:
                selected.append(device_index[device_id])
        return selected

    def _update_operation_ui(self) -> None:
        is_export = self._current_operation_key() == "export"
        self.export_path_label.setVisible(is_export)
        self.export_path_value.setVisible(is_export)
        self.export_browse_btn.setVisible(is_export)

    def _choose_export_path(self) -> None:
        suggested_name = "devices_batch_export.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出设备配置",
            str(Path.cwd() / suggested_name),
            "JSON Files (*.json)",
        )
        if file_path:
            self.export_path_value.setText(file_path)

    def _execute_operation(self) -> None:
        selected_devices = self._selected_devices()
        if not selected_devices:
            QMessageBox.warning(self, "批量操作", "请至少选择一台设备。")
            return

        operation_label = self.operation_combo.currentText()
        operation_key = self._current_operation_key()

        if operation_key == "export" and self.export_path_value.text() == "未设置":
            QMessageBox.warning(self, "批量操作", "请选择导出文件路径。")
            return

        if operation_key == "remove":
            question = f"确定删除选中的 {len(selected_devices)} 台设备吗？该操作不可撤销。"
        else:
            question = f"确定对选中的 {len(selected_devices)} 台设备执行“{operation_label}”吗？"

        if QMessageBox.question(self, "确认操作", question, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        self._set_running_state(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("开始执行")
        self._update_result_cards(success=0, failure=0, total=len(selected_devices))

        export_path = self.export_path_value.text() if operation_key == "export" else None
        self._worker_thread = QThread(self)
        self._worker = BatchOperationWorker(
            device_manager=self._device_manager,
            operation_key=operation_key,
            devices=selected_devices,
            export_path=export_path,
        )
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress_changed.connect(self._on_progress_changed)
        self._worker.finished.connect(self._on_operation_finished)
        self._worker.failed.connect(self._on_operation_failed)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._cleanup_worker)
        self._worker_thread.start()

    def _on_progress_changed(self, current: int, total: int, message: str) -> None:
        progress = 0 if total == 0 else int(current * 100 / total)
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)

    def _on_operation_finished(self, result: Dict[str, Any]) -> None:
        success_count = int(result["success_count"])
        total_count = int(result["total_count"])
        failure_count = total_count - success_count
        self._update_result_cards(success=success_count, failure=failure_count, total=total_count)
        self.progress_bar.setValue(100)
        self.progress_label.setText(result["message"])
        self._set_running_state(False)
        self.operations_completed.emit(success_count, total_count)
        self._load_devices()
        QMessageBox.information(self, "批量操作", result["message"])

    def _on_operation_failed(self, error_message: str) -> None:
        self._set_running_state(False)
        self.progress_label.setText("执行失败")
        QMessageBox.critical(self, "批量操作失败", error_message)

    def _cleanup_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._worker_thread is not None:
            self._worker_thread.deleteLater()
            self._worker_thread = None

    def _set_running_state(self, is_running: bool) -> None:
        self.execute_btn.setEnabled(not is_running)
        self.close_btn.setEnabled(not is_running)
        self.select_all_btn.setEnabled(not is_running)
        self.clear_selection_btn.setEnabled(not is_running)
        self.operation_combo.setEnabled(not is_running)
        self.device_type_filter.setEnabled(not is_running)
        self.export_browse_btn.setEnabled(not is_running)

    def _update_result_cards(self, success: int, failure: int, total: int) -> None:
        self.success_card["value_label"].setText(str(success))
        self.failure_card["value_label"].setText(str(failure))
        self.total_card["value_label"].setText(str(total))

    def _current_operation_key(self) -> str:
        return str(self.operation_combo.currentData())

    @staticmethod
    def _status_text(status: str) -> str:
        mapping = {
            "disconnected": "未连接",
            "connecting": "连接中",
            "connected": "已连接",
            "error": "异常",
        }
        return mapping.get(status, status or "未知")

    @staticmethod
    def _status_brush(status: str) -> Qt.GlobalColor:
        mapping = {
            "disconnected": Qt.GlobalColor.red,
            "connecting": Qt.GlobalColor.darkYellow,
            "connected": Qt.GlobalColor.darkGreen,
            "error": Qt.GlobalColor.darkRed,
        }
        return mapping.get(status, Qt.GlobalColor.black)

    @staticmethod
    def _int_status_to_str(status_int: int) -> str:
        """将旧架构整数状态码转换为新架构字符串"""
        mapping = {0: "disconnected", 1: "connecting", 2: "connected", 3: "error"}
        return mapping.get(status_int, "disconnected")
