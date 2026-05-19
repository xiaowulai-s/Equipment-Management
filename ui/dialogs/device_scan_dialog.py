# -*- coding: utf-8 -*-
"""
Modbus TCP 设备扫描发现对话框

功能：
1. 配置扫描参数（网段/端口/超时/并发数）
2. 实时显示扫描进度（进度条 + 已扫描/总数）
3. 动态展示发现的设备列表
4. 一键将发现的设备添加到 devices.json
5. 支持双击编辑设备参数后添加

使用方式：
    dialog = DeviceScanDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        added = dialog.get_added_devices()
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

DEVICES_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "devices.json"


class DeviceScanDialog(QDialog):
    """Modbus TCP 局域网设备扫描对话框"""

    device_added = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 扫描网络 Modbus 设备")
        self.setMinimumSize(780, 560)
        self._scan_worker = None
        self._added_devices: List[Dict] = []
        self._discovered: List[Dict] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        config_group = QGroupBox("⚙️ 扫描配置")
        config_form = QFormLayout(config_group)
        config_form.setSpacing(10)

        net_layout = QHBoxLayout()
        self.network_combo = QComboBox()
        self.network_combo.setEditable(True)
        self.network_combo.setPlaceholderText("例如: 192.168.31.0/24")
        self.network_combo.setMinimumWidth(220)
        try:
            from core.utils.modbus_scanner import ModbusLanScanner

            nets = ModbusLanScanner.get_local_networks()
            for n in nets:
                self.network_combo.addItem(n)
        except Exception:
            self.network_combo.addItem("192.168.31.0/24")
        net_layout.addWidget(self.network_combo, 1)

        self.detect_btn = QPushButton("自动检测")
        self.detect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detect_btn.setStyleSheet("""
            QPushButton {
                background: #E8F5E9; color: #2E7D32;
                border: 1px solid #A5D6A7; border-radius: 6px;
                padding: 4px 12px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background: #C8E6C9; }
        """)
        self.detect_btn.clicked.connect(self._detect_networks)
        net_layout.addWidget(self.detect_btn)
        config_form.addRow("网段 (CIDR):", net_layout)

        port_layout = QHBoxLayout()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(502)
        self.port_spin.setMaximumWidth(100)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(200, 10000)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setValue(800)
        self.timeout_spin.setMaximumWidth(110)
        port_layout.addWidget(QLabel("端口:"))
        port_layout.addWidget(self.port_spin)
        port_layout.addWidget(QLabel("   超时:"))
        port_layout.addWidget(self.timeout_spin)
        port_layout.addStretch()
        config_form.addRow("端口 / 超时:", port_layout)

        verify_check_layout = QHBoxLayout()
        self.verify_cb = QPushButton("✅ 已启用")
        self.verify_cb.setCheckable(True)
        self.verify_cb.setChecked(True)
        self.verify_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.verify_cb.setStyleSheet("""
            QPushButton:checked {
                background: #E3F2FD; color: #1565C0;
                border: 1px solid #90CAF9; border-radius: 6px;
                padding: 4px 14px; font-size: 12px; font-weight: 600;
            }
            QPushButton:unchecked {
                background: #F5F5F5; color: #9E9E9E;
                border: 1px solid #E0E0E0; border-radius: 6px;
                padding: 4px 14px; font-size: 12px;
            }
        """)
        self.verify_cb.toggled.connect(self._on_verify_toggled)
        verify_check_layout.addWidget(self.verify_cb)
        verify_check_layout.addWidget(
            QLabel("  Modbus 协议验证（关闭则仅检测端口开放，更快但可能误报）")
        )
        verify_check_layout.addStretch()
        config_form.addRow("协议验证:", verify_check_layout)

        main_layout.addWidget(config_group)

        progress_group = QGroupBox("📊 扫描进度")
        progress_layout = QVBoxLayout(progress_group)

        info_bar = QHBoxLayout()
        self.progress_label = QLabel("就绪 — 点击「开始扫描」搜索局域网内的 Modbus 设备")
        self.progress_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        info_bar.addWidget(self.progress_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m (%p%)")
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addLayout(info_bar)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.scan_btn = QPushButton("▶ 开始扫描")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setFixedHeight(36)
        self.scan_btn.setMinimumWidth(140)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white;
                border: none; border-radius: 6px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:pressed { background: #1565C0; }
            QPushButton:disabled { background: #BDBDBD; }
        """)
        self.scan_btn.clicked.connect(self._toggle_scan)
        self.stop_btn = QPushButton("⏹ 停止扫描")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #FFEBEE; color: #C62828;
                border: 1px solid #EF9A9A; border-radius: 6px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #FFCDD2; }
            QPushButton:disabled { background: #F5F5F5; color: #9E9E9E; border: 1px solid #E0E0E0; }
        """)
        self.stop_btn.clicked.connect(self._stop_scan)
        btn_row.addWidget(self.scan_btn)
        btn_row.addWidget(self.stop_btn)
        progress_layout.addLayout(btn_row)

        main_layout.addWidget(progress_group)

        result_group = QGroupBox("📋 发现的设备")
        result_layout = QVBoxLayout(result_group)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels([
            "IP 地址", "端口", "延迟 (ms)", "状态", "操作", "添加状态"
        ])
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.result_table.setColumnWidth(1, 60)
        self.result_table.setColumnWidth(2, 80)
        self.result_table.setColumnWidth(3, 85)
        self.result_table.setColumnWidth(4, 120)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setStyleSheet("""
            QTableWidget {
                background: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                gridline-color: #F0F2F5;
                font-size: 12px;
            }
            QTableWidget::item { padding: 5px 8px; }
            QHeaderView::section {
                background: #F6F8FA; color: #57606A;
                padding: 6px 8px; font-size: 11px; font-weight: 600;
                border: none; border-bottom: 1px solid #E5E7EB;
            }
        """)
        result_layout.addWidget(self.result_table)

        action_bar = QHBoxLayout()
        action_bar.addStretch()
        self.add_selected_btn = QPushButton("➕ 添加选中设备")
        self.add_selected_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_selected_btn.setStyleSheet("""
            QPushButton {
                background: #E8F5E9; color: #2E7D32;
                border: 1px solid #A5D6A7; border-radius: 6px;
                padding: 6px 16px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #C8E6C9; }
            QPushButton:disabled { background: #EEEEEE; color: #BDBDBD; border: 1px solid #E0E0E0; }
        """)
        self.add_selected_btn.clicked.connect(self._add_selected_devices)
        self.add_all_btn = QPushButton("➕ 全部添加")
        self.add_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_all_btn.setStyleSheet("""
            QPushButton {
                background: #E3F2FD; color: #1565C0;
                border: 1px solid #90CAF9; border-radius: 6px;
                padding: 6px 16px; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #BBDEFB; }
            QPushButton:disabled { background: #EEEEEE; color: #BDBDBD; border: 1px solid #E0E0E0; }
        """)
        self.add_all_btn.clicked.connect(self._add_all_devices)
        action_bar.addWidget(self.add_selected_btn)
        action_bar.addWidget(self.add_all_btn)
        result_layout.addLayout(action_bar)

        main_layout.addWidget(result_group)

        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        self.close_btn = QPushButton("关闭")
        self.close_btn.setFixedHeight(34)
        self.close_btn.setMinimumWidth(90)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #F5F5F5; color: #424242;
                border: 1px solid #E0E0E0; border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background: #EEEEEE; }
        """)
        self.close_btn.clicked.connect(self.accept)
        bottom_bar.addWidget(self.close_btn)
        main_layout.addLayout(bottom_bar)

        self._update_button_state(False)

    def _on_verify_toggled(self, checked: bool):
        if checked:
            self.verify_cb.setText("✅ 已启用")
        else:
            self.verify_cb.setText("⚠ 仅端口探测")

    def _detect_networks(self):
        try:
            from core.utils.modbus_scanner import ModbusLanScanner

            nets = ModbusLanScanner.get_local_networks()
            self.network_combo.clear()
            for n in nets:
                self.network_combo.addItem(n)
            self.progress_label.setText(f"✅ 自动检测到 {len(nets)} 个本地网段")
            self.progress_label.setStyleSheet("font-size: 12px; color: #4CAF50;")
        except Exception as e:
            self.progress_label.setText(f"❌ 检测失败: {e}")
            self.progress_label.setStyleSheet("font-size: 12px; color: #F44336;")

    def _toggle_scan(self):
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self._start_scan()

    def _start_scan(self):
        network = self.network_combo.currentText().strip()
        if not network:
            QMessageBox.warning(self, "提示", "请输入要扫描的网段（如 192.168.31.0/24）")
            return

        self.result_table.setRowCount(0)
        self._discovered.clear()
        self._added_devices.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(254)
        self._update_button_state(True)

        try:
            from core.utils.modbus_scanner import AsyncScanWorker

            if self._scan_worker is not None:
                try:
                    self._scan_worker.progress.disconnect()
                    self._scan_worker.finished.disconnect()
                    self._scan_worker.error.disconnect()
                    self._scan_worker.deleteLater()
                except Exception:
                    pass
                self._scan_worker = None

            self._scan_worker = AsyncScanWorker.create(
                network=network,
                port=self.port_spin.value(),
                timeout_ms=self.timeout_spin.value(),
                verify_modbus=self.verify_cb.isChecked(),
            )
            self._scan_worker.progress.connect(self._on_scan_progress)
            self._scan_worker.finished.connect(self._on_scan_finished)
            self._scan_worker.error.connect(self._on_scan_error)
            self._scan_worker.start()
            self.progress_label.setText(
                f"🔍 正在扫描 {network} ... (端口:{self.port_spin.value()})"
            )
            self.progress_label.setStyleSheet("font-size: 12px; color: #2196F3;")
        except Exception as e:
            logger.error("启动扫描失败: %s", e)
            self._update_button_state(False)
            self.progress_label.setText(f"❌ 启动失败: {e}")
            self.progress_label.setStyleSheet("font-size: 12px; color: #F44336;")

    @Slot(int, int, object)
    def _on_scan_progress(self, completed: int, total: int, result_obj):
        if total > 0:
            self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(completed)
        self.progress_label.setText(
            f"🔍 扫描中... {completed}/{total}"
        )

        from core.utils.modbus_scanner import ScanResult

        if isinstance(result_obj, ScanResult) and result_obj.is_modbus:
            self._add_result_row(result_obj.to_dict())
            self._discovered.append(result_obj.to_dict())

    @Slot(list)
    def _on_scan_finished(self, results: list):
        self._update_button_state(False)
        count = len([r for r in results if r.get("is_modbus")])
        self.progress_label.setText(
            f"✅ 扫描完成！发现 {count} 个 Modbus 设备"
        )
        self.progress_label.setStyleSheet(
            "font-size: 12px; color: #4CAF50; font-weight: 600;"
        )

    @Slot(str)
    def _on_scan_error(self, error_msg: str):
        self._update_button_state(False)
        self.progress_label.setText(f"❌ 扫描出错: {error_msg}")
        self.progress_label.setStyleSheet("font-size: 12px; color: #F44336;")

    def _stop_scan(self):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.stop()
            self._scan_worker.wait(3000)
        self._update_button_state(False)
        self.progress_label.setText("⏹ 扫描已停止")
        self.progress_label.setStyleSheet("font-size: 12px; color: #FF9800;")

    def _update_button_state(self, scanning: bool):
        self.scan_btn.setEnabled(not scanning)
        self.scan_btn.setText("▶ 开始扫描" if not scanning else "⏳ 扫描中...")
        self.stop_btn.setEnabled(scanning)
        self.network_combo.setEnabled(not scanning)
        self.port_spin.setEnabled(not scanning)
        self.timeout_spin.setEnabled(not scanning)
        self.detect_btn.setEnabled(not scanning)

    def _add_result_row(self, dev: Dict[str, Any]):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        ip_item = QTableWidgetItem(dev.get("ip", ""))
        ip_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_table.setItem(row, 0, ip_item)

        port_item = QTableWidgetItem(str(dev.get("port", 502)))
        port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_table.setItem(row, 1, port_item)

        lat_item = QTableWidgetItem(f"{dev.get('latency_ms', 0):.0f}")
        lat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_table.setItem(row, 2, lat_item)

        status = "Modbus ✓" if dev.get("is_modbus") else "开放端口"
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if dev.get("is_modbus"):
            status_item.setForeground(Qt.GlobalColor.darkGreen)
        self.result_table.setItem(row, 3, status_item)

        add_btn = QPushButton("➕ 添加")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                color: #2196F3; border: 1px solid #BBDEFB; border-radius: 4px;
                background: #E3F2FD; padding: 2px 10px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #BBDEFB; }
        """)
        add_btn.clicked.connect(lambda _, r=row: self._add_single_device(r))
        self.result_table.setCellWidget(row, 4, add_btn)

        pending_lbl = QLabel("待添加")
        pending_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pending_lbl.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        self.result_table.setItem(row, 5, QTableWidgetItem(""))

    def _add_single_device(self, row: int):
        ip_item = self.result_table.item(row, 0)
        port_item = self.result_table.item(row, 1)
        if not ip_item or not port_item:
            return

        ip = ip_item.text().strip()
        port = int(port_item.text())
        device_id = ip.replace(".", "_")

        new_device = {
            "id": device_id,
            "name": f"扫描设备_{device_id}",
            "description": f"通过网络扫描发现 ({ip}:{port})",
            "ip": ip,
            "port": port,
            "unit_id": 1,
            "timeout_ms": 3000,
            "byte_order": "ABCD",
            "polling_interval_ms": 1000,
            "address_base": 40001,
            "points": [
                {"name": "Data0", "addr": 40001, "type": "uint16"},
                {"name": "Data1", "addr": 40002, "type": "uint16"},
                {"name": "Data2", "addr": 40003, "type": "uint16"},
                {"name": "Data3", "addr": 40004, "type": "uint16"},
            ],
        }

        success = self._save_device_to_config(new_device)
        if success:
            self._added_devices.append(new_device)
            status_item = QTableWidgetItem("✅ 已添加")
            status_item.setForeground(Qt.GlobalColor.darkGreen)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.result_table.setItem(row, 5, status_item)
            btn = self.result_table.cellWidget(row, 4)
            if btn:
                btn.setEnabled(False)
                btn.setText("已添加")
            self.device_added.emit(new_device)

    def _add_selected_devices(self):
        selected_rows = set(item.row() for item in self.result_table.selectedItems())
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在表格中选中要添加的设备行")
            return
        for row in sorted(selected_rows):
            status_item = self.result_table.item(row, 5)
            if status_item and status_item.text() == "✅ 已添加":
                continue
            self._add_single_device(row)

    def _add_all_devices(self):
        for row in range(self.result_table.rowCount()):
            status_item = self.result_table.item(row, 5)
            if status_item and status_item.text() == "✅ 已添加":
                continue
            self._add_single_device(row)

    def _save_device_to_config(self, device_cfg: Dict) -> bool:
        try:
            data = {}
            if DEVICES_CONFIG_PATH.exists():
                with open(DEVICES_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)

            for existing in data.get("devices", []):
                if existing.get("ip") == device_cfg["ip"] and existing.get("port") == device_cfg["port"]:
                    reply = QMessageBox.question(
                        self,
                        "配置重复",
                        f"已存在相同 IP+端口的设备 [{existing.get('name', existing.get('id'))}]。\n是否覆盖？",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if reply != QMessageBox.Yes:
                        return False
                    data["devices"].remove(existing)
                    break

            data.setdefault("devices", []).append(device_cfg)
            data.setdefault("_meta", {})["version"] = "3.0.4"
            data["_meta"]["source"] = "DeviceScanDialog"

            DEVICES_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(DEVICES_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("[Scan] 设备已添加: %s @ %s:%s", device_cfg["id"], device_cfg["ip"], device_cfg["port"])
            return True

        except Exception as e:
            logger.error("保存扫描发现的设备失败: %s", e)
            QMessageBox.warning(self, "保存失败", f"无法保存设备配置: {str(e)}")
            return False

    def get_added_devices(self) -> List[Dict]:
        return self._added_devices
