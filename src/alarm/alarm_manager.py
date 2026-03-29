"""
报警管理器

新架构设计:
    - 报警阈值检测由 Register._check_alarm() 完成 (四级报警 + 死区)
    - AlarmManager 负责信号聚合、记录持久化、确认、统计
    - 可选连接 AlarmNotificationService 进行通知分发
    - 与 DataCollector 配合: collector的信号 → AlarmManager → Repository

信号体系:
    alarm_triggered(dict)  → 新报警触发, 携带报警信息字典
    alarm_cleared(dict)    → 报警清除, 携带清除信息字典
    alarm_acknowledged(int) → 报警已确认 (alarm_record_id)
    statistics_updated(dict) → 统计数据更新
    error_occurred(str)    → 错误信息

使用方式:
    manager = AlarmManager(db_manager)

    # 连接 DataCollector 的报警信号
    collector.device_poll_success.connect(manager._on_device_data)

    # 或直接连接 Device 的报警信号
    device.alarm_triggered.connect(
        lambda name, reg, val, lvl: manager.record_alarm(...)
    )
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from src.data.database import DatabaseManager
from src.data.models import AlarmRecordModel
from src.data.repository.alarm_repository import AlarmRecordRepository, AlarmRuleRepository
from src.device.register import AlarmLevel

logger = logging.getLogger(__name__)


def _now() -> datetime:
    """UTC 时间戳"""
    return datetime.now(timezone.utc)


def _level_to_int(level: str) -> int:
    """将报警级别字符串转换为整数 (用于ORM存储)"""
    return AlarmLevel.severity(level)


def _level_from_int(level: int) -> str:
    """将整数报警级别转换为字符串"""
    reverse_map = {v: k for k, v in AlarmLevel.SEVERITY.items()}
    return reverse_map.get(level, "none")


class AlarmManager(QObject):
    """报警管理器

    职责:
        1. 接收来自 Register/Device 的报警信号
        2. 将报警记录持久化到数据库
        3. 提供报警确认、查询、统计接口
        4. 分发通知到 AlarmNotificationService (可选)

    Attributes:
        db_manager: 数据库管理器 (None 时仅内存模式)
        auto_record: 是否自动记录报警到数据库 (默认 True)
        auto_cleanup_days: 自动清理天数 (默认 90, 0 禁用)
    """

    # ── 信号 ──────────────────────────────────────────────
    alarm_triggered = Signal(dict)  # 报警触发
    alarm_cleared = Signal(dict)  # 报警清除
    alarm_acknowledged = Signal(dict)  # 报警确认
    statistics_updated = Signal(dict)  # 统计更新
    error_occurred = Signal(str)  # 错误

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        auto_record: bool = True,
        auto_cleanup_days: int = 90,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self._db_manager = db_manager
        self._auto_record = auto_record
        self._auto_cleanup_days = auto_cleanup_days

        # 内存中的活跃报警 {device_id: {register_name: alarm_info}}
        self._active_alarms: Dict[str, Dict[str, dict]] = {}

        # 通知回调 (可选)
        self._notification_callback: Optional[Callable[[dict, str], None]] = None

        # 统计缓存
        self._stats_cache: Dict[str, Any] = {
            "total_triggered": 0,
            "total_cleared": 0,
            "active_count": 0,
            "unacknowledged_count": 0,
        }

        logger.info(
            f"AlarmManager 初始化: "
            f"auto_record={auto_record}, "
            f"auto_cleanup={auto_cleanup_days}天, "
            f"db={'有' if db_manager else '无'}"
        )

    # ═══════════════════════════════════════════════════════
    # 报警记录
    # ═══════════════════════════════════════════════════════

    def record_alarm(
        self,
        device_id: str,
        device_name: str,
        register_name: str,
        alarm_level: str,
        value: float,
        description: str = "",
        alarm_type: str = "threshold",
    ) -> Optional[AlarmRecordModel]:
        """记录一条报警

        Args:
            device_id: 设备ID
            device_name: 设备名称
            register_name: 寄存器名称
            alarm_level: 报警级别 (high_high/high/low/low_low)
            value: 触发值
            description: 报警描述
            alarm_type: 报警类型

        Returns:
            创建的 AlarmRecordModel, 无数据库时返回 None
        """
        level_int = _level_to_int(alarm_level)
        rule_id = f"RULE-{device_id}-{register_name}"
        timestamp = _now()

        # 构建报警信息
        alarm_info = {
            "device_id": device_id,
            "device_name": device_name,
            "register_name": register_name,
            "alarm_level": alarm_level,
            "level_int": level_int,
            "value": value,
            "description": description,
            "alarm_type": alarm_type,
            "timestamp": timestamp,
        }

        # 更新活跃报警
        if device_id not in self._active_alarms:
            self._active_alarms[device_id] = {}
        self._active_alarms[device_id][register_name] = alarm_info

        # 持久化
        record = None
        if self._auto_record and self._db_manager is not None:
            try:
                with self._db_manager.session() as session:
                    repo = AlarmRecordRepository(session)
                    record = repo.create_record(
                        rule_id=rule_id,
                        device_id=device_id,
                        device_name=device_name,
                        register_name=register_name,
                        alarm_type=alarm_type,
                        level=level_int,
                        value=value,
                        description=description,
                    )
                    alarm_info["record_id"] = record.id
            except Exception as e:
                logger.exception(f"记录报警失败: {device_id}/{register_name}")
                self.error_occurred.emit(f"记录报警失败: {e}")

        # 更新统计
        self._stats_cache["total_triggered"] += 1
        self._stats_cache["active_count"] = len(self._get_all_active())
        self.statistics_updated.emit(self.get_statistics())

        # 发射信号
        self.alarm_triggered.emit(alarm_info)

        # 通知
        if self._notification_callback:
            try:
                self._notification_callback(alarm_info, "triggered")
            except Exception as e:
                logger.error(f"通知回调异常: {e}")

        logger.warning(
            f"报警触发: [{device_name}] {register_name} " f"{AlarmLevel.display_text(alarm_level)} = {value}"
        )

        return record

    def record_alarm_clear(
        self,
        device_id: str,
        device_name: str,
        register_name: str,
        old_level: str,
        value: float,
        description: str = "",
    ) -> None:
        """记录报警清除

        Args:
            device_id: 设备ID
            device_name: 设备名称
            register_name: 寄存器名称
            old_level: 被清除的报警级别
            value: 当前值
            description: 清除描述
        """
        # 从活跃报警中移除
        if device_id in self._active_alarms:
            self._active_alarms[device_id].pop(register_name, None)
            if not self._active_alarms[device_id]:
                del self._active_alarms[device_id]

        clear_info = {
            "device_id": device_id,
            "device_name": device_name,
            "register_name": register_name,
            "old_level": old_level,
            "value": value,
            "description": description,
            "timestamp": _now(),
        }

        # 更新统计
        self._stats_cache["total_cleared"] += 1
        self._stats_cache["active_count"] = len(self._get_all_active())
        self.statistics_updated.emit(self.get_statistics())

        # 发射信号
        self.alarm_cleared.emit(clear_info)

        # 通知
        if self._notification_callback:
            try:
                self._notification_callback(clear_info, "cleared")
            except Exception as e:
                logger.error(f"通知回调异常: {e}")

        logger.info(f"报警清除: [{device_name}] {register_name} " f"{AlarmLevel.display_text(old_level)}已清除")

    # ═══════════════════════════════════════════════════════
    # 设备信号连接
    # ═══════════════════════════════════════════════════════

    def connect_device(self, device: Any) -> None:
        """连接设备的报警信号

        Args:
            device: src.device.device.Device 实例
        """
        device.alarm_triggered.connect(self._on_device_alarm_triggered)
        device.alarm_cleared.connect(self._on_device_alarm_cleared)
        logger.debug(f"已连接设备报警信号: {device.name}")

    def disconnect_device(self, device: Any) -> None:
        """断开设备的报警信号"""
        try:
            device.alarm_triggered.disconnect(self._on_device_alarm_triggered)
            device.alarm_cleared.disconnect(self._on_device_alarm_cleared)
        except RuntimeError:
            pass
        logger.debug(f"已断开设备报警信号: {device.name}")

    def _on_device_alarm_triggered(self, dev_name: str, reg_name: str, value: float, level: str) -> None:
        """设备报警触发 → 记录"""
        sender = self.sender()
        device_id = sender.id if hasattr(sender, "id") else dev_name
        self.record_alarm(
            device_id=device_id,
            device_name=dev_name,
            register_name=reg_name,
            alarm_level=level,
            value=value,
        )

    def _on_device_alarm_cleared(self, dev_name: str, reg_name: str, old_level: str) -> None:
        """设备报警清除 → 记录"""
        sender = self.sender()
        device_id = sender.id if hasattr(sender, "id") else dev_name
        self.record_alarm_clear(
            device_id=device_id,
            device_name=dev_name,
            register_name=reg_name,
            old_level=old_level,
            value=0.0,
        )

    # ═══════════════════════════════════════════════════════
    # 确认
    # ═══════════════════════════════════════════════════════

    def acknowledge_alarm(self, alarm_id: int, by: str = "system") -> Optional[dict]:
        """确认一条报警

        Args:
            alarm_id: 报警记录ID
            by: 确认人

        Returns:
            确认后的报警记录字典, 无数据库时返回 None
        """
        if self._db_manager is None:
            logger.warning("无数据库, 无法确认报警")
            return None

        try:
            with self._db_manager.session() as session:
                repo = AlarmRecordRepository(session)
                record = repo.acknowledge(alarm_id, by=by)
                if record is None:
                    logger.warning(f"报警记录不存在: {alarm_id}")
                    return None

                result = record.to_dict()

            self.alarm_acknowledged.emit(result)
            self._update_unack_count()

            logger.info(f"报警已确认: {alarm_id} by {by}")
            return result

        except Exception as e:
            logger.exception(f"确认报警失败: {alarm_id}")
            self.error_occurred.emit(f"确认报警失败: {e}")
            return None

    def acknowledge_all_by_device(self, device_id: str, by: str = "system") -> int:
        """批量确认设备的所有未确认报警

        Returns:
            确认的数量
        """
        if self._db_manager is None:
            return 0

        try:
            with self._db_manager.session() as session:
                repo = AlarmRecordRepository(session)
                count = repo.acknowledge_all_by_device(device_id, by=by)

            self._update_unack_count()
            logger.info(f"批量确认设备报警: {device_id}, 数量={count}")
            return count

        except Exception as e:
            logger.exception(f"批量确认报警失败: {device_id}")
            self.error_occurred.emit(f"批量确认报警失败: {e}")
            return 0

    # ═══════════════════════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════════════════════

    def get_active_alarms(self, device_id: Optional[str] = None) -> List[dict]:
        """获取当前活跃报警 (内存中)

        Args:
            device_id: 可选, 指定设备ID

        Returns:
            活跃报警信息列表
        """
        result = []
        for dev_id, regs in self._active_alarms.items():
            if device_id and dev_id != device_id:
                continue
            for reg_name, info in regs.items():
                result.append(dict(info))
        return result

    def get_active_count(self, device_id: Optional[str] = None) -> int:
        """获取当前活跃报警数量"""
        if device_id is None:
            return len(self._get_all_active())
        return len(self._active_alarms.get(device_id, {}))

    def get_alarm_records(self, device_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        """从数据库查询报警记录"""
        if self._db_manager is None:
            return []

        try:
            with self._db_manager.session() as session:
                repo = AlarmRecordRepository(session)
                if device_id:
                    records = repo.get_by_device(device_id, limit=limit)
                else:
                    records = repo.get_unacknowledged(limit=limit)

                return [r.to_dict() for r in records]

        except Exception as e:
            logger.exception("查询报警记录失败")
            self.error_occurred.emit(f"查询报警记录失败: {e}")
            return []

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取报警统计

        Args:
            days: 统计最近N天

        Returns:
            统计字典
        """
        stats = dict(self._stats_cache)

        if self._db_manager is not None:
            try:
                start = _now() - timedelta(days=days)
                end = _now()

                with self._db_manager.session() as session:
                    repo = AlarmRecordRepository(session)
                    db_stats = repo.get_statistics(start, end)
                    stats["db_total"] = db_stats["total"]
                    stats["db_unacknowledged"] = db_stats["unacknowledged"]
                    stats["db_level_counts"] = db_stats["level_counts"]
                    stats["period_days"] = days

            except Exception:
                logger.exception("获取数据库报警统计失败")

        return stats

    # ═══════════════════════════════════════════════════════
    # 报警规则管理
    # ═══════════════════════════════════════════════════════

    def get_rules(self, device_id: Optional[str] = None) -> List[dict]:
        """查询报警规则"""
        if self._db_manager is None:
            return []

        try:
            with self._db_manager.session() as session:
                repo = AlarmRuleRepository(session)
                if device_id:
                    rules = repo.get_by_device(device_id)
                else:
                    rules = repo.get_enabled()

                return [r.to_dict() for r in rules]

        except Exception as e:
            logger.exception("查询报警规则失败")
            return []

    def create_rule(
        self,
        rule_id: str,
        device_id: str,
        device_name: str,
        register_name: str,
        alarm_type: str = "high_limit",
        level: int = 1,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        description: str = "",
        enabled: bool = True,
    ) -> bool:
        """创建报警规则"""
        if self._db_manager is None:
            return False

        try:
            with self._db_manager.session() as session:
                repo = AlarmRuleRepository(session)
                repo.create_rule(
                    rule_id=rule_id,
                    device_id=device_id,
                    device_name=device_name,
                    register_name=register_name,
                    alarm_type=alarm_type,
                    level=level,
                    threshold_high=threshold_high,
                    threshold_low=threshold_low,
                    description=description,
                    enabled=enabled,
                )
                return True

        except Exception as e:
            logger.exception(f"创建报警规则失败: {rule_id}")
            self.error_occurred.emit(f"创建报警规则失败: {e}")
            return False

    def delete_rule(self, rule_id: str) -> bool:
        """删除报警规则"""
        if self._db_manager is None:
            return False

        try:
            with self._db_manager.session() as session:
                repo = AlarmRuleRepository(session)
                return repo.delete_rule(rule_id)

        except Exception as e:
            logger.exception(f"删除报警规则失败: {rule_id}")
            return False

    # ═══════════════════════════════════════════════════════
    # 通知
    # ═══════════════════════════════════════════════════════

    def set_notification_callback(self, callback: Optional[Callable[[dict, str], None]]) -> None:
        """设置通知回调

        Args:
            callback: 回调函数 (alarm_info: dict, event_type: str)
                      event_type: "triggered" 或 "cleared"
        """
        self._notification_callback = callback

    # ═══════════════════════════════════════════════════════
    # 维护
    # ═══════════════════════════════════════════════════════

    def cleanup_old_records(self, days: Optional[int] = None) -> int:
        """清理过期报警记录

        Args:
            days: 清理多少天前的记录 (None 使用 auto_cleanup_days)

        Returns:
            删除的记录数
        """
        if self._db_manager is None:
            return 0

        cleanup_days = days if days is not None else self._auto_cleanup_days
        if cleanup_days <= 0:
            return 0

        try:
            with self._db_manager.session() as session:
                repo = AlarmRecordRepository(session)
                count = repo.cleanup(days=cleanup_days)

            if count > 0:
                logger.info(f"清理过期报警记录: {count}条 (>{cleanup_days}天)")

            return count

        except Exception as e:
            logger.exception("清理报警记录失败")
            return 0

    def clear_active_alarms(self) -> int:
        """清除内存中所有活跃报警 (仅内存, 不影响数据库)

        Returns:
            清除的数量
        """
        count = len(self._get_all_active())
        self._active_alarms.clear()
        self._stats_cache["active_count"] = 0
        return count

    def reset_statistics(self) -> None:
        """重置内存统计"""
        self._stats_cache = {
            "total_triggered": 0,
            "total_cleared": 0,
            "active_count": 0,
            "unacknowledged_count": 0,
        }

    # ═══════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════

    def _get_all_active(self) -> List[dict]:
        """获取所有活跃报警"""
        result = []
        for regs in self._active_alarms.values():
            result.extend(regs.values())
        return result

    def _update_unack_count(self) -> None:
        """更新未确认报警数量"""
        if self._db_manager is None:
            return

        try:
            with self._db_manager.session() as session:
                repo = AlarmRecordRepository(session)
                active = repo.get_active(limit=1)
                # 简化: 只取最新24h未确认
                count = len(active)
                self._stats_cache["unacknowledged_count"] = count

        except Exception:
            pass
