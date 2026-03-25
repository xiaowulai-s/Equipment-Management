# -*- coding: utf-8 -*-
"""
主题管理器
Theme Manager
"""

from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from ui.styles import AppStyles


class ThemeManager(QObject):
    """
    主题管理器 - 支持浅色/深色主题切换
    Theme Manager - Support light/dark theme switching
    """

    theme_changed = Signal(str)  # 主题变化信号

    # 深色主题样式
    DARK_THEME = """
        QMainWindow {
            background-color: #0D1117;
            color: #C9D1D9;
        }

        QWidget {
            background-color: #161B22;
            color: #C9D1D9;
        }

        QPushButton {
            background-color: #21262D;
            color: #C9D1D9;
            border: 1px solid #30363D;
            border-radius: 6px;
            padding: 8px 16px;
        }

        QPushButton:hover {
            background-color: #30363D;
            border-color: #58A6FF;
        }

        QPushButton:pressed {
            background-color: #484F58;
        }

        QPushButton:disabled {
            background-color: #21262D;
            color: #484F58;
            border-color: #30363D;
        }

        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #0D1117;
            color: #C9D1D9;
            border: 1px solid #30363D;
            border-radius: 6px;
            padding: 8px 12px;
        }

        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #58A6FF;
        }

        QLineEdit:disabled, QComboBox:disabled {
            background-color: #161B22;
            color: #484F58;
        }

        QTreeWidget, QTableWidget, QListWidget {
            background-color: #161B22;
            color: #C9D1D9;
            border: 1px solid #30363D;
            gridline-color: #30363D;
        }

        QTreeWidget::item:hover, QTableWidget::item:hover, QListWidget::item:hover {
            background-color: #21262D;
        }

        QTreeWidget::item:selected, QTableWidget::item:selected, QListWidget::item:selected {
            background-color: #1F6FEB;
            color: #FFFFFF;
        }

        QHeaderView::section {
            background-color: #21262D;
            color: #8B949E;
            border: none;
            border-bottom: 1px solid #30363D;
            border-right: 1px solid #30363D;
            padding: 8px;
            font-weight: bold;
        }

        QGroupBox {
            background-color: #161B22;
            color: #C9D1D9;
            border: 1px solid #30363D;
            border-radius: 8px;
            padding: 16px;
            margin-top: 8px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            top: -8px;
            padding: 0 8px;
            background-color: #161B22;
            color: #58A6FF;
            font-weight: 600;
        }

        QScrollBar:vertical {
            background-color: #0D1117;
            width: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background-color: #30363D;
            border-radius: 6px;
            min-height: 20px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #484F58;
        }

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        QScrollBar:horizontal {
            background-color: #0D1117;
            height: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:horizontal {
            background-color: #30363D;
            border-radius: 6px;
            min-width: 20px;
        }

        QScrollBar::handle:horizontal:hover {
            background-color: #484F58;
        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        QMenu {
            background-color: #161B22;
            color: #C9D1D9;
            border: 1px solid #30363D;
            border-radius: 8px;
            padding: 8px;
        }

        QMenu::item {
            padding: 8px 16px;
            border-radius: 4px;
        }

        QMenu::item:selected {
            background-color: #21262D;
        }

        QMenuBar {
            background-color: #161B22;
            color: #C9D1D9;
            border-bottom: 1px solid #30363D;
            padding: 4px;
        }

        QMenuBar::item:selected {
            background-color: #21262D;
            border-radius: 4px;
        }

        QToolBar {
            background-color: #161B22;
            border-bottom: 1px solid #30363D;
            spacing: 8px;
            padding: 4px;
        }

        QStatusBar {
            background-color: #161B22;
            color: #8B949E;
            border-top: 1px solid #30363D;
        }

        QSplitter::handle {
            background-color: #30363D;
        }

        QSplitter::handle:hover {
            background-color: #58A6FF;
        }

        QTabWidget::pane {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-radius: 8px;
        }

        QTabBar::tab {
            background-color: #21262D;
            color: #8B949E;
            border: 1px solid #30363D;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 16px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: #161B22;
            color: #58A6FF;
        }

        QTabBar::tab:hover:!selected {
            background-color: #30363D;
        }

        QCheckBox::indicator {
            background-color: #0D1117;
            border: 1px solid #30363D;
            border-radius: 4px;
        }

        QCheckBox::indicator:checked {
            background-color: #1F6FEB;
            border-color: #1F6FEB;
        }

        QCheckBox::indicator:hover {
            border-color: #58A6FF;
        }

        QRadioButton::indicator {
            background-color: #0D1117;
            border: 1px solid #30363D;
            border-radius: 8px;
        }

        QRadioButton::indicator:checked {
            background-color: #1F6FEB;
            border-color: #1F6FEB;
        }

        QSlider::groove:horizontal {
            background-color: #30363D;
            height: 6px;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background-color: #58A6FF;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }

        QSlider::handle:horizontal:hover {
            background-color: #1F6FEB;
        }

        QProgressBar {
            background-color: #21262D;
            border: none;
            border-radius: 6px;
            height: 8px;
            text-align: center;
            color: #C9D1D9;
        }

        QProgressBar::chunk {
            background-color: #1F6FEB;
            border-radius: 6px;
        }

        QLabel {
            color: #C9D1D9;
        }

        QToolTip {
            background-color: #21262D;
            color: #C9D1D9;
            border: 1px solid #30363D;
            border-radius: 4px;
            padding: 4px 8px;
        }
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._current_theme = "light"  # "light" or "dark"
        self._custom_themes = {}  # 自定义主题

    @property
    def current_theme(self) -> str:
        """当前主题名称"""
        return self._current_theme

    @property
    def is_dark_theme(self) -> bool:
        """是否使用深色主题"""
        return self._current_theme == "dark"

    def apply_theme(self, theme_name: str = "light") -> bool:
        """
        应用主题

        Apply theme

        Args:
            theme_name: 主题名称（"light" 或 "dark"）

        Returns:
            bool: 是否成功
        """
        app = QApplication.instance()
        if not app:
            return False

        if theme_name == "dark":
            app.setStyleSheet(self.DARK_THEME)
            self._current_theme = "dark"
        elif theme_name == "light":
            app.setStyleSheet(AppStyles.MAIN_WINDOW)
            self._current_theme = "light"
        elif theme_name in self._custom_themes:
            app.setStyleSheet(self._custom_themes[theme_name])
            self._current_theme = theme_name
        else:
            return False

        self.theme_changed.emit(self._current_theme)
        return True

    def toggle_theme(self) -> str:
        """
        切换主题（浅色 <-> 深色）

        Toggle theme (light <-> dark)

        Returns:
            str: 切换后的主题名称
        """
        new_theme = "dark" if self._current_theme == "light" else "light"
        self.apply_theme(new_theme)
        return new_theme

    def add_custom_theme(self, name: str, stylesheet: str):
        """
        添加自定义主题

        Add custom theme

        Args:
            name: 主题名称
            stylesheet: 样式表字符串
        """
        self._custom_themes[name] = stylesheet

    def get_theme_stylesheet(self, theme_name: str) -> str:
        """
        获取主题的样式表

        Get theme stylesheet

        Args:
            theme_name: 主题名称

        Returns:
            str: 样式表字符串
        """
        if theme_name == "dark":
            return self.DARK_THEME
        elif theme_name == "light":
            return AppStyles.MAIN_WINDOW
        elif theme_name in self._custom_themes:
            return self._custom_themes[theme_name]
        else:
            return ""

    @staticmethod
    def get_default_theme() -> str:
        """
        获取默认主题

        Get default theme

        Returns:
            str: 默认主题名称
        """
        return "light"


# 便捷函数
def apply_dark_theme():
    """应用深色主题"""
    manager = ThemeManager()
    manager.apply_theme("dark")


def apply_light_theme():
    """应用浅色主题"""
    manager = ThemeManager()
    manager.apply_theme("light")


def toggle_theme() -> str:
    """切换主题"""
    manager = ThemeManager()
    return manager.toggle_theme()
