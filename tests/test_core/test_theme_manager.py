# -*- coding: utf-8 -*-
"""
主题管理器测试
Theme Manager Tests
"""

import pytest
from PySide6.QtWidgets import QApplication

from ui.theme_manager import ThemeManager


class TestThemeManager:
    """主题管理器测试类"""

    @pytest.fixture
    def theme_manager(self):
        """创建主题管理器实例"""
        return ThemeManager()

    @pytest.fixture
    def app(self):
        """创建 QApplication 实例"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_init(self, theme_manager):
        """测试初始化"""
        assert theme_manager._current_theme == "light"
        assert theme_manager.is_dark_theme is False

    def test_apply_theme(self, theme_manager, app):
        """测试应用主题（需要 QApplication）"""
        result = theme_manager.apply_theme("dark")
        assert result is True
        assert theme_manager._current_theme == "dark"
        assert theme_manager.is_dark_theme is True

        result = theme_manager.apply_theme("light")
        assert result is True
        assert theme_manager._current_theme == "light"
        assert theme_manager.is_dark_theme is False

    def test_toggle_theme(self, theme_manager, app):
        """测试切换主题（需要 QApplication）"""
        # 从 light 切换到 dark
        new_theme = theme_manager.toggle_theme()
        assert new_theme == "dark"
        assert theme_manager._current_theme == "dark"
        assert theme_manager.is_dark_theme is True

        # 从 dark 切换到 light
        new_theme = theme_manager.toggle_theme()
        assert new_theme == "light"
        assert theme_manager._current_theme == "light"
        assert theme_manager.is_dark_theme is False

    def test_get_current_theme(self, theme_manager):
        """测试获取当前主题"""
        assert theme_manager.current_theme == "light"

        # 注意：没有 QApplication 时 apply_theme 会失败
        # 这里直接测试属性
        theme_manager._current_theme = "dark"
        assert theme_manager.current_theme == "dark"

    def test_theme_changed_signal(self, theme_manager, app, qtbot):
        """测试主题变化信号"""
        with qtbot.waitSignal(theme_manager.theme_changed, timeout=1000) as blocker:
            theme_manager.apply_theme("dark")

        assert blocker.args == ["dark"]

    def test_invalid_theme(self, theme_manager, app):
        """测试无效主题名称"""
        result = theme_manager.apply_theme("invalid")
        assert result is False
        assert theme_manager._current_theme == "light"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
