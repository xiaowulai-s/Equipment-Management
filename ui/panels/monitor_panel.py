# -*- coding: utf-8 -*-
"""
监控面板组件
Monitor Panel - extracted from MainWindow for SRP compliance
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QTableWidgetItem,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import DataCard


class MonitorPanel(QWidget):
    """监控面板 - 设备数据展示"""

    manage_charts_requested = Signal()
    manage_cards_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._data_cards: Dict[str, DataCard] = {}
        self._current_device_id: Optional[str] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tab_widget = QTabWidget()
        layout.addWidget(self._tab_widget)

        self._data_tab = self._create_data_tab()
        self._tab_widget.addTab(self._data_tab, "数据")

        self._register_tab = self._create_register_tab()
        self._tab_widget.addTab(self._register_tab, "寄存器")

    def _create_data_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        header = QHBoxLayout()
        header.addWidget(QLabel("实时数据"))
        header.addStretch()

        manage_btn = QLabel("<a href='#'>管理卡片</a>")
        manage_btn.linkActivated.connect(lambda: self.manage_cards_requested.emit())
        header.addWidget(manage_btn)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._cards_container = QWidget()
        self._cards_layout = QHBoxLayout(self._cards_container)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll)

        return tab

    def _create_register_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._register_table = QTableWidget()
        self._register_table.setColumnCount(5)
        self._register_table.setHorizontalHeaderLabels(["名称", "地址", "值", "单位", "描述"])
        self._register_table.horizontalHeader().setStretchLastSection(True)
        self._register_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._register_table)

        return tab

    def set_device(self, device_id: str) -> None:
        self._current_device_id = device_id

    def update_data_cards(self, data: Dict[str, Any]) -> None:
        for name, info in data.items():
            if name not in self._data_cards:
                card = DataCard(
                    title=name,
                    value=str(info.get("value", "--")),
                )
                unit = info.get("unit", "")
                if unit:
                    card.unit_label = QLabel(unit)
                    card.unit_label.setStyleSheet("color: #8B949E; font-size: 12px;")
                    card.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    card.layout().addWidget(card.unit_label)
                self._data_cards[name] = card
                self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
            else:
                self._data_cards[name].set_value(
                    str(info.get("value", "--")),
                )
                unit = info.get("unit", "")
                if unit and hasattr(self._data_cards[name], "unit_label") and self._data_cards[name].unit_label:
                    self._data_cards[name].unit_label.setText(unit)

    def update_register_table(self, registers: List) -> None:
        self._register_table.setRowCount(len(registers))
        for row, reg in enumerate(registers):
            self._register_table.setItem(row, 0, QTableWidgetItem(str(reg.get("name", ""))))
            self._register_table.setItem(row, 1, QTableWidgetItem(str(reg.get("address", ""))))
            self._register_table.setItem(row, 2, QTableWidgetItem(str(reg.get("value", ""))))
            self._register_table.setItem(row, 3, QTableWidgetItem(str(reg.get("unit", ""))))
            self._register_table.setItem(row, 4, QTableWidgetItem(str(reg.get("description", ""))))

    def clear(self) -> None:
        for card in self._data_cards.values():
            card.deleteLater()
        self._data_cards.clear()
        self._register_table.setRowCount(0)
