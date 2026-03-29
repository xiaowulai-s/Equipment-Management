# -*- coding: utf-8 -*-
"""
寄存器配置对话框
Register Configuration Dialog

重构说明: 移除所有内联样式, 使用 ui.widgets 组件库统一样式
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import Checkbox, ComboBox, DangerButton, GhostButton, LineEdit, PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    pass


class RegisterConfigDialog(QDialog):
    """寄存器配置对话框"""

    config_updated = Signal(list)  # 更新后的寄存器配置

    def __init__(
        self,
        register_map: Optional[List[Dict[str, Any]]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._register_map: List[Dict[str, Any]] = list(register_map or [])
        self._init_ui()
        self._load_registers()

    def _init_ui(self) -> None:
        self.setWindowTitle("寄存器配置")
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.setLayout(layout)

        # 标题
        title_label = QLabel("寄存器配置")
        title_label.setFont(QFont("Inter", 18, QFont.Bold))
        title_label.setStyleSheet("color: #24292F;")
        layout.addWidget(title_label)

        # 说明标签
        info_label = QLabel("提示：配置设备寄存器地址，用于读取和控制设备。每个寄存器对应一个变量。")
        info_label.setStyleSheet("color: #57606A; font-size: 12px;")
        layout.addWidget(info_label)

        # 寄存器列表区域
        registers_group = QGroupBox("寄存器列表")
        registers_layout = QVBoxLayout()
        registers_group.setLayout(registers_layout)

        # 寄存器表格
        self.register_table = QTableWidget()
        self.register_table.setColumnCount(9)
        self.register_table.setHorizontalHeaderLabels(
            ["启用", "地址", "功能码", "变量名", "数据类型", "读写", "值", "单位", "描述"]
        )
        self.register_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.register_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.register_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.register_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.register_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.register_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.register_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.register_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.register_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Stretch)
        self.register_table.verticalHeader().setVisible(False)
        self.register_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.register_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.register_table.setAlternatingRowColors(False)
        registers_layout.addWidget(self.register_table)

        # 寄存器操作按钮
        register_btn_layout = QHBoxLayout()

        add_register_btn = PrimaryButton("添加寄存器")
        add_register_btn.clicked.connect(self._add_register)

        edit_register_btn = SecondaryButton("编辑寄存器")
        edit_register_btn.clicked.connect(self._edit_register)

        delete_register_btn = DangerButton("删除寄存器")
        delete_register_btn.clicked.connect(self._delete_register)

        move_up_btn = GhostButton("上移")
        move_up_btn.clicked.connect(self._move_up)

        move_down_btn = GhostButton("下移")
        move_down_btn.clicked.connect(self._move_down)

        register_btn_layout.addWidget(add_register_btn)
        register_btn_layout.addWidget(edit_register_btn)
        register_btn_layout.addWidget(delete_register_btn)
        register_btn_layout.addWidget(move_up_btn)
        register_btn_layout.addWidget(move_down_btn)
        register_btn_layout.addStretch()
        registers_layout.addLayout(register_btn_layout)

        layout.addWidget(registers_group)

        # 快速添加区域
        quick_add_group = QGroupBox("快速添加常用寄存器")
        quick_add_layout = QHBoxLayout()
        quick_add_group.setLayout(quick_add_layout)

        quick_templates = [
            ("温度", 40001, 3, "float32", "R", "°C"),
            ("压力", 40003, 3, "float32", "R", "MPa"),
            ("流量", 40005, 3, "float32", "R", "m³/h"),
            ("液位", 40007, 3, "float32", "R", "%"),
            ("启动控制", 40009, 6, "uint16", "RW", ""),
            ("复位", 40010, 6, "uint16", "RW", ""),
        ]

        for name, addr, func, dtype, rw, unit in quick_templates:
            btn = GhostButton(f"{name} (地址{addr})")
            btn.clicked.connect(
                lambda checked, n=name, a=addr, f=func, d=dtype, r=rw, u=unit: self._quick_add_register(
                    n, a, f, d, r, u
                )
            )
            quick_add_layout.addWidget(btn)

        quick_add_layout.addStretch()
        layout.addWidget(quick_add_group)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = SecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)

        save_btn = PrimaryButton("保存配置")
        save_btn.clicked.connect(self._save_config)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)

        # 连接选择信号
        self.register_table.itemSelectionChanged.connect(self._on_register_selected)

    def _load_registers(self) -> None:
        """加载寄存器列表"""
        self.register_table.setRowCount(0)

        for reg in self._register_map:
            row = self.register_table.rowCount()
            self.register_table.insertRow(row)

            # 启用状态
            enabled = reg.get("enabled", True)
            enabled_item = QTableWidgetItem("✓" if enabled else "✗")
            enabled_item.setForeground(Qt.GlobalColor.green if enabled else Qt.GlobalColor.gray)
            self.register_table.setItem(row, 0, enabled_item)

            # 地址
            self.register_table.setItem(row, 1, QTableWidgetItem(str(reg.get("address", 0))))

            # 功能码
            func_map = {3: "读保持", 4: "读输入", 6: "写单个", 16: "写多个"}
            func_code = reg.get("function_code", 3)
            func_item = QTableWidgetItem(func_map.get(func_code, str(func_code)))
            self.register_table.setItem(row, 2, func_item)

            # 变量名
            self.register_table.setItem(row, 3, QTableWidgetItem(reg.get("name", "")))

            # 数据类型
            self.register_table.setItem(row, 4, QTableWidgetItem(reg.get("data_type", "uint16")))

            # 读写权限
            rw = reg.get("read_write", "R")
            rw_item = QTableWidgetItem("读写" if rw == "RW" else "只读")
            rw_item.setForeground(Qt.GlobalColor.blue if rw == "RW" else Qt.GlobalColor.gray)
            self.register_table.setItem(row, 5, rw_item)

            # 值
            self.register_table.setItem(row, 6, QTableWidgetItem(str(reg.get("value", ""))))

            # 单位
            self.register_table.setItem(row, 7, QTableWidgetItem(reg.get("unit", "")))

            # 描述
            self.register_table.setItem(row, 8, QTableWidgetItem(reg.get("description", "")))

            # 居中对齐
            for col in range(9):
                item = self.register_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def _on_register_selected(self) -> None:
        """寄存器选择改变"""
        pass  # 可以在这里显示详情

    def _add_register(self) -> None:
        """添加寄存器"""
        dialog = RegisterEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            register = dialog.get_register()
            if register:
                self._register_map.append(register)
                self._load_registers()

    def _edit_register(self) -> None:
        """编辑寄存器"""
        selected_rows = self.register_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的寄存器")
            return

        row = selected_rows[0].row()
        address = int(self.register_table.item(row, 1).text())

        # 查找对应的寄存器配置
        register = None
        for reg in self._register_map:
            if reg.get("address") == address:
                register = reg
                break

        if not register:
            QMessageBox.warning(self, "错误", "寄存器配置不存在")
            return

        dialog = RegisterEditDialog(self, edit_mode=True, original_register=register)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_register = dialog.get_register()
            if updated_register:
                # 更新寄存器
                for i, reg in enumerate(self._register_map):
                    if reg.get("address") == address:
                        self._register_map[i] = updated_register
                        break
                self._load_registers()

    def _delete_register(self) -> None:
        """删除寄存器"""
        selected_rows = self.register_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的寄存器")
            return

        row = selected_rows[0].row()
        address = int(self.register_table.item(row, 1).text())

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除地址 {address} 的寄存器吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._register_map = [r for r in self._register_map if r.get("address") != address]
            self._load_registers()

    def _move_up(self) -> None:
        """上移寄存器"""
        selected_rows = self.register_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要移动的寄存器")
            return

        row = selected_rows[0].row()
        if row > 0:
            # 交换寄存器
            self._register_map[row], self._register_map[row - 1] = (
                self._register_map[row - 1],
                self._register_map[row],
            )
            self._load_registers()
            # 选中上移后的行
            self.register_table.selectRow(row - 1)

    def _move_down(self) -> None:
        """下移寄存器"""
        selected_rows = self.register_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要移动的寄存器")
            return

        row = selected_rows[0].row()
        if row < len(self._register_map) - 1:
            # 交换寄存器
            self._register_map[row], self._register_map[row + 1] = (
                self._register_map[row + 1],
                self._register_map[row],
            )
            self._load_registers()
            # 选中下移后的行
            self.register_table.selectRow(row + 1)

    def _quick_add_register(
        self,
        name: str,
        address: int,
        function_code: int,
        data_type: str,
        read_write: str,
        unit: str,
    ) -> None:
        """快速添加寄存器"""
        register: Dict[str, Any] = {
            "enabled": True,
            "address": address,
            "function_code": function_code,
            "name": name,
            "data_type": data_type,
            "read_write": read_write,
            "value": 0,
            "unit": unit,
            "description": f"快速添加的{name}寄存器",
        }
        self._register_map.append(register)
        self._load_registers()

    def _save_config(self) -> None:
        """保存配置"""
        self.config_updated.emit(self._register_map)
        self.accept()

    def get_register_map(self) -> List[Dict[str, Any]]:
        """获取寄存器映射"""
        return self._register_map


class RegisterEditDialog(QDialog):
    """寄存器编辑对话框"""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        edit_mode: bool = False,
        original_register: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        self._edit_mode = edit_mode
        self._original_register = original_register
        self._init_ui()

        if edit_mode and original_register:
            self._load_register_data()

    def _init_ui(self) -> None:
        self.setWindowTitle("编辑寄存器" if self._edit_mode else "添加寄存器")
        self.setMinimumSize(500, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.setLayout(layout)

        # 表单区域
        form_group = QGroupBox("寄存器配置")
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_group.setLayout(form_layout)

        # 启用状态
        self.enabled_check = Checkbox("启用此寄存器")
        form_layout.addRow("", self.enabled_check)

        # 地址
        self.address_spin = QSpinBox()
        self.address_spin.setRange(0, 65535)
        self.address_spin.setValue(40001)
        form_layout.addRow(self._label("寄存器地址 *"), self.address_spin)

        # 功能码
        self.function_code_combo = ComboBox()
        self.function_code_combo.addItem("03 - 读保持寄存器", 3)
        self.function_code_combo.addItem("04 - 读输入寄存器", 4)
        self.function_code_combo.addItem("06 - 写单个寄存器", 6)
        self.function_code_combo.addItem("10 - 写多个寄存器", 16)
        form_layout.addRow(self._label("功能码 *"), self.function_code_combo)

        # 变量名
        self.name_edit = LineEdit("例如：温度、压力、启动控制")
        form_layout.addRow(self._label("变量名 *"), self.name_edit)

        # 数据类型
        self.data_type_combo = ComboBox()
        self.data_type_combo.addItems(["uint16", "int16", "uint32", "int32", "float32", "float64", "string", "bool"])
        form_layout.addRow(self._label("数据类型 *"), self.data_type_combo)

        # 读写权限
        self.read_write_combo = ComboBox()
        self.read_write_combo.addItem("只读 (R)", "R")
        self.read_write_combo.addItem("读写 (RW)", "RW")
        form_layout.addRow(self._label("读写权限 *"), self.read_write_combo)

        # 缩放因子
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(-9999, 9999)
        self.scale_spin.setDecimals(4)
        self.scale_spin.setValue(1.0)
        form_layout.addRow(self._label("缩放因子"), self.scale_spin)

        # 单位
        self.unit_edit = LineEdit("例如：°C、MPa、m³/h")
        form_layout.addRow(self._label("单位"), self.unit_edit)

        # 初始值
        self.initial_value_spin = QDoubleSpinBox()
        self.initial_value_spin.setRange(-999999, 999999)
        self.initial_value_spin.setDecimals(2)
        self.initial_value_spin.setValue(0)
        form_layout.addRow(self._label("初始值"), self.initial_value_spin)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("寄存器描述信息")
        self.description_edit.setMaximumHeight(80)
        form_layout.addRow(self._label("描述"), self.description_edit)

        layout.addWidget(form_group)

        # 报警配置区域
        alarm_group = QGroupBox("报警配置")
        alarm_layout = QFormLayout()
        alarm_layout.setSpacing(12)
        alarm_group.setLayout(alarm_layout)

        # 启用报警
        self.alarm_enabled_check = Checkbox("启用报警功能")
        alarm_layout.addRow("", self.alarm_enabled_check)

        # 高高报警阈值 (HH - 最高级别)
        self.high_high_threshold_spin = QDoubleSpinBox()
        self.high_high_threshold_spin.setRange(-999999, 999999)
        self.high_high_threshold_spin.setDecimals(2)
        self.high_high_threshold_spin.setValue(0)
        self.high_high_threshold_spin.setEnabled(False)
        self.high_high_threshold_spin.setSpecialValueText("禁用")
        alarm_layout.addRow(self._label("高高报警阈值 (HH)"), self.high_high_threshold_spin)

        # 高报警阈值 (H)
        self.high_threshold_spin = QDoubleSpinBox()
        self.high_threshold_spin.setRange(-999999, 999999)
        self.high_threshold_spin.setDecimals(2)
        self.high_threshold_spin.setValue(0)
        self.high_threshold_spin.setEnabled(False)
        self.high_threshold_spin.setSpecialValueText("禁用")
        alarm_layout.addRow(self._label("高报警阈值 (H)"), self.high_threshold_spin)

        # 低报警阈值 (L)
        self.low_threshold_spin = QDoubleSpinBox()
        self.low_threshold_spin.setRange(-999999, 999999)
        self.low_threshold_spin.setDecimals(2)
        self.low_threshold_spin.setValue(0)
        self.low_threshold_spin.setEnabled(False)
        self.low_threshold_spin.setSpecialValueText("禁用")
        alarm_layout.addRow(self._label("低报警阈值 (L)"), self.low_threshold_spin)

        # 低低报警阈值 (LL - 最低级别)
        self.low_low_threshold_spin = QDoubleSpinBox()
        self.low_low_threshold_spin.setRange(-999999, 999999)
        self.low_low_threshold_spin.setDecimals(2)
        self.low_low_threshold_spin.setValue(0)
        self.low_low_threshold_spin.setEnabled(False)
        self.low_low_threshold_spin.setSpecialValueText("禁用")
        alarm_layout.addRow(self._label("低低报警阈值 (LL)"), self.low_low_threshold_spin)

        # 死区
        self.deadband_spin = QDoubleSpinBox()
        self.deadband_spin.setRange(0, 1000)
        self.deadband_spin.setDecimals(2)
        self.deadband_spin.setValue(0.5)
        self.deadband_spin.setEnabled(False)
        deadband_label = QLabel("死区 (阈值抖动范围)")
        deadband_label.setToolTip("避免在阈值附近频繁触发/清除报警")
        alarm_layout.addRow(deadband_label, self.deadband_spin)

        # 报警说明
        alarm_info = QLabel("说明: HH > H > L > LL，设为0表示禁用该级别报警")
        alarm_info.setStyleSheet("color: #57606A; font-size: 11px; padding: 5px;")
        alarm_layout.addRow(alarm_info)

        layout.addWidget(alarm_group)

        # 连接报警启用信号
        self.alarm_enabled_check.toggled.connect(self._on_alarm_toggled)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = SecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)

        save_btn = PrimaryButton("保存")
        save_btn.clicked.connect(self._save_register)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)

    @staticmethod
    def _label(text: str) -> QLabel:
        """创建标签"""
        label = QLabel(text)
        label.setStyleSheet("color: #24292F; font-weight: 500;")
        return label

    def _on_alarm_toggled(self, checked: bool) -> None:
        """报警启用状态改变"""
        self.high_high_threshold_spin.setEnabled(checked)
        self.high_threshold_spin.setEnabled(checked)
        self.low_threshold_spin.setEnabled(checked)
        self.low_low_threshold_spin.setEnabled(checked)
        self.deadband_spin.setEnabled(checked)

    def _load_register_data(self) -> None:
        """加载寄存器数据"""
        if not self._original_register:
            return

        reg = self._original_register
        self.enabled_check.setChecked(reg.get("enabled", True))
        self.address_spin.setValue(reg.get("address", 0))

        # 设置功能码
        func_code = reg.get("function_code", 3)
        for i in range(self.function_code_combo.count()):
            if self.function_code_combo.itemData(i) == func_code:
                self.function_code_combo.setCurrentIndex(i)
                break

        self.name_edit.setText(reg.get("name", ""))
        self.data_type_combo.setCurrentText(reg.get("data_type", "uint16"))

        # 设置读写权限
        rw = reg.get("read_write", "R")
        if rw == "RW":
            self.read_write_combo.setCurrentIndex(1)

        self.scale_spin.setValue(reg.get("scale", 1.0))
        self.unit_edit.setText(reg.get("unit", ""))
        self.initial_value_spin.setValue(reg.get("initial_value", 0))
        self.description_edit.setText(reg.get("description", ""))

        # 加载报警配置
        alarm_config = reg.get("alarm_config")
        if alarm_config:
            self.alarm_enabled_check.setChecked(alarm_config.get("enabled", False))

            # 使用0表示禁用，非0值表示启用
            self.high_high_threshold_spin.setValue(alarm_config.get("high_high", 0))
            self.high_threshold_spin.setValue(alarm_config.get("high", 0))
            self.low_threshold_spin.setValue(alarm_config.get("low", 0))
            self.low_low_threshold_spin.setValue(alarm_config.get("low_low", 0))
            self.deadband_spin.setValue(alarm_config.get("deadband", 0.5))
        else:
            self.alarm_enabled_check.setChecked(False)

    def _save_register(self) -> None:
        """保存寄存器"""
        register = self.get_register()
        if register:
            self.accept()

    def get_register(self) -> Optional[Dict[str, Any]]:
        """获取寄存器配置"""
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "错误", "变量名不能为空")
            return None

        function_code = self.function_code_combo.currentData()
        data_type = self.data_type_combo.currentText()
        read_write = self.read_write_combo.currentData()

        # 构建报警配置 (仅在启用时返回)
        alarm_config = None
        if self.alarm_enabled_check.isChecked():
            alarm_config = {
                "enabled": True,
                "high_high": (
                    self.high_high_threshold_spin.value() if self.high_high_threshold_spin.value() != 0 else None
                ),
                "high": self.high_threshold_spin.value() if self.high_threshold_spin.value() != 0 else None,
                "low": self.low_threshold_spin.value() if self.low_threshold_spin.value() != 0 else None,
                "low_low": self.low_low_threshold_spin.value() if self.low_low_threshold_spin.value() != 0 else None,
                "deadband": self.deadband_spin.value(),
            }

        return {
            "enabled": self.enabled_check.isChecked(),
            "address": self.address_spin.value(),
            "function_code": function_code,
            "name": name,
            "data_type": data_type,
            "read_write": read_write,
            "scale": self.scale_spin.value(),
            "unit": self.unit_edit.text().strip(),
            "initial_value": self.initial_value_spin.value(),
            "description": self.description_edit.toPlainText().strip(),
            "alarm_config": alarm_config,
        }
