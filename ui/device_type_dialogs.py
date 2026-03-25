# -*- coding: utf-8 -*-
"""
设备类型管理对话框
Device Type Management Dialogs
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from core.device.device_type_manager import DeviceTypeManager
from ui.styles import AppStyles


class DeviceTypeEditDialog(QDialog):
    """设备类型编辑对话框"""

    def __init__(self, parent=None, name: str = "", code: str = "", description: str = ""):
        super().__init__(parent)
        self._is_edit_mode = bool(name)
        self.setWindowTitle("编辑设备类型" if name else "添加设备类型")
        self.setMinimumWidth(400)
        self.setStyleSheet(AppStyles.DIALOG)
        self._init_ui(name, code, description)

    def _init_ui(self, name: str, code: str, description: str):
        layout = QFormLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        name_label = QLabel("设备类型名称:")
        name_label.setStyleSheet("color: #24292F; font-weight: 500;")
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("请输入设备类型名称")
        self.name_edit.setStyleSheet(AppStyles.LINE_EDIT)
        self.name_edit.textChanged.connect(self._on_name_changed)
        layout.addRow(name_label, self.name_edit)

        code_label = QLabel("代码:")
        code_label.setStyleSheet("color: #24292F; font-weight: 500;")
        self.code_edit = QLineEdit(code)
        self.code_edit.setPlaceholderText("请输入代码")
        self.code_edit.setStyleSheet(AppStyles.LINE_EDIT)
        layout.addRow(code_label, self.code_edit)

        desc_label = QLabel("描述:")
        desc_label.setStyleSheet("color: #24292F; font-weight: 500;")
        self.desc_edit = QLineEdit(description)
        self.desc_edit.setPlaceholderText("请输入描述")
        self.desc_edit.setStyleSheet(AppStyles.LINE_EDIT)
        layout.addRow(desc_label, self.desc_edit)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setStyleSheet(AppStyles.get_button_primary_with_padding(24))
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(AppStyles.get_button_secondary_with_padding(24))
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.setSpacing(12)
        layout.addRow(btn_layout)

        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
        self.setLayout(layout)

    def _on_name_changed(self, text: str):
        """当设备类型名称改变时，自动生成描述"""
        if not self._is_edit_mode and text.strip():
            self.desc_edit.setText(f"通用{text.strip()}设备")

    def _on_ok(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入设备类型名称")
            return
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入代码")
            return
        self.accept()

    def get_type_info(self):
        return (self.name_edit.text().strip(), self.code_edit.text().strip(), self.desc_edit.text().strip())


class DeviceTypeDialog(QDialog):
    """设备类型管理对话框"""

    def __init__(self, device_type_manager: DeviceTypeManager, parent=None):
        super().__init__(parent)
        self._device_type_manager = device_type_manager
        self.setWindowTitle("设备类型管理")
        self.setMinimumWidth(500)
        self.setStyleSheet(AppStyles.DIALOG)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.type_tree = QTreeWidget()
        self.type_tree.setHeaderLabels(["设备类型名称", "代码", "描述"])
        self.type_tree.setStyleSheet(AppStyles.TREE_WIDGET)
        self.type_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.type_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.type_tree.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.type_tree.header().setDefaultAlignment(Qt.AlignCenter)
        layout.addWidget(self.type_tree)

        btn_layout = QHBoxLayout()

        self.add_type_btn = QPushButton("添加类型")
        self.add_type_btn.clicked.connect(self._add_device_type)

        self.edit_type_btn = QPushButton("编辑类型")
        self.edit_type_btn.clicked.connect(self._edit_device_type)

        self.remove_type_btn = QPushButton("删除类型")
        self.remove_type_btn.clicked.connect(self._remove_device_type)

        btn_layout.addWidget(self.add_type_btn)
        btn_layout.addWidget(self.edit_type_btn)
        btn_layout.addWidget(self.remove_type_btn)
        btn_layout.addStretch()

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self._refresh_type_list()

    def _refresh_type_list(self):
        self.type_tree.clear()
        for device_type in self._device_type_manager.get_all_device_types():
            item = QTreeWidgetItem()
            item.setText(0, device_type["name"])
            item.setText(1, device_type["code"])
            item.setText(2, device_type["description"])
            item.setTextAlignment(0, Qt.AlignCenter)
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setTextAlignment(2, Qt.AlignCenter)
            self.type_tree.addTopLevelItem(item)

    def _add_device_type(self):
        dialog = DeviceTypeEditDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, code, description = dialog.get_type_info()
            if self._device_type_manager.add_device_type(name, code, description):
                self._refresh_type_list()
            else:
                QMessageBox.warning(self, "错误", "设备类型名称或代码已存在")

    def _edit_device_type(self):
        item = self.type_tree.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要编辑的设备类型")
            return

        old_name = item.text(0)
        old_code = item.text(1)
        old_description = item.text(2)

        dialog = DeviceTypeEditDialog(self, old_name, old_code, old_description)
        if dialog.exec() == QDialog.Accepted:
            new_name, new_code, new_description = dialog.get_type_info()
            if self._device_type_manager.update_device_type(old_name, new_name, new_code, new_description):
                self._refresh_type_list()
            else:
                QMessageBox.warning(self, "错误", "设备类型名称或代码已存在")

    def _remove_device_type(self):
        item = self.type_tree.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择要删除的设备类型")
            return

        name = item.text(0)
        reply = QMessageBox.question(
            self, "确认删除", f'确定要删除设备类型"{name}"吗？', QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self._device_type_manager.remove_device_type(name):
                self._refresh_type_list()
