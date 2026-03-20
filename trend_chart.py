"""
自定义控件 - 实时趋势图
"""
import numpy as np
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt5.QtCore import Qt, QRectF, QPointF
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class RealTimeTrendChart(FigureCanvas):
    """实时趋势图控件"""

    def __init__(self, parent=None, title="实时趋势图", max_points=100):
        self.title = title
        self.max_points = max_points
        self.x_data = np.arange(0, max_points, 1)
        self.y_data = np.random.randn(max_points).cumsum() + 50

        # 创建Matplotlib图表
        self.fig = Figure(figsize=(8, 3), dpi=100, facecolor='#252525')
        self.ax = self.fig.add_subplot(111, facecolor='#2A2A2A')

        super().__init__(self.fig)
        self.setParent(parent)

        # 设置样式
        self.ax.set_facecolor('#2A2A2A')
        self.ax.tick_params(axis='both', colors='#888888', labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color('#444444')

        # 初始化线
        self.line, = self.ax.plot(self.x_data, self.y_data,
                                    color='#00FFAA', linewidth=1.5)
        self.ax.set_xlim(0, max_points)
        self.ax.set_ylim(0, 100)
        self.ax.set_title(title, color='#FFFFFF', fontsize=11, pad=5)
        self.ax.grid(True, color='#333333', linestyle='--', linewidth=0.5)

        self.fig.tight_layout()

    def update_data(self, new_value):
        """更新数据"""
        self.y_data = np.roll(self.y_data, -1)
        self.y_data[-1] = new_value
        self.line.set_ydata(self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()

    def clear_data(self):
        """清除数据"""
        self.y_data = np.zeros(self.max_points)
        self.line.set_ydata(self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()
