# -*- coding: utf-8 -*-
"""
MCGS Device Configuration Dialog (可视化设备配置管理器)

功能：
1. 图形化编辑 devices.json 配置
2. 实时预览JSON格式
3. 表单验证（IP/端口/地址范围）
4. 一键保存到文件
5. 加载已有配置进行修改
6. 预设模板快速填充

使用方式:
    dialog = MCGSConfigDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        config = dialog.get_config()
        # 使用配置...
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QWidget,
    QGroupBox,
    QMessageBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QColorDialog,
    QFrame,
    QScrollArea,
    QSplitter,
    QStatusBar,
)

logger = logging.getLogger(__name__)


class DevicePointEditor(QWidget):
    """单个数据点配置编辑器"""

    data_changed = Signal()

    def __init__(self, point_data: Optional[Dict] = None, parent=None):
        super().__init__(parent)

        self._point_data = point_data or {
            "name": "",
            "addr": 30002,
            "type": "float",
            "unit": "",
            "decimal_places": 2,
            "scale": 1.0,
            "alarm_high": None,
            "alarm_low": None,
            "description": "",
        }

        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # 参数名称
        self.name_edit = QLineEdit(self._point_data.get("name", ""))
        self.name_edit.setPlaceholderText("例如: Temp_in, Hum_in")
        self.name_edit.textChanged.connect(self._on_changed)
        layout.addRow("参数名称 *:", self.name_edit)

        # Modbus地址
        self.addr_spin = QSpinBox()
        self.addr_spin.setRange(0, 65535)
        self.addr_spin.setValue(self._point_data.get("addr", 0))
        self.addr_spin.setPrefix("0x")
        self.addr_spin.setDisplayIntegerBase(16)  # 十六进制显示
        self.addr_spin.valueChanged.connect(self._on_changed)
        layout.addRow("Modbus地址 *:", self.addr_spin)

        # 数据类型
        self.type_combo = QComboBox()
        self.type_combo.addItems(
            [
                ("float / float32", "float"),
                ("int16 / uint16", "int16"),
                ("int32 / uint32", "int32"),
                ("coil (线圈)", "coil"),
                ("discrete_input (DI)", "di"),
            ]
        )

        # 设置当前值
        current_type = self._point_data.get("type", "float")
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == current_type or self.type_combo.itemText(i).startswith(current_type):
                self.type_combo.setCurrentIndex(i)
                break

        self.type_combo.currentIndexChanged.connect(self._on_changed)
        layout.addRow("数据类型 *:", self.type_combo)

        # 单位
        self.unit_edit = QLineEdit(self._point_data.get("unit", ""))
        self.unit_edit.setPlaceholderText("℃, %RH, kPa, m³/h 等")
        self.unit_edit.textChanged.connect(self._on_changed)
        layout.addRow("工程单位:", self.unit_edit)

        # 小数位数
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(0, 6)
        self.decimal_spin.setValue(self._point_data.get("decimal_places", 2))
        self.decimal_spin.valueChanged.connect(self._on_changed)
        layout.addRow("小数位数:", self.decimal_spin)

        # 缩放因子
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.0001, 10000.0)
        self.scale_spin.setValue(self._point_data.get("scale", 1.0))
        self.scale_spin.setDecimals(4)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.valueChanged.connect(self._on_changed)
        layout.addRow("缩放因子:", self.scale_spin)

        # 报警上限
        self.alarm_high_spin = QDoubleSpinBox()
        self.alarm_high_spin.setRange(-9999.0, 9999.0)
        self.alarm_high_spin.setDecimals(2)
        self.alarm_high_spin.setSpecialValueText("∞")  # 无限
        high_val = self._point_data.get("alarm_high")
        if high_val is not None:
            self.alarm_high_spin.setValue(high_val)
        else:
            self.alarm_high_spin.setValue(0.0)
            self.alarm_high_spin.setSpecialValueText("无")
        self.alarm_high_spin.valueChanged.connect(self._on_changed)
        layout.addRow("报警上限:", self.alarm_high_spin)

        # 报警下限
        self.alarm_low_spin = QDoubleSpinBox()
        self.alarm_low_spin.setRange(-9999.0, 9999.0)
        self.alarm_low_spin.setDecimals(2)
        self.alarm_low_spin.setSpecialValueText("-∞")
        low_val = self._point_data.get("alarm_low")
        if low_val is not None:
            self.alarm_low_spin.setValue(low_val)
        else:
            self.alarm_low_spin.setValue(0.0)
            self.alarm_low_spin.setSpecialValueText("无")
        self.alarm_low_spin.valueChanged.connect(self._on_changed)
        layout.addRow("报警下限:", self.alarm_low_spin)

        # 描述
        self.desc_edit = QLineEdit(self._point_data.get("description", ""))
        self.desc_edit.setPlaceholderText("参数用途说明...")
        self.desc_edit.textChanged.connect(self._on_changed)
        layout.addRow("描述:", self.desc_edit)

    def _on_changed(self):
        """字段变更时发射信号"""
        self.data_changed.emit()

    def get_point_data(self) -> Dict:
        """获取当前配置的字典"""
        return {
            "name": self.name_edit.text().strip(),
            "addr": self.addr_spin.value(),
            "type": self.type_combo.currentData() or "float",
            "unit": self.unit_edit.text().strip(),
            "decimal_places": self.decimal_spin.value(),
            "scale": self.scale_spin.value(),
            "alarm_high": self.alarm_high_spin.value() if not self.alarm_high_spin.specialValueText() else None,
            "alarm_low": self.alarm_low_spin.value() if not self.alarm_low_spin.specialValueText() else None,
            "description": self.desc_edit.text().strip(),
        }

    def set_point_data(self, data: Dict):
        """设置配置数据"""
        self._point_data = data
        self.name_edit.setText(data.get("name", ""))
        self.addr_spin.setValue(data.get("addr", 0))
        self.unit_edit.setText(data.get("unit", ""))
        self.decimal_spin.setValue(data.get("decimal_places", 2))
        self.scale_spin.setValue(data.get("scale", 1.0))
        self.desc_edit.setText(data.get("description", ""))

        if data.get("alarm_high") is not None:
            self.alarm_high_spin.setValue(data["alarm_high"])
        if data.get("alarm_low") is not None:
            self.alarm_low_spin.setValue(data["alarm_low"])

    def validate(self) -> Tuple[bool, str]:
        """验证必填项"""
        name = self.name_edit.text().strip()
        if not name:
            return False, "参数名称不能为空"

        addr = self.addr_spin.value()
        if addr < 0 or addr > 65535:
            return False, f"地址超出范围: {addr}"

        return True, ""


class MCGSConfigDialog(QDialog):
    """
    MCGS设备配置对话框

    功能：
    - Tab1: 基本参数配置（IP/端口/UnitID/字节序）
    - Tab2: 数据点列表管理（增删改查）
    - Tab3: JSON原始编辑（高级用户）
    - Tab4: 预设模板快速填充
    - 实时验证和保存功能
    """

    config_saved = Signal(dict)  # (config_dict) 配置已保存

    def __init__(self, config_path: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("⚙️ MCGS 设备配置管理器")
        self.setMinimumSize(900, 700)

        self._config_path = (
            Path(config_path) if config_path else Path(__file__).parent.parent / "config" / "devices.json"
        )

        self._config_data = {}
        self._points_data: List[Dict] = []

        self._init_ui()
        self._load_existing_config()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()

        self.load_btn = QPushButton("📂 加载配置")
        self.load_btn.clicked.connect(self._load_config_file)
        toolbar.addWidget(self.load_btn)

        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 6px 16px;")
        self.save_btn.clicked.connect(self._save_config)
        toolbar.addWidget(self.save_btn)

        self.validate_btn = QPushButton("✅ 验证配置")
        self.validate_btn.clicked.connect(self._validate_config)
        toolbar.addWidget(self.validate_btn)

        toolbar.addStretch()

        status_label = QLabel(f"配置文件: {self._config_path}")
        status_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        toolbar.addWidget(status_label)

        main_layout.addLayout(toolbar)

        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: 基本参数
        self.tabs.addTab(self._create_basic_tab(), "📡 基本参数")

        # Tab 2: 数据点列表
        self.tabs.addTab(self._create_points_tab(), "📊 数据点配置")

        # Tab 3: JSON原始编辑
        self.tabs.addTab(self._create_json_tab(), "📝 JSON编辑")

        # Tab 4: 预设模板
        self.tabs.addTab(self._create_templates_tab(), "🎨 快速模板")

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪")
        main_layout.addWidget(self.status_bar)

    def _create_basic_tab(self) -> QWidget:
        """创建基本参数配置页"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # ====== 设备基本信息 ======
        basic_group = QGroupBox("设备基本信息")
        basic_layout = QFormLayout(basic_group)

        self.device_id_edit = QLineEdit("mcgs_1")
        self.device_id_edit.setPlaceholderText("设备唯一标识符")
        basic_layout.addRow("设备ID *:", self.device_id_edit)

        self.device_name_edit = QLineEdit("MCGS触摸屏#1")
        self.device_name_edit.setPlaceholderText("显示名称")
        basic_layout.addRow("设备名称:", self.device_name_edit)

        layout.addRow(basic_group)

        # ====== 通信参数 ======
        conn_group = QGroupBox("通信参数 (Modbus TCP)")
        conn_layout = QFormLayout(conn_group)

        self.ip_edit = QLineEdit("192.168.1.100")
        self.ip_edit.setPlaceholderText("IP地址 (例如: 192.168.1.100)")
        self.ip_edit.setInputMask("000.000.000.000;_")
        conn_layout.addRow("IP地址 *:", self.ip_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(502)
        self.port_spin.setPrefix("Port: ")
        conn_layout.addRow("端口号 *:", self.port_spin)

        self.unit_id_spin = QSpinBox()
        self.unit_id_spin.setRange(0, 255)
        self.unit_id_spin.setValue(1)
        conn_layout.addRow("从站ID (Unit ID):", self.unit_id_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 60000)
        self.timeout_spin.setValue(3000)
        self.timeout_spin.setSuffix(" ms")
        self.timeout_spin.setSingleStep(500)
        conn_layout.addRow("超时时间:", self.timeout_spin)

        layout.addRow(conn_group)

        # ====== 高级选项 ======
        adv_group = QGroupBox("高级选项")
        adv_layout = QFormLayout(adv_group)

        self.byte_order_combo = QComboBox()
        self.byte_order_combo.addItems(
            [
                ("ABCD - 大端序 (标准)", "ABCD"),
                ("BADC - 半字交换", "BADC"),
                ("CDAB - 字交换/MCGS ⭐", "CDAB"),
                ("DCBA - 完全反转", "DCBA"),
            ]
        )
        self.byte_order_combo.setCurrentIndex(2)  # 默认CDAB
        adv_layout.addRow("字节序 *:", self.byte_order_combo)

        self.polling_spin = QSpinBox()
        self.polling_spin.setRange(100, 60000)
        self.polling_spin.setValue(1000)
        self.polling_spin.setSuffix(" ms")
        self.polling_spin.setSingleStep(100)
        adv_layout.addRow("轮询周期:", self.polling_spin)

        self.address_base_combo = QComboBox()
        self.address_base_combo.addItems(
            [
                ("1-based (标准Modbus地址)", 1),
                ("0-based (pymodbus内部)", 0),
            ]
        )
        self.address_base_combo.setCurrentIndex(0)
        adv_layout.addRow("地址基数:", self.address_base_combo)

        layout.addRow(adv_group)

        return widget

    def _create_points_tab(self) -> QWidget:
        """创建数据点配置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)

        # 工具栏
        points_toolbar = QHBoxLayout()

        self.add_point_btn = QPushButton("+ 添加点位")
        self.add_point_btn.clicked.connect(self._add_point)
        self.add_point_btn.setStyleSheet("background-color: #3B82F6; color: white; padding: 4px 12px;")
        points_toolbar.addWidget(self.add_point_btn)

        self.remove_point_btn = QPushButton("- 删除选中")
        self.remove_point_btn.clicked.connect(self._remove_selected_point)
        self.remove_point_btn.setEnabled(False)
        points_toolbar.addWidget(self.remove_point_btn)

        self.edit_point_btn = QPushButton("✏ 编辑选中")
        self.edit_point_btn.clicked.connect(self._edit_selected_point)
        self.edit_point_btn.setEnabled(False)
        points_toolbar.addWidget(self.edit_point_btn)

        points_toolbar.addStretch()

        # 预设按钮
        preset_btn = QPushButton("📋 预设: 7点MCGS")
        preset_btn.setToolTip("一键填充示例MCGS配置（7个传感器点位）")
        preset_btn.clicked.connect(self._preset_mcgsm_7points)
        points_toolbar.addWidget(preset_btn)

        preset_coil_btn = QPushButton("🔌 预设: 8路继电器")
        preset_coil_btn.clicked.connect(self._preset_8coils)
        points_toolbar.addWidget(preset_coil_btn)

        layout.addLayout(points_toolbar)

        # 点位表格
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(9)
        self.points_table.setHorizontalHeaderLabels(
            ["参数名", "类型", "地址", "单位", "精度", "缩放", "报警高", "报警低", "描述"]
        )
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.points_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.points_table.currentCellChanged.connect(self._on_point_selection_changed)
        self.points_table.doubleClicked.connect(self._edit_selected_point)

        layout.addWidget(self.points_table)

        # 统计信息
        self.points_stats_label = QLabel("共 0 个数据点 | 地址范围: - | 寄存器数: 0")
        self.points_stats_label.setStyleSheet("color: #6B7280; font-size: 11px; padding: 5px;")
        layout.addWidget(self.points_stats_label)

        return widget

    def _create_json_tab(self) -> QWidget:
        """创建JSON原始编辑页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)

        # 说明标签
        info_label = QLabel("⚠️ 高级模式：直接编辑JSON配置。\n" "适合有经验的用户。修改后请点击[验证配置]检查语法错误。")
        info_label.setStyleSheet("background-color: #FEF3C7; padding: 10px; border-radius: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # JSON编辑器
        self.json_editor = QTextEdit()
        self.json_editor.setFontFamily("Consolas, Courier New, monospace")
        self.json_editor.setMinimumHeight(400)
        layout.addWidget(self.json_editor)

        # 操作按钮
        json_toolbar = QHBoxLayout()

        format_btn = QPushButton("🎨 格式化JSON")
        format_btn.clicked.connect(self._format_json)
        json_toolbar.addWidget(format_btn)

        refresh_btn = QPushButton("🔄 从表单刷新")
        refresh_btn.clicked.connect(self._refresh_json_from_form)
        json_toolbar.addWidget(refresh_btn)

        json_toolbar.addStretch()
        layout.addLayout(json_toolbar)

        return widget

    def _create_templates_tab(self) -> QWidget:
        """创建预设模板页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)

        info = QLabel("选择预设模板可快速填充常用配置，\n" "然后切换到[数据点配置]页进行微调。")
        info.setStyleSheet("padding: 10px; background-color: #E0F2FE; border-radius: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # 模板列表
        templates_list = QListWidget()

        templates = [
            {
                "name": "🏭 MCGS 标准配置 (7个传感器)",
                "desc": "适用于MCGS触摸屏 + DL8017模拟量采集模块",
                "data": {
                    "id": "mcgs_standard",
                    "name": "MCGS标准配置",
                    "ip": "192.168.1.100",
                    "port": 502,
                    "byte_order": "CDAB",
                    "points": [
                        {
                            "name": "Hum_in",
                            "addr": 30002,
                            "type": "float",
                            "unit": "%RH",
                            "decimal_places": 1,
                            "scale": 1.0,
                            "alarm_high": 95.0,
                        },
                        {
                            "name": "RH_in",
                            "addr": 30004,
                            "type": "float",
                            "unit": "%",
                            "decimal_places": 1,
                            "scale": 1.0,
                            "alarm_high": 100.0,
                        },
                        {
                            "name": "AT_in",
                            "addr": 30006,
                            "type": "float",
                            "unit": "℃",
                            "decimal_places": 1,
                            "scale": 1.0,
                            "alarm_high": 80.0,
                            "alarm_low": -10.0,
                        },
                        {
                            "name": "Flow_in",
                            "addr": 30008,
                            "type": "float",
                            "unit": "m³/h",
                            "decimal_places": 2,
                            "scale": 1.0,
                            "alarm_high": 10.0,
                        },
                        {
                            "name": "VPa",
                            "addr": 30012,
                            "type": "float",
                            "unit": "kPa",
                            "decimal_places": 1,
                            "scale": 1.0,
                            "alarm_high": 110.0,
                            "alarm_low": 90.0,
                        },
                        {
                            "name": "VPaIn",
                            "addr": 30014,
                            "type": "float",
                            "unit": "kPa",
                            "decimal_places": 1,
                            "scale": 1.0,
                            "alarm_high": 105.0,
                            "alarm_low": 95.0,
                        },
                    ],
                },
            },
            {
                "name": "🔌 8路继电器控制板",
                "desc": "适用于继电器输出模块或PLC DO点",
                "data": {
                    "id": "relay_board_8",
                    "name": "8路继电器板",
                    "ip": "192.168.1.101",
                    "port": 502,
                    "byte_order": "CDAB",
                    "points": [
                        {"name": "Relay_1_进水阀", "addr": 0, "type": "coil", "unit": "", "writable": True},
                        {"name": "Relay_2_出水阀", "addr": 1, "type": "coil", "unit": "", "writable": True},
                        {"name": "Relay_3_搅拌电机", "addr": 2, "type": "coil", "unit": "", "writable": True},
                        {"name": "Relay_4_加热器", "addr": 3, "type": "coil", "unit": "", "writable": True},
                        {"name": "Relay_5_冷却泵", "addr": 4, "type": "coil", "unit": "", "writable": True},
                        {"name": "Relay_6_报警灯", "addr": 5, "type": "coil", "unit": "", "writable": True},
                        {"name": "Relay_7_备用1", "addr": 6, "type": "coil", "unit": "", "writable": True},
                        {"name": "Relay_8_备用2", "addr": 7, "type": "coil", "unit": "", "writable": True},
                    ],
                },
            },
            {
                "name": "🌡 温湿度采集模块",
                "desc": "SHT30/DHT22等温湿度传感器",
                "data": {
                    "id": "temp_hum_module",
                    "name": "温湿度模块",
                    "ip": "192.168.1.102",
                    "port": 502,
                    "byte_order": "CDAB",
                    "points": [
                        {
                            "name": "Temperature",
                            "addr": 100,
                            "type": "float",
                            "unit": "℃",
                            "decimal_places": 2,
                            "scale": 0.1,
                            "alarm_high": 60.0,
                            "alarm_low": -10.0,
                        },
                        {
                            "name": "Humidity",
                            "addr": 102,
                            "type": "float",
                            "unit": "%RH",
                            "decimal_places": 1,
                            "scale": 1.0,
                            "alarm_high": 90.0,
                            "alarm_low": 10.0,
                        },
                    ],
                },
            },
        ]

        for tmpl in templates:
            item = QListWidgetItem(tmpl["name"])
            item.setData(Qt.UserRole, tmpl)
            item.setToolTip(tmpl["desc"])
            templates_list.addItem(item)

        templates_list.itemDoubleClicked.connect(self._apply_template)
        layout.addWidget(templates_list)

        # 应用按钮
        apply_btn = QPushButton("✅ 应用选中的模板")
        apply_btn.clicked.connect(lambda: self._apply_template(templates_list.currentItem()))
        layout.addWidget(apply_btn)

        return widget

    # ==================== 点位表格操作 ====================

    def _add_point(self):
        """添加新数据点"""
        editor = DevicePointEditor(parent=self)

        if editor.exec() == QDialog.DialogCode.Accepted:
            point_data = editor.get_point_data()

            # 添加到列表
            row = self.points_table.rowCount()
            self.points_table.insertRow(row)

            self._populate_table_row(row, point_data)
            self._points_data.append(point_data)

            self._update_points_stats()
            self.status_bar.showMessage(f"已添加点位: {point_data['name']}")

    def _remove_selected_point(self):
        """删除选中的数据点"""
        row = self.points_table.currentRow()
        if row < 0:
            return

        name = self.points_table.item(row, 0).text()

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除数据点 [{name}] 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.points_table.removeRow(row)
            del self._points_data[row]
            self._update_points_stats()
            self.status_bar.showMessage(f"已删除点位: {name}")

    def _edit_selected_point(self):
        """编辑选中的数据点"""
        row = self.points_table.currentRow()
        if row < 0 or row >= len(self._points_data):
            return

        editor = DevicePointEditor(self._points_data[row], parent=self)

        if editor.exec() == QDialog.DialogCode.Accepted:
            updated_data = editor.get_point_data()
            self._points_data[row] = updated_data
            self._populate_table_row(row, updated_data)
            self.status_bar.showMessage(f"已更新点位: {updated_data['name']}")

    def _on_point_selection_changed(self):
        """点位选择变化时更新按钮状态"""
        has_selection = self.points_table.currentRow() >= 0
        self.remove_point_btn.setEnabled(has_selection)
        self.edit_point_btn.setEnabled(has_selection)

    def _populate_table_row(self, row: int, data: Dict):
        """填充表格行"""
        items = [
            data.get("name", ""),
            data.get("type", ""),
            f"{data.get('addr', 0):05d}",
            data.get("unit", ""),
            str(data.get("decimal_places", 2)),
            f"{data.get('scale', 1.0):.2f}",
            f"{data.get('alarm_high', '-'):.1f}" if data.get("alarm_high") else "-",
            f"{data.get('alarm_low', '-'):.1f}" if data.get("alarm_low") else "-",
            data.get("description", "")[:20],
        ]

        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            self.points_table.setItem(row, col, item)

    def _update_points_stats(self):
        """更新点位统计信息"""
        count = len(self._points_data)

        if count > 0:
            addrs = [p["addr"] for p in self._points_data]
            min_addr = min(addrs)
            max_addr = max(addrs)

            reg_counts = {"float": 2, "int32": 2, "int16": 1, "uint16": 1, "coil": 1, "di": 1}
            total_regs = sum(reg_counts.get(p.get("type", "float"), 1) for p in self._points_data)

            self.points_stats_label.setText(
                f"共 {count} 个数据点 | " f"地址范围: {min_addr:05d}-{max_addr:05d} | " f"寄存器数: ~{total_regs}"
            )
        else:
            self.points_stats_label.setText("暂无数据点")

    # ==================== 预设模板 ====================

    def _preset_mcgsm_7points(self):
        """应用7点MCGS传感器预设"""
        template = (
            [
                t
                for t in [
                    QListWidgetItem().setData(
                        {"name": "🏭 MCGS 标准配置 (7个传感器)", "data": {"points": []}}
                    )  # placeholder
                ]
                if False
            ][0].data()["data"]
            if False
            else None
        )

        # 直接使用硬编码的7点配置
        mcgsm_7points = [
            {
                "name": "Hum_in",
                "addr": 30002,
                "type": "float",
                "unit": "%RH",
                "decimal_places": 1,
                "scale": 1.0,
                "alarm_high": 95.0,
                "alarm_low": 5.0,
                "description": "进气湿度",
            },
            {
                "name": "RH_in",
                "addr": 30004,
                "type": "float",
                "unit": "%",
                "decimal_places": 1,
                "scale": 1.0,
                "alarm_high": 100.0,
                "alarm_low": 0.0,
                "description": "相对湿度",
            },
            {
                "name": "AT_in",
                "addr": 30006,
                "type": "float",
                "unit": "℃",
                "decimal_places": 1,
                "scale": 1.0,
                "alarm_high": 80.0,
                "alarm_low": -10.0,
                "description": "进气温度",
            },
            {
                "name": "Flow_in",
                "addr": 30008,
                "type": "float",
                "unit": "m³/h",
                "decimal_places": 2,
                "scale": 1.0,
                "alarm_high": 10.0,
                "alarm_low": 0.0,
                "description": "进气流量",
            },
            {
                "name": "Display_RB",
                "addr": 30010,
                "type": "float",
                "unit": "",
                "decimal_places": 2,
                "scale": 1.0,
                "alarm_high": None,
                "alarm_low": None,
                "description": "保留寄存器",
            },
            {
                "name": "VPa",
                "addr": 30012,
                "type": "float",
                "unit": "kPa",
                "decimal_places": 1,
                "scale": 1.0,
                "alarm_high": 110.0,
                "alarm_low": 90.0,
                "description": "大气压",
            },
            {
                "name": "VPaIn",
                "addr": 30014,
                "type": "float",
                "unit": "kPa",
                "decimal_places": 1,
                "scale": 1.0,
                "alarm_high": 105.0,
                "alarm_low": 95.0,
                "description": "进气压力",
            },
        ]

        self._points_data = mcgsm_7points
        self._refresh_points_table()
        self.tabs.setCurrentIndex(1)  # 切换到数据点Tab
        self.status_bar.showMessage("已应用预设: MCGS 7点传感器配置")

    def _preset_8coils(self):
        """应用8路继电器预设"""
        coils_8 = [
            {"name": "Relay_1_进水阀", "addr": 0, "type": "coil", "unit": "", "writable": True},
            {"name": "Relay_2_出水阀", "addr": 1, "type": "coil", "unit": "", "writable": True},
            {"name": "Relay_3_搅拌电机", "addr": 2, "type": "coil", "unit": "", "writable": True},
            {"name": "Relay_4_加热器", "addr": 3, "type": "coil", "unit": "", "writable": True},
            {"name": "Relay_5_冷却泵", "addr": 4, "type": "coil", "unit": "", "writable": True},
            {"name": "Relay_6_报警灯", "addr": 5, "type": "coil", "unit": "", "writable": True},
            {"name": "Relay_7_备用1", "addr": 6, "type": "coil", "unit": "", "writable": True},
            {"name": "Relay_8_备用2", "addr": 7, "type": "coil", "unit": "", "writable": True},
        ]

        self._points_data = coils_8
        self._refresh_points_table()
        self.tabs.setCurrentIndex(1)
        self.status_bar.showMessage("已应用预设: 8路继电器配置")

    def _apply_template(self, item):
        """应用预设模板"""
        if item is None:
            return

        template_data = item.data(Qt.UserRole)
        if isinstance(template_data, dict) and "data" in template_data:
            data = template_data["data"]

            # 基本参数
            if "ip" in data:
                self.ip_edit.setText(data["ip"])
            if "port" in data:
                self.port_spin.setValue(data["port"])
            if "byte_order" in data:
                for i in range(self.byte_order_combo.count()):
                    if self.byte_order_combo.itemData(i) == data["byte_order"]:
                        self.byte_order_combo.setCurrentIndex(i)
                        break

            # 数据点
            if "points" in data:
                self._points_data = data["points"]
                self._refresh_points_table()

            self.tabs.setCurrentIndex(1)
            self.status_bar.showMessage(f"已应用模板: {template_data.get('name', '')}")

    def _refresh_points_table(self):
        """刷新点位表格"""
        self.points_table.setRowCount(len(self._points_data))

        for row, point in enumerate(self._points_data):
            self._populate_table_row(row, point)

        self._update_points_stats()

    # ==================== JSON操作 ====================

    def _format_json(self):
        """格式化JSON编辑器内容"""
        try:
            text = self.json_editor.toPlainText()
            parsed = json.loads(text)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            self.json_editor.setPlainText(formatted)
            self.status_bar.showMessage("JSON已格式化 ✓")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON格式错误", f"无法解析JSON:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"格式化失败:\n{e}")

    def _refresh_json_from_form(self):
        """从表单刷新JSON编辑器"""
        config = self._collect_config_from_forms()
        json_str = json.dumps(config, indent=2, ensure_ascii=False, default=str)
        self.json_editor.setPlainText(json_str)
        self.tabs.setCurrentIndex(2)  # 切换到JSON Tab
        self.status_bar.showMessage("已从表单刷新JSON ✓")

    def _collect_config_from_forms(self) -> Dict:
        """从所有表单收集配置数据"""
        points_for_json = []
        for p in self._points_data:
            point_copy = {k: v for k, v in p.items()}
            # 移除None值的报警字段（使用pop避免KeyError）
            point_copy.pop("alarm_high", None)
            point_copy.pop("alarm_low", None)
            points_for_json.append(point_copy)

        config = {
            "_meta": {
                "version": "2.0.0",
                "last_modified": __import__("datetime").datetime.now().isoformat(),
                "source": "MCGSConfigDialog",
            },
            "devices": [
                {
                    "id": self.device_id_edit.text().strip() or "mcgs_1",
                    "name": self.device_name_edit.text().strip() or "MCGS设备",
                    "ip": self.ip_edit.text().strip(),
                    "port": self.port_spin.value(),
                    "unit_id": self.unit_id_spin.value(),
                    "timeout_ms": self.timeout_spin.value(),
                    "byte_order": self.byte_order_combo.currentData() or "CDAB",
                    "polling_interval_ms": self.polling_spin.value(),
                    "address_base": self.address_base_combo.currentData() or 1,
                    "points": points_for_json,
                }
            ],
        }

        return config

    # ==================== 文件操作 ====================

    def _load_config_file(self):
        """加载配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "打开MCGS配置文件", "", "JSON Files (*.json);;All Files (*)")

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                self._config_data = config_data

                # 填充基本参数
                devices = config_data.get("devices", [])
                if devices:
                    dev = devices[0]
                    self.device_id_edit.setText(dev.get("id", ""))
                    self.device_name_edit.setText(dev.get("name", ""))
                    self.ip_edit.setText(dev.get("ip", ""))
                    self.port_spin.setValue(dev.get("port", 502))
                    self.unit_id_spin.setValue(dev.get("unit_id", 1))
                    self.timeout_spin.setValue(dev.get("timeout_ms", 3000))

                    bo = dev.get("byte_order", "CDAB")
                    for i in range(self.byte_order_combo.count()):
                        if self.byte_order_combo.itemData(i) == bo:
                            self.byte_order_combo.setCurrentIndex(i)
                            break

                    self.polling_spin.setValue(dev.get("polling_interval_ms", 1000))

                    self._points_data = dev.get("points", [])
                    self._refresh_points_table()

                # 更新JSON编辑器
                self.json_editor.setPlainText(json.dumps(config_data, indent=2, ensure_ascii=False))

                self._config_path = Path(file_path)
                self.status_bar.showMessage(f"已加载: {file_path} ({len(self._points_data)} 个点位)")

            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"无法读取配置文件:\n{e}")

    def _load_existing_config(self):
        """初始化时加载现有配置"""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config_data = json.load(f)

                devices = self._config_data.get("devices", [])
                if devices:
                    dev = devices[0]
                    self._points_data = dev.get("points", [])
                    self._refresh_points_table()

                logger.info(f"已加载配置: {self._config_path}")

            except Exception as e:
                logger.warning(f"加载配置失败（将使用默认值）: {e}")

    def _save_config(self):
        """
        保存配置到文件（带验证+备份机制+原子写入）

        持久化策略：
        1. 验证配置完整性
        2. 备份旧配置为 .bak 文件
        3. 原子写入：先写临时文件，再重命名
        4. 更新内存中的配置数据
        5. 发射 config_saved 信号通知父窗口
        """
        import shutil
        from datetime import datetime

        # 先验证
        valid, error_msg = self._validate_config()
        if not valid:
            reply = QMessageBox.warning(
                self,
                "配置验证未通过",
                f"发现以下问题:\n\n{error_msg}\n\n是否仍要保存？",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
            )

            if reply != QMessageBox.StandardButton.Save:
                return

        # 收集配置
        config = self._collect_config_from_forms()

        try:
            # 确保目录存在
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            # ====== 步骤1: 备份旧配置 ======
            if self._config_path.exists():
                backup_path = self._config_path.with_suffix(".json.bak")
                try:
                    shutil.copy2(self._config_path, backup_path)
                    logger.info(f"已备份旧配置至: {backup_path}")
                except Exception as backup_err:
                    logger.warning(f"备份旧配置失败（非致命）: {backup_err}")
                    # 备份失败不阻止保存

            # ====== 步骤2: 原子写入 ======
            # 先写入临时文件
            temp_path = self._config_path.with_suffix(".json.tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.write("\n")  # 确保文件以换行符结尾

            # 原子重命名（在大多数操作系统上是原子操作）
            temp_path.replace(self._config_path)

            # ====== 步骤3: 更新内存状态 ======
            self._config_data = config
            if "devices" in config and isinstance(config["devices"], list):
                for dev_config in config["devices"]:
                    if isinstance(dev_config, dict) and "points" in dev_config:
                        self._points_data = dev_config["points"]
                        break
            elif "devices" in config and isinstance(config["devices"], dict):
                for dev_id, dev_config in config["devices"].items():
                    if "points" in dev_config:
                        self._points_data = dev_config["points"]
                        break

            # ====== 步骤4: 发射信号通知父窗口 ======
            self.config_saved.emit(config)

            # ====== 步骤5: 更新UI状态 ======
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_msg = (
                f"✅ 配置已保存 ({timestamp}) | 路径: {self._config_path.name} | 数据点: {len(self._points_data)}个"
            )
            self.status_bar.showMessage(save_msg)

            # 显示成功提示（包含备份信息）
            backup_info = ""
            if self._config_path.with_suffix(".json.bak").exists():
                backup_info = f"\n📦 旧配置已备份为: {self._config_path.name}.bak"

            QMessageBox.information(
                self,
                "保存成功",
                f"配置已成功保存！\n\n"
                f"📄 文件: {self._config_path}\n"
                f"📊 数据点: {len(self._points_data)} 个\n"
                f"⏰ 时间: {timestamp}"
                f"{backup_info}",
            )

            logger.info(f"配置保存成功: {self._config_path} (数据点={len(self._points_data)}, 备份=OK)")

        except PermissionError as perm_err:
            error_detail = (
                f"权限不足，无法写入配置文件:\n"
                f"{self._config_path}\n\n"
                f"可能的原因：\n"
                f"• 文件被其他程序锁定\n"
                f"• 目录没有写权限\n"
                f"• 以只读模式打开"
            )
            QMessageBox.critical(self, "保存失败 - 权限错误", error_detail)
            logger.error(f"配置保存失败(权限错误): {perm_err}")

        except OSError as os_err:
            error_detail = (
                f"系统I/O错误，无法保存配置:\n"
                f"{str(os_err)}\n\n"
                f"请检查：\n"
                f"• 磁盘空间是否充足\n"
                f"• 文件路径是否有效\n"
                f"• 是否有防病毒软件拦截"
            )
            QMessageBox.critical(self, "保存失败 - I/O错误", error_detail)
            logger.error(f"配置保存失败(I/O错误): {os_err}")

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"未知错误:\n{e}")
            logger.exception(f"配置保存失败(未知错误): {e}")

    def _validate_config(self) -> Tuple[bool, str]:
        """验证配置完整性"""
        errors = []

        # 验证基本参数
        device_id = self.device_id_edit.text().strip()
        if not device_id:
            errors.append("• 设备ID不能为空")

        ip = self.ip_edit.text().strip()
        if not ip:
            errors.append("• IP地址不能为空")
        elif not ip.replace(".", "").isdigit():
            # 简单IP格式检查
            parts = ip.split(".")
            if len(parts) != 4 or any(not 0 <= int(p) <= 255 for p in parts):
                errors.append(f"• IP地址格式无效: {ip}")

        port = self.port_spin.value()
        if port < 1 or port > 65535:
            errors.append(f"• 端口超出范围: {port} (应为 1-65535)")

        # 验证数据点
        if len(self._points_data) == 0:
            errors.append("• 至少需要配置1个数据点")

        names_seen = set()
        addrs_seen = set()

        for i, point in enumerate(self._points_data):
            name = point.get("name", "").strip()
            addr = point.get("addr", 0)

            if not name:
                errors.append(f"• 第{i+1}个数据点: 参数名不能为空")
            elif name in names_seen:
                errors.append(f"• 参数名重复: '{name}'")

            names_seen.add(name)

            if addr < 0 or addr > 65535:
                errors.append(f"• [{name}] 地址超出范围: {addr}")
            elif addr in addrs_seen:
                errors.append(f"• [{name}] 地址重复: {addr}")

            addrs_seen.add(addr)

        if errors:
            error_text = "\n".join(errors[:10])  # 最多显示10条
            if len(errors) > 10:
                error_text += f"\n... 还有 {len(errors)-10} 个问题"

            return False, error_text

        return True, "配置验证通过 ✓"

    def get_config(self) -> Dict:
        """获取当前完整配置字典"""
        return self._collect_config_from_forms()

    def get_config_path(self) -> Path:
        """获取配置文件路径"""
        return self._config_path

    def setFocusDevice(self, device_id: str) -> None:
        """
        设置要聚焦的设备ID（用于连接失败时的引导）

        当连接失败时，调用此方法可以：
        1. 自动填充设备ID字段
        2. 切换到基本参数Tab
        3. 高亮显示IP和端口字段，引导用户检查

        Args:
            device_id: 设备标识符（例如 "mcgs_1"）
        """
        if not device_id:
            return

        # 设置设备ID
        self.device_id_edit.setText(device_id)

        # 尝试从已加载的配置中查找该设备的其他信息并填充
        if "devices" in self._config_data and device_id in self._config_data["devices"]:
            dev_config = self._config_data["devices"][device_id]

            # 填充已有配置值
            if "name" in dev_config:
                self.device_name_edit.setText(dev_config["name"])
            if "ip" in dev_config:
                self.ip_edit.setText(dev_config["ip"])
            if "port" in dev_config:
                self.port_spin.setValue(dev_config["port"])
            if "unit_id" in dev_config:
                self.unit_id_spin.setValue(dev_config["unit_id"])
            if "byte_order" in dev_config:
                index = self.byte_order_combo.findText(dev_config["byte_order"])
                if index >= 0:
                    self.byte_order_combo.setCurrentIndex(index)

        # 切换到基本参数Tab（索引0）
        self.tabs.setCurrentIndex(0)

        # 高亮IP地址字段（最可能出错的地方）
        self.ip_edit.setStyleSheet(
            """
            QLineEdit {
                border: 2px solid #F59E0B;
                background-color: #FEF3C7;
                padding: 4px;
            }
        """
        )
        self.ip_edit.setFocus()

        # 显示引导提示
        self.status_bar.showMessage(f"⚠️ 设备 [{device_id}] 连接失败 - 请检查上方高亮的通信参数", 10000)  # 显示10秒

        logger.info(f"配置对话框已聚焦到设备: {device_id}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = MCGSConfigDialog()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        config = dialog.get_config()
        print(f"配置已确认:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
