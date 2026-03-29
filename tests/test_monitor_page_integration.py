# -*- coding: utf-8 -*-
"""
MonitorPage 集成测试窗口

演示如何将 MonitorPage 集成到 MainWindow 中使用。
"""

import sys
from datetime import datetime, timedelta
from typing import Dict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.device import AlarmConfig, AlarmLevel, Device, DeviceStatus, Register, TcpParams
from src.protocols import DataType, ProtocolType
from ui.monitor_page import MonitorPage


class MockDeviceManager:
    """模拟设备管理器，用于演示"""

    def __init__(self):
        self._devices: Dict[str, Device] = {}
        self._create_mock_devices()

    def _create_mock_devices(self):
        """创建模拟设备"""
        # 设备1: 温度传感器
        tcp_params1 = TcpParams(
            host="192.168.1.10",
            port=502,
        )

        device1 = Device(
            name="温度传感器 #1",
            device_id="TEMP-001",
            protocol_type=ProtocolType.MODBUS_TCP,
            tcp_params=tcp_params1,
            poll_interval=1.0,
        )

        # 添加寄存器
        device1.add_register(
            Register(
                address=40001,
                name="环境温度",
                description="环境温度测量值",
                data_type=DataType.FLOAT32,
                unit="°C",
            )
        )

        device1.add_register(
            Register(
                address=40002,
                name="设备温度",
                description="设备内部温度",
                data_type=DataType.FLOAT32,
                unit="°C",
            )
        )

        device1.add_register(
            Register(
                address=40003,
                name="湿度",
                description="环境湿度",
                data_type=DataType.FLOAT32,
                unit="%RH",
            )
        )

        device1.add_register(
            Register(
                address=40004,
                name="压力",
                description="管道压力",
                data_type=DataType.FLOAT32,
                unit="MPa",
            )
        )

        # 设备2: 压力变送器
        tcp_params2 = TcpParams(
            host="192.168.1.11",
            port=502,
        )

        device2 = Device(
            name="压力变送器 #1",
            device_id="PRESS-001",
            protocol_type=ProtocolType.MODBUS_TCP,
            tcp_params=tcp_params2,
            poll_interval=1.0,
        )

        # 添加寄存器 (带报警配置)
        device2.add_register(
            Register(
                address=40001,
                name="系统压力",
                description="主系统压力",
                data_type=DataType.FLOAT32,
                unit="MPa",
            )
        )

        # 给系统压力添加报警配置
        sys_pressure = device2.registers["系统压力"]
        sys_pressure.alarm_config = AlarmConfig(
            enabled=True,
            high_high=2.0,
            high=1.8,
            low=0.2,
            low_low=0.1,
            deadband=0.05,
            level=AlarmLevel.HIGH_HIGH,
        )

        device2.add_register(
            Register(
                address=40002,
                name="系统温度",
                description="系统工作温度",
                data_type=DataType.FLOAT32,
                unit="°C",
            )
        )

        # 给系统温度添加报警配置
        sys_temp = device2.registers["系统温度"]
        sys_temp.alarm_config = AlarmConfig(
            enabled=True,
            high_high=80.0,
            high=70.0,
            low=20.0,
            low_low=10.0,
            deadband=2.0,
            level=AlarmLevel.HIGH,
        )

        # 设备3: 液位传感器
        tcp_params3 = TcpParams(
            host="192.168.1.12",
            port=502,
        )

        device3 = Device(
            name="液位传感器 #1",
            device_id="LEVEL-001",
            protocol_type=ProtocolType.MODBUS_TCP,
            tcp_params=tcp_params3,
            poll_interval=1.0,
        )

        device3.add_register(
            Register(
                address=40001,
                name="液位高度",
                description="储罐液位高度",
                data_type=DataType.FLOAT32,
                unit="m",
            )
        )

        device3.add_register(
            Register(
                address=40002,
                name="流量",
                description="液体流量",
                data_type=DataType.FLOAT32,
                unit="m³/h",
            )
        )

        # 保存设备
        self._devices["TEMP-001"] = device1
        self._devices["PRESS-001"] = device2
        self._devices["LEVEL-001"] = device3

    def get_device(self, device_id: str):
        """获取设备"""
        return self._devices.get(device_id)

    def get_all_devices(self):
        """获取所有设备"""
        return list(self._devices.values())


class MainWindowDemo(QMainWindow):
    """演示主窗口 - 展示MonitorPage集成"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MonitorPage 集成演示")
        self.setMinimumSize(1400, 900)

        # 模拟设备管理器
        self.device_manager = MockDeviceManager()
        self._current_device = None

        # 模拟数据更新定时器
        self._simulation_timer = QTimer()
        self._simulation_timer.timeout.connect(self._simulate_data_update)

        self._setup_ui()
        self._connect_signals()
        self._refresh_device_list()

    def _setup_ui(self):
        """初始化UI"""
        # 创建中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左侧面板 (设备列表) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        # 搜索框
        search_layout = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索设备...")
        self._search_edit.textChanged.connect(self._refresh_device_list)
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self._search_edit)
        left_layout.addLayout(search_layout)

        # 设备树
        self._device_tree = QTreeWidget()
        self._device_tree.setHeaderLabels(["设备名称", "设备ID", "状态"])
        self._device_tree.setColumnWidth(0, 200)
        self._device_tree.setColumnWidth(1, 150)
        self._device_tree.setColumnWidth(2, 100)
        self._device_tree.itemSelectionChanged.connect(self._on_device_selected)
        left_layout.addWidget(self._device_tree)

        splitter.addWidget(left_panel)

        # === 右侧面板 (MonitorPage) ===
        self._monitor_page = MonitorPage()
        self._monitor_page.register_clicked.connect(self._on_register_clicked)
        splitter.addWidget(self._monitor_page)

        # 设置分割器比例
        splitter.setStretchFactor(0, 25)
        splitter.setStretchFactor(1, 75)
        splitter.setSizes([350, 1050])

        main_layout.addWidget(splitter)

    def _connect_signals(self):
        """连接信号"""
        pass

    def _refresh_device_list(self, search_text: str = ""):
        """刷新设备列表"""
        self._device_tree.clear()

        devices = self.device_manager.get_all_devices()

        for device in devices:
            if search_text and search_text.lower() not in device.name.lower():
                continue

            item = QTreeWidgetItem(
                [
                    device.name,
                    device.device_id,
                    "已连接" if device.status == DeviceStatus.CONNECTED else "未连接",
                ]
            )

            # 设置设备ID为用户数据
            item.setData(0, Qt.ItemDataRole.UserRole, device.device_id)

            # 根据状态设置颜色
            if device.status == DeviceStatus.CONNECTED:
                item.setForeground(2, Qt.GlobalColor.green)
            else:
                item.setForeground(2, Qt.GlobalColor.gray)

            self._device_tree.addTopLevelItem(item)

    def _on_device_selected(self):
        """设备选择事件"""
        selected_items = self._device_tree.selectedItems()

        if not selected_items:
            self._monitor_page.set_device(None)
            self._simulation_timer.stop()
            self._current_device = None
            return

        device_id = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        device = self.device_manager.get_device(device_id)

        if device:
            self._current_device = device
            self._monitor_page.set_device(device)

            # 启动模拟数据更新
            self._simulation_timer.start(1000)

    def _on_register_clicked(self, device_id: str, register_address: int):
        """寄存器点击事件"""
        print(f"点击了寄存器: 设备={device_id}, 地址={register_address}")

    def _simulate_data_update(self):
        """模拟数据更新"""
        if not self._current_device:
            return

        import random

        now = datetime.now().timestamp()

        # 随机更新每个寄存器的值
        for reg in self._current_device.registers.values():
            # 根据数据类型生成随机值
            if reg.data_type == DataType.FLOAT32:
                if "温度" in reg.name:
                    # 温度: 20-80°C
                    base = 50
                    variation = random.uniform(-5, 5)
                    value = base + variation
                elif "压力" in reg.name:
                    # 压力: 0-2.0 MPa
                    base = 1.5
                    variation = random.uniform(-0.3, 0.3)
                    value = max(0, base + variation)
                elif "湿度" in reg.name:
                    # 湿度: 40-80%
                    base = 60
                    variation = random.uniform(-10, 10)
                    value = max(0, min(100, base + variation))
                elif "液位" in reg.name:
                    # 液位: 0-5m
                    base = 2.5
                    variation = random.uniform(-0.5, 0.5)
                    value = max(0, min(5, base + variation))
                elif "流量" in reg.name:
                    # 流量: 0-100 m³/h
                    base = 50
                    variation = random.uniform(-15, 15)
                    value = max(0, min(100, base + variation))
                else:
                    value = random.uniform(0, 100)
            else:
                value = random.uniform(0, 100)

            # 更新当前数据
            self._current_device.current_data[reg.address] = value

        # 更新MonitorPage显示
        self._monitor_page.update_data()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    window = MainWindowDemo()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
