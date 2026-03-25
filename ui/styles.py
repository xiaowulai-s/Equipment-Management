# -*- coding: utf-8 -*-
"""
样式管理模块
Style Management Module
"""

class AppStyles:
    """应用样式集合"""

    DIALOG = """
        QDialog {
            background-color: #FFFFFF;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 16px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }
    """

    TREE_WIDGET = """
        QTreeWidget {
            background-color: #F6F8FA;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 12px;
            padding: 8px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QTreeWidget::item {
            height: 56px;
            border-radius: 6px;
            padding: 0 12px;
        }

        QTreeWidget::item:hover {
            background-color: #EAEFF2;
        }

        QTreeWidget::item:selected {
            background: rgba(33, 150, 243, 0.15);
            color: #0969DA;
            border-right: 3px solid #0969DA;
        }

        QTreeWidget::header {
            background-color: #F6F8FA;
            color: #57606A;
            border-bottom: 1px solid #D0D7DE;
        }

        QTreeWidget::header::section {
            background-color: #F6F8FA;
            color: #57606A;
            padding: 12px 16px;
            border: none;
            font-weight: bold;
            font-size: 13px;
            text-transform: none;
            letter-spacing: 0;
        }

        QHeaderView::section {
            text-align: center;
            font-weight: bold;
        }
    """

    DEVICE_TREE = """
        QTreeWidget {
            background-color: #FFFFFF;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 12px;
            padding: 8px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QTreeWidget::item {
            height: 56px;
            border-radius: 6px;
            padding: 0 12px;
        }

        QTreeWidget::item:hover {
            background-color: #EAEFF2;
        }

        QTreeWidget::item:selected {
            background: rgba(9, 105, 218, 0.15);
            color: #0969DA;
            border-right: 3px solid #0969DA;
        }

        QTreeWidget::header {
            background-color: #F6F8FA;
            color: #57606A;
            border-bottom: 1px solid #D0D7DE;
        }

        QTreeWidget::header::section {
            background-color: #F6F8FA;
            color: #57606A;
            padding: 12px 16px;
            border: none;
            font-weight: bold;
            font-size: 13px;
            text-transform: none;
            letter-spacing: 0;
        }

        QHeaderView::section {
            text-align: center;
            font-weight: bold;
        }
    """

    BUTTON_PRIMARY = """
        QPushButton {
            background: qlineargradient(135deg, #0969DA, #0550AE);
            color: white;
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QPushButton:hover {
            background: qlineargradient(135deg, #0550AE, #043E8C);
        }

        QPushButton:pressed {
            background: qlineargradient(135deg, #043E8C, #0550AE);
        }
    """

    BUTTON_SECONDARY = """
        QPushButton {
            background: #FFFFFF;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QPushButton:hover {
            background: #F6F8FA;
            border-color: #0969DA;
        }

        QPushButton:pressed {
            background: #EAEFF2;
        }
    """

    BUTTON_DANGER = """
        QPushButton {
            background: qlineargradient(135deg, #CF222E, #A40E26);
            color: white;
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QPushButton:hover {
            background: qlineargradient(135deg, #A40E26, #82071E);
        }

        QPushButton:pressed {
            background: qlineargradient(135deg, #82071E, #A40E26);
        }
    """

    LINE_EDIT = """
        QLineEdit {
            background-color: #FFFFFF;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QLineEdit:hover:not(:disabled) {
            border-color: #0969DA;
        }

        QLineEdit:focus {
            border-color: #0969DA;
            outline: none;
        }

        QLineEdit::placeholder {
            color: #8B949E;
        }
    """

    COMBO_BOX = """
        QComboBox {
            background-color: #FFFFFF;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
            padding-right: 30px;
        }

        QComboBox:hover:not(:disabled) {
            border-color: #0969DA;
        }

        QComboBox:focus {
            border-color: #0969DA;
            outline: none;
        }
    """

    CHECK_BOX = """
        QCheckBox {
            color: #24292F;
            font-weight: 500;
            font-size: 12px;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            background-color: #FFFFFF;
            border: 1px solid #D0D7DE;
            border-radius: 4px;
        }

        QCheckBox::indicator:hover {
            border-color: #0969DA;
        }

        QCheckBox::indicator:checked {
            background-color: #0969DA;
            border-color: #0969DA;
        }
    """

    GROUP_BOX = """
        QGroupBox {
            background-color: #FFFFFF;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 8px;
            padding: 16px;
            margin-top: 8px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            top: -8px;
            padding: 0 8px;
            background-color: #FFFFFF;
            font-weight: 600;
            font-size: 13px;
        }
    """

    DATA_CARD = """
        QGroupBox#DataCard {
            background: qlineargradient(135deg, #FFFFFF, #F6F8FA);
            border: 1px solid #D0D7DE;
            border-radius: 16px;
            position: relative;
            overflow: hidden;
        }

        QGroupBox#DataCard:hover {
            border-color: #0969DA;
        }

        QGroupBox#DataCard::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: qlineargradient(90deg, #0969DA, #54AEFF);
        }
    """

    MAIN_WINDOW = """
        QMainWindow {
            background-color: #F6F8FA;
            color: #24292F;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QWidget {
            background-color: #F6F8FA;
            color: #24292F;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QPushButton {
            background-color: #FFFFFF;
            color: #24292F;
            border: 1px solid #D0D7DE;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }

        QPushButton:hover {
            background-color: #F6F8FA;
            border-color: #0969DA;
        }
    """

    STACKED_WIDGET = """
        QStackedWidget {
            background-color: #F6F8FA;
            color: #24292F;
        }
    """

    SPLITTER = """
        QSplitter {
            background-color: #F6F8FA;
        }

        QSplitter::handle {
            background-color: #D0D7DE;
            width: 4px;
        }

        QSplitter::handle:hover {
            background-color: #0969DA;
        }
    """

    STATUSBAR = """
        QStatusBar {
            background-color: #F6F8FA;
            color: #57606A;
            border-top: 1px solid #D0D7DE;
            font-size: 11px;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }
    """

    TOOLBAR = """
        QToolBar {
            background-color: #FFFFFF;
            border-bottom: 1px solid #D0D7DE;
            spacing: 8px;
            padding: 4px;
        }
    """

    @staticmethod
    def get_button_primary_with_padding(padding_x: int = 24) -> str:
        """获取带自定义内边距的主按钮样式"""
        return AppStyles.BUTTON_PRIMARY.replace("padding: 8px 16px;", f"padding: 8px {padding_x}px;")

    @staticmethod
    def get_button_secondary_with_padding(padding_x: int = 24) -> str:
        """获取带自定义内边距的次要按钮样式"""
        return AppStyles.BUTTON_SECONDARY.replace("padding: 8px 16px;", f"padding: 8px {padding_x}px;")
