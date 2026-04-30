# -*- coding: utf-8 -*-
"""UI preferences persistence service."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UIPreferencesService:
    """Persist UI layout preferences (card/chart configs, panel sizes) to JSON file.

    Usage:
        prefs = UIPreferencesService()
        prefs.save_cards("dev-001", [{"title": "温度", "register_name": "temp"}])
        cards = prefs.load_cards("dev-001")
        prefs.save_charts("dev-001", [{"title": "趋势", "registers": ["temp"]}])
    """

    def __init__(self, config_dir: Optional[str] = None) -> None:
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = Path("data")
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._file = self._config_dir / "ui_preferences.json"
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._file.exists():
            try:
                text = self._file.read_text(encoding="utf-8")
                self._data = json.loads(text) if text.strip() else {}
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("加载 UI 偏好配置失败: %s", e)
                self._data = {}

    def _save(self) -> None:
        try:
            self._file.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.error("保存 UI 偏好配置失败: %s", e)

    def save_cards(self, device_id: str, cards: List[Dict[str, Any]]) -> None:
        key = "device_cards"
        if key not in self._data:
            self._data[key] = {}
        self._data[key][device_id] = cards
        self._save()

    def load_cards(self, device_id: str) -> List[Dict[str, Any]]:
        return list(self._data.get("device_cards", {}).get(device_id, []))

    def save_charts(self, device_id: str, charts: List[Dict[str, Any]]) -> None:
        key = "device_charts"
        if key not in self._data:
            self._data[key] = {}
        self._data[key][device_id] = charts
        self._save()

    def load_charts(self, device_id: str) -> List[Dict[str, Any]]:
        return list(self._data.get("device_charts", {}).get(device_id, []))

    def remove_device_prefs(self, device_id: str) -> None:
        for key in ("device_cards", "device_charts"):
            if key in self._data and device_id in self._data[key]:
                del self._data[key][device_id]
        self._save()

    def save_panel_state(self, left_collapsed: bool, left_width: int, right_width: int) -> None:
        self._data["panel_state"] = {
            "left_collapsed": left_collapsed,
            "left_width": left_width,
            "right_width": right_width,
        }
        self._save()

    def load_panel_state(self) -> Dict[str, Any]:
        return dict(self._data.get("panel_state", {}))
