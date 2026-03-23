# -*- coding: utf-8 -*-
"""
工业设备管理系统 - QML桥接器
实现Python后端与QML界面的数据绑定和通信
"""

import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer

from DeviceModels import Device, DeviceGroup, DeviceStatus, Register, DeviceMonitorData
from ModbusClient import DeviceMonitor, DataSimulator
from DatabaseManager import DatabaseManager
from ConfigManager import ConfigManager

# 使用统一日志配置
from logging_config import get_logger
logger = get_logger(__name__)


class Backend(QObject):
    """
    QML后端桥接器
    提供与QML界面交互的接口
    """

    # ==================== QML信号定义 ====================
    # 数据更新信号
    dataUpdated = Signal(dict)
    temperatureChanged = Signal(float)
    pressureChanged = Signal(float)
    flowRateChanged = Signal(float)
    powerChanged = Signal(float)
    frequencyChanged = Signal(float)
    efficiencyChanged = Signal(float)

    # 设备状态信号
    connectionStatusChanged = Signal(str)
    onlineCountChanged = Signal(int)
    totalCountChanged = Signal(int)
    lastUpdateChanged = Signal(str)

    # 仪表盘信号
    gauge1Changed = Signal(float)
    gauge2Changed = Signal(float)
    gauge3Changed = Signal(float)
    gauge4Changed = Signal(float)
    gauge1StatusChanged = Signal(int)
    gauge2StatusChanged = Signal(int)
    gauge3StatusChanged = Signal(int)
    gauge4StatusChanged = Signal(int)

    # 趋势图信号
    trendDataChanged = Signal(list, list, list)

    # 设备列表信号
    deviceListChanged = Signal(list)
    selectedDeviceChanged = Signal(str)

    # 寄存器表信号
    registerDataChanged = Signal(list)

    # 系统信号
    systemMessage = Signal(str, str)  # (type, message)

    def __init__(self):
        super().__init__()

        # 数据库管理器
        self._db = DatabaseManager()

        # 配置管理器
        self._config_manager = ConfigManager()

        # 数据监控器
        self._monitor = DeviceMonitor()
        self._monitor.register_data_callback(self._on_data_received)

        # 当前设备数据
        self._current_device_id = "Pump-01"
        self._monitor_data = DeviceMonitorData()

        # 设备列表
        self._device_groups: List[Dict] = []

        # 寄存器数据
        self._register_data: List[Dict] = []

        # 状态
        self._connection_status = "未连接"
        self._online_count = 0
        self._total_count = 5

        # 趋势数据
        self._temp_data: List[float] = []
        self._pressure_data: List[float] = []
        self._flow_data: List[float] = []

        # 批量数据保存队列
        self._history_data_queue: List[Dict] = []
        self._queue_lock = threading.Lock()
        self._batch_save_timer = QTimer()
        self._batch_save_timer.timeout.connect(self._save_batch_history_data)
        self._batch_save_timer.start(5000)  # 每5秒批量保存一次历史数据

        # 初始化子模块
        self._initialize_device_groups()
        self._initialize_register_data()

        logger.info("Backend 初始化完成")

    def _initialize_device_groups(self):
        """初始化设备列表"""
        self._device_groups = [
            {
                "name": "泵站A区",
                "expanded": True,
                "devices": [
                    {"id": "Pump-01", "name": "Pump-01", "status": 0, "ip": "192.168.1.101"},
                    {"id": "Pump-02", "name": "Pump-02", "status": 0, "ip": "192.168.1.102"},
                    {"id": "Pump-03", "name": "Pump-03", "status": 1, "ip": "192.168.1.103"},
                ]
            },
            {
                "name": "泵站B区",
                "expanded": True,
                "devices": [
                    {"id": "Pump-04", "name": "Pump-04", "status": 2, "ip": "192.168.1.104"},
                    {"id": "Pump-05", "name": "Pump-05", "status": 0, "ip": "192.168.1.105"},
                ]
            }
        ]

        # 更新在线数量
        self._update_online_count()

    def _initialize_register_data(self):
        """初始化寄存器数据"""
        self._register_data = [
            {"address": "0x0001", "functionCode": "03", "variableName": "温度传感器", "value": "25.5", "unit": "°C", "status": 0, "statusText": "正常"},
            {"address": "0x0002", "functionCode": "03", "variableName": "压力变送器", "value": "1.23", "unit": "MPa", "status": 0, "statusText": "正常"},
            {"address": "0x0003", "functionCode": "03", "variableName": "流量计", "value": "50.3", "unit": "m³/h", "status": 1, "statusText": "预警"},
            {"address": "0x0004", "functionCode": "03", "variableName": "功率表", "value": "15.2", "unit": "kW", "status": 2, "statusText": "故障"},
            {"address": "0x0005", "functionCode": "03", "variableName": "频率", "value": "50.0", "unit": "Hz", "status": 0, "statusText": "正常"},
            {"address": "0x0006", "functionCode": "03", "variableName": "效率", "value": "95.2", "unit": "%", "status": 0, "statusText": "正常"},
            {"address": "0x0007", "functionCode": "03", "variableName": "入口压力", "value": "0.85", "unit": "MPa", "status": 0, "statusText": "正常"},
            {"address": "0x0008", "functionCode": "03", "variableName": "出口压力", "value": "1.23", "unit": "MPa", "status": 0, "statusText": "正常"},
        ]

    def _update_online_count(self):
        """更新在线设备数量"""
        online = 0
        total = 0
        for group in self._device_groups:
            total += len(group["devices"])
            for device in group["devices"]:
                if device["status"] == 0:  # 在线
                    online += 1

        if self._online_count != online:
            self._online_count = online
            self.onlineCountChanged.emit(online)

        if self._total_count != total:
            self._total_count = total
            self.totalCountChanged.emit(total)

    def _on_data_received(self, data: Dict):
        """接收模拟数据回调"""
        try:
            self._update_monitor_data(data)
        except Exception as e:
            logger.error(f"数据更新失败: {e}")

    def _update_monitor_data(self, data: Dict):
        """更新监控数据并发送信号"""
        # 更新数据
        temperature = data.get("temperature", 0)
        pressure = data.get("pressure", 0)
        flow_rate = data.get("flow_rate", 0)
        power = data.get("power", 0)
        frequency = data.get("frequency", 0)
        efficiency = data.get("efficiency", 0)

        # 发送数据信号
        self.temperatureChanged.emit(temperature)
        self.pressureChanged.emit(pressure)
        self.flowRateChanged.emit(flow_rate)
        self.powerChanged.emit(power)
        self.frequencyChanged.emit(frequency)
        self.efficiencyChanged.emit(efficiency)

        # 更新趋势数据
        self._temp_data.append(temperature)
        self._pressure_data.append(pressure)
        self._flow_data.append(flow_rate)

        # 保持最多60个数据点
        max_points = 60
        if len(self._temp_data) > max_points:
            self._temp_data.pop(0)
        if len(self._pressure_data) > max_points:
            self._pressure_data.pop(0)
        if len(self._flow_data) > max_points:
            self._flow_data.pop(0)

        self.trendDataChanged.emit(
            list(self._temp_data),
            list(self._pressure_data),
            list(self._flow_data)
        )

        # 更新仪表盘
        gauge1 = min(100, max(0, (temperature - 20) / 15 * 100))
        gauge2 = min(100, max(0, (pressure - 0.5) / 1.5 * 100))
        gauge3 = min(100, max(0, (flow_rate - 30) / 30 * 100))
        gauge4 = min(100, max(0, (efficiency - 80) / 20 * 100))

        self.gauge1Changed.emit(gauge1)
        self.gauge2Changed.emit(gauge2)
        self.gauge3Changed.emit(gauge3)
        self.gauge4Changed.emit(gauge4)

        # 仪表盘状态
        self.gauge1StatusChanged.emit(0 if gauge1 < 80 else (1 if gauge1 < 95 else 2))
        self.gauge2StatusChanged.emit(0 if gauge2 < 80 else (1 if gauge2 < 95 else 2))
        self.gauge3StatusChanged.emit(0 if gauge3 < 80 else (1 if gauge3 < 95 else 2))
        self.gauge4StatusChanged.emit(0 if gauge4 < 90 else (1 if gauge4 < 95 else 2))

        # 更新寄存器数据
        self._register_data[0]["value"] = f"{temperature:.1f}"
        self._register_data[1]["value"] = f"{pressure:.2f}"
        self._register_data[2]["value"] = f"{flow_rate:.1f}"
        self._register_data[3]["value"] = f"{power:.1f}"
        self._register_data[4]["value"] = f"{frequency:.1f}"
        self._register_data[5]["value"] = f"{efficiency:.1f}"
        self.registerDataChanged.emit(list(self._register_data))

        # 更新时间
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.lastUpdateChanged.emit(time_str)

        # 将数据添加到历史数据队列
        self._queue_history_data("Pump-01", 0x0001, "温度传感器", temperature, "°C", self._register_data[0]["status"])
        self._queue_history_data("Pump-01", 0x0002, "压力变送器", pressure, "MPa", self._register_data[1]["status"])
        self._queue_history_data("Pump-01", 0x0003, "流量计", flow_rate, "m³/h", self._register_data[2]["status"])
        self._queue_history_data("Pump-01", 0x0004, "功率表", power, "kW", self._register_data[3]["status"])
        self._queue_history_data("Pump-01", 0x0005, "频率", frequency, "Hz", self._register_data[4]["status"])
        self._queue_history_data("Pump-01", 0x0006, "效率", efficiency, "%", self._register_data[5]["status"])

        # 发送完整数据更新信号
        self.dataUpdated.emit(data)

    def _update_last_update_time(self):
        """更新最后更新时间"""
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.lastUpdateChanged.emit(time_str)

    def _queue_history_data(self, device_id: str, register_address: int, register_name: str, 
                          value: float, unit: str, status: int = 0):
        """将历史数据添加到队列"""
        try:
            with self._queue_lock:
                self._history_data_queue.append({
                    "device_id": device_id,
                    "timestamp": datetime.now(),
                    "register_address": register_address,
                    "register_name": register_name,
                    "value": value,
                    "unit": unit,
                    "status": status
                })
        except Exception as e:
            logger.error(f"添加历史数据到队列失败: {e}")

    def _save_batch_history_data(self):
        """批量保存历史数据到数据库"""
        try:
            with self._queue_lock:
                if not self._history_data_queue:
                    return
                
                # 复制并清空队列
                data_to_save = self._history_data_queue.copy()
                self._history_data_queue.clear()
            
            if data_to_save:
                # 批量保存到数据库
                self._db.batch_add_history_data(data_to_save)
        except Exception as e:
            logger.error(f"批量保存历史数据失败: {e}")

    # ==================== QML可调用槽函数 ====================
    # 配置管理API

    @Slot(str, result=str)
    def getUserSetting(self, key: str):
        """获取用户设置"""
        return self._config_manager.get_user_setting(key)

    @Slot(str, str)
    def setUserSetting(self, key: str, value: str):
        """设置用户设置"""
        self._config_manager.set_user_setting(key, value)

    @Slot()
    def resetUserSettings(self):
        """重置用户设置"""
        self._config_manager.reset_user_settings()

    @Slot()
    def saveUserSettings(self):
        """保存用户设置"""
        self._config_manager.save_user_settings()

    # 系统配置API

    @Slot(str, result=str)
    def getSystemConfig(self, key: str):
        """获取系统配置"""
        return self._db.get_system_config_value(key)

    @Slot(str, str)
    def setSystemConfig(self, key: str, value: str):
        """设置系统配置"""
        self._db.set_system_config_value(key, value)

    # 数据导出API

    @Slot(str, str, str, str, str, bool, result=bool)
    def exportHistoryData(self, device_id: str, register_address: str, 
                        start_time_str: str, end_time_str: str, 
                        file_path: str, include_headers: bool):
        """
        导出历史数据
        
        Args:
            device_id: 设备ID
            register_address: 寄存器地址，为空表示所有寄存器
            start_time_str: 开始时间字符串，格式为YYYY-MM-DD HH:MM:SS
            end_time_str: 结束时间字符串，格式为YYYY-MM-DD HH:MM:SS
            file_path: 导出文件路径
            include_headers: 是否包含表头
            
        Returns:
            bool: 导出成功返回True，否则返回False
        """
        try:
            # 解析时间
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S") if start_time_str else None
            end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S") if end_time_str else None
            
            # 解析寄存器地址
            register_address = int(register_address, 16) if register_address else None
            
            # 确定导出格式
            if file_path.endswith('.csv'):
                return self._db.export_history_data_csv(
                    device_id=device_id,
                    register_address=register_address,
                    start_time=start_time,
                    end_time=end_time,
                    file_path=file_path,
                    include_headers=include_headers
                )
            elif file_path.endswith('.xlsx'):
                return self._db.export_history_data_excel(
                    device_id=device_id,
                    register_address=register_address,
                    start_time=start_time,
                    end_time=end_time,
                    file_path=file_path,
                    include_headers=include_headers
                )
            else:
                logger.error(f"不支持的导出格式: {file_path}")
                return False
        except Exception as e:
            logger.error(f"导出历史数据失败: {e}")
            return False

    @Slot(str, bool, result=bool)
    def exportAllData(self, file_path: str, include_headers: bool):
        """
        导出所有设备的历史数据
        
        Args:
            file_path: 导出文件路径
            include_headers: 是否包含表头
            
        Returns:
            bool: 导出成功返回True，否则返回False
        """
        try:
            # 确定导出格式
            if file_path.endswith('.csv'):
                return self._db.export_all_data(
                    file_path=file_path,
                    format="csv",
                    include_headers=include_headers
                )
            elif file_path.endswith('.xlsx'):
                return self._db.export_all_data(
                    file_path=file_path,
                    format="excel",
                    include_headers=include_headers
                )
            else:
                logger.error(f"不支持的导出格式: {file_path}")
                return False
        except Exception as e:
            logger.error(f"导出所有数据失败: {e}")
            return False

    @Slot()
    def start_monitoring(self):
        """启动监控"""
        logger.info("启动监控...")
        self._connection_status = "已连接"
        self.connectionStatusChanged.emit(self._connection_status)
        self._monitor.start_simulation()
        self.systemMessage.emit("success", "监控系统已启动")

    @Slot()
    def stop_monitoring(self):
        """停止监控"""
        logger.info("停止监控...")
        self._connection_status = "已断开"
        self.connectionStatusChanged.emit(self._connection_status)
        self._monitor.stop_simulation()
        self.systemMessage.emit("info", "监控系统已停止")

    @Slot(str)
    def select_device(self, device_id: str):
        """选择设备"""
        logger.info(f"选择设备: {device_id}")
        self._current_device_id = device_id
        self.selectedDeviceChanged.emit(device_id)

    @Slot(result=str)
    def get_connection_status(self) -> str:
        """获取连接状态"""
        return self._connection_status

    @Slot(result=int)
    def get_online_count(self) -> int:
        """获取在线设备数"""
        return self._online_count

    @Slot(result=int)
    def get_total_count(self) -> int:
        """获取设备总数"""
        return self._total_count

    @Slot(result=str)
    def get_last_update(self) -> str:
        """获取最后更新时间"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @Slot(result=list)
    def get_device_groups(self) -> list:
        """获取设备分组列表"""
        return self._device_groups

    @Slot(result=list)
    def get_register_data(self) -> list:
        """获取寄存器数据"""
        return self._register_data

    @Slot(result=list)
    def get_temperature_data(self) -> list:
        """获取温度趋势数据"""
        return list(self._temp_data)

    @Slot(result=list)
    def get_pressure_data(self) -> list:
        """获取压力趋势数据"""
        return list(self._pressure_data)

    @Slot(result=list)
    def get_flow_data(self) -> list:
        """获取流量趋势数据"""
        return list(self._flow_data)

    # ==================== QML属性 ====================

    @Property(float, notify=temperatureChanged)
    def temperature(self) -> float:
        return self._monitor_data.temperature

    @Property(float, notify=pressureChanged)
    def pressure(self) -> float:
        return self._monitor_data.pressure

    @Property(float, notify=flowRateChanged)
    def flowRate(self) -> float:
        return self._monitor_data.flow_rate

    @Property(float, notify=powerChanged)
    def power(self) -> float:
        return self._monitor_data.power

    @Property(float, notify=frequencyChanged)
    def frequency(self) -> float:
        return self._monitor_data.frequency

    @Property(float, notify=efficiencyChanged)
    def efficiency(self) -> float:
        return self._monitor_data.efficiency

    @Property(str, notify=connectionStatusChanged)
    def connectionStatus(self) -> str:
        return self._connection_status

    @Property(int, notify=onlineCountChanged)
    def onlineCount(self) -> int:
        return self._online_count

    @Property(int, notify=totalCountChanged)
    def totalCount(self) -> int:
        return self._total_count

    @Property(str, notify=lastUpdateChanged)
    def lastUpdate(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 导出模块
__all__ = ['Backend', 'DeviceMonitor', 'DataSimulator']
