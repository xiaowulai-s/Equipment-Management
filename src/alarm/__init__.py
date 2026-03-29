"""
报警系统

新架构报警管理器:
    - AlarmManager: 信号聚合 + 记录持久化 + 确认 + 统计
    - AlarmNotificationService: 通知渠道 (弹窗/声音/自定义)

与旧架构区别:
    - 报警检测在 Register 层完成 (带死区、升级/降级机制)
    - AlarmManager 不再做阈值检测, 仅负责记录和通知
    - 使用 src.data.repository 中的 Repository 持久化
    - 新增 AlarmNotificationService 独立通知服务
"""

from .alarm_manager import AlarmManager
from .notification import AlarmNotificationService, NotificationChannel, NotificationConfig

__all__ = [
    "AlarmManager",
    "NotificationChannel",
    "NotificationConfig",
    "AlarmNotificationService",
]
