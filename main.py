"""
设备管理系统 - 工业监控上位机
主程序入口
Version: 1.0
"""
import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QFrame, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QPushButton, QComboBox, QProgressBar
)
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt, QTimer, QRectF, QDateTime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from gauge import CircularGauge
from trend_chart import RealTimeTrendChart
from data_card import DataCard
from modbus_table import ModbusRegisterTable


class IndustrialMonitorApp(QMainWindow):
    """Industrial Monitor Main Window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Equipment Management System")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)

        # Initialize data
        self.init_data()
        # Initialize UI
        self.init_ui()
        # Initialize timer
        self.init_timer()

    def init_data(self):
        """初始化数据"""
        self.temperature = 25.5
        self.pressure = 123.4
        self.gas_concentration = 405.0
        self.humidity = 38.2

        self.gauge_values = {"SQ10": 75.5, "AR2": 115.2, "B": 12.8, "C": 14.8}

    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.create_sidebar(main_layout)
        self.create_content_area(main_layout)

    def create_sidebar(self, parent_layout):
        """Create sidebar"""
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("background-color: #1E1E1E; border-right: 1px solid #2A2A2A;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        title_bar = QFrame()
        title_bar.setFixedHeight(70)
        title_bar.setStyleSheet("background-color: #252525; border-bottom: 1px solid #2A2A2A;")
        t_layout = QHBoxLayout(title_bar)
        t_layout.setContentsMargins(15, 0, 15, 0)

        t_layout.addWidget(QLabel("🏭"))
        t_layout.addWidget(QLabel("Device List").setFont(QFont("Microsoft YaHei", 14, QFont.Bold)))
        t_layout.addStretch()

        self.device_count = QLabel("6 Devices")
        self.device_count.setFont(QFont("Microsoft YaHei", 9))
        self.device_count.setStyleSheet("color: #888888; background-color: #3A3A3A; padding: 3px 10px; border-radius: 10px;")
        t_layout.addWidget(self.device_count)
        layout.addWidget(title_bar)

        # 设备列表
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("""
            QListWidget { background-color: #1E1E1E; border: none; }
            QListWidget::item { padding: 15px; margin: 5px 10px; background-color: #252525; border-radius: 6px; color: #FFF; }
            QListWidget::item:hover { background-color: #2D2D2D; }
            QListWidget::item:selected { background-color: #0078D4; }
        """)

        devices = [
            ("Sensor Node B", "🌡️", "Online"),
            ("Sensor Node T", "🌡️", "Online"),
            ("Sensor Node A", "🌡️", "Online"),
            ("Mirror Node L", "🔒", "Offline"),
            ("WallPump Node S", "💨", "Online"),
            ("Fansoh Loss", "⚡", "Online"),
        ]

        for name, icon, status in devices:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, name)

            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(10, 8, 10, 8)

            h = QHBoxLayout()
            h.addWidget(QLabel(icon))
            h.addWidget(QLabel(name).setFont(QFont("Microsoft YaHei", 12)))
            h.addStretch()

            s = QLabel(status)
            s.setFont(QFont("Microsoft YaHei", 9))
            if status == "Online":
                s.setStyleSheet("color: #00FFAA; background-color: #1A3A2A; padding: 2px 8px; border-radius: 3px;")
            else:
                s.setStyleSheet("color: #888888; background-color: #2A2A2A; padding: 2px 8px; border-radius: 3px;")
            h.addWidget(s)

            v.addLayout(h)
            item.setSizeHint(w.sizeHint())
            self.device_list.addItem(item)
            self.device_list.setItemWidget(item, w)

        self.device_list.setCurrentRow(0)
        layout.addWidget(self.device_list)

        # 连接状态栏
        conn_bar = QFrame()
        conn_bar.setFixedHeight(60)
        conn_bar.setStyleSheet("background-color: #252525; border-top: 1px solid #2A2A2A;")
        c_layout = QHBoxLayout(conn_bar)
        c_layout.setContentsMargins(15, 0, 15, 0)

        self.conn_status = QLabel("● Serial Connected")
        self.conn_status.setFont(QFont("Microsoft YaHei", 10))
        self.conn_status.setStyleSheet("color: #00FFAA;")
        c_layout.addWidget(self.conn_status)
        c_layout.addStretch()

        settings_btn = QPushButton("Settings")
        settings_btn.setFixedSize(50, 28)
        settings_btn.setStyleSheet("QPushButton { background-color: #3A3A3A; color: #FFF; border: none; border-radius: 4px; }")
        c_layout.addWidget(settings_btn)

        layout.addWidget(conn_bar)
        parent_layout.addWidget(sidebar)

    def create_content_area(self, parent_layout):
        """Create content area"""
        content = QWidget()
        content.setStyleSheet("background-color: #1A1A1A;")
        v = QVBoxLayout(content)
        v.setSpacing(10)
        v.setContentsMargins(15, 15, 15, 15)

        self.create_top_bar(v)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll_content = QWidget()
        sv = QVBoxLayout(scroll_content)
        sv.setSpacing(10)

        self.create_trend_section(sv)
        self.create_gauge_section(sv)
        self.create_cards_section(sv)
        self.create_modbus_section(sv)

        scroll.setWidget(scroll_content)
        v.addWidget(scroll)
        parent_layout.addWidget(content)

    def create_top_bar(self, parent_layout):
        """Create top bar"""
        bar = QFrame()
        bar.setFixedHeight(70)
        bar.setStyleSheet("background-color: #2A2A2A; border-radius: 8px;")
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)

        h.addWidget(QLabel("⛽"))
        self.device_title = QLabel("Pump Station A")
        self.device_title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        self.device_title.setStyleSheet("color: #00AAFF;")
        h.addWidget(self.device_title)
        h.addStretch()

        for icon in ["👤", "📊", "🔔", "⚙️"]:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("QPushButton { background-color: #3A3A3A; border: none; border-radius: 20px; }")
            h.addWidget(btn)

        self.time_label = QLabel()
        self.time_label.setFont(QFont("Consolas", 12))
        self.time_label.setStyleSheet("color: #888888;")
        h.addWidget(self.time_label)

        parent_layout.addWidget(bar)

    def create_trend_section(self, parent_layout):
        """Trend section"""
        frame = QFrame()
        frame.setStyleSheet("background-color: #2A2A2A; border-radius: 8px;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 10, 10, 10)

        title_h = QHBoxLayout()
        title_h.addWidget(QLabel("Real-Time Trend").setFont(QFont("Microsoft YaHei", 12, QFont.Bold)))
        title_h.addStretch()

        for text, color in [("Temp", "#FF6B6B"), ("Pressure", "#4ECDC4"), ("Clear", "#888888")]:
            btn = QPushButton(text)
            btn.setFixedSize(50, 26)
            btn.setStyleSheet(f"QPushButton {{ background-color: {color}33; color: {color}; border: 1px solid {color}; border-radius: 4px; }}")
            title_h.addWidget(btn)

        v.addLayout(title_h)

        self.trend_chart = RealTimeTrendChart(title="Temperature Trend (C)")
        v.addWidget(self.trend_chart)

        parent_layout.addWidget(frame)

    def create_gauge_section(self, parent_layout):
        """Gauge section"""
        frame = QFrame()
        frame.setStyleSheet("background-color: #2A2A2A; border-radius: 8px;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 10, 10, 10)

        v.addWidget(QLabel("Dashboard").setFont(QFont("Microsoft YaHei", 12, QFont.Bold)))

        grid = QGridLayout()
        grid.setSpacing(20)

        self.gauges = {}
        gauge_data = [("SQ10", 0, 150, "bar"), ("AR2", 0, 200, "psi"),
                       ("B", 0, 50, "kPa"), ("C", 0, 30, "°C")]

        for i, (name, min_v, max_v, unit) in enumerate(gauge_data):
            gauge = CircularGauge(min_value=min_v, max_value=max_v, unit=unit, title=name)
            gauge.setValue(self.gauge_values[name])
            self.gauges[name] = gauge
            grid.addWidget(gauge, 0, i)

        v.addLayout(grid)
        parent_layout.addWidget(frame)

    def create_cards_section(self, parent_layout):
        """Data cards section"""
        frame = QFrame()
        frame.setStyleSheet("background-color: #2A2A2A; border-radius: 8px;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 10, 10, 10)

        v.addWidget(QLabel("Key Data").setFont(QFont("Microsoft YaHei", 12, QFont.Bold)))

        grid = QGridLayout()
        grid.setSpacing(15)

        self.cards = {}
        card_data = [
            ("temperature", "Temperature", "°C", "🌡️"),
            ("pressure", "Pressure", "AsB", "⚡"),
            ("gas_concentration", "Gas Concentration", "cAsB", "💨"),
            ("humidity", "Humidity", "%RH", "💧"),
        ]

        for i, (key, title, unit, icon) in enumerate(card_data):
            card = DataCard(title=title, unit=unit, icon=icon)
            value = getattr(self, key)
            card.setValue(value)
            self.cards[key] = card
            grid.addWidget(card, 0, i)

        v.addLayout(grid)
        parent_layout.addWidget(frame)

    def create_modbus_section(self, parent_layout):
        """Modbus register section"""
        frame = QFrame()
        frame.setStyleSheet("background-color: #2A2A2A; border-radius: 8px;")
        v = QVBoxLayout(frame)
        v.setContentsMargins(10, 10, 10, 10)

        v.addWidget(QLabel("Modbus Registers").setFont(QFont("Microsoft YaHei", 12, QFont.Bold)))

        self.modbus_table = ModbusRegisterTable()
        v.addWidget(self.modbus_table)

        parent_layout.addWidget(frame)

    def init_timer(self):
        """Initialize timer"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)

    def update_data(self):
        """Update data"""
        # Update time
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.time_label.setText(now)

        # Update trend chart
        self.trend_chart.update_data(self.temperature + np.random.randn() * 2)

        # Update gauges
        for name in self.gauges:
            self.gauge_values[name] += np.random.randn() * 0.5
            self.gauge_values[name] = max(0, min(100, self.gauge_values[name]))
            self.gauges[name].setValue(self.gauge_values[name])

        # Update data cards
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
    palette = QColor(30, 30, 30)
    app.setPalette(palette)

    window = IndustrialMonitorApp()
    window.show()
    sys.exit(app.exec_())
