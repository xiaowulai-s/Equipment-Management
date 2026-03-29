# -*- coding: utf-8 -*-
"""
主题管理器 - 统一主题系统

职责:
    - 从 QSS 文件加载浅色主题
    - 提供当前主题颜色查询 API (供组件动态着色)

主题文件:
    ui/styles/qss/base.qss        - 全局基础样式 (字体等)
    ui/styles/qss/base_light.qss  - 浅色基础样式 (菜单/工具栏/滚动条等)
    ui/styles/qss/light.qss       - 浅色控件样式
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# QSS 目录
_QSS_DIR = Path(__file__).resolve().parent / "styles" / "qss"


# ═══════════════════════════════════════════════════════════
# 主题颜色定义
# ═══════════════════════════════════════════════════════════


class ThemeColors:
    """浅色主题颜色查询接口."""

    _COLORS: Dict[str, str] = {
        # 基础
        "bg_base": "#FFFFFF",
        "bg_raised": "#F6F8FA",
        "bg_overlay": "#F3F4F6",
        "bg_hover": "#F0F2F5",
        # 文本
        "text_primary": "#1F2937",
        "text_secondary": "#6B7280",
        "text_tertiary": "#9CA3AF",
        # 边框
        "border_default": "#D1D5DB",
        "border_muted": "#E5E7EB",
        "border_accent": "#2563EB",
        # 功能色
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "info": "#06B6D4",
        "primary": "#2196F6",
        # 图表
        "chart_bg": "#FFFFFF",
        "chart_axis": "#6B7280",
        "chart_grid": "#E5E7EB",
    }

    def __getattr__(self, name: str) -> str:
        if name in self._COLORS:
            return self._COLORS[name]
        raise AttributeError(
            f"'{type(self).__name__}' has no color '{name}'. " f"Available: {list(self._COLORS.keys())}"
        )


# ═══════════════════════════════════════════════════════════
# ThemeManager
# ═══════════════════════════════════════════════════════════


class ThemeManager(QObject):
    """主题管理器 (仅浅色主题).

    功能:
        - 从 QSS 文件加载浅色主题
        - 提供 ThemeColors 查询接口

    用法:
        tm = ThemeManager()
        tm.apply_theme()              # 应用浅色主题
        tm.colors.bg_base             # 获取背景色
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.colors = ThemeColors()

    def _load_qss(self, filename: str) -> str:
        """从 QSS 文件加载内容, 失败返回空字符串."""
        path = _QSS_DIR / filename
        if not path.exists():
            logger.warning("QSS 文件不存在: %s", path)
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("读取 QSS 失败: %s - %s", path, e)
            return ""

    def _build_stylesheet(self) -> str:
        """组合生成浅色样式表: base.qss + base_light.qss + light.qss."""
        parts: list[str] = []

        base = self._load_qss("base.qss")
        if base:
            parts.append(base)

        base_light = self._load_qss("base_light.qss")
        if base_light:
            parts.append(base_light)

        light = self._load_qss("light.qss")
        if light:
            parts.append(light)

        return "\n".join(parts)

    def apply_theme(self) -> bool:
        """应用浅色主题到 QApplication."""
        app = QApplication.instance()
        if app is None:
            logger.warning("QApplication 未初始化, 无法应用主题")
            return False

        stylesheet = self._build_stylesheet()
        app.setStyleSheet(stylesheet)

        logger.info("浅色主题已应用")
        return True
