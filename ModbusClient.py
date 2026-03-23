# -*- coding: utf-8 -*-
"""
工业设备管理系统 - Modbus通信模块
实现Modbus TCP客户端和模拟数据生成器
"""

import time
import random
import logging
from typing import Optional, Dict, Callable, List, Any
from datetime import datetime
from enum import Enum
import threading
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
from pymodbus import FramerType

# 使用统一日志配置
from logging_config import get_logger
logger = get_logger(__name__)


class ConnectionStatus(Enum):
    """连接状态"""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ERROR = 3


class ModbusClient:
    """Modbus TCP客户端封装 - 使用真实的pymodbus库"""

    def __init__(self, host: str, port: int = 502, slave_id: int = 1):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.status = ConnectionStatus.DISCONNECTED
        self._client = None  # 真实的Modbus TCP客户端
        self._lock = threading.Lock()
        self._is_running = False
        self._reconnect_interval = 5  # 重连间隔(秒)
        self._last_error_time = 0
        self._read_attempts = 0
        self._max_read_attempts = 3

    def connect(self) -> bool:
        """连接到Modbus服务器"""
        with self._lock:
            try:
                # 关闭现有连接
                if self._client:
                    self._client.close()

                logger.info(f"正在连接 {self.host}:{self.port}...")
                self.status = ConnectionStatus.CONNECTING

                # 创建并连接Modbus客户端
                self._client = ModbusTcpClient(
                    host=self.host,
                    port=self.port,
                    framer=FramerType.TCP,
                    timeout=3,
                    retries=2,
                    retry_on_empty=True
                )

                # 尝试连接
                if self._client.connect():
                    self.status = ConnectionStatus.CONNECTED
                    self._read_attempts = 0
                    logger.info(f"已连接到 {self.host}:{self.port}")
                    return True
                else:
                    self.status = ConnectionStatus.ERROR
                    logger.error(f"连接失败: 无法建立连接到 {self.host}:{self.port}")
                    return False

            except Exception as e:
                logger.error(f"连接失败: {e}")
                self.status = ConnectionStatus.ERROR
                return False

    def disconnect(self):
        """断开连接"""
        with self._lock:
            try:
                if self._client:
                    self._client.close()
                    self._client = None
                self.status = ConnectionStatus.DISCONNECTED
                logger.info(f"已断开连接 {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"断开连接失败: {e}")

    def read_holding_registers(self, address: int, count: int = 1) -> Optional[List[int]]:
        """读取保持寄存器 (Function Code 03)"""
        with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取寄存器
                result = self._client.read_holding_registers(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"读取保持寄存器失败: {result}")
                    self._handle_error()
                    return None

                # 提取数据
                values = result.registers
                logger.debug(f"读取保持寄存器成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                self._handle_error()
                return None
            except Exception as e:
                logger.error(f"读取寄存器失败: {e}")
                self._handle_error()
                return None

    def read_input_registers(self, address: int, count: int = 1) -> Optional[List[int]]:
        """读取输入寄存器 (Function Code 04)"""
        with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取寄存器
                result = self._client.read_input_registers(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"读取输入寄存器失败: {result}")
                    self._handle_error()
                    return None

                # 提取数据
                values = result.registers
                logger.debug(f"读取输入寄存器成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                self._handle_error()
                return None
            except Exception as e:
                logger.error(f"读取寄存器失败: {e}")
                self._handle_error()
                return None

    def write_single_register(self, address: int, value: int) -> bool:
        """写入单个寄存器 (Function Code 06)"""
        with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return False

            try:
                # 写入寄存器
                result = self._client.write_register(address=address, value=value, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"写入寄存器失败: {result}")
                    self._handle_error()
                    return False

                logger.info(f"写入寄存器成功: 地址={address}, 值={value}")
                return True

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                self._handle_error()
                return False
            except Exception as e:
                logger.error(f"写入寄存器失败: {e}")
                self._handle_error()
                return False

    def write_coil(self, address: int, value: bool) -> bool:
        """写入线圈 (Function Code 05)"""
        with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return False

            try:
                # 写入线圈
                result = self._client.write_coil(address=address, value=value, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"写入线圈失败: {result}")
                    self._handle_error()
                    return False

                logger.info(f"写入线圈成功: 地址={address}, 值={value}")
                return True

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                self._handle_error()
                return False
            except Exception as e:
                logger.error(f"写入线圈失败: {e}")
                self._handle_error()
                return False

    def read_coils(self, address: int, count: int = 1) -> Optional[List[bool]]:
        """读取线圈 (Function Code 01)"""
        with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取线圈
                result = self._client.read_coils(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"读取线圈失败: {result}")
                    self._handle_error()
                    return None

                # 提取数据
                values = result.bits
                logger.debug(f"读取线圈成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                self._handle_error()
                return None
            except Exception as e:
                logger.error(f"读取线圈失败: {e}")
                self._handle_error()
                return None

    def read_discrete_inputs(self, address: int, count: int = 1) -> Optional[List[bool]]:
        """读取离散输入 (Function Code 02)"""
        with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取离散输入
                result = self._client.read_discrete_inputs(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"读取离散输入失败: {result}")
                    self._handle_error()
                    return None

                # 提取数据
                values = result.bits
                logger.debug(f"读取离散输入成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                self._handle_error()
                return None
            except Exception as e:
                logger.error(f"读取离散输入失败: {e}")
                self._handle_error()
                return None

    def is_connected(self) -> bool:
        """检查连接状态"""
        with self._lock:
            if self._client:
                # 检查连接状态
                if self.status == ConnectionStatus.CONNECTED:
                    # 尝试发送一个简单的请求来验证连接
                    try:
                        # 读取一个不存在的寄存器，只是为了测试连接
                        self._client.read_holding_registers(address=0, count=1, slave=self.slave_id)
                        return True
                    except:
                        self.status = ConnectionStatus.DISCONNECTED
                        return False
            return False

    def _handle_error(self):
        """处理错误并尝试重连"""
        self._read_attempts += 1
        
        if self._read_attempts >= self._max_read_attempts:
            logger.warning(f"连续 {self._max_read_attempts} 次读取失败，尝试重连...")
            self.status = ConnectionStatus.DISCONNECTED
            # 异步重连
            threading.Thread(target=self._reconnect, daemon=True).start()

    def _reconnect(self):
        """尝试重连"""
        time.sleep(self._reconnect_interval)
        logger.info(f"尝试重新连接到 {self.host}:{self.port}...")
        self.connect()

    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "host": self.host,
            "port": self.port,
            "slave_id": self.slave_id,
            "status": self.status.name,
            "is_connected": self.is_connected(),
            "read_attempts": self._read_attempts
        }


class DataSimulator:
    """数据模拟器 - 生成模拟设备数据"""

    def __init__(self):
        self._is_running = False
        self._thread = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []
        self._interval = 2.0  # 更新间隔(秒)

        # 模拟数据状态
        self._temperature = 25.0
        self._pressure = 1.2
        self._flow_rate = 50.0
        self._power = 15.0
        self._frequency = 50.0
        self._efficiency = 95.0

    def start(self):
        """启动模拟器"""
        with self._lock:
            if self._is_running:
                return

            self._is_running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logger.info("数据模拟器已启动")

    def stop(self):
        """停止模拟器"""
        with self._lock:
            self._is_running = False
            if self._thread:
                self._thread.join(timeout=2)
            logger.info("数据模拟器已停止")

    def register_callback(self, callback: Callable):
        """注册数据更新回调"""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """取消注册回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _run(self):
        """运行模拟循环"""
        while self._is_running:
            try:
                # 更新模拟数据
                self._update_simulation_data()

                # 获取当前数据
                data = self.get_current_data()

                # 调用所有回调
                for callback in self._callbacks:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"回调执行失败: {e}")

                time.sleep(self._interval)

            except Exception as e:
                logger.error(f"模拟循环异常: {e}")
                time.sleep(1)

    def _update_simulation_data(self):
        """更新模拟数据"""
        # 温度: 20-35°C
        self._temperature += (random.random() - 0.5) * 0.5
        self._temperature = max(20.0, min(35.0, self._temperature))

        # 压力: 0.8-2.0 MPa
        self._pressure += (random.random() - 0.5) * 0.05
        self._pressure = max(0.8, min(2.0, self._pressure))

        # 流量: 40-60 m³/h
        self._flow_rate += (random.random() - 0.5) * 2.0
        self._flow_rate = max(40.0, min(60.0, self._flow_rate))

        # 功率: 10-20 kW
        self._power += (random.random() - 0.5) * 0.5
        self._power = max(10.0, min(20.0, self._power))

        # 频率: 49-51 Hz
        self._frequency += (random.random() - 0.5) * 0.2
        self._frequency = max(49.0, min(51.0, self._frequency))

        # 效率: 90-98%
        self._efficiency += (random.random() - 0.5) * 0.3
        self._efficiency = max(90.0, min(98.0, self._efficiency))

    def get_current_data(self) -> Dict:
        """获取当前模拟数据"""
        return {
            "temperature": round(self._temperature, 1),
            "pressure": round(self._pressure, 2),
            "flow_rate": round(self._flow_rate, 1),
            "power": round(self._power, 1),
            "frequency": round(self._frequency, 1),
            "efficiency": round(self._efficiency, 1),
            "timestamp": datetime.now().isoformat()
        }

    def get_register_values(self, address: int) -> Optional[int]:
        """获取指定寄存器的模拟值"""
        # 模拟寄存器映射
        register_map = {
            0x0001: int(self._temperature * 10),  # 温度 * 10
            0x0002: int(self._pressure * 100),   # 压力 * 100
            0x0003: int(self._flow_rate * 10),    # 流量 * 10
            0x0004: int(self._power * 10),       # 功率 * 10
            0x0005: int(self._frequency * 10),   # 频率 * 10
            0x0006: int(self._efficiency * 10),  # 效率 * 10
            0x0007: int(self._pressure * 100 * 0.7),  # 入口压力
            0x0008: int(self._pressure * 100),   # 出口压力
        }
        return register_map.get(address)


class DeviceMonitor:
    """设备监控器 - 管理设备连接和数据采集"""

    def __init__(self):
        self._clients: Dict[str, ModbusClient] = {}
        self._simulator = DataSimulator()
        self._is_running = False
        self._lock = threading.Lock()
        self._data_callbacks: List[Callable] = []
        self._simulation_callbacks: List[Callable] = []
        self._batch_read_enabled = True
        self._max_registers_per_request = 125
        self._address_grouping_enabled = True
        self._max_address_gap = 10

    def add_device(self, device_id: str, host: str, port: int = 502, slave_id: int = 1) -> bool:
        """添加设备"""
        with self._lock:
            try:
                client = ModbusClient(host, port, slave_id)
                self._clients[device_id] = client
                logger.info(f"已添加设备: {device_id} ({host}:{port})")
                return True
            except Exception as e:
                logger.error(f"添加设备失败: {e}")
                return False

    def remove_device(self, device_id: str):
        """移除设备"""
        with self._lock:
            if device_id in self._clients:
                client = self._clients[device_id]
                client.disconnect()
                del self._clients[device_id]
                logger.info(f"已移除设备: {device_id}")

    def connect_device(self, device_id: str) -> bool:
        """连接设备"""
        with self._lock:
            if device_id in self._clients:
                return self._clients[device_id].connect()
            return False

    def connect_all(self) -> Dict[str, bool]:
        """连接所有设备"""
        results = {}
        with self._lock:
            for device_id, client in self._clients.items():
                results[device_id] = client.connect()
        return results

    def disconnect_all(self):
        """断开所有设备"""
        with self._lock:
            for client in self._clients.values():
                client.disconnect()

    def read_registers(self, device_id: str, address: int, count: int = 1, 
                      register_type: str = "holding_register") -> Optional[List[int]]:
        """读取设备寄存器"""
        with self._lock:
            if device_id not in self._clients:
                return None

            client = self._clients[device_id]
            
            try:
                if register_type == "holding_register":
                    return client.read_holding_registers(address, count)
                elif register_type == "input_register":
                    return client.read_input_registers(address, count)
                elif register_type == "coil":
                    bits = client.read_coils(address, count)
                    return [1 if bit else 0 for bit in bits] if bits else None
                elif register_type == "discrete_input":
                    bits = client.read_discrete_inputs(address, count)
                    return [1 if bit else 0 for bit in bits] if bits else None
                else:
                    logger.error(f"未知的寄存器类型: {register_type}")
                    return None
            except Exception as e:
                logger.error(f"读取寄存器失败: {e}")
                return None

    def write_register(self, device_id: str, address: int, value: int, 
                      register_type: str = "holding_register") -> bool:
        """写入设备寄存器"""
        with self._lock:
            if device_id not in self._clients:
                return False

            client = self._clients[device_id]
            
            try:
                if register_type == "holding_register":
                    return client.write_single_register(address, value)
                elif register_type == "coil":
                    return client.write_coil(address, bool(value))
                else:
                    logger.error(f"不支持的写入类型: {register_type}")
                    return False
            except Exception as e:
                logger.error(f"写入寄存器失败: {e}")
                return False

    def batch_read_registers(self, device_id: str, registers: List[Dict]) -> Dict[int, int]:
        """批量读取寄存器
        
        Args:
            device_id: 设备ID
            registers: 寄存器列表，每个字典包含address和type字段
            
        Returns:
            Dict[int, int]: 寄存器地址到值的映射
        """
        if not self._batch_read_enabled:
            # 单条读取
            results = {}
            for reg in registers:
                values = self.read_registers(
                    device_id, 
                    reg["address"], 
                    1, 
                    reg["type"]
                )
                if values:
                    results[reg["address"]] = values[0]
            return results

        with self._lock:
            if device_id not in self._clients:
                return {}

            client = self._clients[device_id]
            results = {}

            try:
                # 按寄存器类型分组
                reg_groups = {}
                for reg in registers:
                    reg_type = reg["type"]
                    if reg_type not in reg_groups:
                        reg_groups[reg_type] = []
                    reg_groups[reg_type].append(reg["address"])

                # 对每种寄存器类型进行批量读取
                for reg_type, addresses in reg_groups.items():
                    if reg_type in ["holding_register", "input_register"]:
                        # 对地址进行排序并分组
                        sorted_addrs = sorted(addresses)
                        addr_groups = self._group_registers(sorted_addrs)

                        # 批量读取每个地址组
                        for addr_group in addr_groups:
                            if not addr_group:
                                continue
                            
                            start_addr = addr_group[0]
                            count = max(addr_group) - start_addr + 1
                            count = min(count, self._max_registers_per_request)

                            if reg_type == "holding_register":
                                values = client.read_holding_registers(start_addr, count)
                            else:
                                values = client.read_input_registers(start_addr, count)

                            if values:
                                for i, addr in enumerate(addr_group):
                                    if addr >= start_addr and addr < start_addr + len(values):
                                        results[addr] = values[addr - start_addr]

                    elif reg_type in ["coil", "discrete_input"]:
                        # 线圈和离散输入的批量读取
                        sorted_addrs = sorted(addresses)
                        addr_groups = self._group_registers(sorted_addrs)

                        for addr_group in addr_groups:
                            if not addr_group:
                                continue
                            
                            start_addr = addr_group[0]
                            count = max(addr_group) - start_addr + 1
                            count = min(count, self._max_registers_per_request)

                            if reg_type == "coil":
                                bits = client.read_coils(start_addr, count)
                            else:
                                bits = client.read_discrete_inputs(start_addr, count)

                            if bits:
                                for i, addr in enumerate(addr_group):
                                    if addr >= start_addr and addr < start_addr + len(bits):
                                        results[addr] = 1 if bits[addr - start_addr] else 0

            except Exception as e:
                logger.error(f"批量读取失败: {e}")

            return results

    def _group_registers(self, addresses: List[int]) -> List[List[int]]:
        """将连续的寄存器地址分组"""
        return self._smart_group_registers(addresses)

    def _smart_group_registers(self, addresses: List[int], max_gap: int = 5) -> List[List[int]]:
        """智能分组寄存器地址
        
        将连续或接近连续的寄存器地址分组，减少通信次数
        
        Args:
            addresses: 寄存器地址列表
            max_gap: 最大地址间隔
            
        Returns:
            List[List[int]]: 分组后的地址列表
        """
        if not addresses:
            return []

        sorted_addrs = sorted(addresses)
        groups = [[sorted_addrs[0]]]
        
        for addr in sorted_addrs[1:]:
            last_group = groups[-1]
            if addr - last_group[-1] <= max_gap:
                # 添加到当前组
                last_group.append(addr)
            else:
                # 开始新组
                groups.append([addr])
        
        return groups

    def _split_large_group(self, addresses: List[int], max_size: int) -> List[List[int]]:
        """拆分大的地址组
        
        Args:
            addresses: 寄存器地址列表
            max_size: 最大组大小
            
        Returns:
            List[List[int]]: 拆分后的地址列表
        """
        return [addresses[i:i + max_size] for i in range(0, len(addresses), max_size)]

    def _read_single_reg_group(self, client, reg_type: str, addresses: List[int], results: Dict[int, int]):
        """读取单个寄存器地址组
        
        Args:
            client: Modbus客户端
            reg_type: 寄存器类型
            addresses: 寄存器地址列表
            results: 存储结果的字典
        """
        if not addresses:
            return
        
        start_addr = addresses[0]
        count = addresses[-1] - start_addr + 1
        
        try:
            if reg_type == "holding_register":
                values = client.read_holding_registers(start_addr, count)
            else:
                values = client.read_input_registers(start_addr, count)

            if values:
                for addr in addresses:
                    if addr >= start_addr and addr < start_addr + len(values):
                        results[addr] = values[addr - start_addr]
                        
        except Exception as e:
            logger.error(f"读取寄存器组失败 [{reg_type}@{start_addr}:{count}]: {e}")
            # 尝试单个读取
            for addr in addresses:
                try:
                    if reg_type == "holding_register":
                        values = client.read_holding_registers(addr, 1)
                    else:
                        values = client.read_input_registers(addr, 1)
                    
                    if values:
                        results[addr] = values[0]
                        
                except Exception as single_e:
                    logger.error(f"单个读取寄存器失败 [{reg_type}@{addr}]: {single_e}")

    def start_simulation(self):
        """启动数据模拟"""
        self._simulator.register_callback(self._on_simulation_data)
        self._simulator.start()
        self._is_running = True

    def stop_simulation(self):
        """停止数据模拟"""
        self._is_running = False
        self._simulator.unregister_callback(self._on_simulation_data)
        self._simulator.stop()

    def register_data_callback(self, callback: Callable):
        """注册数据回调"""
        self._data_callbacks.append(callback)

    def unregister_data_callback(self, callback: Callable):
        """取消注册数据回调"""
        if callback in self._data_callbacks:
            self._data_callbacks.remove(callback)

    def _on_simulation_data(self, data: Dict):
        """模拟数据回调"""
        for callback in self._data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"数据回调失败: {e}")

    def is_connected(self, device_id: str) -> bool:
        """检查设备连接状态"""
        with self._lock:
            if device_id in self._clients:
                return self._clients[device_id].is_connected()
            return False

    def get_connected_count(self) -> int:
        """获取已连接设备数"""
        with self._lock:
            return sum(1 for c in self._clients.values() if c.is_connected())

    def get_total_count(self) -> int:
        """获取设备总数"""
        with self._lock:
            return len(self._clients)

    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备信息"""
        with self._lock:
            if device_id in self._clients:
                client = self._clients[device_id]
                return {
                    "device_id": device_id,
                    **client.get_client_info(),
                    "is_connected": client.is_connected()
                }
            return None

    def get_all_devices_info(self) -> List[Dict[str, Any]]:
        """获取所有设备信息"""
        info_list = []
        with self._lock:
            for device_id, client in self._clients.items():
                info_list.append({
                    "device_id": device_id,
                    **client.get_client_info(),
                    "is_connected": client.is_connected()
                })
        return info_list

    def set_batch_read_settings(self, enabled: bool, max_registers: int = 125, 
                              grouping_enabled: bool = True, max_gap: int = 10):
        """设置批量读取参数"""
        with self._lock:
            self._batch_read_enabled = enabled
            self._max_registers_per_request = max_registers
            self._address_grouping_enabled = grouping_enabled
            self._max_address_gap = max_gap
            logger.info(f"批量读取设置已更新: enabled={enabled}, max_registers={max_registers}, \
                       grouping={grouping_enabled}, max_gap={max_gap}")
