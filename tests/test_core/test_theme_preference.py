# -*- coding: utf-8 -*-
"""
主题偏好管理器测试
Theme Preference Manager Tests
"""

import json
from pathlib import Path

import pytest

from ui.theme_preference import ThemePreferenceManager


class TestThemePreferenceManager:
    """主题偏好管理器测试类"""

    @pytest.fixture
    def clean_config(self):
        """清理配置文件"""
        config_file = ThemePreferenceManager.CONFIG_FILE
        if config_file.exists():
            config_file.unlink()
        yield
        if config_file.exists():
            config_file.unlink()

    def test_save_preference(self, clean_config):
        """测试保存主题偏好"""
        result = ThemePreferenceManager.save_theme_preference("dark")
        assert result is True
        assert ThemePreferenceManager.CONFIG_FILE.exists()

        with open(ThemePreferenceManager.CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            assert config["theme"] == "dark"

    def test_load_preference_default(self, clean_config):
        """测试加载默认主题偏好"""
        theme = ThemePreferenceManager.load_theme_preference()
        assert theme == ThemePreferenceManager.DEFAULT_THEME

    def test_load_preference_saved(self, clean_config):
        """测试加载已保存的主题偏好"""
        ThemePreferenceManager.save_theme_preference("dark")
        theme = ThemePreferenceManager.load_theme_preference()
        assert theme == "dark"

    def test_save_invalid_theme(self, clean_config):
        """测试保存无效主题"""
        result = ThemePreferenceManager.save_theme_preference("invalid")
        assert result is True

        theme = ThemePreferenceManager.load_theme_preference()
        assert theme == "invalid"

    def test_config_directory_creation(self, clean_config):
        """测试配置目录自动创建"""
        ThemePreferenceManager.save_theme_preference("dark")
        assert ThemePreferenceManager.CONFIG_DIR.exists()
        assert ThemePreferenceManager.CONFIG_FILE.exists()

    def test_load_nonexistent_file(self, clean_config):
        """测试加载不存在的配置文件"""
        assert not ThemePreferenceManager.CONFIG_FILE.exists()
        theme = ThemePreferenceManager.load_theme_preference()
        assert theme == ThemePreferenceManager.DEFAULT_THEME


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
