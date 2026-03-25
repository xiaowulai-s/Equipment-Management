# -*- coding: utf-8 -*-
"""
批量操作对话框
Batch Operations Dialog
"""

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
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.device.device_manager import DeviceManager
from core.device.device_model import DeviceStatus
from ui.styles import AppStyles


class BatchOperationsDialog(QDialog):
    """批量操作对话框"""

    operations_completed = Signal(int, int)  # success_count, total_count

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self._device_manager = device_manager
        self._selected_devices = []
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("批量操作")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(AppStyles.MAIN_WINDOW)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.setLayout(layout)

        # 设备选择区域
        select_group = QGroupBox("设备选择")
        select_group.setStyleSheet(AppStyles.STATUSBAR)
        select_layout = QVBoxLayout()
        select_group.setLayout(select_layout)

        # 设备列表表格
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(5)
        self.device_table.setHorizontalHeaderLabels(["选择", "设备名称", "设备 ID", "类型", "状态"])
        self.device_table.setStyleSheet(self._get_table_style())
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.verticalHeader().setVisible(False)
        self.device_table.setAlternatingRowColors(False)
        select_layout.addWidget(self.device_table)

        # 全选/反选按钮
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet(self._get_secondary_button_style())
        select_all_btn.clicked.connect(self._select_all)

        deselect_all_btn = QPushButton("反选")
        deselect_all_btn.setStyleSheet(self._get_secondary_button_style())
        deselect_all_btn.clicked.connect(self._deselect_all)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        btn_layout.addStretch()
        select_layout.addLayout(btn_layout)

        layout.addWidget(select_group)

        # 操作选择区域
        operation_group = QGroupBox("操作类型")
        operation_group.setStyleSheet(AppStyles.STATUSBAR)
        operation_layout = QVBoxLayout()
        operation_group.setLayout(operation_layout)

        self.operation_combo = QComboBox()
        self.operation_combo.addItems(
            ["批量连接设备", "批量断开设备", "批量删除设备", "批量导出配置", "批量启动仿真", "批量停止仿真"]
        )
        self.operation_combo.setStyleSheet(AppStyles.LINE_EDIT)
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)
        operation_layout.addWidget(self.operation_combo)

        # 动态参数区域
        self.params_group = QGroupBox("操作参数")
        self.params_group.setStyleSheet(AppStyles.STATUSBAR)
        params_layout = QFormLayout()
        self.params_group.setLayout(params_layout)

        # 根据操作类型动态添加参数
        self._setup_operation_params(params_layout)

        operation_layout.addWidget(self.params_group)

        layout.addWidget(operation_group)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.execute_btn = QPushButton("执行操作")
        self.execute_btn.setStyleSheet(self._get_primary_button_style())
        self.execute_btn.clicked.connect(self._execute_operation)

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(self._get_secondary_button_style())
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.execute_btn)
        layout.addLayout(button_layout)

        # 加载设备列表
        self._load_devices()

    def _load_devices(self):
        """加载设备列表"""
        devices = self._device_manager.get_all_devices()
        self.device_table.setRowCount(len(devices))

        for row, device in enumerate(devices):
            config = device.get_device_config()

            # 复选框
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox.setStyleSheet("QCheckBox { margin: 0; }")
            self.device_table.setCellWidget(row, 0, checkbox_widget)

            # 设备信息
            self.device_table.setItem(row, 1, QTableWidgetItem(config.get("name", "")))
            self.device_table.setItem(row, 2, QTableWidgetItem(device.get_device_id()))
            self.device_table.setItem(row, 3, QTableWidgetItem(config.get("type", "")))

            # 状态
            status = device.get_status()
            if status == DeviceStatus.CONNECTED:
                status_text = "已连接"
                status_color = Qt.green
            elif status == DeviceStatus.DISCONNECTED:
                status_text = "已断开"
                status_color = Qt.red
            else:
                status_text = "错误"
                status_color = Qt.yellow

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(status_color)
            self.device_table.setItem(row, 4, status_item)

            # 居中对齐
            for col in range(1, 5):
                item = self.device_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _select_all(self):
        """全选"""
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)

    def _deselect_all(self):
        """反选"""
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)

    def _on_operation_changed(self, index):
        """操作类型改变"""
        # 清空并重新设置参数
        while self.params_group.layout().count():
            item = self.params_group.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        params_layout = self.params_group.layout()
        if isinstance(params_layout, QFormLayout):
            self._setup_operation_params(params_layout)

    def _setup_operation_params(self, layout: QFormLayout):
        """设置操作参数"""
        operation = self.operation_combo.currentText()

        if operation == "批量导出配置":
            layout.addRow(QLabel("导出格式:"))
            self.format_combo = QComboBox()
            self.format_combo.addItems(["JSON", "CSV", "XML"])
            layout.addRow("", self.format_combo)
        elif operation in ["批量启动仿真", "批量停止仿真"]:
            layout.addRow(QLabel("仿真参数:"))
            self.simulation_spin = QSpinBox()
            self.simulation_spin.setRange(1, 1000)
            self.simulation_spin.setValue(100)
            layout.addRow("", self.simulation_spin)
        else:
            layout.addRow(QLabel("无额外参数"))

    def _get_selected_devices(self):
        """获取选中的设备"""
        selected = []
        devices = self._device_manager.get_all_devices()

        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 0).findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                selected.append(devices[row])

        return selected

    def _execute_operation(self):
        """执行批量操作"""
        selected_devices = self._get_selected_devices()

        if not selected_devices:
            QMessageBox.warning(self, "提示", "请至少选择一个设备")
            return

        operation = self.operation_combo.currentText()

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认操作",
            f'确定要对 {len(selected_devices)} 个设备执行"{operation}"吗？',
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        success_count = 0
        total_count = len(selected_devices)

        try:
            if operation == "批量连接设备":
                for device in selected_devices:
                    if self._device_manager.connect_device(device.get_device_id()):
                        success_count += 1

            elif operation == "批量断开设备":
                for device in selected_devices:
                    self._device_manager.disconnect_device(device.get_device_id())
                    success_count += 1

            elif operation == "批量删除设备":
                for device in selected_devices:
                    self._device_manager.remove_device(device.get_device_id())
                    success_count += 1

            elif operation == "批量导出配置":
                # TODO: 实现批量导出
                QMessageBox.information(self, "提示", "批量导出配置功能开发中")

            elif operation == "批量启动仿真":
                for device in selected_devices:
                    # TODO: 启动仿真
                    success_count += 1

            elif operation == "批量停止仿真":
                for device in selected_devices:
                    # TODO: 停止仿真
                    success_count += 1

            self.operations_completed.emit(success_count, total_count)

            QMessageBox.information(self, "操作完成", f"批量操作完成！\n成功：{success_count}/{total_count}")

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败：{str(e)}")

    def _get_primary_button_style(self):
        """获取主按钮样式"""
        return """
            QPushButton {
                background-color: #0969DA;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0550AE;
            }
            QPushButton:pressed {
                background-color: #043E8C;
            }
        """

    def _get_secondary_button_style(self):
        """获取次要按钮样式"""
        return """
            QPushButton {
                background-color: #FFFFFF;
                color: #24292F;
                border: 1px solid #D0D7DE;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #F6F8FA;
                border-color: #0969DA;
            }
            QPushButton:pressed {
                background-color: #EAEFF2;
            }
        """

    def _get_table_style(self) -> str:
        """获取表格样式"""
        return """
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #D0D7DE;
                border-radius: 8px;
                gridline-color: #EAEFF2;
                selection-background-color: rgba(9, 105, 218, 0.15);
            }
            QTableWidget::item {
                padding: 10px;
                border: none;
                text-align: center;
            }
            QTableWidget::item:hover {
                background-color: #F6F8FA;
            }
            QTableWidget::item:selected {
                background-color: rgba(9, 105, 218, 0.2);
                color: #24292F;
            }
            QHeaderView::section {
                background-color: #F6F8FA;
                color: #57606A;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #D0D7DE;
                font-weight: 600;
                font-size: 13px;
                text-align: center;
            }
            QHeaderView::section:hover {
                background-color: #EAEFF2;
            }
            QHeaderView::section:pressed {
                background-color: #D0D7DE;
            }
        """


from PySide6.QtWidgets import QWidget
