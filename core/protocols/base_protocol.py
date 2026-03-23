# -*- coding: utf-8 -*-
"""
协议基类
Base Protocol
"""

from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal
from ..communication.base_driver import BaseDriver


class BaseProtocol(QObject):
    """
    协议基类
    Base class for protocols
    """

    # 信号定义
    data_updated = Signal(dict)  # 数据更新信号
    command_sent = Signal(bytes)  # 命令发送信号
    response_received = Signal(bytes)  # 响应接收信号
    error_occurred = Signal(str)  # 错误发生信号

    def __init__(self, driver: Optional[BaseDriver] = None, parent=None):
        super().__init__(parent)
        self._driver = driver
        self._device_config: Dict[str, Any] = {}
        self._register_map: List[Dict[str, Any]] = []

    def set_driver(self, driver: BaseDriver):
        """
        设置通信驱动
        Set communication driver
        """
        self._driver = driver

    def set_device_config(self, config: Dict[str, Any]):
        """
        设置设备配置
        Set device configuration
        """
        self._device_config = config

    def set_register_map(self, register_map: List[Dict[str, Any]]):
        """
        设置寄存器映射
        Set register map
        """
        self._register_map = register_map

    def initialize(self) -> bool:
        """
        初始化协议
        Initialize protocol
        """
        raise NotImplementedError("子类必须实现initialize方法")

    def read_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        读取寄存器
        Read registers
        """
        raise NotImplementedError("子类必须实现read_registers方法")

    def write_register(self, address: int, value: int) -> bool:
        """
        写入单个寄存器
        Write single register
        """
        raise NotImplementedError("子类必须实现write_register方法")

    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        写入多个寄存器
        Write multiple registers
        """
        raise NotImplementedError("子类必须实现write_registers方法")

    def poll_data(self) -> Dict[str, Any]:
        """
        轮询数据
        Poll data from device
        """
        raise NotImplementedError("子类必须实现poll_data方法")

    def get_protocol_name(self) -> str:
        """
        获取协议名称
        Get protocol name
        """
        return self.__class__.__name__
