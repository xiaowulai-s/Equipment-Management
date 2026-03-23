# -*- coding: utf-8 -*-
"""
工业设备管理系统 - 数据模型层
定义设备、数据点、寄存器等数据模型
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import threading


class DeviceStatus(Enum):
    """设备状态枚举"""
    ONLINE = 0      # 在线
    WARNING = 1     # 警告
    OFFLINE = 2     # 离线
    FAULT = 3       # 故障


class RegisterType(Enum):
    """寄存器类型枚举"""
    HOLDING_REGISTER = 3      # 保持寄存器 (Read Holding Registers)
    INPUT_REGISTER = 4        # 输入寄存器 (Read Input Registers)
    COIL = 1                  # 线圈 (Read/Write Coils)
    DISCRETE_INPUT = 2        # 离散输入 (Read Discrete Inputs)


@dataclass
class Register:
    """Modbus寄存器数据模型"""
    address: int              # 寄存器地址
    name: str                 # 寄存器名称
    value: float              # 当前值
    unit: str                 # 单位
    register_type: RegisterType  # 寄存器类型
    raw_value: int = 0        # 原始整数值
    status: int = 0           # 状态 (0:正常, 1:警告, 2:故障)
    min_value: float = 0.0    # 最小值
    max_value: float = 100.0  # 最大值
    scale: float = 1.0        # 缩放因子
    timestamp: Optional[datetime] = None  # 最后更新时间

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def percentage(self) -> float:
        """获取百分比值"""
        if self.max_value == self.min_value:
            return 0.0
        return ((self.value - self.min_value) / (self.max_value - self.min_value)) * 100

    def update_value(self, raw_value: int, timestamp: Optional[datetime] = None):
        """更新寄存器值"""
        self.raw_value = raw_value
        self.value = raw_value * self.scale
        self.timestamp = timestamp or datetime.now()


@dataclass
class Device:
    """设备抽象层 - 实现统一的设备接口"""
    id: str                           # 设备ID
    name: str                         # 设备名称
    ip_address: str                   # IP地址
    port: int = 502                   # 端口
    slave_id: int = 1                 # 从机ID
    status: DeviceStatus = DeviceStatus.OFFLINE
    registers: Dict[int, Register] = field(default_factory=dict)
    last_update: Optional[datetime] = None
    group: str = ""                   # 设备分组
    description: str = ""             # 设备描述
    product_id: Optional[str] = None  # 产品ID
    communication_params: Dict[str, Any] = field(default_factory=dict)  # 通信参数

    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()

    def add_register(self, register: Register):
        """添加寄存器"""
        self.registers[register.address] = register

    def get_register(self, address: int) -> Optional[Register]:
        """获取寄存器"""
        return self.registers.get(address)

    def get_register_by_name(self, name: str) -> Optional[Register]:
        """根据名称获取寄存器"""
        for register in self.registers.values():
            if register.name == name:
                return register
        return None

    def update_register(self, address: int, raw_value: int, timestamp: Optional[datetime] = None) -> bool:
        """更新寄存器值"""
        register = self.get_register(address)
        if register:
            register.update_value(raw_value, timestamp)
            self.last_update = timestamp or datetime.now()
            return True
        return False

    def update_status(self, status: DeviceStatus):
        """更新设备状态"""
        self.status = status
        self.last_update = datetime.now()

    def is_online(self) -> bool:
        """检查设备是否在线"""
        return self.status == DeviceStatus.ONLINE

    def get_online_count(self) -> int:
        """获取在线设备数量"""
        return 1 if self.is_online() else 0

    def get_register_values(self) -> Dict[int, float]:
        """获取所有寄存器的当前值"""
        return {addr: reg.value for addr, reg in self.registers.items()}

    def get_register_status(self) -> Dict[int, int]:
        """获取所有寄存器的状态"""
        return {addr: reg.status for addr, reg in self.registers.items()}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "port": self.port,
            "slave_id": self.slave_id,
            "status": self.status.name,
            "status_code": self.status.value,
            "group": self.group,
            "description": self.description,
            "product_id": self.product_id,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "register_count": len(self.registers),
            "online": self.is_online()
        }

    def from_config(self, config: Dict[str, Any]):
        """从配置字典加载设备信息"""
        self.name = config.get("name", self.name)
        self.ip_address = config.get("ip_address", self.ip_address)
        self.port = config.get("port", self.port)
        self.slave_id = config.get("slave_id", self.slave_id)
        self.group = config.get("group", self.group)
        self.description = config.get("description", self.description)
        self.product_id = config.get("product_id", self.product_id)
        self.communication_params = config.get("communication_params", self.communication_params)


@dataclass
class DeviceGroup:
    """设备分组数据模型 - 管理一组设备"""
    name: str                         # 分组名称
    devices: List[Device] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"group_{datetime.now().timestamp()}")  # 分组ID
    description: str = ""             # 分组描述
    parent_group_id: Optional[str] = None  # 父分组ID

    def add_device(self, device: Device) -> bool:
        """添加设备到分组"""
        if device not in self.devices:
            self.devices.append(device)
            device.group = self.name
            return True
        return False

    def remove_device(self, device: Device) -> bool:
        """从分组中移除设备"""
        if device in self.devices:
            self.devices.remove(device)
            device.group = ""
            return True
        return False

    def remove_device_by_id(self, device_id: str) -> bool:
        """根据设备ID移除设备"""
        for device in self.devices:
            if device.id == device_id:
                return self.remove_device(device)
        return False

    def get_device(self, device_id: str) -> Optional[Device]:
        """根据设备ID获取设备"""
        for device in self.devices:
            if device.id == device_id:
                return device
        return None

    def get_online_count(self) -> int:
        """获取分组内在线设备数"""
        return sum(1 for d in self.devices if d.is_online())

    def get_warning_count(self) -> int:
        """获取分组内警告设备数"""
        return sum(1 for d in self.devices if d.status == DeviceStatus.WARNING)

    def get_fault_count(self) -> int:
        """获取分组内故障设备数"""
        return sum(1 for d in self.devices if d.status == DeviceStatus.FAULT)

    def get_offline_count(self) -> int:
        """获取分组内离线设备数"""
        return sum(1 for d in self.devices if d.status == DeviceStatus.OFFLINE)

    def get_total_count(self) -> int:
        """获取分组内设备总数"""
        return len(self.devices)

    def get_devices_by_status(self, status: DeviceStatus) -> List[Device]:
        """根据状态获取设备列表"""
        return [d for d in self.devices if d.status == status]

    def get_devices_by_product(self, product_id: str) -> List[Device]:
        """根据产品ID获取设备列表"""
        return [d for d in self.devices if d.product_id == product_id]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_group_id": self.parent_group_id,
            "total_count": self.get_total_count(),
            "online_count": self.get_online_count(),
            "warning_count": self.get_warning_count(),
            "fault_count": self.get_fault_count(),
            "offline_count": self.get_offline_count(),
            "device_ids": [d.id for d in self.devices]
        }


class DataPoint:
    """数据点记录（用于历史数据）"""
    def __init__(self, timestamp: datetime, value: float):
        self.timestamp = timestamp
        self.value = value


class DataSeries:
    """数据序列（用于图表）"""
    def __init__(self, max_points: int = 60):
        self.max_points = max_points
        self.data_points: List[DataPoint] = []
        self._lock = threading.Lock()

    def add_point(self, value: float, timestamp: Optional[datetime] = None):
        """添加数据点"""
        with self._lock:
            ts = timestamp or datetime.now()
            self.data_points.append(DataPoint(ts, value))

            # 保持最大数据点数
            while len(self.data_points) > self.max_points:
                self.data_points.pop(0)

    def get_values(self) -> List[float]:
        """获取所有值"""
        with self._lock:
            return [dp.value for dp in self.data_points]

    def clear(self):
        """清空数据"""
        with self._lock:
            self.data_points.clear()


class GaugeData:
    """仪表盘数据"""
    def __init__(self, title: str, value: float = 0, min_value: float = 0,
                 max_value: float = 100, unit: str = "%", status: int = 0):
        self.title = title
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self.status = status


class DeviceMonitorData:
    """设备监控数据（用于界面显示）"""
    def __init__(self):
        self.temperature = 0.0
        self.pressure = 0.0
        self.flow_rate = 0.0
        self.power = 0.0
        self.frequency = 0.0
        self.efficiency = 0.0

        # 趋势数据
        self.temperature_series = DataSeries()
        self.pressure_series = DataSeries()
        self.flow_series = DataSeries()

        # 仪表盘数据
        self.gauges: List[GaugeData] = [
            GaugeData("SQ10", 0, 0, 100, "%", 0),
            GaugeData("AR2", 0, 0, 100, "%", 0),
            GaugeData("B", 0, 0, 100, "%", 0),
            GaugeData("C", 0, 0, 100, "%", 0),
        ]

    def update_readings(self, temp: float, pressure: float, flow: float,
                       power: float, freq: float, eff: float):
        """更新所有读数"""
        self.temperature = temp
        self.pressure = pressure
        self.flow_rate = flow
        self.power = power
        self.frequency = freq
        self.efficiency = eff

        # 添加到趋势序列
        self.temperature_series.add_point(temp)
        self.pressure_series.add_point(pressure)
        self.flow_series.add_point(flow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "temperature": self.temperature,
            "pressure": self.pressure,
            "flow_rate": self.flow_rate,
            "power": self.power,
            "frequency": self.frequency,
            "efficiency": self.efficiency,
        }


# 模拟设备数据工厂
class MockDeviceFactory:
    """模拟设备数据工厂"""

    @staticmethod
    def create_pump_station_a() -> Device:
        """创建泵站A设备"""
        device = Device(
            id="Pump-01",
            name="Pump-01",
            ip_address="192.168.1.101",
            port=502,
            slave_id=1,
            status=DeviceStatus.ONLINE,
            group="泵站A区",
            description="主泵机组"
        )

        # 添加寄存器
        registers = [
            Register(0x0001, "温度传感器", 25.5, "°C", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=100, scale=0.1),
            Register(0x0002, "压力变送器", 1.23, "MPa", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=2, scale=0.01),
            Register(0x0003, "流量计", 50.3, "m³/h", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=100, scale=0.1),
            Register(0x0004, "功率表", 15.2, "kW", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=50, scale=0.1),
            Register(0x0005, "频率", 50.0, "Hz", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=60, scale=0.1),
            Register(0x0006, "效率", 95.2, "%", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=100, scale=0.1),
            Register(0x0007, "入口压力", 0.85, "MPa", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=2, scale=0.01),
            Register(0x0008, "出口压力", 1.23, "MPa", RegisterType.HOLDING_REGISTER,
                    min_value=0, max_value=2, scale=0.01),
        ]

        for reg in registers:
            device.add_register(reg)

        return device

    @staticmethod
    def create_device_groups() -> List[DeviceGroup]:
        """创建设备分组"""
        groups = []

        # 泵站A区
        group_a = DeviceGroup(name="泵站A区")
        for i in range(1, 4):
            device = Device(
                id=f"Pump-0{i}",
                name=f"Pump-0{i}",
                ip_address=f"192.168.1.10{i}",
                port=502,
                slave_id=i,
                status=DeviceStatus.ONLINE if i < 3 else DeviceStatus.WARNING,
                group="泵站A区"
            )
            group_a.devices.append(device)
        groups.append(group_a)

        # 泵站B区
        group_b = DeviceGroup(name="泵站B区")
        for i in range(4, 6):
            device = Device(
                id=f"Pump-0{i}",
                name=f"Pump-0{i}",
                ip_address=f"192.168.1.10{i}",
                port=502,
                slave_id=i,
                status=DeviceStatus.OFFLINE if i == 4 else DeviceStatus.ONLINE,
                group="泵站B区"
            )
            group_b.devices.append(device)
        groups.append(group_b)

        return groups
