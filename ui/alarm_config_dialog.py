# -*- coding: utf-8 -*-
"""Alarm rule configuration dialog."""

from __future__ import annotations

import logging
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.utils.alarm_manager import AlarmLevel, AlarmManager, AlarmRule, AlarmType
from ui.widgets import (
    Checkbox,
    ComboBox,
    DangerButton,
    DataTable,
    GhostButton,
    LineEdit,
    PrimaryButton,
    SecondaryButton,
    SuccessButton,
)

logger = logging.getLogger(__name__)


class _RuleFormWidget(QWidget):
    """Form widget for creating / editing a single alarm rule."""

    # Emitted after the user clicks "save" with valid data.
    rule_saved = None  # replaced by Signal in __init__

    ALARM_TYPE_LABELS = {
        AlarmType.THRESHOLD_HIGH: "高阈值报警",
        AlarmType.THRESHOLD_LOW: "低阈值报警",
        AlarmType.DEVICE_OFFLINE: "设备离线",
        AlarmType.COMMUNICATION_ERROR: "通信错误",
        AlarmType.CUSTOM: "自定义",
    }

    ALARM_LEVEL_LABELS = {
        AlarmLevel.INFO: "信息 (0)",
        AlarmLevel.WARNING: "警告 (1)",
        AlarmLevel.ERROR: "错误 (2)",
        AlarmLevel.CRITICAL: "严重 (3)",
    }

    def __init__(
        self,
        alarm_manager: AlarmManager,
        device_names: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        from PySide6.QtCore import Signal

        _RuleFormWidget.rule_saved = Signal(dict)

        self._alarm_manager = alarm_manager
        self._device_names = device_names or {}
        self._editing_rule_id: Optional[str] = None

        self._build_ui()

    # ── UI construction ──────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # --- basic fields group ---
        basic_group = QGroupBox("基本信息")
        basic_group.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        form = QFormLayout(basic_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)
        form.setContentsMargins(16, 16, 16, 16)

        self._rule_id_edit = LineEdit("自动生成")
        self._rule_id_edit.setToolTip("规则唯一标识，留空自动生成")
        form.addRow("规则 ID:", self._rule_id_edit)

        self._device_combo = ComboBox()
        self._device_combo.setMinimumWidth(200)
        self._device_combo.addItem("* (所有设备)", userData="*")
        for dev_id, dev_name in self._device_names.items():
            self._device_combo.addItem(f"{dev_name} ({dev_id})", userData=dev_id)
        form.addRow("设备:", self._device_combo)

        self._parameter_edit = LineEdit("如 Temperature")
        self._parameter_edit.setToolTip("监测参数名称")
        form.addRow("参数:", self._parameter_edit)

        self._alarm_type_combo = ComboBox()
        for at in AlarmType:
            self._alarm_type_combo.addItem(self.ALARM_TYPE_LABELS[at], userData=at)
        self._alarm_type_combo.currentIndexChanged.connect(self._on_alarm_type_changed)
        form.addRow("报警类型:", self._alarm_type_combo)

        self._level_combo = ComboBox()
        for al in AlarmLevel:
            self._level_combo.addItem(self.ALARM_LEVEL_LABELS[al], userData=al)
        self._level_combo.setCurrentIndex(1)  # default WARNING
        form.addRow("报警级别:", self._level_combo)

        layout.addWidget(basic_group)

        # --- threshold fields group ---
        threshold_group = QGroupBox("阈值设置")
        threshold_group.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        threshold_layout = QGridLayout(threshold_group)
        threshold_layout.setContentsMargins(16, 16, 16, 16)
        threshold_layout.setSpacing(10)

        threshold_layout.addWidget(QLabel("高阈值:"), 0, 0)
        self._threshold_high_edit = LineEdit("")
        self._threshold_high_edit.setToolTip("超过此值触发高阈值报警")
        threshold_layout.addWidget(self._threshold_high_edit, 0, 1)

        threshold_layout.addWidget(QLabel("低阈值:"), 1, 0)
        self._threshold_low_edit = LineEdit("")
        self._threshold_low_edit.setToolTip("低于此值触发低阈值报警")
        threshold_layout.addWidget(self._threshold_low_edit, 1, 1)

        layout.addWidget(threshold_group)

        # --- extra fields group ---
        extra_group = QGroupBox("其他")
        extra_group.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        extra_layout = QVBoxLayout(extra_group)
        extra_layout.setContentsMargins(16, 16, 16, 16)
        extra_layout.setSpacing(10)

        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("描述:"))
        self._description_edit = LineEdit("可选描述信息")
        self._description_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        desc_row.addWidget(self._description_edit)
        extra_layout.addLayout(desc_row)

        self._enabled_checkbox = Checkbox("启用此规则")
        self._enabled_checkbox.setChecked(True)
        extra_layout.addWidget(self._enabled_checkbox)

        layout.addWidget(extra_group)

        # --- action buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self._save_btn = SuccessButton("保存规则")
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        self._cancel_btn = SecondaryButton("取消")
        self._cancel_btn.clicked.connect(self._reset_form)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    # ── Public helpers ───────────────────────────────────────

    def reset(self) -> None:
        """Clear the form for a new rule."""
        self._reset_form()

    def edit_rule(self, rule: AlarmRule) -> None:
        """Populate the form from an existing *rule*."""
        self._editing_rule_id = rule.rule_id
        self._rule_id_edit.setText(rule.rule_id)
        self._rule_id_edit.setEnabled(False)

        # device
        idx = self._device_combo.findData(rule.device_id)
        if idx >= 0:
            self._device_combo.setCurrentIndex(idx)
        else:
            self._device_combo.setCurrentText(rule.device_id)

        self._parameter_edit.setText(rule.parameter)

        idx = self._device_combo.findData(rule.alarm_type)
        if idx >= 0:
            self._alarm_type_combo.setCurrentIndex(idx)

        idx = self._level_combo.findData(rule.level)
        if idx >= 0:
            self._level_combo.setCurrentIndex(idx)

        self._threshold_high_edit.setText(str(rule.threshold_high) if rule.threshold_high is not None else "")
        self._threshold_low_edit.setText(str(rule.threshold_low) if rule.threshold_low is not None else "")
        self._description_edit.setText(rule.description)
        self._enabled_checkbox.setChecked(rule.enabled)

    # ── Slots ────────────────────────────────────────────────

    def _on_alarm_type_changed(self, _index: int) -> None:
        at = self._alarm_type_combo.currentData()
        if at == AlarmType.THRESHOLD_HIGH:
            self._threshold_high_edit.setEnabled(True)
            self._threshold_low_edit.setEnabled(False)
            self._threshold_low_edit.clear()
        elif at == AlarmType.THRESHOLD_LOW:
            self._threshold_high_edit.setEnabled(False)
            self._threshold_high_edit.clear()
            self._threshold_low_edit.setEnabled(True)
        else:
            self._threshold_high_edit.setEnabled(False)
            self._threshold_low_edit.setEnabled(False)

    def _on_save(self) -> None:
        rule_id = self._rule_id_edit.text().strip()
        device_id = self._device_combo.currentData()
        parameter = self._parameter_edit.text().strip()
        alarm_type = self._alarm_type_combo.currentData()
        level = self._level_combo.currentData()

        # Validation
        if not parameter:
            QMessageBox.warning(self, "输入错误", "参数名称不能为空。")
            return

        threshold_high: Optional[float] = None
        threshold_low: Optional[float] = None

        if alarm_type == AlarmType.THRESHOLD_HIGH:
            th_text = self._threshold_high_edit.text().strip()
            if not th_text:
                QMessageBox.warning(self, "输入错误", "高阈值报警需要设置高阈值。")
                return
            try:
                threshold_high = float(th_text)
            except ValueError:
                QMessageBox.warning(self, "输入错误", "高阈值必须是数字。")
                return

        elif alarm_type == AlarmType.THRESHOLD_LOW:
            tl_text = self._threshold_low_edit.text().strip()
            if not tl_text:
                QMessageBox.warning(self, "输入错误", "低阈值报警需要设置低阈值。")
                return
            try:
                threshold_low = float(tl_text)
            except ValueError:
                QMessageBox.warning(self, "输入错误", "低阈值必须是数字。")
                return

        description = self._description_edit.text().strip()
        enabled = self._enabled_checkbox.isChecked()

        # Build AlarmRule
        if not rule_id:
            import uuid

            rule_id = uuid.uuid4().hex[:8].upper()

        rule = AlarmRule(
            rule_id=rule_id,
            device_id=device_id,
            parameter=parameter,
            alarm_type=alarm_type,
            threshold_high=threshold_high,
            threshold_low=threshold_low,
            level=level,
            enabled=enabled,
            description=description,
        )

        if self._editing_rule_id and self._editing_rule_id != rule_id:
            # Remove the old rule first
            self._alarm_manager.remove_rule(self._editing_rule_id)

        added = self._alarm_manager.add_rule(rule)
        if added:
            logger.info("报警规则已保存: %s", rule_id)
            self.rule_saved.emit(rule_id)
            self._reset_form()
        else:
            # Rule ID collision – try updating
            self._alarm_manager._rules[rule_id] = rule
            logger.info("报警规则已更新: %s", rule_id)
            self.rule_saved.emit(rule_id)
            self._reset_form()

    def _reset_form(self) -> None:
        self._editing_rule_id = None
        self._rule_id_edit.clear()
        self._rule_id_edit.setEnabled(True)
        self._device_combo.setCurrentIndex(0)
        self._parameter_edit.clear()
        self._alarm_type_combo.setCurrentIndex(0)
        self._level_combo.setCurrentIndex(1)
        self._threshold_high_edit.clear()
        self._threshold_low_edit.clear()
        self._description_edit.clear()
        self._enabled_checkbox.setChecked(True)


class AlarmConfigDialog(QDialog):
    """Dialog for managing alarm rules.

    Provides:
    - A table listing all current (runtime) alarm rules
    - A form to add / edit / delete rules
    """

    LEVEL_TEXT = {
        AlarmLevel.INFO: "信息",
        AlarmLevel.WARNING: "警告",
        AlarmLevel.ERROR: "错误",
        AlarmLevel.CRITICAL: "严重",
    }

    LEVEL_COLOR = {
        AlarmLevel.INFO: "#2196F3",
        AlarmLevel.WARNING: "#FFC107",
        AlarmLevel.ERROR: "#FF9800",
        AlarmLevel.CRITICAL: "#F44336",
    }

    TYPE_TEXT = {
        AlarmType.THRESHOLD_HIGH: "高阈值",
        AlarmType.THRESHOLD_LOW: "低阈值",
        AlarmType.DEVICE_OFFLINE: "设备离线",
        AlarmType.COMMUNICATION_ERROR: "通信错误",
        AlarmType.CUSTOM: "自定义",
    }

    def __init__(
        self,
        alarm_manager: AlarmManager,
        device_manager=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._alarm_manager = alarm_manager
        self._device_manager = device_manager

        self.setWindowTitle("报警规则配置")
        self.setMinimumSize(960, 640)
        self.resize(1050, 700)

        self._build_ui()
        self._refresh_table()

    # ── UI construction ──────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # Title
        title = QLabel("报警规则配置")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #1F2937;")
        root.addWidget(title)

        subtitle = QLabel("管理运行时报警规则：添加、编辑、启用/禁用、删除。")
        subtitle.setStyleSheet("color: #6B7280; font-size: 13px;")
        root.addWidget(subtitle)

        # Table
        columns = [
            "规则 ID",
            "设备",
            "参数",
            "报警类型",
            "报警级别",
            "高阈值",
            "低阈值",
            "描述",
            "状态",
            "操作",
        ]
        self._table = DataTable(columns=columns)
        self._table.setSelectionBehavior(DataTable.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        for i in range(len(columns)):
            if i >= 8:
                header.setSectionResizeMode(i, header.ResizeMode.Fixed)
                self._table.setColumnWidth(i, 120)
            else:
                header.setSectionResizeMode(i, header.ResizeMode.Stretch)
        self._table.horizontalHeader().setStretchLastSection(False)

        root.addWidget(self._table, 1)

        # Bottom: count label + action buttons
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self._count_label = QLabel("共 0 条规则")
        self._count_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        bottom.addWidget(self._count_label)
        bottom.addStretch()

        self._add_btn = SuccessButton("+ 添加规则")
        self._add_btn.setMinimumHeight(34)
        self._add_btn.clicked.connect(self._on_add_rule)
        bottom.addWidget(self._add_btn)

        self._delete_btn = DangerButton("删除选中")
        self._delete_btn.setMinimumHeight(34)
        self._delete_btn.clicked.connect(self._on_delete_selected)
        bottom.addWidget(self._delete_btn)

        self._close_btn = PrimaryButton("关闭")
        self._close_btn.setMinimumHeight(34)
        self._close_btn.clicked.connect(self.accept)
        bottom.addWidget(self._close_btn)

        root.addLayout(bottom)

    # ── Table refresh ────────────────────────────────────────

    def _refresh_table(self) -> None:
        rules = self._alarm_manager.get_all_rules()
        self._table.setRowCount(len(rules))

        for row, rule in enumerate(rules):
            self._populate_row(row, rule)

        self._table.resizeColumnsToContents()
        self._count_label.setText(f"共 {len(rules)} 条规则")

    def _populate_row(self, row: int, rule: AlarmRule) -> None:
        from PySide6.QtWidgets import QTableWidgetItem

        def _item(text: str, alignment: int = Qt.AlignmentFlag.AlignCenter) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setTextAlignment(alignment)
            return item

        self._table.setItem(row, 0, _item(rule.rule_id))

        # device column
        device_text = rule.device_id if rule.device_id == "*" else rule.device_id
        self._table.setItem(row, 1, _item(device_text))

        self._table.setItem(row, 2, _item(rule.parameter))
        self._table.setItem(row, 3, _item(self.TYPE_TEXT.get(rule.alarm_type, str(rule.alarm_type))))

        level_text = self.LEVEL_TEXT.get(rule.level, str(rule.level))
        level_item = _item(level_text)
        color = self.LEVEL_COLOR.get(rule.level, "#6B7280")
        level_item.setForeground(color)
        self._table.setItem(row, 4, level_item)

        self._table.setItem(row, 5, _item(str(rule.threshold_high) if rule.threshold_high is not None else "-"))
        self._table.setItem(row, 6, _item(str(rule.threshold_low) if rule.threshold_low is not None else "-"))
        self._table.setItem(row, 7, _item(rule.description, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))

        # status column: enable/disable toggle button
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(4, 4, 4, 4)
        status_layout.setSpacing(4)

        toggle_btn = SuccessButton("启用" if not rule.enabled else "已启用")
        toggle_btn.setFixedHeight(28)
        toggle_btn.setMinimumWidth(64)
        if rule.enabled:
            toggle_btn.setStyleSheet(
                "QPushButton { background: #4CAF50; color: white; border: none;"
                " border-radius: 4px; font-size: 12px; font-weight: 500; }"
                "QPushButton:hover { background: #43A047; }"
            )
        else:
            toggle_btn.setStyleSheet(
                "QPushButton { background: #F3F4F6; color: #6B7280; border: 1px solid #D1D5DB;"
                " border-radius: 4px; font-size: 12px; font-weight: 500; }"
                "QPushButton:hover { background: #E5E7EB; }"
            )

        toggle_btn.clicked.connect(lambda checked, rid=rule.rule_id, en=rule.enabled: self._toggle_rule(rid, en))
        status_layout.addWidget(toggle_btn)

        self._table.setCellWidget(row, 8, status_widget)

        # action column: edit + delete buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 4, 4, 4)
        action_layout.setSpacing(4)

        edit_btn = GhostButton("编辑")
        edit_btn.setFixedHeight(28)
        edit_btn.clicked.connect(lambda checked, rid=rule.rule_id: self._on_edit_rule(rid))
        action_layout.addWidget(edit_btn)

        del_btn = DangerButton("删除")
        del_btn.setFixedHeight(28)
        del_btn.setMinimumWidth(52)
        del_btn.clicked.connect(lambda checked, rid=rule.rule_id: self._on_delete_rule(rid))
        action_layout.addWidget(del_btn)

        self._table.setCellWidget(row, 9, action_widget)

    # ── Actions ──────────────────────────────────────────────

    def _on_add_rule(self) -> None:
        """Open a small dialog to add a new rule."""
        device_names: Dict[str, str] = {}
        if self._device_manager is not None:
            for dev_info in self._device_manager.get_all_devices():
                cfg = dev_info.get("config", {})
                device_names[dev_info["device_id"]] = cfg.get("name", dev_info["device_id"])

        add_dlg = _AddRuleDialog(self._alarm_manager, device_names, self)
        if add_dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_table()

    def _on_edit_rule(self, rule_id: str) -> None:
        """Open a small dialog to edit an existing rule."""
        rule = self._alarm_manager.get_rule(rule_id)
        if rule is None:
            QMessageBox.warning(self, "错误", f"规则 {rule_id} 不存在。")
            return

        device_names: Dict[str, str] = {}
        if self._device_manager is not None:
            for dev_info in self._device_manager.get_all_devices():
                cfg = dev_info.get("config", {})
                device_names[dev_info["device_id"]] = cfg.get("name", dev_info["device_id"])

        edit_dlg = _AddRuleDialog(self._alarm_manager, device_names, self, rule)
        if edit_dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_table()

    def _on_delete_rule(self, rule_id: str) -> None:
        reply = QMessageBox.question(
            self,
            "确认删除",
            f'确定要删除报警规则 "{rule_id}" 吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._alarm_manager.remove_rule(rule_id)
            logger.info("报警规则已删除: %s", rule_id)
            self._refresh_table()

    def _on_delete_selected(self) -> None:
        selected = self._table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要删除的规则。")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected)} 条规则吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for index in reversed(selected):
                row = index.row()
                item = self._table.item(row, 0)
                if item:
                    self._alarm_manager.remove_rule(item.text())
            self._refresh_table()

    def _toggle_rule(self, rule_id: str, current_enabled: bool) -> None:
        self._alarm_manager.enable_rule(rule_id, not current_enabled)
        self._refresh_table()


class _AddRuleDialog(QDialog):
    """Modal dialog for adding or editing a single alarm rule."""

    ALARM_TYPE_LABELS = {
        AlarmType.THRESHOLD_HIGH: "高阈值报警",
        AlarmType.THRESHOLD_LOW: "低阈值报警",
        AlarmType.DEVICE_OFFLINE: "设备离线",
        AlarmType.COMMUNICATION_ERROR: "通信错误",
        AlarmType.CUSTOM: "自定义",
    }

    ALARM_LEVEL_LABELS = {
        AlarmLevel.INFO: "信息 (0)",
        AlarmLevel.WARNING: "警告 (1)",
        AlarmLevel.ERROR: "错误 (2)",
        AlarmLevel.CRITICAL: "严重 (3)",
    }

    def __init__(
        self,
        alarm_manager: AlarmManager,
        device_names: Dict[str, str],
        parent: Optional[QWidget] = None,
        edit_rule: Optional[AlarmRule] = None,
    ) -> None:
        super().__init__(parent)
        self._alarm_manager = alarm_manager
        self._edit_rule = edit_rule
        self._device_names = device_names

        is_edit = edit_rule is not None
        self.setWindowTitle("编辑报警规则" if is_edit else "添加报警规则")
        self.setMinimumWidth(520)
        self.setFixedHeight(580)

        self._build_ui()
        if edit_rule:
            self._populate(edit_rule)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(16)

        # Title
        is_edit = self._edit_rule is not None
        title = QLabel("编辑报警规则" if is_edit else "添加报警规则")
        title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #1F2937;")
        root.addWidget(title)

        # Form
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        self._rule_id_edit = LineEdit("留空自动生成")
        if self._edit_rule:
            self._rule_id_edit.setEnabled(False)
        form.addRow("规则 ID:", self._rule_id_edit)

        self._device_combo = ComboBox()
        self._device_combo.addItem("* (所有设备)", userData="*")
        for dev_id, dev_name in self._device_names.items():
            self._device_combo.addItem(f"{dev_name} ({dev_id})", userData=dev_id)
        form.addRow("设备:", self._device_combo)

        self._parameter_edit = LineEdit("如 Temperature")
        form.addRow("参数:", self._parameter_edit)

        self._alarm_type_combo = ComboBox()
        for at in AlarmType:
            self._alarm_type_combo.addItem(self.ALARM_TYPE_LABELS[at], userData=at)
        self._alarm_type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("报警类型:", self._alarm_type_combo)

        self._level_combo = ComboBox()
        for al in AlarmLevel:
            self._level_combo.addItem(self.ALARM_LEVEL_LABELS[al], userData=al)
        self._level_combo.setCurrentIndex(1)
        form.addRow("报警级别:", self._level_combo)

        self._threshold_high_edit = LineEdit("")
        self._threshold_high_edit.setToolTip("超过此值触发报警")
        form.addRow("高阈值:", self._threshold_high_edit)

        self._threshold_low_edit = LineEdit("")
        self._threshold_low_edit.setToolTip("低于此值触发报警")
        form.addRow("低阈值:", self._threshold_low_edit)

        self._description_edit = LineEdit("可选描述")
        form.addRow("描述:", self._description_edit)

        self._enabled_cb = Checkbox("启用此规则")
        self._enabled_cb.setChecked(True)
        form.addRow("", self._enabled_cb)

        root.addLayout(form)
        root.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = SecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._save_btn = SuccessButton("保存")
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        root.addLayout(btn_layout)

    def _populate(self, rule: AlarmRule) -> None:
        self._rule_id_edit.setText(rule.rule_id)
        idx = self._device_combo.findData(rule.device_id)
        if idx >= 0:
            self._device_combo.setCurrentIndex(idx)
        self._parameter_edit.setText(rule.parameter)
        idx = self._alarm_type_combo.findData(rule.alarm_type)
        if idx >= 0:
            self._alarm_type_combo.setCurrentIndex(idx)
        idx = self._level_combo.findData(rule.level)
        if idx >= 0:
            self._level_combo.setCurrentIndex(idx)
        if rule.threshold_high is not None:
            self._threshold_high_edit.setText(str(rule.threshold_high))
        if rule.threshold_low is not None:
            self._threshold_low_edit.setText(str(rule.threshold_low))
        self._description_edit.setText(rule.description)
        self._enabled_cb.setChecked(rule.enabled)

    def _on_type_changed(self, _index: int) -> None:
        at = self._alarm_type_combo.currentData()
        if at == AlarmType.THRESHOLD_HIGH:
            self._threshold_high_edit.setEnabled(True)
            self._threshold_low_edit.setEnabled(False)
            self._threshold_low_edit.clear()
        elif at == AlarmType.THRESHOLD_LOW:
            self._threshold_high_edit.setEnabled(False)
            self._threshold_high_edit.clear()
            self._threshold_low_edit.setEnabled(True)
        else:
            self._threshold_high_edit.setEnabled(False)
            self._threshold_low_edit.setEnabled(False)

    def _on_save(self) -> None:
        rule_id = self._rule_id_edit.text().strip()
        device_id: str = self._device_combo.currentData()
        parameter = self._parameter_edit.text().strip()
        alarm_type: AlarmType = self._alarm_type_combo.currentData()
        level: AlarmLevel = self._level_combo.currentData()

        if not parameter:
            QMessageBox.warning(self, "输入错误", "参数名称不能为空。")
            return

        threshold_high: Optional[float] = None
        threshold_low: Optional[float] = None

        if alarm_type == AlarmType.THRESHOLD_HIGH:
            text = self._threshold_high_edit.text().strip()
            if not text:
                QMessageBox.warning(self, "输入错误", "高阈值报警需设置高阈值。")
                return
            try:
                threshold_high = float(text)
            except ValueError:
                QMessageBox.warning(self, "输入错误", "高阈值必须是数字。")
                return
        elif alarm_type == AlarmType.THRESHOLD_LOW:
            text = self._threshold_low_edit.text().strip()
            if not text:
                QMessageBox.warning(self, "输入错误", "低阈值报警需设置低阈值。")
                return
            try:
                threshold_low = float(text)
            except ValueError:
                QMessageBox.warning(self, "输入错误", "低阈值必须是数字。")
                return

        if not rule_id:
            import uuid

            rule_id = uuid.uuid4().hex[:8].upper()

        new_rule = AlarmRule(
            rule_id=rule_id,
            device_id=device_id,
            parameter=parameter,
            alarm_type=alarm_type,
            threshold_high=threshold_high,
            threshold_low=threshold_low,
            level=level,
            enabled=self._enabled_cb.isChecked(),
            description=self._description_edit.text().strip(),
        )

        # If editing, remove old first (unless rule_id unchanged)
        if self._edit_rule and self._edit_rule.rule_id != rule_id:
            self._alarm_manager.remove_rule(self._edit_rule.rule_id)

        # Try add, if conflict overwrite
        if not self._alarm_manager.add_rule(new_rule):
            self._alarm_manager._rules[rule_id] = new_rule

        logger.info("报警规则已保存: %s (编辑=%s)", rule_id, self._edit_rule is not None)
        self.accept()
