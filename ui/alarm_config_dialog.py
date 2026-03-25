# -*- coding: utf-8 -*-
"""
报警规则配置对话框
Alarm Rule Configuration Dialog
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
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
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.utils.alarm_manager import AlarmLevel, AlarmManager, AlarmRule, AlarmType
from ui.styles import AppStyles


class AlarmRuleConfigDialog(QDialog):
    """报警规则配置对话框"""

    rules_updated = Signal()

    def __init__(self, alarm_manager: AlarmManager, parent=None):
        super().__init__(parent)
        self._alarm_manager = alarm_manager
        self._init_ui()
        self._load_rules()

    def _init_ui(self):
        self.setWindowTitle("报警规则配置")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(AppStyles.MAIN_WINDOW)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.setLayout(layout)

        # 标题
        title_label = QLabel("报警规则配置")
        title_label.setFont(QFont("Inter", 18, QFont.Bold))
        title_label.setStyleSheet("color: #24292F;")
        layout.addWidget(title_label)

        # 规则列表区域
        rules_group = QGroupBox("报警规则列表")
        rules_group.setStyleSheet(AppStyles.STATUSBAR)
        rules_layout = QVBoxLayout()
        rules_group.setLayout(rules_layout)

        # 规则表格
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(7)
        self.rules_table.setHorizontalHeaderLabels(["启用", "规则 ID", "设备 ID", "参数", "类型", "阈值", "级别"])
        self.rules_table.setStyleSheet(self._get_table_style())
        self.rules_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rules_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.rules_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.rules_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.rules_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.rules_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.rules_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rules_table.setAlternatingRowColors(False)
        rules_layout.addWidget(self.rules_table)

        # 规则操作按钮
        rule_btn_layout = QHBoxLayout()

        add_rule_btn = QPushButton("添加规则")
        add_rule_btn.setStyleSheet(self._get_primary_button_style())
        add_rule_btn.clicked.connect(self._add_rule)

        edit_rule_btn = QPushButton("编辑规则")
        edit_rule_btn.setStyleSheet(self._get_secondary_button_style())
        edit_rule_btn.clicked.connect(self._edit_rule)

        delete_rule_btn = QPushButton("删除规则")
        delete_rule_btn.setStyleSheet(self._get_primary_button_style(danger=True))
        delete_rule_btn.clicked.connect(self._delete_rule)

        rule_btn_layout.addWidget(add_rule_btn)
        rule_btn_layout.addWidget(edit_rule_btn)
        rule_btn_layout.addWidget(delete_rule_btn)
        rule_btn_layout.addStretch()
        rules_layout.addLayout(rule_btn_layout)

        layout.addWidget(rules_group)

        # 规则详情区域
        detail_group = QGroupBox("规则详情")
        detail_group.setStyleSheet(AppStyles.STATUSBAR)
        detail_layout = QVBoxLayout()
        detail_group.setLayout(detail_layout)

        # 详情表格
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(2)
        self.detail_table.setHorizontalHeaderLabels(["属性", "值"])
        self.detail_table.setStyleSheet(self._get_table_style())
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail_table.setAlternatingRowColors(False)
        detail_layout.addWidget(self.detail_table)

        layout.addWidget(detail_group)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(self._get_secondary_button_style())
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        # 连接选择信号
        self.rules_table.itemSelectionChanged.connect(self._on_rule_selected)

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

    def _get_primary_button_style(self, danger=False):
        """获取主按钮样式"""
        if danger:
            return """
                QPushButton {
                    background-color: #CF222E;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #A40E26;
                }
                QPushButton:pressed {
                    background-color: #82071E;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #0969DA;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                    min-width: 80px;
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
                padding: 8px 16px;
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

    def _load_rules(self):
        """加载规则列表"""
        self.rules_table.setRowCount(0)
        rules = self._alarm_manager.get_all_rules()

        for rule in rules:
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)

            # 启用状态
            enabled_item = QTableWidgetItem("✓" if rule.enabled else "✗")
            enabled_item.setForeground(Qt.green if rule.enabled else Qt.gray)
            self.rules_table.setItem(row, 0, enabled_item)

            # 规则 ID
            self.rules_table.setItem(row, 1, QTableWidgetItem(rule.rule_id))

            # 设备 ID
            self.rules_table.setItem(row, 2, QTableWidgetItem(rule.device_id))

            # 参数
            self.rules_table.setItem(row, 3, QTableWidgetItem(rule.parameter))

            # 类型
            type_text = {
                AlarmType.THRESHOLD_HIGH: "高阈值",
                AlarmType.THRESHOLD_LOW: "低阈值",
                AlarmType.DEVICE_OFFLINE: "设备离线",
                AlarmType.COMMUNICATION_ERROR: "通信错误",
            }.get(rule.alarm_type, str(rule.alarm_type))
            self.rules_table.setItem(row, 4, QTableWidgetItem(type_text))

            # 阈值
            threshold = ""
            if rule.alarm_type == AlarmType.THRESHOLD_HIGH:
                threshold = f"> {rule.threshold_high}"
            elif rule.alarm_type == AlarmType.THRESHOLD_LOW:
                threshold = f"< {rule.threshold_low}"
            else:
                threshold = "N/A"
            self.rules_table.setItem(row, 5, QTableWidgetItem(threshold))

            # 级别
            level_colors = {
                AlarmLevel.INFO: Qt.blue,
                AlarmLevel.WARNING: Qt.yellow,
                AlarmLevel.ERROR: Qt.red,
                AlarmLevel.CRITICAL: Qt.darkRed,
            }
            level_item = QTableWidgetItem(rule.level.name)
            level_item.setForeground(level_colors.get(rule.level, Qt.black))
            self.rules_table.setItem(row, 6, level_item)

            # 居中对齐
            for col in range(7):
                item = self.rules_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _on_rule_selected(self):
        """规则选择改变"""
        selected_rows = self.rules_table.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        rule_id = self.rules_table.item(row, 1).text()
        rule = self._alarm_manager.get_rule(rule_id)

        if rule:
            self._show_rule_details(rule)

    def _show_rule_details(self, rule: AlarmRule):
        """显示规则详情"""
        self.detail_table.setRowCount(0)

        details = [
            ("规则 ID", rule.rule_id),
            ("设备 ID", rule.device_id),
            ("参数", rule.parameter),
            ("报警类型", str(rule.alarm_type.name)),
            ("报警级别", rule.level.name),
            ("描述", rule.description),
            ("启用状态", "是" if rule.enabled else "否"),
        ]

        if rule.alarm_type == AlarmType.THRESHOLD_HIGH:
            details.append(("高阈值", str(rule.threshold_high)))
        elif rule.alarm_type == AlarmType.THRESHOLD_LOW:
            details.append(("低阈值", str(rule.threshold_low)))

        for key, value in details:
            row = self.detail_table.rowCount()
            self.detail_table.insertRow(row)
            self.detail_table.setItem(row, 0, QTableWidgetItem(key))
            self.detail_table.setItem(row, 1, QTableWidgetItem(value))

    def _add_rule(self):
        """添加规则"""
        dialog = RuleEditDialog(self._alarm_manager, self)
        if dialog.exec() == QDialog.Accepted:
            rule = dialog.get_rule()
            if rule:
                self._alarm_manager.add_rule(rule)
                self._load_rules()
                self.rules_updated.emit()
                QMessageBox.information(self, "成功", "规则添加成功！")

    def _edit_rule(self):
        """编辑规则"""
        selected_rows = self.rules_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要编辑的规则")
            return

        row = selected_rows[0].row()
        rule_id = self.rules_table.item(row, 1).text()
        rule = self._alarm_manager.get_rule(rule_id)

        if not rule:
            QMessageBox.warning(self, "错误", "规则不存在")
            return

        dialog = RuleEditDialog(self._alarm_manager, self, edit_mode=True, original_rule=rule)
        if dialog.exec() == QDialog.Accepted:
            updated_rule = dialog.get_rule()
            if updated_rule:
                self._alarm_manager.remove_rule(rule_id)
                self._alarm_manager.add_rule(updated_rule)
                self._load_rules()
                self.rules_updated.emit()
                QMessageBox.information(self, "成功", "规则更新成功！")

    def _delete_rule(self):
        """删除规则"""
        selected_rows = self.rules_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的规则")
            return

        row = selected_rows[0].row()
        rule_id = self.rules_table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除规则 {rule_id} 吗？", QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._alarm_manager.remove_rule(rule_id)
            self._load_rules()
            self.rules_updated.emit()
            QMessageBox.information(self, "成功", "规则删除成功！")


class RuleEditDialog(QDialog):
    """规则编辑对话框"""

    def __init__(self, alarm_manager: AlarmManager, parent=None, edit_mode=False, original_rule: AlarmRule = None):
        super().__init__(parent)
        self._alarm_manager = alarm_manager
        self._edit_mode = edit_mode
        self._original_rule = original_rule
        self._init_ui()

        if edit_mode and original_rule:
            self._load_rule_data()

    def _init_ui(self):
        self.setWindowTitle("编辑报警规则" if self._edit_mode else "添加报警规则")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(AppStyles.MAIN_WINDOW)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.setLayout(layout)

        # 表单区域
        form_group = QGroupBox("规则配置")
        form_group.setStyleSheet(AppStyles.STATUSBAR)
        form_layout = QFormLayout()
        form_group.setLayout(form_layout)

        # 规则 ID
        self.rule_id_edit = QLineEdit()
        self.rule_id_edit.setPlaceholderText("例如：TEMP_HIGH_001")
        self.rule_id_edit.setStyleSheet(AppStyles.LINE_EDIT)
        if self._edit_mode:
            self.rule_id_edit.setReadOnly(True)
        form_layout.addRow("规则 ID *", self.rule_id_edit)

        # 设备 ID
        self.device_id_edit = QLineEdit()
        self.device_id_edit.setPlaceholderText("设备 ID，使用 * 表示所有设备")
        self.device_id_edit.setStyleSheet(AppStyles.LINE_EDIT)
        form_layout.addRow("设备 ID", self.device_id_edit)

        # 参数
        self.parameter_edit = QLineEdit()
        self.parameter_edit.setPlaceholderText("例如：温度、压力")
        self.parameter_edit.setStyleSheet(AppStyles.LINE_EDIT)
        form_layout.addRow("监测参数 *", self.parameter_edit)

        # 报警类型
        self.type_combo = QComboBox()
        self.type_combo.addItems(["高阈值报警", "低阈值报警", "设备离线", "通信错误"])
        self.type_combo.setStyleSheet(AppStyles.LINE_EDIT)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_layout.addRow("报警类型 *", self.type_combo)

        # 阈值参数区域
        self.threshold_widget = QWidget()
        threshold_form = QFormLayout()
        self.threshold_widget.setLayout(threshold_form)

        self.high_threshold_spin = QDoubleSpinBox()
        self.high_threshold_spin.setRange(-9999, 9999)
        self.high_threshold_spin.setDecimals(2)
        self.high_threshold_spin.setStyleSheet(AppStyles.LINE_EDIT)
        threshold_form.addRow("高阈值", self.high_threshold_spin)

        self.low_threshold_spin = QDoubleSpinBox()
        self.low_threshold_spin.setRange(-9999, 9999)
        self.low_threshold_spin.setDecimals(2)
        self.low_threshold_spin.setStyleSheet(AppStyles.LINE_EDIT)
        threshold_form.addRow("低阈值", self.low_threshold_spin)

        form_layout.addRow("", self.threshold_widget)

        # 报警级别
        self.level_combo = QComboBox()
        self.level_combo.addItems(["INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setStyleSheet(AppStyles.LINE_EDIT)
        form_layout.addRow("报警级别 *", self.level_combo)

        # 描述
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("规则描述信息")
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setStyleSheet(AppStyles.LINE_EDIT)
        form_layout.addRow("描述", self.description_edit)

        # 启用状态
        self.enabled_combo = QComboBox()
        self.enabled_combo.addItems(["启用", "禁用"])
        self.enabled_combo.setStyleSheet(AppStyles.LINE_EDIT)
        form_layout.addRow("状态", self.enabled_combo)

        layout.addWidget(form_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(self._get_button_style())
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(self._get_button_style())
        save_btn.clicked.connect(self._save_rule)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)

        # 初始化阈值显示
        self._on_type_changed(0)

    def _get_button_style(self):
        """获取按钮样式"""
        return """
            QPushButton {
                background: qlineargradient(135deg, #0969DA, #0550AE);
                color: white;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(135deg, #0550AE, #043E8C);
            }
        """

    def _on_type_changed(self, index):
        """报警类型改变"""
        if index in [0, 1]:  # 阈值报警
            self.threshold_widget.setVisible(True)
            if index == 0:  # 高阈值
                self.high_threshold_spin.setVisible(True)
                self.low_threshold_spin.setVisible(False)
            else:  # 低阈值
                self.high_threshold_spin.setVisible(False)
                self.low_threshold_spin.setVisible(True)
        else:  # 非阈值报警
            self.threshold_widget.setVisible(False)

    def _load_rule_data(self):
        """加载规则数据"""
        if not self._original_rule:
            return

        rule = self._original_rule
        self.rule_id_edit.setText(rule.rule_id)
        self.device_id_edit.setText(rule.device_id)
        self.parameter_edit.setText(rule.parameter)

        # 设置类型
        type_map = {
            AlarmType.THRESHOLD_HIGH: 0,
            AlarmType.THRESHOLD_LOW: 1,
            AlarmType.DEVICE_OFFLINE: 2,
            AlarmType.COMMUNICATION_ERROR: 3,
        }
        self.type_combo.setCurrentIndex(type_map.get(rule.alarm_type, 0))

        # 设置阈值
        if rule.threshold_high is not None:
            self.high_threshold_spin.setValue(rule.threshold_high)
        if rule.threshold_low is not None:
            self.low_threshold_spin.setValue(rule.threshold_low)

        # 设置级别
        level_map = {AlarmLevel.INFO: 0, AlarmLevel.WARNING: 1, AlarmLevel.ERROR: 2, AlarmLevel.CRITICAL: 3}
        self.level_combo.setCurrentIndex(level_map.get(rule.level, 1))

        self.description_edit.setText(rule.description)
        self.enabled_combo.setCurrentIndex(0 if rule.enabled else 1)

    def _save_rule(self):
        """保存规则"""
        rule = self.get_rule()
        if rule:
            self.accept()

    def get_rule(self) -> AlarmRule:
        """获取规则"""
        rule_id = self.rule_id_edit.text().strip()
        device_id = self.device_id_edit.text().strip() or "*"
        parameter = self.parameter_edit.text().strip()

        if not rule_id:
            QMessageBox.warning(self, "错误", "规则 ID 不能为空")
            return None

        if not parameter:
            QMessageBox.warning(self, "错误", "监测参数不能为空")
            return None

        type_index = self.type_combo.currentIndex()
        alarm_type = [
            AlarmType.THRESHOLD_HIGH,
            AlarmType.THRESHOLD_LOW,
            AlarmType.DEVICE_OFFLINE,
            AlarmType.COMMUNICATION_ERROR,
        ][type_index]

        level_index = self.level_combo.currentIndex()
        alarm_level = [AlarmLevel.INFO, AlarmLevel.WARNING, AlarmLevel.ERROR, AlarmLevel.CRITICAL][level_index]

        threshold_high = self.high_threshold_spin.value() if type_index == 0 else None
        threshold_low = self.low_threshold_spin.value() if type_index == 1 else None

        description = self.description_edit.toPlainText().strip()
        enabled = self.enabled_combo.currentIndex() == 0

        return AlarmRule(
            rule_id=rule_id,
            device_id=device_id,
            parameter=parameter,
            alarm_type=alarm_type,
            threshold_high=threshold_high,
            threshold_low=threshold_low,
            level=alarm_level,
            description=description,
            enabled=enabled,
        )
