# -*- coding: utf-8 -*-
"""
MCGS Modbus TCP 数据读取器（v2.0 重构版）

应用层（Application Layer）— 委托下层完成工作：

职责：
1. 加载 devices.json 配置文件（应用层逻辑）
2. 自动计算读取范围（应用层算法）
3. 批量读取优化（应用层调度）
4. 委托 core.protocols 进行协议通信
5. 委托 core.communication.modbus_value_parser 进行数据解析
6. 数据映射与格式化输出

分层架构：
  core/protocols/modbus_protocol.py        ← 协议层（帧构建/解析/TCP/RTU/ASCII）
  core/protocols/byte_order_config.py      ← 字节序配置（ABCD/BADC/CDAB/DCBA）
  core/communication/modbus_value_parser.py ← 解析层（寄存器值→工程值）
  core/utils/mcgs_modbus_reader.py        ← 应用层（配置/调度/映射）
  core/services/mcgs_service.py           ← 业务层（报警/存储/发布）
"""

import json
import logging
import math
import struct
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ==================== 数据结构定义 ====================


@dataclass
class DevicePointConfig:
    """
    单个数据点配置（从JSON解析）

    Attributes:
        name: 参数名称 (如 "Hum_in")
        addr: Modbus标准地址 (1-based, 如 30002)
        type: 数据类型 ("float", "int16", "int32", "coil", "di")
        unit: 工程单位 (如 "%RH", "℃", "kPa")
        decimal_places: 显示小数位数
        scale: 缩放因子 (原始值 × scale = 工程值)
        alarm_high: 报警上限 (None表示不报警)
        alarm_low: 报警下限
        description: 中文描述
    """

    name: str
    addr: int
    type: str = "float"
    unit: str = ""
    decimal_places: int = 2
    scale: float = 1.0
    alarm_high: Optional[float] = None
    alarm_low: Optional[float] = None
    description: str = ""

    @property
    def register_count(self) -> int:
        """该数据点占用的寄存器数量 — 委托给 RegisterDataType"""
        try:
            from core.enums.data_type_enum import RegisterDataType

            dtype_map = {
                "float": RegisterDataType.HOLDING_FLOAT32,
                "float32": RegisterDataType.HOLDING_FLOAT32,
                "int32": RegisterDataType.HOLDING_INT32,
                "uint32": RegisterDataType.HOLDING_INT32,
                "int16": RegisterDataType.HOLDING_INT16,
                "uint16": RegisterDataType.HOLDING_INT16,
                "coil": RegisterDataType.COIL,
                "di": RegisterDataType.DISCRETE_INPUT,
            }
            dtype = dtype_map.get(self.type.lower())
            if dtype:
                return dtype.get_register_count()
        except Exception:
            pass
        return 2


@dataclass
class DeviceConfig:
    """
    单个设备配置

    Attributes:
        id: 设备唯一标识
        name: 设备名称
        ip: IP地址
        port: 端口号
        unit_id: Modbus从站ID
        timeout_ms: 超时时间(毫秒)
        byte_order: 字节序 ("ABCD"/"BADC"/"CDAB"/"DCBA")
        polling_interval_ms: 轮询周期(毫秒)
        address_base: 地址基数 (1=标准Modbus, 0=pymodbus)
        points: 数据点列表
    """

    id: str
    name: str
    ip: str
    port: int = 502
    unit_id: int = 1
    timeout_ms: int = 3000
    byte_order: str = "CDAB"
    polling_interval_ms: int = 1000
    address_base: int = 1
    points: List[DevicePointConfig] = field(default_factory=list)


@dataclass
class ReadResult:
    """
    单次读取结果（包含原始数据和解析值）

    Attributes:
        device_id: 设备ID
        success: 是否成功
        timestamp: 读取时间戳
        raw_registers: 原始寄存器列表 [reg0, reg1, reg2, ...]
        parsed_data: 解析后的数据 {name: value}
        error_message: 错误信息（失败时）
        read_duration_ms: 读取耗时(毫秒)
        register_count: 读取的寄存器总数
    """

    device_id: str
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    raw_registers: List[int] = field(default_factory=list)
    parsed_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    read_duration_ms: float = 0.0
    register_count: int = 0


# ==================== 核心类：MCGS Modbus Reader ====================


class MCGSModbusReader:
    """
    MCGS Modbus TCP 数据读取器（重构版 v2.0）

    核心功能：
    1. 加载 devices.json 配置文件
    2. 自动计算最优读取范围（最小化通信次数）
    3. 批量读取所有寄存器（单次 FC03 请求）
    4. 按 CDAB 等字节序正确解析浮点数
    5. 三层异常防护机制
    6. 性能统计和日志记录

    支持模式：
    - pymodbus 模式：使用 pymodbus 库（需安装）
    - 内置模式：使用项目自研的 modbus_protocol.py

    Examples:
        >>> reader = MCGSModbusReader("config/devices.json")
        >>> result = reader.read_device("mcgs_1")
        >>> if result.success:
        ...     print(result.parsed_data)
        ...     {'Hum_in': 23.6, 'RH_in': 45.2, ...}
        >>>
        >>> # 循环读取所有设备
        >>> while True:
        ...     all_data = reader.read_all()
        ...     print(all_data)
        ...     time.sleep(1)
    """

    def __init__(self, config_path: Union[str, Path], mode: str = "auto"):
        """
        初始化读取器

        Args:
            config_path: 配置文件路径 (devices.json)
            mode: 运行模式
                - "auto": 自动检测（优先pymodbus，回退内置）
                - "pymodbus": 强制使用 pymodbus
                - "builtin": 强制使用内置协议栈
        """
        self._config_path = Path(config_path)
        self._mode = mode
        self._devices: Dict[str, DeviceConfig] = {}
        self._clients: Dict[str, Any] = {}  # {device_id: client/connection}

        # 性能统计
        self._stats = {
            "total_reads": 0,
            "successful_reads": 0,
            "failed_reads": 0,
            "total_registers_read": 0,
            "total_duration_ms": 0.0,
        }

        # 加载配置
        self.load_config(config_path)

        logger.info("MCGSModbusReader 初始化完成 [设备数=%d, 模式=%s]", len(self._devices), mode)

    # ==================== 任务1: JSON配置加载 ====================

    def load_config(self, path: Union[str, Path]) -> None:
        """
        加载并解析 JSON 配置文件

        配置格式参考: config/devices.json

        Args:
            path: JSON配置文件路径

        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: JSON格式错误
            ValueError: 配置字段缺失或无效
        """
        config_path = Path(path)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"JSON格式错误: {e.msg}", e.doc, e.pos)

        # 解析设备列表（支持新旧两种格式）
        # 旧格式: {"devices": [...]}
        # 新格式(v3.0网关化): {"gateways": [{"id":..., "variables": [...]}]}
        devices_raw = config_data.get("devices", [])
        gateways_raw = config_data.get("gateways", [])

        if not devices_raw and gateways_raw:
            for gw_raw in gateways_raw:
                device = self._parse_gateway_config(gw_raw)
                self._devices[device.id] = device
        elif devices_raw:
            for dev_raw in devices_raw:
                device = self._parse_device_config(dev_raw)
                self._devices[device.id] = device
        else:
            raise ValueError("配置文件中无任何设备定义")

    def _parse_device_config(self, raw: Dict[str, Any]) -> DeviceConfig:
        """解析单个设备配置"""
        # 解析数据点列表
        points_raw = raw.get("points", [])
        points = []
        for p_raw in points_raw:
            point = DevicePointConfig(
                name=p_raw["name"],
                addr=int(p_raw["addr"]),
                type=p_raw.get("type", "float"),
                unit=p_raw.get("unit", ""),
                decimal_places=int(p_raw.get("decimal_places", 2)),
                scale=float(p_raw.get("scale", 1.0)),
                alarm_high=p_raw.get("alarm_high"),
                alarm_low=p_raw.get("alarm_low"),
                description=p_raw.get("description", ""),
            )
            points.append(point)

        return DeviceConfig(
            id=raw["id"],
            name=raw.get("name", raw["id"]),
            ip=raw["ip"],
            port=int(raw.get("port", 502)),
            unit_id=int(raw.get("unit_id", 1)),
            timeout_ms=int(raw.get("timeout_ms", 3000)),
            byte_order=raw.get("byte_order", "CDAB").upper(),
            polling_interval_ms=int(raw.get("polling_interval_ms", 1000)),
            address_base=int(raw.get("address_base", 1)),
            points=points,
        )

    def _parse_gateway_config(self, gw_raw: Dict[str, Any]) -> DeviceConfig:
        """解析网关化格式(v3.0)的网关配置为 DeviceConfig"""
        variables_raw = gw_raw.get("variables", [])
        points = []
        for v_raw in variables_raw:
            point = DevicePointConfig(
                name=v_raw["name"],
                addr=int(v_raw["addr"]),
                type=v_raw.get("type", "uint16"),
                unit=v_raw.get("unit", ""),
                decimal_places=int(v_raw.get("decimal_places", 2)),
                scale=float(1.0),
                alarm_high=v_raw.get("alarm_high"),
                alarm_low=v_raw.get("alarm_low"),
                description=v_raw.get("description", ""),
            )
            points.append(point)

        device = DeviceConfig(
            id=gw_raw["id"],
            name=gw_raw.get("name", gw_raw["id"]),
            ip=gw_raw.get("ip", "127.0.0.1"),
            port=int(gw_raw.get("port", 502)),
            unit_id=int(gw_raw.get("unit_id", 1)),
            timeout_ms=int(gw_raw.get("timeout_ms", 3000)),
            byte_order=gw_raw.get("byte_order", "ABCD").upper(),
            polling_interval_ms=int(gw_raw.get("polling_interval_ms", 1000)),
            address_base=1,
            points=points,
        )

        logger.info(
            "加载设备 [%s] %s@%s:%d [点位=%d, 字节序=%s] (网关模式)",
            device.id,
            device.name,
            device.ip,
            device.port,
            len(device.points),
            device.byte_order,
        )
        return device

    # ==================== 任务2: 自动计算读取范围算法 ====================

    @staticmethod
    def calc_read_range(points: List[DevicePointConfig]) -> Tuple[int, int]:
        """
        ✅ 任务2: 自动计算最优读取范围

        算法说明：
        1. 提取所有点位的起始地址
        2. 找到最小地址作为读取起点
        3. 找到最大地址 + 该点占用寄存器数 作为终点
        4. 计算总寄存器数量 = 终点 - 起点

        优势：
        - 一次请求覆盖所有点位（最小化通信次数）
        - 自动处理不同数据类型的寄存器占用差异
        - 支持非连续地址（中间空隙会被读取但忽略）

        Args:
            points: 数据点配置列表

        Returns:
            (start_address, register_count) 元组
            - start_address: 最小地址（1-based，如30002）
            - register_count: 需要读取的寄存器总数

        Examples:
            >>> points = [
            ...     DevicePointConfig("A", 30002, "float"),  # 占2寄存器
            ...     DevicePointConfig("B", 30004, "float"),  # 占2寄存器
            ...     DevicePointConfig("C", 30006, "float"),  # 占2寄存器
            ... ]
            >>> start, count = MCGSModbusReader.calc_read_range(points)
            >>> print(start, count)
            30002 14  # 从30002开始读14个寄存器(到30015)

        Performance:
            - 时间复杂度: O(n)，n=点位数量
            - 空间复杂度: O(1)
        """
        if not points:
            return (0, 0)

        # 提取所有地址
        addresses = [p.addr for p in points]

        # 计算起点和终点
        start_addr = min(addresses)

        # 终点 = 最大(地址 + 占用寄存器数)
        end_points = [(p.addr + p.register_count) for p in points]
        end_addr = max(end_points)

        # 总寄存器数
        register_count = end_addr - start_addr

        logger.debug(
            "calc_read_range: 起点=%d, 终点=%d, 寄存器数=%d (点位=%d)",
            start_addr,
            end_addr,
            register_count,
            len(points),
        )

        return (start_addr, register_count)

    # ==================== 任务3: 批量读取实现 ====================

    def connect_device(self, device_id: str) -> bool:
        """
        建立设备连接（延迟连接，首次读取时自动调用）

        V04修复: 重复连接时先关闭旧连接，防止资源泄漏

        Args:
            device_id: 设备ID

        Returns:
            是否连接成功
        """
        if device_id not in self._devices:
            logger.error("未知设备ID: %s", device_id)
            return False

        if device_id in self._clients:
            return True  # 已连接

        device = self._devices[device_id]

        try:
            if self._mode in ("auto", "pymodbus"):
                client = self._create_pymodbus_client(device)
                if client is not None:
                    self._clients[device_id] = {
                        "client": client,
                        "type": "pymodbus",
                    }
                    logger.info("设备 [%s] pymodbus 连接成功", device_id)
                    return True

            if self._mode in ("auto", "builtin"):
                conn = self._create_builtin_connection(device)
                if conn is not None:
                    self._clients[device_id] = {
                        "connection": conn,
                        "type": "builtin",
                    }
                    logger.info("设备 [%s] 内置协议栈连接成功", device_id)
                    return True

            logger.error("设备 [%s] 所有连接方式均失败", device_id)
            return False

        except Exception as e:
            logger.error("设备 [%s] 连接异常: %s", device_id, str(e))
            return False

    def disconnect_device(self, device_id: str) -> bool:
        """
        断开单个设备连接

        V04修复: 安全关闭pymodbus连接，防止socket泄漏

        Args:
            device_id: 设备ID

        Returns:
            是否成功断开
        """
        if device_id not in self._clients:
            return True

        client_info = self._clients.pop(device_id)
        try:
            if client_info["type"] == "pymodbus":
                client = client_info["client"]
                try:
                    client.close()
                except Exception:
                    pass
                try:
                    if hasattr(client, "socket") and client.socket:
                        client.socket.close()
                except Exception:
                    pass
            else:
                conn = client_info.get("connection", {})
                driver = conn.get("driver")
                if driver:
                    driver.disconnect()

            logger.info("设备 [%s] 已断开", device_id)
            return True

        except Exception as e:
            logger.warning("断开 [%s] 异常: %s", device_id, str(e))
            return False

    def _handle_comm_failure(self, device_id: str):
        """
        V11: 通信失败处理 — 标记断线并清除连接缓存

        下次 read_device() 时会自动重连
        """
        if device_id in self._clients:
            logger.info("[%s] 通信失败，清除连接缓存（下次自动重连）", device_id)
            try:
                self.disconnect_device(device_id)
            except Exception:
                self._clients.pop(device_id, None)

    def is_device_connected(self, device_id: str) -> bool:
        """检查设备是否已连接"""
        return device_id in self._clients

    def reconnect_device(self, device_id: str) -> bool:
        """
        V11: 手动重连设备

        Args:
            device_id: 设备ID

        Returns:
            是否重连成功
        """
        logger.info("[%s] 尝试重连...", device_id)
        self.disconnect_device(device_id)
        return self.connect_device(device_id)

    def _create_pymodbus_client(self, device: DeviceConfig) -> Optional[Any]:
        """创建 pymodbus TCP客户端"""
        try:
            from pymodbus.client import ModbusTcpClient

            client = ModbusTcpClient(
                host=device.ip,
                port=device.port,
                timeout=device.timeout_ms / 1000.0,
            )

            if client.connect():
                return client
            else:
                logger.warning("pymodbus 连接失败 [%s:%d]", device.ip, device.port)
                return None

        except ImportError:
            logger.debug("pymodbus 未安装，回退到内置协议栈")
            return None
        except Exception as e:
            logger.warning("pymodbus 创建失败: %s", str(e))
            return None

    def _create_builtin_connection(self, device: DeviceConfig) -> Optional[Any]:
        try:
            from core.device.connection_factory import ConnectionFactory
            from core.device.device_models import ConnectionConfig, ProtocolConfig

            factory = ConnectionFactory()
            conn_config = ConnectionConfig(
                connection_type="TCP",
                host=device.ip,
                port=device.port,
                timeout=device.timeout_ms / 1000.0,
            )
            proto_config = ProtocolConfig(
                protocol_type="MODBUS_TCP",
                unit_id=device.unit_id,
            )
            driver, protocol = factory.create(conn_config, proto_config)

            if driver is None or protocol is None:
                return None

            if driver.connect():
                return {"driver": driver, "protocol": protocol}
            else:
                return None

        except Exception as e:
            logger.warning("内置协议栈创建失败: %s", str(e))
            return None

    def read_device(self, device_id: str) -> ReadResult:
        """
        ✅ 任务3+4+5+6: 读取单个设备所有点位（批量+解析+异常处理）

        核心流程：
        1. 建立连接（如果尚未连接）
        2. 计算 optimal 读取范围
        3. 地址转换 (1-based → 0-based for pymodbus)
        4. 发送 FC03 批量读取请求
        5. 第一层检查：通信是否成功
        6. 第二层检查：数据长度是否足够
        7. 第三层保护：逐点解析（try/except）
        8. 格式化输出结果

        Args:
            device_id: 设备ID

        Returns:
            ReadResult 对象（包含原始寄存器和解析数据）
        """
        start_time = time.time()

        # 初始化结果对象
        result = ReadResult(
            device_id=device_id,
            success=False,
            timestamp=datetime.now(),
        )

        try:
            # ===== 前置检查 =====
            if device_id not in self._devices:
                result.error_message = f"未知设备ID: {device_id}"
                logger.error(result.error_message)
                return result

            device = self._devices[device_id]
            points = device.points

            if not points:
                result.error_message = "设备无配置的数据点"
                logger.warning("[%s] %s", device_id, result.error_message)
                result.success = True  # 空配置也算成功
                return result

            # ===== 建立连接 =====
            if not self.connect_device(device_id):
                result.error_message = "无法建立连接"
                logger.error("[%s] %s", device_id, result.error_message)
                return result

            client_info = self._clients[device_id]

            # ===== 任务2: 计算读取范围 =====
            start_addr, reg_count = self.calc_read_range(points)

            if reg_count == 0:
                result.error_message = "无效的读取范围"
                logger.warning("[%s] %s", device_id, result.error_message)
                return result

            # ===== 任务3: 地址转换 + 批量读取 =====
            # ⚠️ 关键：pymodbus 使用 0-based 地址
            # Modbus标准地址 30002 → pymodbus 实际读取 30001
            actual_start = start_addr - device.address_base

            logger.info(
                "[%s] 批量读取 [地址=%d(实际%d), 数量=%d, 字节序=%s]",
                device_id,
                start_addr,
                actual_start,
                reg_count,
                device.byte_order,
            )

            # 根据客户端类型执行读取
            if client_info["type"] == "pymodbus":
                registers = self._read_with_pymodbus(client_info["client"], actual_start, reg_count, device.unit_id)
            else:
                registers = self._read_with_builtin(
                    client_info["connection"],
                    actual_start,
                    reg_count,
                )

            # ===== 第一层：通信检查 =====
            if registers is None:
                result.error_message = "通信失败（无响应或超时）"
                logger.warning("[%s] %s", device_id, result.error_message)
                self._handle_comm_failure(device_id)
                self._update_stats(False, 0, time.time() - start_time)
                return result

            # 更新原始数据
            result.raw_registers = registers
            result.register_count = len(registers)

            # ===== 任务5: 数据解析与映射 =====
            parsed_data = self._parse_all_points(registers, points, start_addr, device.byte_order, device_id)

            result.parsed_data = parsed_data
            result.success = True

            # ===== 性能统计 =====
            duration = (time.time() - start_time) * 1000
            result.read_duration_ms = duration
            self._update_stats(True, len(registers), duration / 1000.0)

            logger.info(
                "[%s] 读取成功 [寄存器=%d个, 点位=%d个, 耗时=%.1fms]",
                device_id,
                len(registers),
                len(parsed_data),
                duration,
            )

            # 打印详细数据（便于调试）
            self._log_parsed_data(device_id, parsed_data, registers)

            return result

        except Exception as e:
            # 兜底异常捕获
            result.error_message = f"未预期的异常: {str(e)}"
            logger.error("[%s] %s\n%s", device_id, result.error_message, traceback.format_exc())
            self._update_stats(False, 0, time.time() - start_time)
            return result

    def _read_with_pymodbus(self, client, start: int, count: int, unit_id: int) -> Optional[List[int]]:
        """使用 pymodbus 执行 FC03 读取"""
        try:
            response = client.read_holding_registers(start, count=count, device_id=unit_id)

            if response.isError():
                logger.warning("pymodbus 读取错误: %s", response)
                return None

            return list(response.registers)

        except Exception as e:
            logger.error("pymodbus 异常: %s", str(e))
            return None

    def _read_with_builtin(self, conn_info: dict, start: int, count: int) -> Optional[List[int]]:
        """使用内置协议栈执行 FC03 读取"""
        try:
            protocol = conn_info["protocol"]
            result = protocol.read_holding_registers(start, count)

            if result is None:
                logger.warning("内置协议栈读取返回None")
                return None

            return result

        except Exception as e:
            logger.error("内置协议栈异常: %s", str(e))
            return None

    # ==================== 数据解析与映射 ====================

    def _parse_with_value_parser(
        self,
        registers: List[int],
        offset: int,
        data_type_str: str,
        byte_order_str: str,
    ) -> Optional[Union[float, int, bool]]:
        """
        委托 ModbusValueParser 解析 — 消除重复解析逻辑

        Step 8: 替代 _parse_float/_parse_int16/_parse_int32
        """
        try:
            from core.communication.modbus_value_parser import ModbusValueParser
            from core.protocols.byte_order_config import ByteOrderConfig
            from core.enums.data_type_enum import RegisterDataType

            dtype_map = {
                "float": RegisterDataType.HOLDING_FLOAT32,
                "float32": RegisterDataType.HOLDING_FLOAT32,
                "int16": RegisterDataType.HOLDING_INT16,
                "uint16": RegisterDataType.HOLDING_INT16,
                "int32": RegisterDataType.HOLDING_INT32,
                "uint32": RegisterDataType.HOLDING_INT32,
                "coil": RegisterDataType.COIL,
                "di": RegisterDataType.DISCRETE_INPUT,
            }

            dtype = dtype_map.get(data_type_str.lower())
            if dtype is None:
                logger.warning("未知数据类型 '%s'", data_type_str)
                return None

            byte_order = ByteOrderConfig.from_string(byte_order_str)
            parser = ModbusValueParser(byte_order=byte_order)
            return parser.parse(registers, offset, dtype)

        except Exception as e:
            logger.error("ModbusValueParser解析异常: %s", e)
            return None

    def _parse_all_points(
        self, registers: List[int], points: List[DevicePointConfig], start_addr: int, byte_order: str, device_id: str
    ) -> Dict[str, Any]:
        """
        ✅ 任务5: 解析所有数据点并映射为字典

        对每个数据点：
        1. 计算偏移量 offset = point.addr - start_addr
        2. 提取对应的寄存器子集
        3. 根据数据类型调用相应解析方法
        4. 应用缩放因子和小数位格式化
        5. 检查报警阈值

        Args:
            registers: 原始寄存器列表
            points: 数据点配置列表
            start_addr: 读取起始地址
            byte_order: 字节序
            device_id: 设备ID（用于日志）

        Returns:
            {参数名: 格式化后的字符串} 字典
        """
        parsed = {}

        for point in points:
            try:
                # 计算偏移量
                offset = point.addr - start_addr

                # V14修复: 偏移越界保护 — 负偏移或超出寄存器范围
                if offset < 0:
                    logger.warning(
                        "[%s] 偏移越界(负偏移) [%s] offset=%d, start=%d, point.addr=%d",
                        device_id,
                        point.name,
                        offset,
                        start_addr,
                        point.addr,
                    )
                    parsed[point.name] = "OFFSET_ERR"
                    continue

                # 第二层：检查寄存器是否足够
                needed = point.register_count
                if offset + needed > len(registers):
                    logger.warning(
                        "[%s] 寄存器不足 [%s] need=%d have=%d", device_id, point.name, needed, len(registers) - offset
                    )
                    parsed[point.name] = "N/A"
                    continue

                # 提取该点的寄存器

                # 第三层：根据类型解析 — 委托给 ModbusValueParser
                raw_value = self._parse_with_value_parser(registers, offset, point.type, byte_order)

                if raw_value is None:
                    parsed[point.name] = "PARSE_ERR"
                    continue

                # 应用缩放和格式化
                if raw_value is not None:
                    scaled_value = raw_value * point.scale

                    # V15修复: 缩放后NaN/Inf检查
                    if isinstance(scaled_value, float) and (math.isnan(scaled_value) or math.isinf(scaled_value)):
                        logger.warning(
                            "[%s] 缩放后值非法 [%s]: raw=%.4f, scale=%.4f",
                            device_id,
                            point.name,
                            raw_value,
                            point.scale,
                        )
                        parsed[point.name] = "INVALID"
                        continue

                    # 格式化显示值
                    if point.type.lower() in ("coil", "di"):
                        formatted = "ON" if scaled_value else "OFF"
                    else:
                        formatted = f"{scaled_value:.{point.decimal_places}f}"

                        # 添加单位
                        if point.unit:
                            formatted += f" {point.unit}"

                    parsed[point.name] = formatted

                    # 检查报警
                    self._check_alarm(point, scaled_value, device_id)

                else:
                    parsed[point.name] = "PARSE_ERR"

            except Exception as e:
                # 第三层防护：单个点解析失败不影响其他点
                logger.error("[%s] 解析异常 [%s]: %s", device_id, point.name, str(e))
                parsed[point.name] = "EXCEPTION"

        return parsed

    def _check_alarm(self, point: DevicePointConfig, value: float, device_id: str):
        """检查报警阈值"""
        if point.alarm_high is not None and value > point.alarm_high:
            logger.warning("⚠️ [%s] 报警-高限 [%s]: %.2f > %.2f", device_id, point.name, value, point.alarm_high)

        if point.alarm_low is not None and value < point.alarm_low:
            logger.warning("⚠️ [%s] 报警-低限 [%s]: %.2f < %.2f", device_id, point.name, value, point.alarm_low)

    def _log_parsed_data(self, device_id: str, data: dict, registers: List[int]):
        """打印解析结果（调试用）"""
        logger.debug("[%s] 原始寄存器: %s", device_id, registers)

        log_lines = [f"[{device_id}] 解析结果:"]
        for name, value in data.items():
            log_lines.append(f"  {name}: {value}")

        logger.debug("\n".join(log_lines))

    # ==================== 任务6: 三层异常防护增强 ====================

    def read_all(self) -> Dict[str, Dict[str, Any]]:
        """
        读取所有设备的主入口方法

        对每个设备调用 read_device()，
        并汇总结果为嵌套字典。

        Returns:
            {device_id: {param_name: value}} 或
            {device_id: None} （失败的设备）

        Examples:
            >>> reader = MCGSModbusReader("config/devices.json")
            >>> data = reader.read_all()
            >>> print(data)
            {'mcgs_1': {'Hum_in': '23.6 %RH', 'AT_in': '26.1 ℃', ...}}
        """
        all_results = {}

        for device_id in self._devices:
            result = self.read_device(device_id)

            if result.success:
                all_results[device_id] = result.parsed_data
            else:
                all_results[device_id] = None
                logger.error("[%s] 读取失败: %s", device_id, result.error_message)

        return all_results

    def read_all_loop(self, interval: float = 1.0, callback=None):
        """
        循环读取所有设备（用于持续监控）

        Args:
            interval: 读取间隔（秒）
            callback: 回调函数 (data: dict) -> None
        """
        logger.info("开始循环读取 [间隔=%.1fs, 设备=%d]", interval, len(self._devices))

        while True:
            try:
                data = self.read_all()

                if callback:
                    callback(data)
                else:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                    for dev_id, values in data.items():
                        if values:
                            print(f"  [{dev_id}]")
                            for name, val in values.items():
                                print(f"    {name}: {val}")

                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("用户中断循环读取")
                break
            except Exception as e:
                logger.error("循环读取异常: %s", str(e))
                time.sleep(interval)

    # ==================== 辅助方法 ====================

    def _update_stats(self, success: bool, reg_count: int, duration: float):
        """更新性能统计"""
        self._stats["total_reads"] += 1
        self._stats["total_registers_read"] += reg_count
        self._stats["total_duration_ms"] += duration * 1000

        if success:
            self._stats["successful_reads"] += 1
        else:
            self._stats["failed_reads"] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        total = self._stats["total_reads"]
        if total == 0:
            return self._stats.copy()

        avg_duration = self._stats["total_duration_ms"] / total if total > 0 else 0
        success_rate = self._stats["successful_reads"] / total * 100 if total > 0 else 0

        return {
            **self._stats,
            "avg_duration_ms": round(avg_duration, 2),
            "success_rate_percent": round(success_rate, 2),
        }

    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        """获取指定设备的配置"""
        return self._devices.get(device_id)

    def list_devices(self) -> List[str]:
        """列出所有已加载的设备ID"""
        return list(self._devices.keys())

    def disconnect_all(self):
        """断开所有设备连接"""
        device_ids = list(self._clients.keys())
        for device_id in device_ids:
            self.disconnect_device(device_id)

    def __del__(self):
        """析构时自动断开连接 — V05修复: 保护解释器关闭时的异常"""
        try:
            self.disconnect_all()
        except Exception:
            pass


# ==================== 便捷函数 ====================


def create_mcgsm_reader(config_path: str = "config/devices.json") -> MCGSModbusReader:
    """
    创建 MCGS Modbus 读取器的便捷函数

    Args:
        config_path: 配置文件路径（默认 config/devices.json）

    Returns:
        已初始化的 MCGSModbusReader 实例

    Examples:
        >>> reader = create_mcgsm_reader()
        >>> data = reader.read_all()
        >>> print(data)
    """
    return MCGSModbusReader(config_path)


if __name__ == "__main__":
    # 快速测试入口
    print("=" * 60)
    print("MCGS Modbus Reader v2.0 - 测试模式")
    print("=" * 60)

    try:
        reader = create_mcgsm_reader()
        print(f"\n✅ 配置加载成功")
        print(f"   设备列表: {reader.list_devices()}")

        # 读取一次测试
        print("\n📡 开始读取...")
        data = reader.read_all()

        print("\n📊 读取结果:")
        for dev_id, values in data.items():
            print(f"\n  [{dev_id}]")
            if values:
                for name, val in values.items():
                    print(f"    {name}: {val}")
            else:
                print("    ❌ 读取失败")

        # 性能统计
        stats = reader.get_statistics()
        print(f"\n📈 性能统计:")
        print(f"   总读取次数: {stats['total_reads']}")
        print(f"   成功率: {stats['success_rate_percent']}%")
        print(f"   平均耗时: {stats['avg_duration_ms']:.2f}ms")

        reader.disconnect_all()
        print("\n✅ 测试完成")

    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback

        traceback.print_exc()
