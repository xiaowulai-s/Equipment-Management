# -*- coding: utf-8 -*-
"""
应用样式常量 - AppStyles

集中管理所有内联 QSS 样式常量，供各 UI 组件引用。
主题相关的样式已迁移到 ui/styles/qss/ 目录，
此处仅保留不依赖主题的通用布局样式。
"""


class AppStyles:
    """应用内联样式常量"""

    TOOLBAR = """
        QToolBar {
            background: transparent;
            border: none;
            spacing: 8px;
            padding: 4px 8px;
        }
        QToolBar QToolButton {
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 13px;
        }
    """

    STATUSBAR = """
        QStatusBar {
            background: transparent;
            border-top: 1px solid #E5E7EB;
            font-size: 12px;
            padding: 2px 8px;
        }
    """

    SPLITTER = """
        QSplitter::handle {
            background: #E5E7EB;
            width: 1px;
        }
        QSplitter::handle:hover {
            background: #D1D5DB;
        }
    """

    STACKED_WIDGET = """
        QStackedWidget {
            background: #FFFFFF;
            border: none;
        }
    """

    TAB_WIDGET = """
        QTabWidget::pane {
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            background: #FFFFFF;
            top: -1px;
        }
        QTabBar::tab {
            background: transparent;
            border: 1px solid transparent;
            border-bottom: none;
            padding: 8px 20px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-size: 13px;
            color: #6B7280;
        }
        QTabBar::tab:selected {
            background: #FFFFFF;
            border-color: #E5E7EB;
            color: #2196F3;
            font-weight: 600;
        }
        QTabBar::tab:hover:!selected {
            background: #F3F4F6;
        }
    """

    DEVICE_TREE = """
        QTreeWidget {
            background-color: #FFFFFF;
            alternate-background-color: #F6F8FA;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 4px;
            font-size: 13px;
            outline: none;
        }
        QTreeWidget::item {
            padding: 8px 4px;
            border-bottom: 1px solid #F0F2F5;
        }
        QTreeWidget::item:hover {
            background-color: #F0F2F5;
        }
        QTreeWidget::item:selected {
            background-color: #E3F2FD;
            color: #1565C0;
        }
        QTreeWidget::item:selected:hover {
            background-color: #BBDEFB;
        }
        QHeaderView::section {
            background-color: #F6F8FA;
            color: #57606A;
            border: none;
            border-bottom: 1px solid #E5E7EB;
            padding: 8px 6px;
            font-size: 12px;
            font-weight: 600;
        }
    """
