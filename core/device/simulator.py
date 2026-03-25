# -*- coding: utf-8 -*-
"""
设备模拟器
Device Simulator
"""

import math
import random
import threading
import time
from typing import Any, Dict, List

from PySide6.QtCore import QObject, Signal


class Simulator(QObject):
    """
    设备模拟器
    Device Simulator
    """

    data_updated = Signal(dict)
    connected = Signal()
    disconnected = Signal()

    def __init__(self, device_config: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self._device_config = device_config or {}
        self._is_connected = False
        self._is_running = False
        self._simulation_thread = None
        self._register_values: Dict[int, int] = {}
        self._base_time = time.time()

        # 初始化模拟寄存器
        self._init_simulated_registers()

    def _init_simulated_registers(self):
        """
        初始化模拟寄存器
        Initialize simulated registers
        """
        # 温度寄存器（25°C基础值）
        self._register_values[0] = 250
        # 压力寄存器（1.0MPa基础值）
        self._register_values[1] = 100
        # 流量寄存器（50.0m³/h基础值）
        self._register_values[2] = 500
        # 设备状态寄存器
        self._register_values[3] = 1
        # 报警状态寄存器
        self._register_values[4] = 0

    def connect(self) -> bool:
        """
        连接模拟器
        Connect simulator
        """
        if self._is_connected:
            return True

        self._is_connected = True
        self._is_running = True
        self._base_time = time.time()

        # 启动模拟线程
        self._simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._simulation_thread.start()

        self.connected.emit()
        return True

    def disconnect(self):
        """
        断开模拟器
        Disconnect simulator
        """
        self._is_running = False
        self._is_connected = False

        if self._simulation_thread and self._simulation_thread.is_alive():
            self._simulation_thread.join(timeout=1.0)
            self._simulation_thread = None

        self.disconnected.emit()

    def is_connected(self) -> bool:
        """
        检查连接状态
        Check connection status
        """
        return self._is_connected

    def read_registers(self, address: int, count: int) -> List[int]:
        """
        读取模拟寄存器
        Read simulated registers
        """
        result = []
        for i in range(count):
            addr = address + i
            if addr in self._register_values:
                result.append(self._register_values[addr])
            else:
                result.append(0)
        return result

    def write_register(self, address: int, value: int) -> bool:
        """
        写入模拟寄存器
        Write simulated register
        """
        self._register_values[address] = value
        return True

    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        写入多个模拟寄存器
        Write multiple simulated registers
        """
        for i, value in enumerate(values):
            self._register_values[address + i] = value
        return True

    def _simulation_loop(self):
        """
        模拟循环
        Simulation loop
        """
        while self._is_running:
            current_time = time.time()
            elapsed = current_time - self._base_time

            # 生成模拟数据（带波动的真实感数据）
            self._update_temperature(elapsed)
            self._update_pressure(elapsed)
            self._update_flow(elapsed)

            # 准备数据字典
            data = {
                "temperature": {
                    "raw": self._register_values[0],
                    "value": self._register_values[0] * 0.1,
                    "address": 0,
                    "unit": "°C",
                },
                "pressure": {
                    "raw": self._register_values[1],
                    "value": self._register_values[1] * 0.1,
                    "address": 1,
                    "unit": "MPa",
                },
                "flow": {
                    "raw": self._register_values[2],
                    "value": self._register_values[2] * 0.1,
                    "address": 2,
                    "unit": "m³/h",
                },
                "status": {"raw": self._register_values[3], "value": self._register_values[3], "address": 3},
                "alarm": {"raw": self._register_values[4], "value": self._register_values[4], "address": 4},
            }

            # 发出数据更新信号
            self.data_updated.emit(data)

            # 等待100ms
            time.sleep(0.1)

    def _update_temperature(self, elapsed: float):
        """
        更新温度模拟
        Update temperature simulation
        """
        # 基础温度 25°C，带日周期波动 + 随机噪声
        base_temp = 250  # 25.0°C
        diurnal = 20 * math.sin(elapsed * 0.0001)  # 日周期波动
        random_noise = random.uniform(-5, 5)  # 随机噪声

        new_temp = int(base_temp + diurnal + random_noise)
        # 限制在合理范围内
        new_temp = max(0, min(500, new_temp))
        self._register_values[0] = new_temp

        # 检查是否超温报警
        if new_temp > 400:  # 40°C
            self._register_values[4] |= 0x01
        else:
            self._register_values[4] &= ~0x01

    def _update_pressure(self, elapsed: float):
        """
        更新压力模拟
        Update pressure simulation
        """
        # 基础压力 1.0MPa，带缓慢波动
        base_pressure = 100  # 1.0MPa
        # 缓慢波动
        slow_wave = 10 * math.sin(elapsed * 0.001)
        # 快速波动
        fast_wave = 5 * math.sin(elapsed * 0.01)

        new_pressure = int(base_pressure + slow_wave + fast_wave)
        new_pressure = max(50, min(150, new_pressure))  # 0.5-1.5MPa
        self._register_values[1] = new_pressure

        # 检查压力报警
        if new_pressure > 120:  # 1.2MPa
            self._register_values[4] |= 0x02
        else:
            self._register_values[4] &= ~0x02

    def _update_flow(self, elapsed: float):
        """
        更新流量模拟
        Update flow simulation
        """
        # 基础流量 50.0m³/h，带与压力相关的波动
        base_flow = 500  # 50.0 m³/h
        pressure_factor = (self._register_values[1] - 100) * 0.5
        random_noise = random.uniform(-10, 10)

        new_flow = int(base_flow + pressure_factor + random_noise)
        new_flow = max(0, min(1000, new_flow))  # 0-100 m³/h
        self._register_values[2] = new_flow
