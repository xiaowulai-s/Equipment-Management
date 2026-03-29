"""
TCP通信驱动

设计原则:
    1. 继承BaseDriver, 实现TCP客户端通信
    2. 使用Python标准socket (非阻塞I/O + select超时)
    3. TCP Keepalive心跳保活
    4. 连接超时/读写超时独立配置
    5. SSL/TLS加密支持 (可选)
    6. 自动重连机制 (可配置)

使用示例:
    driver = TcpDriver(host="192.168.1.100", port=502, timeout=5.0)
    driver.opened.connect(lambda: print("TCP已连接"))
    driver.open()
    driver.write(b"\\x00\\x01\\x00\\x00\\x00\\x06\\x01\\x03\\x00\\x00\\x00\\x0a")
    response = driver.read(12)
    driver.close()
"""

from __future__ import annotations

import ipaddress
import logging
import select
import socket
import ssl
import struct
import threading
from typing import Any, Optional, Union

from PySide6.QtCore import QObject, Signal

from src.communication.base_driver import BaseDriver, DriverState, DriverStats
from src.utils.exceptions import DriverError, DriverOpenError, DriverReadError, DriverWriteError

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# TCP驱动默认参数
# ═══════════════════════════════════════════════════════════════

# TCP Keepalive 参数 (Linux/macOS)
_TCP_KEEPALIVE_IDLE = 10  # 空闲秒数后开始发送keepalive
_TCP_KEEPALIVE_INTERVAL = 3  # keepalive探测间隔 (秒)
_TCP_KEEPALIVE_COUNT = 3  # 最多探测次数

# SSL默认参数
_SSL_DEFAULT_CA_CERTS = None  # 使用系统默认CA证书
_SSL_PROTOCOL = ssl.PROTOCOL_TLS_CLIENT


# ═══════════════════════════════════════════════════════════════
# TCP驱动
# ═══════════════════════════════════════════════════════════════


class TcpDriver(BaseDriver):
    """TCP通信驱动

    基于Python标准socket实现, 支持非阻塞I/O和超时控制。
    适用于Modbus TCP协议层使用。

    Args:
        host: 目标IP地址或主机名
        port: 目标端口号 (1-65535)
        timeout: 默认读写超时 (秒)
        connect_timeout: 连接超时 (秒), 默认等于timeout
        keepalive: 是否启用TCP Keepalive, 默认True
        ssl_context: SSL上下文 (None=不使用SSL)
        parent: Qt父对象

    Attributes:
        host: 目标地址
        port: 目标端口
        local_address: 本地绑定地址 (可选)
        connect_timeout: 连接超时
        keepalive_enabled: 是否启用keepalive
        reconnect_enabled: 是否启用自动重连
        reconnect_interval: 自动重连间隔 (秒)
        reconnect_max_attempts: 最大重连次数 (-1=无限)
    """

    # ── 额外信号 ──
    connection_lost = Signal(str)  # 连接意外断开 (附带原因)

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 502,
        timeout: float = 5.0,
        connect_timeout: Optional[float] = None,
        keepalive: bool = True,
        ssl_context: Optional[ssl.SSLContext] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(
            driver_type="tcp",
            timeout=timeout,
            parent=parent,
        )

        # 连接参数
        self._host: str = host
        self._port: int = port
        self._connect_timeout: float = connect_timeout or timeout

        # Keepalive
        self._keepalive_enabled: bool = keepalive

        # SSL
        self._ssl_context: Optional[ssl.SSLContext] = ssl_context

        # 自动重连
        self._reconnect_enabled: bool = False
        self._reconnect_interval: float = 3.0  # 秒
        self._reconnect_max_attempts: int = -1  # -1=无限
        self._reconnect_attempts: int = 0
        self._reconnect_timer: Optional[threading.Timer] = None
        self._reconnect_lock = threading.Lock()

        # 本地绑定
        self._local_address: Optional[tuple[str, int]] = None

        # socket引用
        self._socket: Optional[socket.socket] = None

        # 写入缓冲区 (确保完整发送)
        self._write_buffer_lock = threading.Lock()

        # 初始配置
        self._config = {
            "host": host,
            "port": port,
            "connect_timeout": self._connect_timeout,
            "keepalive": keepalive,
        }

        logger.debug(f"[TCP] 创建驱动: {host}:{port}, " f"timeout={timeout}s, keepalive={keepalive}")

    # ═══════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════

    @property
    def host(self) -> str:
        """目标IP地址或主机名"""
        return self._host

    @host.setter
    def host(self, value: str) -> None:
        """设置目标地址 (需在open前设置)"""
        self._validate_host(value)
        self._host = value

    @property
    def port(self) -> int:
        """目标端口号"""
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        """设置目标端口 (需在open前设置)"""
        if not 1 <= value <= 65535:
            raise ValueError(f"端口号必须在1-65535之间, 实际: {value}")
        self._port = value

    @property
    def connect_timeout(self) -> float:
        """连接超时 (秒)"""
        return self._connect_timeout

    @connect_timeout.setter
    def connect_timeout(self, value: float) -> None:
        """设置连接超时"""
        if value <= 0:
            raise ValueError(f"连接超时必须大于0, 实际: {value}")
        self._connect_timeout = value

    @property
    def keepalive_enabled(self) -> bool:
        """是否启用TCP Keepalive"""
        return self._keepalive_enabled

    @property
    def reconnect_enabled(self) -> bool:
        """是否启用自动重连"""
        return self._reconnect_enabled

    @property
    def reconnect_interval(self) -> float:
        """自动重连间隔 (秒)"""
        return self._reconnect_interval

    @property
    def reconnect_max_attempts(self) -> int:
        """最大重连次数 (-1=无限)"""
        return self._reconnect_max_attempts

    @property
    def local_address(self) -> Optional[tuple[str, int]]:
        """本地绑定地址"""
        return self._local_address

    @property
    def remote_endpoint(self) -> str:
        """远端端点字符串 (host:port)"""
        return f"{self._host}:{self._port}"

    def set_reconnect(
        self,
        enabled: bool = True,
        interval: float = 3.0,
        max_attempts: int = -1,
    ) -> None:
        """配置自动重连

        Args:
            enabled: 是否启用
            interval: 重连间隔 (秒)
            max_attempts: 最大重连次数 (-1=无限)
        """
        self._reconnect_enabled = enabled
        self._reconnect_interval = max(0.5, interval)
        self._reconnect_max_attempts = max_attempts
        self._reconnect_attempts = 0
        logger.info(f"[TCP] 自动重连: enabled={enabled}, " f"interval={interval}s, max={max_attempts}")

    def bind_local(self, host: str, port: int = 0) -> None:
        """绑定本地地址

        Args:
            host: 本地IP地址
            port: 本地端口 (0=自动分配)
        """
        self._local_address = (host, port)
        logger.debug(f"[TCP] 本地绑定: {host}:{port}")

    # ═══════════════════════════════════════════════════════════
    # 参数校验
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _validate_host(host: str) -> None:
        """校验主机地址合法性"""
        if not host or len(host) > 253:
            raise ValueError(f"主机地址不合法: '{host}'")

        try:
            ipaddress.ip_address(host)
            # 合法IP
        except ValueError:
            # 不是IP, 检查主机名
            labels = host.split(".")
            for label in labels:
                if not label:
                    raise ValueError(f"主机名包含空标签: '{host}'")

    def _validate_config(self, **kwargs: Any) -> None:
        """校验TCP驱动参数"""
        if "host" in kwargs:
            self._validate_host(kwargs["host"])
        if "port" in kwargs:
            p = kwargs["port"]
            if not isinstance(p, int) or not 1 <= p <= 65535:
                raise ValueError(f"端口号必须为1-65535的整数, 实际: {p}")
        if "connect_timeout" in kwargs:
            ct = kwargs["connect_timeout"]
            if not isinstance(ct, (int, float)) or ct <= 0:
                raise ValueError(f"连接超时必须为正数, 实际: {ct}")

    # ═══════════════════════════════════════════════════════════
    # 抽象方法实现
    # ═══════════════════════════════════════════════════════════

    def _do_open(self) -> None:
        """建立TCP连接"""
        self._validate_host(self._host)

        # 创建socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # 设置连接超时
        sock.settimeout(self._connect_timeout)

        try:
            # 绑定本地地址 (如果指定)
            if self._local_address:
                sock.bind(self._local_address)
                logger.debug(f"[TCP] 绑定本地: {self._local_address}")

            # 发起连接
            sock.connect((self._host, self._port))

            # 连接成功, 配置Keepalive
            if self._keepalive_enabled:
                self._setup_keepalive(sock)

            # SSL握手 (如果配置)
            if self._ssl_context:
                sock = self._ssl_context.wrap_socket(sock, server_hostname=self._host)
                logger.info(f"[TCP] SSL连接已建立: " f"{sock.version()}")

            # 切换为阻塞模式 (使用select控制超时)
            sock.setblocking(True)
            sock.settimeout(None)

            self._socket = sock
            self._reconnect_attempts = 0

            logger.info(f"[TCP] 连接成功: {self._host}:{self._port}")

        except socket.timeout:
            sock.close()
            raise DriverOpenError(
                message=(f"TCP连接超时: " f"{self._host}:{self._port} " f"({self._connect_timeout}s)"),
                port=f"{self._host}:{self._port}",
                details={"host": self._host, "port": self._port, "timeout": self._connect_timeout},
            )

        except ConnectionRefusedError:
            sock.close()
            raise DriverOpenError(
                message=(f"TCP连接被拒绝: " f"{self._host}:{self._port}"),
                port=f"{self._host}:{self._port}",
                details={"host": self._host, "port": self._port, "reason": "connection_refused"},
            )

        except OSError as e:
            sock.close()
            error_code_map = {
                10060: "连接超时",
                10061: "连接被拒绝",
                10064: "主机不可达",
                10065: "主机无路由",
                10051: "网络不可达",
                11001: "主机名解析失败",
            }
            desc = error_code_map.get(
                e.winerror if hasattr(e, "winerror") else e.errno,
                str(e),
            )
            raise DriverOpenError(
                message=f"TCP连接失败: {desc}",
                port=f"{self._host}:{self._port}",
                details={"host": self._host, "port": self._port, "os_error": str(e)},
            )

    def _do_close(self) -> None:
        """关闭TCP连接"""
        self._cancel_reconnect()

        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # 可能已断开
            finally:
                self._socket.close()
                self._socket = None
            logger.info(f"[TCP] 已断开: {self._host}:{self._port}")

    def _do_read(self, size: int) -> bytes:
        """读取TCP数据

        Args:
            size: >0=精确读取size字节, -1=读取所有可用

        Returns:
            读取到的数据
        """
        if not self._socket:
            raise DriverReadError(
                message="TCP socket未初始化",
            )

        if size < 0:
            # 非阻塞读取所有可用数据
            return self._read_available()

        # 精确读取指定字节数
        return self._read_exact(size)

    def _do_write(self, data: bytes) -> int:
        """写入TCP数据 (确保完整发送)"""
        if not self._socket:
            raise DriverWriteError(
                message="TCP socket未初始化",
            )

        with self._write_buffer_lock:
            total_sent = 0
            remaining = len(data)

            while remaining > 0:
                # 使用select等待socket可写
                try:
                    _, writable, _ = select.select(
                        [],
                        [self._socket],
                        [],
                        self._timeout,
                    )
                except (ValueError, OSError):
                    # socket已关闭
                    self._handle_connection_lost("select失败")
                    raise DriverWriteError(
                        message="TCP连接已断开",
                    )

                if not writable:
                    raise DriverWriteError(
                        message=f"TCP写入超时 ({self._timeout}s)",
                    )

                try:
                    sent = self._socket.send(data[total_sent:])
                except OSError as e:
                    self._handle_connection_lost(str(e))
                    raise DriverWriteError(
                        message=f"TCP写入失败: {e}",
                    )

                if sent == 0:
                    self._handle_connection_lost("发送0字节")
                    raise DriverWriteError(
                        message="TCP连接已断开 (发送0字节)",
                    )

                total_sent += sent
                remaining -= sent

            return total_sent

    # ═══════════════════════════════════════════════════════════
    # 内部I/O方法
    # ═══════════════════════════════════════════════════════════

    def _read_exact(self, size: int) -> bytes:
        """精确读取指定字节数 (阻塞, 带超时)"""
        if size <= 0:
            return b""

        buf = bytearray()
        deadline = self._calc_deadline()

        while len(buf) < size:
            remaining_time = self._remaining_time(deadline)
            if remaining_time <= 0:
                raise DriverReadError(
                    message=(f"TCP读取超时: " f"已读{len(buf)}/{size}字节 " f"({self._timeout}s)"),
                    bytes_expected=size,
                    bytes_received=len(buf),
                )

            try:
                readable, _, _ = select.select(
                    [self._socket],
                    [],
                    [],
                    remaining_time,
                )
            except (ValueError, OSError):
                self._handle_connection_lost("select失败")
                raise DriverReadError(
                    message="TCP连接已断开",
                    bytes_expected=size - len(buf),
                )

            if not readable:
                raise DriverReadError(
                    message=(f"TCP读取超时: " f"已读{len(buf)}/{size}字节"),
                    bytes_expected=size - len(buf),
                )

            try:
                chunk = self._socket.recv(size - len(buf))
            except OSError as e:
                self._handle_connection_lost(str(e))
                raise DriverReadError(
                    message=f"TCP读取失败: {e}",
                    bytes_expected=size - len(buf),
                )

            if not chunk:
                # 对方关闭连接
                self._handle_connection_lost("远端关闭连接")
                raise DriverReadError(
                    message=(f"TCP连接被远端关闭: " f"已读{len(buf)}/{size}字节"),
                    bytes_expected=size - len(buf),
                )

            buf.extend(chunk)

        return bytes(buf)

    def _read_available(self) -> bytes:
        """非阻塞读取所有可用数据"""
        buf = bytearray()

        try:
            readable, _, _ = select.select(
                [self._socket],
                [],
                [],
                self._timeout,
            )
        except (ValueError, OSError):
            self._handle_connection_lost("select失败")
            raise DriverReadError(
                message="TCP连接已断开",
            )

        if not readable:
            return b""

        try:
            while True:
                chunk = self._socket.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                # 再次检查是否有更多数据
                readable, _, _ = select.select(
                    [self._socket],
                    [],
                    [],
                    0.0,  # 立即返回
                )
                if not readable:
                    break
        except OSError as e:
            if buf:
                # 已读到一些数据, 返回已读部分
                logger.warning(f"[TCP] 读取中出错 (已读{len(buf)}字节): {e}")
            else:
                self._handle_connection_lost(str(e))
                raise DriverReadError(
                    message=f"TCP读取失败: {e}",
                )

        return bytes(buf)

    # ═══════════════════════════════════════════════════════════
    # Keepalive
    # ═══════════════════════════════════════════════════════════

    def _setup_keepalive(self, sock: socket.socket) -> None:
        """配置TCP Keepalive"""
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # 平台差异处理
            if hasattr(socket, "TCP_KEEPIDLE"):
                # Linux
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPIDLE,
                    _TCP_KEEPALIVE_IDLE,
                )
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPINTVL,
                    _TCP_KEEPALIVE_INTERVAL,
                )
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPCNT,
                    _TCP_KEEPALIVE_COUNT,
                )
            elif hasattr(socket, "TCP_KEEPALIVE"):
                # macOS
                # macOS的TCP_KEEPALIVE值单位为秒 (不是毫秒)
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPALIVE,
                    _TCP_KEEPALIVE_IDLE,
                )
            elif sys.platform == "win32":
                # Windows: 使用ioctl
                sock.ioctl(
                    socket.SIO_KEEPALIVE_VALS,
                    (
                        1,  # 启用
                        _TCP_KEEPALIVE_IDLE * 1000,  # 空闲ms
                        _TCP_KEEPALIVE_INTERVAL * 1000,  # 间隔ms
                    ),
                )

            logger.debug(
                f"[TCP] Keepalive已启用: "
                f"idle={_TCP_KEEPALIVE_IDLE}s, "
                f"interval={_TCP_KEEPALIVE_INTERVAL}s, "
                f"count={_TCP_KEEPALIVE_COUNT}"
            )

        except OSError as e:
            logger.warning(f"[TCP] Keepalive配置失败: {e}")

    # ═══════════════════════════════════════════════════════════
    # 自动重连
    # ═══════════════════════════════════════════════════════════

    def _handle_connection_lost(self, reason: str) -> None:
        """处理连接丢失"""
        logger.warning(f"[TCP] 连接丢失: {reason} " f"({self._host}:{self._port})")

        # 清理socket
        old_socket = self._socket
        self._socket = None
        if old_socket:
            try:
                old_socket.close()
            except OSError:
                pass

        # 更新状态
        if self._state == DriverState.OPEN:
            try:
                self._set_state(DriverState.ERROR)
            except DriverError:
                pass

        # 发射信号
        self.connection_lost.emit(reason)

        # 自动重连
        if self._reconnect_enabled:
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """调度自动重连"""
        with self._reconnect_lock:
            # 取消之前的定时器
            self._cancel_reconnect()

            # 检查重连次数
            if self._reconnect_max_attempts >= 0 and self._reconnect_attempts >= self._reconnect_max_attempts:
                logger.info(f"[TCP] 已达最大重连次数 " f"({self._reconnect_max_attempts}), " f"停止重连")
                return

            self._reconnect_attempts += 1
            logger.info(f"[TCP] 将在{self._reconnect_interval}s后重连 " f"(第{self._reconnect_attempts}次)")

            self._reconnect_timer = threading.Timer(
                self._reconnect_interval,
                self._do_reconnect,
            )
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()

    def _do_reconnect(self) -> None:
        """执行重连 (在定时器线程中)"""
        try:
            if self._state == DriverState.OPEN:
                return

            logger.info(f"[TCP] 尝试重连 " f"(第{self._reconnect_attempts}次): " f"{self._host}:{self._port}")

            # 直接调用open()
            self.open()

        except Exception as e:
            logger.warning(f"[TCP] 重连失败: {e}")
            # 继续调度下一次重连
            if self._reconnect_enabled:
                self._schedule_reconnect()

    def _cancel_reconnect(self) -> None:
        """取消自动重连定时器"""
        with self._reconnect_lock:
            if self._reconnect_timer:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None

    # ═══════════════════════════════════════════════════════════
    # 超时工具
    # ═══════════════════════════════════════════════════════════

    def _calc_deadline(self) -> float:
        """计算超时截止时间"""
        import time

        return time.monotonic() + self._timeout

    @staticmethod
    def _remaining_time(deadline: float) -> float:
        """计算剩余超时时间"""
        import time

        return max(0.0, deadline - time.monotonic())

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"'{self._host}:{self._port}', "
            f"state='{self._state}', "
            f"timeout={self._timeout}s"
            f")"
        )

    def get_info(self) -> dict[str, Any]:
        """获取TCP驱动信息"""
        info = super().get_info()
        info.update(
            {
                "host": self._host,
                "port": self._port,
                "connect_timeout": self._connect_timeout,
                "keepalive": self._keepalive_enabled,
                "ssl": self._ssl_context is not None,
                "reconnect": {
                    "enabled": self._reconnect_enabled,
                    "interval": self._reconnect_interval,
                    "max_attempts": self._reconnect_max_attempts,
                    "current_attempts": self._reconnect_attempts,
                },
                "local_address": self._local_address,
            }
        )
        return info


# 需要在方法中使用sys.platform
import sys
