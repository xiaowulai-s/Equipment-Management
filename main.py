"""
设备管理系统 - 工业监控上位机
主程序入口 v2.0
基于现代化工业UI设计规范
"""
import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QFrame, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QPushButton, QComboBox, QProgressBar, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient, QIcon
from PyQt5.QtCore import Qt, QTimer, QRectF, QDateTime, pyqtSignal, QObject

from gauge import CircularGauge
from trend_chart import RealTimeTrendChart
from data_card import DataCard
from modbus_table import ModbusRegisterTable


class IndustrialMonitorApp(QMainWindow):
    """Industrial Monitor Main Window - Modern Dark Theme"""

    # 颜色系统 - 基于UI设计方案的深色主题
    COLORS = {
        # 背景色
        'bg_primary': '#0F1419',      # 最深背景
        'bg_secondary': '#161B22',    # 卡片/面板
        'bg_tertiary': '#1C2128',     # 弹窗/下拉
        'bg_hover': '#21262D',        # 悬停
        'bg_active': '#30363D',       # 激活

        # 文本色
        'text_primary': '#E6EDF3',    # 主要文本
        'text_secondary': '#8B949E',  # 次要文本
        'text_tertiary': '#6E7681',   # 禁用/提示

        # 边框色
        'border_default': '#30363D',
        'border_muted': '#21262D',
        'border_accent': '#388BFD',

        # 主色
        'primary': '#2196F3',
        'primary_light': '#64B5F6',
        'accent': '#00BCD4',

        # 状态色
        'success': '#3FB950',
        'success_bg': 'rgba(63, 185, 80, 0.15)',
        'warning': '#D29922',
        'warning_bg': 'rgba(210, 153, 34, 0.15)',
        'error': '#F85149',
        'error_bg': 'rgba(248, 81, 73, 0.15)',
        'info': '#388BFD',
        'info_bg': 'rgba(56, 139, 253, 0.15)',
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Equipment Management System - Industrial Monitor")
        self.setGeometry(100, 100, 1500, 950)
        self.setMinimumSize(1280, 800)

        # 初始化数据
        self.init_data()
        # 初始化UI
        self.init_ui()
        # 初始化定时器
        self.init_timer()

    def init_data(self):
        """初始化数据"""
        self.temperature = 25.5
        self.pressure = 123.4
        self.gas_concentration = 405.0
        self.humidity = 38.2

        self.gauge_values = {"SQ10": 75.5, "AR2": 115.2, "B": 12.8, "C": 14.8}

        # 设备列表
        self.devices = [
            {"name": "Pump Station A", "type": "Pump", "status": "online", "icon": "P"},
            {"name": "Sensor Node B", "type": "Sensor", "status": "online", "icon": "S"},
            {"name": "Sensor Node T", "type": "Sensor", "status": "online", "icon": "S"},
            {"name": "Sensor Node A", "type": "Sensor", "status": "online", "icon": "S"},
            {"name": "Mirror Node L", "type": "Mirror", "status": "offline", "icon": "M"},
            {"name": "WallPump Node S", "type": "Pump", "status": "online", "icon": "P"},
            {"name": "Fansoh Loss", "type": "Fan", "status": "online", "icon": "F"},
        ]
        self.selected_device = 0

    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {self.COLORS['bg_primary']};")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.create_sidebar(main_layout)
        self.create_content_area(main_layout)

    def create_sidebar(self, parent_layout):
        """Create sidebar with device list"""
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-right: 1px solid {self.COLORS['border_default']};
        """)

        layout = QVBoxLayout(sidebar)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Logo区域
        self.create_sidebar_header(layout)

        # 设备列表
        self.create_device_list(layout)

        # 底部状态栏
        self.create_sidebar_footer(layout)

        parent_layout.addWidget(sidebar)

    def create_sidebar_header(self, parent_layout):
        """Logo和标题区域"""
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-bottom: 1px solid {self.COLORS['border_default']};
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        # Logo
        logo_frame = QFrame()
        logo_frame.setFixedSize(40, 40)
        logo_frame.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                spread:pad, stops:0px 0% {self.COLORS['primary']},
                100% {self.COLORS['accent']});
            border-radius: 8px;
        """)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_icon = QLabel("EM")
        logo_icon.setFont(QFont("Segoe UI", 14, QFont.Bold))
        logo_icon.setStyleSheet("color: white;")
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(logo_icon)
        h_layout.addWidget(logo_frame)

        # 系统标题
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title = QLabel("Equipment MGMT")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        title_layout.addWidget(title)

        subtitle = QLabel("Industrial Monitoring System")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet(f"color: {self.COLORS['text_tertiary']};")
        title_layout.addWidget(subtitle)

        h_layout.addLayout(title_layout)
        h_layout.addStretch()

        # 在线设备数量
        self.online_count = QLabel("5 Online")
        self.online_count.setFont(QFont("Segoe UI", 10))
        self.online_count.setStyleSheet(f"""
            color: {self.COLORS['success']};
            background-color: {self.COLORS['success_bg']};
            padding: 4px 12px;
            border-radius: 12px;
        """)
        h_layout.addWidget(self.online_count)

        parent_layout.addWidget(header)

    def create_device_list(self, parent_layout):
        """创建设备列表"""
        list_container = QFrame()
        list_container.setStyleSheet(f"background-color: {self.COLORS['bg_secondary']};")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(12, 12, 12, 12)

        # 列表标题
        list_header = QHBoxLayout()
        list_header.setSpacing(8)

        list_title = QLabel("DEVICES")
        list_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        list_title.setStyleSheet(f"color: {self.COLORS['text_tertiary']}; letter-spacing: 1px;")
        list_header.addWidget(list_title)

        list_header.addStretch()

        # 搜索图标按钮
        search_btn = QPushButton("🔍")
        search_btn.setFixedSize(28, 28)
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['bg_tertiary']};
                border: none;
                border-radius: 6px;
                color: {self.COLORS['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['bg_hover']};
            }}
        """)
        list_header.addWidget(search_btn)

        list_layout.addLayout(list_header)

        # 设备列表
        self.device_list = QListWidget()
        self.device_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border-radius: 8px;
                margin-bottom: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {self.COLORS['info_bg']};
            }}
        """)
        self.device_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.device_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        for i, device in enumerate(self.devices):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, i)

            widget = self.create_device_item(device)
            item.setSizeHint(widget.sizeHint())
            self.device_list.addItem(item)
            self.device_list.setItemWidget(item, widget)

        self.device_list.currentItemChanged.connect(self.on_device_selected)
        self.device_list.setCurrentRow(0)
        list_layout.addWidget(self.device_list)

        parent_layout.addWidget(list_container, 1)

    def create_device_item(self, device):
        """创建设备项组件"""
        widget = QFrame()
        widget.setFixedHeight(64)
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLORS['bg_tertiary']};
                border-radius: 8px;
                border: 1px solid transparent;
            }}
            QFrame:hover {{
                background-color: {self.COLORS['bg_hover']};
                border: 1px solid {self.COLORS['border_default']};
            }}
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 0, 12, 0)

        # 状态指示灯
        status_color = self.COLORS['success'] if device['status'] == 'online' else self.COLORS['error']
        status_dot = QLabel()
        status_dot.setFixedSize(10, 10)
        status_dot.setStyleSheet(f"""
            background-color: {status_color};
            border-radius: 5px;
            {'animation: pulse 2s infinite;' if device['status'] == 'online' else ''}
        """)

        # 设备图标
        icon_label = QLabel(device['icon'])
        icon_label.setFixedSize(36, 36)
        icon_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            color: {self.COLORS['text_primary']};
            background-color: {self.COLORS['bg_hover']};
            border-radius: 8px;
        """)

        # 设备信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(device['name'])
        name_label.setFont(QFont("Segoe UI", 12, QFont.Medium))
        name_label.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        info_layout.addWidget(name_label)

        type_label = QLabel(device['type'])
        type_label.setFont(QFont("Segoe UI", 10))
        type_label.setStyleSheet(f"color: {self.COLORS['text_tertiary']};")
        info_layout.addWidget(type_label)

        layout.addWidget(status_dot)
        layout.addWidget(icon_label)
        layout.addLayout(info_layout)
        layout.addStretch()

        # 状态标签
        status_label = QLabel(device['status'].upper())
        status_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        status_bg = self.COLORS['success_bg'] if device['status'] == 'online' else self.COLORS['error_bg']
        status_color = self.COLORS['success'] if device['status'] == 'online' else self.COLORS['error']
        status_label.setStyleSheet(f"""
            color: {status_color};
            background-color: {status_bg};
            padding: 3px 8px;
            border-radius: 4px;
        """)
        layout.addWidget(status_label)

        return widget

    def create_sidebar_footer(self, parent_layout):
        """底部连接状态栏"""
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-top: 1px solid {self.COLORS['border_default']};
        """)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 0, 20, 0)

        # 连接状态
        self.conn_indicator = QLabel("●")
        self.conn_indicator.setStyleSheet(f"color: {self.COLORS['success']}; font-size: 10px;")
        f_layout.addWidget(self.conn_indicator)

        self.conn_label = QLabel("Modbus TCP Connected")
        self.conn_label.setFont(QFont("Segoe UI", 10))
        self.conn_label.setStyleSheet(f"color: {self.COLORS['text_secondary']};")
        f_layout.addWidget(self.conn_label)

        f_layout.addStretch()

        # 设置按钮
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['bg_tertiary']};
                border: none;
                border-radius: 6px;
                color: {self.COLORS['text_secondary']};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['bg_hover']};
                color: {self.COLORS['text_primary']};
            }}
        """)
        f_layout.addWidget(settings_btn)

        parent_layout.addWidget(footer)

    def on_device_selected(self, current, previous):
        """设备选择改变"""
        if current:
            self.selected_device = current.data(Qt.UserRole)

    def create_content_area(self, parent_layout):
        """Create main content area"""
        content = QWidget()
        content.setStyleSheet(f"background-color: {self.COLORS['bg_primary']};")
        v = QVBoxLayout(content)
        v.setSpacing(16)
        v.setContentsMargins(24, 24, 24, 24)

        # 顶部栏
        self.create_top_bar(v)

        # 可滚动内容区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        sv = QVBoxLayout(scroll_content)
        sv.setSpacing(16)

        # 趋势图区域
        self.create_trend_section(sv)

        # 仪表盘和数据卡片区域
        h_container = QWidget()
        h_layout = QHBoxLayout(h_container)
        h_layout.setSpacing(16)
        h_layout.setContentsMargins(0, 0, 0, 0)

        self.create_gauge_section(h_layout)
        self.create_cards_section(h_layout)

        sv.addWidget(h_container)

        # Modbus寄存器表格
        self.create_modbus_section(sv)

        # 操作面板
        self.create_control_panel(sv)

        scroll.setWidget(scroll_content)
        v.addWidget(scroll, 1)

        parent_layout.addWidget(content, 1)

    def create_top_bar(self, parent_layout):
        """Create top bar with device info"""
        bar = QFrame()
        bar.setFixedHeight(80)
        bar.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-radius: 12px;
            border: 1px solid {self.COLORS['border_default']};
        """)
        h = QHBoxLayout(bar)
        h.setContentsMargins(24, 0, 24, 0)

        # 设备图标
        device_icon = QLabel("P")
        device_icon.setFixedSize(48, 48)
        device_icon.setFont(QFont("Segoe UI", 18, QFont.Bold))
        device_icon.setAlignment(Qt.AlignCenter)
        device_icon.setStyleSheet(f"""
            color: white;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                spread:pad, stops:0px 0% {self.COLORS['primary']},
                100% {self.COLORS['accent']});
            border-radius: 10px;
        """)
        h.addWidget(device_icon)

        # 设备信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.device_title = QLabel("Pump Station A")
        self.device_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.device_title.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        info_layout.addWidget(self.device_title)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        status_dot = QLabel("●")
        status_dot.setStyleSheet(f"color: {self.COLORS['success']}; font-size: 10px;")
        status_layout.addWidget(status_dot)

        status_text = QLabel("Online | IP: 192.168.1.100 | Unit ID: 1")
        status_text.setFont(QFont("Segoe UI", 11))
        status_text.setStyleSheet(f"color: {self.COLORS['text_secondary']};")
        status_layout.addWidget(status_text)

        info_layout.addLayout(status_layout)

        h.addLayout(info_layout)
        h.addStretch()

        # 操作按钮
        for icon, name in [("👤", "User"), ("📊", "Report"), ("🔔", "Alert"), ("⚙", "Settings")]:
            btn = QPushButton(icon)
            btn.setFixedSize(44, 44)
            btn.setToolTip(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.COLORS['bg_tertiary']};
                    border: 1px solid {self.COLORS['border_default']};
                    border-radius: 10px;
                    color: {self.COLORS['text_secondary']};
                }}
                QPushButton:hover {{
                    background-color: {self.COLORS['bg_hover']};
                    border-color: {self.COLORS['border_accent']};
                    color: {self.COLORS['text_primary']};
                }}
            """)
            h.addWidget(btn)

        # 时间显示
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Consolas", 12))
        self.time_label.setStyleSheet(f"color: {self.COLORS['text_tertiary']};")
        h.addWidget(self.time_label)

        parent_layout.addWidget(bar)

    def create_trend_section(self, parent_layout):
        """Trend section with real-time chart"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-radius: 12px;
            border: 1px solid {self.COLORS['border_default']};
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(16, 16, 16, 16)

        # 标题栏
        title_h = QHBoxLayout()
        title_h.setSpacing(12)

        title = QLabel("Real-Time Trend")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        title_h.addWidget(title)

        # 图例
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(16)

        for name, color in [("Temperature", "#FF6B6B"), ("Pressure", "#4ECDC4"), ("Gas", "#45B7D1")]:
            legend_item = QHBoxLayout()
            legend_item.setSpacing(6)

            dot = QLabel()
            dot.setFixedSize(12, 4)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            legend_item.addWidget(dot)

            text = QLabel(name)
            text.setFont(QFont("Segoe UI", 10))
            text.setStyleSheet(f"color: {self.COLORS['text_secondary']};")
            legend_item.addWidget(text)

            legend_layout.addLayout(legend_item)

        title_h.addLayout(legend_layout)
        title_h.addStretch()

        # 时间范围按钮
        for text in ["1H", "6H", "24H", "ALL"]:
            btn = QPushButton(text)
            btn.setFixedSize(44, 28)
            btn.setFont(QFont("Segoe UI", 10))
            if text == "1H":
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.COLORS['primary']};
                        border: none;
                        border-radius: 6px;
                        color: white;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.COLORS['bg_tertiary']};
                        border: none;
                        border-radius: 6px;
                        color: {self.COLORS['text_secondary']};
                    }}
                    QPushButton:hover {{
                        background-color: {self.COLORS['bg_hover']};
                        color: {self.COLORS['text_primary']};
                    }}
                """)
            title_h.addWidget(btn)

        v.addLayout(title_h)

        # 趋势图
        self.trend_chart = RealTimeTrendChart(title="")
        v.addWidget(self.trend_chart)

        parent_layout.addWidget(frame)

    def create_gauge_section(self, parent_layout):
        """Gauge section"""
        frame = QFrame()
        frame.setMinimumWidth(420)
        frame.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-radius: 12px;
            border: 1px solid {self.COLORS['border_default']};
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(16, 16, 16, 16)

        # 标题
        title = QLabel("Dashboard")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        v.addWidget(title)

        # 仪表盘网格
        grid = QGridLayout()
        grid.setSpacing(16)

        self.gauges = {}
        gauge_data = [
            ("SQ10", 0, 150, "bar", 0),
            ("AR2", 0, 200, "psi", 0),
            ("B", 0, 50, "kPa", 1),
            ("C", 0, 30, "°C", 1),
        ]

        for name, min_v, max_v, unit, col in gauge_data:
            gauge = CircularGauge(min_value=min_v, max_value=max_v, unit=unit, title=name)
            gauge.setValue(self.gauge_values[name])
            self.gauges[name] = gauge
            row = 0 if name in ["SQ10", "AR2"] else 1
            grid.addWidget(gauge, row, col)

        v.addLayout(grid)
        parent_layout.addWidget(frame)

    def create_cards_section(self, parent_layout):
        """Data cards section"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-radius: 12px;
            border: 1px solid {self.COLORS['border_default']};
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(16, 16, 16, 16)

        # 标题
        title = QLabel("Key Data")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        v.addWidget(title)

        # 卡片网格
        grid = QGridLayout()
        grid.setSpacing(12)

        self.cards = {}
        card_data = [
            ("temperature", "Temperature", "°C", "🌡️", "#FF6B6B"),
            ("pressure", "Pressure", "AsB", "⚡", "#4ECDC4"),
            ("gas_concentration", "Gas Conc", "cAsB", "💨", "#45B7D1"),
            ("humidity", "Humidity", "%RH", "💧", "#96CEB4"),
        ]

        for i, (key, title, unit, icon, color) in enumerate(card_data):
            card = DataCard(title=title, unit=unit, icon=icon, accent_color=color)
            value = getattr(self, key)
            card.setValue(value)
            self.cards[key] = card
            row = 0 if i < 2 else 1
            col = i % 2
            grid.addWidget(card, row, col)

        v.addLayout(grid)
        parent_layout.addWidget(frame)

    def create_modbus_section(self, parent_layout):
        """Modbus register section"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-radius: 12px;
            border: 1px solid {self.COLORS['border_default']};
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(16, 16, 16, 16)

        # 标题栏
        title_h = QHBoxLayout()

        title = QLabel("Modbus Registers")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        title_h.addWidget(title)

        title_h.addStretch()

        # 功能码标签
        func_label = QLabel("Function: 03H (Read Holding Registers)")
        func_label.setFont(QFont("Segoe UI", 10))
        func_label.setStyleSheet(f"color: {self.COLORS['text_tertiary']};")
        title_h.addWidget(func_label)

        v.addLayout(title_h)

        # 寄存器表格
        self.modbus_table = ModbusRegisterTable()
        v.addWidget(self.modbus_table)

        parent_layout.addWidget(frame)

    def create_control_panel(self, parent_layout):
        """Control panel section"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {self.COLORS['bg_secondary']};
            border-radius: 12px;
            border: 1px solid {self.COLORS['border_default']};
        """)
        v = QVBoxLayout(frame)
        v.setContentsMargins(16, 16, 16, 16)

        # 标题
        title = QLabel("Device Control")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {self.COLORS['text_primary']};")
        v.addWidget(title)

        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        controls = [
            ("Start", "▶", self.COLORS['success'], self.COLORS['success_bg']),
            ("Stop", "⏹", self.COLORS['error'], self.COLORS['error_bg']),
            ("Reset", "🔄", self.COLORS['warning'], self.COLORS['warning_bg']),
            ("Settings", "⚙", self.COLORS['info'], self.COLORS['info_bg']),
        ]

        for name, icon, color, bg_color in controls:
            btn = QPushButton(f"{icon}  {name}")
            btn.setFixedHeight(44)
            btn.setFont(QFont("Segoe UI", 12, QFont.Medium))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: {color};
                    border: 1px solid {color}40;
                    border-radius: 8px;
                    padding: 0 24px;
                }}
                QPushButton:hover {{
                    background-color: {color}30;
                    border-color: {color};
                }}
                QPushButton:pressed {{
                    background-color: {color}50;
                }}
            """)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()

        v.addLayout(btn_layout)

        parent_layout.addWidget(frame)

    def init_timer(self):
        """Initialize timer"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)

    def update_data(self):
        """Update data"""
        # 更新时间
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd  hh:mm:ss")
        self.time_label.setText(now)

        # 更新趋势图
        new_temp = self.temperature + np.random.randn() * 2
        self.trend_chart.update_data(new_temp)

        # 更新仪表盘
        for name in self.gauges:
            self.gauge_values[name] += np.random.randn() * 0.5
            self.gauge_values[name] = max(0, min(100, self.gauge_values[name]))
            self.gauges[name].setValue(self.gauge_values[name])

        # 更新数据卡片
        self.temperature += np.random.randn() * 0.3
        self.pressure += np.random.randn() * 0.5
        self.gas_concentration += np.random.randn() * 2
        self.humidity += np.random.randn() * 0.2

        self.cards["temperature"].setValue(self.temperature)
        self.cards["pressure"].setValue(self.pressure)
        self.cards["gas_concentration"].setValue(self.gas_concentration)
        self.cards["humidity"].setValue(self.humidity)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置深色主题
    app.setStyleSheet(f"""
        QToolTip {{
            background-color: {IndustrialMonitorApp.COLORS['bg_tertiary']};
            color: {IndustrialMonitorApp.COLORS['text_primary']};
            border: 1px solid {IndustrialMonitorApp.COLORS['border_default']};
            padding: 4px 8px;
            border-radius: 4px;
        }}
        QScrollBar:vertical {{
            background: {IndustrialMonitorApp.COLORS['bg_primary']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {IndustrialMonitorApp.COLORS['bg_active']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:hover {{
            background: {IndustrialMonitorApp.COLORS['text_tertiary']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """)

    window = IndustrialMonitorApp()
    window.show()
    sys.exit(app.exec_())