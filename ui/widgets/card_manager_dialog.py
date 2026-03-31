# -*- coding: utf-8 -*-
"""
数据卡片管理对话框
Data Card Management Dialog

用于管理设备的数据卡片配置，支持添加、编辑、删除数据卡片。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
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

from ui.widgets import DangerButton, GhostButton, LineEdit, PrimaryButton, SecondaryButton


class CardManagerDialog(QDialog):
    """
    数据卡片管理对话框
    Data Card Management Dialog
    """

    def __init__(
        self,
        device_id: str,
        device_name: str,
        available_registers: List[Dict[str, Any]],
        existing_cards: List[Dict[str, Any]],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._device_id = device_id
        self._device_name = device_name
        self._available_registers = available_registers
        self._cards = list(existing_cards)  # 复制现有卡片配置

        self.setWindowTitle(f"数据卡片管理 - {device_name}")
        self.setMinimumSize(700, 600)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel(f"管理 {self._device_name} 的数据卡片")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #24292F;")
        layout.addWidget(title_label)

        # 说明
        info_label = QLabel("数据卡片用于在实时监控页面显示设备的关键参数。")
        info_label.setStyleSheet("font-size: 13px; color: #57606A;")
        layout.addWidget(info_label)

        # 卡片列表
        cards_group = QGroupBox("数据卡片列表")
        cards_layout = QVBoxLayout(cards_group)

        # 卡片表格
        self._card_table = QTableWidget()
        self._card_table.setColumnCount(5)
        self._card_table.setHorizontalHeaderLabels(["标题", "关联寄存器", "最小值", "最大值", "操作"])
        self._card_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._card_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._card_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._card_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._card_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._card_table.verticalHeader().setVisible(False)
        self._card_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._card_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._card_table.setAlternatingRowColors(True)
        cards_layout.addWidget(self._card_table)

        # 卡片操作按钮
        card_btn_layout = QHBoxLayout()

        add_btn = PrimaryButton("+ 添加卡片")
        add_btn.clicked.connect(self._on_add_card)

        edit_btn = SecondaryButton("编辑卡片")
        edit_btn.clicked.connect(self._on_edit_card)

        delete_btn = DangerButton("删除卡片")
        delete_btn.clicked.connect(self._on_delete_card)

        move_up_btn = GhostButton("上移")
        move_up_btn.clicked.connect(self._on_move_up)

        move_down_btn = GhostButton("下移")
        move_down_btn.clicked.connect(self._on_move_down)

        card_btn_layout.addWidget(add_btn)
        card_btn_layout.addWidget(edit_btn)
        card_btn_layout.addWidget(delete_btn)
        card_btn_layout.addWidget(move_up_btn)
        card_btn_layout.addWidget(move_down_btn)
        card_btn_layout.addStretch()
        cards_layout.addLayout(card_btn_layout)

        layout.addWidget(cards_group)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = SecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)

        save_btn = PrimaryButton("保存配置")
        save_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        # 加载现有卡片
        self._refresh_card_table()

    def _refresh_card_table(self) -> None:
        """刷新卡片表格"""
        self._card_table.setRowCount(0)

        for i, card in enumerate(self._cards):
            row = self._card_table.rowCount()
            self._card_table.insertRow(row)

            # 标题
            title_item = QTableWidgetItem(card.get("title", ""))
            title_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._card_table.setItem(row, 0, title_item)

            # 关联寄存器
            register_name = card.get("register_name", "")
            register_item = QTableWidgetItem(register_name)
            register_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._card_table.setItem(row, 1, register_item)

            # 最小值
            min_item = QTableWidgetItem(str(card.get("min_value", 0)))
            min_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._card_table.setItem(row, 2, min_item)

            # 最大值
            max_item = QTableWidgetItem(str(card.get("max_value", 100)))
            max_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._card_table.setItem(row, 3, max_item)

            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(4)

            edit_btn = GhostButton("编辑")
            edit_btn.setFixedSize(60, 28)
            edit_btn.clicked.connect(lambda checked, r=row: self._on_edit_card(r))

            delete_btn = GhostButton("删除")
            delete_btn.setFixedSize(60, 28)
            delete_btn.clicked.connect(lambda checked, r=row: self._on_delete_card(r))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)

            self._card_table.setCellWidget(row, 4, action_widget)

    def _on_add_card(self) -> None:
        """添加卡片"""
        dialog = CardEditDialog(self._available_registers, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            card = dialog.get_card()
            if card:
                self._cards.append(card)
                self._refresh_card_table()

    def _on_edit_card(self, row: Optional[int] = None) -> None:
        """编辑卡片"""
        if row is None:
            # 从选中行获取
            selected_items = self._card_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "提示", "请先选择要编辑的数据卡片")
                return
            row = selected_items[0].row()

        if 0 <= row < len(self._cards):
            card = self._cards[row]
            dialog = CardEditDialog(self._available_registers, card, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_card = dialog.get_card()
                if updated_card:
                    self._cards[row] = updated_card
                    self._refresh_card_table()

    def _on_delete_card(self, row: Optional[int] = None) -> None:
        """删除卡片"""
        if row is None:
            # 从选中行获取
            selected_items = self._card_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "提示", "请先选择要删除的数据卡片")
                return
            row = selected_items[0].row()

        if 0 <= row < len(self._cards):
            card = self._cards[row]
            title = card.get("title", "")
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除数据卡片 '{title}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._cards.pop(row)
                self._refresh_card_table()

    def _on_move_up(self) -> None:
        """上移卡片"""
        selected_items = self._card_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要移动的数据卡片")
            return

        row = selected_items[0].row()
        if row > 0:
            # 交换卡片
            self._cards[row], self._cards[row - 1] = self._cards[row - 1], self._cards[row]
            self._refresh_card_table()
            # 选中上移后的行
            self._card_table.selectRow(row - 1)

    def _on_move_down(self) -> None:
        """下移卡片"""
        selected_items = self._card_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要移动的数据卡片")
            return

        row = selected_items[0].row()
        if row < len(self._cards) - 1:
            # 交换卡片
            self._cards[row], self._cards[row + 1] = self._cards[row + 1], self._cards[row]
            self._refresh_card_table()
            # 选中下移后的行
            self._card_table.selectRow(row + 1)

    def get_cards(self) -> List[Dict[str, Any]]:
        """获取所有数据卡片配置"""
        return self._cards


class CardEditDialog(QDialog):
    """
    数据卡片编辑对话框
    Data Card Edit Dialog
    """

    def __init__(
        self,
        available_registers: List[Dict[str, Any]],
        existing_card: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._available_registers = available_registers
        self._existing_card = existing_card

        self.setWindowTitle("编辑数据卡片" if existing_card else "添加数据卡片")
        self.setMinimumSize(500, 400)
        self._init_ui()

        if existing_card:
            self._load_card_data()

    def _init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 表单组
        form_group = QGroupBox("数据卡片配置")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(12)

        # 标题
        self._title_edit = LineEdit("请输入卡片标题")
        form_layout.addRow(self._create_label("卡片标题 *"), self._title_edit)

        # 关联寄存器
        register_layout = QHBoxLayout()
        self._register_combo = PrimaryButton("选择寄存器")
        self._register_combo.setFixedHeight(36)
        self._register_combo.clicked.connect(self._on_select_register)
        self._register_label = QLabel("未选择")
        self._register_label.setStyleSheet("font-size: 13px; color: #57606A;")
        register_layout.addWidget(self._register_combo)
        register_layout.addWidget(self._register_label)
        form_layout.addRow(self._create_label("关联寄存器 *"), register_layout)

        # 最小值
        self._min_value_edit = LineEdit("0.0")
        form_layout.addRow(self._create_label("最小值"), self._min_value_edit)

        # 最大值
        self._max_value_edit = LineEdit("100.0")
        form_layout.addRow(self._create_label("最大值"), self._max_value_edit)

        # 颜色
        self._color_edit = LineEdit("#2196F3")
        form_layout.addRow(self._create_label("卡片颜色"), self._color_edit)

        layout.addWidget(form_group)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = SecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)

        save_btn = PrimaryButton("保存")
        save_btn.clicked.connect(self._on_save)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        # 当前选择的寄存器名称
        self._selected_register_name = ""
        self._selected_register_address = ""

    def _create_label(self, text: str) -> QLabel:
        """创建标签"""
        label = QLabel(text)
        label.setStyleSheet("font-weight: 500; color: #24292F;")
        return label

    def _load_card_data(self) -> None:
        """加载现有卡片数据"""
        if not self._existing_card:
            return

        card = self._existing_card
        self._title_edit.setText(card.get("title", ""))

        # 加载寄存器信息
        self._selected_register_name = card.get("register_name", "")
        self._register_label.setText(self._selected_register_name)

        self._min_value_edit.setText(str(card.get("min_value", 0)))
        self._max_value_edit.setText(str(card.get("max_value", 100)))
        self._color_edit.setText(card.get("color", "#2196F3"))

    def _on_select_register(self) -> None:
        """选择寄存器"""
        # 创建寄存器选择对话框
        dialog = RegisterSelectionDialog(self._available_registers, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            register = dialog.get_selected_register()
            if register:
                self._selected_register_name = register["name"]
                self._selected_register_address = register["address"]
                self._register_label.setText(self._selected_register_name)

    def _on_save(self) -> None:
        """保存卡片"""
        title = self._title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "错误", "卡片标题不能为空")
            return

        if not self._selected_register_name:
            QMessageBox.warning(self, "错误", "请选择关联寄存器")
            return

        try:
            min_value = float(self._min_value_edit.text())
            max_value = float(self._max_value_edit.text())
        except ValueError:
            QMessageBox.warning(self, "错误", "最小值和最大值必须是数字")
            return

        if min_value >= max_value:
            QMessageBox.warning(self, "错误", "最小值必须小于最大值")
            return

        self.accept()

    def get_card(self) -> Optional[Dict[str, Any]]:
        """获取卡片配置"""
        title = self._title_edit.text().strip()

        if not title or not self._selected_register_name:
            return None

        return {
            "title": title,
            "register_name": self._selected_register_name,
            "register_address": self._selected_register_address,
            "min_value": float(self._min_value_edit.text()),
            "max_value": float(self._max_value_edit.text()),
            "color": self._color_edit.text().strip(),
        }


class RegisterSelectionDialog(QDialog):
    """
    寄存器选择对话框
    Register Selection Dialog
    """

    def __init__(
        self,
        available_registers: List[Dict[str, Any]],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._available_registers = available_registers
        self._selected_register = None

        self.setWindowTitle("选择寄存器")
        self.setMinimumSize(500, 400)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel("选择要关联的数据寄存器")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #24292F;")
        layout.addWidget(title_label)

        # 寄存器表格
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["寄存器名称", "寄存器地址"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)

        # 填充数据
        for reg in self._available_registers:
            row = table.rowCount()
            table.insertRow(row)

            name_item = QTableWidgetItem(reg.get("name", ""))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 0, name_item)

            addr_item = QTableWidgetItem(str(reg.get("address", "")))
            addr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 1, addr_item)

        table.itemDoubleClicked.connect(self._on_register_double_clicked)
        layout.addWidget(table)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = SecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)

        select_btn = PrimaryButton("选择")
        select_btn.clicked.connect(self._on_select)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(select_btn)
        layout.addLayout(btn_layout)

        self._table = table

    def _on_register_double_clicked(self, item: QTableWidgetItem) -> None:
        """双击选择寄存器"""
        row = item.row()
        self._selected_register = self._available_registers[row]
        self.accept()

    def _on_select(self) -> None:
        """点击选择按钮"""
        selected_items = self._table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择一个寄存器")
            return

        row = selected_items[0].row()
        self._selected_register = self._available_registers[row]
        self.accept()

    def get_selected_register(self) -> Optional[Dict[str, Any]]:
        """获取选中的寄存器"""
        return self._selected_register
