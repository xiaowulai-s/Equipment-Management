"""
工业设备管理系统 - 启动脚本
运行此脚本启动上位机界面
"""
import os
import sys

# 设置Qt插件路径（解决Windows平台插件加载问题）
plugin_path = os.path.join(os.path.dirname(__file__), 'venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor, QPalette
from main import IndustrialMonitorApp

if __name__ == "__main__":
    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置深色主题
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    app.setPalette(dark_palette)

    # 创建并显示主窗口
    window = IndustrialMonitorApp()
    window.show()

    # 运行应用
    sys.exit(app.exec_())
