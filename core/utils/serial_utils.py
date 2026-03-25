# -*- coding: utf-8 -*-
"""
串口工具模块
Serial Port Utilities
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from serial.tools import list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    list_ports = None


@dataclass
class SerialPortInfo:
    """串口端口信息"""

    device: str  # 设备名称，如 'COM1'
    description: str  # 描述
    hwid: str  # 硬件 ID
    vid: Optional[str]  # Vendor ID
    pid: Optional[str]  # Product ID
    serial_number: Optional[str]  # 序列号
    location: Optional[str]  # 位置
    manufacturer: Optional[str]  # 制造商
    product: Optional[str]  # 产品名称
    interface: Optional[str]  # 接口


def list_serial_ports() -> List[str]:
    """
    枚举可用串口

    Returns:
        List[str]: 串口设备名称列表，如 ['COM1', 'COM2', ...]
    """
    if not SERIAL_AVAILABLE:
        return []

    return [port.device for port in list_ports.comports()]


def get_serial_ports_info() -> List[SerialPortInfo]:
    """
    获取串口详细信息

    Returns:
        List[SerialPortInfo]: 串口信息列表
    """
    if not SERIAL_AVAILABLE:
        return []

    ports_info = []
    for port in list_ports.comports():
        info = SerialPortInfo(
            device=port.device,
            description=port.description,
            hwid=port.hwid,
            vid=port.vid,
            pid=port.pid,
            serial_number=port.serial_number,
            location=port.location,
            manufacturer=port.manufacturer,
            product=port.product,
            interface=port.interface,
        )
        ports_info.append(info)

    return ports_info


def get_serial_port_by_description(keyword: str) -> Optional[str]:
    """
    根据描述查找串口

    Args:
        keyword: 搜索关键词

    Returns:
        Optional[str]: 找到的串口设备名称，未找到返回 None
    """
    if not SERIAL_AVAILABLE:
        return None

    for port in list_ports.comports():
        if keyword.lower() in port.description.lower():
            return port.device

    return None


def get_serial_port_details(device: str) -> Optional[SerialPortInfo]:
    """
    获取指定串口的详细信息

    Args:
        device: 串口设备名称，如 'COM1'

    Returns:
        Optional[SerialPortInfo]: 串口信息，未找到返回 None
    """
    if not SERIAL_AVAILABLE:
        return None

    for port in list_ports.comports():
        if port.device == device:
            return SerialPortInfo(
                device=port.device,
                description=port.description,
                hwid=port.hwid,
                vid=port.vid,
                pid=port.pid,
                serial_number=port.serial_number,
                location=port.location,
                manufacturer=port.manufacturer,
                product=port.product,
                interface=port.interface,
            )

    return None


def serial_port_to_dict(port: Any) -> Dict[str, Any]:
    """
    将串口对象转换为字典

    Args:
        port: 串口对象

    Returns:
        Dict[str, Any]: 串口信息字典
    """
    if not SERIAL_AVAILABLE:
        return {}

    return {
        "device": port.device,
        "description": port.description,
        "hwid": port.hwid,
        "vid": port.vid,
        "pid": port.pid,
        "serial_number": port.serial_number,
        "location": port.location,
        "manufacturer": port.manufacturer,
        "product": port.product,
        "interface": port.interface,
    }


def list_serial_ports_as_dict() -> List[Dict[str, Any]]:
    """
    以字典列表形式返回所有串口信息

    Returns:
        List[Dict[str, Any]]: 串口信息字典列表
    """
    if not SERIAL_AVAILABLE:
        return []

    return [serial_port_to_dict(port) for port in list_ports.comports()]


# 便捷函数
def is_serial_available() -> bool:
    """
    检查 pyserial 是否可用

    Returns:
        bool: 是否可用
    """
    return SERIAL_AVAILABLE


def get_port_count() -> int:
    """
    获取可用串口数量

    Returns:
        int: 串口数量
    """
    if not SERIAL_AVAILABLE:
        return 0

    return len(list_ports.comports())


def test_serial_port(
    device: str, baudrate: int = 9600, timeout: float = 1.0, test_data: bytes = b"AT\r\n"
) -> tuple[bool, str]:
    """
    测试串口是否可用

    Test if serial port is available

    Args:
        device: 串口设备名称，如 'COM1'
        baudrate: 波特率，默认 9600
        timeout: 超时时间（秒），默认 1.0
        test_data: 测试数据，默认 b"AT\\r\\n"

    Returns:
        tuple[bool, str]: (是否成功，消息)
    """
    if not SERIAL_AVAILABLE:
        return False, "pyserial 未安装"

    try:
        import serial

        # 尝试打开串口
        ser = serial.Serial(port=device, baudrate=baudrate, timeout=timeout)

        # 发送测试数据
        ser.write(test_data)

        # 尝试读取响应（非必需）
        try:
            response = ser.read(100)  # 最多读取 100 字节
        except:
            response = b""

        # 关闭串口
        ser.close()

        return True, f"串口 {device} 测试成功"

    except serial.SerialException as e:
        return False, f"串口错误：{str(e)}"
    except Exception as e:
        return False, f"测试失败：{str(e)}"


def get_serial_port_status(device: str) -> dict:
    """
    获取串口状态信息

    Get serial port status information

    Args:
        device: 串口设备名称

    Returns:
        dict: 串口状态字典
    """
    if not SERIAL_AVAILABLE:
        return {"available": False, "error": "pyserial 未安装"}

    try:
        import serial

        # 检查串口是否存在
        port_info = get_serial_port_details(device)
        if not port_info:
            return {"available": False, "error": f"串口 {device} 不存在"}

        # 尝试打开串口
        try:
            ser = serial.Serial(port=device, baudrate=9600, timeout=0.1)
            ser.close()
            return {
                "available": True,
                "device": device,
                "description": port_info.description,
                "hwid": port_info.hwid,
                "error": None,
            }
        except serial.SerialException as e:
            return {"available": False, "device": device, "error": f"无法打开串口：{str(e)}"}

    except Exception as e:
        return {"available": False, "error": f"检查失败：{str(e)}"}
