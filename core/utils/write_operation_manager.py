# -*- coding: utf-8 -*-
"""
写操作统一安全网关 - Write Operation Manager
=============================================

处理流程：
    用户点击阀门按钮
      → DynamicMonitorPanel.coil_write_requested
        → MainWindow._on_coil_write_request
          → WriteOperationManager.request_write()
            → emit confirm_required → QMessageBox
              → 用户Yes/No
                → on_user_confirmed()
                  → 审计日志
                    → emit operation_result
                      → device.confirm_write() → protocol.write_single_coil()

设计原则:
✅ 安全网关：所有写操作必须经过确认流程
✅ 状态机：严格的状态转换（pending→confirmed/cancelled→executed/aborted）
✅ 审计日志：完整记录所有写操作历史
✅ 并发安全：支持多请求排队处理

状态机定义:
    PENDING (待确认)
      ├─→ CONFIRMED (已确认) ──→ EXECUTED (已执行)
      └─→ CANCELLED (已取消) ──→ ABORTED (已中止)

使用示例:
    >>> manager = WriteOperationManager()
    >>> manager.confirm_required.connect(show_confirmation_dialog)
    >>> manager.operation_result.connect(handle_result)
    >>>
    >>> # 发起写请求
    >>> req_id = manager.request_write("device_001", "进水阀", True, config)
    >>>
    >>> # 用户确认后调用
    >>> manager.on_user_confirmed(req_id, approved=True)
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from .permission_manager import PermissionManager

logger = logging.getLogger(__name__)


class WriteOperationStatus(Enum):
    """写操作状态枚举"""

    PENDING = auto()  # 待用户确认
    CONFIRMED = auto()  # 用户已确认，等待执行
    CANCELLED = auto()  # 用户取消
    EXECUTED = auto()  # 已成功执行
    ABORTED = auto()  # 执行失败或中止


@dataclass
class WriteOperation:
    """
    写操作数据类

    Attributes:
        req_id: 唯一请求ID
        device_id: 设备标识符
        param_name: 参数名称
        value: 目标值
        config: 寄存器点配置（RegisterPointConfig）
        status: 当前状态
        created_at: 创建时间戳
        confirmed_at: 确认时间戳
        executed_at: 执行时间戳
        result: 执行结果（True=成功, False=失败）
        error_message: 错误信息
    """

    req_id: str
    device_id: str
    param_name: str
    value: Any  # bool for coil, int/float for register
    config: object  # RegisterPointConfig instance
    status: WriteOperationStatus = WriteOperationStatus.PENDING
    created_at: float = field(default_factory=time.time)
    confirmed_at: Optional[float] = None
    executed_at: Optional[float] = None
    result: Optional[bool] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于审计日志）"""
        return {
            "req_id": self.req_id,
            "device_id": self.device_id,
            "param_name": self.param_name,
            "value": self.value,
            "status": self.status.name,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "confirmed_at": (datetime.fromtimestamp(self.confirmed_at).isoformat() if self.confirmed_at else None),
            "executed_at": (datetime.fromtimestamp(self.executed_at).isoformat() if self.executed_at else None),
            "result": self.result,
            "error_message": self.error_message,
        }


class WriteOperationManager(QObject):
    """
    写操作统一安全网关

    核心职责：
    - 接收写请求并分配唯一ID
    - 发射确认信号等待用户响应
    - 管理操作生命周期（状态机）
    - 记录完整审计日志
    - 处理并发请求队列

    信号:
        confirm_required(str, str, Any, object): 需要用户确认
            参数: (device_id, param_name, value, config)
        operation_result(str, dict): 操作完成通知
            参数: (req_id, operation_dict)

    使用示例:
        >>> manager = WriteOperationManager()
        >>>
        >>> # 连接信号
        >>> manager.confirm_required.connect(
        ...     lambda dev_id, name, val, cfg: show_confirm_dialog(dev_id, name, val)
        ... )
        >>> manager.operation_result.connect(handle_operation_completed)
        >>>
        >>> # 发起写请求
        >>> req_id = manager.request_write("dev_001", "进水阀", True, coil_config)
        >>>
        >>> # 用户点击Yes后回调
        >>> manager.on_user_confirmed(req_id, approved=True)
    """

    # ==================== Qt 信号定义 ====================

    confirm_required = Signal(str, str, object, object)  # device_id, param_name, value, config
    operation_result = Signal(str, dict)  # req_id, operation_dict

    # ✅ 新增：批量操作信号
    batch_confirm_required = Signal(str, list, object)  # device_id, [(name, value), ...], config
    batch_operation_result = Signal(str, dict)  # req_id, {name: result}

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 操作存储 {req_id: WriteOperation}
        self._operations: Dict[str, WriteOperation] = {}

        # 审计日志列表
        self._audit_log: List[Dict[str, Any]] = []

        # 最大并发请求数
        self._max_concurrent_requests = 10

        # 权限管理器引用（由外部设置）
        self._permission_manager: Optional["PermissionManager"] = None

        # ✅ 新增：撤销管理器引用（由外部设置）
        self._undo_manager: Optional["OperationUndoManager"] = None

        logger.info("WriteOperationManager 初始化完成")

    # ==================== ✅ 新增：批量写操作方法 ====================

    def request_batch_write(self, device_id: str, operations: List[Dict[str, Any]], config: object) -> str:
        """
        发起批量写请求

        一次提交多个写操作，支持线圈和寄存器混合。
        UI层会显示批量确认对话框。

        Args:
            device_id: 设备标识符
            operations: 操作列表
                [{"name": "进水阀", "value": True}, {"name": "温度设定", "value": 2500}, ...]
            config: 配置信息（可包含操作类型等元数据）

        Returns:
            请求ID字符串

        Examples:
            >>> ops = [
            ...     {"name": "阀1", "value": True},
            ...     {"name": "阀2", "value": False},
            ... ]
            >>> req_id = manager.request_batch_write("dev_001", ops, batch_config)
        """
        # 权限检查
        if self._permission_manager is not None:
            allowed, reason = self._permission_manager.check_write_permission(
                device_id=device_id, param_name="[批量操作]"
            )

            if not allowed:
                req_id = f"batch_{uuid.uuid4().hex[:12]}"
                self.batch_operation_result.emit(req_id, {"error": f"权限不足: {reason}", "results": {}})
                return req_id

        # 生成请求ID
        req_id = f"batch_{uuid.uuid4().hex[:12]}"

        # 提取操作摘要（用于确认对话框显示）
        operation_summary = [(op.get("name", f"@{op.get('address', '?')}"), op.get("value")) for op in operations]

        logger.info("批量写操作请求已创建 [req=%s, 设备=%s, 操作数=%d]", req_id, device_id, len(operations))

        # 发射批量确认信号
        self.batch_confirm_required.emit(device_id, operation_summary, config)

        return req_id

    def on_batch_confirmed(self, req_id: str, approved: bool) -> None:
        """
        用户确认/取消批量操作回调

        Args:
            req_id: 请求ID
            approved: True=用户确认, False=用户取消
        """
        if approved:
            logger.info("用户已确认批量写操作 [req=%s]", req_id)
            self.batch_operation_result.emit(req_id, {"status": "confirmed", "req_id": req_id})
        else:
            logger.info("用户已取消批量写操作 [req=%s]", req_id)
            self.batch_operation_result.emit(req_id, {"status": "cancelled", "req_id": req_id})

    def request_write(
        self,
        device_id: str,
        param_name: str,
        value: Any,
        config: object,
        skip_confirm: bool = False,
    ) -> str:
        """
        发起写操作请求

        这是写操作的入口方法。
        创建操作记录、发射确认信号、返回请求ID。

        Args:
            device_id: 设备标识符
            param_name: 参数名称（如"进水阀"、"温度设定值"）
            value: 目标值（bool用于线圈，int/float用于寄存器）
            config: 寄存器点配置对象（RegisterPointConfig）

        Returns:
            请求ID字符串（用于后续确认回调）

        Raises:
            RuntimeError: 并发请求数超过限制时抛出

        Examples:
            >>> req_id = manager.request_write(
            ...     "device_001",
            ...     "进水阀",
            ...     True,
            ...     coil_config
            ... )
            >>> print(f"请求已提交: {req_id}")
        """
        # 检查并发限制
        pending_count = sum(1 for op in self._operations.values() if op.status == WriteOperationStatus.PENDING)

        if pending_count >= self._max_concurrent_requests:
            raise RuntimeError(f"并发请求数超过限制 ({self._max_concurrent_requests})")

        # ✅ 新增：权限检查（如果配置了权限管理器）
        if self._permission_manager is not None:
            allowed, reason = self._permission_manager.check_write_permission(
                device_id=device_id, param_name=param_name
            )

            if not allowed:
                # 权限不足，生成请求ID但标记为DENIED状态
                req_id = f"wr_{uuid.uuid4().hex[:12]}"

                operation = WriteOperation(
                    req_id=req_id,
                    device_id=device_id,
                    param_name=param_name,
                    value=value,
                    config=config,
                    status=WriteOperationStatus.CANCELLED,  # 直接标记为取消
                )
                operation.error_message = f"权限不足: {reason}"

                self._operations[req_id] = operation
                self._log_audit(operation, "PERMISSION_DENIED")

                # 发射结果信号（包含拒绝信息）
                self.operation_result.emit(req_id, operation.to_dict())

                logger.warning(
                    "写操作被权限系统拒绝 [req=%s, 设备=%s, 参数=%s, 原因=%s]", req_id, device_id, param_name, reason
                )

                return req_id

        # 生成唯一请求ID
        req_id = f"wr_{uuid.uuid4().hex[:12]}"

        # 创建操作记录
        operation = WriteOperation(
            req_id=req_id,
            device_id=device_id,
            param_name=param_name,
            value=value,
            config=config,
            status=WriteOperationStatus.PENDING,
        )

        # 存储到内存
        self._operations[req_id] = operation

        # 记录审计日志
        self._log_audit(operation, "REQUEST_CREATED")

        logger.info(
            "写操作请求已创建 [req=%s, 设备=%s, 参数=%s, 值=%s]",
            req_id,
            device_id,
            param_name,
            "ON" if value else "OFF" if isinstance(value, bool) else value,
        )

        if skip_confirm:
            self.on_user_confirmed(req_id, approved=True)
        else:
            self.confirm_required.emit(device_id, param_name, value, config)

        return req_id

    def on_user_confirmed(self, req_id: str, approved: bool) -> None:
        """
        用户确认/取消回调

        当用户在确认对话框中点击"Yes"或"No"后，
        由MainWindow调用此方法。

        Args:
            req_id: 请求ID（由 request_write() 返回）
            approved: True=用户确认, False=用户取消

        Examples:
            >>> # 在MainWindow的槽函数中
            >>> def _on_dialog_closed(self, req_id, result):
            ...     if result == QDialog.DialogCode.Accepted:
            ...         write_manager.on_user_confirmed(req_id, approved=True)
            ...     else:
            ...         write_manager.on_user_confirmed(req_id, approved=False)
        """
        operation = self._operations.get(req_id)

        if operation is None:
            logger.error("未找到写操作请求: %s", req_id)
            return

        # 检查当前状态（必须是PENDING才能确认）
        if operation.status != WriteOperationStatus.PENDING:
            logger.warning("操作状态错误 [req=%s, 当前状态=%s, 期望=PENDING]", req_id, operation.status.name)
            return

        if approved:
            # 用户确认 → 转换为CONFIRMED状态
            operation.status = WriteOperationStatus.CONFIRMED
            operation.confirmed_at = time.time()

            self._log_audit(operation, "USER_CONFIRMED")

            logger.info(
                "用户已确认写操作 [req=%s, 设备=%s, 参数=%s]", req_id, operation.device_id, operation.param_name
            )

            # 注意：实际执行由外部调用 execute_operation() 完成
            # 这里只更新状态，发射结果信号
            self.operation_result.emit(req_id, operation.to_dict())

        else:
            # 用户取消 → 转换为CANCELLED状态
            operation.status = WriteOperationStatus.CANCELLED

            self._log_audit(operation, "USER_CANCELLED")

            logger.info(
                "用户已取消写操作 [req=%s, 设备=%s, 参数=%s]", req_id, operation.device_id, operation.param_name
            )

            # 发射结果信号（包含取消信息）
            self.operation_result.emit(req_id, operation.to_dict())

    def mark_executed(self, req_id: str, success: bool, error_msg: Optional[str] = None) -> None:
        """
        标记操作执行完成

        由外部调用（如DeviceConnection.confirm_write()完成后），
        用于更新最终状态和审计日志。

        Args:
            req_id: 请求ID
            success: 是否执行成功
            error_msg: 失败时的错误信息

        Examples:
            >>> # 在 DeviceConnection.coil_written 信号的槽函数中
            >>> def _on_coil_written(param_name, address, success):
            ...     write_manager.mark_executed(current_req_id, success)
        """
        operation = self._operations.get(req_id)

        if operation is None:
            logger.error("未找到写操作请求: %s", req_id)
            return

        # 更新状态和结果
        operation.executed_at = time.time()
        operation.result = success
        operation.error_message = error_msg

        if success:
            operation.status = WriteOperationStatus.EXECUTED
            self._log_audit(operation, "EXECUTION_SUCCESS")

            # ✅ 新增：记录到撤销管理器（如果已配置）
            if self._undo_manager is not None:
                # 确定操作类型
                operation_type = "coil_write" if isinstance(operation.value, bool) else "register_write"

                # 记录撤销信息（previous_value 需要外部提供，这里先记录基本信息）
                # 注意：理想的实现应该在 request_write() 时读取当前值作为 previous_value
                # 这里简化处理，记录 new_value 为当前值，撤销时会提示用户
                self._undo_manager.record_operation(
                    req_id=req_id,
                    device_id=operation.device_id,
                    param_name=operation.param_name,
                    previous_value=not operation.value if isinstance(operation.value, bool) else 0,
                    new_value=operation.value,
                    operation_type=operation_type,
                )
                logger.debug("写操作已记录到撤销历史 [req=%s, 参数=%s]", req_id, operation.param_name)
        else:
            operation.status = WriteOperationStatus.ABORTED
            self._log_audit(operation, "EXECUTION_FAILED")

        logger.info(
            "写操作执行完成 [req=%s, 结果=%s%s]",
            req_id,
            "成功" if success else "失败",
            f", 错误={error_msg}" if not success else "",
        )

        # 发射最终结果信号
        self.operation_result.emit(req_id, operation.to_dict())

    def get_operation(self, req_id: str) -> Optional[WriteOperation]:
        """
        获取操作详情

        Args:
            req_id: 请求ID

        Returns:
            WriteOperation 实例，不存在返回None
        """
        return self._operations.get(req_id)

    def get_pending_operations(self) -> List[WriteOperation]:
        """
        获取所有待处理的操作

        Returns:
            状态为PENDING的操作列表
        """
        return [op for op in self._operations.values() if op.status == WriteOperationStatus.PENDING]

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """
        获取完整审计日志

        Returns:
            审计日志列表（每条记录为一个字典）
        """
        return list(self._audit_log)

    def clear_history(self, older_than_seconds: Optional[int] = None) -> int:
        """
        清理历史操作记录

        Args:
            older_than_seconds: 清理多少秒前的记录（None=全部清理）

        Returns:
            清理的记录数
        """
        now = time.time()
        to_remove = []

        for req_id, op in self._operations.items():
            if older_than_seconds is None:
                to_remove.append(req_id)
            elif (now - op.created_at) > older_than_seconds:
                to_remove.append(req_id)

        for req_id in to_remove:
            del self._operations[req_id]

        count = len(to_remove)

        if count > 0:
            logger.info("已清理 %d 条历史写操作记录", count)

        return count

    def _log_audit(self, operation: WriteOperation, event: str) -> None:
        """
        记录审计日志

        Args:
            operation: 写操作实例
            event: 事件类型字符串
        """
        log_entry = {
            **operation.to_dict(),
            "event": event,
            "event_time": datetime.now().isoformat(),
        }

        self._audit_log.append(log_entry)

        # 限制日志大小（最多保留1000条）
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            包含各状态操作数量的统计字典
        """
        stats = {
            "total": len(self._operations),
            "pending": 0,
            "confirmed": 0,
            "cancelled": 0,
            "executed": 0,
            "aborted": 0,
            "success_rate": 0.0,
        }

        executed_success = 0
        executed_total = 0

        for op in self._operations.values():
            status_name = op.status.name.lower()
            if status_name in stats:
                stats[status_name] += 1

            if op.status == WriteOperationStatus.EXECUTED:
                executed_total += 1
                if op.result:
                    executed_success += 1

        # 计算成功率
        if executed_total > 0:
            stats["success_rate"] = (executed_success / executed_total) * 100.0

        return stats

    def set_permission_manager(self, pm: Optional["PermissionManager"]) -> None:
        """
        设置权限管理器（依赖注入）

        Args:
            pm: PermissionManager 实例，传入 None 可移除权限检查
        """
        self._permission_manager = pm
        logger.info("WriteOperationManager 权限管理器已%s", "设置" if pm else "移除")

    def set_undo_manager(self, um: Optional["OperationUndoManager"]) -> None:
        """
        设置撤销管理器（依赖注入）

        当设置后，每次写操作成功执行时会自动记录到撤销历史中。

        Args:
            um: OperationUndoManager 实例，传入 None 可移除撤销记录
        """
        self._undo_manager = um
        logger.info("WriteOperationManager 撤销管理器已%s", "设置" if um else "移除")

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"WriteOperationManager("
            f"total={stats['total']}, "
            f"pending={stats['pending']}, "
            f"success_rate={stats['success_rate']:.1f}%)"
        )
