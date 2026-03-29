"""
串口通信驱动

设计原则:
    1. 继承BaseDriver, 实现串口通信 (基于pyserial)
    2. 支持完整串口参数配置 (波特率/数据位/停止位/校验位)
    3. 支持串口设备枚举 (跨平台: Windows COM / Linux /dev/tty*)
    4. 支持硬件流控 (RTS/CTS, DTR/DSR)
    5. 支持串口热插拔检测 (线程轮询)
    6. 串口缓冲区大小配置
    7. 所有I/O在QMutex保护下执行

使用示例:
    driver = SerialDriver(port="COM3", baudrate=9600)
    driver.opened.connect(lambda: print("串口已打开"))
    driver.open()
    driver.write(b"\\x01\\x03\\x00\\x00\\x00\\x0A\\xC5\\xCD")
    response = driver.read(8)
    driver.close()

依赖:
    - pyserial (pip install pyserial)
"""

from __future__ import annotations

import logging
import threading
import time
from enum import IntEnum
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

from src.communication.base_driver import BaseDriver, DriverState, DriverStats
from src.utils.exceptions import DriverError, DriverOpenError, DriverReadError, DriverWriteError

logger = logging.getLogger(__name__)

# pyserial 导入 (可选依赖)
try:
    import serial
    import serial.tools.list_ports

    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False
    logger.warning("pyserial未安装, 串口驱动将不可用. " "请运行: pip install pyserial")


# ═══════════════════════════════════════════════════════════════
# 串口参数常量
# ═══════════════════════════════════════════════════════════════


class BaudRate(IntEnum):
    """标准波特率"""

    B_1200 = 1200
    B_2400 = 2400
    B_4800 = 4800
    B_9600 = 9600
    B_19200 = 19200
    B_38400 = 38400
    B_57600 = 57600
    B_115200 = 115200


class DataBits(IntEnum):
    """数据位"""

    BITS_5 = 5
    BITS_6 = 6
    BITS_7 = 7
    BITS_8 = 8


class StopBits:
    """停止位"""

    ONE = 1.0
    ONE_HALF = 1.5
    TWO = 2.0


class Parity:
    """校验位"""

    NONE = "N"
    EVEN = "E"
    ODD = "O"
    MARK = "M"
    SPACE = "S"


# pyserial parity映射
_PARITY_MAP = {
    Parity.NONE: serial.PARITY_NONE if _SERIAL_AVAILABLE else "N",
    Parity.EVEN: serial.PARITY_EVEN if _SERIAL_AVAILABLE else "E",
    Parity.ODD: serial.PARITY_ODD if _SERIAL_AVAILABLE else "O",
    Parity.MARK: serial.PARITY_MARK if _SERIAL_AVAILABLE else "M",
    Parity.SPACE: serial.PARITY_SPACE if _SERIAL_AVAILABLE else "S",
}

# 合法参数集合
_VALID_BAUDRATES = {b.value for b in BaudRate}
_VALID_DATA_BITS = {d.value for d in DataBits}
_VALID_STOP_BITS = {StopBits.ONE, StopBits.ONE_HALF, StopBits.TWO}
_VALID_PARITIES = {Parity.NONE, Parity.EVEN, Parity.ODD, Parity.MARK, Parity.SPACE}

# 热插拔检测间隔
_HOTPLUG_CHECK_INTERVAL = 2.0  # 秒


# ═══════════════════════════════════════════════════════════════
# 串口驱动
# ═══════════════════════════════════════════════════════════════


class SerialDriver(BaseDriver):
    """串口通信驱动

    基于pyserial的串口客户端。支持RTU/ASCII模式Modbus通信。

    Args:
        port: 串口号 (如 "COM3", "/dev/ttyUSB0")
        baudrate: 波特率 (默认9600)
        data_bits: 数据位 (默认8)
        stop_bits: 停止位 (默认1.0)
        parity: 校验位 (默认"N"无校验)
        timeout: 读写超时 (秒)
        rtscts: 是否启用RTS/CTS硬件流控
        dsrdtr: 是否启用DTR/DSR硬件流控
        parent: Qt父对象
    """

    # ── 额外信号 ──
    device_removed = Signal(str)  # 设备被拔出
    device_arrived = Signal(str)  # 新设备插入

    def __init__(
        self,
        port: str = "COM1",
        baudrate: int = 9600,
        data_bits: int = 8,
        stop_bits: float = 1.0,
        parity: str = "N",
        timeout: float = 1.0,
        rtscts: bool = False,
        dsrdtr: bool = False,
        parent: Optional[QObject] = None,
    ) -> None:
        if not _SERIAL_AVAILABLE:
            raise ImportError("pyserial未安装, 请运行: pip install pyserial")

        super().__init__(
            driver_type="serial",
            timeout=timeout,
            parent=parent,
        )

        # 串口参数
        self._port: str = port
        self._baudrate: int = baudrate
        self._data_bits: int = data_bits
        self._stop_bits: float = stop_bits
        self._parity: str = parity

        # 流控
        self._rtscts: bool = rtscts
        self._dsrdtr: bool = dsrdtr

        # 缓冲区大小
        self._input_buffer_size: int = 4096
        self._output_buffer_size: int = 4096

        # 热插拔
        self._hotplug_enabled: bool = False
        self._hotplug_thread: Optional[threading.Thread] = None
        self._hotplug_stop_event = threading.Event()

        # serial引用
        self._serial: Optional[serial.Serial] = None

        # 初始配置
        self._config = {
            "port": port,
            "baudrate": baudrate,
            "data_bits": data_bits,
            "stop_bits": stop_bits,
            "parity": parity,
            "rtscts": rtscts,
            "dsrdtr": dsrdtr,
        }

        logger.debug(
            f"[SERIAL] 创建驱动: {port}, " f"baud={baudrate}, bits={data_bits}, " f"stop={stop_bits}, parity={parity}"
        )

    # ═══════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════

    @property
    def port(self) -> str:
        """串口号"""
        return self._port

    @port.setter
    def port(self, value: str) -> None:
        """设置串口号"""
        if not value or not isinstance(value, str):
            raise ValueError(f"串口号不能为空: '{value}'")
        self._port = value

    @property
    def baudrate(self) -> int:
        """波特率"""
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value: int) -> None:
        """设置波特率"""
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"波特率必须为正整数, 实际: {value}")
        self._baudrate = value

    @property
    def data_bits(self) -> int:
        """数据位"""
        return self._data_bits

    @data_bits.setter
    def data_bits(self, value: int) -> None:
        """设置数据位"""
        if value not in _VALID_DATA_BITS:
            raise ValueError(f"数据位必须为 {sorted(_VALID_DATA_BITS)}, " f"实际: {value}")
        self._data_bits = value

    @property
    def stop_bits(self) -> float:
        """停止位"""
        return self._stop_bits

    @stop_bits.setter
    def stop_bits(self, value: float) -> None:
        """设置停止位"""
        if value not in _VALID_STOP_BITS:
            raise ValueError(f"停止位必须为 1.0, 1.5 或 2.0, 实际: {value}")
        self._stop_bits = value

    @property
    def parity(self) -> str:
        """校验位"""
        return self._parity

    @parity.setter
    def parity(self, value: str) -> None:
        """设置校验位"""
        val_upper = value.upper() if isinstance(value, str) else value
        if val_upper not in _VALID_PARITIES:
            raise ValueError(f"校验位必须为 {sorted(_VALID_PARITIES)}, " f"实际: {value}")
        self._parity = val_upper

    @property
    def rtscts(self) -> bool:
        """是否启用RTS/CTS流控"""
        return self._rtscts

    @property
    def dsrdtr(self) -> bool:
        """是否启用DTR/DSR流控"""
        return self._dsrdtr

    @property
    def input_buffer_size(self) -> int:
        """输入缓冲区大小"""
        return self._input_buffer_size

    @property
    def output_buffer_size(self) -> int:
        """输出缓冲区大小"""
        return self._output_buffer_size

    @property
    def hotplug_enabled(self) -> bool:
        """是否启用热插拔检测"""
        return self._hotplug_enabled

    @property
    def port_description(self) -> str:
        """端口描述字符串 (COM3 9600-8N1)"""
        parity_map = {
            "N": "N",
            "E": "E",
            "O": "O",
            "M": "M",
            "S": "S",
        }
        stop_str = "1" if self._stop_bits == 1.0 else "1.5" if self._stop_bits == 1.5 else "2"
        return (
            f"{self._port} "
            f"{self._baudrate}-"
            f"{self._data_bits}"
            f"{parity_map.get(self._parity, self._parity)}"
            f"{stop_str}"
        )

    # ═══════════════════════════════════════════════════════════
    # 参数校验
    # ═══════════════════════════════════════════════════════════

    def _validate_config(self, **kwargs: Any) -> None:
        """校验串口参数"""
        if "port" in kwargs:
            v = kwargs["port"]
            if not v or not isinstance(v, str):
                raise ValueError(f"串口号不能为空: '{v}'")
        if "baudrate" in kwargs:
            v = kwargs["baudrate"]
            if not isinstance(v, int) or v <= 0:
                raise ValueError(f"波特率必须为正整数, 实际: {v}")
        if "data_bits" in kwargs:
            v = kwargs["data_bits"]
            if v not in _VALID_DATA_BITS:
                raise ValueError(f"无效数据位: {v}")
        if "stop_bits" in kwargs:
            v = kwargs["stop_bits"]
            if v not in _VALID_STOP_BITS:
                raise ValueError(f"无效停止位: {v}")
        if "parity" in kwargs:
            v = kwargs["parity"]
            val = v.upper() if isinstance(v, str) else v
            if val not in _VALID_PARITIES:
                raise ValueError(f"无效校验位: {v}")

    # ═══════════════════════════════════════════════════════════
    # 缓冲区配置
    # ═══════════════════════════════════════════════════════════

    def set_buffer_size(
        self,
        input_size: int = 4096,
        output_size: int = 4096,
    ) -> None:
        """配置串口缓冲区大小

        Args:
            input_size: 输入缓冲区字节数 (需在open前设置)
            output_size: 输出缓冲区字节数 (需在open前设置)
        """
        if input_size < 1 or output_size < 1:
            raise ValueError("缓冲区大小必须 >= 1")
        self._input_buffer_size = input_size
        self._output_buffer_size = output_size
        logger.debug(f"[SERIAL] 缓冲区: rx={input_size}, tx={output_size}")

    # ═══════════════════════════════════════════════════════════
    # 抽象方法实现
    # ═══════════════════════════════════════════════════════════

    def _do_open(self) -> None:
        """打开串口"""
        if not _SERIAL_AVAILABLE:
            raise DriverOpenError(
                message="pyserial未安装",
                port=self._port,
            )

        try:
            ser = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._data_bits,
                stopbits=self._stop_bits,
                parity=_PARITY_MAP.get(self._parity, self._parity),
                timeout=self._timeout,
                rtscts=self._rtscts,
                dsrdtr=self._dsrdtr,
            )

            # 配置缓冲区
            if hasattr(ser, "set_buffer_size"):
                try:
                    ser.set_buffer_size(
                        self._input_buffer_size,
                        self._output_buffer_size,
                    )
                except (serial.SerialException, OSError):
                    logger.debug("[SERIAL] 缓冲区大小设置不被支持")

            self._serial = ser
            logger.info(f"[SERIAL] 已打开: {self.port_description}")

        except serial.SerialException as e:
            raise DriverOpenError(
                message=f"串口打开失败: {e}",
                port=self._port,
                details={
                    "port": self._port,
                    "baudrate": self._baudrate,
                    "reason": str(e),
                },
            )

        except OSError as e:
            # 端口不存在 / 权限不足 / 被占用
            error_desc = str(e)
            if "could not open port" in error_desc.lower():
                error_desc = f"串口不存在或被占用: {self._port}"
            elif "permission" in error_desc.lower():
                error_desc = f"串口权限不足: {self._port}"

            raise DriverOpenError(
                message=f"串口打开失败: {error_desc}",
                port=self._port,
                details={
                    "port": self._port,
                    "reason": error_desc,
                },
            )

    def _do_close(self) -> None:
        """关闭串口"""
        self._stop_hotplug()

        if self._serial and self._serial.is_open:
            try:
                # 清空缓冲区
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
            except OSError:
                pass
            finally:
                self._serial.close()
                self._serial = None
            logger.info(f"[SERIAL] 已关闭: {self._port}")

    def _do_read(self, size: int) -> bytes:
        """读取串口数据

        Args:
            size: >0=精确读取size字节, -1=读取所有可用
        """
        if not self._serial or not self._serial.is_open:
            raise DriverReadError(
                message="串口未打开",
            )

        if size < 0:
            # 读取所有可用数据
            available = self._serial.in_waiting
            if available <= 0:
                return b""
            try:
                return self._serial.read(available)
            except OSError as e:
                raise DriverReadError(
                    message=f"串口读取失败: {e}",
                )

        # 精确读取
        return self._read_exact(size)

    def _do_write(self, data: bytes) -> int:
        """写入串口数据"""
        if not self._serial or not self._serial.is_open:
            raise DriverWriteError(
                message="串口未打开",
            )

        try:
            # 清空输入缓冲区 (防止残留数据干扰响应)
            self._serial.reset_input_buffer()
            written = self._serial.write(data)

            # 确保数据发送完成
            if hasattr(self._serial, "flush"):
                self._serial.flush()

            return written

        except OSError as e:
            raise DriverWriteError(
                message=f"串口写入失败: {e}",
                details={"port": self._port, "reason": str(e)},
            )

    # ═══════════════════════════════════════════════════════════
    # 精确读取
    # ═══════════════════════════════════════════════════════════

    def _read_exact(self, size: int) -> bytes:
        """精确读取指定字节数 (带超时)"""
        buf = bytearray()
        deadline = time.monotonic() + self._timeout

        while len(buf) < size:
            remaining_time = max(0.0, deadline - time.monotonic())
            if remaining_time <= 0:
                raise DriverReadError(
                    message=(f"串口读取超时: " f"已读{len(buf)}/{size}字节 " f"({self._timeout}s)"),
                    bytes_expected=size,
                    bytes_received=len(buf),
                )

            # 更新串口超时为剩余时间
            old_timeout = self._serial.timeout
            self._serial.timeout = remaining_time

            try:
                chunk = self._serial.read(size - len(buf))
            except OSError as e:
                raise DriverReadError(
                    message=f"串口读取失败: {e}",
                    bytes_expected=size - len(buf),
                )
            finally:
                self._serial.timeout = old_timeout

            if not chunk:
                # 超时无数据
                raise DriverReadError(
                    message=(f"串口读取超时: " f"已读{len(buf)}/{size}字节"),
                    bytes_expected=size - len(buf),
                )

            buf.extend(chunk)

        return bytes(buf)

    # ═══════════════════════════════════════════════════════════
    # 流控信号
    # ═══════════════════════════════════════════════════════════

    def set_rts(self, level: bool) -> None:
        """设置RTS信号电平

        Args:
            level: True=高电平, False=低电平
        """
        if self._serial and self._serial.is_open:
            self._serial.rts = level

    def set_dtr(self, level: bool) -> None:
        """设置DTR信号电平

        Args:
            level: True=高电平, False=低电平
        """
        if self._serial and self._serial.is_open:
            self._serial.dtr = level

    def get_cts(self) -> bool:
        """读取CTS信号电平"""
        if self._serial and self._serial.is_open:
            return bool(self._serial.cts)
        return False

    def get_dsr(self) -> bool:
        """读取DSR信号电平"""
        if self._serial and self._serial.is_open:
            return bool(self._serial.dsr)
        return False

    def get_ri(self) -> bool:
        """读取RI (Ring Indicator) 信号电平"""
        if self._serial and self._serial.is_open:
            return bool(self._serial.ri)
        return False

    def get_cd(self) -> bool:
        """读取CD (Carrier Detect) 信号电平"""
        if self._serial and self._serial.is_open:
            return bool(self._serial.cd)
        return False

    # ═══════════════════════════════════════════════════════════
    # 缓冲区操作
    # ═══════════════════════════════════════════════════════════

    def clear_buffers(self) -> None:
        """清空输入/输出缓冲区"""
        if self._serial and self._serial.is_open:
            try:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
            except OSError as e:
                logger.warning(f"[SERIAL] 清空缓冲区失败: {e}")

    @property
    def in_waiting(self) -> int:
        """输入缓冲区中等待读取的字节数"""
        if self._serial and self._serial.is_open:
            return self._serial.in_waiting
        return 0

    @property
    def out_waiting(self) -> int:
        """输出缓冲区中等待发送的字节数"""
        if self._serial and self._serial.is_open:
            try:
                return self._serial.out_waiting
            except AttributeError:
                return 0
        return 0

    # ═══════════════════════════════════════════════════════════
    # 热插拔检测
    # ═══════════════════════════════════════════════════════════

    def start_hotplug_detection(self) -> None:
        """启动串口热插拔检测线程"""
        if not _SERIAL_AVAILABLE:
            logger.warning("[SERIAL] pyserial未安装, 无法启动热插拔检测")
            return

        if self._hotplug_enabled:
            return

        self._hotplug_enabled = True
        self._hotplug_stop_event.clear()
        self._hotplug_thread = threading.Thread(
            target=self._hotplug_loop,
            name=f"serial-hotplug-{self._port}",
            daemon=True,
        )
        self._hotplug_thread.start()
        logger.info(f"[SERIAL] 热插拔检测已启动: {self._port}")

    def stop_hotplug_detection(self) -> None:
        """停止串口热插拔检测"""
        self._stop_hotplug()
        logger.info(f"[SERIAL] 热插拔检测已停止: {self._port}")

    def _stop_hotplug(self) -> None:
        """停止热插拔线程"""
        self._hotplug_enabled = False
        self._hotplug_stop_event.set()
        if self._hotplug_thread and self._hotplug_thread.is_alive():
            self._hotplug_thread.join(timeout=3.0)
        self._hotplug_thread = None

    def _hotplug_loop(self) -> None:
        """热插拔检测循环"""
        was_present = True  # 假设初始存在

        while not self._hotplug_stop_event.is_set():
            try:
                current_ports = {p.device for p in serial.tools.list_ports.comports()}
                is_present = self._port in current_ports

                if was_present and not is_present:
                    logger.warning(f"[SERIAL] 设备被拔出: {self._port}")
                    self.device_removed.emit(self._port)
                    # 如果正在连接, 更新状态
                    if self.is_open:
                        self._handle_device_removed()

                elif not was_present and is_present:
                    logger.info(f"[SERIAL] 设备已插入: {self._port}")
                    self.device_arrived.emit(self._port)

                was_present = is_present

            except Exception as e:
                logger.debug(f"[SERIAL] 热插拔检测异常: {e}")

            # 等待下次检查
            self._hotplug_stop_event.wait(_HOTPLUG_CHECK_INTERVAL)

    def _handle_device_removed(self) -> None:
        """处理设备被拔出"""
        logger.warning(f"[SERIAL] 设备被拔出, 关闭连接: {self._port}")
        try:
            if self._serial:
                self._serial.close()
                self._serial = None
            # 更新状态 (不经过mutex, 因为在热插拔线程中)
            self._state = DriverState.ERROR
        except Exception as e:
            logger.error(f"[SERIAL] 处理设备拔出失败: {e}")

        self.connection_lost.emit("设备被拔出")
        self.error_occurred.emit(f"串口设备被拔出: {self._port}")

    # ═══════════════════════════════════════════════════════════
    # 静态方法: 设备枚举
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def enumerate_serial_ports() -> list[dict[str, str]]:
        """枚举系统所有可用串口

        Returns:
            串口信息列表, 每项包含:
            - device: 设备路径 (如 "COM3", "/dev/ttyUSB0")
            - description: 设备描述
            - hwid: 硬件ID
        """
        if not _SERIAL_AVAILABLE:
            return []

        ports = []
        try:
            for p in serial.tools.list_ports.comports():
                ports.append(
                    {
                        "device": p.device,
                        "description": p.description,
                        "hwid": p.hwid,
                    }
                )
        except Exception as e:
            logger.error(f"[SERIAL] 枚举失败: {e}")

        return ports

    @staticmethod
    def is_port_available(port: str) -> bool:
        """检查指定串口是否可用

        Args:
            port: 串口号

        Returns:
            True=可用, False=不存在
        """
        if not _SERIAL_AVAILABLE:
            return False
        return any(p.device == port for p in serial.tools.list_ports.comports())

    # ═══════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"'{self.port_description}', "
            f"state='{self._state}', "
            f"timeout={self._timeout}s"
            f")"
        )

    def get_info(self) -> dict[str, Any]:
        """获取串口驱动信息"""
        info = super().get_info()
        info.update(
            {
                "port": self._port,
                "baudrate": self._baudrate,
                "data_bits": self._data_bits,
                "stop_bits": self._stop_bits,
                "parity": self._parity,
                "rtscts": self._rtscts,
                "dsrdtr": self._dsrdtr,
                "hotplug": self._hotplug_enabled,
                "input_buffer_size": self._input_buffer_size,
                "output_buffer_size": self._output_buffer_size,
            }
        )
        return info
