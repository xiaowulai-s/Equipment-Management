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


class DevicePointEditor(QDialog):
    """单个数据点配置编辑器"""

    data_changed = Signal()

    def __init__(self, point_data: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑数据点")
        self.setModal(True)
        self.setMinimumWidth(400)

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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(8)

        layout = QFormLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 参数名称
        self.name_edit = QLineEdit(self._point_data.get("name", ""))
        self.name_edit.setPlaceholderText("例如: Temp_in, Hum_in")
        self.name_edit.textChanged.connect(self._on_changed)
        layout.addRow("参数名称 *:", self.name_edit)

        # Modbus地址
        self.addr_spin = QSpinBox()
        self.addr_spin.setRange(0, 65535)
        raw_addr = self._point_data.get("addr", 0)
        try:
            self.addr_spin.setValue(int(raw_addr))
        except (ValueError, TypeError):
            self.addr_spin.setValue(0)
        self.addr_spin.setPrefix("0x")
        self.addr_spin.setDisplayIntegerBase(16)  # 十六进制显示
        self.addr_spin.valueChanged.connect(self._on_changed)
        layout.addRow("Modbus地址 *:", self.addr_spin)

        # 数据类型
        self.type_combo = QComboBox()
        type_options = [
            ("float / float32", "float"),
            ("int16 / uint16", "int16"),
            ("int32 / uint32", "int32"),
            ("coil (线圈)", "coil"),
            ("discrete_input (DI)", "di"),
            ("string (字符串)", "string"),
        ]
        for text, data in type_options:
            self.type_combo.addItem(text, data)

        # 设置当前值（支持别名：uint16→int16, uint32→int32, float32→float）
        current_type = self._point_data.get("type", "float")
        type_alias = {
            "uint16": "int16",
            "uint32": "int32",
            "float32": "float",
        }
        match_type = type_alias.get(current_type, current_type)
        found = False
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == match_type or self.type_combo.itemText(i).startswith(match_type):
                self.type_combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            logger.warning("MCGS配置: 未知数据类型 '%s', 使用默认float", current_type)

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
        raw_dp = self._point_data.get("decimal_places", 2)
        try:
            self.decimal_spin.setValue(int(raw_dp))
        except (ValueError, TypeError):
            self.decimal_spin.setValue(2)
        self.decimal_spin.valueChanged.connect(self._on_changed)
        layout.addRow("小数位数:", self.decimal_spin)

        # 缩放因子
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.0001, 10000.0)
        raw_scale = self._point_data.get("scale", 1.0)
        try:
            self.scale_spin.setValue(float(raw_scale))
        except (ValueError, TypeError):
            self.scale_spin.setValue(1.0)
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
        if high_val is not None and high_val != "":
            try:
                self.alarm_high_spin.setValue(float(high_val))
            except (ValueError, TypeError):
                self.alarm_high_spin.setValue(0.0)
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
        if low_val is not None and low_val != "":
            try:
                self.alarm_low_spin.setValue(float(low_val))
            except (ValueError, TypeError):
                self.alarm_low_spin.setValue(0.0)
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

        main_layout.addLayout(layout)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 8px 24px; border-radius: 6px;"
        )
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("padding: 8px 24px; border-radius: 6px;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

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

    def __init__(self, config_path: Optional[str] = None, parent=None, target_device_id: str = None):
        super().__init__(parent)

        self.setWindowTitle("⚙️ MCGS 设备配置管理器")
        self.setMinimumSize(900, 700)

        self._config_path = (
            Path(config_path) if config_path else Path(__file__).parent.parent / "config" / "devices.json"
        )

        self._config_data = {}
        self._points_data: List[Dict] = []
        self._original_device_id: str = ""
        self._target_device_id: str = target_device_id or ""

        self._init_ui()
        self._load_existing_config(target_device_id=target_device_id)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()

        self.load_btn = QPushButton("📂 加载配置")
        self.load_btn.clicked.connect(self._load_config_file)
        toolbar.addWidget(self.load_btn)

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setToolTip("保存配置（不关闭对话框）")
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
        main_layout.addWidget(self.tabs, 1)

        # Tab 1: 基本参数
        self.tabs.addTab(self._create_basic_tab(), "📡 基本参数")

        # Tab 2: 数据点列表
        self.tabs.addTab(self._create_points_tab(), "📊 数据点配置")

        # Tab 3: JSON原始编辑
        self.tabs.addTab(self._create_json_tab(), "📝 JSON编辑")

        # Tab 4: 预设模板
        self.tabs.addTab(self._create_templates_tab(), "🎨 快速模板")

        # 底部操作按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.addStretch()
        self.save_close_btn = QPushButton("💾 保存并关闭")
        self.save_close_btn.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;"
        )
        self.save_close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.save_close_btn)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("padding: 8px 20px; border-radius: 6px;")
        self.cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(bottom_layout)

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪")
        main_layout.addWidget(self.status_bar)

        # Tab切换监听 - 自动刷新JSON编辑器
        self.tabs.currentChanged.connect(self._on_tab_changed)

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
        basic_layout.addRow("设备编号 *:", self.device_id_edit)

        self.device_name_edit = QLineEdit("MCGS触摸屏#1")
        self.device_name_edit.setPlaceholderText("显示名称")
        basic_layout.addRow("设备名称:", self.device_name_edit)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("设备描述（可选，如：车间A-温度采集）")
        basic_layout.addRow("设备描述:", self.description_edit)

        layout.addRow(basic_group)

        # ====== 通信参数 ======
        conn_group = QGroupBox("通信参数 (Modbus TCP)")
        conn_layout = QFormLayout(conn_group)

        self.ip_edit = QLineEdit("192.168.31.239")
        self.ip_edit.setPlaceholderText("IP地址 (例如: 192.168.31.239)")
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
        byte_order_items = [
            ("ABCD - 大端序 (标准)", "ABCD"),
            ("BADC - 半字交换", "BADC"),
            ("CDAB - 字交换/MCGS", "CDAB"),
            ("DCBA - 完全反转", "DCBA"),
        ]
        for text, data in byte_order_items:
            self.byte_order_combo.addItem(text, data)
        self.byte_order_combo.setCurrentIndex(0)  # 默认ABCD
        adv_layout.addRow("字节序 *:", self.byte_order_combo)

        self.polling_spin = QSpinBox()
        self.polling_spin.setRange(100, 60000)
        self.polling_spin.setValue(1000)
        self.polling_spin.setSuffix(" ms")
        self.polling_spin.setSingleStep(100)
        adv_layout.addRow("轮询周期:", self.polling_spin)

        self.address_base_combo = QComboBox()
        address_base_items = [
            ("40001-based (4xxxx保持寄存器)", 40001),
            ("1-based (标准Modbus地址)", 1),
            ("0-based (pymodbus内部)", 0),
        ]
        for text, data in address_base_items:
            self.address_base_combo.addItem(text, data)
        self.address_base_combo.setCurrentIndex(0)  # 默认40001
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

        # 使用模板按钮
        use_template_btn = QPushButton("🎨 使用模板")
        use_template_btn.setToolTip("从预设模板快速加载数据点配置")
        use_template_btn.clicked.connect(self._show_template_selector)
        points_toolbar.addWidget(use_template_btn)

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

    def _on_tab_changed(self, index: int):
        """Tab页切换时的处理"""
        if index == 2:  # JSON编辑Tab
            self._refresh_json_editor()

    def _refresh_json_editor(self):
        """刷新JSON编辑器内容为当前设备的配置"""
        import json

        config = self._get_current_device_config()
        json_str = json.dumps(config, ensure_ascii=False, indent=2)
        self.json_editor.setPlainText(json_str)
        self.status_bar.showMessage(f"JSON已刷新 ({len(json_str)} 字符)")

    def _get_current_device_config(self) -> Dict:
        """获取当前正在编辑的设备完整配置"""
        config = {
            "id": self.device_id_edit.text(),
            "name": self.device_name_edit.text(),
            "description": self.description_edit.text(),
            "ip": self.ip_edit.text(),
            "port": self.port_spin.value(),
            "unit_id": self.unit_id_spin.value(),
            "timeout_ms": self.timeout_spin.value(),
            "byte_order": self.byte_order_combo.currentData(),
            "polling_interval_ms": self.polling_spin.value(),
            "address_base": self.address_base_combo.currentData(),
            "points": self._get_points_from_table(),
        }
        return config

    def _create_templates_tab(self) -> QWidget:
        """创建预设模板页 - 显示模板列表和详情"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)

        # 说明信息
        info = QLabel("💡 模板可用于快速配置常用设备类型。\n" "选择模板后可在[数据点配置]页面微调。")
        info.setStyleSheet("padding: 10px; background-color: #E0F2FE; border-radius: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # 分割布局：左侧模板列表，右侧模板详情
        from PySide6.QtWidgets import QSplitter

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：模板列表
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)

        list_header = QLabel("可用模板")
        list_header.setStyleSheet("font-weight: bold; font-size: 13px;")
        list_layout.addWidget(list_header)

        self.templates_list = QListWidget()
        self.templates_list.currentItemChanged.connect(self._on_template_selected)
        list_layout.addWidget(self.templates_list)

        # 添加/删除模板按钮
        template_btn_layout = QHBoxLayout()
        add_template_btn = QPushButton("+ 添加模板")
        add_template_btn.clicked.connect(self._add_custom_template)
        template_btn_layout.addWidget(add_template_btn)
        list_layout.addLayout(template_btn_layout)

        splitter.addWidget(list_widget)

        # 右侧：模板详情
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(10, 0, 0, 0)

        detail_header = QLabel("模板详情")
        detail_header.setStyleSheet("font-weight: bold; font-size: 13px;")
        detail_layout.addWidget(detail_header)

        self.template_title = QLabel("")
        self.template_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1F2937;")
        detail_layout.addWidget(self.template_title)

        self.template_desc = QLabel("")
        self.template_desc.setWordWrap(True)
        self.template_desc.setStyleSheet("color: #6B7280; padding: 5px 0;")
        detail_layout.addWidget(self.template_desc)

        # JSON预览
        json_label = QLabel("JSON格式:")
        json_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        detail_layout.addWidget(json_label)

        self.template_json_preview = QTextEdit()
        self.template_json_preview.setReadOnly(True)
        self.template_json_preview.setFontFamily("Consolas, monospace")
        self.template_json_preview.setMaximumHeight(300)
        detail_layout.addWidget(self.template_json_preview)

        # 应用模板按钮
        apply_btn = QPushButton("📥 应用此模板")
        apply_btn.setStyleSheet("background-color: #10B981; color: white; padding: 8px 16px; border-radius: 6px;")
        apply_btn.clicked.connect(self._apply_selected_template)
        detail_layout.addWidget(apply_btn)

        detail_layout.addStretch()
        splitter.addWidget(detail_widget)

        splitter.setSizes([200, 600])
        layout.addWidget(splitter)

        # 加载内置模板
        self._load_builtin_templates()

        return widget

    def _load_builtin_templates(self):
        """加载内置和自定义模板"""
        self._templates = []

        # 内置模板1: 六路通用数据（对应设备1配置）
        self._templates.append(
            {
                "id": "template_6points",
                "title": "六路通用数据",
                "description": "适用于MCGS触摸屏设备0 - 7通道数据转发\n地址范围: 40001-40006\n包含: 通讯状态/DevPoint/H2O/Data0-2",
                "config": {
                    "byte_order": "ABCD",
                    "address_base": 40001,
                    "points": [
                        {"name": "通讯状态", "addr": "40001", "type": "int16"},
                        {"name": "DevPoint_读写4W0001", "addr": "40002", "type": "int16"},
                        {"name": "DevPointAtm_读写4W0002", "addr": "40003", "type": "int16"},
                        {"name": "H2Oppm_读写4W0003", "addr": "40004", "type": "int16"},
                        {"name": "Data0_读写4W0004", "addr": "40005", "type": "int16"},
                        {"name": "Data1_读写4W0005", "addr": "40006", "type": "int16"},
                    ],
                },
            }
        )

        # 内置模板2: 四路传感器
        self._templates.append(
            {
                "id": "template_4points",
                "title": "四路传感器",
                "description": "通用四路模拟量采集模块\n地址范围: 40001-40004\n适用于DL8017等模块",
                "config": {
                    "byte_order": "CDAB",
                    "address_base": 40001,
                    "points": [
                        {"name": "Data0", "addr": "40001", "type": "uint16"},
                        {"name": "Data1", "addr": "40002", "type": "uint16"},
                        {"name": "Data2", "addr": "40003", "type": "uint16"},
                        {"name": "Data3", "addr": "40004", "type": "uint16"},
                    ],
                },
            }
        )

        # 显示到列表
        for tmpl in self._templates:
            item = QListWidgetItem(tmpl["title"])
            item.setData(Qt.ItemDataRole.UserRole, tmpl["id"])
            self.templates_list.addItem(item)

    def _on_template_selected(self, current, previous):
        """模板选择变化时更新详情"""
        if not current:
            return

        template_id = current.data(Qt.ItemDataRole.UserRole)
        tmpl = next((t for t in self._templates if t["id"] == template_id), None)

        if tmpl:
            self.template_title.setText(tmpl["title"])
            self.template_desc.setText(tmpl["description"])
            import json

            json_str = json.dumps(tmpl["config"], ensure_ascii=False, indent=2)
            self.template_json_preview.setPlainText(json_str)

    def _apply_selected_template(self):
        """应用选中的模板到数据点配置"""
        current_item = self.templates_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return

        template_id = current_item.data(Qt.ItemDataRole.UserRole)
        tmpl = next((t for t in self._templates if t["id"] == template_id), None)

        if tmpl and "config" in tmpl:
            config = tmpl["config"]

            # 应用字节序和地址基数
            if "byte_order" in config:
                idx = self.byte_order_combo.findData(config["byte_order"])
                if idx >= 0:
                    self.byte_order_combo.setCurrentIndex(idx)

            if "address_base" in config:
                idx = self.address_base_combo.findData(config["address_base"])
                if idx >= 0:
                    self.address_base_combo.setCurrentIndex(idx)

            # 应用数据点
            if "points" in config:
                self._fill_points_to_table(config["points"])

            # 切换到数据点配置Tab
            self.tabs.setCurrentIndex(1)  # 数据点配置Tab

            self.status_bar.showMessage(f"已应用模板: {tmpl['title']}")
            QMessageBox.information(self, "成功", f"模板 [{tmpl['title']}] 已应用！\n请切换到[数据点配置]页查看。")

    def _add_custom_template(self):
        """添加自定义模板"""
        QMessageBox.information(self, "开发中", "自定义模板功能即将推出！\n当前可使用内置模板。")

    def _show_template_selector(self):
        """显示模板选择对话框"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("选择数据点模板")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        hint = QLabel("选择一个预设模板来填充数据点配置：")
        layout.addWidget(hint)

        template_list = QListWidget()

        # 添加可用模板
        templates = [
            ("六路通用数据", "设备1的40001-40006六个数据点"),
            ("四路传感器", "通用四路采集模块40001-40004"),
        ]

        for title, desc in templates:
            item = QListWidgetItem(f"{title}\n   {desc}")
            item.setData(Qt.ItemDataRole.UserRole, title)
            template_list.addItem(item)

        layout.addWidget(template_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = template_list.currentItem()
            if selected:
                template_name = selected.data(Qt.ItemDataRole.UserRole)
                if template_name == "六路通用数据":
                    self._apply_preset_6points()
                elif template_name == "四路传感器":
                    self._apply_preset_4points()

    def _apply_preset_6points(self):
        """应用六路数据点预设"""
        preset_points = [
            {"name": "通讯状态", "addr": "40001", "type": "int16"},
            {"name": "DevPoint_读写4W0001", "addr": "40002", "type": "int16"},
            {"name": "DevPointAtm_读写4W0002", "addr": "40003", "type": "int16"},
            {"name": "H2Oppm_读写4W0003", "addr": "40004", "type": "int16"},
            {"name": "Data0_读写4W0004", "addr": "40005", "type": "int16"},
            {"name": "Data1_读写4W0005", "addr": "40006", "type": "int16"},
        ]
        self._fill_points_to_table(preset_points)

    def _apply_preset_4points(self):
        """应用四路数据点预设"""
        preset_points = [
            {"name": "Data0", "addr": "40001", "type": "uint16"},
            {"name": "Data1", "addr": "40002", "type": "uint16"},
            {"name": "Data2", "addr": "40003", "type": "uint16"},
            {"name": "Data3", "addr": "40004", "type": "uint16"},
        ]
        self._fill_points_to_table(preset_points)

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
        # 类型安全转换：addr 可能为 int 或 str
        raw_addr = data.get("addr", 0)
        try:
            addr_str = f"{int(raw_addr):05d}"
        except (ValueError, TypeError):
            addr_str = str(raw_addr)

        raw_dp = data.get("decimal_places", 2)
        try:
            dp_str = str(int(raw_dp))
        except (ValueError, TypeError):
            dp_str = str(raw_dp)

        raw_scale = data.get("scale", 1.0)
        try:
            scale_str = f"{float(raw_scale):.2f}"
        except (ValueError, TypeError):
            scale_str = str(raw_scale)

        raw_high = data.get("alarm_high")
        alarm_high_str = (
            f"{float(raw_high):.1f}" if raw_high is not None and raw_high != "-" and raw_high != "" else "-"
        )
        raw_low = data.get("alarm_low")
        alarm_low_str = f"{float(raw_low):.1f}" if raw_low is not None and raw_low != "-" and raw_low != "" else "-"

        items = [
            data.get("name", ""),
            data.get("type", ""),
            addr_str,
            data.get("unit", ""),
            dp_str,
            scale_str,
            alarm_high_str,
            alarm_low_str,
            data.get("description", "")[:20],
        ]

        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            self.points_table.setItem(row, col, item)

    def _get_points_from_table(self) -> List[Dict]:
        """从表格读取当前设备的所有数据点配置"""
        points = []
        for p in self._points_data:
            point_copy = {k: v for k, v in p.items()}
            points.append(point_copy)
        return points

    def _update_points_stats(self):
        """更新点位统计信息"""
        count = len(self._points_data)

        if count > 0:
            addrs = []
            addr_names = {}  # addr → [names...]
            for p in self._points_data:
                try:
                    a = int(p["addr"])
                    addrs.append(a)
                    n = p.get("name", "")
                    if a not in addr_names:
                        addr_names[a] = []
                    addr_names[a].append(n)
                except (ValueError, TypeError, KeyError):
                    addrs.append(0)
            min_addr = min(addrs)
            max_addr = max(addrs)

            reg_counts = {"float": 2, "int32": 2, "int16": 1, "uint16": 1, "coil": 1, "di": 1}
            total_regs = sum(reg_counts.get(p.get("type", "float"), 1) for p in self._points_data)

            # 检测重复地址
            dup_warnings = []
            for addr, names in addr_names.items():
                if len(names) > 1:
                    types_at_addr = {}
                    for p in self._points_data:
                        try:
                            if int(p["addr"]) == addr:
                                types_at_addr.setdefault(p.get("type", "?"), []).append(p.get("name", ""))
                        except (ValueError, TypeError, KeyError):
                            pass
                    type_strs = [f"{t}({','.join(ns)})" for t, ns in types_at_addr.items()]
                    dup_warnings.append(f" 地址 {addr:05d}: {' vs '.join(type_strs)}")

            stats_text = f"共 {count} 个数据点 | 地址范围: {min_addr:05d}-{max_addr:05d} | 寄存器数: ~{total_regs}"
            if dup_warnings:
                stats_text += " | ⚠️ 地址重复: " + "; ".join(dup_warnings)
                self.points_stats_label.setStyleSheet(
                    "color: #D97706; font-size: 12px; font-weight: bold; padding: 4px;"
                )
            else:
                self.points_stats_label.setStyleSheet("color: #333; font-size: 12px;")

            self.points_stats_label.setText(stats_text)
        else:
            self.points_stats_label.setText("暂无数据点")
            self.points_stats_label.setStyleSheet("color: #999; font-size: 12px;")

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
        """从所有表单收集配置数据，保留所有已有设备，支持重命名"""
        points_for_json = []
        for p in self._points_data:
            point_copy = {k: v for k, v in p.items()}
            point_copy.pop("alarm_high", None)
            point_copy.pop("alarm_low", None)
            points_for_json.append(point_copy)

        current_device_id = self.device_id_edit.text().strip() or "mcgs_1"
        edited_device = {
            "id": current_device_id,
            "name": self.device_name_edit.text().strip() or "MCGS设备",
            "description": self.description_edit.text().strip(),
            "ip": self.ip_edit.text().strip(),
            "port": self.port_spin.value(),
            "unit_id": self.unit_id_spin.value(),
            "timeout_ms": self.timeout_spin.value(),
            "byte_order": self.byte_order_combo.currentData() or "CDAB",
            "polling_interval_ms": self.polling_spin.value(),
            "address_base": self.address_base_combo.currentData() or 1,
            "points": points_for_json,
        }

        original_devices = self._config_data.get("devices", [])
        target_id = self._original_device_id or current_device_id
        is_rename = target_id != "" and target_id != current_device_id

        if isinstance(original_devices, list):
            devices_list = []
            updated = False
            for dev in original_devices:
                dev_id = dev.get("id") if isinstance(dev, dict) else None
                if dev_id == target_id:
                    devices_list.append(edited_device)
                    updated = True
                    if is_rename:
                        logger.info("设备重命名: %s → %s", target_id, current_device_id)
                else:
                    devices_list.append(dev)
            if not updated:
                devices_list.append(edited_device)
                logger.info("新增设备: %s (原始目标 %s 不在列表中)", current_device_id, target_id)
        elif isinstance(original_devices, dict):
            devices_list = [edited_device]
            for did, dev in original_devices.items():
                if did != target_id and did != current_device_id:
                    dev["id"] = did
                    devices_list.append(dev)
        else:
            devices_list = [edited_device]

        config = {
            "_meta": {
                "version": "2.0.0",
                "last_modified": __import__("datetime").datetime.now().isoformat(),
                "source": "MCGSConfigDialog",
            },
            "devices": devices_list,
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

                devices = config_data.get("devices", [])
                if devices:
                    self._load_device_to_form(devices[0])

                self.json_editor.setPlainText(json.dumps(config_data, indent=2, ensure_ascii=False))

                self._config_path = Path(file_path)
                self.status_bar.showMessage(f"已加载: {file_path} ({len(self._points_data)} 个点位)")

            except Exception as e:
                QMessageBox.critical(self, "加载失败", f"无法读取配置文件:\n{e}")

    def _load_existing_config(self, target_device_id: str = None):
        """初始化时加载现有配置，支持指定目标设备"""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config_data = json.load(f)

                devices = self._config_data.get("devices", [])
                if not devices:
                    return

                target_id = target_device_id or self._target_device_id
                dev = None
                if target_id:
                    for d in devices:
                        if isinstance(d, dict) and d.get("id") == target_id:
                            dev = d
                            break
                if dev is None and devices:
                    dev = devices[0]
                elif dev is None:
                    return

                self._load_device_to_form(dev)
                logger.info(f"已加载配置: {self._config_path} (编辑设备: {dev.get('id', '?')})")

            except Exception as e:
                logger.warning(f"加载配置失败（将使用默认值）: {e}")

    def _load_device_to_form(self, dev: Dict) -> None:
        """将单个设备配置字典填充到表单控件"""
        self._original_device_id = dev.get("id", "")
        self.device_id_edit.setText(self._original_device_id)
        self.device_name_edit.setText(dev.get("name", "MCGS触摸屏#1"))
        self.description_edit.setText(dev.get("description", ""))
        self.ip_edit.setText(dev.get("ip", ""))
        self.port_spin.setValue(dev.get("port", 502))
        self.unit_id_spin.setValue(dev.get("unit_id", 1))
        self.timeout_spin.setValue(dev.get("timeout_ms", 3000))

        bo = dev.get("byte_order", "ABCD")
        for i in range(self.byte_order_combo.count()):
            if self.byte_order_combo.itemData(i) == bo:
                self.byte_order_combo.setCurrentIndex(i)
                break

        self.polling_spin.setValue(dev.get("polling_interval_ms", 1000))

        ab = dev.get("address_base", 40001)
        for i in range(self.address_base_combo.count()):
            if self.address_base_combo.itemData(i) == ab:
                self.address_base_combo.setCurrentIndex(i)
                break

        # 加载设备类型（如果有）
        device_type = dev.get("device_type", "MCGS触摸屏")

        # 加载数据点（保留所有字段包括description, unit, alarm_high等）
        raw_points = dev.get("points", [])
        self._points_data = []
        for pt in raw_points:
            point_copy = dict(pt)
            # 确保关键字段存在
            if "description" not in point_copy:
                point_copy["description"] = ""
            if "unit" not in point_copy:
                point_copy["unit"] = ""
            if "alarm_high" not in point_copy:
                point_copy["alarm_high"] = None
            if "alarm_low" not in point_copy:
                point_copy["alarm_low"] = None
            self._points_data.append(point_copy)

        self._refresh_points_table()

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
            self._original_device_id = self.device_id_edit.text().strip() or ""

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
        """验证配置完整性（增强版：支持新字段验证）"""
        errors = []
        warnings = []

        # 验证基本参数
        device_id = self.device_id_edit.text().strip()
        if not device_id:
            errors.append("• 设备ID不能为空")

        ip = self.ip_edit.text().strip()
        if not ip:
            errors.append("• IP地址不能为空")
        elif not ip.replace(".", "").isdigit():
            parts = ip.split(".")
            if len(parts) != 4 or any(not 0 <= int(p) <= 255 for p in parts):
                errors.append(f"• IP地址格式无效: {ip}")

        port = self.port_spin.value()
        if port < 1 or port > 65535:
            errors.append(f"• 端口超出范围: {port} (应为 1-65535)")

        unit_id = self.unit_id_spin.value()
        if unit_id < 0 or unit_id > 255:
            warnings.append(f"• Unit ID超出推荐范围: {unit_id} (建议0-255)")

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

            # 地址验证（支持字符串和数字）
            try:
                addr_num = int(addr)
                if addr_num < 0 or addr_num > 65535:
                    errors.append(f"• [{name}] 地址超出范围: {addr}")
                elif addr_num in addrs_seen:
                    warnings.append(f"• [{name}] 地址可能重复: {addr}")
                addrs_seen.add(addr_num)
            except (ValueError, TypeError):
                errors.append(f"• [{name}] 地址格式无效: {addr}")

            # 类型验证
            ptype = point.get("type", "")
            valid_types = ["int16", "uint16", "int32", "uint32", "float", "coil", "di"]
            if ptype and ptype not in valid_types:
                warnings.append(f"• [{name}] 数据类型异常: {ptype}")

            # 报警值验证
            alarm_high = point.get("alarm_high")
            alarm_low = point.get("alarm_low")
            if alarm_high is not None and alarm_low is not None:
                try:
                    if float(alarm_high) <= float(alarm_low):
                        warnings.append(f"• [{name}] 报警上限({alarm_high}) ≤ 下限({alarm_low})")
                except (ValueError, TypeError):
                    warnings.append(f"• [{name}] 报警值格式异常")

        # 构建结果消息
        result_parts = []

        if errors:
            error_section = "\n".join(errors)
            result_parts.append(f"❌ 错误 ({len(errors)}个):\n{error_section}")

        if warnings:
            warning_section = "\n".join(warnings)
            result_parts.append(f"\n⚠️ 警告 ({len(warnings)}个):\n{warning_section}")

        if not errors and not warnings:
            return True, "✅ 配置验证通过！所有项目均符合要求。"

        final_msg = "\n".join(result_parts)

        if errors:
            return False, final_msg
        else:
            return True, final_msg

    def get_config(self) -> Dict:
        """获取当前完整配置字典"""
        return self._collect_config_from_forms()

    def get_config_path(self) -> Path:
        """获取配置文件路径"""
        return self._config_path

    def setFocusDevice(self, device_id: str) -> None:
        """
        切换到指定设备的配置编辑

        Args:
            device_id: 设备标识符（例如 "mcgs_1"）
        """
        if not device_id:
            return

        devices = self._config_data.get("devices", [])
        target_dev = None
        for d in devices:
            if isinstance(d, dict) and d.get("id") == device_id:
                target_dev = d
                break

        if target_dev:
            self._load_device_to_form(target_dev)
            logger.info(f"已切换到设备: {device_id}")
        else:
            self._original_device_id = device_id
            self.device_id_edit.setText(device_id)
            logger.warning(f"未找到设备 {device_id} 的配置，仅设置设备编号")

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

    def accept(self) -> None:
        """覆盖 QDialog.accept: 关闭前自动保存配置"""
        self._save_config()
        super().accept()

    def reject(self) -> None:
        """覆盖 QDialog.reject: 取消时提示未保存的更改"""
        current_config = self._collect_config_from_forms()
        saved_config = self._config_data
        current_devices = current_config.get("devices", []) if current_config else []
        saved_devices = saved_config.get("devices", []) if saved_config else []
        if current_devices != saved_devices:
            reply = QMessageBox.question(
                self,
                "确认关闭",
                "配置有未保存的更改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_config()
                super().accept()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
            else:
                super().reject()
        else:
            super().reject()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = MCGSConfigDialog()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        config = dialog.get_config()
        print(f"配置已确认:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
