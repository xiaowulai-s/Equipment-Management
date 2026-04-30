# -*- coding: utf-8 -*-
"""
登录对话框 - Login Dialog
============================

提供用户认证界面，支持用户名/密码输入和角色显示。

功能特性:
✅ 用户名/密码输入框
✅ 密码掩码显示（•••）
✅ 记住我选项
✅ 自动聚焦到用户名输入框
✅ 回车键快捷提交
✅ 错误提示信息显示

使用示例:
    >>> dialog = LoginDialog(permission_manager, parent=self)
    >>> if dialog.exec() == QDialog.DialogCode.Accepted:
    ...     print(f"登录成功: {dialog.username}")
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.utils.permission_manager import PermissionManager


class LoginDialog(QDialog):
    """
    登录对话框

    提供标准的用户名/密码登录界面，
    与 PermissionManager 集成进行身份验证。
    """

    def __init__(
        self, permission_manager: PermissionManager, parent: Optional[QWidget] = None, title: str = "用户登录"
    ) -> None:
        """
        初始化登录对话框

        Args:
            permission_manager: 权限管理器实例
            parent: 父窗口
            title: 对话框标题
        """
        super().__init__(parent)
        self._pm = permission_manager
        self._username: Optional[str] = None

        self.setWindowTitle(title)
        self.setFixedSize(380, 280)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 20)
        layout.setSpacing(15)

        # 标题标签
        title_label = QLabel("工业设备管理系统")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1F2937; background: transparent; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # 副标题
        subtitle_label = QLabel("请输入您的账户信息以继续")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setFont(QFont("Microsoft YaHei", 10))
        subtitle_label.setStyleSheet("color: #6B7280; background: transparent;")
        layout.addWidget(subtitle_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layoutsetLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 用户名输入框
        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("请输入用户名")
        self._username_edit.setMinimumHeight(36)
        self._username_edit.setText("admin")  # 默认填充方便测试
        form_layout.addRow("用户名:", self._username_edit)

        # 密码输入框
        self._password_edit = QLineEdit()
        self._password_edit.setPlaceholderText("请输入密码")
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setMinimumHeight(36)
        self._password_edit.setText("admin123")  # 默认填充方便测试
        form_layout.addRow("密码:", self._password_edit)

        layout.addLayout(form_layout)

        # 记住我复选框
        self._remember_check = QCheckBox("记住我（本次会话有效）")
        self._remember_check.setChecked(True)
        self._remember_check.setStyleSheet("color: #6B7280; background: transparent;")
        layout.addWidget(self._remember_check)

        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._on_login)
        button_box.rejected.connect(self.reject)

        login_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if login_btn:
            login_btn.setText("登 录")
            login_btn.setMinimumHeight(36)
            login_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 8px 24px;
                }
                QPushButton:hover {
                    background-color: #2563EB;
                }
                QPushButton:pressed {
                    background-color: #1D4ED8;
                }
            """
            )

        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setText("取 消")
            cancel_btn.setMinimumHeight(36)

        layout.addWidget(button_box)

        # 帮助信息
        help_label = QLabel("默认账户: admin/admin123  operator/operator123  viewer/viewer123")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setFont(QFont("Microsoft YaHei", 8))
        help_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(help_label)

        # 自动聚焦到密码输入框（因为用户名已默认填充）
        self._password_edit.setFocus()

    def _on_login(self) -> None:
        """
        处理登录按钮点击事件

        获取输入的用户名和密码，调用 PermissionManager 进行认证。
        成功后关闭对话框，失败则显示错误提示。
        """
        username = self._username_edit.text().strip()
        password = self._password_edit.text()

        # 输入验证
        if not username:
            QMessageBox.warning(self, "输入错误", "请输入用户名")
            self._username_edit.setFocus()
            return

        if not password:
            QMessageBox.warning(self, "输入错误", "请输入密码")
            self._password_edit.setFocus()
            return

        # 执行登录
        try:
            success = self._pm.login(username, password)

            if success:
                self._username = username
                self.accept()
            else:
                QMessageBox.warning(self, "登录失败", "用户名或密码错误，请重试。\n\n" "提示：检查大小写和空格。")
                # 清空密码框并重新聚焦
                self._password_edit.clear()
                self._password_edit.setFocus()

        except Exception as e:
            QMessageBox.critical(self, "系统异常", f"登录过程中发生错误:\n{str(e)}")
            logger.exception("登录异常")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        重写键盘事件，支持回车键提交

        Args:
            event: 键盘事件
        """
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._on_login()
        else:
            super().keyPressEvent(event)

    @property
    def username(self) -> Optional[str]:
        """获取登录成功后的用户名"""
        return self._username
