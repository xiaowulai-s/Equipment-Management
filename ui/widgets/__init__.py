# -*- coding: utf-8 -*-
"""
UI 组件库 - 自定义 Widget 组件集合

提供统一的 Fluent Design 风格组件，替代原生 Qt 控件。
所有组件支持主题色适配。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

# ═══════════════════════════════════════════════════════════
# 颜色常量
# ═══════════════════════════════════════════════════════════


class Colors:
    """通用颜色常量"""

    PRIMARY = "#2196F3"
    PRIMARY_HOVER = "#1976D2"
    PRIMARY_ACTIVE = "#1565C0"
    SUCCESS = "#4CAF50"
    SUCCESS_HOVER = "#43A047"
    DANGER = "#F44336"
    DANGER_HOVER = "#E53935"
    WARNING = "#FFC107"
    TEXT_PRIMARY = "#1F2937"
    TEXT_SECONDARY = "#6B7280"
    TEXT_TERTIARY = "#9CA3AF"
    BG_BASE = "#FFFFFF"
    BG_HOVER = "#F3F4F6"
    BG_ACTIVE = "#E5E7EB"
    BORDER = "#D1D5DB"
    BORDER_FOCUS = "#2196F3"
    RADIUS = "6px"
    RADIUS_LG = "8px"


# ═══════════════════════════════════════════════════════════
# 基础按钮样式生成器
# ═══════════════════════════════════════════════════════════


def _button_base_style(
    bg: str = "",
    bg_hover: str = "",
    text_color: str = Colors.TEXT_PRIMARY,
    border: str = f"1px solid {Colors.BORDER}",
    radius: str = Colors.RADIUS,
) -> str:
    """生成按钮基础 QSS"""
    lines = [
        f"QPushButton {{ background: {bg or 'transparent'}; color: {text_color}; "
        f"border: {border}; border-radius: {radius}; padding: 6px 16px; "
        f"font-size: 13px; font-weight: 500; }}",
    ]
    if bg_hover:
        lines.append(f"QPushButton:hover {{ background: {bg_hover}; }}")
    if bg:
        lines.append(f"QPushButton:pressed {{ background: {bg}; opacity: 0.8; }}")
    lines.append("QPushButton:disabled { color: #9CA3AF; background: #F3F4F6; }")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 按钮组件
# ═══════════════════════════════════════════════════════════


class PrimaryButton(QPushButton):
    """主要操作按钮 - 蓝色填充"""

    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        self.setStyleSheet(
            _button_base_style(
                bg=Colors.PRIMARY,
                bg_hover=Colors.PRIMARY_HOVER,
                text_color="#FFFFFF",
                border="none",
            )
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)


class SecondaryButton(QPushButton):
    """次要操作按钮 - 白色背景 + 边框"""

    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        self.setStyleSheet(
            _button_base_style(
                bg="",
                bg_hover=Colors.BG_HOVER,
                text_color=Colors.TEXT_PRIMARY,
            )
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)


class SuccessButton(QPushButton):
    """成功操作按钮 - 绿色填充"""

    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        self.setStyleSheet(
            _button_base_style(
                bg=Colors.SUCCESS,
                bg_hover=Colors.SUCCESS_HOVER,
                text_color="#FFFFFF",
                border="none",
            )
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)


class DangerButton(QPushButton):
    """危险操作按钮 - 红色填充"""

    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        self.setStyleSheet(
            _button_base_style(
                bg=Colors.DANGER,
                bg_hover=Colors.DANGER_HOVER,
                text_color="#FFFFFF",
                border="none",
            )
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)


class GhostButton(QPushButton):
    """幽灵按钮 - 无背景无边框"""

    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        self.setStyleSheet(
            _button_base_style(
                bg="",
                bg_hover=Colors.BG_HOVER,
                text_color=Colors.TEXT_SECONDARY,
                border="none",
            )
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)


# ═══════════════════════════════════════════════════════════
# 输入组件
# ═══════════════════════════════════════════════════════════


class LineEdit(QLineEdit):
    """带样式的单行输入框"""

    def __init__(self, placeholder: str = "", parent: QWidget = None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet(
            f"""
            QLineEdit {{
                background: {Colors.BG_BASE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Colors.RADIUS};
                padding: 6px 12px;
                font-size: 13px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Colors.BORDER_FOCUS};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_TERTIARY};
            }}
        """
        )
        self.setFixedHeight(36)


class ComboBox(QComboBox):
    """带样式的下拉选择框"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QComboBox {{
                background: {Colors.BG_BASE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Colors.RADIUS};
                padding: 6px 12px;
                font-size: 13px;
                color: {Colors.TEXT_PRIMARY};
                min-width: 120px;
            }}
            QComboBox:focus {{
                border-color: {Colors.BORDER_FOCUS};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {Colors.TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background: {Colors.BG_BASE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Colors.RADIUS};
                selection-background-color: #E3F2FD;
                selection-color: #1565C0;
                font-size: 13px;
            }}
        """
        )
        self.setFixedHeight(36)


class Checkbox(QCheckBox):
    """带样式的复选框"""

    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"""
            QCheckBox {{
                font-size: 13px;
                color: {Colors.TEXT_PRIMARY};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {Colors.BORDER};
                border-radius: 3px;
                background: {Colors.BG_BASE};
            }}
            QCheckBox::indicator:checked {{
                background: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.BORDER_FOCUS};
            }}
        """
        )


class InputWithLabel(QWidget):
    """带标签的输入框组合"""

    def __init__(self, label: str = "", parent: QWidget = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = QLabel(label)
        self.label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")

        self.input = LineEdit()
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(self.label)
        layout.addWidget(self.input)


# ═══════════════════════════════════════════════════════════
# 设备树组件
# ═══════════════════════════════════════════════════════════


class DeviceTree(QTreeWidget):
    """设备列表树形控件"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setHeaderLabels(["设备名称", "设备编号", "状态", "操作"])
        self.setAlternatingRowColors(True)
        self.setIndentation(0)
        self.setAnimated(True)
        self.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.setHeaderHidden(False)

        header = self.header()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStretchLastSection(False)
        # 设置各列比例
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(3, 170)  # 操作列宽度

        self.setStyleSheet(
            """
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
        )


# ═══════════════════════════════════════════════════════════
# 数据表格组件
# ═══════════════════════════════════════════════════════════


class DataTable(QTableWidget):
    """数据表格控件"""

    def __init__(self, columns: list = None, parent: QWidget = None):
        super().__init__(parent)
        if columns:
            self.setColumnCount(len(columns))
            self.setHorizontalHeaderLabels(columns)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)

        self.setStyleSheet(
            f"""
            QTableWidget {{
                background: {Colors.BG_BASE};
                alternate-background-color: #F9FAFB;
                border: 1px solid {Colors.BORDER};
                border-radius: {Colors.RADIUS_LG};
                font-size: 13px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid #F3F4F6;
            }}
            QTableWidget::item:hover {{
                background: {Colors.BG_HOVER};
            }}
            QTableWidget::item:selected {{
                background: #E3F2FD;
                color: #1565C0;
            }}
            QHeaderView::section {{
                background: #F6F8FA;
                color: #57606A;
                border: none;
                border-bottom: 1px solid #E5E7EB;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
        """
        )


# ═══════════════════════════════════════════════════════════
# 状态徽章组件
# ═══════════════════════════════════════════════════════════


class StatusBadge(QWidget):
    """状态徽章 - 带颜色圆点和文字"""

    STATUS_COLORS = {
        "online": "#4CAF50",
        "offline": "#9CA3AF",
        "warning": "#FFC107",
        "error": "#F44336",
        "info": "#2196F3",
        "success": "#4CAF50",
        "default": "#9CA3AF",
    }

    def __init__(self, text: str = "", status: str = "default", parent: QWidget = None):
        super().__init__(parent)
        self._status = status
        self._text = text

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)

        self._label = QLabel(text)
        self._label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_SECONDARY};")

        layout.addWidget(self._dot)
        layout.addWidget(self._label)

        self.set_status(status)

    def set_status(self, status: str) -> None:
        """设置状态"""
        self._status = status
        color = self.STATUS_COLORS.get(status, self.STATUS_COLORS["default"])
        self._dot.setStyleSheet(
            f"""
            background: {color};
            border-radius: 4px;
        """
        )

    def set_text(self, text: str) -> None:
        """设置文字"""
        self._label.setText(text)


# ═══════════════════════════════════════════════════════════
# 数据卡片组件
# ═══════════════════════════════════════════════════════════


class DataCard(QFrame):
    """数据卡片 - 显示设备参数值"""

    def __init__(self, title: str = "", value: str = "0.00", parent: QWidget = None):
        super().__init__(parent)
        self._title_text = title
        self._value_text = value

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"""
            DataCard {{
                background: {Colors.BG_BASE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Colors.RADIUS_LG};
                padding: 16px;
            }}
            DataCard:hover {{
                border-color: {Colors.BORDER_FOCUS};
                background: #F8FBFF;
            }}
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 24px; font-weight: 700;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label, 1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.unit_label = None  # 可选: 外部添加

    def set_value(self, value: str) -> None:
        """更新显示值"""
        self._value_text = value
        self.value_label.setText(value)


# ═══════════════════════════════════════════════════════════
# 操作卡片组件
# ═══════════════════════════════════════════════════════════


class ActionCard(QFrame):
    """操作卡片 - 带标题和按钮的快捷操作区域"""

    def __init__(self, title: str = "", parent: QWidget = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"""
            ActionCard {{
                background: {Colors.BG_BASE};
                border: 1px solid {Colors.BORDER};
                border-radius: {Colors.RADIUS_LG};
                padding: 16px;
            }}
        """
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(12)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        self._layout.addWidget(self.title_label)

    def add_widget(self, widget: QWidget) -> None:
        """添加子组件"""
        self._layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        """添加子布局"""
        self._layout.addLayout(layout)
