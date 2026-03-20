"""测试脚本"""
import sys
sys.path.insert(0, 'e:/下载/app/equipment management')

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor

app = QApplication([])
app.setPalette(QColor(30, 30, 30))

from main import IndustrialMonitorApp
window = IndustrialMonitorApp()

print('UI initialized successfully')
print('Window title:', window.windowTitle())
print('Window size:', window.geometry().width(), 'x', window.geometry().height())
