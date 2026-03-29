"""
通信驱动抽象基类

设计原则:
    1. 继承QObject, 全面支持Qt信号槽
    2. 定义驱动通用接口: open / close / read / write
    3. QMutex保证线程安全 (子类I/O在QThread中执行)
    4. 统一的错误码体系 (DriverError层次)
    5. 内置性能监控: 收发字节统计 + 最后活动时间
    6. 超时配置统一管理
    7. 支持驱动参数配置 (configure方法)

信号体系:
    opened()                     → 驱动打开成功
    closed()                     → 驱动关闭
    data_received(bytes)         → 原始数据接收
    error_occurred(str)          → 错误通知 (人类可读)
    bytes_sent_changed(int)      → 累计发送字节数变化
    bytes_received_changed(int)  → 累计接收字节数变化
"""

from __future__ import annotations

import logging
import threading
import time
from abc import ABCMeta, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

# 联合元类: 同时支持ABC抽象方法和QObject信号
_qobject_meta = type(QObject)

if issubclass(_qobject_meta, ABCMeta):
    _CombinedMeta = _qobject_meta
else:

    class _CombinedMeta(ABCMeta, _qobject_meta):  # type: ignore[misc, misc]
        """联合元类: 同时支持ABC抽象方法和QObject信号"""

        pass


from src.utils.exceptions import DriverError, DriverOpenError, DriverReadError, DriverWriteError

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 驱动状态枚举
# ═══════════════════════════════════════════════════════════════


class DriverState:
    """驱动状态常量 (字符串枚举, 便于JSON序列化)

    Attributes:
        CLOSED: 已关闭
        OPENING: 正在打开
        OPEN: 已打开
        CLOSING: 正在关闭
        ERROR: 错误状态
    """

    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    ERROR = "error"


# ═══════════════════════════════════════════════════════════════
# 性能统计
# ═══════════════════════════════════════════════════════════════


class DriverStats:
    """驱动性能统计

    线程安全地追踪:
        - 累计收发字节数
        - 最后活动时间
        - 读写操作次数
        - 错误次数
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bytes_sent: int = 0
        self._bytes_received: int = 0
        self._read_count: int = 0
        self._write_count: int = 0
        self._error_count: int = 0
        self._last_activity: Optional[float] = None  # time.time()
        self._open_count: int = 0  # 累计打开次数

    # ── 字节统计 ──

    def add_bytes_sent(self, count: int) -> None:
        """增加发送字节数"""
        if count <= 0:
            return
        with self._lock:
            self._bytes_sent += count
            self._last_activity = time.time()
            self._write_count += 1

    def add_bytes_received(self, count: int) -> None:
        """增加接收字节数"""
        if count <= 0:
            return
        with self._lock:
            self._bytes_received += count
            self._last_activity = time.time()
            self._read_count += 1

    def record_error(self) -> None:
        """记录一次错误"""
        with self._lock:
            self._error_count += 1

    def record_open(self) -> None:
        """记录一次打开操作"""
        with self._lock:
            self._open_count += 1
            self._last_activity = time.time()

    # ── 查询属性 ──

    @property
    def bytes_sent(self) -> int:
        with self._lock:
            return self._bytes_sent

    @property
    def bytes_received(self) -> int:
        with self._lock:
            return self._bytes_received

    @property
    def read_count(self) -> int:
        with self._lock:
            return self._read_count

    @property
    def write_count(self) -> int:
        with self._lock:
            return self._write_count

    @property
    def error_count(self) -> int:
        with self._lock:
            return self._error_count

    @property
    def open_count(self) -> int:
        with self._lock:
            return self._open_count

    @property
    def last_activity(self) -> Optional[float]:
        """最后活动时间 (time.time())"""
        with self._lock:
            return self._last_activity

    @property
    def last_activity_str(self) -> str:
        """最后活动时间 (可读字符串, 本地时区)"""
        ts = self.last_activity
        if ts is None:
            return "从未活动"
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def idle_seconds(self) -> float:
        """空闲秒数 (距最后活动的时长, 从未活动返回-1)"""
        ts = self.last_activity
        if ts is None:
            return -1.0
        return time.time() - ts

    def to_dict(self) -> dict[str, Any]:
        """导出为字典 (JSON可序列化)"""
        with self._lock:
            return {
                "bytes_sent": self._bytes_sent,
                "bytes_received": self._bytes_received,
                "read_count": self._read_count,
                "write_count": self._write_count,
                "error_count": self._error_count,
                "open_count": self._open_count,
                "last_activity": self.last_activity_str,
                "idle_seconds": round(self.idle_seconds, 2),
            }

    def reset(self) -> None:
        """重置所有统计"""
        with self._lock:
            self._bytes_sent = 0
            self._bytes_received = 0
            self._read_count = 0
            self._write_count = 0
            self._error_count = 0
            self._open_count = 0
            self._last_activity = None


# ═══════════════════════════════════════════════════════════════
# 驱动基类
# ═══════════════════════════════════════════════════════════════


class BaseDriver(QObject, metaclass=_CombinedMeta):
    """通信驱动抽象基类

    提供统一的驱动接口和状态管理。子类必须实现:
        - _do_open(): 执行打开操作
        - _do_close(): 执行关闭操作
        - _do_read(size): 读取指定字节数
        - _do_write(data): 写入数据

    线程安全保证:
        - open()/close()/read()/write() 通过QMutex保护
        - 状态转换通过状态机严格约束
        - 所有公共方法均可从任意线程安全调用

    使用示例:
        class TcpDriver(BaseDriver):
            def _do_open(self):
                self._socket.connect(...)
            def _do_close(self):
                self._socket.close()
            def _do_read(self, size):
                return self._socket.read(size)
            def _do_write(self, data):
                self._socket.write(data)

        driver = TcpDriver(timeout=5.0)
        driver.opened.connect(lambda: print("已连接"))
        driver.data_received.connect(lambda d: print(f"收到: {d}"))
        driver.open()
    """

    # ── Qt信号 ──
    opened = Signal()
    closed = Signal()
    data_received = Signal(bytes)
    error_occurred = Signal(str)
    bytes_sent_changed = Signal(int)
    bytes_received_changed = Signal(int)

    def __init__(
        self,
        driver_type: str = "base",
        timeout: float = 5.0,
        parent: Optional[QObject] = None,
    ) -> None:
        """
        Args:
            driver_type: 驱动类型标识 (如 "tcp", "serial")
            timeout: 默认超时时间 (秒)
            parent: Qt父对象
        """
        super().__init__(parent)

        self._driver_type = driver_type
        self._timeout = timeout
        self._state = DriverState.CLOSED
        self._stats = DriverStats()

        # Qt互斥锁保护状态转换和I/O操作
        self._mutex = threading.RLock()
        self._state_mutex = threading.Lock()

        # 驱动参数 (子类扩展)
        self._config: dict[str, Any] = {}

        logger.debug(f"[{self._driver_type}] 驱动创建, timeout={timeout}s")

    # ═══════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════

    @property
    def driver_type(self) -> str:
        """驱动类型标识"""
        return self._driver_type

    @property
    def state(self) -> str:
        """当前状态 (DriverState常量)"""
        return self._state

    @property
    def is_open(self) -> bool:
        """是否已打开"""
        return self._state == DriverState.OPEN

    @property
    def timeout(self) -> float:
        """超时时间 (秒)"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        """设置超时时间

        Args:
            value: 超时秒数, 必须 > 0

        Raises:
            ValueError: 超时值不合法
        """
        if value <= 0:
            raise ValueError(f"超时时间必须大于0, 实际: {value}")
        self._timeout = value
        logger.debug(f"[{self._driver_type}] 超时设置为 {value}s")

    @property
    def stats(self) -> DriverStats:
        """性能统计对象 (只读)"""
        return self._stats

    @property
    def config(self) -> dict[str, Any]:
        """驱动参数配置副本"""
        return dict(self._config)

    # ═══════════════════════════════════════════════════════════
    # 状态管理 (状态机)
    # ═══════════════════════════════════════════════════════════

    def _set_state(self, new_state: str) -> None:
        """安全切换状态 (线程安全)

        状态转换规则:
            CLOSED   → OPENING → OPEN / ERROR
            OPEN     → CLOSING → CLOSED / ERROR
            ERROR    → OPENING (重试) / CLOSING (关闭)
            CLOSING  → CLOSED / ERROR

        Args:
            new_state: 目标状态

        Raises:
            DriverError: 非法状态转换
        """
        with self._state_mutex:
            old_state = self._state

            # 验证状态转换合法性
            valid_transitions = {
                DriverState.CLOSED: {DriverState.OPENING},
                DriverState.OPENING: {DriverState.OPEN, DriverState.ERROR},
                DriverState.OPEN: {DriverState.CLOSING, DriverState.ERROR},
                DriverState.CLOSING: {DriverState.CLOSED, DriverState.ERROR},
                DriverState.ERROR: {DriverState.OPENING, DriverState.CLOSING, DriverState.CLOSED},
            }

            allowed = valid_transitions.get(old_state, set())
            if new_state not in allowed:
                msg = f"[{self._driver_type}] 非法状态转换: " f"{old_state} → {new_state}"
                logger.error(msg)
                raise DriverError(msg)

            self._state = new_state

            if old_state != new_state:
                logger.debug(f"[{self._driver_type}] 状态: {old_state} → {new_state}")

    def _check_open(self) -> None:
        """检查驱动是否已打开, 未打开则抛异常"""
        if not self.is_open:
            raise DriverError(
                f"驱动未打开 (当前状态: {self._state})",
                error_code="DRIVER_NOT_OPEN",
                details={"driver_type": self._driver_type, "state": self._state},
            )

    # ═══════════════════════════════════════════════════════════
    # 公共接口 (模板方法模式)
    # ═══════════════════════════════════════════════════════════

    def open(self) -> None:
        """打开驱动 (线程安全)

        执行流程:
            1. 状态检查 (已打开→跳过, 非CLOSED/ERROR→拒绝)
            2. 状态 → OPENING
            3. 调用 _do_open() (子类实现)
            4. 成功 → 状态=OPEN, 发射opened信号
            5. 失败 → 状态=ERROR, 发射error_occurred信号

        Raises:
            DriverError: 状态不允许 / 子类打开失败
        """
        with self._mutex:
            # 已打开, 直接返回
            if self.is_open:
                logger.debug(f"[{self._driver_type}] 已打开, 跳过")
                return

            # 检查状态合法性
            if self._state not in (DriverState.CLOSED, DriverState.ERROR):
                raise DriverError(
                    f"当前状态({self._state})不允许打开操作",
                    error_code="DRIVER_INVALID_STATE",
                    details={"current_state": self._state},
                )

            try:
                self._set_state(DriverState.OPENING)
                self._do_open()
                self._set_state(DriverState.OPEN)
                self._stats.record_open()
                logger.info(f"[{self._driver_type}] 驱动打开成功")
                self.opened.emit()

            except Exception as e:
                self._set_state(DriverState.ERROR)
                self._stats.record_error()
                error_msg = f"[{self._driver_type}] 驱动打开失败: {e}"
                logger.error(error_msg, exc_info=True)

                if isinstance(e, DriverError):
                    self.error_occurred.emit(str(e))
                    raise

                # 包装为DriverError
                raise DriverOpenError(
                    message=f"驱动打开失败: {e}",
                    details={"driver_type": self._driver_type, "reason": str(e)},
                ) from e

    def close(self) -> None:
        """关闭驱动 (线程安全)

        执行流程:
            1. 已关闭→跳过
            2. 状态 → CLOSING
            3. 调用 _do_close() (子类实现)
            4. 成功 → 状态=CLOSED, 发射closed信号
            5. 失败 → 状态=ERROR, 发射error_occurred信号
        """
        with self._mutex:
            # 已关闭, 直接返回
            if self._state == DriverState.CLOSED:
                logger.debug(f"[{self._driver_type}] 已关闭, 跳过")
                return

            # 允许从任何非CLOSED状态关闭
            try:
                self._set_state(DriverState.CLOSING)
                self._do_close()
                self._set_state(DriverState.CLOSED)
                logger.info(f"[{self._driver_type}] 驱动已关闭")
                self.closed.emit()

            except Exception as e:
                self._set_state(DriverState.ERROR)
                self._stats.record_error()
                error_msg = f"[{self._driver_type}] 驱动关闭失败: {e}"
                logger.error(error_msg, exc_info=True)
                self.error_occurred.emit(error_msg)

                # 关闭失败不应抛异常, 防止资源泄漏
                # 调用者应通过信号获取错误

    def read(self, size: int = -1) -> bytes:
        """读取数据 (线程安全)

        Args:
            size: 读取字节数
                - >0: 精确读取指定字节数 (可能阻塞)
                - -1: 读取所有可用数据 (非阻塞)

        Returns:
            读取到的字节数据

        Raises:
            DriverError: 驱动未打开
            DriverReadError: 读取失败
        """
        self._check_open()

        with self._mutex:
            try:
                data = self._do_read(size)
                if data:
                    self._stats.add_bytes_received(len(data))
                    self.bytes_received_changed.emit(self._stats.bytes_received)
                    # 发射数据接收信号
                    self.data_received.emit(data)
                return data or b""

            except Exception as e:
                self._stats.record_error()
                logger.error(
                    f"[{self._driver_type}] 读取失败: {e}",
                    exc_info=True,
                )

                if isinstance(e, DriverError):
                    self.error_occurred.emit(str(e))
                    raise

                raise DriverReadError(
                    message=f"数据读取失败: {e}",
                    bytes_expected=size if size > 0 else None,
                    details={"driver_type": self._driver_type, "reason": str(e)},
                ) from e

    def write(self, data: bytes) -> int:
        """写入数据 (线程安全)

        Args:
            data: 要发送的字节数据

        Returns:
            实际写入的字节数

        Raises:
            DriverError: 驱动未打开 / 数据为空
            DriverWriteError: 写入失败
        """
        self._check_open()

        if not data:
            raise DriverWriteError(
                message="写入数据不能为空",
                error_code="DRIVER_WRITE_EMPTY",
            )

        with self._mutex:
            try:
                bytes_written = self._do_write(data)
                self._stats.add_bytes_sent(bytes_written)
                self.bytes_sent_changed.emit(self._stats.bytes_sent)
                logger.debug(f"[{self._driver_type}] 写入 " f"{bytes_written}/{len(data)} 字节")
                return bytes_written

            except Exception as e:
                self._stats.record_error()
                logger.error(
                    f"[{self._driver_type}] 写入失败: {e}",
                    exc_info=True,
                )

                if isinstance(e, DriverError):
                    self.error_occurred.emit(str(e))
                    raise

                raise DriverWriteError(
                    message=f"数据写入失败: {e}",
                    details={"driver_type": self._driver_type, "data_length": len(data), "reason": str(e)},
                ) from e

    def configure(self, **kwargs: Any) -> None:
        """配置驱动参数 (线程安全)

        子类可重写此方法添加参数校验逻辑。
        参数设置后不会立即生效, 需要关闭后重新打开。

        Args:
            **kwargs: 驱动参数键值对

        Raises:
            ValueError: 参数值不合法
        """
        self._validate_config(**kwargs)
        with self._mutex:
            self._config.update(kwargs)
        logger.debug(f"[{self._driver_type}] 配置更新: {kwargs}")

    def reset_stats(self) -> None:
        """重置性能统计"""
        self._stats.reset()
        logger.debug(f"[{self._driver_type}] 性能统计已重置")

    # ═══════════════════════════════════════════════════════════
    # 抽象方法 (子类必须实现)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def _do_open(self) -> None:
        """执行打开操作 (子类实现)

        此方法在QMutex保护下被调用。
        成功时应直接返回, 失败时抛出异常。

        Raises:
            DriverOpenError: 打开失败
        """
        ...

    @abstractmethod
    def _do_close(self) -> None:
        """执行关闭操作 (子类实现)

        此方法在QMutex保护下被调用。
        应确保释放所有底层资源。

        Raises:
            Exception: 关闭过程中的异常会被基类捕获并记录
        """
        ...

    @abstractmethod
    def _do_read(self, size: int) -> bytes:
        """执行读取操作 (子类实现)

        Args:
            size: 读取字节数 (-1=全部可用)

        Returns:
            读取到的字节数据

        Raises:
            DriverReadError: 读取失败
        """
        ...

    @abstractmethod
    def _do_write(self, data: bytes) -> int:
        """执行写入操作 (子类实现)

        Args:
            data: 要发送的数据

        Returns:
            实际写入的字节数

        Raises:
            DriverWriteError: 写入失败
        """
        ...

    # ═══════════════════════════════════════════════════════════
    # 可重写钩子方法
    # ═══════════════════════════════════════════════════════════

    def _validate_config(self, **kwargs: Any) -> None:
        """校验驱动参数 (子类可重写)

        默认实现不做校验, 子类应重写此方法添加参数约束。

        Args:
            **kwargs: 待校验的参数

        Raises:
            ValueError: 参数不合法
        """
        pass

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"type='{self._driver_type}', "
            f"state='{self._state}', "
            f"timeout={self._timeout}s, "
            f"tx={self._stats.bytes_sent}, "
            f"rx={self._stats.bytes_received}"
            f")"
        )

    def get_info(self) -> dict[str, Any]:
        """获取驱动信息 (JSON可序列化)"""
        return {
            "driver_type": self._driver_type,
            "driver_class": self.__class__.__name__,
            "state": self._state,
            "timeout": self._timeout,
            "config": self._config,
            "stats": self._stats.to_dict(),
        }
