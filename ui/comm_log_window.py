# -*- coding: utf-8 -*-
"""
通信日志窗口

独立窗口显示通信日志，支持：
- 实时显示日志
- 清空日志
- 保存日志到文件
- 自动滚动
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import PrimaryButton, SecondaryButton


class CommLogWindow(QMainWindow):
    """
    通信日志窗口

    独立窗口显示设备通信日志，支持实时更新。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("通信日志")
        self.setMinimumSize(800, 400)
        self.resize(900, 500)

        self._init_ui()
        self._init_toolbar()

    def _init_ui(self) -> None:
        """初始化UI"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 日志文本框
        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._log_text.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 12px;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px;
            }
        """
        )

        # 设置字体
        font = QFont("JetBrains Mono", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._log_text.setFont(font)

        layout.addWidget(self._log_text)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._clear_btn = SecondaryButton("清空")
        self._clear_btn.setToolTip("清空日志 (Ctrl+L)")
        self._clear_btn.clicked.connect(self.clear_log)
        self._clear_btn.setShortcut("Ctrl+L")

        self._save_btn = SecondaryButton("保存")
        self._save_btn.setToolTip("保存日志到文件 (Ctrl+S)")
        self._save_btn.clicked.connect(self.save_log)
        self._save_btn.setShortcut("Ctrl+S")

        self._close_btn = PrimaryButton("关闭")
        self._close_btn.setToolTip("关闭窗口 (Esc)")
        self._close_btn.clicked.connect(self.hide)

        btn_layout.addWidget(self._clear_btn)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addWidget(self._close_btn)

        layout.addLayout(btn_layout)

    def _init_toolbar(self) -> None:
        """初始化工具栏"""
        toolbar = QToolBar("工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 自动滚动
        self._auto_scroll_action = QAction("自动滚动", self)
        self._auto_scroll_action.setCheckable(True)
        self._auto_scroll_action.setChecked(True)
        toolbar.addAction(self._auto_scroll_action)

        toolbar.addSeparator()

        # 复制
        copy_action = QAction("复制", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self._copy_selected)
        toolbar.addAction(copy_action)

        # 全选
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self._log_text.selectAll)
        toolbar.addAction(select_all_action)

    def append_log(self, message: str, level: str = "INFO") -> None:
        """添加日志消息

        Args:
            message: 日志消息
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # 根据级别设置颜色
        color_map = {
            "INFO": "#D4D4D4",  # 白色
            "WARNING": "#FF9800",  # 橙色
            "ERROR": "#F44336",  # 红色
            "DEBUG": "#9E9E9E",  # 灰色
            "SUCCESS": "#4CAF50",  # 绿色
        }
        color = color_map.get(level, "#D4D4D4")

        # 构造HTML格式日志
        html_message = (
            f'<span style="color: #6B7280;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
        )

        # 使用HTML追加（保留颜色）
        self._log_text.appendHtml(html_message)

        # 自动滚动
        if self._auto_scroll_action.isChecked():
            scrollbar = self._log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def clear_log(self) -> None:
        """清空日志"""
        self._log_text.clear()

    def save_log(self) -> None:
        """保存日志到文件"""
        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存日志",
            f"comm_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*.*)",
        )

        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self._log_text.toPlainText())
                QMessageBox.information(self, "保存成功", f"日志已保存到:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存日志失败:\n{str(e)}")

    def _copy_selected(self) -> None:
        """复制选中的文本"""
        cursor = self._log_text.textCursor()
        if cursor.hasSelection():
            QApplication.clipboard().setText(cursor.selectedText())

    def closeEvent(self, event) -> None:
        """关闭事件 - 隐藏而不是真正关闭"""
        self.hide()
        event.ignore()

    def show_window(self) -> None:
        """显示窗口"""
        self.show()
        self.raise_()
        self.activateWindow()
