"""
自定义控件 - Modbus寄存器表格 v2.0
现代化工业风格设计
"""
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QFrame
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt


class ModbusRegisterTable(QTableWidget):
    """Modbus寄存器表格 - 现代化工业风格"""

    # 列名
    COLUMNS = ["Address", "Function", "Value", "Status"]

    # 示例数据
    DATA = [
        ["0x0001", "03", "25.5", "OK"],
        ["0x0002", "03", "123.4", "OK"],
        ["0x0003", "04", "405.0", "OK"],
        ["0x0004", "03", "38.2", "OK"],
        ["0x0005", "04", "89.1", "Warning"],
        ["0x0006", "03", "67.8", "OK"],
        ["0x0007", "03", "45.2", "OK"],
        ["0x0008", "04", "78.9", "Warning"],
    ]

    # 颜色配置
    COLORS = {
        'bg': '#161B22',
        'bg_alternate': '#1C2128',
        'grid': '#21262D',
        'header_bg': '#0F1419',
        'header_text': '#8B949E',
        'text_primary': '#E6EDF3',
        'text_secondary': '#8B949E',
        'text_tertiary': '#6E7681',
        'border': '#30363D',
        'primary': '#388BFD',
        'success': '#3FB950',
        'warning': '#D29922',
        'error': '#F85149',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        # 设置表格属性
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setRowCount(len(self.DATA))

        # 启用交替行颜色
        self.setAlternatingRowColors(True)

        # 设置表格样式
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.COLORS['bg']};
                alternate-background-color: {self.COLORS['bg_alternate']};
                border: none;
                color: {self.COLORS['text_primary']};
                gridline-color: {self.COLORS['grid']};
                gridline-width: 1px;
                font-family: "Consolas", "Segoe UI";
                font-size: 12px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {self.COLORS['grid']};
            }}
            QTableWidget::item:selected {{
                background-color: {self.COLORS['primary']}30;
                color: {self.COLORS['text_primary']};
            }}
            QTableWidget::item:hover {{
                background-color: {self.COLORS['bg_alternate']};
            }}
            QHeaderView::section {{
                background-color: {self.COLORS['header_bg']};
                color: {self.COLORS['header_text']};
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid {self.COLORS['primary']};
                border-right: 1px solid {self.COLORS['grid']};
                font-family: "Segoe UI";
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QScrollBar:vertical {{
                background: {self.COLORS['bg']};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.COLORS['border']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:hover {{
                background: {self.COLORS['text_tertiary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {self.COLORS['bg']};
                height: 8px;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.COLORS['border']};
                border-radius: 4px;
                min-width: 20px;
            }}
        """)

        # 设置列宽
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(0, 90)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(3, 80)

        # 设置行高
        self.verticalHeader().setDefaultSectionSize(40)

        # 隐藏垂直表头
        self.verticalHeader().setVisible(False)

        # 禁止编辑
        self.setEditTriggers(QTableWidget.NoEditTriggers)

        # 选择模式
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)

        # 填充数据
        self.populate_data()

    def populate_data(self):
        """填充表格数据"""
        for row, data in enumerate(self.DATA):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)

                # 地址列样式
                if col == 0:
                    item.setFont(QFont("Consolas", 11, QFont.Medium))
                    item.setForeground(QColor(self.COLORS['primary']))

                # 功能码列样式
                elif col == 1:
                    item.setFont(QFont("Consolas", 11))
                    item.setForeground(QColor(self.COLORS['text_tertiary']))

                # 数值列样式
                elif col == 2:
                    item.setFont(QFont("Consolas", 12, QFont.Bold))
                    item.setForeground(QColor(self.COLORS['text_primary']))

                # 状态列特殊样式
                elif col == 3:
                    item.setFont(QFont("Segoe UI", 10, QFont.Medium))
                    if value == "OK":
                        item.setForeground(QColor(self.COLORS['success']))
                    elif value == "Warning":
                        item.setForeground(QColor(self.COLORS['warning']))
                    else:
                        item.setForeground(QColor(self.COLORS['error']))

                self.setItem(row, col, item)

    def update_register(self, address, value, status="OK"):
        """更新单个寄存器"""
        for row in range(self.rowCount()):
            if self.item(row, 0).text() == address:
                self.item(row, 2).setText(str(value))
                self.item(row, 3).setText(status)

                if status == "OK":
                    self.item(row, 3).setForeground(QColor(self.COLORS['success']))
                elif status == "Warning":
                    self.item(row, 3).setForeground(QColor(self.COLORS['warning']))
                else:
                    self.item(row, 3).setForeground(QColor(self.COLORS['error']))
                break

    def add_register(self, address, function, value, status="OK"):
        """添加新寄存器"""
        row = self.rowCount()
        self.insertRow(row)

        data = [address, function, str(value), status]
        for col, value in enumerate(data):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)

            if col == 0:
                item.setFont(QFont("Consolas", 11, QFont.Medium))
                item.setForeground(QColor(self.COLORS['primary']))
            elif col == 1:
                item.setFont(QFont("Consolas", 11))
                item.setForeground(QColor(self.COLORS['text_tertiary']))
            elif col == 2:
                item.setFont(QFont("Consolas", 12, QFont.Bold))
                item.setForeground(QColor(self.COLORS['text_primary']))
            elif col == 3:
                item.setFont(QFont("Segoe UI", 10, QFont.Medium))
                if status == "OK":
                    item.setForeground(QColor(self.COLORS['success']))
                elif status == "Warning":
                    item.setForeground(QColor(self.COLORS['warning']))
                else:
                    item.setForeground(QColor(self.COLORS['error']))

            self.setItem(row, col, item)