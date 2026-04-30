# -*- coding: utf-8 -*-
"""
MCGS TCP Server 模拟器 (v2.0 网关化重构版)

规范要求: 保留并重构 Simulator 类，使其能模拟 MCGS 的 TCP 响应报文，
确保脱机状态下全链路可演示。

核心变更 (v1.0 → v2.0):
- v1.0: 仅模拟寄存器值，通过 data_updated 信号直接推送
- v2.0: 模拟完整的 MCGS TCP Server，监听端口，响应 Modbus TCP 请求

架构:
    MCGSSimulator (TCP Server)
    ├── 监听 127.0.0.1:5020 (可配置)
    ├── 接收 Modbus TCP 请求 (FC03/FC04/FC08)
    ├── 构造合法的 Modbus TCP 响应报文
    └── 通过 DataBus 发布数据（与真实网关完全一致的数据流）

数据流（与真实 MCGS 网关一致）:
    GatewayEngine → TCPDriver → MCGSSimulator:5020
                                       ↓
                               Modbus TCP 响应报文
                                       ↓
                           TCPDriver.data_received
                                       ↓
                           ModbusProtocol.parse()
                                       ↓
                           DataBus.publish_device_data()

使用方式:
    sim = MCGSSimulator(port=5020)
    sim.add_variable("Hum_in", 30002, "float", deadband=0.5)
    sim.add_variable("AT_in", 30004, "float", deadband=0.1)
    sim.start()

    # 在 devices.json 中配置:
    # "ip": "127.0.0.1", "port": 5020

    sim.stop()
"""

import logging
import math
import random
import socket
import struct
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from core.foundation.data_bus import DataBus
from core.device.gateway_model import VariablePoint

logger = logging.getLogger(__name__)


class SimulatedVariable:
    """模拟变量点 — 生成带波动的仿真数据"""

    def __init__(
        self,
        name: str,
        addr: int,
        data_type: str = "float",
        initial_value: float = 0.0,
        min_value: float = -100.0,
        max_value: float = 100.0,
        noise_amplitude: float = 0.5,
        wave_amplitude: float = 5.0,
        wave_period: float = 60.0,
    ):
        self.name = name
        self.addr = addr
        self.data_type = data_type
        self.initial_value = initial_value
        self.min_value = min_value
        self.max_value = max_value
        self.noise_amplitude = noise_amplitude
        self.wave_amplitude = wave_amplitude
        self.wave_period = wave_period
        self._base_time = time.monotonic()

    def generate_value(self) -> float:
        elapsed = time.monotonic() - self._base_time
        wave = math.sin(2 * math.pi * elapsed / self.wave_period) * self.wave_amplitude
        noise = random.uniform(-self.noise_amplitude, self.noise_amplitude)
        value = self.initial_value + wave + noise
        return max(self.min_value, min(self.max_value, value))

    def to_registers(self, byte_order: str = "CDAB") -> List[int]:
        """将浮点值转换为 Modbus 寄存器值（2个寄存器 = 4字节）"""
        value = self.generate_value()

        if self.data_type == "float":
            raw_bytes = struct.pack(">f", value)

            if byte_order == "CDAB":
                raw_bytes = raw_bytes[2:4] + raw_bytes[0:2]
            elif byte_order == "BADC":
                raw_bytes = raw_bytes[1:2] + raw_bytes[0:1] + raw_bytes[3:4] + raw_bytes[2:3]
            elif byte_order == "DCBA":
                raw_bytes = raw_bytes[3:4] + raw_bytes[2:3] + raw_bytes[1:2] + raw_bytes[0:1]

            reg_hi = struct.unpack(">H", raw_bytes[0:2])[0]
            reg_lo = struct.unpack(">H", raw_bytes[2:4])[0]
            return [reg_hi, reg_lo]

        elif self.data_type == "int16":
            int_val = int(value)
            return [max(0, min(65535, int_val & 0xFFFF))]

        elif self.data_type == "uint16":
            return [max(0, min(65535, int(value) & 0xFFFF))]

        return [0, 0]


class MCGSSimulator(QObject):
    """
    MCGS TCP Server 模拟器 (v2.0)

    模拟 MCGS 触摸屏的 Modbus TCP Server 行为:
    1. 监听指定端口，接受客户端连接
    2. 解析 Modbus TCP 请求报文
    3. 构造合法的 Modbus TCP 响应报文
    4. 支持仿真数据波动（正弦+噪声）
    5. 通过 DataBus 发布数据（与真实网关一致）

    支持的功能码:
    - FC03 (0x03): 读保持寄存器
    - FC04 (0x04): 读输入寄存器
    - FC08 (0x08): 诊断（心跳响应）
    """

    simulator_started = Signal(str, int)
    simulator_stopped = Signal(str)
    simulator_error = Signal(str, str)
    simulator_data_published = Signal(str, dict)

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 5020
    DEFAULT_UNIT_ID = 1

    FC_READ_HOLDING = 0x03
    FC_READ_INPUT = 0x04
    FC_DIAGNOSTICS = 0x08

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        unit_id: int = DEFAULT_UNIT_ID,
        byte_order: str = "CDAB",
        parent=None,
    ):
        super().__init__(parent)

        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._byte_order = byte_order

        self._variables: Dict[str, SimulatedVariable] = {}
        self._addr_map: Dict[int, str] = {}

        self._server_socket: Optional[socket.socket] = None
        self._client_sockets: List[socket.socket] = []
        self._is_running = False
        self._accept_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._request_count = 0
        self._error_count = 0

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def is_running(self) -> bool:
        return self._is_running

    def add_variable(
        self,
        name: str,
        addr: int,
        data_type: str = "float",
        initial_value: float = 0.0,
        min_value: float = -100.0,
        max_value: float = 100.0,
        noise_amplitude: float = 0.5,
        wave_amplitude: float = 5.0,
        wave_period: float = 60.0,
    ) -> None:
        var = SimulatedVariable(
            name=name,
            addr=addr,
            data_type=data_type,
            initial_value=initial_value,
            min_value=min_value,
            max_value=max_value,
            noise_amplitude=noise_amplitude,
            wave_amplitude=wave_amplitude,
            wave_period=wave_period,
        )
        self._variables[name] = var
        self._addr_map[addr] = name

    def add_variable_from_point(self, vp: VariablePoint) -> None:
        """从 VariablePoint 配置添加模拟变量"""
        defaults = {
            "float": (25.0, -50.0, 150.0, 0.5, 5.0),
            "int16": (100, 0, 1000, 1.0, 50.0),
            "uint16": (100, 0, 1000, 1.0, 50.0),
        }
        init, mn, mx, noise, wave = defaults.get(vp.type, (25.0, -50.0, 150.0, 0.5, 5.0))

        if "Hum" in vp.name:
            init, mn, mx, noise, wave = 55.0, 0.0, 100.0, 0.3, 3.0
        elif "AT" in vp.name or "Temp" in vp.name:
            init, mn, mx, noise, wave = 25.0, -10.0, 60.0, 0.1, 2.0

        self.add_variable(
            name=vp.name,
            addr=vp.addr,
            data_type=vp.type,
            initial_value=init,
            min_value=mn,
            max_value=mx,
            noise_amplitude=noise,
            wave_amplitude=wave,
        )

    def load_from_gateway_config(self, config: dict) -> None:
        """从 devices.json 网关配置加载变量"""
        for var_data in config.get("variables", []):
            vp = VariablePoint.from_dict(var_data)
            self.add_variable_from_point(vp)

    def start(self) -> bool:
        if self._is_running:
            return True

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.settimeout(1.0)
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(5)

            self._is_running = True

            self._accept_thread = threading.Thread(
                target=self._accept_loop,
                name=f"MCGSSim-{self._port}",
                daemon=True,
            )
            self._accept_thread.start()

            self.simulator_started.emit(self._host, self._port)
            logger.info(
                "MCGS模拟器已启动 [%s:%d] 变量=%d",
                self._host, self._port, len(self._variables),
            )
            return True

        except Exception as e:
            self.simulator_error.emit("start", str(e))
            logger.error("MCGS模拟器启动失败: %s", e)
            return False

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False

        with self._lock:
            for client in self._client_sockets:
                try:
                    client.close()
                except Exception:
                    pass
            self._client_sockets.clear()

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=3.0)
            self._accept_thread = None

        self.simulator_stopped.emit(f"{self._host}:{self._port}")
        logger.info("MCGS模拟器已停止")

    def _accept_loop(self):
        while self._is_running:
            try:
                client_socket, addr = self._server_socket.accept()
                client_socket.settimeout(5.0)
                with self._lock:
                    self._client_sockets.append(client_socket)

                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr),
                    name=f"MCGSSim-Client-{addr[1]}",
                    daemon=True,
                )
                client_thread.start()

            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                if self._is_running:
                    logger.debug("接受连接异常: %s", e)

    def _handle_client(self, client_socket: socket.socket, addr: Tuple):
        logger.info("模拟器接受连接: %s:%d", addr[0], addr[1])

        while self._is_running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break

                self._request_count += 1
                response = self._process_request(data)

                if response:
                    client_socket.sendall(response)

            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break
            except Exception as e:
                self._error_count += 1
                if self._is_running:
                    logger.debug("处理客户端请求异常: %s", e)
                break

        with self._lock:
            if client_socket in self._client_sockets:
                self._client_sockets.remove(client_socket)

        try:
            client_socket.close()
        except Exception:
            pass

        logger.info("模拟器客户端断开: %s:%d", addr[0], addr[1])

    def _process_request(self, data: bytes) -> Optional[bytes]:
        """解析 Modbus TCP 请求并构造响应"""
        if len(data) < 7:
            return None

        trans_id = struct.unpack(">H", data[0:2])[0]
        protocol_id = struct.unpack(">H", data[2:4])[0]
        length = struct.unpack(">H", data[4:6])[0]
        unit_id = data[6]

        if protocol_id != 0:
            return None

        if unit_id != self._unit_id:
            return self._build_exception_response(trans_id, unit_id, data[7], 0x02)

        if len(data) < 8:
            return None

        fc = data[7]

        if fc == self.FC_READ_HOLDING or fc == self.FC_READ_INPUT:
            return self._handle_read_request(trans_id, unit_id, fc, data)
        elif fc == self.FC_DIAGNOSTICS:
            return self._handle_diagnostics_request(trans_id, unit_id, data)
        else:
            return self._build_exception_response(trans_id, unit_id, fc, 0x01)

    def _handle_read_request(self, trans_id: int, unit_id: int, fc: int, data: bytes) -> bytes:
        """处理 FC03/FC04 读寄存器请求"""
        start_addr = struct.unpack(">H", data[8:10])[0]
        reg_count = struct.unpack(">H", data[10:12])[0]

        register_data = bytearray()
        parsed_data = {}

        for i in range(reg_count):
            current_addr = start_addr + i
            var_name = self._addr_map.get(current_addr + 1)

            if var_name and var_name in self._variables:
                var = self._variables[var_name]
                regs = var.to_registers(self._byte_order)

                addr_offset = current_addr - (var.addr - 1)
                if 0 <= addr_offset < len(regs):
                    register_data += struct.pack(">H", regs[addr_offset])
                else:
                    register_data += struct.pack(">H", 0)

                if addr_offset == 0 and var.data_type == "float":
                    parsed_data[var_name] = {
                        "value": var.generate_value(),
                        "unit": "",
                        "quality": 0,
                    }
            else:
                register_data += struct.pack(">H", random.randint(0, 100))

        byte_count = len(register_data)

        response = struct.pack(">HHH", trans_id, 0, 3 + byte_count)
        response += bytes([unit_id, fc, byte_count])
        response += register_data

        if parsed_data:
            gateway_id = f"sim_{self._port}"
            DataBus.instance().publish_device_data(gateway_id, parsed_data)
            self.simulator_data_published.emit(gateway_id, parsed_data)

        return response

    def _handle_diagnostics_request(self, trans_id: int, unit_id: int, data: bytes) -> bytes:
        """处理 FC08 诊断请求（心跳响应）"""
        if len(data) < 12:
            return self._build_exception_response(trans_id, unit_id, self.FC_DIAGNOSTICS, 0x02)

        sub_function = struct.unpack(">H", data[8:10])[0]

        response = struct.pack(">HHH", trans_id, 0, 6)
        response += bytes([unit_id, self.FC_DIAGNOSTICS])
        response += struct.pack(">H", sub_function)
        response += data[10:12]

        return response

    def _build_exception_response(self, trans_id: int, unit_id: int, fc: int, exception_code: int) -> bytes:
        """构造异常响应"""
        response = struct.pack(">HHH", trans_id, 0, 3)
        response += bytes([unit_id, fc | 0x80, exception_code])
        return response

    def get_statistics(self) -> dict:
        return {
            "host": self._host,
            "port": self._port,
            "is_running": self._is_running,
            "variable_count": len(self._variables),
            "client_count": len(self._client_sockets),
            "request_count": self._request_count,
            "error_count": self._error_count,
        }

    def __repr__(self) -> str:
        return (
            f"MCGSSimulator({self._host}:{self._port}, "
            f"vars={len(self._variables)}, "
            f"running={self._is_running})"
        )


class LegacySimulator(QObject):
    """
    旧版模拟器兼容层 (v1.0)

    保留旧的寄存器级模拟接口，供不需要 TCP Server 的场景使用。
    新代码应使用 MCGSSimulator。
    """

    data_updated = Signal(dict)
    connected = Signal()
    disconnected = Signal()

    def __init__(self, device_config: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self._device_config = device_config or {}
        self._is_connected = False
        self._is_running = False
        self._simulation_thread: Optional[threading.Thread] = None
        self._register_values: Dict[int, int] = {}
        self._base_time = time.time()
        self._lock = threading.Lock()
        self._init_simulated_registers()

    def _init_simulated_registers(self):
        self._register_values[0] = 250
        self._register_values[1] = 100
        self._register_values[2] = 500
        self._register_values[3] = 1
        self._register_values[4] = 0

    def connect(self) -> bool:
        if self._is_connected:
            return True

        with self._lock:
            self._is_connected = True
            self._is_running = True
            self._base_time = time.time()

            self._simulation_thread = threading.Thread(
                target=self._simulation_loop,
                name="LegacySimulator",
                daemon=True,
            )
            self._simulation_thread.start()

        self.connected.emit()
        logger.info("旧版模拟器已启动")
        return True

    def disconnect(self):
        with self._lock:
            self._is_running = False
            self._is_connected = False

            if self._simulation_thread and self._simulation_thread.is_alive():
                self._simulation_thread.join(timeout=2.0)
                self._simulation_thread = None

        self.disconnected.emit()
        logger.info("旧版模拟器已停止")

    def cleanup(self):
        try:
            self.disconnect()
            self._register_values.clear()
        except Exception as e:
            logger.warning("旧版模拟器清理时出错: %s", e)

    def is_connected(self) -> bool:
        return self._is_connected

    def read_registers(self, address: int, count: int) -> List[int]:
        result = []
        for i in range(count):
            addr = address + i
            value = self._simulate_register_value(addr)
            result.append(value)
        return result

    def _simulate_register_value(self, address: int) -> int:
        base_value = self._register_values.get(address, 0)
        elapsed = time.time() - self._base_time

        if address == 0:
            variation = math.sin(elapsed * 0.5) * 20 + random.uniform(-1, 1)
            value = int(base_value + variation)
        elif address == 1:
            variation = math.sin(elapsed * 0.2) * 10 + random.uniform(-0.5, 0.5)
            value = int(base_value + variation)
        elif address == 2:
            variation = abs(math.sin(elapsed * 2)) * 100 + random.uniform(-2, 2)
            value = int(base_value + variation)
        elif address == 3:
            value = base_value
        elif address == 4:
            value = 1 if random.random() < 0.01 else 0
        else:
            value = base_value + random.randint(-5, 5)

        return max(0, min(65535, value))

    def write_registers(self, address: int, values: List[int]) -> bool:
        for i, val in enumerate(values):
            self._register_values[address + i] = val
        return True

    def _simulation_loop(self):
        while self._is_running:
            try:
                data = {
                    "registers": {
                        addr: self._simulate_register_value(addr)
                        for addr in self._register_values.keys()
                    },
                    "timestamp": time.time(),
                }
                self.data_updated.emit(data)
                time.sleep(1.0)
            except Exception as e:
                if self._is_running:
                    logger.error("旧版模拟循环错误: %s", e)
                    time.sleep(1.0)


Simulator = MCGSSimulator
