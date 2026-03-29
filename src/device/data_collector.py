"""
数据采集引擎

设计原则:
    1. 继承QObject, 全面支持Qt信号槽
    2. 每个设备一个QThread (PollWorker), 并行轮询
    3. 采集引擎主控: 启停所有Worker, 聚合状态/错误
    4. 失败重试机制 (可配置重试次数和间隔)
    5. 读请求自动合并 (Device.get_read_requests)
    6. 支持单设备/单寄存器写入
    7. 采集统计 (成功率/延迟/吞吐量)
    8. 优雅关闭 (stop等待所有线程退出)

核心数据流:
    DataCollector.start()
      → 为每个enabled设备创建PollWorker(QThread)
        → PollWorker.run(): 循环
          → Device.get_read_requests() 生成读取请求列表
          → BaseProtocol.read_xxx() 执行协议读取
          → Device.update_register_value() 回写寄存器
          → Register.update_raw_value() 自动工程值转换 + 报警检测
          → value_changed/alarm_triggered 信号通知UI

信号体系:
    started()                     → 采集引擎启动
    stopped()                     → 采集引擎停止
    device_poll_success(str)      → 设备单次轮询成功 (device_id)
    device_poll_failure(str, str) → 设备单次轮询失败 (device_id, error_msg)
    write_completed(str, str, bool) → 写入完成 (device_id, reg_name, success)
    stats_updated(dict)           → 统计信息更新
    error_occurred(str)           → 全局错误
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Optional

from PySide6.QtCore import QMutex, QMutexLocker, QObject, QThread, Signal

from src.device.device import Device
from src.device.register import Register
from src.protocols.base_protocol import BaseProtocol, ReadResult, WriteResult
from src.protocols.enums import DeviceStatus, ProtocolType, RegisterType
from src.utils.logger import get_logger

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 轮询统计
# ═══════════════════════════════════════════════════════════════


class CollectorStats:
    """采集引擎统计信息 (线程安全)"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_polls: int = 0
        self._success_polls: int = 0
        self._failed_polls: int = 0
        self._total_registers_read: int = 0
        self._total_writes: int = 0
        self._write_successes: int = 0
        self._write_failures: int = 0
        self._start_time: Optional[float] = None
        self._last_poll_time: Optional[float] = None
        self._avg_latency_ms: float = 0.0
        self._latency_samples: list[float] = []  # 最近100次延迟

    def record_poll(self, success: bool, register_count: int, latency_ms: float) -> None:
        """记录一次轮询结果"""
        with self._lock:
            self._total_polls += 1
            if success:
                self._success_polls += 1
                self._total_registers_read += register_count
            else:
                self._failed_polls += 1
            self._last_poll_time = time.monotonic()

            # 延迟采样 (保留最近100个)
            self._latency_samples.append(latency_ms)
            if len(self._latency_samples) > 100:
                self._latency_samples.pop(0)
            self._avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)

    def record_write(self, success: bool) -> None:
        """记录一次写入"""
        with self._lock:
            self._total_writes += 1
            if success:
                self._write_successes += 1
            else:
                self._write_failures += 1

    def start(self) -> None:
        with self._lock:
            self._start_time = time.monotonic()

    @property
    def uptime_seconds(self) -> float:
        with self._lock:
            if self._start_time is None:
                return 0.0
            return time.monotonic() - self._start_time

    @property
    def success_rate(self) -> float:
        with self._lock:
            if self._total_polls == 0:
                return 100.0
            return (self._success_polls / self._total_polls) * 100.0

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_polls": self._total_polls,
                "success_polls": self._success_polls,
                "failed_polls": self._failed_polls,
                "success_rate": round(self.success_rate, 2),
                "total_registers_read": self._total_registers_read,
                "total_writes": self._total_writes,
                "write_successes": self._write_successes,
                "write_failures": self._write_failures,
                "avg_latency_ms": round(self._avg_latency_ms, 2),
                "uptime_seconds": round(self.uptime_seconds, 1),
                "last_poll": (datetime.now().isoformat() if self._last_poll_time else None),
            }

    def reset(self) -> None:
        with self._lock:
            self._total_polls = 0
            self._success_polls = 0
            self._failed_polls = 0
            self._total_registers_read = 0
            self._total_writes = 0
            self._write_successes = 0
            self._write_failures = 0
            self._start_time = None
            self._last_poll_time = None
            self._avg_latency_ms = 0.0
            self._latency_samples.clear()


# ═══════════════════════════════════════════════════════════════
# 轮询工作线程
# ═══════════════════════════════════════════════════════════════


class PollWorker(QThread):
    """单设备轮询工作线程

    在独立线程中循环执行:
        1. 获取设备读取请求 (Device.get_read_requests)
        2. 通过协议层执行读取 (BaseProtocol.read_xxx)
        3. 将结果回写到设备模型 (Device.update_register_value)
        4. 失败时按配置重试

    Args:
        device: 设备实例
        protocol: 协议实例 (已配置host/port等)
        poll_interval_ms: 轮询间隔 (毫秒)
        timeout_ms: 单次请求超时 (毫秒)
        retry_count: 失败重试次数
        retry_interval_ms: 重试间隔 (毫秒)
    """

    # ── 信号 ──
    poll_success = Signal(str)  # device_id
    poll_failure = Signal(str, str)  # device_id, error_msg
    status_changed = Signal(str, object)  # device_id, DeviceStatus

    def __init__(
        self,
        device: Device,
        protocol: BaseProtocol,
        poll_interval_ms: int = 1000,
        timeout_ms: int = 3000,
        retry_count: int = 3,
        retry_interval_ms: int = 500,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self._device = device
        self._protocol = protocol
        self._poll_interval_ms = poll_interval_ms
        self._timeout_ms = timeout_ms
        self._retry_count = retry_count
        self._retry_interval_ms = retry_interval_ms
        self._stop_flag = threading.Event()

    @property
    def device_id(self) -> str:
        return self._device.id

    def stop(self) -> None:
        """请求停止轮询"""
        self._stop_flag.set()

    def run(self) -> None:
        """轮询主循环 (在线程中执行)"""
        logger.info(f"轮询线程启动: {self._device.name} " f"(间隔={self._poll_interval_ms}ms)")

        while not self._stop_flag.is_set():
            try:
                self._poll_once()
            except Exception as e:
                error_msg = f"轮询异常: {e}"
                logger.error(
                    f"设备[{self._device.name}] {error_msg}",
                    exc_info=True,
                )
                self.poll_failure.emit(self._device.id, error_msg)
                self._device.set_error(error_msg)

            # 等待下一次轮询
            self._stop_flag.wait(self._poll_interval_ms / 1000.0)

        # 断开连接
        try:
            self._protocol.disconnect_from_device()
        except Exception:
            pass

        self._device.set_status(DeviceStatus.DISCONNECTED)
        self.status_changed.emit(self._device.id, DeviceStatus.DISCONNECTED)
        logger.info(f"轮询线程退出: {self._device.name}")

    def _poll_once(self) -> None:
        """执行一次完整的设备轮询"""
        if not self._protocol.is_connected:
            self._connect_device()
            if not self._protocol.is_connected:
                return

        # 获取读取请求列表
        read_requests = self._device.get_read_requests()
        if not read_requests:
            return

        success_count = 0
        total_requests = len(read_requests)
        total_registers = 0

        for request in read_requests:
            reg_type = request["register_type"]
            start_addr = request["start_address"]
            count = request["count"]
            reg_names = request["register_names"]

            success = False
            last_error = ""

            # 重试机制
            for attempt in range(self._retry_count + 1):
                try:
                    result = self._execute_read(reg_type, start_addr, count)

                    if result.success:
                        # 回写寄存器值
                        self._dispatch_values(result, start_addr, reg_names)
                        success = True
                        total_registers += len(reg_names)
                        break
                    else:
                        last_error = result.error_message
                        if attempt < self._retry_count:
                            self._stop_flag.wait(self._retry_interval_ms / 1000.0)
                except Exception as e:
                    last_error = str(e)
                    logger.warning(
                        f"设备[{self._device.name}] 读取失败 " f"(尝试 {attempt + 1}/{self._retry_count + 1}): " f"{e}"
                    )
                    if attempt < self._retry_count:
                        self._stop_flag.wait(self._retry_interval_ms / 1000.0)

            if not success:
                self._device.record_poll_failure()
                self._device.set_error(last_error)
                self.poll_failure.emit(self._device.id, last_error)
            else:
                success_count += 1

        # 设备级统计
        if success_count == total_requests:
            self._device.record_poll_success()
            self.poll_success.emit(self._device.id)
        else:
            self._device.record_poll_failure()

    def _connect_device(self) -> None:
        """连接设备"""
        self._device.set_status(DeviceStatus.CONNECTING)
        self.status_changed.emit(self._device.id, DeviceStatus.CONNECTING)

        try:
            self._protocol.connect_to_device()
            self._device.set_status(DeviceStatus.CONNECTED)
            self.status_changed.emit(self._device.id, DeviceStatus.CONNECTED)
        except Exception as e:
            self._device.set_error(str(e))
            self.status_changed.emit(self._device.id, DeviceStatus.ERROR)
            raise

    def _execute_read(self, reg_type: RegisterType, start_addr: int, count: int) -> ReadResult:
        """根据寄存器类型执行对应的读取方法"""
        if reg_type == RegisterType.COIL:
            return self._protocol.read_coils(start_addr, count)
        elif reg_type == RegisterType.DISCRETE_INPUT:
            return self._protocol.read_discrete_inputs(start_addr, count)
        elif reg_type == RegisterType.HOLDING_REGISTER:
            return self._protocol.read_holding_registers(start_addr, count)
        elif reg_type == RegisterType.INPUT_REGISTER:
            return self._protocol.read_input_registers(start_addr, count)
        else:
            return ReadResult.error(
                f"不支持的寄存器类型: {reg_type}",
                start_address=start_addr,
            )

    def _dispatch_values(
        self,
        result: ReadResult,
        start_addr: int,
        reg_names: list[str],
    ) -> None:
        """将读取结果分发给对应的寄存器

        合并请求可能包含多个寄存器, 需要根据地址拆分。
        """
        values = result.values
        if not values:
            return

        for i, reg_name in enumerate(reg_names):
            register = self._device.get_register(reg_name)
            if register is None:
                continue

            # 计算该寄存器在返回值列表中的偏移
            reg_offset = register.address - start_addr

            if reg_type_is_bit(result.function_code):
                # 位操作: 值为bool列表
                if reg_offset < len(values):
                    raw_val = 1 if values[reg_offset] else 0
                    self._device.update_register_value(reg_name, raw_val)
            else:
                # 寄存器操作: 需要提取该寄存器占用的连续值
                qty = register.quantity
                if qty == 1:
                    if reg_offset < len(values):
                        self._device.update_register_value(reg_name, int(values[reg_offset]))
                else:
                    # 多寄存器值 → 通过字节重新编码
                    # 提取属于该寄存器的原始字节
                    raw_bytes = self._extract_register_bytes(result.raw_data, reg_offset, qty)
                    if raw_bytes:
                        raw_val = register.parse_bytes(raw_bytes)
                        self._device.update_register_value(reg_name, raw_val)

    def _extract_register_bytes(self, raw_data: bytes, offset: int, quantity: int) -> bytes:
        """从原始响应数据中提取指定寄存器的字节"""
        if not raw_data or offset < 0:
            return b""
        byte_offset = offset * 2  # 每寄存器2字节
        byte_count = quantity * 2
        end = byte_offset + byte_count
        if end > len(raw_data):
            return raw_data[byte_offset:]
        return raw_data[byte_offset:end]

    def write_register(self, register_name: str, value: Any) -> WriteResult:
        """写入单个寄存器 (从工作线程调用)

        Args:
            register_name: 寄存器名称
            value: 写入值

        Returns:
            WriteResult
        """
        register = self._device.get_register(register_name)
        if register is None:
            return WriteResult(
                function_code=0,
                address=0,
                success=False,
                error_message=f"寄存器不存在: {register_name}",
            )

        if not register.writable:
            return WriteResult(
                function_code=0,
                address=register.address,
                success=False,
                error_message=f"寄存器'{register_name}'不可写",
            )

        if not self._protocol.is_connected:
            return WriteResult(
                function_code=0,
                address=register.address,
                success=False,
                error_message="设备未连接",
            )

        try:
            if register.register_type == RegisterType.COIL:
                return self._protocol.write_single_coil(register.address, bool(value))
            elif register.register_type == RegisterType.HOLDING_REGISTER:
                raw_value = register.engineering_to_raw(float(value))
                return self._protocol.write_single_register(register.address, raw_value)
            else:
                return WriteResult(
                    function_code=0,
                    address=register.address,
                    success=False,
                    error_message="该寄存器类型不支持写入",
                )
        except Exception as e:
            return WriteResult(
                function_code=0,
                address=register.address,
                success=False,
                error_message=str(e),
            )


def reg_type_is_bit(function_code: int) -> bool:
    """判断功能码是否为位操作"""
    return function_code in (0x01, 0x02)


# ═══════════════════════════════════════════════════════════════
# 协议工厂
# ═══════════════════════════════════════════════════════════════


def create_protocol(device: Device, parent: Optional[QObject] = None) -> BaseProtocol:
    """根据设备协议类型创建协议实例

    Args:
        device: 设备实例
        parent: Qt父对象

    Returns:
        对应的协议实例

    Raises:
        ValueError: 不支持的协议类型
    """
    if device.protocol_type == ProtocolType.MODBUS_TCP:
        from src.protocols.modbus_tcp import ModbusTCPProtocol

        tcp = device.tcp_params
        return ModbusTCPProtocol(
            host=tcp.host,
            port=tcp.port,
            timeout=tcp.timeout,
            slave_address=device.slave_id,
            parent=parent,
        )
    elif device.protocol_type == ProtocolType.MODBUS_RTU:
        from src.protocols.modbus_rtu import ModbusRTUProtocol

        sp = device.serial_params
        return ModbusRTUProtocol(
            port=sp.port,
            baudrate=sp.baud_rate,
            slave_address=device.slave_id,
            timeout=sp.timeout,
            parent=parent,
        )
    elif device.protocol_type == ProtocolType.MODBUS_ASCII:
        from src.protocols.modbus_ascii import ModbusASCIIProtocol

        sp = device.serial_params
        return ModbusASCIIProtocol(
            port=sp.port,
            baudrate=sp.baud_rate,
            slave_address=device.slave_id,
            timeout=sp.timeout,
            parent=parent,
        )
    else:
        raise ValueError(f"不支持的协议类型: {device.protocol_type}")


# ═══════════════════════════════════════════════════════════════
# 数据采集引擎
# ═══════════════════════════════════════════════════════════════


class DataCollector(QObject):
    """数据采集引擎

    管理所有设备的轮询采集。每个设备一个PollWorker线程。

    Usage:
        collector = DataCollector(device_manager)
        collector.start()     # 启动所有设备轮询
        collector.stop()      # 停止所有
        collector.write_register(device_id, reg_name, value)  # 写入
        stats = collector.get_stats()

    Attributes:
        device_manager: 设备管理器引用
    """

    # ── 信号 ──
    started = Signal()  # 引擎启动
    stopped = Signal()  # 引擎停止
    device_poll_success = Signal(str)  # device_id
    device_poll_failure = Signal(str, str)  # device_id, error_msg
    write_completed = Signal(str, str, bool)  # device_id, reg_name, success
    stats_updated = Signal(dict)  # stats dict
    error_occurred = Signal(str)  # error message

    def __init__(
        self,
        device_manager: Any,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self._device_manager = device_manager
        self._workers: dict[str, PollWorker] = {}  # device_id → PollWorker
        self._protocols: dict[str, BaseProtocol] = {}  # device_id → Protocol
        self._mutex = QMutex()
        self._running = False
        self._stats = CollectorStats()

    # ═══════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def active_device_count(self) -> int:
        return len(self._workers)

    @property
    def stats(self) -> dict[str, Any]:
        return self._stats.to_dict()

    # ═══════════════════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════════════════

    def start(self) -> None:
        """启动采集引擎, 为所有已启用设备创建轮询线程"""
        if self._running:
            logger.warning("采集引擎已在运行")
            return

        locker = QMutexLocker(self._mutex)

        # 获取所有已启用设备
        devices = self._device_manager.get_enabled_devices()

        if not devices:
            logger.warning("没有已启用的设备, 无法启动采集")
            return

        self._stats.start()
        self._running = True

        for device in devices:
            self._start_device_worker(device)

        self.started.emit()
        logger.info(f"采集引擎启动: {len(devices)} 个设备")

    def stop(self) -> None:
        """停止采集引擎, 等待所有线程退出"""
        if not self._running:
            return

        locker = QMutexLocker(self._mutex)
        self._running = False

        # 停止所有worker
        for worker in self._workers.values():
            worker.stop()

        # 等待线程退出 (最多5秒)
        for worker in list(self._workers.values()):
            worker.wait(5000)

        self._workers.clear()
        self._protocols.clear()

        self.stopped.emit()
        logger.info("采集引擎已停止")

    def stop_device(self, device_id: str) -> bool:
        """停止单个设备的轮询

        Args:
            device_id: 设备ID

        Returns:
            True=成功停止
        """
        locker = QMutexLocker(self._mutex)

        worker = self._workers.pop(device_id, None)
        protocol = self._protocols.pop(device_id, None)

        if worker:
            worker.stop()
            worker.wait(5000)
            if protocol:
                try:
                    protocol.disconnect_from_device()
                except Exception:
                    pass
            return True
        return False

    def start_device(self, device_id: str) -> bool:
        """启动单个设备的轮询

        Args:
            device_id: 设备ID

        Returns:
            True=成功启动
        """
        locker = QMutexLocker(self._mutex)

        if device_id in self._workers:
            logger.warning(f"设备 {device_id} 已在轮询中")
            return False

        device = self._device_manager.get_device(device_id)
        if device is None:
            logger.error(f"设备不存在: {device_id}")
            return False

        self._start_device_worker(device)
        return True

    def restart_device(self, device_id: str) -> bool:
        """重启单个设备的轮询"""
        self.stop_device(device_id)
        return self.start_device(device_id)

    def _start_device_worker(self, device: Device) -> None:
        """为单个设备创建并启动轮询线程"""
        try:
            # 创建协议实例
            protocol = create_protocol(device, parent=self)

            # 创建工作线程
            poll_config = device.poll_config
            worker = PollWorker(
                device=device,
                protocol=protocol,
                poll_interval_ms=poll_config.interval_ms,
                timeout_ms=poll_config.timeout_ms,
                retry_count=poll_config.retry_count,
                retry_interval_ms=poll_config.retry_interval_ms,
                parent=self,
            )

            # 连接信号
            worker.poll_success.connect(self._on_poll_success)
            worker.poll_failure.connect(self._on_poll_failure)
            worker.status_changed.connect(self._on_status_changed)

            # 存储引用
            self._workers[device.id] = worker
            self._protocols[device.id] = protocol

            # 启动线程
            worker.start()

            logger.info(f"设备[{device.name}] 轮询已启动 " f"(间隔={poll_config.interval_ms}ms)")

        except Exception as e:
            logger.error(
                f"设备[{device.name}] 启动轮询失败: {e}",
                exc_info=True,
            )
            self.error_occurred.emit(f"设备[{device.name}] 启动失败: {e}")

    # ═══════════════════════════════════════════════════════════
    # 写入操作
    # ═══════════════════════════════════════════════════════════

    def write_register(
        self,
        device_id: str,
        register_name: str,
        value: Any,
    ) -> WriteResult:
        """写入单个寄存器值

        Args:
            device_id: 设备ID
            register_name: 寄存器名称
            value: 写入值 (工程值)

        Returns:
            WriteResult
        """
        worker = self._workers.get(device_id)
        if worker is None:
            return WriteResult(
                function_code=0,
                address=0,
                success=False,
                error_message=f"设备 {device_id} 未在轮询中",
            )

        result = worker.write_register(register_name, value)
        self._stats.record_write(result.success)
        self.write_completed.emit(device_id, register_name, result.success)
        return result

    # ═══════════════════════════════════════════════════════════
    # 信号处理
    # ═══════════════════════════════════════════════════════════

    def _on_poll_success(self, device_id: str) -> None:
        """轮询成功回调"""
        self._stats.record_poll(True, 0, 0)
        self.device_poll_success.emit(device_id)
        # 每10次成功轮询更新一次统计
        total = self._stats.to_dict()["total_polls"]
        if total % 10 == 0:
            self.stats_updated.emit(self._stats.to_dict())

    def _on_poll_failure(self, device_id: str, error_msg: str) -> None:
        """轮询失败回调"""
        self._stats.record_poll(False, 0, 0)
        self.device_poll_failure.emit(device_id, error_msg)
        self.stats_updated.emit(self._stats.to_dict())

    def _on_status_changed(self, device_id: str, status: DeviceStatus) -> None:
        """设备状态变化回调"""
        # 可以在这里处理重连逻辑
        if status == DeviceStatus.DISCONNECTED and self._running:
            logger.warning(f"设备 {device_id} 已断开连接, 轮询线程将自动重连")

    # ═══════════════════════════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════════════════════════

    def get_stats(self) -> dict[str, Any]:
        """获取采集统计信息"""
        return self._stats.to_dict()

    def get_device_stats(self, device_id: str) -> Optional[dict[str, Any]]:
        """获取指定设备的统计信息"""
        device = self._device_manager.get_device(device_id)
        if device is None:
            return None
        return {
            "device_id": device.id,
            "device_name": device.name,
            "status": device.device_status.value,
            "total_polls": device.total_polls,
            "failed_polls": device.failed_polls,
            "success_rate": round(device.success_rate, 2),
            "register_count": device.register_count,
            "alarm_count": device.alarm_count,
            "is_polling": device_id in self._workers,
        }

    def get_polling_devices(self) -> list[str]:
        """获取正在轮询的设备ID列表"""
        return list(self._workers.keys())

    def is_device_polling(self, device_id: str) -> bool:
        """检查指定设备是否正在轮询"""
        return device_id in self._workers

    # ═══════════════════════════════════════════════════════════
    # 统计
    # ═══════════════════════════════════════════════════════════

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats.reset()
        for device in self._device_manager:
            device.reset_statistics()
        logger.info("采集统计已重置")

    def __repr__(self) -> str:
        return f"DataCollector(" f"running={self._running}, " f"devices={self.active_device_count}" f")"
