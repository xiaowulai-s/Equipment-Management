# -*- coding: utf-8 -*-
"""
网关通信引擎（Gateway Engine）

规范控制点④核心实现:
- MCGS触摸屏为唯一TCP Server，上位机为Client
- DeviceManager支持多网关并发管理（每个网关对应一个长连接线程）
- 禁止频繁connect，保持长连接

架构:
    GatewayEngine
    ├── GatewayConnection[0]  ← 网关1 (独立线程)
    │   ├── TCPDriver         ← 通信层
    │   ├── ModbusProtocol    ← 协议层
    │   ├── HeartbeatManager  ← 心跳管理
    │   └── ReconnectPolicy   ← 重连策略
    ├── GatewayConnection[1]  ← 网关2 (独立线程)
    │   └── ...
    └── ...

数据流（规范控制点⑥ — 单向数据流）:
    GatewayEngine.poll_gateway()
        → TCPDriver.send_data()          [通信线程]
        → TCPDriver.data_received        [通信线程]
        → ModbusProtocol.parse()         [通信线程]
        → DataBus.publish_device_data()  [通信线程 → UI线程 via Signal]

线程模型（规范控制点8️⃣）:
    - 通信线程: 每个网关独立的轮询线程
    - 解析线程: 在通信线程中同步执行（Modbus解析是CPU轻量操作）
    - UI线程: 通过DataBus Signal/Slot异步更新
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from core.engine.reconnect_policy import ReconnectPolicy
from core.engine.heartbeat_manager import HeartbeatManager, HeartbeatState
from core.foundation.data_bus import DataBus

logger = logging.getLogger(__name__)


class GatewayState(IntEnum):
    IDLE = 0
    CONNECTING = 1
    CONNECTED = 2
    POLLING = 3
    RECONNECTING = 4
    DISCONNECTING = 5
    ERROR = 6


@dataclass
class GatewayConfig:
    """
    网关配置模型

    对应 devices.json 中的单个网关条目
    """
    id: str
    name: str
    ip: str
    port: int = 502
    unit_id: int = 1
    timeout_ms: int = 3000
    byte_order: str = "CDAB"
    polling_interval_ms: int = 1000
    heartbeat_interval_ms: int = 10000
    max_heartbeat_failures: int = 3
    reconnect: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "initial_delay_ms": 1000,
        "max_delay_ms": 30000,
        "multiplier": 2.0,
        "max_attempts": 10,
    })
    variables: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'GatewayConfig':
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            ip=data.get("ip", "127.0.0.1"),
            port=data.get("port", 502),
            unit_id=data.get("unit_id", 1),
            timeout_ms=data.get("timeout_ms", 3000),
            byte_order=data.get("byte_order", "CDAB"),
            polling_interval_ms=data.get("polling_interval_ms", 1000),
            heartbeat_interval_ms=data.get("heartbeat_interval_ms", 10000),
            max_heartbeat_failures=data.get("max_heartbeat_failures", 3),
            reconnect=data.get("reconnect", {}),
            variables=data.get("variables", []),
        )


class GatewayConnection:
    """
    单个网关的连接管理（运行在独立线程中）

    职责:
    1. 管理 TCPDriver + ModbusProtocol 生命周期
    2. 执行轮询循环
    3. 处理心跳失败 → 重置连接
    4. 处理连接断开 → 指数退避重连

    线程安全:
    - 所有公共方法通过 _lock 保护
    - 轮询循环在独立线程中运行
    - 通过 DataBus Signal 跨线程通知
    """

    def __init__(self, config: GatewayConfig):
        self._config = config
        self._state = GatewayState.IDLE
        self._driver = None
        self._protocol = None
        self._heartbeat_mgr = HeartbeatManager(
            gateway_id=config.id,
            max_failures=config.max_heartbeat_failures,
            check_interval_ms=config.heartbeat_interval_ms,
        )
        self._reconnect_policy = ReconnectPolicy.from_dict(
            config.reconnect if config.reconnect else {}
        )

        self._poll_thread: Optional[threading.Thread] = None
        self._is_polling = False
        self._lock = threading.RLock()

        self._poll_count = 0
        self._error_count = 0
        self._last_poll_time: Optional[float] = None
        self._last_error: str = ""

        self._on_data_callback: Optional[Callable] = None
        self._on_state_changed_callback: Optional[Callable] = None
        self._on_error_callback: Optional[Callable] = None

        self._heartbeat_mgr.connection_reset_required.connect(
            self._on_heartbeat_reset_required
        )

    @property
    def gateway_id(self) -> str:
        return self._config.id

    @property
    def config(self) -> GatewayConfig:
        return self._config

    @property
    def state(self) -> GatewayState:
        with self._lock:
            return self._state

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._state in (GatewayState.CONNECTED, GatewayState.POLLING)

    def set_callbacks(
        self,
        on_data: Optional[Callable] = None,
        on_state_changed: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        self._on_data_callback = on_data
        self._on_state_changed_callback = on_state_changed
        self._on_error_callback = on_error

    def connect(self) -> bool:
        with self._lock:
            if self._state in (GatewayState.CONNECTED, GatewayState.POLLING):
                return True

            self._set_state(GatewayState.CONNECTING)

        try:
            from core.communication.tcp_driver import TCPDriver
            from core.protocols.modbus_protocol import ModbusProtocol
            from core.protocols.byte_order_config import ByteOrderConfig

            driver = TCPDriver(self._config.ip, self._config.port)
            driver.set_unit_id(self._config.unit_id)
            driver.set_heartbeat_interval(self._config.heartbeat_interval_ms)

            if not driver.connect():
                with self._lock:
                    self._set_state(GatewayState.ERROR)
                    self._last_error = "TCP连接失败"
                return False

            protocol = ModbusProtocol()
            protocol.set_driver(driver)

            byte_order = ByteOrderConfig.from_string(self._config.byte_order)
            if hasattr(protocol, 'set_byte_order'):
                protocol.set_byte_order(byte_order)

            if not protocol.initialize():
                driver.disconnect()
                with self._lock:
                    self._set_state(GatewayState.ERROR)
                    self._last_error = "协议初始化失败"
                return False

            with self._lock:
                self._driver = driver
                self._protocol = protocol
                self._set_state(GatewayState.CONNECTED)
                self._reconnect_policy.reset()
                self._error_count = 0

            self._heartbeat_mgr.reset()
            self._heartbeat_mgr.start()

            DataBus.instance().publish_device_connected(self._config.id)

            logger.info(
                "网关连接成功 [%s] %s:%d",
                self._config.id, self._config.ip, self._config.port,
            )
            return True

        except Exception as e:
            with self._lock:
                self._set_state(GatewayState.ERROR)
                self._last_error = str(e)

            logger.error("网关连接异常 [%s]: %s", self._config.id, e)
            return False

    def disconnect(self):
        with self._lock:
            if self._state == GatewayState.IDLE:
                return

            self._set_state(GatewayState.DISCONNECTING)

        self.stop_polling()
        self._heartbeat_mgr.stop()

        with self._lock:
            if self._protocol is not None:
                try:
                    self._protocol = None
                except Exception:
                    pass

            if self._driver is not None:
                try:
                    self._driver.disconnect()
                except Exception as e:
                    logger.debug("断开驱动时出错 [%s]: %s", self._config.id, e)
                self._driver = None

            self._set_state(GatewayState.IDLE)

        DataBus.instance().publish_device_disconnected(self._config.id)
        logger.info("网关已断开 [%s]", self._config.id)

    def start_polling(self):
        with self._lock:
            if self._state != GatewayState.CONNECTED:
                logger.warning("网关未连接，无法启动轮询 [%s]", self._config.id)
                return

            if self._is_polling:
                return

            self._is_polling = True
            self._set_state(GatewayState.POLLING)

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            name=f"GatewayPoll-{self._config.id}",
            daemon=True,
        )
        self._poll_thread.start()
        logger.info("网关轮询已启动 [%s] 间隔=%dms", self._config.id, self._config.polling_interval_ms)

    def stop_polling(self):
        with self._lock:
            if not self._is_polling:
                return
            self._is_polling = False

        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=3.0)

        with self._lock:
            self._poll_thread = None
            if self._state == GatewayState.POLLING:
                self._set_state(GatewayState.CONNECTED)

        logger.info("网关轮询已停止 [%s]", self._config.id)

    def poll_once(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._state not in (GatewayState.CONNECTED, GatewayState.POLLING):
                return None

            driver = self._driver
            protocol = self._protocol

        if driver is None or protocol is None:
            return None

        try:
            data = protocol.poll_data()
            self._poll_count += 1
            self._last_poll_time = time.monotonic()

            if data:
                self._notify_data(data)
                DataBus.instance().publish_device_data(self._config.id, data)

            return data

        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error("轮询异常 [%s]: %s", self._config.id, e)
            self._notify_error(str(e))
            DataBus.instance().publish_comm_error(self._config.id, str(e))
            return None

    def force_reset(self):
        """
        强制重置连接（心跳3次失败后调用）

        流程: 停止轮询 → 断开驱动 → 重连
        """
        logger.warning("强制重置网关连接 [%s]", self._config.id)

        self.stop_polling()
        self._heartbeat_mgr.stop()

        with self._lock:
            if self._driver is not None:
                try:
                    self._driver.disconnect()
                except Exception:
                    pass
                self._driver = None
            self._protocol = None
            self._set_state(GatewayState.RECONNECTING)

        DataBus.instance().publish_comm_error(self._config.id, "心跳失败，强制重置连接")

        if self._config.reconnect.get("enabled", True):
            self._reconnect_async()
        else:
            with self._lock:
                self._set_state(GatewayState.ERROR)

    def _reconnect_async(self):
        def _reconnect_loop():
            while self._reconnect_policy.should_retry():
                delay = self._reconnect_policy.next_delay()
                if delay < 0:
                    break

                logger.info(
                    "网关重连等待 [%s] 延迟=%dms 剩余尝试=%d",
                    self._config.id, delay, self._reconnect_policy.remaining_attempts,
                )
                time.sleep(delay / 1000.0)

                if self.connect():
                    self.start_polling()
                    return

            logger.error("网关重连耗尽 [%s]", self._config.id)
            with self._lock:
                self._set_state(GatewayState.ERROR)
            self._notify_error("重连次数耗尽")

        thread = threading.Thread(
            target=_reconnect_loop,
            name=f"GatewayReconnect-{self._config.id}",
            daemon=True,
        )
        thread.start()

    def _poll_loop(self):
        logger.info("轮询线程启动 [%s]", self._config.id)

        while self._is_polling:
            try:
                self.poll_once()
            except Exception as e:
                logger.error("轮询循环异常 [%s]: %s", self._config.id, e)

            interval = self._config.polling_interval_ms / 1000.0
            deadline = time.monotonic() + interval
            while self._is_polling and time.monotonic() < deadline:
                time.sleep(min(0.1, max(0, deadline - time.monotonic())))

        logger.info("轮询线程退出 [%s]", self._config.id)

    def _on_heartbeat_reset_required(self, gateway_id: str, failures: int):
        logger.error(
            "心跳连续失败达阈值 [%s] 失败次数=%d → 触发强制重置",
            gateway_id, failures,
        )
        self.force_reset()

    def _set_state(self, state: GatewayState):
        old = self._state
        self._state = state
        if old != state:
            logger.debug("网关状态变更 [%s] %s→%s", self._config.id, old.name, state.name)
            if self._on_state_changed_callback:
                try:
                    self._on_state_changed_callback(self._config.id, state)
                except Exception:
                    pass

    def _notify_data(self, data: Dict[str, Any]):
        if self._on_data_callback:
            try:
                self._on_data_callback(self._config.id, data)
            except Exception:
                pass

    def _notify_error(self, error: str):
        if self._on_error_callback:
            try:
                self._on_error_callback(self._config.id, error)
            except Exception:
                pass

    def get_statistics(self) -> dict:
        with self._lock:
            return {
                "gateway_id": self._config.id,
                "state": self._state.name,
                "is_connected": self.is_connected,
                "is_polling": self._is_polling,
                "poll_count": self._poll_count,
                "error_count": self._error_count,
                "last_poll_time": self._last_poll_time,
                "last_error": self._last_error,
                "heartbeat": self._heartbeat_mgr.get_statistics(),
                "reconnect": self._reconnect_policy.get_statistics(),
            }


class GatewayEngine(QObject):
    """
    网关通信引擎 — 多网关并发管理核心

    规范控制点④:
    - MCGS触摸屏为唯一TCP Server
    - 上位机为Client，每个网关对应一个长连接线程
    - 禁止频繁connect，保持长连接

    使用方式:
        engine = GatewayEngine()

        # 添加网关配置
        config = GatewayConfig.from_dict({
            "id": "mcgs_gw_1",
            "name": "1号车间MCGS网关",
            "ip": "192.168.31.140",
            "port": 502,
            "variables": [...]
        })
        engine.add_gateway(config)

        # 启动所有网关
        engine.start_all()

        # 停止所有网关
        engine.stop_all()
    """

    gateway_connected = Signal(str)
    gateway_disconnected = Signal(str)
    gateway_error = Signal(str, str)
    gateway_data_updated = Signal(str, dict)
    gateway_state_changed = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gateways: Dict[str, GatewayConnection] = {}
        self._lock = threading.Lock()

    def add_gateway(self, config: GatewayConfig) -> bool:
        with self._lock:
            if config.id in self._gateways:
                logger.warning("网关已存在 [%s]", config.id)
                return False

            conn = GatewayConnection(config)
            conn.set_callbacks(
                on_data=self._on_gateway_data,
                on_state_changed=self._on_gateway_state,
                on_error=self._on_gateway_error,
            )
            self._gateways[config.id] = conn

            logger.info("网关已添加 [%s] %s (%s:%d)", config.id, config.name, config.ip, config.port)
            return True

    def remove_gateway(self, gateway_id: str) -> bool:
        with self._lock:
            conn = self._gateways.get(gateway_id)
            if conn is None:
                return False

            conn.disconnect()
            del self._gateways[gateway_id]

        logger.info("网关已移除 [%s]", gateway_id)
        return True

    def connect_gateway(self, gateway_id: str) -> bool:
        conn = self._gateways.get(gateway_id)
        if conn is None:
            logger.warning("网关不存在 [%s]", gateway_id)
            return False

        success = conn.connect()
        if success:
            conn.start_polling()
            self.gateway_connected.emit(gateway_id)

        return success

    def disconnect_gateway(self, gateway_id: str):
        conn = self._gateways.get(gateway_id)
        if conn is None:
            return

        conn.disconnect()
        self.gateway_disconnected.emit(gateway_id)

    def start_all(self):
        logger.info("启动所有网关连接 (共%d个)", len(self._gateways))
        for gateway_id in list(self._gateways.keys()):
            try:
                self.connect_gateway(gateway_id)
            except Exception as e:
                logger.error("启动网关失败 [%s]: %s", gateway_id, e)

    def stop_all(self):
        logger.info("停止所有网关连接 (共%d个)", len(self._gateways))
        for conn in list(self._gateways.values()):
            try:
                conn.disconnect()
            except Exception as e:
                logger.debug("停止网关时出错: %s", e)

    def poll_gateway(self, gateway_id: str) -> Optional[Dict[str, Any]]:
        conn = self._gateways.get(gateway_id)
        if conn is None:
            return None
        return conn.poll_once()

    def get_gateway(self, gateway_id: str) -> Optional[GatewayConnection]:
        return self._gateways.get(gateway_id)

    def get_gateway_ids(self) -> List[str]:
        return list(self._gateways.keys())

    def get_gateway_state(self, gateway_id: str) -> Optional[GatewayState]:
        conn = self._gateways.get(gateway_id)
        return conn.state if conn else None

    def is_gateway_connected(self, gateway_id: str) -> bool:
        conn = self._gateways.get(gateway_id)
        return conn.is_connected if conn else False

    def get_all_statistics(self) -> Dict[str, dict]:
        return {
            gid: conn.get_statistics()
            for gid, conn in self._gateways.items()
        }

    def shutdown(self):
        logger.info("GatewayEngine 开始停机")
        self.stop_all()
        with self._lock:
            self._gateways.clear()
        logger.info("GatewayEngine 停机完成")

    def _on_gateway_data(self, gateway_id: str, data: Dict[str, Any]):
        self.gateway_data_updated.emit(gateway_id, data)

    def _on_gateway_state(self, gateway_id: str, state: GatewayState):
        self.gateway_state_changed.emit(gateway_id, int(state))

    def _on_gateway_error(self, gateway_id: str, error: str):
        self.gateway_error.emit(gateway_id, error)
