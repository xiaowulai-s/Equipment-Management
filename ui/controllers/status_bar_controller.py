# -*- coding: utf-8 -*-
"""Status bar controller."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, Optional

from PySide6.QtWidgets import QLabel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


class StatusBarController:
    """Encapsulates status bar creation and update logic."""

    def __init__(self) -> None:
        self._status_msg_label: QLabel | None = None
        self._status_total_label: QLabel | None = None
        self._status_online_label: QLabel | None = None
        self._status_offline_label: QLabel | None = None
        self._status_error_label: QLabel | None = None
        self._status_auto_reconnect_enabled: QLabel | None = None
        self._status_auto_reconnect_disabled: QLabel | None = None
        self._status_tx_label: QLabel | None = None
        self._status_rx_label: QLabel | None = None

    # ═══════════════════════════════════════════════════════════
    # 公共属性接口 (Public Properties)
    # ═══════════════════════════════════════════════════════════

    @property
    def status_msg_label(self) -> Optional[QLabel]:
        """状态消息标签"""
        return self._status_msg_label

    @property
    def total_label(self) -> Optional[QLabel]:
        """设备总数标签"""
        return self._status_total_label

    @property
    def online_label(self) -> Optional[QLabel]:
        """在线数量标签"""
        return self._status_online_label

    @property
    def offline_label(self) -> Optional[QLabel]:
        """离线数量标签"""
        return self._status_offline_label

    @property
    def error_label(self) -> Optional[QLabel]:
        """错误数量标签"""
        return self._status_error_label

    @property
    def tx_label(self) -> Optional[QLabel]:
        """发送计数标签"""
        return self._status_tx_label

    @property
    def rx_label(self) -> Optional[QLabel]:
        """接收计数标签"""
        return self._status_rx_label

    def get_all_widgets(self) -> Dict[str, Optional[QLabel]]:
        """
        获取所有状态栏控件的字典

        Returns:
            Dict[str, QLabel]: 控件名称到控件的映射
        """
        return {
            "status_msg": self._status_msg_label,
            "total": self._status_total_label,
            "online": self._status_online_label,
            "offline": self._status_offline_label,
            "error": self._status_error_label,
            "auto_reconnect_enabled": self._status_auto_reconnect_enabled,
            "auto_reconnect_disabled": self._status_auto_reconnect_disabled,
            "tx": self._status_tx_label,
            "rx": self._status_rx_label,
        }

    def build(self, window: QMainWindow, styles: dict) -> None:
        status_bar = window.statusBar()
        status_bar.setStyleSheet(styles.get("STATUSBAR", ""))

        self._status_msg_label = QLabel("就绪")
        self._status_msg_label.setStyleSheet("color: #6B7280; font-size: 12px; padding: 0 8px;")
        status_bar.addWidget(self._status_msg_label)

        for text in ("|",):
            sep = QLabel(text)
            sep.setStyleSheet("color: #D1D5DB; font-size: 12px; padding: 0 4px;")
            status_bar.addPermanentWidget(sep)

        self._status_total_label = self._make_status_label("设备 0", "#374151")
        status_bar.addPermanentWidget(self._status_total_label)

        self._status_online_label = self._make_status_label("● 在线 0", "#2DA44E")  # Fluent绿色
        status_bar.addPermanentWidget(self._status_online_label)

        self._status_offline_label = self._make_status_label("● 离线 0", "#57606A")  # 深灰
        status_bar.addPermanentWidget(self._status_offline_label)

        self._status_error_label = self._make_status_label("● 错误 0", "#CF222E")  # Fluent红色
        status_bar.addPermanentWidget(self._status_error_label)

        for text in ("|",):
            sep = QLabel(text)
            sep.setStyleSheet("color: #D0D7DE; font-size: 12px; padding: 0 4px;")  # Fluent边框色
            status_bar.addPermanentWidget(sep)

        self._status_auto_reconnect_enabled = self._make_status_label("● 自动重连启用 0", "#0969DA")  # Fluent蓝色
        status_bar.addPermanentWidget(self._status_auto_reconnect_enabled)

        self._status_auto_reconnect_disabled = self._make_status_label("● 自动重连禁用 0", "D29922")  # Fluent金色
        status_bar.addPermanentWidget(self._status_auto_reconnect_disabled)

        for text in ("|",):
            sep = QLabel(text)
            sep.setStyleSheet("color: #D0D7DE; font-size: 12px; padding: 0 4px;")  # Fluent边框色
            status_bar.addPermanentWidget(sep)

        self._status_tx_label = self._make_status_label("TX: 0", "#0969DA")  # Fluent蓝色
        status_bar.addPermanentWidget(self._status_tx_label)

        self._status_rx_label = self._make_status_label("RX: 0", "#2DA44E")  # Fluent绿色
        status_bar.addPermanentWidget(self._status_rx_label)

    @staticmethod
    def _make_status_label(text: str, color: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {color}; font-size: 12px; padding: 0 4px;")
        return label

    def set_message(self, msg: str) -> None:
        if self._status_msg_label:
            self._status_msg_label.setText(msg)

    def update_device_stats(self, total: int, online: int, offline: int, error: int) -> None:
        if self._status_total_label:
            self._status_total_label.setText(f"设备 {total}")
        if self._status_online_label:
            self._status_online_label.setText(f"● 在线 {online}")
        if self._status_offline_label:
            self._status_offline_label.setText(f"● 离线 {offline}")
        if self._status_error_label:
            self._status_error_label.setText(f"● 错误 {error}")

    def update_reconnect_stats(self, enabled_count: int, disabled_count: int) -> None:
        if self._status_auto_reconnect_enabled:
            self._status_auto_reconnect_enabled.setText(f"● 自动重连启用 {enabled_count}")
        if self._status_auto_reconnect_disabled:
            self._status_auto_reconnect_disabled.setText(f"● 自动重连禁用 {disabled_count}")

    def update_command_stats(self, tx: int, rx: int) -> None:
        if self._status_tx_label:
            self._status_tx_label.setText(f"TX: {tx}")
        if self._status_rx_label:
            self._status_rx_label.setText(f"RX: {rx}")
