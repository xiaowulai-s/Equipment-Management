"""
报警通知服务

提供多种通知渠道:
    - POPUP:   系统弹窗 (QMessageBox)
    - SOUND:   系统声音 (winsound / afplay / aplay)
    - CUSTOM:  自定义回调函数

设计要点:
    - 从旧架构 core.utils.alarm_notification.py 迁移
    - 去除对 core 模块的依赖
    - 适配新架构的报警级别体系 (high_high/high/low/low_low)
    - 支持报警抑制: 同一设备同一寄存器在冷却期内不重复通知
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """通知渠道类型"""

    POPUP = "popup"
    SOUND = "sound"
    CUSTOM = "custom"


@dataclass
class NotificationConfig:
    """通知配置"""

    enabled_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.POPUP])
    sound_file: Optional[Path] = None
    custom_handler: Optional[Callable[[Dict[str, Any], str], None]] = None
    volume: float = 0.8
    cooldown_seconds: float = 30.0  # 报警通知冷却时间 (秒)

    # 报警级别过滤: 只有 severity >= min_level 的报警才通知
    # 0=none, 1=low, 2=low_low, 3=high, 4=high_high
    min_level: int = 1


class AlarmNotificationService(QObject):
    """报警通知服务

    负责通过多种渠道分发报警通知。
    支持报警抑制和冷却机制，避免频繁通知。

    使用方式:
        config = NotificationConfig(
            enabled_channels=[NotificationChannel.POPUP, NotificationChannel.SOUND],
            min_level=3,  # 只通知 high 及以上
        )
        service = AlarmNotificationService(config)

        # 连接 AlarmManager
        manager.alarm_triggered.connect(service.on_alarm_triggered)
    """

    notification_sent = Signal(str, str, str)  # device_id, level, channel

    def __init__(
        self,
        config: Optional[NotificationConfig] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self._config = config or NotificationConfig()
        self._sound_available = self._check_sound_available()

        # 报警抑制: {(device_id, register_name): last_notify_time}
        self._last_notify: Dict[tuple, float] = {}

        # 冷却清理定时器 (每分钟清理过期的抑制记录)
        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_suppression)
        self._cleanup_timer.start(60_000)

        logger.info(
            f"AlarmNotificationService 初始化: "
            f"channels={[c.value for c in self._config.enabled_channels]}, "
            f"min_level={self._config.min_level}"
        )

    # ═══════════════════════════════════════════════════════
    # 公开接口
    # ═══════════════════════════════════════════════════════

    def on_alarm_triggered(self, alarm_info: dict) -> None:
        """处理报警触发事件 (可连接到 AlarmManager.alarm_triggered)

        Args:
            alarm_info: 报警信息字典, 应包含:
                - device_id, device_name, register_name
                - alarm_level, value, description
        """
        import time

        level = alarm_info.get("alarm_level", "none")
        device_id = alarm_info.get("device_id", "")
        register_name = alarm_info.get("register_name", "")

        # 级别过滤
        severity_map = {"none": 0, "low": 1, "low_low": 2, "high": 3, "high_high": 4}
        severity = severity_map.get(level, 0)
        if severity < self._config.min_level:
            return

        # 冷却检查
        key = (device_id, register_name)
        last_time = self._last_notify.get(key, 0.0)
        now = time.monotonic()
        if (now - last_time) < self._config.cooldown_seconds:
            return

        # 发送通知
        self._send_notification(alarm_info, "triggered")
        self._last_notify[key] = now

    def on_alarm_cleared(self, clear_info: dict) -> None:
        """处理报警清除事件 (可连接到 AlarmManager.alarm_cleared)"""
        # 清除通知不做级别过滤, 但保持冷却
        device_id = clear_info.get("device_id", "")
        register_name = clear_info.get("register_name", "")

        key = (device_id, register_name)
        # 清除时重置冷却 (下次触发可以立即通知)
        self._last_notify.pop(key, None)

    def notify(
        self,
        device_id: str,
        register_name: str,
        level: str,
        value: float,
        description: str = "",
        device_name: str = "",
    ) -> None:
        """手动发送通知"""
        alarm_info = {
            "device_id": device_id,
            "device_name": device_name or device_id,
            "register_name": register_name,
            "alarm_level": level,
            "value": value,
            "description": description,
        }
        self._send_notification(alarm_info, "manual")

    # ═══════════════════════════════════════════════════════
    # 通知分发
    # ═══════════════════════════════════════════════════════

    def _send_notification(self, alarm_data: dict, source: str) -> None:
        """通过所有启用的渠道发送通知"""
        for channel in self._config.enabled_channels:
            try:
                if channel == NotificationChannel.POPUP:
                    self._send_popup(alarm_data)
                elif channel == NotificationChannel.SOUND and self._sound_available:
                    self._send_sound(alarm_data)
                elif channel == NotificationChannel.CUSTOM and self._config.custom_handler:
                    self._config.custom_handler(alarm_data, source)

                self.notification_sent.emit(
                    alarm_data.get("device_id", ""),
                    alarm_data.get("alarm_level", ""),
                    channel.value,
                )

            except Exception as e:
                logger.error(f"发送 {channel.value} 通知失败: {e}")

    def _send_popup(self, alarm_data: dict) -> None:
        """弹窗通知"""
        try:
            from PySide6.QtWidgets import QMessageBox

            level = alarm_data.get("alarm_level", "unknown")
            level_text_map = {
                "high_high": "🔴 高高报警",
                "high": "🟠 高报警",
                "low": "🔵 低报警",
                "low_low": "🟡 低低报警",
            }
            level_text = level_text_map.get(level, f"⚠️ {level}")

            title = f"报警通知: {level_text}"
            message = (
                f"设备: {alarm_data.get('device_name', alarm_data.get('device_id', ''))}\n"
                f"参数: {alarm_data.get('register_name', '')}\n"
                f"值: {alarm_data.get('value', 0)}\n"
                f"描述: {alarm_data.get('description', '')}"
            )

            # 使用非阻塞弹窗
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.show()

            logger.info(f"弹窗通知已发送: {title}")

        except Exception as e:
            logger.error(f"弹窗通知异常: {e}")

    def _send_sound(self, alarm_data: dict) -> None:
        """声音通知"""
        try:
            level = alarm_data.get("alarm_level", "")

            if self._config.sound_file and self._config.sound_file.exists():
                self._play_sound_file(str(self._config.sound_file))
            else:
                self._play_system_sound(level)

            logger.info(f"声音通知已发送: level={level}")

        except Exception as e:
            logger.error(f"声音通知异常: {e}")

    def _play_sound_file(self, file_path: str) -> None:
        """播放自定义声音文件"""
        system = platform.system()
        try:
            if system == "Windows":
                import winsound

                winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif system == "Darwin":
                import os

                os.system(f"afplay -v {self._config.volume} '{file_path}' &")
            elif system == "Linux":
                import os

                os.system(f"aplay -q -v {self._config.volume} '{file_path}' &")
        except Exception as e:
            logger.error(f"播放声音文件失败: {e}")

    def _play_system_sound(self, level: str) -> None:
        """播放系统默认声音"""
        system = platform.system()
        try:
            if system == "Windows":
                import winsound

                if level in ("high", "high_high"):
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                else:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif system == "Darwin":
                import os

                if level in ("high", "high_high"):
                    os.system("afplay /System/Library/Sounds/Basso.aiff &")
                else:
                    os.system("afplay /System/Library/Sounds/Glass.aiff &")
            elif system == "Linux":
                import os

                if level in ("high", "high_high"):
                    os.system("paplay /usr/share/sounds/freedesktop/stereo/dialog-warning.oga &")
                else:
                    os.system("paplay /usr/share/sounds/freedesktop/stereo/dialog-information.oga &")
        except Exception as e:
            logger.error(f"播放系统声音失败: {e}")

    # ═══════════════════════════════════════════════════════
    # 维护
    # ═══════════════════════════════════════════════════════

    def update_config(self, config: NotificationConfig) -> None:
        """更新通知配置"""
        self._config = config
        logger.info("通知配置已更新")

    def is_channel_available(self, channel: NotificationChannel) -> bool:
        """检查通知渠道是否可用"""
        if channel == NotificationChannel.POPUP:
            return True
        elif channel == NotificationChannel.SOUND:
            return self._sound_available
        elif channel == NotificationChannel.CUSTOM:
            return self._config.custom_handler is not None
        return False

    def _check_sound_available(self) -> bool:
        """检查声音是否可用"""
        try:
            system = platform.system()
            if system == "Windows":
                import winsound

                return True
            elif system == "Darwin":
                return True
            elif system == "Linux":
                return True
        except ImportError:
            pass
        return False

    def _cleanup_suppression(self) -> None:
        """清理过期的报警抑制记录"""
        import time

        now = time.monotonic()
        cutoff = now - self._config.cooldown_seconds * 2
        expired = [k for k, v in self._last_notify.items() if v < cutoff]
        for k in expired:
            del self._last_notify[k]
