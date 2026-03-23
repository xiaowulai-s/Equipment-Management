"""
工业设备管理系统 - 启动脚本
Version: 1.0
"""
import os
import sys
import multiprocessing

def fix_ssl():
    """修复SSL问题（某些Windows环境）"""
    import ssl
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context

def get_base_path():
    """获取基础路径，兼容开发模式和打包模式"""
    if getattr(sys, 'frozen', False):
        # 打包模式
        return sys._MEIPASS
    else:
        # 开发模式
        return os.path.dirname(os.path.abspath(__file__))

def setup_qt_plugin_path():
    """设置Qt插件路径"""
    if getattr(sys, 'frozen', False):
        # 打包模式下的插件路径
        plugin_path = os.path.join(get_base_path(), 'PyQt5', 'Qt5', 'plugins', 'platforms')
    else:
        # 开发模式下的插件路径
        plugin_path = os.path.join(os.path.dirname(__file__), 'venv', 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins', 'platforms')

    if os.path.exists(plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

def main():
    """主函数"""
    # 修复SSL
    fix_ssl()

    # 设置Qt插件路径
    setup_qt_plugin_path()

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QColor, QPalette
    from main import IndustrialMonitorApp

    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置应用信息
    app.setApplicationName("Equipment Management System")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Industrial Monitor")

    # 设置深色主题
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Base, QColor(40, 40, 40))
    dark_palette.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Button, QColor(50, 50, 50))
    dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.Link, QColor(0, 150, 255))
    dark_palette.setColor(QPalette.Highlight, QColor(0, 150, 255))
    dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark_palette)

    # 创建并显示主窗口
    window = IndustrialMonitorApp()
    window.show()

    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    # Windows下多进程支持
    multiprocessing.freeze_support()
    main()
