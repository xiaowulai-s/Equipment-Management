# -*- coding: utf-8 -*-
"""
命令终端组件 - 紧凑嵌入式版本，用于嵌入监控页面
Embedded Command Terminal Component for Monitor Page (with Modbus frame parsing + DMT143 support)
"""

from __future__ import annotations

import logging
import math
import struct
import threading
import time
from collections import deque
from datetime import datetime
from enum import IntEnum
from typing import Any

from PySide6.QtCore import Qt, QEvent, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.widgets import PrimaryButton, SecondaryButton

logger = logging.getLogger(__name__)

# ==================== 模块级常量 ====================

MODBUS_TCP_HEADER_SIZE = 7  # Transaction(2) + Proto(2) + Length(2) + Unit(1)
MODBUS_MIN_FRAME_SIZE = MODBUS_TCP_HEADER_SIZE + 2  # 最小PDU: FC + Data
MODBUS_PROTO_ID = 0x0000  # Modbus协议标识符
MODBUS_MAX_PDU_LENGTH = 253  # TCP模式最大PDU长度
MODBUS_FC_READ_HOLDING = 0x03  # Read Holding Registers
MODBUS_FC_READ_INPUT = 0x04  # Read Input Registers
MODBUS_FC_WRITE_SINGLE = 0x06  # Write Single Register
MODBUS_FC_WRITE_MULTI = 0x10  # Write Multiple Registers

# F5: Modbus RTU 预留常量 (串口设备)
MODBUS_RTU_MIN_FRAME_SIZE = 4  # Addr(1)+FC(1)+Data(0min)+CRC(2)

# S9: PDU内字段偏移量 (相对于帧起始)
PDU_ADDR_OFFSET = MODBUS_TCP_HEADER_SIZE + 1  # 地址字段: byte[8]
PDU_COUNT_OFFSET = MODBUS_TCP_HEADER_SIZE + 3  # 计数字段: byte[10]

MAX_RX_BUFFER_BYTES = 64 * 1024  # 接收缓冲区上限 64KB
MAX_LOG_LINES = 5000  # 日志最大行数
MAX_INPUT_CHARS = 8192  # 输入框字符上限
BATCH_FLUSH_MS = 100  # 日志批量刷新间隔ms
DISPLAY_INLINE_MAX_LEN = 160  # 单行显示最大宽度
LOG_TRUNCATE_HEX = 150  # HEX日志截断长度
LOG_TRUNCATE_TEXT = 200  # 文本日志截断长度
TX_ADDR_QUEUE_DEPTH = 32  # 每设备TX地址队列深度
MAX_EXTRACT_ITERATIONS = 100  # 帧提取单次迭代上限
TS_CACHE_MS = 50  # 时间戳缓存间隔ms

COLOR_TX = "#58a6ff"
COLOR_RX = "#3fb950"
COLOR_ERR = "#f85149"
COLOR_WARN = "#D29922"
COLOR_INFO = "#8B949E"
COLOR_DEFAULT = "#c9d1d9"

LOG_COLOR_MAP = {
    "INFO": COLOR_INFO,
    "WARNING": COLOR_WARN,
    "ERROR": COLOR_ERR,
}


class DisplayMode(IntEnum):
    """通信日志显示模式枚举"""

    DMT143 = 0
    GENERIC = 1
    HEX = 2
    ASCII = 3

    @classmethod
    def from_name(cls, name: str) -> "DisplayMode":
        if cls._NAME_MAP is None:
            cls._NAME_MAP = {
                "DMT143解析": cls.DMT143,
                "通用帧解析": cls.GENERIC,
                "HEX": cls.HEX,
                "ASCII": cls.ASCII,
            }
        return cls._NAME_MAP.get(name, cls.GENERIC)


# V5: _NAME_MAP 在类定义外初始化（避免IntEnum将其视为枚举成员）
DisplayMode._NAME_MAP: dict[str, DisplayMode] | None = None

_LOG_STYLE = f"""
    QTextEdit {{
        background-color: #0d1117;
        color: {COLOR_DEFAULT};
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 11px;
        border: 1px solid #30363d;
        border-radius: 4px;
    }}
"""

_FC_NAMES = {
    0x01: "Read Coils",
    0x02: "Read Discrete Inputs",
    0x03: "Read Holding Registers",
    0x04: "Read Input Registers",
    0x05: "Write Single Coil",
    0x06: "Write Single Register",
    0x0F: "Write Multiple Coils",
    0x10: "Write Multiple Registers",
    0x81: "Error(Read Coils)",
    0x82: "Error(Read DI)",
    0x83: "Error(Read HR)",
    0x84: "Error(Read IR)",
    0x86: "Error(Write SR)",
    0x90: "Error(Write MR)",
}

_EC_NAMES = {
    0x01: "Illegal Function",
    0x02: "Illegal Data Address",
    0x03: "Illegal Data Value",
    0x04: "Server Device Failure",
}


# F11: DMT143协议数据提取为类属性
class DMT143Protocol:
    """Vaisala DMT143 露点变送器寄存器协议定义"""

    REGISTERS = {
        (0, 1): ("Dew Point Td", "\u00b0C", "float32"),
        (2, 3): ("Frost Point Tf", "\u00b0C", "float32"),
        (4, 5): ("Gas Temp T", "\u00b0C", "float32"),
        (6, 7): ("RH / Mix Ratio", "%RH", "float32"),
        (8, 9): ("Pressure P", "bar", "float32"),
    }
    ERROR_CODES = {
        1: "Temp measurement error",
        2: "Humidity measurement error",
        64: "Device settings corrupted",
        128: "Additional config corrupted",
        256: "Sensor coefficients corrupted",
        512: "Main config corrupted",
        2048: "Supply voltage out of range",
        65536: "NVM read/write failure",
        131072: "Firmware checksum mismatch",
    }
    SPECIAL_REGS = {
        0x203: ("ErrorCode", "", "uint32"),
        0x300: ("PressureSet", "bar", "float32"),
    }

    _ADDR_MAP: dict[int, tuple[str, str, str]] | None = None
    _SECOND_HALF_ADDRS: set[int] | None = None
    _lookup_lock = threading.Lock()

    @classmethod
    def _ensure_lookup(cls) -> None:
        if cls._ADDR_MAP is not None:
            return
        with cls._lookup_lock:
            if cls._ADDR_MAP is not None:
                return
            addr_map = {}
            second_half = set()
            for (start, end), info in cls.REGISTERS.items():
                addr_map[start] = info
                for a in range(start + 1, end + 1):
                    second_half.add(a)
            for addr, info in cls.SPECIAL_REGS.items():
                addr_map[addr] = info
            cls._ADDR_MAP = addr_map
            cls._SECOND_HALF_ADDRS = second_half

    @classmethod
    def get_register_info(cls, addr: int) -> tuple[str, str, str] | None:
        cls._ensure_lookup()
        return cls._ADDR_MAP.get(addr)

    @classmethod
    def is_second_half(cls, addr: int) -> bool:
        cls._ensure_lookup()
        return addr in cls._SECOND_HALF_ADDRS


class CommandTerminalWidget(QWidget):
    """
    命令终端 - 紧凑嵌入式版本（左右双栏日志 + Modbus帧解析 + DMT143）

    Signals:
        command_sent(str, bytes): 用户点击发送时触发。
            参数1 (str): 目标设备ID（来自device_combo当前选中项）
            参数2 (bytes): 编码后的原始字节数据
            注意：信号在UI线程中发射，接收方应避免阻塞操作
    """

    command_sent = Signal(str, bytes)

    def __init__(self, parent: QWidget | None = None, compact: bool = True) -> None:
        super().__init__(parent)
        self._compact = compact
        self._tx_count = 0
        self._rx_count = 0
        self._auto_scroll = True
        self._rx_buffer = bytearray()
        self._tx_addr_queues: dict[str, deque[int]] = {}
        self._batch_pending = False
        self._device_log_batch: list[str] = []
        self._comm_log_batch: list[str] = []
        self._destroyed = False
        self._rx_lock = threading.Lock()
        self._queue_lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._state_lock = threading.RLock()  # 新增: 保护状态变量
        self._flush_timer: QTimer | None = None  # 新增: 定时器引用
        self._ts_cached = ""
        self._ts_cache_time = 0.0
        self._last_display_mode: str = ""
        self._init_ui()

    # ==================== UI 初始化 ====================

    def _init_ui(self) -> None:
        m = 4 if self._compact else 12
        s = 6 if self._compact else 12
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(m, m, m, m)
        root_layout.setSpacing(s)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        device_label = QLabel("目标设备:")
        toolbar.addWidget(device_label)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(140 if self._compact else 180)
        toolbar.addWidget(self.device_combo)

        toolbar.addSpacing(12)

        enc_label = QLabel("编码:")
        toolbar.addWidget(enc_label)
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["ASCII", "HEX"])
        self.encoding_combo.setFixedWidth(70 if self._compact else 90)
        toolbar.addWidget(self.encoding_combo)

        disp_label = QLabel("显示:")
        toolbar.addWidget(disp_label)
        self.display_combo = QComboBox()
        self.display_combo.addItems(["DMT143解析", "通用帧解析", "HEX", "ASCII"])
        self.display_combo.setFixedWidth(100 if self._compact else 120)
        # F4: 显示模式切换时追加系统提示
        self.display_combo.currentIndexChanged.connect(self._on_display_mode_changed)
        toolbar.addWidget(self.display_combo)

        toolbar.addStretch()

        self.clear_input_btn = SecondaryButton("清空")
        self.send_btn = PrimaryButton("发送")
        toolbar.addWidget(self.clear_input_btn)
        toolbar.addWidget(self.send_btn)
        root_layout.addLayout(toolbar)

        self.command_input = QTextEdit()
        h = 60 if self._compact else 80
        self.command_input.setMinimumHeight(h)
        self.command_input.setMaximumHeight(h + (20 if not self._compact else 10))
        self.command_input.setPlaceholderText("输入命令 (ASCII文本或HEX字节序列)... (Ctrl+Enter发送)")
        # F10: Ctrl+Enter 快捷发送
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.command_input)
        shortcut.activated.connect(self._on_send_command)
        shortcut_enter = QShortcut(QKeySequence("Ctrl+\r"), self.command_input)
        shortcut_enter.activated.connect(self._on_send_command)
        root_layout.addWidget(self.command_input)

        self.clear_input_btn.clicked.connect(self.command_input.clear)
        self.send_btn.clicked.connect(self._on_send_command)

        log_bar = QHBoxLayout()
        scroll_lbl = QLabel("自动滚动: 开")
        scroll_lbl.setStyleSheet(f"color: {COLOR_INFO}; font-size: 11px;")
        scroll_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        scroll_lbl.installEventFilter(self)
        self._auto_scroll_label = scroll_lbl
        log_bar.addWidget(scroll_lbl)
        log_bar.addStretch()
        self.clear_log_btn = SecondaryButton("清空日志")
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        log_bar.addWidget(self.clear_log_btn)
        root_layout.addLayout(log_bar)

        log_splitter = QHBoxLayout()
        log_splitter.setSpacing(4)

        self.log_device = QTextEdit()
        self.log_device.setReadOnly(True)
        self.log_device.setStyleSheet(_LOG_STYLE)
        # F7: 启用默认右键菜单(复制/全选/搜索)
        self.log_device.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.log_device.setMinimumHeight(120 if self._compact else 250)
        log_splitter.addWidget(self.log_device, 1)

        self.log_comm = QTextEdit()
        self.log_comm.setReadOnly(True)
        self.log_comm.setStyleSheet(_LOG_STYLE)
        self.log_comm.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.log_comm.setMinimumHeight(120 if self._compact else 250)
        log_splitter.addWidget(self.log_comm, 1)

        root_layout.addLayout(log_splitter, 1)

    def closeEvent(self, event: QCloseEvent) -> None:
        with self._state_lock:
            self._destroyed = True
            self._batch_pending = False

            if self._flush_timer and self._flush_timer.isActive():
                self._flush_timer.stop()
                self._flush_timer = None

        logger.debug("CommandTerminal closing, resources cleaned up")
        with self._rx_lock:
            self._rx_buffer.clear()
        super().closeEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._auto_scroll_label and event.type() == QEvent.Type.MouseButtonPress:
            self._toggle_auto_scroll()
            return True
        return super().eventFilter(watched, event)

    @Slot(int)
    def _on_display_mode_changed(self, index: int) -> None:
        mode_name = self.display_combo.itemText(index)
        if mode_name == self._last_display_mode:
            return
        self._last_display_mode = mode_name
        mode = DisplayMode.from_name(mode_name)
        self.add_system_log(f"显示模式切换为: {mode_name}", "INFO")

    # ==================== 命令发送 ====================

    @Slot()
    def _on_send_command(self) -> None:
        text = self.command_input.toPlainText().strip()
        if not text:
            return

        if len(text) > MAX_INPUT_CHARS:
            self._add_comm_log("错误", f"输入过长 ({len(text)}>{MAX_INPUT_CHARS}字符)", COLOR_ERR)
            logger.warning("Command input too long: %d chars", len(text))
            return

        device_id = self._get_selected_device_id()
        if not device_id:
            self._add_comm_log("错误", "请选择目标设备", COLOR_ERR)
            return

        try:
            if self.encoding_combo.currentText() == "HEX":
                hex_data = text.replace(" ", "").replace("\n", "")
                if len(hex_data) % 2 != 0:
                    self._add_comm_log("错误", f"HEX长度必须为偶数 ({len(hex_data)}字符)", COLOR_ERR)
                    return
                try:
                    data = bytes.fromhex(hex_data)
                except ValueError:
                    self._add_comm_log("错误", "非法HEX字符", COLOR_ERR)
                    return
            else:
                data = text.encode("utf-8")

            if not data:
                self._add_comm_log("错误", "编码后数据为空", COLOR_ERR)
                return

            self.command_sent.emit(device_id, data)
            self._increment_tx()

            ts = self._timestamp()
            mode = DisplayMode.from_name(self.display_combo.currentText())
            ds = self._format_tx_display(data, mode)

            if self._is_modbus_tcp(data) and len(data) >= 12 and data[MODBUS_TCP_HEADER_SIZE] == MODBUS_FC_READ_HOLDING:
                req = self._parse_read_request(data)
                if req is not None:
                    _, addr, _ = req
                    self._push_tx_addr(device_id, addr)

            self._add_comm_log("TX", f"[{ts}] {ds}", COLOR_TX)
            # F8: 发送成功使用SUCCESS级别
            logger.debug("TX %s: %s", device_id, ds[:80])
        except Exception as e:
            self._add_comm_log("异常", str(e), COLOR_ERR)
            logger.exception("Send command failed")

    # ==================== 统一TX格式化 (F6: 使用公共FC描述方法) ====================

    def _format_tx_display(self, data: bytes, mode: DisplayMode) -> str:
        """统一TX帧显示格式化 (纯函数，不修改任何实例状态)"""
        if self._is_modbus_tcp(data):
            mbap = self._parse_mbap_header(data)
            req = self._parse_read_request(data)
            if req is not None:
                fc, addr, cnt = req
                trans_id = mbap[0]
                unit_id = mbap[3]

                if mode == DisplayMode.DMT143:
                    reg_desc = self._describe_dmt143_registers(addr, cnt)
                    return f"TX={trans_id} UID={unit_id} Read HR Addr={addr} N={cnt} [{reg_desc}]"
                elif mode == DisplayMode.GENERIC:
                    return f"TX={trans_id} UID={unit_id} Read Holding Registers Addr={addr} Count={cnt}"

            fc = data[MODBUS_TCP_HEADER_SIZE]
            if mode in (DisplayMode.DMT143, DisplayMode.GENERIC):
                return self._format_tx_frame(data, fc)

        if mode == DisplayMode.HEX:
            return data.hex(" ").upper()
        return data.decode("utf-8", errors="replace")

    # F6: 公共FC PDU描述方法
    @staticmethod
    def _parse_read_request(data: bytes) -> tuple[int, int, int] | None:
        """解析FC03/04请求的 (fc, addr, count)，返回None表示非读请求或数据不足"""
        if len(data) < MODBUS_TCP_HEADER_SIZE + 5:
            return None
        fc = data[MODBUS_TCP_HEADER_SIZE]
        if fc not in (MODBUS_FC_READ_HOLDING, MODBUS_FC_READ_INPUT):
            return None
        addr = struct.unpack(">H", data[PDU_ADDR_OFFSET : PDU_ADDR_OFFSET + 2])[0]
        cnt = struct.unpack(">H", data[PDU_COUNT_OFFSET : PDU_COUNT_OFFSET + 2])[0]
        return fc, addr, cnt

    @staticmethod
    def _describe_fc_payload(fc: int, data: bytes) -> list[str]:
        """返回功能码对应的PDU参数描述列表"""
        parts = []
        if fc in (MODBUS_FC_READ_HOLDING, MODBUS_FC_READ_INPUT) and len(data) >= 12:
            addr = struct.unpack(">H", data[PDU_ADDR_OFFSET : PDU_ADDR_OFFSET + 2])[0]
            cnt = struct.unpack(">H", data[PDU_COUNT_OFFSET : PDU_COUNT_OFFSET + 2])[0]
            parts.append(f"Addr={addr} Count={cnt}")
        elif fc == MODBUS_FC_WRITE_SINGLE and len(data) >= 12:
            addr = struct.unpack(">H", data[PDU_ADDR_OFFSET : PDU_ADDR_OFFSET + 2])[0]
            val = struct.unpack(">H", data[PDU_COUNT_OFFSET : PDU_COUNT_OFFSET + 2])[0]
            parts.append(f"Addr={addr} Val={val}")
        elif fc == MODBUS_FC_WRITE_MULTI and len(data) >= 13:
            addr = struct.unpack(">H", data[PDU_ADDR_OFFSET : PDU_ADDR_OFFSET + 2])[0]
            cnt = struct.unpack(">H", data[PDU_COUNT_OFFSET : PDU_COUNT_OFFSET + 2])[0]
            parts.append(f"Addr={addr} Count={cnt}")
        return parts

    # F1+F2+V3: 数据接收 - 锁内提取原始帧，锁外格式化+日志
    def add_received_data(self, data: bytes) -> None:
        """接收原始字节流数据（TCP驱动层）"""
        overflow_info = None
        raw_frames: list[bytes] = []
        with self._rx_lock:
            self._rx_buffer.extend(data)

            if len(self._rx_buffer) > MAX_RX_BUFFER_BYTES:
                buf_len = len(self._rx_buffer)
                self._rx_buffer.clear()
                overflow_info = buf_len
            else:
                raw_frames = self._extract_frames_collect()

        if overflow_info is not None:
            logger.warning("RX buffer overflow (%d bytes), discarding", overflow_info)
            self._add_comm_log("WARN", f"Buffer overflow, discarded {overflow_info}B", COLOR_WARN)
            return

        ts = self._timestamp()
        mode = DisplayMode.from_name(self.display_combo.currentText())
        device_id = self._get_selected_device_id()

        for frame in raw_frames:
            self._increment_rx()
            if mode == DisplayMode.DMT143:
                tx_addr = self._pop_tx_addr(device_id)
                parsed = self._parse_dmt143_response(frame, tx_addr)
                self._add_comm_log("RX", f"[{ts}] {parsed}", COLOR_RX)
            elif mode == DisplayMode.GENERIC:
                parsed = self._parse_modbus_tcp_response(frame)
                self._add_comm_log("RX", f"[{ts}] {parsed}", COLOR_RX)
            elif mode == DisplayMode.HEX:
                self._add_comm_log("RX", f"[{ts}] {frame.hex(' ').upper()}", COLOR_RX)
            else:
                try:
                    text = frame.decode("utf-8", errors="replace")
                    self._add_comm_log("RX", f"[{ts}] {text}", COLOR_RX)
                except Exception:
                    logger.debug("UTF-8解码失败，使用hex显示")
                    self._add_comm_log("RX", f"[{ts}] {frame.hex(' ').upper()}", COLOR_RX)

        raw_entries = self._check_raw_residual()
        for entry in raw_entries:
            self._increment_rx()
            self._add_comm_log(entry["level"], f"[{entry['ts']}] {entry['text']}", entry["color"])

    def add_protocol_data(self, data: dict[str, Any]) -> None:
        """接收协议层解析后的数据（模拟器/轮询数据）"""
        self._increment_rx()
        ts = self._timestamp()
        mode = DisplayMode.from_name(self.display_combo.currentText())

        if mode in (DisplayMode.DMT143, DisplayMode.GENERIC):
            parsed = self._format_protocol_data_dmt143(data)
            self._add_comm_log("RX", f"[{ts}] {parsed}", COLOR_RX)
        elif mode == DisplayMode.HEX:
            hex_str = str(data).replace(" ", "")[:LOG_TRUNCATE_HEX]
            self._add_comm_log("RX", f"[{ts}] {hex_str}", COLOR_RX)
        else:
            self._add_comm_log("RX", f"[{ts}] {str(data)[:LOG_TRUNCATE_TEXT]}", COLOR_RX)

    # ==================== 帧提取 (F2重构: 收集模式) ====================

    @staticmethod
    def _is_modbus_tcp(data: bytes, min_pdu_size: int = 1) -> bool:
        return (
            len(data) >= MODBUS_TCP_HEADER_SIZE + min_pdu_size
            and data[2] == (MODBUS_PROTO_ID >> 8 & 0xFF)
            and data[3] == (MODBUS_PROTO_ID & 0xFF)
        )

    # F5: RTU检测预留接口 (S5: TODO - 需集成到 _extract_frames_collect 的 else 分支)
    @staticmethod
    def _is_modbus_rtu(data: bytes) -> bool:
        """检测是否为Modbus RTU帧（预留，串口设备扩展用）"""
        return len(data) >= MODBUS_RTU_MIN_FRAME_SIZE and data[0] > 0 and data[0] <= 247

    @staticmethod
    def _parse_mbap_header(frame: bytes) -> tuple[int, int, int, int]:
        trans_id = struct.unpack(">H", frame[0:2])[0]
        proto_id = struct.unpack(">H", frame[2:4])[0]
        length = struct.unpack(">H", frame[4:6])[0]
        unit_id = frame[6]
        return trans_id, proto_id, length, unit_id

    @staticmethod
    def _peek_mbap_header(buf: bytearray) -> tuple[int, int, int, int]:
        return (
            struct.unpack(">H", buf[0:2])[0],
            struct.unpack(">H", buf[2:4])[0],
            struct.unpack(">H", buf[4:6])[0],
            buf[6],
        )

    # F2+V3: 帧提取 - 锁内仅收集原始字节帧，锁外格式化
    def _extract_frames_collect(self) -> list[bytes]:
        """在 _rx_lock 内调用，仅从缓冲区提取原始帧字节（不含格式化/日志）"""
        raw_frames = []
        for _ in range(MAX_EXTRACT_ITERATIONS):
            if len(self._rx_buffer) < MODBUS_MIN_FRAME_SIZE:
                break

            trans_id, proto_id, length, unit_id = self._peek_mbap_header(self._rx_buffer)

            is_modbus_tcp = (
                proto_id == MODBUS_PROTO_ID
                and 6 <= length <= MODBUS_MAX_PDU_LENGTH
                and len(self._rx_buffer) >= 6 + length
            )

            if is_modbus_tcp:
                frame_size = 6 + length
                frame = bytes(self._rx_buffer[:frame_size])
                del self._rx_buffer[:frame_size]
                raw_frames.append(frame)
            else:
                break

        return raw_frames

    # V6: 残余数据检查 - 调用顺序不变量: 必须在 _extract_frames_collect 之后调用
    # 因为 _extract_frames_collect 在无法识别完整帧时会 break 留下残余字节
    def _check_raw_residual(self) -> list[dict]:
        """检查并处理缓冲区中的残余非Modbus数据（调用方负责 _rx_count 计数）"""
        with self._rx_lock:
            has_residual = 0 < len(self._rx_buffer) < MODBUS_MIN_FRAME_SIZE
            if has_residual:
                raw = bytes(self._rx_buffer)
                self._rx_buffer.clear()
            else:
                raw = b""

        if not has_residual or not raw:
            return []

        ts = self._timestamp()
        mode = DisplayMode.from_name(self.display_combo.currentText())
        if mode == DisplayMode.HEX:
            return [{"level": "RX", "ts": ts, "text": f"{raw.hex(' ').upper()} (raw)", "color": COLOR_RX}]
        else:
            try:
                text = raw.decode("utf-8", errors="replace")
                return [{"level": "RX", "ts": ts, "text": f"{text} (raw)", "color": COLOR_RX}]
            except Exception:
                logger.debug("原始数据UTF-8解码失败，使用hex显示")
                return [{"level": "RX", "ts": ts, "text": f"{raw.hex(' ').upper()} (raw)", "color": COLOR_RX}]

    # ==================== TX帧格式化 (F6重构) ====================

    def _format_tx_frame(self, data: bytes, fc: int = 0) -> str:
        if not self._is_modbus_tcp(data):
            return data.hex(" ").upper()

        if fc == 0:
            fc = data[MODBUS_TCP_HEADER_SIZE]

        trans_id, _, _, unit_id = self._parse_mbap_header(data)
        fc_name = _FC_NAMES.get(fc, f"FC:{fc:#04X}")
        parts = [f"TX={trans_id} UID={unit_id} {fc_name}"]

        parts.extend(self._describe_fc_payload(fc, data))

        return f"{' | '.join(parts)} [{data.hex(' ').upper()}]"

    # ==================== Modbus TCP应答解析 ====================

    def _parse_modbus_tcp_response(self, frame: bytes) -> str:
        trans_id, _, _, unit_id = self._parse_mbap_header(frame)
        pdu = frame[MODBUS_TCP_HEADER_SIZE:]

        if not pdu:
            return f"Empty PDU [TX={trans_id} UID={unit_id}]"

        fc = pdu[0]
        fc_name = _FC_NAMES.get(fc, f"FC:{fc:#04X}")
        parts = [f"RX={trans_id} UID={unit_id} {fc_name}"]

        if fc & 0x80:
            ec = pdu[1] if len(pdu) > 1 else 0
            ec_name = _EC_NAMES.get(ec, f"Code:{ec:#02X}")
            parts.append(f"ERR: {ec_name}")
        else:
            byte_count = pdu[1] if len(pdu) > 1 else 0
            reg_data = pdu[2:] if len(pdu) > 2 else b""
            if byte_count > 0 and len(reg_data) >= byte_count:
                vals = []
                for i in range(0, min(byte_count, len(reg_data)), 2):
                    if i + 1 < len(reg_data):
                        v = struct.unpack(">H", reg_data[i : i + 2])[0]
                        vals.append(str(v))
                if vals:
                    parts.append(f"Data=[{', '.join(vals)}]")
                else:
                    parts.append(f"Data={reg_data.hex(' ').upper()}")
            elif len(pdu) > 2:
                parts.append(f"Data={pdu[2:].hex(' ').upper()}")

        return f"{' | '.join(parts)} [{frame.hex(' ').upper()}]"

    # ==================== DMT143应答解析 ====================

    def _parse_dmt143_response(self, frame: bytes, tx_addr: int = 0) -> str:
        """解析DMT143专用应答帧"""
        trans_id, _, _, unit_id = self._parse_mbap_header(frame)
        pdu = frame[MODBUS_TCP_HEADER_SIZE:]

        if not pdu:
            return f"DMT143 Empty PDU [TX={trans_id} UID={unit_id}]"

        fc = pdu[0]
        fc_name = _FC_NAMES.get(fc, f"FC:{fc:#04X}")

        if fc & 0x80:
            ec = pdu[1] if len(pdu) > 1 else 0
            ec_name = _EC_NAMES.get(ec, f"Code:{ec:#02X}")
            return f"DMT143 RX={trans_id} UID={unit_id} ERR: {ec_name} [{frame.hex(' ').upper()}]"

        if fc != MODBUS_FC_READ_HOLDING:
            return self._parse_modbus_tcp_response(frame)

        byte_count = pdu[1] if len(pdu) > 1 else 0
        reg_data = pdu[2:] if len(pdu) > 2 else b""

        if byte_count <= 0 or len(reg_data) < byte_count:
            return f"DMT143 RX={trans_id} UID={unit_id} Read HR (empty/short) [{frame.hex(' ').upper()}]"

        header = f"DMT143 RX={trans_id} UID={unit_id}"
        values = []
        num_regs = byte_count // 2

        for i in range(num_regs):
            reg_addr = tx_addr + i
            if self._is_dmt143_register_second_half(reg_addr):
                continue
            raw_val = struct.unpack(">H", reg_data[i * 2 : i * 2 + 2])[0]
            reg_info = self._get_dmt143_register_info(reg_addr)
            if reg_info:
                name, unit, fmt = reg_info
                if name == "ErrorCode" and fmt == "uint32":
                    if i * 2 + 4 <= len(reg_data):
                        full_val = struct.unpack(">I", reg_data[i * 2 : i * 2 + 4])[0]
                    else:
                        full_val = raw_val
                    err_desc = DMT143Protocol.ERROR_CODES.get(full_val, f"Unknown(0x{full_val:X})")
                    values.append(f"{name}=0x{full_val:#010X}({err_desc})")
                    continue
                if fmt == "float32" and i * 2 + 4 <= len(reg_data):
                    try:
                        float_val = struct.unpack(">f", reg_data[i * 2 : i * 2 + 4])[0]
                        values.append(self._format_float_value(name, unit, float_val, raw_val))
                    except Exception:
                        logger.debug("float32解包失败，使用原始值")
                        values.append(f"{name}=0x{raw_val:#06X}{unit}")
                else:
                    values.append(f"{name}={raw_val}{unit}")
            else:
                values.append(f"Reg[{reg_addr}]=0x{raw_val:#06X}")

        result_str = f"{header} {' | '.join(values)}"
        if len(result_str) > DISPLAY_INLINE_MAX_LEN:
            hex_str = frame.hex(" ").upper()
            result_str = f"{header} [{hex_str}]"
            for v in values:
                result_str += f"\n  \u25b8 {v}"
        else:
            result_str += f" [{frame.hex(' ').upper()}]"
        return result_str

    @staticmethod
    def _format_float_value(name: str, unit: str, value: float, fallback: int) -> str:
        if math.isfinite(value):
            return f"{name}={value:.2f}{unit}"
        elif math.isnan(value):
            return f"{name}=NaN{unit}"
        else:
            sign = "+" if value > 0 else "-"
            return f"{name}={sign}Inf{unit}"

    # ==================== DMT143寄存器查询 ====================

    def _get_dmt143_register_info(self, addr: int) -> tuple[str, str, str] | None:
        return DMT143Protocol.get_register_info(addr)

    def _is_dmt143_register_second_half(self, addr: int) -> bool:
        return DMT143Protocol.is_second_half(addr)

    def _describe_dmt143_registers(self, start_addr: int, count: int) -> str:
        regs = []
        i = 0
        while i < count:
            addr = start_addr + i
            if self._is_dmt143_register_second_half(addr):
                i += 1
                continue
            info = self._get_dmt143_register_info(addr)
            if info:
                name, unit, fmt = info
                regs.append(f"{name}({fmt})")
                if fmt == "float32":
                    i += 2
                    continue
            else:
                regs.append(f"Reg[{addr}]")
            i += 1
        return "+".join(regs) if regs else f"Reg[{start_addr}..{start_addr+count-1}]"

    # ==================== 协议层数据格式化 ====================

    def _format_protocol_data_dmt143(self, data: dict[str, Any]) -> str:
        parts = ["Protocol"]
        for key, val in data.items():
            if isinstance(val, dict):
                inner = val.get("value", val.get("raw", "?"))
                unit = val.get("unit", "")
                if isinstance(inner, list):
                    inner_str = ",".join(str(v) for v in inner[:5])
                else:
                    try:
                        inner_str = f"{float(inner):.2f}"
                    except (ValueError, TypeError, OverflowError):
                        inner_str = str(inner)
                label = key.replace("_", " ").title()
                parts.append(f"{label}={inner_str}{unit}" if unit else f"{label}={inner_str}")
            else:
                parts.append(f"{key}={val}")
        return " | ".join(parts)

    # ==================== 按设备TX地址队列 ====================

    def _push_tx_addr(self, device_id: str, addr: int) -> None:
        if not device_id:
            return
        with self._queue_lock:
            if device_id not in self._tx_addr_queues:
                self._tx_addr_queues[device_id] = deque(maxlen=TX_ADDR_QUEUE_DEPTH)
            self._tx_addr_queues[device_id].append(addr)

    def _pop_tx_addr(self, device_id: str) -> int:
        if not device_id:
            return 0
        with self._queue_lock:
            if device_id not in self._tx_addr_queues:
                return 0
            q = self._tx_addr_queues[device_id]
            return q.popleft() if q else 0

    # ==================== 日志系统 ====================

    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def add_system_log(self, message: str, level: str = "INFO") -> None:
        ts = self._timestamp()
        color = LOG_COLOR_MAP.get(level, COLOR_INFO)
        self._add_device_log(level, f"[{ts}] {message}", color)

    def _add_device_log(self, level: str, message: str, color: str = COLOR_DEFAULT) -> None:
        safe_msg = self._escape_html(message)
        html = (
            f'<span style="color:{color};font-size:11px;">[{level}]</span> '
            f'<span style="color:{COLOR_DEFAULT};font-size:11px;">{safe_msg}</span>'
        )
        with self._log_lock:
            self._device_log_batch.append(html)
        self._schedule_flush()

    def _add_comm_log(self, level: str, message: str, color: str = COLOR_DEFAULT) -> None:
        safe_msg = self._escape_html(message)
        html = (
            f'<span style="color:{color};font-size:11px;">[{level}]</span> '
            f'<span style="color:{COLOR_DEFAULT};font-size:11px;">{safe_msg}</span>'
        )
        with self._log_lock:
            self._comm_log_batch.append(html)
        self._schedule_flush()

    def _schedule_flush(self) -> None:
        with self._state_lock:
            if self._batch_pending or self._destroyed:
                return
            self._batch_pending = True

        if self._flush_timer is None:
            self._flush_timer = QTimer(self)
            self._flush_timer.setSingleShot(True)
            self._flush_timer.timeout.connect(self._flush_log_batches)

        self._flush_timer.start(BATCH_FLUSH_MS)

    def _flush_log_batches(self) -> None:
        with self._state_lock:
            if self._destroyed:
                return
            self._batch_pending = False

        device_batch: list[str] = []
        comm_batch: list[str] = []
        with self._log_lock:
            if self._device_log_batch:
                device_batch = self._device_log_batch[:]
                self._device_log_batch.clear()
            if self._comm_log_batch:
                comm_batch = self._comm_log_batch[:]
                self._comm_log_batch.clear()

        if device_batch:
            self.log_device.append("<br>".join(device_batch))
            self._trim_log(self.log_device)
            if self._auto_scroll:
                self.log_device.verticalScrollBar().setValue(self.log_device.verticalScrollBar().maximum())

        if comm_batch:
            self.log_comm.append("<br>".join(comm_batch))
            self._trim_log(self.log_comm)
            if self._auto_scroll:
                self.log_comm.verticalScrollBar().setValue(self.log_comm.verticalScrollBar().maximum())

    # F3: 分级日志裁剪策略
    def _trim_log(self, widget: QTextEdit) -> None:
        doc = widget.document()
        total = doc.blockCount()
        if total <= MAX_LOG_LINES:
            return
        # 严重超限(>200%): 用setPlainText整体替换，避免大量增量删除
        if total > MAX_LOG_LINES * 2:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.KeepAnchor, MAX_LOG_LINES)
            remaining = cursor.selectedText()
            widget.setPlainText(remaining)
        else:
            # 轻度超限: 用增量删除，保留滚动位置和选择状态
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, total - MAX_LOG_LINES)
            cursor.removeSelectedText()

    def _toggle_auto_scroll(self) -> None:
        self._auto_scroll = not self._auto_scroll
        state = "\u5f00" if self._auto_scroll else "\u5173"
        self._auto_scroll_label.setText(f"\u81ea\u52a8\u6eda\u52a8: {state}")

    def _timestamp(self) -> str:
        now = time.time()
        if now - self._ts_cache_time > TS_CACHE_MS / 1000.0:
            self._ts_cached = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._ts_cache_time = now
        return self._ts_cached

    # ==================== 公共接口 ====================

    # V11: RX计数器统一入口（便于未来添加速率统计等功能）
    def _increment_rx(self) -> None:
        self._rx_count += 1

    # S3: TX计数器统一入口
    def _increment_tx(self) -> None:
        self._tx_count += 1

    @Slot()
    def _on_clear_log(self) -> None:
        self.log_device.clear()
        self.log_comm.clear()
        with self._rx_lock:
            self._rx_buffer.clear()
        self._device_log_batch.clear()
        self._comm_log_batch.clear()
        self._batch_pending = False
        logger.info("Logs cleared")

    def _get_selected_device_id(self) -> str:
        idx = self.device_combo.currentIndex()
        if idx >= 0:
            return self.device_combo.currentData(Qt.ItemDataRole.UserRole) or ""
        return ""

    def update_device_list(self, devices: list[dict]) -> None:
        active_ids = {d.get("device_id", "") for d in devices}
        with self._queue_lock:
            stale_ids = set(self._tx_addr_queues.keys()) - active_ids
            for stale_id in stale_ids:
                del self._tx_addr_queues[stale_id]
                logger.debug("Cleaned stale TX queue for device: %s", stale_id)

        current_id = self._get_selected_device_id()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for dev in devices:
            name = dev.get("name", "-")
            did = dev.get("device_id", "")
            st = dev.get("status", "")
            icon = "\u25cf" if st in ("CONNECTED", "connected", 2) else "\u25cb"
            self.device_combo.addItem(f"{icon} {name}", did)
        self.device_combo.blockSignals(False)
        if current_id:
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == current_id:
                    self.device_combo.setCurrentIndex(i)
                    break

    def get_tx_count(self) -> int:
        return self._tx_count

    def get_rx_count(self) -> int:
        return self._rx_count

    # F9: reset_counters 清除时间戳缓存
    def reset_counters(self) -> None:
        self._tx_count = 0
        self._rx_count = 0
        self._ts_cached = ""
        self._ts_cache_time = 0.0
        self._last_display_mode = ""
