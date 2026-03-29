"""
可视化组件集成测试示例

演示如何在 MainWindow 中使用 DataCard、Gauge、TrendChart 组件。
"""

import sys
from datetime import datetime, timedelta

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QGridLayout, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from ui.widgets.data_card import DataCard
from ui.widgets.gauge import Gauge
from ui.widgets.trend_chart import TrendChart


class ComponentTestWindow(QMainWindow):
    """可视化组件测试窗口

    演示:
    - DataCard (数据卡片)
    - Gauge (仪表盘)
    - TrendChart (趋势图)
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("可视化组件集成测试")
        self.setGeometry(100, 100, 1200, 800)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # === 第一行: 数据卡片 (4个) ===
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        # 温度卡片
        self.temp_card = DataCard("温度", "°C")
        self.temp_card.set_value(25.5, 0)  # 不变
        self.temp_card.set_status("normal")
        cards_layout.addWidget(self.temp_card)

        # 压力卡片
        self.pressure_card = DataCard("压力", "MPa")
        self.pressure_card.set_value(1.2, 1)  # 上升
        self.pressure_card.set_status("warning")
        cards_layout.addWidget(self.pressure_card)

        # 流量卡片
        self.flow_card = DataCard("流量", "m³/h")
        self.flow_card.set_value(50.0, -1)  # 下降
        self.flow_card.set_status("error")
        cards_layout.addWidget(self.flow_card)

        # 转速卡片
        self.speed_card = DataCard("转速", "rpm")
        self.speed_card.set_value(1500.0, 0)  # 不变
        self.speed_card.set_status("normal")
        cards_layout.addWidget(self.speed_card)

        main_layout.addLayout(cards_layout)

        # === 第二行: 仪表盘 (3个) ===
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(20)

        # 压力仪表盘
        self.pressure_gauge = Gauge("系统压力", "MPa", 0.0, 2.0)
        self.pressure_gauge.set_value(1.2)
        self.pressure_gauge.set_status("warning")
        gauges_layout.addWidget(self.pressure_gauge)

        # 温度仪表盘
        self.temp_gauge = Gauge("系统温度", "°C", 0.0, 100.0)
        self.temp_gauge.set_value(45.5)
        self.temp_gauge.set_status("normal")
        gauges_layout.addWidget(self.temp_gauge)

        # 液位仪表盘
        self.level_gauge = Gauge("液位", "%", 0.0, 100.0)
        self.level_gauge.set_value(85.0)
        self.level_gauge.set_status("error")  # 高液位报警
        gauges_layout.addWidget(self.level_gauge)

        main_layout.addLayout(gauges_layout)

        # === 第三行: 趋势图 ===
        charts_layout = QGridLayout()

        # 温度趋势图
        self.temp_chart = TrendChart()
        self.temp_chart.setMinimumHeight(300)
        self.temp_chart.add_series("温度", QColor("#FF5722"))
        self.temp_chart.set_y_range(20.0, 50.0)
        charts_layout.addWidget(self.temp_chart, 0, 0, 1, 2)

        # 压力趋势图
        self.pressure_chart = TrendChart()
        self.pressure_chart.setMinimumHeight(300)
        self.pressure_chart.add_series("压力", QColor("#2196F3"))
        self.pressure_chart.set_y_range(0.0, 2.0)
        charts_layout.addWidget(self.pressure_chart, 0, 2, 1, 2)

        main_layout.addLayout(charts_layout)

        # === 数据初始化 ===
        self._init_chart_data()

        # === 定时器 - 模拟实时数据更新 ===
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_data)
        self.timer.start(1000)  # 每秒更新一次

        self._time_counter = 0

    def _init_chart_data(self):
        """初始化趋势图数据"""
        now = datetime.now()

        # 温度数据 (最近60秒)
        for i in range(60):
            timestamp = (now - timedelta(seconds=60 - i)).timestamp()
            value = 25.0 + i * 0.1 + (i % 5) * 0.5
            self.temp_chart.add_point("温度", timestamp, value)

        # 压力数据 (最近60秒)
        for i in range(60):
            timestamp = (now - timedelta(seconds=60 - i)).timestamp()
            value = 1.0 + i * 0.005 + (i % 7) * 0.05
            self.pressure_chart.add_point("压力", timestamp, value)

    def _update_data(self):
        """更新实时数据 (模拟)"""
        self._time_counter += 1
        now = datetime.now()
        timestamp = now.timestamp()

        # === 更新温度数据 ===
        # 模拟温度波动 (25.0 - 30.0)
        temp_value = 25.0 + (self._time_counter % 10) * 0.5 + (self._time_counter % 5) * 0.3
        self.temp_card.set_value(temp_value, 1 if self._time_counter % 2 == 0 else -1)
        self.temp_gauge.set_value(temp_value)
        self.temp_chart.add_point("温度", timestamp, temp_value)

        # 保持数据点数量不超过 60
        if len(self.temp_chart._series[0][2]) > 60:
            self.temp_chart._series[0][2].pop(0)

        # === 更新压力数据 ===
        # 模拟压力波动 (1.0 - 1.5)
        pressure_value = 1.0 + (self._time_counter % 8) * 0.06 + (self._time_counter % 4) * 0.05
        self.pressure_card.set_value(pressure_value, 1 if pressure_value > 1.2 else -1)
        self.pressure_gauge.set_value(pressure_value)
        self.pressure_chart.add_point("压力", timestamp, pressure_value)

        # 保持数据点数量不超过 60
        if len(self.pressure_chart._series[0][2]) > 60:
            self.pressure_chart._series[0][2].pop(0)

        # === 更新流量数据 ===
        # 模拟流量波动 (40.0 - 60.0)
        flow_value = 50.0 + (self._time_counter % 10) * 2.0 - 5.0
        self.flow_card.set_value(flow_value, 1 if self._time_counter % 3 == 0 else -1)

        # === 更新转速数据 ===
        # 模拟转速波动 (1450 - 1550)
        speed_value = 1500.0 + (self._time_counter % 20) * 5.0 - 50.0
        self.speed_card.set_value(speed_value, 0)

        # === 更新液位数据 ===
        # 模拟液位缓慢变化
        level_value = 80.0 + (self._time_counter % 30) * 0.5
        self.level_gauge.set_value(level_value)
        self.level_gauge.set_status("error" if level_value > 90.0 else "normal")


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle("Fusion")

    # 创建并显示窗口
    window = ComponentTestWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
