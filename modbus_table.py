"""
自定义控件 - Modbus寄存器表格
"""
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt


class ModbusRegisterTable(QTableWidget):
    """Modbus寄存器表格"""

    # 列名
    COLUMNS = ["地址", "功能码", "当前值", "状态"]

    # 示例数据
    DATA = [
        ["0x0001", "03", "25.5", "正常"],
        ["0x0002", "03", "123.4", "正常"],
        ["0x0003", "04", "405.0", "正常"],
        ["0x0004", "03", "38.2", "正常"],
        ["0x0005", "04", "89.1", "警告"],
        ["0x0006", "03", "67.8", "正常"],
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        # 设置表格属性
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setRowCount(len(self.DATA))

        # 设置表格样式
        self.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                border: none;
                color: #FFFFFF;
                gridline-color: #3A3A3A;
                font-family: "Consolas", "Microsoft YaHei";
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3A3A3A;
            }
            QTableWidget::item:selected {
                background-color: #0078D4;
            }
            QHeaderView::section {
                background-color: #1E1E1E;
                color: #FFFFFF;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #0078D4;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background: #2A2A2A;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #4A4A4A;
                border-radius: 5px;
            }
        """)

        # 设置列宽
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(0, 80)
        self.setColumnWidth(1, 70)
        self.setColumnWidth(3, 70)

        # 隐藏垂直表头
        self.verticalHeader().setVisible(False)

        # 填充数据
        self.populate_data()

    def populate_data(self):
        """填充表格数据"""
        for row, data in enumerate(self.DATA):
            for col, value in enumerate(data):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)

                # 状态列特殊样式
                if col == 3:
                    if value == "正常":
                        item.setForeground(QColor("#00FFAA"))
                    elif value == "警告":
                        item.setForeground(QColor("#FFAA00"))
                    else:
                        item.setForeground(QColor("#FF5555"))

                self.setItem(row, col, item)

    def update_register(self, address, value, status="正常"):
        """更新单个寄存器"""
        for row in range(self.rowCount()):
            if self.item(row, 0).text() == address:
                self.item(row, 2).setText(str(value))
                self.item(row, 3).setText(status)
                if status == "正常":
                    self.item(row, 3).setForeground(QColor("#00FFAA"))
                elif status == "警告":
                    self.item(row, 3).setForeground(QColor("#FFAA00"))
                else:
                    self.item(row, 3).setForeground(QColor("#FF5555"))
                break
