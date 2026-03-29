"""
设备管理层 - 设备模型与管理

包含:
    - Register: 寄存器数据模型 (继承QObject, 支持信号槽)
    - AlarmConfig: 报警阈值配置
    - AlarmLevel: 报警级别常量
    - Device: 设备数据模型 (继承QObject, 聚合Register)
    - TcpParams: TCP通信参数
    - SerialParams: 串口通信参数
    - PollConfig: 轮询配置
    - DeviceManager: 设备管理器 (CRUD + 搜索 + 批量操作 + 信号聚合 + 持久化)
    - DataCollector: 数据采集引擎 (并行轮询 + 失败重试 + 统计)
    - PollWorker: 单设备轮询工作线程
    - CollectorStats: 采集统计信息
    - create_protocol: 协议工厂函数
"""

from src.device.data_collector import CollectorStats, DataCollector, PollWorker, create_protocol
from src.device.device import Device, PollConfig, SerialParams, TcpParams
from src.device.device_manager import DeviceManager
from src.device.register import AlarmConfig, AlarmLevel, Register

__all__ = [
    # 寄存器模型
    "Register",
    "AlarmConfig",
    "AlarmLevel",
    # 设备模型
    "Device",
    "TcpParams",
    "SerialParams",
    "PollConfig",
    # 设备管理器
    "DeviceManager",
    # 数据采集引擎
    "DataCollector",
    "PollWorker",
    "CollectorStats",
    "create_protocol",
]
