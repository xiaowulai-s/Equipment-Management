# -*- coding: utf-8 -*-
"""Device priority helper - determines polling priority based on device config."""

from __future__ import annotations

from typing import Any, Dict

from .polling import PollPriority


class DevicePriorityHelper:
    """Determine polling priority from device configuration."""

    @staticmethod
    def determine_priority(config: Dict[str, Any]) -> PollPriority:
        device_type = (config.get("device_type") or "").lower()
        protocol = (config.get("protocol") or "").lower()

        if "emergency" in device_type or "alarm" in device_type:
            return PollPriority.HIGH
        if protocol in ("modbus", "mcgs", "opc_ua"):
            return PollPriority.NORMAL
        return PollPriority.LOW