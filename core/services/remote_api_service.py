# -*- coding: utf-8 -*-
"""
远程 API 服务
Remote API Service - HTTP REST + MQTT 接口
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from core.utils.logger import get_logger

logger = get_logger(__name__)


class APIRequestHandler(BaseHTTPRequestHandler):
    """HTTP REST API 请求处理器"""

    device_manager = None
    alarm_manager = None

    def log_message(self, format, *args):
        logger.debug("API %s", format % args)

    def _send_json(self, data: Any, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        if path == "/api/devices":
            self._handle_get_devices()
        elif path.startswith("/api/devices/"):
            device_id = path.split("/")[3]
            self._handle_get_device(device_id)
        elif path == "/api/alarms":
            self._handle_get_alarms(params)
        elif path == "/api/stats":
            self._handle_get_stats()
        elif path == "/api/health":
            self._send_json({"status": "ok", "timestamp": datetime.now().isoformat()})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if path == "/api/devices" and self.device_manager:
            self._handle_add_device(data)
        elif path.startswith("/api/devices/") and "/connect" in path:
            device_id = path.split("/")[3]
            self._handle_connect_device(device_id)
        elif path.startswith("/api/devices/") and "/disconnect" in path:
            device_id = path.split("/")[3]
            self._handle_disconnect_device(device_id)
        else:
            self._send_json({"error": "Not found"}, 404)

    def _handle_get_devices(self) -> None:
        if not self.device_manager:
            self._send_json({"error": "Device manager not available"}, 503)
            return
        devices = self.device_manager.get_all_devices()
        self._send_json({"devices": devices, "count": len(devices)})

    def _handle_get_device(self, device_id: str) -> None:
        if not self.device_manager:
            self._send_json({"error": "Device manager not available"}, 503)
            return
        device = self.device_manager.get_device(device_id)
        if device:
            config = device.get_device_config()
            data = device.get_current_data()
            self._send_json({"device_id": device_id, "config": config, "data": data, "status": device.get_status()})
        else:
            self._send_json({"error": "Device not found"}, 404)

    def _handle_get_alarms(self, params: Dict) -> None:
        if not self.alarm_manager:
            self._send_json({"error": "Alarm manager not available"}, 503)
            return
        active = self.alarm_manager.get_active_alarms()
        history = self.alarm_manager.get_alarm_history(50)
        self._send_json(
            {
                "active": [a.to_dict() for a in active],
                "history": [a.to_dict() for a in history],
            }
        )

    def _handle_get_stats(self) -> None:
        if not self.device_manager:
            self._send_json({"error": "Not available"}, 503)
            return
        stats = self.device_manager.get_polling_statistics()
        self._send_json(stats)

    def _handle_add_device(self, data: Dict) -> None:
        try:
            device_id = self.device_manager.add_device(data)
            self._send_json({"device_id": device_id}, 201)
        except Exception as e:
            self._send_json({"error": str(e)}, 400)

    def _handle_connect_device(self, device_id: str) -> None:
        success, error_type, error_msg = self.device_manager.connect_device(device_id)
        if success:
            self._send_json({"status": "connected", "device_id": device_id})
        else:
            self._send_json({"status": "failed", "error_type": error_type, "error_msg": error_msg}, 400)

    def _handle_disconnect_device(self, device_id: str) -> None:
        self.device_manager.disconnect_device(device_id)
        self._send_json({"status": "disconnected", "device_id": device_id})


class RemoteAPIService:
    """远程 API 服务 - HTTP REST 接口"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, device_manager=None, alarm_manager=None) -> None:
        APIRequestHandler.device_manager = device_manager
        APIRequestHandler.alarm_manager = alarm_manager

        self._server = HTTPServer((self._host, self._port), APIRequestHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("远程API服务已启动", host=self._host, port=self._port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            logger.info("远程API服务已停止")
