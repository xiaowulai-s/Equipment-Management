# -*- coding: utf-8 -*-
"""
主题偏好管理
Theme Preference Management
"""

import json
from pathlib import Path
from typing import Optional


class ThemePreferenceManager:
    """主题偏好管理器 - 保存和加载用户主题偏好"""

    DEFAULT_THEME = "light"
    CONFIG_DIR = Path("config")
    CONFIG_FILE = CONFIG_DIR / "theme.json"

    @classmethod
    def save_theme_preference(cls, theme: str) -> bool:
        """
        保存主题偏好到文件

        Save theme preference to file

        Args:
            theme: 主题名称（"light" 或 "dark"）

        Returns:
            bool: 保存成功返回 True
        """
        try:
            # 创建配置目录
            cls.CONFIG_DIR.mkdir(exist_ok=True)

            # 保存配置
            config = {"theme": theme}
            with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"保存主题偏好失败：{str(e)}")
            return False

    @classmethod
    def load_theme_preference(cls) -> str:
        """
        从文件加载主题偏好

        Load theme preference from file

        Returns:
            str: 主题名称，默认返回 "light"
        """
        try:
            if not cls.CONFIG_FILE.exists():
                return cls.DEFAULT_THEME

            with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("theme", cls.DEFAULT_THEME)

        except Exception as e:
            print(f"加载主题偏好失败：{str(e)}")
            return cls.DEFAULT_THEME

    @classmethod
    def delete_theme_preference(cls) -> bool:
        """
        删除主题偏好文件

        Delete theme preference file

        Returns:
            bool: 删除成功返回 True
        """
        try:
            if cls.CONFIG_FILE.exists():
                cls.CONFIG_FILE.unlink()
            return True

        except Exception as e:
            print(f"删除主题偏好失败：{str(e)}")
            return False

    @classmethod
    def is_dark_theme(cls) -> bool:
        """
        检查当前是否为深色主题

        Check if current theme is dark

        Returns:
            bool: 是否为深色主题
        """
        return cls.load_theme_preference() == "dark"

    @classmethod
    def get_available_themes(cls) -> list:
        """
        获取可用主题列表

        Get available themes list

        Returns:
            list: 主题列表
        """
        return ["light", "dark"]


# 便捷函数
def save_theme(theme: str) -> bool:
    """保存主题偏好"""
    return ThemePreferenceManager.save_theme_preference(theme)


def load_theme() -> str:
    """加载主题偏好"""
    return ThemePreferenceManager.load_theme_preference()


def is_dark() -> bool:
    """是否为深色主题"""
    return ThemePreferenceManager.is_dark_theme()
