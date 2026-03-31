# -*- coding: utf-8 -*-
"""
仪表盘配置对话框

支持:
- 手动添加仪表盘
- 关联寄存器变量
- 设置仪表盘参数（范围、单位、颜色）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QSpinBox, QVBoxLayout, QWidget

from ui.widgets import ComboBox, LineEdit, PrimaryButton, SecondaryButton


class GaugeConfigDialog(QDialog):
    """
    仪表盘配置对话框

    用于添加或编辑仪表盘，支持关联寄存器变量。
    """

    def __init__(
        self,
        available_registers: List[Dict[str, Any]],
        existing_config: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._available_registers = available_registers
        self._existing_config = existing_config or {}
        self._result: Optional[Dict[str, Any]] = None

        self.setWindowTitle("编辑仪表盘" if existing_config else "添加仪表盘")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # 仪表盘标题
        self._title_edit = LineEdit("请输入仪表盘名称")
        self._title_edit.setText(self._existing_config.get("title", ""))
        form_layout.addRow("标题:", self._title_edit)

        # 关联寄存器
        self._register_combo = ComboBox()
        self._register_combo.addItem("-- 请选择寄存器 --", "")
        for reg in self._available_registers:
            name = reg.get("name", "")
            address = reg.get("address", "")
            display_text = f"{name} (地址: {address})"
            self._register_combo.addItem(display_text, name)

        # 设置已选寄存器
        existing_reg = self._existing_config.get("register_name", "")
        for i in range(self._register_combo.count()):
            if self._register_combo.itemData(i) == existing_reg:
                self._register_combo.setCurrentIndex(i)
                break

        form_layout.addRow("关联寄存器:", self._register_combo)

        # 数值范围
        range_layout = QHBoxLayout()
        self._min_spin = QSpinBox()
        self._min_spin.setRange(-999999, 999999)
        self._min_spin.setValue(self._existing_config.get("min_value", 0))
        self._max_spin = QSpinBox()
        self._max_spin.setRange(-999999, 999999)
        self._max_spin.setValue(self._existing_config.get("max_value", 100))
        range_layout.addWidget(self._min_spin)
        range_layout.addWidget(QLabel("至"))
        range_layout.addWidget(self._max_spin)
        form_layout.addRow("数值范围:", range_layout)

        # 单位
        self._unit_edit = LineEdit("请输入单位")
        self._unit_edit.setText(self._existing_config.get("unit", ""))
        form_layout.addRow("单位:", self._unit_edit)

        # 颜色选择
        self._color_combo = ComboBox()
        colors = [
            ("蓝色", "#2196F3"),
            ("绿色", "#4CAF50"),
            ("橙色", "#FF9800"),
            ("红色", "#F44336"),
            ("紫色", "#9C27B0"),
            ("青色", "#00BCD4"),
        ]
        for name, color in colors:
            self._color_combo.addItem(name, color)

        # 设置已选颜色
        existing_color = self._existing_config.get("color", "#2196F3")
        for i in range(self._color_combo.count()):
            if self._color_combo.itemData(i) == existing_color:
                self._color_combo.setCurrentIndex(i)
                break

        form_layout.addRow("颜色:", self._color_combo)

        layout.addLayout(form_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._ok_btn = PrimaryButton("确定")
        self._cancel_btn = SecondaryButton("取消")
        self._ok_btn.clicked.connect(self._on_ok)
        self._cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self._ok_btn)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)

    def _on_ok(self) -> None:
        """确认按钮点击"""
        title = self._title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "警告", "请输入仪表盘标题")
            return

        register_name = self._register_combo.currentData()
        if not register_name:
            QMessageBox.warning(self, "警告", "请选择关联的寄存器")
            return

        min_value = self._min_spin.value()
        max_value = self._max_spin.value()
        if min_value >= max_value:
            QMessageBox.warning(self, "警告", "最小值必须小于最大值")
            return

        self._result = {
            "title": title,
            "register_name": register_name,
            "min_value": min_value,
            "max_value": max_value,
            "unit": self._unit_edit.text().strip(),
            "color": self._color_combo.currentData(),
        }
        self.accept()

    def get_config(self) -> Optional[Dict[str, Any]]:
        """获取配置结果"""
        return self._result


class GaugeManagerDialog(QDialog):
    """
    仪表盘管理对话框

    用于管理设备的所有仪表盘，支持添加、编辑、删除。
    """

    def __init__(
        self,
        device_id: str,
        device_name: str,
        available_registers: List[Dict[str, Any]],
        existing_gauges: List[Dict[str, Any]],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._device_id = device_id
        self._device_name = device_name
        self._available_registers = available_registers
        self._gauges = list(existing_gauges)

        self.setWindowTitle(f"仪表盘管理 - {device_name}")
        self.setMinimumSize(600, 400)
        self._init_ui()
        self._refresh_gauge_list()

    def _init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel(f"设备: {self._device_name}")
        title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #24292F;")
        layout.addWidget(title_label)

        # 说明
        desc_label = QLabel("管理该设备的仪表盘显示，每个仪表盘可关联一个寄存器变量。")
        desc_label.setStyleSheet("font-size: 12px; color: #57606A;")
        layout.addWidget(desc_label)

        # 仪表盘列表
        from ui.widgets import DataTable

        self._gauge_table = DataTable(columns=["标题", "关联寄存器", "范围", "单位", "操作"])
        self._gauge_table.setColumnWidth(0, 120)
        self._gauge_table.setColumnWidth(1, 150)
        self._gauge_table.setColumnWidth(2, 100)
        self._gauge_table.setColumnWidth(3, 80)
        self._gauge_table.setColumnWidth(4, 120)
        layout.addWidget(self._gauge_table)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._add_btn = PrimaryButton("+ 添加仪表盘")
        self._add_btn.clicked.connect(self._on_add_gauge)
        btn_layout.addWidget(self._add_btn)

        self._ok_btn = PrimaryButton("确定")
        self._ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._ok_btn)

        layout.addLayout(btn_layout)

    def _refresh_gauge_list(self) -> None:
        """刷新仪表盘列表"""
        self._gauge_table.setRowCount(len(self._gauges))

        for row, gauge in enumerate(self._gauges):
            # 标题
            self._gauge_table.setItem(row, 0, self._create_table_item(gauge.get("title", "")))

            # 关联寄存器
            self._gauge_table.setItem(row, 1, self._create_table_item(gauge.get("register_name", "")))

            # 范围
            range_text = f"{gauge.get('min_value', 0)} ~ {gauge.get('max_value', 100)}"
            self._gauge_table.setItem(row, 2, self._create_table_item(range_text))

            # 单位
            self._gauge_table.setItem(row, 3, self._create_table_item(gauge.get("unit", "")))

            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            edit_btn = SecondaryButton("编辑")
            edit_btn.setFixedHeight(24)
            edit_btn.clicked.connect(lambda checked, r=row: self._on_edit_gauge(r))

            del_btn = DangerButton("删除")
            del_btn.setFixedHeight(24)
            del_btn.clicked.connect(lambda checked, r=row: self._on_delete_gauge(r))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(del_btn)
            action_layout.addStretch()

            self._gauge_table.setCellWidget(row, 4, action_widget)

    def _create_table_item(self, text: str) -> Any:
        """创建表格项"""
        from PySide6.QtWidgets import QTableWidgetItem

        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _on_add_gauge(self) -> None:
        """添加仪表盘"""
        dialog = GaugeConfigDialog(self._available_registers, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            if config:
                self._gauges.append(config)
                self._refresh_gauge_list()

    def _on_edit_gauge(self, row: int) -> None:
        """编辑仪表盘"""
        if 0 <= row < len(self._gauges):
            dialog = GaugeConfigDialog(self._available_registers, self._gauges[row], parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_config()
                if config:
                    self._gauges[row] = config
                    self._refresh_gauge_list()

    def _on_delete_gauge(self, row: int) -> None:
        """删除仪表盘"""
        if 0 <= row < len(self._gauges):
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除仪表盘 '{self._gauges[row].get('title', '')}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._gauges.pop(row)
                self._refresh_gauge_list()

    def get_gauges(self) -> List[Dict[str, Any]]:
        """获取所有仪表盘配置"""
        return self._gauges


# 为了兼容性，导入 DangerButton
from ui.widgets import DangerButton
