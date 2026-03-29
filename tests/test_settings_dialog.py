# -*- coding: utf-8 -*-
"""
SettingsDialog 组件测试

演示如何使用系统设置对话框。
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from ui.dialogs.settings_dialog import SettingsDialog


class SettingsDialogDemo(QMainWindow):
    """SettingsDialog 演示应用"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("系统设置对话框演示")
        self.setMinimumSize(800, 600)

        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # === 标题 ===
        from PySide6.QtGui import QFont

        title_label = QPushButton("打开系统设置")
        title_label.setMinimumHeight(50)
        title_label.clicked.connect(self._open_settings_dialog)

        layout.addWidget(title_label)

        # === 说明文本 ===
        from PySide6.QtWidgets import QLabel

        info_label = QLabel(
            "演示说明: \n\n"
            "系统设置对话框提供以下功能:\n\n"
            "1. 主题设置\n"
            "   - 深色主题\n"
            "   - 浅色主题\n"
            "   - 跟随系统\n\n"
            "2. 数据采集设置\n"
            "   - 默认轮询间隔\n"
            "   - 失败重试次数\n"
            "   - 重试间隔\n"
            "   - 最大数据点数\n\n"
            "3. 报警设置\n"
            "   - 启用弹窗/声音通知\n"
            "   - 报警冷却时间\n"
            "   - 最低通知级别\n\n"
            "4. 日志设置\n"
            "   - 日志级别\n"
            "   - 启用文件日志\n"
            "   - 日志文件路径\n\n"
            "5. 界面设置\n"
            "   - 界面语言\n"
            "   - 字体选择\n"
            "   - 字体大小\n\n"
            "点击上方按钮打开设置对话框。\n"
            "修改设置后点击'应用'按钮生效。"
        )
        info_label.setStyleSheet(
            """
            QLabel {
                color: #57606A;
                padding: 16px;
                background-color: #F6F8FA;
                border-radius: 8px;
                border: 1px solid #D0D7DE;
            }
        """
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

    def _open_settings_dialog(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            print("\n" + "=" * 60)
            print("设置已应用:")
            print("=" * 60)
            for key, value in settings.items():
                print(f"  {key}: {value}")
            print("=" * 60 + "\n")


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")

    window = SettingsDialogDemo()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
