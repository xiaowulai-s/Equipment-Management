# -*- coding: utf-8 -*-
"""
RealTimeChart 组件测试

演示如何使用基于pyqtgraph的实时曲线图组件。
"""

import os
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui.widgets.realtime_chart import RealTimeChart, RealTimeChartWidget


class RealTimeChartDemo(QMainWindow):
    """RealTimeChart 演示应用"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("RealTimeChart 演示")
        self.setMinimumSize(1200, 800)

        # 定时器（每秒添加数据）
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_data)
        self._data_count = 0

        self._setup_ui()

        # 启动定时器
        self._timer.start(100)  # 每100ms更新一次

    def _setup_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # === 标题 ===
        title_label = QLabel("实时曲线图演示 (RealTimeChart)")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #24292F;")
        main_layout.addWidget(title_label)

        # === 按钮栏 ===
        button_layout = QHBoxLayout()

        self._start_btn = QPushButton("开始")
        self._start_btn.clicked.connect(self._start_demo)
        button_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("停止")
        self._stop_btn.clicked.connect(self._stop_demo)
        button_layout.addWidget(self._stop_btn)

        self._clear_btn = QPushButton("清除")
        self._clear_btn.clicked.connect(self._clear_data)
        button_layout.addWidget(self._clear_btn)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # === 说明文本 ===
        info_label = QLabel(
            "演示说明: \n"
            "- 点击'开始'启动数据更新\n"
            "- 点击'停止'暂停数据更新\n"
            "- 点击'清除'清空所有数据\n"
            "- 支持鼠标滚轮缩放和拖拽平移"
        )
        info_label.setStyleSheet("color: #57606A; padding: 8px; background-color: #F6F8FA; border-radius: 4px;")
        main_layout.addWidget(info_label)

        # === 实时曲线图（完整版）===
        self._chart_widget = RealTimeChartWidget(title="多曲线实时监测", y_label="数值")
        main_layout.addWidget(self._chart_widget, stretch=1)

        # 添加数据系列
        self._chart_widget.add_series("温度", QColor("#FF6B6B"))  # 红色
        self._chart_widget.add_series("压力", QColor("#4ECDC4"))  # 青色
        self._chart_widget.add_series("流量", QColor("#FFE66D"))  # 黄色
        self._chart_widget.add_series("转速", QColor("#1A535C"))  # 深蓝色

        self._running = False

    def _start_demo(self):
        """开始演示"""
        self._running = True
        self._timer.start(100)

    def _stop_demo(self):
        """停止演示"""
        self._running = False
        self._timer.stop()

    def _clear_data(self):
        """清除数据"""
        self._chart_widget.clear_all()

    def _update_data(self):
        """更新数据（模拟实时数据）"""
        if not self._running:
            return

        self._data_count += 1
        now = datetime.now().timestamp()

        # 模拟四个通道的数据
        import math

        # 温度: 正弦波 + 随机噪声
        temp = 50 + 30 * math.sin(self._data_count * 0.1) + (hash(str(self._data_count)) % 10 - 5)
        self._chart_widget.add_point("温度", now, temp)

        # 压力: 余弦波 + 随机噪声
        pressure = 1.5 + 0.5 * math.cos(self._data_count * 0.15) + (hash(str(self._data_count + 1)) % 5 - 2.5)
        self._chart_widget.add_point("压力", now, pressure)

        # 流量: 方波 + 随机噪声
        flow = 60 + 20 * (1 if (self._data_count % 50) < 25 else -1) + (hash(str(self._data_count + 2)) % 8 - 4)
        self._chart_widget.add_point("流量", now, flow)

        # 转速: 三角波 + 随机噪声
        rpm = 1000 + 500 * ((self._data_count % 100) / 50 - 1) + (hash(str(self._data_count + 3)) % 20 - 10)
        self._chart_widget.add_point("转速", now, rpm)


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")

    window = RealTimeChartDemo()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
