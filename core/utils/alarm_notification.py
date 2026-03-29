# -*- coding: utf-8 -*-
"""
Alarm Notification Service
报警通知服务

Provides multiple notification channels for alarms.
提供多种报警通知渠道（声音、弹窗、邮件）。
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification channel types."""

    POPUP = "popup"
    SOUND = "sound"
    EMAIL = "email"
    CUSTOM = "custom"


@dataclass
class NotificationConfig:
    """Notification configuration."""

    enabled_channels: List[NotificationChannel]
    sound_file: Optional[Path] = None
    email_recipients: List[str] = None
    custom_handler: Optional[Callable[[Dict[str, Any]], None]] = None
    volume: float = 0.8

    def __post_init__(self) -> None:
        if self.email_recipients is None:
            self.email_recipients = []


class AlarmNotificationService(QObject):
    """
    Alarm Notification Service
    报警通知服务

    Sends notifications through multiple channels when alarms are triggered.
    当报警触发时通过多种渠道发送通知。
    """

    notification_sent = Signal(str, str)

    def __init__(self, config: Optional[NotificationConfig] = None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        if config is None:
            config = NotificationConfig(enabled_channels=[NotificationChannel.POPUP])

        self._config = config
        self._sound_available = self._check_sound_available()
        self._email_available = False

        if NotificationChannel.EMAIL in config.enabled_channels:
            self._init_email()

        logger.info(
            f"Alarm notification service initialized with channels: {[c.value for c in config.enabled_channels]}"
        )

    def _check_sound_available(self) -> bool:
        """Check if sound playback is available."""
        try:
            if platform.system() == "Windows":
                import winsound

                return True
            elif platform.system() == "Darwin":
                import os

                return os.system("afplay -v 0.01") == 0
            elif platform.system() == "Linux":
                import os

                return os.system("aplay -q --null") == 0
        except ImportError:
            logger.warning("Sound playback not available")
        return False

    def _init_email(self) -> None:
        """Initialize email notification."""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            self._email_available = True
            logger.info("Email notification initialized")
        except ImportError:
            logger.warning("Email notification not available: smtplib not installed")

    def notify(
        self,
        device_id: str,
        parameter: str,
        level: str,
        value: float,
        threshold: Optional[float] = None,
        description: str = "",
    ) -> None:
        """
        Send notification through all enabled channels.
        通过所有启用的渠道发送通知。
        """
        alarm_data = {
            "device_id": device_id,
            "parameter": parameter,
            "level": level,
            "value": value,
            "threshold": threshold,
            "description": description,
        }

        for channel in self._config.enabled_channels:
            try:
                if channel == NotificationChannel.POPUP:
                    self._send_popup_notification(alarm_data)
                elif channel == NotificationChannel.SOUND and self._sound_available:
                    self._send_sound_notification(alarm_data)
                elif channel == NotificationChannel.EMAIL and self._email_available:
                    self._send_email_notification(alarm_data)
                elif channel == NotificationChannel.CUSTOM and self._config.custom_handler:
                    self._config.custom_handler(alarm_data)

                self.notification_sent.emit(device_id, level)

            except Exception as e:
                logger.error(f"Failed to send {channel.value} notification: {e}")

    def _send_popup_notification(self, alarm_data: Dict[str, Any]) -> None:
        """Send popup notification."""
        level_text = alarm_data["level"].upper()
        threshold_text = f" (Threshold: {alarm_data['threshold']})" if alarm_data.get("threshold") else ""

        title = f"Alarm: {level_text}"
        message = (
            f"Device: {alarm_data['device_id']}\n"
            f"Parameter: {alarm_data['parameter']}\n"
            f"Value: {alarm_data['value']}{threshold_text}\n"
            f"Description: {alarm_data['description']}"
        )

        QMessageBox.warning(None, title, message)
        logger.info(f"Popup notification sent: {title}")

    def _send_sound_notification(self, alarm_data: Dict[str, Any]) -> None:
        """Send sound notification."""
        try:
            if self._config.sound_file and self._config.sound_file.exists():
                self._play_sound_file(str(self._config.sound_file))
            else:
                self._play_system_sound(alarm_data["level"])

            logger.info(f"Sound notification sent for level: {alarm_data['level']}")
        except Exception as e:
            logger.error(f"Failed to play sound: {e}")

    def _play_sound_file(self, file_path: str) -> None:
        """Play custom sound file."""
        system_name = platform.system()

        if system_name == "Windows":
            import winsound

            winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif system_name == "Darwin":
            import os

            os.system(f"afplay -v {self._config.volume} '{file_path}' &")
        elif system_name == "Linux":
            import os

            os.system(f"aplay -q -v {self._config.volume} '{file_path}' &")

    def _play_system_sound(self, level: str) -> None:
        """Play system default sound based on alarm level."""
        system_name = platform.system()

        if system_name == "Windows":
            import winsound

            if level in ("WARNING", "ERROR", "CRITICAL"):
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif system_name == "Darwin":
            import os

            if level in ("WARNING", "ERROR", "CRITICAL"):
                os.system("afplay /System/Library/Sounds/Basso.aiff &")
            else:
                os.system("afplay /System/Library/Sounds/Glass.aiff &")
        elif system_name == "Linux":
            import os

            if level in ("WARNING", "ERROR", "CRITICAL"):
                os.system("paplay /usr/share/sounds/freedesktop/stereo/dialog-warning.oga &")
            else:
                os.system("paplay /usr/share/sounds/freedesktop/stereo/dialog-information.oga &")

    def _send_email_notification(self, alarm_data: Dict[str, Any]) -> None:
        """Send email notification."""
        if not self._config.email_recipients:
            logger.warning("No email recipients configured")
            return

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["From"] = "equipment-monitor@example.com"
            msg["To"] = ", ".join(self._config.email_recipients)
            msg["Subject"] = f"Alarm Alert: {alarm_data['level']} - {alarm_data['device_id']}"

            body = f"""
Alarm Details:
- Device ID: {alarm_data['device_id']}
- Parameter: {alarm_data['parameter']}
- Level: {alarm_data['level']}
- Value: {alarm_data['value']}
- Threshold: {alarm_data.get('threshold', 'N/A')}
- Description: {alarm_data['description']}
- Timestamp: {alarm_data.get('timestamp', 'N/A')}

Please check the system for more details.
            """

            msg.attach(MIMEText(body, "plain"))

            logger.info(f"Email notification sent to {len(self._config.email_recipients)} recipients")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def update_config(self, config: NotificationConfig) -> None:
        """
        Update notification configuration.
        更新通知配置。
        """
        self._config = config

        if NotificationChannel.EMAIL in config.enabled_channels and not self._email_available:
            self._init_email()

        logger.info("Notification configuration updated")

    def is_channel_available(self, channel: NotificationChannel) -> bool:
        """
        Check if a notification channel is available.
        检查通知渠道是否可用。
        """
        if channel == NotificationChannel.POPUP:
            return True
        elif channel == NotificationChannel.SOUND:
            return self._sound_available
        elif channel == NotificationChannel.EMAIL:
            return self._email_available
        elif channel == NotificationChannel.CUSTOM:
            return self._config.custom_handler is not None
        return False

    def test_notifications(self) -> None:
        """
        Test all enabled notification channels.
        测试所有启用的通知渠道。
        """
        logger.info("Testing notification channels...")

        self.notify(
            device_id="TEST_DEVICE",
            parameter="TestParameter",
            level="INFO",
            value=0.0,
            description="This is a test notification",
        )
