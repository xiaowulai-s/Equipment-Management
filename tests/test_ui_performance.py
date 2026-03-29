"""
UI组件性能测试
测试DataCard、Gauge、TrendChart、RealTimeChart等组件的性能
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from performance_tester import PerformanceTester
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from ui.widgets.data_card import DataCard
from ui.widgets.gauge import Gauge
from ui.widgets.realtime_chart import RealTimeChart
from ui.widgets.trend_chart import TrendChart


class PerformanceTestWindow(QMainWindow):
    """性能测试窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("UI组件性能测试")
        self.setGeometry(100, 100, 1200, 800)

        self.tester = PerformanceTester()
        self.test_results = {}

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 测试按钮（在实际测试中会自动触发）
        # 这里仅作为占位符

    def run_all_tests(self):
        """运行所有性能测试"""
        print("\n" + "=" * 80)
        print("开始UI组件性能测试")
        print("=" * 80)

        # 测试1: DataCard性能
        self.test_data_card()

        # 测试2: Gauge性能
        self.test_gauge()

        # 测试3: TrendChart性能
        self.test_trend_chart()

        # 测试4: RealTimeChart性能
        self.test_realtime_chart()

        # 测试5: 综合场景测试
        self.test_combined_scenario()

        print("\n" + "=" * 80)
        print("所有性能测试完成")
        print("=" * 80)

        return self.test_results

    def test_data_card(self):
        """测试DataCard组件性能"""
        print("\n" + "-" * 80)
        print("测试1: DataCard组件性能")
        print("-" * 80)

        self.tester.reset()

        # 创建测试函数
        def create_data_card():
            card = DataCard("Temperature", 25.5, "°C", "Normal")
            return card

        # 基准测试：创建性能
        stats = self.tester.benchmark(create_data_card, 100, "data_card_creation")

        # 测试更新性能
        def update_data_card(card):
            for i in range(100):
                card.update_value(20 + np.random.random() * 10)

        card = DataCard("Test", 0, "unit", "Normal")
        stats = self.tester.benchmark(update_data_card, 10, "data_card_update", card)

        self.test_results["data_card"] = stats

    def test_gauge(self):
        """测试Gauge组件性能"""
        print("\n" + "-" * 80)
        print("测试2: Gauge组件性能")
        print("-" * 80)

        self.tester.reset()

        # 创建测试函数
        def create_gauge():
            gauge = Gauge("Pressure", 0, 100, 50, "bar")
            return gauge

        # 基准测试：创建性能
        stats = self.tester.benchmark(create_gauge, 50, "gauge_creation")

        # 测试更新性能
        def update_gauge(gauge):
            for i in range(100):
                gauge.set_value(50 + np.random.random() * 40 - 20)

        gauge = Gauge("Test", 0, 100, 50, "bar")
        stats = self.tester.benchmark(update_gauge, 10, "gauge_update", gauge)

        self.test_results["gauge"] = stats

    def test_trend_chart(self):
        """测试TrendChart组件性能"""
        print("\n" + "-" * 80)
        print("测试3: TrendChart组件性能")
        print("-" * 80)

        self.tester.reset()

        # 创建测试函数
        def create_trend_chart():
            chart = TrendChart("Temperature Trend", "Time", "Value")
            return chart

        # 基准测试：创建性能
        stats = self.tester.benchmark(create_trend_chart, 50, "trend_chart_creation")

        # 测试数据更新性能
        def update_trend_chart(chart):
            times = np.arange(60)
            values = 20 + np.random.random(60) * 10
            chart.update_data(times.tolist(), values.tolist())

        chart = TrendChart("Test", "Time", "Value")
        stats = self.tester.benchmark(update_trend_chart, 10, "trend_chart_update", chart)

        self.test_results["trend_chart"] = stats

    def test_realtime_chart(self):
        """测试RealTimeChart组件性能"""
        print("\n" + "-" * 80)
        print("测试4: RealTimeChart组件性能")
        print("-" * 80)

        self.tester.reset()

        # 创建测试函数
        def create_realtime_chart():
            chart = RealTimeChart()
            chart.add_series("Temperature", "#2196F3")
            chart.add_series("Pressure", "#FF5722")
            return chart

        # 基准测试：创建性能
        stats = self.tester.benchmark(create_realtime_chart, 50, "realtime_chart_creation")

        # 测试实时更新性能
        def update_realtime_chart(chart):
            import time

            base_time = time.time()
            for i in range(100):
                timestamp = base_time + i * 0.01
                chart.add_point("Temperature", timestamp, 20 + np.random.random() * 10)
                chart.add_point("Pressure", timestamp, 5 + np.random.random() * 2)

        chart = RealTimeChart()
        chart.add_series("Temperature", "#2196F3")
        chart.add_series("Pressure", "#FF5722")
        stats = self.tester.benchmark(update_realtime_chart, 10, "realtime_chart_update", chart)

        # 内存泄漏测试
        self.tester.reset()
        result = self.tester.memory_leak_test(create_realtime_chart, 100, "realtime_chart_memory_leak")

        self.test_results["realtime_chart"] = stats
        self.test_results["realtime_chart_memory"] = result

    def test_combined_scenario(self):
        """测试综合场景性能"""
        print("\n" + "-" * 80)
        print("测试5: 综合场景性能")
        print("-" * 80)

        self.tester.reset()

        def create_combined_widgets():
            """创建多个组件的综合场景"""
            cards = [DataCard(f"Sensor_{i}", 0, "unit", "Normal") for i in range(10)]
            gauges = [Gauge(f"Gauge_{i}", 0, 100, 50, "bar") for i in range(5)]
            charts = [RealTimeChart() for _ in range(3)]

            # 为图表添加数据系列
            for chart in charts:
                chart.add_series("Series1", "#2196F3")

            return {"cards": cards, "gauges": gauges, "charts": charts}

        # 基准测试
        stats = self.tester.benchmark(create_combined_widgets, 20, "combined_creation")

        # 压力测试：持续更新
        def update_combined_widgets(widgets):
            import time

            base_time = time.time()

            # 更新卡片
            for card in widgets["cards"]:
                card.update_value(np.random.random() * 100)

            # 更新仪表盘
            for gauge in widgets["gauges"]:
                gauge.set_value(np.random.random() * 100)

            # 更新图表
            for chart in widgets["charts"]:
                chart.add_point("Series1", base_time, np.random.random() * 100)

        widgets = create_combined_widgets()
        stats = self.tester.stress_test(update_combined_widgets, 10, "combined_stress", widgets)  # 10秒压力测试

        # 内存泄漏测试
        self.tester.reset()
        result = self.tester.memory_leak_test(create_combined_widgets, 50, "combined_memory_leak")

        self.test_results["combined"] = stats
        self.test_results["combined_memory"] = result


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 创建测试窗口
    test_window = PerformanceTestWindow()
    test_window.show()

    # 运行所有测试
    QTimer.singleShot(1000, test_window.run_all_tests)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
