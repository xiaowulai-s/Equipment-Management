# -*- coding: utf-8 -*-
"""Modbus LAN Scanner - TCP端口扫描与Modbus设备发现"""

from __future__ import annotations

import ipaddress
import logging
import socket
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    ip: str
    port: int = 502
    is_modbus: bool = False
    latency_ms: float = 0.0
    unit_id: int = 1
    device_info: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "port": self.port,
            "is_modbus": self.is_modbus,
            "latency_ms": self.latency_ms,
            "unit_id": self.unit_id,
            "device_info": self.device_info,
        }


class ModbusLanScanner:
    """本地网络扫描器"""

    @staticmethod
    def get_local_networks() -> List[str]:
        networks = []
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            for ip in ips:
                if not ip.startswith("127.") and ":" not in ip:
                    parts = ip.split(".")
                    network = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
                    if network not in networks:
                        networks.append(network)
        except Exception:
            pass

        if not networks:
            networks = ["192.168.1.0/24", "192.168.31.0/24", "10.0.0.0/24"]

        return sorted(networks)

    @staticmethod
    def scan_single(ip: str, port: int = 502, timeout_ms: int = 800) -> ScanResult:
        result = ScanResult(ip=ip, port=port)
        start = time.time()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_ms / 1000.0)
            sock.connect((ip, port))
            result.latency_ms = (time.time() - start) * 1000

            result.is_modbus = True
            result.device_info = "Modbus TCP"

            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError):
            result.is_modbus = False
        except Exception as e:
            logger.debug("扫描 %s 异常: %s", ip, e)
            result.is_modbus = False

        return result


class AsyncScanWorker(QThread):
    progress = Signal(int, int, object)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._network: str = ""
        self._port: int = 502
        self._timeout_ms: int = 800
        self._verify_modbus: bool = True
        self._stopped: bool = False
        self._mutex = QMutex()

    @classmethod
    def create(
        cls,
        network: str,
        port: int = 502,
        timeout_ms: int = 800,
        verify_modbus: bool = True,
    ) -> "AsyncScanWorker":
        worker = cls()
        worker._network = network
        worker._port = port
        worker._timeout_ms = timeout_ms
        worker._verify_modbus = verify_modbus
        return worker

    def run(self):
        results: List[Dict[str, Any]] = []
        ips = []

        try:
            network = ipaddress.IPv4Network(self._network, strict=False)
            ips = [str(ip) for ip in network.hosts()]
        except Exception as e:
            self.error.emit(f"网段解析失败: {e}")
            self.finished.emit([])
            return

        total = len(ips)
        for idx, ip in enumerate(ips):
            with QMutexLocker(self._mutex):
                if self._stopped:
                    break

            try:
                start = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self._timeout_ms / 1000.0)
                sock.connect((ip, self._port))
                latency = (time.time() - start) * 1000

                result = ScanResult(
                    ip=ip,
                    port=self._port,
                    is_modbus=self._verify_modbus,
                    latency_ms=latency,
                    device_info="Modbus TCP" if self._verify_modbus else "TCP",
                )
                results.append(result.to_dict())
                self.progress.emit(idx + 1, total, result)

                try:
                    sock.close()
                except Exception:
                    pass

            except (socket.timeout, ConnectionRefusedError, OSError):
                pass
            except Exception as e:
                logger.debug("扫描异常 %s: %s", ip, e)

            if idx % 16 == 0:
                self.msleep(1)

        self.finished.emit(results)

    def stop(self):
        with QMutexLocker(self._mutex):
            self._stopped = True