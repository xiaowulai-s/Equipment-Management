"""
自定义控件 - 实时趋势图 v2.0
现代化工业风格设计
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

# 配置matplotlib样式
plt.rcParams['font.family'] = ['Segoe UI', 'Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


class RealTimeTrendChart(FigureCanvas):
    """实时趋势图控件 - 现代化工业风格"""

    def __init__(self, parent=None, title="", max_points=120):
        self.title = title
        self.max_points = max_points

        # 初始化数据
        self.x_data = np.arange(0, max_points, 1)
        self.y_data = np.random.randn(max_points).cumsum() + 50

        # 创建Matplotlib图表
        self.fig = Figure(figsize=(10, 3.5), dpi=100, facecolor='#161B22')
        self.ax = self.fig.add_subplot(111, facecolor='#161B22')

        super().__init__(self.fig)
        self.setParent(parent)

        # 设置图表样式
        self.setup_style()

        # 初始化线
        self.line, = self.ax.plot(
            self.x_data, self.y_data,
            color='#2196F3', linewidth=1.8, label='Temperature'
        )

        # 初始化第二条线（压力）
        self.y_data_2 = np.random.randn(max_points).cumsum() + 30
        self.line_2, = self.ax.plot(
            self.x_data, self.y_data_2,
            color='#4ECDC4', linewidth=1.2, alpha=0.7, label='Pressure'
        )

        # 初始化第三条线（气体）
        self.y_data_3 = np.random.randn(max_points).cumsum() + 60
        self.line_3, = self.ax.plot(
            self.x_data, self.y_data_3,
            color='#45B7D1', linewidth=1.2, alpha=0.5, label='Gas'
        )

        self.ax.set_xlim(0, max_points)
        self.ax.set_ylim(0, 120)

        # 图例
        self.ax.legend(
            loc='upper left',
            framealpha=0.3,
            fontsize=9,
            frameon=True,
            facecolor='#1C2128',
            edgecolor='#30363D',
            labelcolor='#8B949E'
        )

        self.fig.tight_layout(pad=1.5)

        # 减少边距
        self.fig.subplots_adjust(left=0.06, right=0.95, top=0.92, bottom=0.18)

    def setup_style(self):
        """设置图表样式"""
        # 设置轴颜色
        self.ax.tick_params(axis='both', colors='#6E7681', labelsize=9)

        # 设置轴 spines
        for spine in self.ax.spines.values():
            spine.set_color('#30363D')
            spine.set_linewidth(0.5)

        # 网格
        self.ax.grid(True, color='#21262D', linestyle='-', linewidth=0.5, alpha=0.7)
        self.ax.set_axisbelow(True)

        # Y轴标签
        self.ax.set_ylabel('Value', color='#6E7681', fontsize=9)
        self.ax.set_xlabel('Time (s)', color='#6E7681', fontsize=9)

        # 标题
        if self.title:
            self.ax.set_title(self.title, color='#E6EDF3', fontsize=11, pad=5)

    def update_data(self, new_value):
        """更新主数据"""
        self.y_data = np.roll(self.y_data, -1)
        self.y_data[-1] = new_value
        self.line.set_ydata(self.y_data)

        # 更新副数据（模拟）
        self.y_data_2 = np.roll(self.y_data_2, -1)
        self.y_data_2[-1] = new_value * 0.8 + np.random.randn() * 5

        self.y_data_3 = np.roll(self.y_data_3, -1)
        self.y_data_3[-1] = new_value * 1.2 + np.random.randn() * 8

        self.line_2.set_ydata(self.y_data_2)
        self.line_3.set_ydata(self.y_data_3)

        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()

    def clear_data(self):
        """清除数据"""
        self.y_data = np.zeros(self.max_points)
        self.y_data_2 = np.zeros(self.max_points)
        self.y_data_3 = np.zeros(self.max_points)

        self.line.set_ydata(self.y_data)
        self.line_2.set_ydata(self.y_data_2)
        self.line_3.set_ydata(self.y_data_3)

        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()

    def set_visible_lines(self, temp=True, pressure=True, gas=True):
        """设置可见的线"""
        self.line.set_visible(temp)
        self.line_2.set_visible(pressure)
        self.line_3.set_visible(gas)
        self.draw()


class MiniTrendChart(FigureCanvas):
    """迷你趋势图"""

    def __init__(self, parent=None, color='#2196F3', max_points=50):
        super().__init__(Figure(figsize=(4, 1.5), dpi=80, facecolor='transparent'))

        self.max_points = max_points
        self.color = color
        self.y_data = np.random.randn(max_points).cumsum() + 50

        self.ax = self.fig.add_subplot(111, facecolor='#1C2128')
        self.ax.set_facecolor('#1C2128')

        self.setup_style()

        self.line, = self.ax.plot(
            self.x_data, self.y_data,
            color=color, linewidth=1.2
        )

        self.ax.set_xlim(0, max_points)
        self.ax.set_ylim(0, 100)
        self.fig.tight_layout(pad=0.3)

    @property
    def x_data(self):
        return np.arange(0, self.max_points, 1)

    def setup_style(self):
        """设置样式"""
        self.ax.tick_params(axis='both', colors='#6E7681', labelsize=7)
        for spine in self.ax.spines.values():
            spine.set_color('#30363D')
            spine.set_linewidth(0.3)
        self.ax.grid(True, color='#21262D', linestyle='-', linewidth=0.3)
        self.ax.set_axisbelow(True)
        self.ax.set_xticklabels([])
        self.ax.set_yticklabels([])

    def update_data(self, new_value):
        """更新数据"""
        self.y_data = np.roll(self.y_data, -1)
        self.y_data[-1] = new_value
        self.line.set_ydata(self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()