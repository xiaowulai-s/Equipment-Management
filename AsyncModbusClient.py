# -*- coding: utf-8 -*-
"""
工业设备管理系统 - 异步Modbus通信模块
使用Python asyncio实现异步Modbus TCP通信
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import threading

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
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


class AsyncModbusClient:
    """
    异步Modbus TCP客户端封装
    使用asyncio实现异步通信
    """

    def __init__(self, host: str, port: int = 502, slave_id: int = 1):
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.status = ConnectionStatus.DISCONNECTED
        self._client: Optional[AsyncModbusTcpClient] = None
        self._lock = threading.Lock()
        self._is_running = False
        self._reconnect_interval = 5  # 重连间隔(秒)
        self._read_attempts = 0
        self._max_read_attempts = 3
        self._disconnect_event = asyncio.Event()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._max_registers_per_request = 125  # Modbus协议限制单次最多读取125个寄存器

    async def connect(self) -> bool:
        """异步连接到Modbus服务器"""
        async with self._lock:
            try:
                # 关闭现有连接
                if self._client:
                    await self._client.close()
                    self._client = None

                logger.info(f"正在异步连接 {self.host}:{self.port}...")
                self.status = ConnectionStatus.CONNECTING

                # 创建异步Modbus客户端
                self._client = AsyncModbusTcpClient(
                    host=self.host,
                    port=self.port,
                    framer=FramerType.TCP,
                    timeout=3,
                    retries=2,
                    retry_on_empty=True
                )

                # 尝试连接
                if await self._client.connect():
                    self.status = ConnectionStatus.CONNECTED
                    self._read_attempts = 0
                    self._disconnect_event.clear()
                    logger.info(f"已异步连接到 {self.host}:{self.port}")
                    
                    # 启动自动重连任务
                    self._reconnect_task = asyncio.create_task(self._auto_reconnect())
                    
                    return True
                else:
                    self.status = ConnectionStatus.ERROR
                    logger.error(f"异步连接失败: 无法建立连接到 {self.host}:{self.port}")
                    return False

            except Exception as e:
                logger.error(f"异步连接失败: {e}")
                self.status = ConnectionStatus.ERROR
                return False

    async def disconnect(self):
        """异步断开连接"""
        async with self._lock:
            try:
                self._disconnect_event.set()
                
                if self._reconnect_task:
                    self._reconnect_task.cancel()
                    self._reconnect_task = None

                if self._client:
                    await self._client.close()
                    self._client = None
                
                self.status = ConnectionStatus.DISCONNECTED
                logger.info(f"已异步断开连接 {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"异步断开连接失败: {e}")

    async def read_holding_registers(self, address: int, count: int = 1) -> Optional[List[int]]:
        """异步读取保持寄存器 (Function Code 03)"""
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取寄存器
                result = await self._client.read_holding_registers(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"异步读取保持寄存器失败: {result}")
                    await self._handle_error()
                    return None

                # 提取数据
                values = result.registers
                logger.debug(f"异步读取保持寄存器成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return None
            except Exception as e:
                logger.error(f"异步读取寄存器失败: {e}")
                await self._handle_error()
                return None

    async def read_input_registers(self, address: int, count: int = 1) -> Optional[List[int]]:
        """异步读取输入寄存器 (Function Code 04)"""
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取寄存器
                result = await self._client.read_input_registers(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"异步读取输入寄存器失败: {result}")
                    await self._handle_error()
                    return None

                # 提取数据
                values = result.registers
                logger.debug(f"异步读取输入寄存器成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return None
            except Exception as e:
                logger.error(f"异步读取寄存器失败: {e}")
                await self._handle_error()
                return None

    async def write_single_register(self, address: int, value: int) -> bool:
        """异步写入单个寄存器 (Function Code 06)"""
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return False

            try:
                # 写入寄存器
                result = await self._client.write_register(address=address, value=value, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"异步写入寄存器失败: {result}")
                    await self._handle_error()
                    return False

                logger.info(f"异步写入寄存器成功: 地址={address}, 值={value}")
                return True

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return False
            except Exception as e:
                logger.error(f"异步写入寄存器失败: {e}")
                await self._handle_error()
                return False

    async def write_coil(self, address: int, value: bool) -> bool:
        """异步写入线圈 (Function Code 05)"""
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return False

            try:
                # 写入线圈
                result = await self._client.write_coil(address=address, value=value, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"异步写入线圈失败: {result}")
                    await self._handle_error()
                    return False

                logger.info(f"异步写入线圈成功: 地址={address}, 值={value}")
                return True

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return False
            except Exception as e:
                logger.error(f"异步写入线圈失败: {e}")
                await self._handle_error()
                return False

    async def read_coils(self, address: int, count: int = 1) -> Optional[List[bool]]:
        """异步读取线圈 (Function Code 01)"""
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取线圈
                result = await self._client.read_coils(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"异步读取线圈失败: {result}")
                    await self._handle_error()
                    return None

                # 提取数据
                values = result.bits
                logger.debug(f"异步读取线圈成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return None
            except Exception as e:
                logger.error(f"异步读取线圈失败: {e}")
                await self._handle_error()
                return None

    async def read_discrete_inputs(self, address: int, count: int = 1) -> Optional[List[bool]]:
        """异步读取离散输入 (Function Code 02)"""
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            try:
                # 读取离散输入
                result = await self._client.read_discrete_inputs(address=address, count=count, slave=self.slave_id)

                # 检查结果
                if result.isError():
                    logger.error(f"异步读取离散输入失败: {result}")
                    await self._handle_error()
                    return None

                # 提取数据
                values = result.bits
                logger.debug(f"异步读取离散输入成功: 地址={address}, 数量={count}, 值={values}")
                return values

            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return None
            except Exception as e:
                logger.error(f"异步读取离散输入失败: {e}")
                await self._handle_error()
                return None

    async def batch_read_holding_registers(self, addresses: List[int]) -> Optional[Dict[int, int]]:
        """
        批量读取保持寄存器，自动合并连续地址
        
        Args:
            addresses: 要读取的寄存器地址列表
            
        Returns:
            Dict[int, int]: 地址到值的映射字典，如果失败返回None
        """
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            if not addresses:
                return {}

            try:
                # 排序地址并合并连续地址
                sorted_addresses = sorted(addresses)
                address_ranges = []
                
                # 合并连续地址范围
                start = sorted_addresses[0]
                end = start
                
                for addr in sorted_addresses[1:]:
                    if addr == end + 1:
                        end = addr
                    else:
                        address_ranges.append((start, end - start + 1))
                        start = addr
                        end = addr
                address_ranges.append((start, end - start + 1))
                
                # 处理超出最大寄存器数限制的情况
                final_ranges = []
                for start_addr, count in address_ranges:
                    while count > self._max_registers_per_request:
                        final_ranges.append((start_addr, self._max_registers_per_request))
                        start_addr += self._max_registers_per_request
                        count -= self._max_registers_per_request
                    if count > 0:
                        final_ranges.append((start_addr, count))
                
                result_dict = {}
                
                # 执行批量读取
                for start_addr, count in final_ranges:
                    result = await self._client.read_holding_registers(
                        address=start_addr, count=count, slave=self.slave_id
                    )
                    
                    if result.isError():
                        logger.error(f"批量读取保持寄存器失败: {result}")
                        await self._handle_error()
                        return None
                    
                    # 将结果映射回原始地址
                    values = result.registers
                    for i in range(count):
                        addr = start_addr + i
                        if addr in addresses:
                            result_dict[addr] = values[i]
                    
                    logger.debug(f"批量读取保持寄存器成功: 地址={start_addr}, 数量={count}, 值={values}")
                
                return result_dict
                
            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return None
            except Exception as e:
                logger.error(f"批量读取保持寄存器失败: {e}")
                await self._handle_error()
                return None

    async def batch_read_input_registers(self, addresses: List[int]) -> Optional[Dict[int, int]]:
        """
        批量读取输入寄存器，自动合并连续地址
        
        Args:
            addresses: 要读取的寄存器地址列表
            
        Returns:
            Dict[int, int]: 地址到值的映射字典，如果失败返回None
        """
        async with self._lock:
            if self.status != ConnectionStatus.CONNECTED or not self._client:
                return None

            if not addresses:
                return {}

            try:
                # 排序地址并合并连续地址
                sorted_addresses = sorted(addresses)
                address_ranges = []
                
                # 合并连续地址范围
                start = sorted_addresses[0]
                end = start
                
                for addr in sorted_addresses[1:]:
                    if addr == end + 1:
                        end = addr
                    else:
                        address_ranges.append((start, end - start + 1))
                        start = addr
                        end = addr
                address_ranges.append((start, end - start + 1))
                
                # 处理超出最大寄存器数限制的情况
                final_ranges = []
                for start_addr, count in address_ranges:
                    while count > self._max_registers_per_request:
                        final_ranges.append((start_addr, self._max_registers_per_request))
                        start_addr += self._max_registers_per_request
                        count -= self._max_registers_per_request
                    if count > 0:
                        final_ranges.append((start_addr, count))
                
                result_dict = {}
                
                # 执行批量读取
                for start_addr, count in final_ranges:
                    result = await self._client.read_input_registers(
                        address=start_addr, count=count, slave=self.slave_id
                    )
                    
                    if result.isError():
                        logger.error(f"批量读取输入寄存器失败: {result}")
                        await self._handle_error()
                        return None
                    
                    # 将结果映射回原始地址
                    values = result.registers
                    for i in range(count):
                        addr = start_addr + i
                        if addr in addresses:
                            result_dict[addr] = values[i]
                    
                    logger.debug(f"批量读取输入寄存器成功: 地址={start_addr}, 数量={count}, 值={values}")
                
                return result_dict
                
            except ModbusException as e:
                logger.error(f"Modbus异常: {e}")
                await self._handle_error()
                return None
            except Exception as e:
                logger.error(f"批量读取输入寄存器失败: {e}")
                await self._handle_error()
                return None

    async def is_connected(self) -> bool:
        """异步检查连接状态"""
        async with self._lock:
            if self._client and self.status == ConnectionStatus.CONNECTED:
                # 尝试发送一个简单的请求来验证连接
                try:
                    # 读取一个不存在的寄存器，只是为了测试连接
                    await self._client.read_holding_registers(address=0, count=1, slave=self.slave_id)
                    return True
                except:
                    self.status = ConnectionStatus.DISCONNECTED
                    return False
            return False

    async def _handle_error(self):
        """处理错误并尝试重连"""
        self._read_attempts += 1
        
        if self._read_attempts >= self._max_read_attempts:
            logger.warning(f"连续 {self._max_read_attempts} 次异步读取失败，尝试重连...")
            self.status = ConnectionStatus.DISCONNECTED

    async def _auto_reconnect(self):
        """自动重连任务"""
        while not self._disconnect_event.is_set():
            try:
                # 检查连接状态
                if self.status != ConnectionStatus.CONNECTED and self._client:
                    logger.info(f"检测到连接断开，尝试自动重连到 {self.host}:{self.port}...")
                    if await self._client.connect():
                        self.status = ConnectionStatus.CONNECTED
                        self._read_attempts = 0
                        logger.info(f"自动重连成功: {self.host}:{self.port}")
                    else:
                        logger.error(f"自动重连失败: {self.host}:{self.port}")
                        await asyncio.sleep(self._reconnect_interval)
                else:
                    await asyncio.sleep(1)  # 每秒检查一次
            except Exception as e:
                logger.error(f"自动重连任务错误: {e}")
                await asyncio.sleep(self._reconnect_interval)

    async def batch_read_registers(self, registers: List[Dict[str, Any]]) -> Dict[int, int]:
        """异步批量读取寄存器 - 智能分组和合并
        
        Args:
            registers: 寄存器列表，每个字典包含address和type字段
            
        Returns:
            Dict[int, int]: 寄存器地址到值的映射
        """
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
                    # 对地址进行排序并智能分组
                    sorted_addrs = sorted(addresses)
                    addr_groups = self._smart_group_registers(sorted_addrs)

                    # 批量读取每个地址组
                    for addr_group in addr_groups:
                        if not addr_group:
                            continue
                        
                        start_addr = addr_group[0]
                        count = addr_group[-1] - addr_group[0] + 1
                        
                        # 限制单次读取的寄存器数量
                        if count > self._max_registers_per_request:
                            # 拆分大的请求
                            sub_groups = self._split_large_group(addr_group, self._max_registers_per_request)
                            for sub_group in sub_groups:
                                await self._read_single_reg_group(
                                    reg_type, sub_group, results
                                )
                        else:
                            # 单次读取
                            await self._read_single_reg_group(
                                reg_type, addr_group, results
                            )

                elif reg_type in ["coil", "discrete_input"]:
                    # 线圈和离散输入的批量读取
                    sorted_addrs = sorted(addresses)
                    addr_groups = self._smart_group_registers(sorted_addrs, max_gap=10)

                    for addr_group in addr_groups:
                        if not addr_group:
                            continue
                        
                        start_addr = addr_group[0]
                        count = addr_group[-1] - addr_group[0] + 1
                        
                        if reg_type == "coil":
                            bits = await self.read_coils(start_addr, count)
                        else:
                            bits = await self.read_discrete_inputs(start_addr, count)

                        if bits:
                            for addr in addr_group:
                                if addr >= start_addr and addr < start_addr + len(bits):
                                    results[addr] = 1 if bits[addr - start_addr] else 0

        except Exception as e:
            logger.error(f"异步批量读取失败: {e}")

        return results

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

    async def _read_single_reg_group(self, reg_type: str, addresses: List[int], results: Dict[int, int]):
        """读取单个寄存器地址组
        
        Args:
            reg_type: 寄存器类型
            addresses: 寄存器地址列表
            results: 存储结果的字典
        """
        if not addresses:
            return
        
        start_addr = addresses[0]
        count = addresses[-1] - addresses[0] + 1
        
        try:
            if reg_type == "holding_register":
                values = await self.read_holding_registers(start_addr, count)
            else:
                values = await self.read_input_registers(start_addr, count)

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
                        values = await self.read_holding_registers(addr, 1)
                    else:
                        values = await self.read_input_registers(addr, 1)
                    
                    if values:
                        results[addr] = values[0]
                        
                except Exception as single_e:
                    logger.error(f"单个读取寄存器失败 [{reg_type}@{addr}]: {single_e}")

    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "host": self.host,
            "port": self.port,
            "slave_id": self.slave_id,
            "status": self.status.name,
            "read_attempts": self._read_attempts
        }


class AsyncDeviceManager:
    """
    异步设备管理器
    使用异步方式管理多个设备的连接和通信
    支持大规模设备并发处理
    """

    def __init__(self):
        self._clients: Dict[str, AsyncModbusClient] = {}  # 设备ID到异步客户端的映射
        self._device_map: Dict[str, Device] = {}  # 设备ID到设备对象的映射
        self._lock = threading.Lock()  # 线程锁
        self._loop: Optional[asyncio.AbstractEventLoop] = None  # 事件循环
        self._is_running = False  # 运行状态
        self._tasks: List[asyncio.Task] = []  # 异步任务列表
        self._update_interval = 0.1  # 更新间隔(秒)
        self._max_concurrent_connections = 100  # 最大并发连接数
        self._semaphore: Optional[asyncio.Semaphore] = None  # 信号量用于限制并发连接

    def add_device(self, device: Device) -> bool:
        """添加异步设备 - 使用设备对象"""
        with self._lock:
            try:
                client = AsyncModbusClient(
                    host=device.ip_address,
                    port=device.port,
                    slave_id=device.slave_id
                )
                self._clients[device.id] = client
                self._device_map[device.id] = device
                logger.info(f"已添加异步设备: {device.id} ({device.ip_address}:{device.port})")
                return True
            except Exception as e:
                logger.error(f"添加异步设备失败: {e}")
                return False

    def remove_device(self, device_id: str) -> bool:
        """移除异步设备"""
        with self._lock:
            if device_id in self._clients:
                # 异步断开连接
                client = self._clients[device_id]
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(client.disconnect(), self._loop)
                del self._clients[device_id]
                
            if device_id in self._device_map:
                del self._device_map[device_id]
                
            logger.info(f"已移除异步设备: {device_id}")
            return True
        return False

    async def start(self) -> bool:
        """启动异步设备管理器"""
        if self._is_running:
            return True
            
        try:
            self._loop = asyncio.get_running_loop()
            self._semaphore = asyncio.Semaphore(self._max_concurrent_connections)
            self._is_running = True
            
            # 启动设备管理任务
            self._tasks.append(asyncio.create_task(self._device_management_task()))
            logger.info(f"异步设备管理器已启动，支持最大 {self._max_concurrent_connections} 个并发连接")
            return True
            
        except Exception as e:
            logger.error(f"启动异步设备管理器失败: {e}")
            self._is_running = False
            return False

    async def stop(self) -> bool:
        """停止异步设备管理器"""
        if not self._is_running:
            return True
            
        try:
            self._is_running = False
            
            # 取消所有任务
            for task in self._tasks:
                task.cancel()
            
            # 等待任务完成
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
            
            # 断开所有设备连接
            await self.disconnect_all()
            
            logger.info("异步设备管理器已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止异步设备管理器失败: {e}")
            return False

    async def _device_management_task(self):
        """设备管理任务 - 定期检查设备状态"""
        while self._is_running:
            try:
                # 检查所有设备连接状态
                for device_id, client in self._clients.items():
                    if client.status != ConnectionStatus.CONNECTED:
                        logger.debug(f"设备 {device_id} 连接状态异常: {client.status.name}")
                        
                # 等待下一次更新
                await asyncio.sleep(self._update_interval)
                
            except Exception as e:
                logger.error(f"设备管理任务错误: {e}")
                await asyncio.sleep(1)

    async def connect_device(self, device_id: str) -> bool:
        """异步连接设备"""
        with self._lock:
            if device_id in self._clients:
                return await self._clients[device_id].connect()
            return False

    async def connect_all(self) -> Dict[str, bool]:
        """异步连接所有设备"""
        results = {}
        
        # 创建所有连接任务
        tasks = []
        with self._lock:
            for device_id, client in self._clients.items():
                tasks.append((device_id, asyncio.create_task(client.connect())))

        # 等待所有任务完成
        for device_id, task in tasks:
            try:
                results[device_id] = await task
            except Exception as e:
                logger.error(f"连接设备 {device_id} 时出错: {e}")
                results[device_id] = False

        return results

    async def disconnect_all(self):
        """异步断开所有设备"""
        # 创建所有断开连接任务
        tasks = []
        with self._lock:
            for client in self._clients.values():
                tasks.append(asyncio.create_task(client.disconnect()))

        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)

    async def read_register(self, device_id: str, address: int, register_type: str = "holding_register") -> Optional[int]:
        """异步读取单个寄存器"""
        with self._lock:
            if device_id not in self._clients:
                return None

            client = self._clients[device_id]
            
            try:
                if register_type == "holding_register":
                    values = await client.read_holding_registers(address, 1)
                elif register_type == "input_register":
                    values = await client.read_input_registers(address, 1)
                elif register_type == "coil":
                    bits = await client.read_coils(address, 1)
                    values = [1 if bits[0] else 0] if bits else None
                elif register_type == "discrete_input":
                    bits = await client.read_discrete_inputs(address, 1)
                    values = [1 if bits[0] else 0] if bits else None
                else:
                    logger.error(f"未知的寄存器类型: {register_type}")
                    return None

                return values[0] if values else None

            except Exception as e:
                logger.error(f"异步读取寄存器失败: {e}")
                return None

    async def write_register(self, device_id: str, address: int, value: int, 
                           register_type: str = "holding_register") -> bool:
        """异步写入单个寄存器"""
        with self._lock:
            if device_id not in self._clients:
                return False

            client = self._clients[device_id]
            
            try:
                if register_type == "holding_register":
                    return await client.write_single_register(address, value)
                elif register_type == "coil":
                    return await client.write_coil(address, bool(value))
                else:
                    logger.error(f"不支持的写入类型: {register_type}")
                    return False

            except Exception as e:
                logger.error(f"异步写入寄存器失败: {e}")
                return False

    async def batch_read_registers(self, device_id: str, registers: List[Dict[str, Any]]) -> Dict[int, int]:
        """异步批量读取设备寄存器"""
        with self._lock:
            if device_id not in self._clients:
                return {}

            client = self._clients[device_id]
            return await client.batch_read_registers(registers)

    async def batch_read_all_devices(self, device_registers: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[int, int]]:
        """异步批量读取所有设备的寄存器
        
        Args:
            device_registers: 设备ID到寄存器列表的映射
            
        Returns:
            Dict[str, Dict[int, int]]: 设备ID到寄存器地址值映射的映射
        """
        results = {}
        
        # 创建所有批量读取任务
        tasks = []
        for device_id, registers in device_registers.items():
            if device_id in self._clients:
                client = self._clients[device_id]
                tasks.append((device_id, asyncio.create_task(client.batch_read_registers(registers))))

        # 等待所有任务完成
        for device_id, task in tasks:
            try:
                results[device_id] = await task
            except Exception as e:
                logger.error(f"批量读取设备 {device_id} 时出错: {e}")
                results[device_id] = {}

        return results

    async def get_device_status(self, device_id: str) -> str:
        """获取设备状态"""
        with self._lock:
            if device_id in self._clients:
                client = self._clients[device_id]
                return client.status.name
            return "NOT_FOUND"

    def get_all_devices(self) -> List[str]:
        """获取所有设备ID"""
        with self._lock:
            return list(self._clients.keys())

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """设置事件循环"""
        self._loop = loop


# 异步设备管理器实例
async_device_manager = AsyncDeviceManager()


async def example_usage():
    """异步Modbus客户端使用示例"""
    try:
        # 创建异步Modbus客户端
        client = AsyncModbusClient("192.168.1.101", 502, 1)

        # 连接到设备
        if await client.connect():
            # 读取保持寄存器
            values = await client.read_holding_registers(1, 5)
            print(f"读取保持寄存器: {values}")

            # 写入单个寄存器
            success = await client.write_single_register(100, 1)
            print(f"写入寄存器: {success}")

            # 读取线圈
            coils = await client.read_coils(100, 1)
            print(f"读取线圈: {coils}")

            # 断开连接
            await client.disconnect()

    except Exception as e:
        print(f"示例错误: {e}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
