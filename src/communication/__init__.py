"""
通信驱动层 - 底层通信驱动实现

包含:
    - BaseDriver: 驱动抽象基类 (继承QObject, 支持信号槽)
    - DriverState: 驱动状态常量
    - DriverStats: 驱动性能统计
    - TcpDriver: TCP通信驱动 (基于socket, 非阻塞I/O+select超时+Keepalive)
    - SerialDriver: 串口通信驱动 (基于pyserial, 流控+热插拔+缓冲区)
    - DriverManager: 驱动管理器 (连接池/自动重连/心跳, 待步骤3.4实现)
"""

from src.communication.base_driver import BaseDriver, DriverState, DriverStats
from src.communication.serial_driver import BaudRate, DataBits, Parity, SerialDriver, StopBits
from src.communication.tcp_driver import TcpDriver

__all__ = [
    "BaseDriver",
    "DriverState",
    "DriverStats",
    "TcpDriver",
    "SerialDriver",
    "BaudRate",
    "DataBits",
    "StopBits",
    "Parity",
]
