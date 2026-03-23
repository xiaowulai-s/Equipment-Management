# -*- coding: utf-8 -*-
"""
工业设备管理系统 - 任务调度器
实现设备通信任务的优先级管理和调度
"""

import time
import heapq
import threading
import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from DeviceModels import Device, Register
from AsyncModbusClient import AsyncDeviceManager, AsyncModbusClient
from ModbusClient import DeviceMonitor

# 使用统一日志配置
from logging_config import get_logger
logger = get_logger(__name__)


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 0      # 低优先级 (如版本号、设备信息等)
    NORMAL = 1   # 正常优先级 (如常规状态监控)
    HIGH = 2     # 高优先级 (如实时压力、温度等)
    CRITICAL = 3 # 关键优先级 (如紧急报警、故障状态)


class TaskType(Enum):
    """任务类型枚举"""
    READ_REGISTER = 0      # 读取寄存器
    WRITE_REGISTER = 1     # 写入寄存器
    READ_COIL = 2          # 读取线圈
    WRITE_COIL = 3         # 写入线圈
    DEVICE_STATUS = 4      # 设备状态检查
    BATCH_READ = 5         # 批量读取
    CUSTOM = 6             # 自定义任务


class ScheduledTask:
    """调度任务数据模型"""
    
    def __init__(self,
                 device_id: str,
                 task_type: TaskType,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 interval: float = 1.0,  # 执行间隔(秒)
                 callback: Optional[Callable] = None,
                 args: Tuple = (),
                 kwargs: Dict[str, Any] = {},
                 register_addresses: Optional[List[int]] = None,
                 write_value: Optional[Any] = None,
                 task_id: Optional[str] = None):
        
        self.task_id = task_id or f"task_{datetime.now().timestamp()}"
        self.device_id = device_id
        self.task_type = task_type
        self.priority = priority
        self.interval = interval
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.register_addresses = register_addresses or []
        self.write_value = write_value
        
        self.last_executed = 0.0  # 上次执行时间戳
        self.next_execution = time.time() + interval  # 下次执行时间戳
        self.is_active = True      # 任务是否激活
        self.execution_count = 0   # 执行次数
        self.failure_count = 0     # 失败次数
        self.max_failures = 3      # 最大失败次数
        
    def __lt__(self, other):
        """优先级比较 - 用于优先队列"""
        if self.priority != other.priority:
            return self.priority.value > other.priority.value
        return self.next_execution < other.next_execution

    def should_execute(self) -> bool:
        """检查任务是否应该执行"""
        return self.is_active and time.time() >= self.next_execution

    def update_next_execution(self):
        """更新下次执行时间"""
        self.next_execution = time.time() + self.interval

    def mark_executed(self, success: bool = True):
        """标记任务已执行"""
        self.last_executed = time.time()
        self.execution_count += 1
        
        if not success:
            self.failure_count += 1
            if self.failure_count >= self.max_failures:
                logger.warning(f"任务 {self.task_id} 连续失败 {self.max_failures} 次，自动禁用")
                self.is_active = False
        else:
            self.failure_count = 0


class TaskScheduler:
    """
    任务调度器 - 管理设备通信任务的优先级和执行频率
    
    设计要点：
    1. 支持不同优先级的任务调度
    2. 智能合并相似任务，减少通信次数
    3. 防止Modbus队列阻塞
    4. 支持同步和异步执行模式
    """
    
    def __init__(self,
                 async_manager: Optional[AsyncDeviceManager] = None,
                 sync_manager: Optional[DeviceMonitor] = None):
        
        self._tasks: Dict[str, ScheduledTask] = {}  # 任务ID到任务的映射
        self._priority_queue = []  # 优先队列
        self._lock = threading.Lock()  # 线程锁
        self._is_running = False  # 运行状态
        self._thread: Optional[threading.Thread] = None  # 调度线程
        self._loop: Optional[asyncio.AbstractEventLoop] = None  # 异步事件循环
        
        # 设备管理器
        self._async_manager = async_manager
        self._sync_manager = sync_manager
        
        # 配置参数
        self._polling_interval = 0.1  # 轮询间隔(秒)
        self._max_concurrent_tasks = 10  # 最大并发任务数
        self._batch_threshold = 5  # 批量合并阈值
        
        # 任务统计
        self._stats = {
            "total_tasks": 0,
            "active_tasks": 0,
            "executed_tasks": 0,
            "failed_tasks": 0,
            "merged_tasks": 0
        }
        
        logger.info("任务调度器已初始化")
    
    def start(self) -> bool:
        """启动任务调度器"""
        if self._is_running:
            return True
            
        try:
            self._is_running = True
            
            # 启动调度线程
            self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._thread.start()
            
            logger.info("任务调度器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动任务调度器失败: {e}")
            self._is_running = False
            return False
    
    def stop(self) -> bool:
        """停止任务调度器"""
        if not self._is_running:
            return True
            
        try:
            self._is_running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
                
            logger.info("任务调度器已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止任务调度器失败: {e}")
            return False
    
    def add_task(self, task: ScheduledTask) -> bool:
        """添加调度任务"""
        with self._lock:
            if task.task_id in self._tasks:
                logger.warning(f"任务 {task.task_id} 已存在")
                return False
            
            self._tasks[task.task_id] = task
            heapq.heappush(self._priority_queue, task)
            
            self._stats["total_tasks"] += 1
            self._stats["active_tasks"] += 1
            
            logger.info(f"已添加任务: {task.task_id} (优先级: {task.priority.name}, 间隔: {task.interval}秒)")
            return True
    
    def remove_task(self, task_id: str) -> bool:
        """移除调度任务"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            task.is_active = False
            
            # 从队列中移除并重新构建队列
            self._priority_queue = [t for t in self._priority_queue if t.task_id != task_id]
            heapq.heapify(self._priority_queue)
            
            del self._tasks[task_id]
            
            self._stats["active_tasks"] -= 1
            
            logger.info(f"已移除任务: {task_id}")
            return True
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """更新任务参数"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            
            # 更新任务参数
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # 如果更新了优先级或间隔，需要重新构建队列
            self._priority_queue = [t for t in self._priority_queue if t.task_id != task_id]
            heapq.heapify(self._priority_queue)
            heapq.heappush(self._priority_queue, task)
            
            logger.info(f"已更新任务: {task_id}")
            return True
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            self._tasks[task_id].is_active = False
            self._stats["active_tasks"] -= 1
            
            logger.info(f"已暂停任务: {task_id}")
            return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            task.is_active = True
            task.next_execution = time.time()  # 立即执行一次
            
            self._stats["active_tasks"] += 1
            
            # 将任务重新加入队列
            heapq.heappush(self._priority_queue, task)
            
            logger.info(f"已恢复任务: {task_id}")
            return True
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """获取所有任务"""
        with self._lock:
            return list(self._tasks.values())
    
    def get_stats(self) -> Dict[str, int]:
        """获取调度器统计信息"""
        with self._lock:
            return self._stats.copy()
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self._is_running:
            try:
                # 获取需要执行的任务
                tasks_to_execute = self._get_pending_tasks()
                
                if tasks_to_execute:
                    # 合并相似任务
                    merged_tasks = self._merge_similar_tasks(tasks_to_execute)
                    
                    # 执行任务
                    self._execute_tasks(merged_tasks)
                
                # 等待下一次检查
                time.sleep(self._polling_interval)
                
            except Exception as e:
                logger.error(f"调度器循环错误: {e}")
                time.sleep(1)
    
    def _get_pending_tasks(self) -> List[ScheduledTask]:
        """获取待执行的任务"""
        with self._lock:
            tasks = []
            
            # 检查队列中的任务
            while self._priority_queue:
                task = self._priority_queue[0]
                
                if task.should_execute():
                    # 从队列中取出任务
                    heapq.heappop(self._priority_queue)
                    tasks.append(task)
                else:
                    break
            
            return tasks
    
    def _merge_similar_tasks(self, tasks: List[ScheduledTask]) -> List[ScheduledTask]:
        """合并相似的任务以减少通信次数"""
        if not tasks:
            return []
            
        merged_tasks = []
        task_groups = {}
        
        # 按设备、任务类型和优先级分组
        for task in tasks:
            key = (task.device_id, task.task_type, task.priority)
            
            if key not in task_groups:
                task_groups[key] = []
            
            task_groups[key].append(task)
        
        # 合并每组任务
        for (device_id, task_type, priority), group_tasks in task_groups.items():
            if task_type in [TaskType.READ_REGISTER, TaskType.BATCH_READ] and len(group_tasks) > 1:
                # 合并寄存器读取任务
                merged_task = self._merge_register_read_tasks(group_tasks)
                merged_tasks.append(merged_task)
                self._stats["merged_tasks"] += len(group_tasks) - 1
            elif task_type == TaskType.WRITE_REGISTER and len(group_tasks) > 1:
                # 合并寄存器写入任务
                merged_task = self._merge_register_write_tasks(group_tasks)
                merged_tasks.append(merged_task)
                self._stats["merged_tasks"] += len(group_tasks) - 1
            else:
                # 其他任务类型不合并
                merged_tasks.extend(group_tasks)
        
        return merged_tasks

    def _merge_register_write_tasks(self, tasks: List[ScheduledTask]) -> ScheduledTask:
        """合并寄存器写入任务"""
        if not tasks:
            raise ValueError("任务列表不能为空")
            
        # 使用优先级最高的任务作为基础
        base_task = max(tasks, key=lambda t: t.priority.value)
        
        # 合并所有寄存器地址和值
        write_values = {}
        for task in tasks:
            if task.register_addresses and len(task.register_addresses) == 1:
                addr = task.register_addresses[0]
                write_values[addr] = task.write_value
        
        # 创建合并后的任务
        merged_task = ScheduledTask(
            device_id=base_task.device_id,
            task_type=TaskType.BATCH_READ,  # 使用BATCH_READ类型，但实际是批量写入
            priority=base_task.priority,
            interval=base_task.interval,
            callback=self._handle_batch_write_result,
            args=(tasks,),  # 保存原始任务以便回调
            register_addresses=list(write_values.keys()),
            task_id=f"merged_write_{base_task.task_id}"
        )
        
        # 保存写入值到任务对象
        merged_task.write_value = write_values
        
        merged_task.last_executed = base_task.last_executed
        merged_task.next_execution = base_task.next_execution
        
        return merged_task

    def _handle_batch_write_result(self, original_tasks: List[ScheduledTask], success: bool):
        """处理批量写入结果并调用原始任务的回调"""
        for task in original_tasks:
            if task.callback:
                try:
                    task.callback(success, *task.args, **task.kwargs)
                except Exception as e:
                    logger.error(f"执行任务回调失败: {e}")
                    task.mark_executed(success=False)
                else:
                    task.mark_executed(success=True)
    
    def _merge_register_read_tasks(self, tasks: List[ScheduledTask]) -> ScheduledTask:
        """合并寄存器读取任务"""
        if not tasks:
            raise ValueError("任务列表不能为空")
            
        # 使用优先级最高的任务作为基础
        base_task = max(tasks, key=lambda t: t.priority.value)
        
        # 合并所有寄存器地址
        all_addresses = set()
        for task in tasks:
            all_addresses.update(task.register_addresses)
        
        # 创建合并后的任务
        merged_task = ScheduledTask(
            device_id=base_task.device_id,
            task_type=TaskType.BATCH_READ,
            priority=base_task.priority,
            interval=base_task.interval,
            callback=self._handle_batch_read_result,
            args=(tasks,),  # 保存原始任务以便回调
            register_addresses=list(all_addresses),
            task_id=f"merged_{base_task.task_id}"
        )
        
        merged_task.last_executed = base_task.last_executed
        merged_task.next_execution = base_task.next_execution
        
        return merged_task
    
    def _handle_batch_read_result(self, original_tasks: List[ScheduledTask], result: Dict[int, int]):
        """处理批量读取结果并调用原始任务的回调"""
        for task in original_tasks:
            if task.callback:
                # 提取当前任务需要的寄存器值
                task_result = {addr: result.get(addr) for addr in task.register_addresses}
                
                try:
                    task.callback(task_result, *task.args, **task.kwargs)
                except Exception as e:
                    logger.error(f"执行任务回调失败: {e}")
                    task.mark_executed(success=False)
                else:
                    task.mark_executed(success=True)
    
    def _execute_tasks(self, tasks: List[ScheduledTask]):
        """执行任务"""
        if not tasks:
            return

        # 限制并发执行的任务数量
        tasks_to_execute = tasks[:self._max_concurrent_tasks]
        remaining_tasks = tasks[self._max_concurrent_tasks:]

        # 将剩余任务放回队列
        if remaining_tasks:
            with self._lock:
                for task in remaining_tasks:
                    heapq.heappush(self._priority_queue, task)

        # 创建任务执行线程
        threads = []
        task_results = [None] * len(tasks_to_execute)

        def execute_task_wrapper(index, task):
            try:
                if task.task_type == TaskType.BATCH_READ:
                    self._execute_batch_read(task)
                elif task.task_type == TaskType.READ_REGISTER:
                    self._execute_register_read(task)
                elif task.task_type == TaskType.WRITE_REGISTER:
                    self._execute_register_write(task)
                elif task.task_type == TaskType.DEVICE_STATUS:
                    self._execute_device_status(task)
                elif task.task_type == TaskType.CUSTOM:
                    self._execute_custom_task(task)
                
                # 更新任务状态
                task.update_next_execution()
                task.mark_executed(success=True)
                self._stats["executed_tasks"] += 1
                
            except Exception as e:
                logger.error(f"执行任务 {task.task_id} 失败: {e}")
                task.mark_executed(success=False)
                self._stats["failed_tasks"] += 1
            
            finally:
                # 如果任务仍然激活，将其放回队列
                if task.is_active:
                    with self._lock:
                        heapq.heappush(self._priority_queue, task)

        # 启动任务执行线程
        for i, task in enumerate(tasks_to_execute):
            thread = threading.Thread(target=execute_task_wrapper, args=(i, task), daemon=True)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成或超时
        for thread in threads:
            thread.join(timeout=5.0)  # 5秒超时
    
    def _execute_batch_read(self, task: ScheduledTask):
        """执行批量读取任务"""
        logger.debug(f"执行批量读取任务: {task.task_id} (设备: {task.device_id}, 地址: {task.register_addresses})")
        
        # 构造寄存器列表
        registers = [{
            "address": addr,
            "type": "holding_register"
        } for addr in task.register_addresses]
        
        result = {}
        
        try:
            if self._async_manager and self._async_manager._is_running:
                # 使用异步管理器
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def batch_read():
                    return await self._async_manager.batch_read_registers(
                        task.device_id, registers
                    )
                
                result = loop.run_until_complete(batch_read())
                loop.close()
                
            elif self._sync_manager:
                # 使用同步管理器
                result = self._sync_manager.batch_read_registers(
                    task.device_id, registers
                )
            
            # 调用回调函数
            if task.callback:
                task.callback(result, *task.args, **task.kwargs)
                
            task.mark_executed(success=True)
            self._stats["executed_tasks"] += 1
            
        except Exception as e:
            logger.error(f"批量读取失败: {e}")
            task.mark_executed(success=False)
            self._stats["failed_tasks"] += 1
    
    def _execute_register_read(self, task: ScheduledTask):
        """执行寄存器读取任务"""
        logger.debug(f"执行寄存器读取任务: {task.task_id} (设备: {task.device_id}, 地址: {task.register_addresses})")
        
        try:
            if not task.register_addresses:
                logger.error(f"寄存器读取任务 {task.task_id} 没有指定寄存器地址")
                task.mark_executed(success=False)
                self._stats["failed_tasks"] += 1
                return
            
            # 调用设备管理器执行读取操作
            result = {}
            if self._async_manager and self._async_manager._is_running:
                # 使用异步管理器
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def read_registers():
                    return await self._async_manager.read_registers(
                        task.device_id, 
                        task.register_addresses[0], 
                        len(task.register_addresses)
                    )
                
                values = loop.run_until_complete(read_registers())
                loop.close()
                
                if values:
                    for i, addr in enumerate(task.register_addresses):
                        if i < len(values):
                            result[addr] = values[i]
                            
            elif self._sync_manager:
                # 使用同步管理器
                for addr in task.register_addresses:
                    values = self._sync_manager.read_registers(
                        task.device_id, 
                        addr, 
                        1
                    )
                    if values:
                        result[addr] = values[0]
            
            # 调用回调函数
            if task.callback and result:
                task.callback(result, *task.args, **task.kwargs)
                
            task.mark_executed(success=True)
            self._stats["executed_tasks"] += 1
            
        except Exception as e:
            logger.error(f"执行寄存器读取任务失败: {e}")
            task.mark_executed(success=False)
            self._stats["failed_tasks"] += 1
    
    def _execute_register_write(self, task: ScheduledTask):
        """执行寄存器写入任务"""
        logger.debug(f"执行寄存器写入任务: {task.task_id} (设备: {task.device_id}, 地址: {task.register_addresses}, 值: {task.write_value})")
        
        try:
            if not task.register_addresses:
                logger.error(f"寄存器写入任务 {task.task_id} 没有指定寄存器地址")
                task.mark_executed(success=False)
                self._stats["failed_tasks"] += 1
                return
            
            if task.write_value is None:
                logger.error(f"寄存器写入任务 {task.task_id} 没有指定写入值")
                task.mark_executed(success=False)
                self._stats["failed_tasks"] += 1
                return
            
            # 调用设备管理器执行写入操作
            success = False
            if self._async_manager and self._async_manager._is_running:
                # 使用异步管理器
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def write_register():
                    return await self._async_manager.write_register(
                        task.device_id, 
                        task.register_addresses[0], 
                        task.write_value
                    )
                
                success = loop.run_until_complete(write_register())
                loop.close()
                
            elif self._sync_manager:
                # 使用同步管理器
                success = self._sync_manager.write_register(
                    task.device_id, 
                    task.register_addresses[0], 
                    task.write_value
                )
            
            # 调用回调函数
            if task.callback:
                task.callback(success, *task.args, **task.kwargs)
                
            task.mark_executed(success=success)
            if success:
                self._stats["executed_tasks"] += 1
            else:
                self._stats["failed_tasks"] += 1
                
        except Exception as e:
            logger.error(f"执行寄存器写入任务失败: {e}")
            task.mark_executed(success=False)
            self._stats["failed_tasks"] += 1
    
    def _execute_device_status(self, task: ScheduledTask):
        """执行设备状态检查任务"""
        logger.debug(f"执行设备状态检查任务: {task.task_id} (设备: {task.device_id})")
        
        try:
            # 调用设备管理器检查设备状态
            is_connected = False
            if self._async_manager and self._async_manager._is_running:
                # 使用异步管理器
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def check_status():
                    return await self._async_manager.is_device_connected(task.device_id)
                
                is_connected = loop.run_until_complete(check_status())
                loop.close()
                
            elif self._sync_manager:
                # 使用同步管理器
                is_connected = self._sync_manager.is_connected(task.device_id)
            
            # 调用回调函数
            if task.callback:
                task.callback(is_connected, *task.args, **task.kwargs)
                
            task.mark_executed(success=True)
            self._stats["executed_tasks"] += 1
            
        except Exception as e:
            logger.error(f"执行设备状态检查任务失败: {e}")
            task.mark_executed(success=False)
            self._stats["failed_tasks"] += 1
    
    def _execute_custom_task(self, task: ScheduledTask):
        """执行自定义任务"""
        logger.debug(f"执行自定义任务: {task.task_id} (设备: {task.device_id})")
        
        if task.callback:
            try:
                task.callback(*task.args, **task.kwargs)
                task.mark_executed(success=True)
                self._stats["executed_tasks"] += 1
            except Exception as e:
                logger.error(f"执行自定义任务失败: {e}")
                task.mark_executed(success=False)
                self._stats["failed_tasks"] += 1
        else:
            logger.warning(f"自定义任务 {task.task_id} 没有回调函数")
            task.mark_executed(success=False)
            self._stats["failed_tasks"] += 1


# 创建任务调度器实例
def create_task_scheduler(async_manager: Optional[AsyncDeviceManager] = None,
                         sync_manager: Optional[DeviceMonitor] = None) -> TaskScheduler:
    """创建任务调度器实例"""
    return TaskScheduler(async_manager, sync_manager)


# 示例用法
def example_usage():
    """任务调度器示例用法"""
    
    # 创建调度器
    scheduler = TaskScheduler()
    
    # 启动调度器
    scheduler.start()
    
    # 定义回调函数
    def temperature_callback(result):
        logger.info(f"温度数据: {result}")
    
    def pressure_callback(result):
        logger.info(f"压力数据: {result}")
    
    # 添加高优先级任务 (温度)
    temp_task = ScheduledTask(
        device_id="Pump-01",
        task_type=TaskType.READ_REGISTER,
        priority=TaskPriority.HIGH,
        interval=0.5,  # 500ms执行一次
        callback=temperature_callback,
        register_addresses=[1],  # 温度寄存器地址
        task_id="temp_monitor"
    )
    scheduler.add_task(temp_task)
    
    # 添加正常优先级任务 (压力)
    pressure_task = ScheduledTask(
        device_id="Pump-01",
        task_type=TaskType.READ_REGISTER,
        priority=TaskPriority.NORMAL,
        interval=1.0,  # 1秒执行一次
        callback=pressure_callback,
        register_addresses=[2],  # 压力寄存器地址
        task_id="pressure_monitor"
    )
    scheduler.add_task(pressure_task)
    
    # 运行一段时间
    try:
        logger.info("调度器示例运行中...")
        time.sleep(10)
    finally:
        # 停止调度器
        scheduler.stop()
        logger.info("调度器示例结束")


if __name__ == "__main__":
    example_usage()
