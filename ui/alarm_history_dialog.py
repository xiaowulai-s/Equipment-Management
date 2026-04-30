# -*- coding: utf-8 -*-
"""
报警历史查看对话框
Alarm History Dialog - 表格展示、筛选、分页
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.constants import ALARM_LEVEL_NAMES_BY_INT

if TYPE_CHECKING:
    from core.data.models import DatabaseManager
    from core.utils.alarm_manager import AlarmManager

PAGE_SIZE = 50


class AlarmHistoryDialog(QDialog):
    """报警历史查看对话框 - 支持筛选、分页、确认操作"""

    def __init__(
        self, alarm_manager: "AlarmManager", db_manager: Optional["DatabaseManager"] = None, parent=None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("报警历史")
        self.setMinimumSize(900, 550)
        self._alarm_manager = alarm_manager
        self._db_manager = db_manager
        self._current_page = 0
        self._total_records = 0
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("级别:"))
        self._level_filter = QComboBox()
        self._level_filter.addItem("全部", -1)
        for val, name in ALARM_LEVEL_NAMES_BY_INT.items():
            self._level_filter.addItem(name, val)
        self._level_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._level_filter)

        filter_layout.addWidget(QLabel("时间:"))
        self._time_filter = QComboBox()
        self._time_filter.addItem("全部", 0)
        self._time_filter.addItem("最近1小时", 1)
        self._time_filter.addItem("最近24小时", 24)
        self._time_filter.addItem("最近7天", 168)
        self._time_filter.addItem("最近30天", 720)
        self._time_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._time_filter)

        ack_btn = QPushButton("确认选中报警")
        ack_btn.clicked.connect(self._acknowledge_selected)
        filter_layout.addWidget(ack_btn)

        ack_all_btn = QPushButton("确认全部")
        ack_all_btn.clicked.connect(self._acknowledge_all)
        filter_layout.addWidget(ack_all_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(["ID", "时间", "设备", "参数", "类型", "级别", "值", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        page_layout = QHBoxLayout()
        self._prev_btn = QPushButton("上一页")
        self._prev_btn.clicked.connect(self._prev_page)
        self._page_label = QLabel("第 1 页")
        self._next_btn = QPushButton("下一页")
        self._next_btn.clicked.connect(self._next_page)
        self._total_label = QLabel("共 0 条")

        page_layout.addWidget(self._prev_btn)
        page_layout.addWidget(self._page_label)
        page_layout.addWidget(self._next_btn)
        page_layout.addStretch()
        page_layout.addWidget(self._total_label)
        layout.addLayout(page_layout)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _on_filter_changed(self) -> None:
        self._current_page = 0
        self._load_data()

    def _load_data(self) -> None:
        self._table.setRowCount(0)
        alarms = self._alarm_manager.get_alarm_history(1000)
        level_filter = self._level_filter.currentData()
        hours_filter = self._time_filter.currentData()

        filtered = []
        now = datetime.now()
        for alarm in alarms:
            alarm_dict = alarm.to_dict()

            if level_filter >= 0 and alarm_dict.get("level") != level_filter:
                continue

            if hours_filter > 0:
                try:
                    alarm_time = datetime.strptime(alarm_dict["timestamp"], "%Y-%m-%d %H:%M:%S")
                    if (now - alarm_time).total_seconds() > hours_filter * 3600:
                        continue
                except (ValueError, TypeError):
                    pass

            filtered.append(alarm_dict)

        self._total_records = len(filtered)
        start = self._current_page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_data = filtered[start:end]

        for alarm_dict in page_data:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(str(alarm_dict.get("alarm_id", ""))))
            self._table.setItem(row, 1, QTableWidgetItem(str(alarm_dict.get("timestamp", ""))))
            self._table.setItem(row, 2, QTableWidgetItem(str(alarm_dict.get("device_id", ""))))
            self._table.setItem(row, 3, QTableWidgetItem(str(alarm_dict.get("parameter", ""))))
            self._table.setItem(row, 4, QTableWidgetItem(str(alarm_dict.get("alarm_type", ""))))

            level_val = alarm_dict.get("level", 0)
            level_name = ALARM_LEVEL_NAMES_BY_INT.get(level_val, str(level_val))
            level_item = QTableWidgetItem(level_name)
            if level_val >= 2:
                level_item.setForeground(QBrush(QColor(Qt.GlobalColor.red)))
            elif level_val >= 1:
                level_item.setForeground(QBrush(QColor(Qt.GlobalColor.darkYellow)))
            self._table.setItem(row, 5, level_item)

            self._table.setItem(row, 6, QTableWidgetItem(str(alarm_dict.get("value", ""))))

            status = "已确认" if alarm_dict.get("acknowledged") else "未确认"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(
                QBrush(QColor(Qt.GlobalColor.green if alarm_dict.get("acknowledged") else Qt.GlobalColor.red))
            )
            self._table.setItem(row, 7, status_item)

        total_pages = max(1, (self._total_records + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page_label.setText(f"第 {self._current_page + 1} / {total_pages} 页")
        self._total_label.setText(f"共 {self._total_records} 条")
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(end < self._total_records)

    def _prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._load_data()

    def _next_page(self) -> None:
        if (self._current_page + 1) * PAGE_SIZE < self._total_records:
            self._current_page += 1
            self._load_data()

    def _acknowledge_selected(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "提示", "请先选择报警记录")
            return
        for index in rows:
            alarm_id = self._table.item(index.row(), 0).text()
            self._alarm_manager.acknowledge_alarm(alarm_id)
        self._load_data()

    def _acknowledge_all(self) -> None:
        if QMessageBox.question(self, "确认", "确认全部报警?") == QMessageBox.StandardButton.Yes:
            for alarm in self._alarm_manager.get_active_alarms():
                self._alarm_manager.acknowledge_alarm(alarm.alarm_id)
            self._load_data()
