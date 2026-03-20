import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QListWidget, QListWidgetItem, 
                            QLabel, QFrame, QGridLayout, QTableWidget,
                            QTableWidgetItem)
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
from PyQt5.QtCore import Qt, QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# 主窗口类
class IndustrialMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initData()
        self.initTimer()

    # 初始化UI
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle("设备管理系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置深色主题
        self.setDarkTheme()

        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧设备列表
        self.device_list = QListWidget()
        self.device_list.setFixedWidth(250)
        self.device_list.setStyleSheet("""QListWidget {
            background-color: #1E1E1E;
            border: 1px solid #2A2A2A;
            border-radius: 0;
        }
        QListWidgetItem {
            padding: 15px;
            margin: 5px;
            background-color: #2A2A2A;
            border-radius: 5px;
            color: white;
            font-size: 14px;
        }
        QListWidgetItem:hover {
            background-color: #3A3A3A;
        }
        QListWidget::item:selected {
            background-color: #00AAFF;
        }""")

        # 主内容区
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(10, 10, 10, 10)

        # 添加到主布局
        main_layout.addWidget(self.device_list)
        main_layout.addWidget(self.content_area)

        # 设置中心部件
        self.setCentralWidget(main_widget)

        # 创建顶部标题栏
        self.createTitleBar()
        
        # 创建实时趋势图
        self.createTrendChart()
        
        # 创建仪表盘区域
        self.createGauges()
        
        # 创建数据卡片
        self.createDataCards()
        
        # 创建Modbus寄存器表格
        self.createRegisterTable()

    # 设置深色主题
    def setDarkTheme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(40, 40, 40))
        palette.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
        palette.setColor(QPalette.ToolTipBase, QColor(30, 30, 30))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(0, 150, 255))
        palette.setColor(QPalette.Highlight, QColor(0, 150, 255))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        self.setPalette(palette)

    # 创建顶部标题栏
    def createTitleBar(self):
        title_frame = QFrame()
        title_frame.setFixedHeight(60)
        title_frame.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(20, 0, 20, 0)

        # 标题
        title_label = QLabel("⛽ Pump Station A")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #00AAFF;")
        title_layout.addWidget(title_label)

        # 右侧操作按钮
        buttons_frame = QFrame()
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setSpacing(15)

        for icon in ["👤", "📊", "🔔", "⚙️", "📋"]:
            btn = QLabel(icon)
            btn.setFont(QFont("Arial", 16))
            btn.setFixedSize(40, 40)
            btn.setAlignment(Qt.AlignCenter)
            btn.setStyleSheet("border-radius: 20px; background-color: #3A3A3A;")
            buttons_layout.addWidget(btn)

        title_layout.addStretch()
        title_layout.addWidget(buttons_frame)

        self.content_layout.addWidget(title_frame)

    # 创建实时趋势图
    def createTrendChart(self):
        chart_frame = QFrame()
        chart_frame.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        chart_layout = QVBoxLayout(chart_frame)

        # 图表标题
        chart_title = QLabel("实时趋势图")
        chart_title.setFont(QFont("Arial", 12, QFont.Bold))
        chart_title.setStyleSheet("color: white; padding: 10px;")
        chart_layout.addWidget(chart_title)

        # 创建Matplotlib图表
        self.figure = Figure(figsize=(10, 4), dpi=100, facecolor='#2A2A2A')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("border: none;")
        
        self.ax = self.figure.add_subplot(111, facecolor='#2A2A2A')
        self.ax.tick_params(axis='both', colors='#888888')
        self.ax.spines['bottom'].set_color('#888888')
        self.ax.spines['left'].set_color('#888888')
        self.ax.spines['right'].set_color('#888888')
        self.ax.spines['top'].set_color('#888888')
        
        # 生成初始数据
        self.x_data = np.arange(0, 100, 1)
        self.y_data = np.random.randn(100).cumsum() + 100
        
        # 绘制图表
        self.line, = self.ax.plot(self.x_data, self.y_data, color='#00FFAA', linewidth=2)
        
        chart_layout.addWidget(self.canvas)
        self.content_layout.addWidget(chart_frame)

    # 创建仪表盘区域
    def createGauges(self):
        gauge_frame = QFrame()
        gauge_frame.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        gauge_layout = QVBoxLayout(gauge_frame)

        # 仪表盘标题
        gauge_title = QLabel("仪表盘")
        gauge_title.setFont(QFont("Arial", 12, QFont.Bold))
        gauge_title.setStyleSheet("color: white; padding: 10px;")
        gauge_layout.addWidget(gauge_title)

        # 仪表盘网格
        gauges_grid = QGridLayout()
        gauges_grid.setSpacing(20)
        gauges_grid.setContentsMargins(20, 0, 20, 20)

        # 创建4个仪表盘
        self.gauge_labels = []
        for i, name in enumerate(["SQ10", "AR2", "B", ""]):
            gauge_container = QFrame()
            gauge_container.setStyleSheet("background-color: #3A3A3A; border-radius: 50px;")
            gauge_container.setFixedSize(120, 120)
            gauge_container_layout = QVBoxLayout(gauge_container)
            gauge_container_layout.setAlignment(Qt.AlignCenter)
            
            # 数值显示
            value_label = QLabel("0.0")
            value_label.setFont(QFont("Arial", 18, QFont.Bold))
            value_label.setStyleSheet("color: #00FFAA;")
            value_label.setAlignment(Qt.AlignCenter)
            
            # 名称显示
            name_label = QLabel(name)
            name_label.setFont(QFont("Arial", 10))
            name_label.setStyleSheet("color: white;")
            name_label.setAlignment(Qt.AlignCenter)
            
            gauge_container_layout.addWidget(value_label)
            gauge_container_layout.addWidget(name_label)
            
            gauges_grid.addWidget(gauge_container, 0, i)
            self.gauge_labels.append(value_label)

        gauge_layout.addLayout(gauges_grid)
        self.content_layout.addWidget(gauge_frame)

    # 创建数据卡片
    def createDataCards(self):
        cards_frame = QFrame()
        cards_frame.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        cards_layout = QVBoxLayout(cards_frame)

        # 卡片标题
        cards_title = QLabel("关键数据")
        cards_title.setFont(QFont("Arial", 12, QFont.Bold))
        cards_title.setStyleSheet("color: white; padding: 10px;")
        cards_layout.addWidget(cards_title)

        # 卡片网格
        cards_grid = QGridLayout()
        cards_grid.setSpacing(15)
        cards_grid.setContentsMargins(15, 0, 15, 15)

        # 创建3个数据卡片
        self.card_labels = []
        for i, (name, value) in enumerate([("Temperature", "25.5°C"),
                                           ("Pressure", "123 AsB"),
                                           ("Gas Concentration", "405 cAsB (123°C)")]):
            card = QFrame()
            card.setStyleSheet("background-color: #3A3A3A; border-radius: 5px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 15, 15, 15)
            
            # 卡片名称
            card_name = QLabel(name)
            card_name.setFont(QFont("Arial", 12))
            card_name.setStyleSheet("color: #AAAAAA;")
            
            # 卡片数值
            card_value = QLabel(value)
            card_value.setFont(QFont("Arial", 24, QFont.Bold))
            card_value.setStyleSheet("color: #00FFAA;")
            
            card_layout.addWidget(card_name)
            card_layout.addWidget(card_value)
            
            cards_grid.addWidget(card, 0, i)
            self.card_labels.append(card_value)

        cards_layout.addLayout(cards_grid)
        self.content_layout.addWidget(cards_frame)

    # 创建Modbus寄存器表格
    def createRegisterTable(self):
        table_frame = QFrame()
        table_frame.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        table_layout = QVBoxLayout(table_frame)

        # 表格标题
        table_title = QLabel("Modbus寄存器")
        table_title.setFont(QFont("Arial", 12, QFont.Bold))
        table_title.setStyleSheet("color: white; padding: 10px;")
        table_layout.addWidget(table_title)

        # 创建表格
        self.register_table = QTableWidget()
        self.register_table.setRowCount(3)
        self.register_table.setColumnCount(4)
        self.register_table.setHorizontalHeaderLabels(["address", "valate", "value", "status"])
        
        # 设置表格样式
        self.register_table.setStyleSheet("""QTableWidget {
            background-color: #3A3A3A;
            border: none;
            color: white;
        }
        QHeaderView::section {
            background-color: #2A2A2A;
            color: white;
            padding: 8px;
            border: 1px solid #4A4A4A;
        }
        QTableWidgetItem {
            background-color: #3A3A3A;
            color: white;
            padding: 8px;
            border: 1px solid #4A4A4A;
        }""")
        
        # 设置列宽
        self.register_table.setColumnWidth(0, 100)
        self.register_table.setColumnWidth(1, 100)
        self.register_table.setColumnWidth(2, 150)
        self.register_table.setColumnWidth(3, 100)
        
        table_layout.addWidget(self.register_table)
        self.content_layout.addWidget(table_frame)

    # 初始化数据
    def initData(self):
        # 初始化设备列表
        devices = ["Sensor Node B", "Sensor Node T", "Sensor Node A",
                  "Mirmor Node L", "LwllmpNode S", "Fansoh Loss"]
        
        for device in devices:
            item = QListWidgetItem(device)
            item.setFont(QFont("Arial", 14))
            item.setForeground(QColor("white"))
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.device_list.addItem(item)
        
        # 默认选中第一个设备
        if self.device_list.count() > 0:
            self.device_list.setCurrentRow(0)

        # 初始化仪表盘数据
        self.gauge_values = [75.5, 115.2, 12.8, 14.8]
        for i, value in enumerate(self.gauge_values):
            self.gauge_labels[i].setText(f"{value:.1f}")

        # 初始化Modbus寄存器数据
        register_data = [
            ["0x0001", "06", "25.5", "OK"],
            ["0x0001", "24", "20:25", "OK"],
            ["0x0001", "1", "10:55", "OK"]
        ]
        
        for row, data in enumerate(register_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                if col == 3:  # Status column
                    item.setForeground(QColor("#00FFAA"))
                self.register_table.setItem(row, col, item)

    # 初始化定时器
    def initTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateData)
        self.timer.start(1000)  # 每秒更新一次

    # 更新实时数据
    def updateData(self):
        # 更新趋势图数据
        self.y_data = np.roll(self.y_data, -1)
        self.y_data[-1] = self.y_data[-2] + (np.random.randn() * 2 - 1)
        self.line.set_ydata(self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        # 更新仪表盘数据
        for i in range(len(self.gauge_values)):
            self.gauge_values[i] += (np.random.randn() * 0.5)
            self.gauge_values[i] = max(0, min(100, self.gauge_values[i]))
            self.gauge_labels[i].setText(f"{self.gauge_values[i]:.1f}")

        # 更新数据卡片
        # 这里可以添加更复杂的数据更新逻辑

# 主程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IndustrialMonitorApp()
    window.show()
    sys.exit(app.exec_())
