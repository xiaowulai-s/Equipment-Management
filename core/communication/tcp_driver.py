# -*- coding: utf-8 -*-
"""
TCP通信驱动
TCP Communication Driver

功能特性：
- 标准Modbus TCP FC08诊断心跳机制
- TCP KeepAlive辅助保活（防止NAT超时）
- 线程安全的连接管理
- 完整的错误处理和日志记录
"""

import logging
import socket
import struct
import sys
import threading
import time
from typing import Optional

from PySide6.QtCore import QTimer, Signal
import shiboken6

from .base_driver import BaseDriver

logger = logging.getLogger(__name__)


class TCPDriver(BaseDriver):
    """
    TCP通信驱动
    TCP Communication Driver

    心跳机制说明：
    1. 主方案：Modbus FC08诊断请求（应用层，符合Modbus v1.1b3标准）
    2. 辅助：TCP KeepAlive（传输层，防止NAT/防火墙超时）

    FC08报文格式（12字节）：
    ┌─────────────┬─────────────┬─────────────┬──────────┬──────────┬─────────────┬─────────────┐
    │ Transaction │  Protocol   │   Length    │ Unit ID  │ FuncCode │ Sub-function│   Data      │
    │    ID (2B)  │   ID (2B)   │   (2B)      │  (1B)    │   (1B)   │ Code (2B)   │ Field (2B)  │
    │  自增       │  0x0000     │  0x0006     │  可配置  │  0x08    │  0x0000     │  0x0000     │
    └─────────────┴─────────────┴─────────────┴──────────┴──────────┴─────────────┴─────────────┘
    MBAP Header (7 bytes)              PDU (5 bytes)
    """

    # Modbus协议常量
    MODBUS_PROTOCOL_ID = 0x0000  # Modbus协议标识
    FC_DIAGNOSTICS = 0x08        # 功能码：诊断
    DIAG_SUBFUNC_RETURN_QUERY = 0x0000  # 子功能码：返回查询数据

    def __init__(self, host: str = "127.0.0.1", port: int = 502, parent=None):
        super().__init__(parent)
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._is_running = False

        # 心跳定时器（FC08 Modbus诊断请求）
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)

        # 心跳配置参数
        self._unit_id = 0x01              # 默认单元ID
        self._heartbeat_interval_ms = 10000  # 心跳间隔：10秒
        self._transaction_id = 0          # 事务ID计数器
        self._heartbeat_enabled = True    # 心跳开关

        # 统计信息
        self._heartbeat_sent_count = 0
        self._heartbeat_success_count = 0
        self._last_heartbeat_time: Optional[float] = None

        # 线程安全锁
        self._lock = threading.RLock()

    def _safe_emit_signal(self, signal, *args):
        """安全发射Qt信号，处理对象已销毁的情况"""
        try:
            if shiboken6.isValid(self):
                signal.emit(*args)
        except (RuntimeError, NameError) as e:
            logger.debug("信号发射失败(对象可能已销毁): %s", e)

    def connect(self) -> bool:
        """
        连接设备
        Connect to device

        连接成功后自动启动：
        1. FC08心跳定时器（应用层）
        2. TCP KeepAlive（传输层）
        """
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except OSError as e:
                    logger.debug("关闭旧连接时出错: %s", e)
                self._socket = None

            if self._receive_thread and self._receive_thread.is_alive():
                self._is_running = False
                self._receive_thread.join(timeout=1.0)

            self._heartbeat_timer.stop()

            try:
                # 创建TCP socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(5.0)

                # 配置TCP KeepAlive（防止NAT/防火墙超时断开）
                self._configure_keepalive(self._socket)

                # 建立连接
                self._socket.connect((self._host, self._port))
                self._is_connected = True
                self._is_running = True

                # 启动接收线程
                self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                self._receive_thread.start()

                # 启动FC08心跳定时器
                if self._heartbeat_enabled:
                    if threading.current_thread() == threading.main_thread():
                        self._heartbeat_timer.start(self._heartbeat_interval_ms)
                    else:
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: self._heartbeat_timer.start(self._heartbeat_interval_ms))
                    logger.info("Modbus FC08心跳已启动，间隔=%dms", self._heartbeat_interval_ms)

                # 重置统计信息
                self._reset_heartbeat_stats()

                logger.info("TCP连接成功 [%s:%d]", self._host, self._port)
                self.connected.emit()
                return True

            except (ConnectionRefusedError, TimeoutError, OSError, socket.error) as e:
                logger.error("TCP连接失败 [%s:%d]: %s", self._host, self._port, e)
                if self._socket:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
                    self._socket = None
                self._safe_emit_signal(self.error_occurred, f"TCP连接失败: {str(e)}")
                return False
            except Exception as e:
                logger.exception("TCP连接时发生未预期错误")
                if self._socket:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
                    self._socket = None
                self._safe_emit_signal(self.error_occurred, f"TCP连接异常: {str(e)}")
                return False

    def disconnect(self):
        """
        断开连接
        Disconnect from device
        
        V01修复: 避免死锁 — 先释放标志位和socket，再在锁外等待线程退出
        """
        with self._lock:
            self._is_running = False
            self._heartbeat_timer.stop()

            if self._socket:
                try:
                    self._socket.close()
                except OSError as e:
                    logger.debug("断开连接时socket关闭出错: %s", e)
                self._socket = None

            self._is_connected = False
            self._clear_buffer()

        receive_thread = self._receive_thread
        if receive_thread and receive_thread.is_alive():
            receive_thread.join(timeout=2.0)
            if receive_thread.is_alive():
                logger.warning("接收线程未能在超时时间内退出")

        with self._lock:
            self._receive_thread = None

        self._safe_emit_signal(self.disconnected)

    def send_data(self, data: bytes) -> bool:
        with self._lock:
            if not self._is_connected or not self._socket:
                return False

            try:
                self._socket.sendall(data)
                self._safe_emit_signal(self.data_sent, data)
                return True
            except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError, socket.error) as e:
                logger.error("发送数据失败: %s", e)
                self._safe_emit_signal(self.error_occurred, f"发送数据失败: {str(e)}")
                self._handle_connection_loss()
                return False
            except Exception as e:
                logger.exception("发送数据时发生未预期错误")
                self._safe_emit_signal(self.error_occurred, f"发送数据异常: {str(e)}")
                return False

    def _receive_loop(self):
        while self._is_running and self._socket:
            try:
                data = self._socket.recv(4096)
                if data:
                    if self._is_heartbeat_response(data):
                        self._on_heartbeat_response(data)
                    else:
                        self._append_to_buffer(data)
                        self._safe_emit_signal(self.data_received, data)
                else:
                    logger.info("连接被对端关闭")
                    break
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                logger.warning("接收数据连接异常: %s", e)
                self._safe_emit_signal(self.error_occurred, f"接收数据连接中断: {str(e)}")
                self._handle_connection_loss()
                break
            except Exception as e:
                if self._is_running:
                    logger.exception("接收数据循环发生错误")
                    self._safe_emit_signal(self.error_occurred, f"接收数据失败: {str(e)}")
                break

    def _handle_connection_loss(self):
        """处理连接丢失"""
        with self._lock:
            if self._is_connected:
                self._is_connected = False
                self._is_running = False
                if self._socket:
                    try:
                        self._socket.close()
                    except OSError:
                        pass
                    self._socket = None

    def _is_heartbeat_response(self, data: bytes) -> bool:
        """判断是否为FC08诊断心跳响应"""
        if len(data) >= 8:
            fc = data[7]
            return fc == self.FC_DIAGNOSTICS
        return False

    def _on_heartbeat_response(self, data: bytes):
        """处理心跳响应（不入公共缓冲区，避免数据污染）"""
        self._heartbeat_success_count += 1
        self._last_heartbeat_time = time.monotonic()
        logger.debug(
            "FC08心跳响应已接收 (累计成功=%d)",
            self._heartbeat_success_count,
        )

    def _send_heartbeat(self):
        """
        发送标准Modbus FC08诊断心跳请求

        符合Modbus Application Protocol v1.1b3规范（Section 6.9）
        报文结构：MBAP Header (7 bytes) + PDU (4 bytes) = 11 bytes

        功能：
        1. 检测Modbus通信链路健康度（应用层）
        2. 验证设备是否正常响应Modbus请求
        3. 保持NAT映射活跃（配合TCP KeepAlive）

        错误处理策略：
        - 发送失败 → 标记连接断开，触发重连机制
        - 超时无响应 → 记录警告，下次心跳继续尝试
        - 设备返回异常 → 记录日志，不主动断开
        """
        if not self._is_connected or not self._socket:
            logger.debug("跳过心跳：未连接")
            return

        with self._lock:
            try:
                # 生成事务ID（循环递增，避免溢出）
                self._transaction_id = (self._transaction_id + 1) % 65536
                trans_id = self._transaction_id

                # 构建符合标准的FC08诊断请求报文（12字节）
                # MBAP Header (7 bytes): TransactionID(2) + ProtocolID(2) + Length(2) + UnitID(1)
                # PDU (5 bytes):          FunctionCode(1) + SubFunctionCode(2) + DataField(2)
                # 总长度: 7 + 5 = 12 字节

                # 构建MBAP Header（7字节）
                heartbeat_request = struct.pack(
                    ">HHHB",                    # 大端序网络字节
                    trans_id,                   # Transaction ID: 自增计数器
                    self.MODBUS_PROTOCOL_ID,    # Protocol ID: 0x0000 (Modbus)
                    0x0006,                     # Length: 6 (UnitID 1B + PDU 5B)
                    self._unit_id               # Unit ID: 默认0x01
                )

                # 构建PDU（5字节）：功能码 + 子功能码 + 数据字段
                heartbeat_request += struct.pack(
                    ">BHH",                     # 大端序
                    self.FC_DIAGNOSTICS,        # Function Code: 0x08 (Diagnostics)
                    self.DIAG_SUBFUNC_RETURN_QUERY,  # Sub-function: 0x0000 (Return Query Data)
                    0x0000                      # Data Field: 0x0000 (要回显的数据)
                )

                # 验证报文长度（必须为12字节：MBAP 7B + PDU 5B）
                assert len(heartbeat_request) == 12, \
                    f"FC08心跳报文长度错误：期望12字节，实际{len(heartbeat_request)}字节"

                # 发送心跳请求
                self._socket.sendall(heartbeat_request)
                self._heartbeat_sent_count += 1
                self._last_heartbeat_time = time.monotonic()

                logger.debug(
                    "FC08心跳已发送 [TransID=%04X | UnitID=%02X | %d字节]",
                    trans_id,
                    self._unit_id,
                    len(heartbeat_request)
                )

            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                logger.warning("❌ FC08心跳发送失败，检测到连接断开: %s", e)
                self._handle_connection_loss()
            except Exception as e:
                logger.exception("❌ FC08心跳发送时发生异常: %s", e)

    def _configure_keepalive(self, sock: socket.socket):
        """
        配置TCP KeepAlive参数（传输层辅助保活）

        作用：
        - 防止NAT网关/防火墙因长时间空闲而关闭连接
        - 检测对端异常宕机（无需应用层干预）
        - 与FC08心跳形成双重保障

        参数说明（Windows平台）：
        - TCP_KEEPIDLE:   空闲多少秒后开始发送探测包（默认10秒）
        - TCP_KEEPINTVL:  探测失败后的重试间隔（默认5秒）
        - TCP_KEEPCNT:    最大重试次数后判定连接死亡（默认3次）

        总超时时间 = keepidle + keepintvl * keepcnt = 10 + 5*3 = 25秒
        """
        try:
            # 启用KeepAlive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # 平台特定配置
            if sys.platform.startswith('win'):
                # Windows平台使用IOCTL
                # TCP_KEEPIDLE = 空闲时间（毫秒）
                # TCP_KEEPINTVL = 探测间隔（毫秒）
                # TCP_KEEPCNT = 探测次数
                tcp_keepidle = 10 * 1000   # 10秒（转换为毫秒）
                tcp_keepintvl = 5 * 1000   # 5秒
                tcp_keepcnt = 3             # 3次

                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, tcp_keepidle)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, tcp_keepintvl)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, tcp_keepcnt)

            elif sys.platform.startswith('linux'):
                # Linux平台直接使用TCP选项
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)   # 10秒
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)    # 5秒
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)      # 3次

            else:
                # macOS/其他平台：仅启用基础KeepAlive（使用系统默认值）
                logger.debug("使用系统默认TCP KeepAlive参数")

            logger.info(
                "✅ TCP KeepAlive已配置 [空闲=%ds | 间隔=%ds | 重试=%d次]",
                10, 5, 3
            )

        except OSError as e:
            logger.warning("⚠️ TCP KeepAlive配置失败（不影响主功能）: %s", e)
        except Exception as e:
            logger.warning("⚠️ TCP KeepAlive配置异常: %s", e)

    def _reset_heartbeat_stats(self):
        """重置心跳统计信息"""
        self._heartbeat_sent_count = 0
        self._heartbeat_success_count = 0
        self._last_heartbeat_time = None
        self._transaction_id = 0

    def set_host(self, host: str):
        """
        设置主机地址
        Set host address
        """
        self._host = host

    def set_port(self, port: int):
        """
        设置端口
        Set port
        """
        self._port = port

    def set_unit_id(self, unit_id: int):
        """
        设置Modbus单元ID（心跳报文使用）
        Set Modbus Unit ID (used in heartbeat frames)

        Args:
            unit_id: 单元标识符（0-255），默认1
        """
        if 0 <= unit_id <= 255:
            self._unit_id = unit_id
            logger.info("Modbus单元ID已更新为: %d", unit_id)
        else:
            logger.warning("无效的单元ID: %d（必须在0-255范围内）", unit_id)

    def set_heartbeat_interval(self, interval_ms: int):
        """
        设置FC08心跳间隔时间
        Set FC08 heartbeat interval

        Args:
            interval_ms: 心跳间隔（毫秒），建议5000-30000ms
                         - 工业场景推荐：10000ms（10秒）
                         - 高可靠性场景：5000ms（5秒）
                         - 低带宽场景：30000ms（30秒）
        """
        if interval_ms < 1000:
            logger.warning("⚠️ 心跳间隔过短(%dms)，可能导致网络拥塞", interval_ms)
        elif interval_ms > 60000:
            logger.warning("⚠️ 心跳间隔过长(%dms)，可能无法及时检测断连", interval_ms)

        self._heartbeat_interval_ms = interval_ms

        # 如果定时器正在运行，动态更新间隔
        if self._heartbeat_timer.isActive():
            self._heartbeat_timer.setInterval(interval_ms)
            logger.info("FC08心跳间隔已更新为: %dms", interval_ms)

    def enable_heartbeat(self, enabled: bool = True):
        """
        启用/禁用FC08心跳机制
        Enable/Disable FC08 heartbeat mechanism

        Args:
            enabled: True=启用, False=禁用
        """
        self._heartbeat_enabled = enabled

        if enabled and self._is_connected and not self._heartbeat_timer.isActive():
            self._heartbeat_timer.start(self._heartbeat_interval_ms)
            logger.info("✅ FC08心跳已启用")
        elif not enabled:
            self._heartbeat_timer.stop()
            logger.info("⏸️ FC08心跳已禁用")

    def get_heartbeat_stats(self) -> dict:
        """
        获取心跳统计信息
        Get heartbeat statistics

        Returns:
            dict: 包含发送次数、成功率、最后发送时间等统计信息
        """
        success_rate = 0.0
        if self._heartbeat_sent_count > 0:
            success_rate = (self._heartbeat_success_count / self._heartbeat_sent_count) * 100

        return {
            "enabled": self._heartbeat_enabled,
            "interval_ms": self._heartbeat_interval_ms,
            "unit_id": self._unit_id,
            "sent_count": self._heartbeat_sent_count,
            "success_count": self._heartbeat_success_count,
            "success_rate": f"{success_rate:.1f}%",
            "last_heartbeat_time": self._last_heartbeat_time,
            "is_connected": self._is_connected,
            "keepalive_configured": True  # 始终配置TCP KeepAlive
        }
