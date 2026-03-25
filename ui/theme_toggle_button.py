# -*- coding: utf-8 -*-
"""
主题切换按钮组件
Theme Toggle Button Component
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QPushButton

from ui.theme_manager import ThemeManager


class ThemeToggleButton(QPushButton):
    """
    主题切换按钮 - 支持浅色/深色主题切换
    Theme Toggle Button - Support light/dark theme switching
    """

    theme_toggled = Signal(str)  # 主题切换信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_manager = ThemeManager()
        self._is_dark = self._theme_manager.is_dark_theme
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化 UI"""
        self._update_button_text()
        self.setFixedSize(40, 40)
        self.setToolTip("切换主题（浅色/深色）")

    def _connect_signals(self):
        """连接信号"""
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        """处理点击事件"""
        new_theme = self._theme_manager.toggle_theme()
        self._is_dark = self._theme_manager.is_dark_theme
        self._update_button_text()
        self.theme_toggled.emit(new_theme)

    def _update_button_text(self):
        """更新按钮文本"""
        if self._is_dark:
            self.setText("☀️")
            self.setToolTip("切换到浅色主题")
        else:
            self.setText("🌙")
            self.setToolTip("切换到深色主题")

    def set_theme(self, theme: str):
        """
        设置主题

        Set theme

        Args:
            theme: 主题名称（"light" 或 "dark"）
        """
        if theme == "dark" and not self._is_dark:
            self._on_clicked()
        elif theme == "light" and self._is_dark:
            self._on_clicked()


class ThemeMenuButton(QPushButton):
    """
    主题菜单按钮 - 支持多主题选择
    Theme Menu Button - Support multiple theme selection
    """

    theme_selected = Signal(str)  # 主题选择信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_manager = ThemeManager()
        self._menu = QMenu(self)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化 UI"""
        self.setText("🎨 主题")
        self.setFixedHeight(32)

        # 添加主题菜单项
        light_action = QAction("☀️ 浅色主题", self)
        light_action.triggered.connect(lambda: self._select_theme("light"))
        self._menu.addAction(light_action)

        dark_action = QAction("🌙 深色主题", self)
        dark_action.triggered.connect(lambda: self._select_theme("dark"))
        self._menu.addAction(dark_action)

        self._menu.addSeparator()

        # 添加自定义主题（示例）
        custom_action = QAction("🎨 自定义主题", self)
        custom_action.triggered.connect(lambda: self._select_theme("custom"))
        self._menu.addAction(custom_action)

        self.setMenu(self._menu)
        self._update_button_text()

    def _connect_signals(self):
        """连接信号"""
        pass

    def _select_theme(self, theme: str):
        """选择主题"""
        if theme == "custom":
            # 这里可以打开主题配置对话框
            pass
        else:
            success = self._theme_manager.apply_theme(theme)
            if success:
                self._update_button_text()
                self.theme_selected.emit(theme)

    def _update_button_text(self):
        """更新按钮文本"""
        current = self._theme_manager.current_theme
        if current == "dark":
            self.setText("🌙 深色")
        elif current == "light":
            self.setText("☀️ 浅色")
        else:
            self.setText(f"🎨 {current}")


class ThemeStatusBarButton(QPushButton):
    """
    状态栏主题按钮 - 紧凑型
    Status Bar Theme Button - Compact version
    """

    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_manager = ThemeManager()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化 UI"""
        self.setFixedSize(28, 28)
        self._update_button_text()
        self.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 14px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """
        )

    def _connect_signals(self):
        """连接信号"""
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        """处理点击事件"""
        new_theme = self._theme_manager.toggle_theme()
        self._update_button_text()
        self.theme_changed.emit(new_theme)

    def _update_button_text(self):
        """更新按钮文本"""
        if self._theme_manager.is_dark_theme:
            self.setText("☀️")
        else:
            self.setText("🌙")
