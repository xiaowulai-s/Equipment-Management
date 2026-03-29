"""
协议层 - Modbus协议实现

包含:
    - BaseProtocol: 协议抽象基类 (继承QObject, 支持信号槽)
    - ReadResult: 读取结果容器
    - WriteResult: 写入结果容器
    - ModbusTCPProtocol: ModbusTCP协议
    - ModbusRTUProtocol: ModbusRTU协议
    - ModbusASCIIProtocol: ModbusASCII协议
    - ProtocolType: 协议类型枚举
    - FunctionCode: Modbus功能码枚举
    - DeviceStatus: 设备状态枚举
    - RegisterType: 寄存器类型枚举
    - DataType: 数据类型枚举
    - Endian: 字节序枚举
"""

from src.protocols.base_protocol import BaseProtocol, ReadResult, WriteResult
from src.protocols.enums import DataType, DeviceStatus, Endian, FunctionCode, ProtocolType, RegisterType
from src.protocols.modbus_ascii import ModbusASCIIProtocol
from src.protocols.modbus_rtu import ModbusRTUProtocol
from src.protocols.modbus_tcp import ModbusTCPProtocol

__all__ = [
    "ProtocolType",
    "FunctionCode",
    "DeviceStatus",
    "RegisterType",
    "DataType",
    "Endian",
    "BaseProtocol",
    "ReadResult",
    "WriteResult",
    "ModbusTCPProtocol",
    "ModbusRTUProtocol",
    "ModbusASCIIProtocol",
]
