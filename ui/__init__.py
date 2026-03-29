"""
UI层 - PySide6 Widgets用户界面

包含:
    - styles/: 样式系统 (主题/色彩/QSS)
    - main_window: 主窗口框架 (新架构 src/)
    - main_window_v2: 旧主窗口 (旧架构 core/)
    - dialogs/: 对话框集合
    - widgets/: 自定义可视化组件
"""


def __getattr__(name):
    """延迟导入以避免循环依赖"""
    if name == "MainWindow":
        from ui.main_window import MainWindow

        return MainWindow
    if name == "MainWindowV2":
        from ui.main_window_v2 import MainWindowV2

        return MainWindowV2
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["MainWindow", "MainWindowV2"]
