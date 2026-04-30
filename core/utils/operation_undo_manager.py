# -*- coding: utf-8 -*-
"""
操作撤销管理器 - Operation Undo Manager
========================================

提供"撤销上次写操作"功能，将设备恢复到前一状态。

功能特性:
✅ 记录每次写操作的前后值
✅ 提供撤销接口（恢复到 previous_value）
✅ 维护撤销历史栈（最多保存100条）
✅ 防止重复撤销
✅ 信号驱动架构（与 WriteOperationManager 集成）

设计原则:
✅ 操作原子性：每次写操作都记录完整的前后状态
✅ 幂等性：同一操作只能撤销一次
✅ 时序性：撤销历史按时间顺序，支持连续撤销
✅ 可追溯：完整的审计日志记录

使用示例:
    >>> undo_mgr = OperationUndoManager()
    >>> undo_mgr.undo_executed.connect(on_undo)
    >>>
    >>> # 写操作执行前记录
    >>> undo_mgr.record_operation(
    ...     req_id="wr_abc123",
    ...     device_id="device_001",
    ...     param_name="进水阀",
    ...     previous_value=False,
    ...     new_value=True
    ... )
    >>>
    >>> # 用户点击撤销
    >>> record = undo_mgr.undo_last_operation()
    >>> if record:
    ...     print(f"恢复 {record.param_name} 为 {record.previous_value}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


@dataclass
class UndoRecord:
    """
    撤销记录数据类

    存储单次写操作的完整信息，用于后续撤销时恢复原始值。

    Attributes:
        req_id: 原操作的请求ID
        device_id: 设备ID
        param_name: 参数名称
        previous_value: 操作前的原始值（用于撤销时恢复）
        new_value: 操作后的新值
        operation_type: 操作类型 ("coil_write" / "register_write")
        executed_at: 操作执行时间
        can_undo: 是否可撤销
        undone_at: 撤销时间（如果已撤销则为datetime，否则为None）
    """

    req_id: str
    device_id: str
    param_name: str
    previous_value: Any
    new_value: Any
    operation_type: str  # "coil_write" / "register_write"
    executed_at: datetime
    can_undo: bool = True
    undone_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "req_id": self.req_id,
            "device_id": self.device_id,
            "param_name": self.param_name,
            "previous_value": self._format_value(self.previous_value),
            "new_value": self._format_value(self.new_value),
            "operation_type": self.operation_type,
            "executed_at": self.executed_at.isoformat(),
            "can_undo": self.can_undo,
            "undone_at": self.undone_at.isoformat() if self.undone_at else None,
        }

    @staticmethod
    def _format_value(value: Any) -> str:
        """格式化值为可读字符串"""
        if isinstance(value, bool):
            return "ON" if value else "OFF"
        return str(value)

    @property
    def display_summary(self) -> str:
        """
        生成用户友好的摘要信息

        Returns:
            如 "进水阀: OFF → ON"
        """
        prev_str = self._format_value(self.previous_value)
        new_str = self._format_value(self.new_value)
        return f"{self.param_name}: {prev_str} → {new_str}"


class OperationUndoManager(QObject):
    """
    操作撤销管理器 - 核心控制器

    管理所有写操作的撤销记录，
    提供撤销接口和查询功能。

    信号 (Signals):
        undo_available(bool): 是否有可撤销的操作变化时发射
        undo_executed(str): 撤销操作执行完成时发射 (req_id)
        undo_failed(str, str): 撤销失败时发射 (req_id, reason)
        history_changed(): 撤销历史变化时发射

    使用示例:
        >>> undo_mgr = OperationUndoManager(max_history=100)
        >>> undo_mgr.undo_executed.connect(handle_undo)
        >>>
        >>> # 在写操作前记录
        >>> undo_mgr.record_operation(
        ...     req_id="wr_001",
        ...     device_id="dev1",
        ...     param_name="温度设定",
        ...     previous_value=2500,
        ...     new_value=2600,
        ...     operation_type="register_write"
        ... )
        >>>
        >>> # 执行撤销
        >>> record = undo_mgr.undo_last_operation()
        >>> if record:
        ...     # record 包含恢复所需的所有信息
        ...     execute_restore(record.device_id, record.param_name, record.previous_value)
    """

    # ==================== Qt 信号定义 ====================

    undo_available = Signal(bool)  # 是否有可撤销的操作
    undo_executed = Signal(str)  # 撤销操作执行完成 (req_id)
    undo_failed = Signal(str, str)  # 撤销失败 (req_id, reason)
    history_changed = Signal()  # 历史记录变化

    # 默认最大历史记录数
    DEFAULT_MAX_HISTORY = 100

    def __init__(self, max_history: int = DEFAULT_MAX_HISTORY, parent: Optional[QObject] = None) -> None:
        """
        初始化操作撤销管理器

        Args:
            max_history: 最大保存的撤销记录数（默认100条）
            parent: Qt父对象
        """
        super().__init__(parent)

        # 撤销历史栈（最新的在末尾）
        self._undo_stack: List[UndoRecord] = []

        # 已执行的请求ID集合（防止重复记录）
        self._executed_ids: set = set()

        # 最大历史记录数
        self._max_history = max_history

        logger.info("OperationUndoManager 初始化完成 (最大历史=%d条)", max_history)

    def record_operation(
        self,
        req_id: str,
        device_id: str,
        param_name: str,
        previous_value: Any,
        new_value: Any,
        operation_type: str = "coil_write",
    ) -> None:
        """
        记录写操作（在执行前调用）

        此方法应在实际写入操作执行之前调用，
        用于保存操作前的原始值。

        Args:
            req_id: 写操作请求ID（来自 WriteOperationManager）
            device_id: 设备ID
            param_name: 参数名称
            previous_value: 操作前的值（用于撤销时恢复）
            new_value: 要写入的新值
            operation_type: 操作类型 ("coil_write" / "register_write")

        Examples:
            >>> # 在 WriteOperationManager.request_write() 中调用
            >>> current_value = get_current_device_value(device_id, param_name)
            >>> undo_mgr.record_operation(
            ...     req_id=req_id,
            ...     device_id=device_id,
            ...     param_name=param_name,
            ...     previous_value=current_value,
            ...     new_value=target_value,
            ...     operation_type="coil_write"
            ... )
        """
        # 防止重复记录同一请求
        if req_id in self._executed_ids:
            logger.debug("撤销记录已存在，跳过: %s", req_id)
            return

        # 创建撤销记录
        record = UndoRecord(
            req_id=req_id,
            device_id=device_id,
            param_name=param_name,
            previous_value=previous_value,
            new_value=new_value,
            operation_type=operation_type,
            executed_at=datetime.now(),
            can_undo=True,
        )

        # 添加到栈中
        self._undo_stack.append(record)
        self._executed_ids.add(req_id)

        # 限制历史栈大小（超出时移除最旧的记录）
        while len(self._undo_stack) > self._max_history:
            removed = self._undo_stack.pop(0)
            # 从已执行集合中也移除
            self._executed_ids.discard(removed.req_id)
            logger.debug("撤销记录已清理（超出上限）: %s", removed.req_id)

        # 发射信号
        self.undo_available.emit(True)
        self.history_changed.emit()

        logger.info(
            "记录撤销操作 [参数=%s, %s → %s, req=%s]",
            param_name,
            UndoRecord._format_value(previous_value),
            UndoRecord._format_value(new_value),
            req_id,
        )

    def undo_last_operation(self) -> Optional[UndoRecord]:
        """
        撤销最后一次操作

        从栈顶取出最后一条可撤销的记录，
        标记为已撤销并发射信号通知外部执行实际的恢复操作。

        流程：
        1. 从栈顶取出最后一条记录
        2. 检查是否可撤销（can_undo == True 且 未被撤销过）
        3. 标记为正在撤销（设置 can_undo=False）
        4. 发射 undo_executed 信号
        5. 返回记录供外部执行恢复

        Returns:
            UndoRecord 如果成功找到可撤销的操作
            None 如果没有可撤销的操作

        Examples:
            >>> record = undo_mgr.undo_last_operation()
            >>> if record:
            ...     # 外部执行实际的恢复写入
            ...     success = device.confirm_write(
            ...         record.param_name,
            ...         record.previous_value
            ...     )
            ...     if not success:
            ...         undo_mgr.mark_undo_failed(record.req_id, "恢复写入失败")
        """
        if not self._undo_stack:
            logger.warning("没有可撤销的操作")
            self.undo_available.emit(False)
            return None

        # 从栈顶开始查找第一条可撤销的记录
        for i in range(len(self._undo_stack) - 1, -1, -1):
            record = self._undo_stack[i]

            # 检查是否可撤销
            if not record.can_undo:
                continue

            if record.undone_at is not None:
                # 已经被撤销过
                continue

            # 找到可撤销的记录
            # 标记为不可撤销（防止重复撤销）
            record.can_undo = False
            record.undone_at = datetime.now()

            logger.info(
                "准备撤销操作 [参数=%s, 恢复为=%s, req=%s]",
                record.param_name,
                UndoRecord._format_value(record.previous_value),
                record.req_id,
            )

            # 发射信号通知外部执行恢复
            self.undo_executed.emit(record.req_id)

            # 检查是否还有其他可撤销的操作
            has_undoable = any(r.can_undo and r.undone_at is None for r in self._undo_stack)
            self.undo_available.emit(has_undoable)
            self.history_changed.emit()

            return record

        # 没有找到可撤销的记录
        logger.warning("没有找到可撤销的操作（可能都已撤销）")
        self.undo_available.emit(False)
        return None

    def mark_undo_failed(self, req_id: str, reason: str) -> None:
        """
        标记撤销操作失败

        当外部执行恢复写入失败时调用此方法。
        将记录重新标记为可撤销（允许重试）。

        Args:
            req_id: 请求ID
            reason: 失败原因
        """
        # 查找记录
        record = None
        for r in self._undo_stack:
            if r.req_id == req_id:
                record = r
                break

        if record is None:
            logger.error("未找到撤销记录: %s", req_id)
            return

        # 重新标记为可撤销（允许重试）
        record.can_undo = True
        record.undone_at = None

        # 发射信号
        self.undo_failed.emit(req_id, reason)
        self.undo_available.emit(True)

        logger.warning("撤销操作失败，已标记为可重试 [req=%s, 原因=%s]", req_id, reason)

    def mark_undo_success(self, req_id: str) -> None:
        record = None
        for r in self._undo_stack:
            if r.req_id == req_id:
                record = r
                break

        if record is None:
            logger.error("未找到撤销记录: %s", req_id)
            return

        record.can_undo = False
        logger.info("撤销操作成功 [req=%s]", req_id)

    def get_undo_history(self, limit: int = 10) -> List[UndoRecord]:
        """
        获取最近的撤销历史

        返回最近的N条记录（最新的在前）。

        Args:
            limit: 返回的最大条数

        Returns:
            UndoRecord 列表（最新的在前）
        """
        # 取出最近N条并反转（让最新的在前）
        recent = self._undo_stack[-limit:] if limit > 0 else []
        return list(reversed(recent))

    @property
    def can_undo(self) -> bool:
        """
        是否有可撤销的操作

        Returns:
            True 如果至少有一条可撤销的记录
        """
        return any(r.can_undo and r.undone_at is None for r in self._undo_stack)

    @property
    def history_count(self) -> int:
        """获取当前历史记录总数"""
        return len(self._undo_stack)

    @property
    def undoable_count(self) -> int:
        """获取可撤销的记录数量"""
        return sum(1 for r in self._undo_stack if r.can_undo and r.undone_at is None)

    def clear_history(self) -> None:
        """
        清空撤销历史

        谨慎使用！清空后将无法撤销任何操作。
        """
        count = len(self._undo_stack)
        self._undo_stack.clear()
        self._executed_ids.clear()

        self.undo_available.emit(False)
        self.history_changed.emit()

        logger.info("撤销历史已清空 (%d 条记录)", count)

    def remove_record(self, req_id: str) -> bool:
        """
        移除指定的撤销记录

        Args:
            req_id: 要移除的请求ID

        Returns:
            是否成功移除
        """
        for i, record in enumerate(self._undo_stack):
            if record.req_id == req_id:
                removed = self._undo_stack.pop(i)
                self._executed_ids.discard(req_id)

                # 更新可用状态
                self.undo_available.emit(self.can_undo)
                self.history_changed.emit()

                logger.info("撤销记录已移除: %s", req_id)
                return True

        logger.warning("未找到要移除的撤销记录: %s", req_id)
        return False

    def get_record_by_req_id(self, req_id: str) -> Optional[UndoRecord]:
        """
        根据请求ID查找撤销记录

        Args:
            req_id: 请求ID

        Returns:
            UndoRecord 实例，未找到返回 None
        """
        for record in self._undo_stack:
            if record.req_id == req_id:
                return record
        return None

    def __repr__(self) -> str:
        return (
            f"OperationUndoManager("
            f"total={len(self._undo_stack)}, "
            f"undoable={self.undoable_count}, "
            f"max={self._max_history})"
        )
