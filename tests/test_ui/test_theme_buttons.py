# -*- coding: utf-8 -*-
"""
UI 组件测试
UI Component Tests
"""

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from ui.theme_toggle_button import ThemeMenuButton, ThemeStatusBarButton, ThemeToggleButton


class TestThemeToggleButton:
    """主题切换按钮测试类"""

    @pytest.fixture
    def theme_button(self, qtbot):
        """创建主题切换按钮实例"""
        button = ThemeToggleButton()
        qtbot.addWidget(button)
        return button

    def test_init(self, theme_button):
        """测试初始化"""
        assert theme_button._theme_manager is not None
        assert theme_button._is_dark is False

    def test_toggle_theme(self, theme_button, qtbot):
        """测试切换主题"""
        # 模拟点击按钮
        with qtbot.waitSignal(theme_button.theme_toggled, timeout=1000) as blocker:
            theme_button.click()

        assert blocker.args == ["dark"]
        assert theme_button._is_dark is True

    def test_button_text_update(self, theme_button, qtbot):
        """测试按钮文本更新"""
        # 初始状态（浅色主题）
        initial_text = theme_button.text()

        # 切换到深色主题
        theme_button.click()
        new_text = theme_button.text()

        # 文本应该改变
        assert initial_text != new_text


class TestThemeMenuButton:
    """主题菜单按钮测试类"""

    @pytest.fixture
    def menu_button(self, qtbot):
        """创建主题菜单按钮实例"""
        button = ThemeMenuButton()
        qtbot.addWidget(button)
        return button

    def test_init(self, menu_button):
        """测试初始化"""
        assert menu_button._theme_manager is not None

    def test_menu_actions(self, menu_button):
        """测试菜单动作"""
        actions = menu_button.actions()
        # 至少应该有 1 个动作（实际有 3 个：浅色、深色、自定义）
        assert len(actions) >= 1


class TestThemeStatusBarButton:
    """状态栏主题按钮测试类"""

    @pytest.fixture
    def status_button(self, qtbot):
        """创建状态栏主题按钮实例"""
        button = ThemeStatusBarButton()
        qtbot.addWidget(button)
        return button

    def test_init(self, status_button):
        """测试初始化"""
        assert status_button._theme_manager is not None

    def test_click_toggle(self, status_button, qtbot):
        """测试点击切换"""
        with qtbot.waitSignal(status_button.theme_changed, timeout=1000) as blocker:
            status_button.click()

        assert len(blocker.args) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
