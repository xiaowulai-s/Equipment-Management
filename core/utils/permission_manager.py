# -*- coding: utf-8 -*-
"""
权限管理系统 - Permission Manager
================================

实现三级权限体系（管理员/操作员/观察者），控制写操作访问。

功能特性:
✅ 用户认证（登录/登出）
✅ 权限检查（写操作前验证）
✅ 会话管理（超时自动登出）
✅ 操作审计（记录谁在什么时候做了什么）
✅ 密码哈希存储（SHA256）

权限等级:
- ADMIN (管理员): 完全权限，可执行所有操作
- OPERATOR (操作员): 可执行写操作（需确认）
- OBSERVER (观察者): 只读，无法执行写操作

使用示例:
    >>> pm = PermissionManager()
    >>> pm.login("admin", "admin123")  # True
    >>> pm.check_write_permission()  # (True, "权限充足")
    >>> pm.logout()

设计原则:
✅ 安全性: 密码使用SHA256哈希存储
✅ 可扩展: 支持自定义用户数据源（数据库/LDAP）
✅ 信号驱动: 使用Qt Signal通知权限状态变化
✅ 审计追踪: 所有登录/登出/权限检查都有日志记录
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """
    用户角色枚举

    定义系统的三种用户角色及其权限级别。
    """

    ADMIN = auto()  # 管理员：完全权限（配置管理、用户管理、所有写操作）
    OPERATOR = auto()  # 操作员：可执行写操作（需二次确认）
    OBSERVER = auto()  # 观察者：只读模式，无法执行任何写操作

    @property
    def display_name(self) -> str:
        """获取角色显示名称"""
        names = {
            UserRole.ADMIN: "管理员",
            UserRole.OPERATOR: "操作员",
            UserRole.OBSERVER: "观察者",
        }
        return names.get(self, "未知")

    @property
    def can_write(self) -> bool:
        """是否可以执行写操作"""
        return self in [UserRole.ADMIN, UserRole.OPERATOR]

    @property
    def can_manage_users(self) -> bool:
        """是否可以管理用户（添加/删除/修改）"""
        return self == UserRole.ADMIN

    @property
    def requires_confirmation(self) -> bool:
        """写操作是否需要额外确认"""
        return self == UserRole.OPERATOR


@dataclass
class User:
    """
    用户数据类

    Attributes:
        username: 用户名（唯一标识符）
        password_hash: 密码的SHA256哈希值
        role: 用户角色
        is_active: 账户是否激活
        last_login: 最后登录时间
        created_at: 账户创建时间
    """

    username: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def verify_password(self, plain_password: str) -> bool:
        """
        验证密码

        Args:
            plain_password: 明文密码

        Returns:
            是否匹配
        """
        return self.password_hash == PermissionManager._hash_password(plain_password)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role.name,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PermissionManager(QObject):
    """
    权限管理器 - 核心控制器

    提供完整的用户认证和权限管理功能。

    信号 (Signals):
        permission_denied(str, str): 权限被拒绝时发射
            参数: (username, reason)
        user_logged_in(str, UserRole): 用户登录成功时发射
            参数: (username, role)
        user_logged_out(str): 用户登出时发射
            参数: (username)
        session_timeout(str): 会话超时时发射
            参数: (username)
        permission_changed(): 权限状态变化时发射（用于UI更新）

    线程安全:
        ✅ 所有公共方法都是线程安全的
        ✅ 信号在主线程中发射（Qt机制保证）

    使用示例:
        >>> pm = PermissionManager(parent=app)
        >>> pm.user_logged_in.connect(on_login)
        >>> pm.permission_denied.connect(on_denied)
        >>>
        >>> # 登录
        >>> if pm.login("operator", "operator123"):
        ...     print(f"已登录为 {pm.current_user_role.display_name}")
        >>>
        >>> # 检查权限
        >>> allowed, reason = pm.check_write_permission()
        >>> if not allowed:
        ...     print(f"权限不足: {reason}")
    """

    # ==================== Qt 信号定义 ====================

    permission_denied = Signal(str, str)  # username, reason
    user_logged_in = Signal(str, object)  # username, UserRole
    user_logged_out = Signal(str)  # username
    session_timeout = Signal(str)  # username
    permission_changed = Signal()  # 权限状态变化

    # 默认会话超时时间（30分钟）
    DEFAULT_SESSION_TIMEOUT_MS = 30 * 60 * 1000

    def __init__(self, parent: Optional[QObject] = None, session_timeout_ms: int = DEFAULT_SESSION_TIMEOUT_MS) -> None:
        """
        初始化权限管理器

        Args:
            parent: Qt父对象
            session_timeout_ms: 会话超时时间（毫秒），默认30分钟
        """
        super().__init__(parent)

        # 当前登录的用户
        self._current_user: Optional[User] = None

        # 用户数据库 {username: User}
        self._users: Dict[str, User] = {}

        # 会话超时设置
        self._session_timeout_ms = session_timeout_ms

        # 会话超时定时器
        self._session_timer: Optional[QTimer] = None
        self._last_activity_time: float = 0.0  # 上次活动时间戳

        # 审计日志列表
        self._audit_log: List[Dict[str, Any]] = []

        # 加载默认用户
        self._load_default_users()

        # 初始化会话超时定时器
        self._init_session_timer()

        logger.info("PermissionManager 初始化完成 (超时=%d秒)", session_timeout_ms // 1000)

    def _init_session_timer(self) -> None:
        """初始化会话超时检测定时器"""
        self._session_timer = QTimer(self)
        self._session_timer.setInterval(60000)  # 每分钟检查一次
        self._session_timer.timeout.connect(self._check_session_timeout)
        self._session_timer.start()

        logger.debug("会话超时检测定时器已启动（间隔60秒）")

    def _check_session_timeout(self) -> None:
        """检查会话是否超时"""
        if self._current_user is None:
            return

        elapsed_ms = (time.time() - self._last_activity_time) * 1000

        if elapsed_ms > self._session_timeout_ms:
            username = self._current_user.username
            logger.warning("会话超时，自动登出用户: %s (空闲%.1f分钟)", username, elapsed_ms / 60000)

            # 记录审计日志
            self._log_audit("SESSION_TIMEOUT", f"会话超时 ({elapsed_ms / 60000:.1f}分钟)")

            # 执行登出
            self.logout()

            # 发射超时信号
            self.session_timeout.emit(username)

    @staticmethod
    def _hash_password(plain_password: str) -> str:
        """
        计算密码的SHA256哈希值

        Args:
            plain_password: 明文密码

        Returns:
            SHA256哈希字符串（64字符十六进制）
        """
        return hashlib.sha256(plain_password.encode("utf-8")).hexdigest()

    def _load_default_users(self) -> None:
        """
        加载默认用户账户

        生产环境应从数据库或LDAP加载，
        此处提供默认账户用于开发和测试。
        """
        now = datetime.now()

        default_users = [
            User(
                username="admin",
                password_hash=self._hash_password("admin123"),
                role=UserRole.ADMIN,
                is_active=True,
                created_at=now,
            ),
            User(
                username="operator",
                password_hash=self._hash_password("operator123"),
                role=UserRole.OPERATOR,
                is_active=True,
                created_at=now,
            ),
            User(
                username="viewer",
                password_hash=self._hash_password("viewer123"),
                role=UserRole.OBSERVER,
                is_active=True,
                created_at=now,
            ),
        ]

        for user in default_users:
            self._users[user.username] = user

        logger.info("已加载 %d 个默认用户账户: %s", len(default_users), ", ".join(u.username for u in default_users))

    def login(self, username: str, password: str) -> bool:
        """
        用户登录认证

        验证用户名和密码，成功后设置当前用户并发射信号。

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            是否登录成功

        Raises:
            无异常，失败返回False

        Examples:
            >>> if pm.login("admin", "admin123"):
            ...     print("登录成功")
            ... else:
            ...     print("用户名或密码错误")
        """
        # 查找用户
        user = self._users.get(username)

        if user is None:
            logger.warning("登录失败: 用户不存在 '%s'", username)
            self._log_audit("LOGIN_FAILED", f"用户不存在: {username}")
            return False

        # 检查账户是否激活
        if not user.is_active:
            logger.warning("登录失败: 账户已禁用 '%s'", username)
            self._log_audit("LOGIN_FAILED", f"账户已禁用: {username}")
            return False

        # 验证密码
        if not user.verify_password(password):
            logger.warning("登录失败: 密码错误 '%s'", username)
            self._log_audit("LOGIN_FAILED", f"密码错误: {username}")
            return False

        # 登录成功
        self._current_user = user
        self._last_activity_time = time.time()

        # 更新最后登录时间
        user.last_login = datetime.now()

        # 记录审计日志
        self._log_audit("LOGIN_SUCCESS", f"角色={user.role.display_name}")

        # 发射信号
        self.user_logged_in.emit(username, user.role)
        self.permission_changed.emit()

        logger.info("用户登录成功 [用户=%s, 角色=%s]", username, user.role.display_name)

        return True

    def logout(self) -> None:
        """
        用户登出

        清除当前用户状态并发射信号。
        """
        if self._current_user is None:
            return

        username = self._current_user.username
        role = self._current_user.role

        # 记录审计日志
        self._log_audit("LOGOUT", f"角色={role.display_name}")

        # 清除当前用户
        self._current_user = None
        self._last_activity_time = 0.0

        # 发射信号
        self.user_logged_out.emit(username)
        self.permission_changed.emit()

        logger.info("用户已登出: %s", username)

    def check_write_permission(
        self, device_id: Optional[str] = None, param_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        检查写操作权限

        在每次写操作前调用此方法验证当前用户是否有权执行。

        权限规则:
        - ADMIN: 允许所有写操作（无需额外确认或仅需一次确认）
        - OPERATOR: 允许写操作（但需要二次确认对话框）
        - OBSERVER: 拒绝所有写操作（按钮应置灰/隐藏）
        - 未登录: 拒绝所有写操作（提示先登录）

        Args:
            device_id: 设备ID（可选，用于审计日志）
            param_name: 参数名称（可选，用于审计日志）

        Returns:
            (allowed: bool, reason: str)
            - allowed: True表示允许执行
            - reason: 不允许时的原因说明

        Examples:
            >>> allowed, reason = pm.check_write_permission()
            >>> if not allowed:
            ...     QMessageBox.warning(None, "权限不足", reason)
        """
        # 更新活动时间（防止会话超时）
        self._update_activity()

        # 检查是否已登录
        if self._current_user is None:
            reason = "未登录，请先登录系统"
            logger.warning("写操作被拒绝: 未登录 [设备=%s, 参数=%s]", device_id, param_name)
            self.permission_denied.emit("", reason)
            self._log_audit("WRITE_DENIED", reason, device_id, param_name)
            return (False, reason)

        user = self._current_user
        username = user.username
        role = user.role

        # 检查账户是否激活
        if not user.is_active:
            reason = f"账户 '{username}' 已被禁用"
            logger.warning("写操作被拒绝: 账户已禁用 [用户=%s, 设备=%s, 参数=%s]", username, device_id, param_name)
            self.permission_denied.emit(username, reason)
            self._log_audit("WRITE_DENIED", reason, device_id, param_name)
            return (False, reason)

        # 根据角色判断权限
        if role == UserRole.ADMIN:
            # 管理员：完全权限
            logger.debug(
                "写操作权限通过 [用户=%s, 角色=%s, 设备=%s, 参数=%s]",
                username,
                role.display_name,
                device_id,
                param_name,
            )
            self._log_audit("WRITE_ALLOWED", "管理员完全权限", device_id, param_name)
            return (True, "")

        elif role == UserRole.OPERATOR:
            # 操作员：允许但需要确认
            logger.info("写操作权限通过（需确认）[用户=%s, 设备=%s, 参数=%s]", username, device_id, param_name)
            self._log_audit("WRITE_ALLOWED_NEEDS_CONFIRM", "操作员需要二次确认", device_id, param_name)
            return (True, "需要二次确认")

        elif role == UserRole.OBSERVER:
            # 观察者：只读模式
            reason = f"当前用户 '{username}' 为观察者角色，" f"无法执行写操作。请联系管理员升级权限。"
            logger.warning("写操作被拒绝: 观察者无写权限 [用户=%s, 设备=%s, 参数=%s]", username, device_id, param_name)
            self.permission_denied.emit(username, reason)
            self._log_audit("WRITE_DENIED", "观察者只读模式", device_id, param_name)
            return (False, reason)

        else:
            # 未知角色（防御性编程）
            reason = f"未知用户角色: {role}"
            logger.error("写操作被拒绝: %s [用户=%s]", reason, username)
            self.permission_denied.emit(username, reason)
            self._log_audit("WRITE_DENIED", reason, device_id, param_name)
            return (False, reason)

    def _update_activity(self) -> None:
        """更新最后活动时间（防止会话超时）"""
        self._last_activity_time = time.time()

    def _log_audit(
        self, event: str, detail: str = "", device_id: Optional[str] = None, param_name: Optional[str] = None
    ) -> None:
        """
        记录审计日志

        Args:
            event: 事件类型
            detail: 详细信息
            device_id: 相关设备ID
            param_name: 相关参数名
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "detail": detail,
            "user": self._current_user.username if self._current_user else None,
            "role": self._current_user.role.name if self._current_user else None,
            "device_id": device_id,
            "param_name": param_name,
        }

        self._audit_log.append(log_entry)

        # 限制日志大小（最多保留2000条）
        if len(self._audit_log) > 2000:
            self._audit_log = self._audit_log[-2000:]

    # ==================== 属性访问器 ====================

    @property
    def current_user(self) -> Optional[User]:
        """获取当前登录的用户对象"""
        return self._current_user

    @property
    def current_username(self) -> Optional[str]:
        """获取当前登录用户名"""
        return self._current_user.username if self._current_user else None

    @property
    def current_user_role(self) -> Optional[UserRole]:
        """获取当前用户角色"""
        return self._current_user.role if self._current_user else None

    @property
    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self._current_user is not None

    @property
    def is_admin(self) -> bool:
        """当前用户是否是管理员"""
        return self._current_user is not None and self._current_user.role == UserRole.ADMIN

    @property
    def can_write(self) -> bool:
        """当前用户是否可执行写操作"""
        if not self._current_user:
            return False
        return self._current_user.role.can_write

    @property
    def requires_confirmation(self) -> bool:
        """写操作是否需要二次确认"""
        if not self._current_user:
            return True  # 未登录时要求确认（实际会被拒绝）
        return self._current_user.role.requires_confirmation

    # ==================== 用户管理方法 ====================

    def add_user(self, username: str, password: str, role: UserRole, is_active: bool = True) -> Tuple[bool, str]:
        """
        添加新用户（仅ADMIN可用）

        Args:
            username: 用户名（唯一）
            password: 明文密码
            role: 用户角色
            is_active: 是否激活

        Returns:
            (success, message)
        """
        # 权限检查
        if not self.is_admin:
            return (False, "只有管理员才能添加用户")

        # 检查用户名是否已存在
        if username in self._users:
            return (False, f"用户名 '{username}' 已存在")

        # 创建用户
        user = User(
            username=username,
            password_hash=self._hash_password(password),
            role=role,
            is_active=is_active,
            created_at=datetime.now(),
        )

        self._users[username] = user

        # 记录审计日志
        self._log_audit("USER_ADDED", f"角色={role.display_name}")

        logger.info("用户已添加: %s (%s)", username, role.display_name)
        return (True, f"用户 '{username}' 创建成功")

    def remove_user(self, username: str) -> Tuple[bool, str]:
        """
        删除用户（仅ADMIN可用）

        不能删除自己或默认的 admin/operator/viewer 账户。

        Args:
            username: 要删除的用户名

        Returns:
            (success, message)
        """
        # 权限检查
        if not self.is_admin:
            return (False, "只有管理员才能删除用户")

        # 不能删除自己
        if self._current_user and username == self._current_user.username:
            return (False, "不能删除自己的账户")

        # 保护默认账户
        protected_users = {"admin", "operator", "viewer"}
        if username in protected_users:
            return (False, f"不能删除内置账户 '{username}'")

        # 检查用户是否存在
        if username not in self._users:
            return (False, f"用户 '{username}' 不存在")

        # 删除用户
        del self._users[username]

        # 记录审计日志
        self._log_audit("USER_REMOVED", f"用户={username}")

        logger.info("用户已删除: %s", username)
        return (True, f"用户 '{username}' 已删除")

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        修改用户密码

        管理员可以修改任意用户的密码，
        其他用户只能修改自己的密码。

        Args:
            username: 目标用户名
            old_password: 旧密码（非管理员必须提供）
            new_password: 新密码

        Returns:
            (success, message)
        """
        # 查找用户
        user = self._users.get(username)
        if user is None:
            return (False, f"用户 '{username}' 不存在")

        # 权限检查
        if not self.is_admin:
            # 非管理员只能修改自己的密码
            if self._current_user is None or username != self._current_user.username:
                return (False, "只能修改自己的密码")

            # 验证旧密码
            if not user.verify_password(old_password):
                return (False, "旧密码错误")

        # 更新密码
        user.password_hash = self._hash_password(new_password)

        # 记录审计日志
        self._log_audit("PASSWORD_CHANGED", f"用户={username}")

        logger.info("密码已修改: %s", username)
        return (True, f"用户 '{username}' 密码修改成功")

    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        获取所有用户列表（仅ADMIN可用）

        Returns:
            用户信息列表（不包含密码哈希）
        """
        if not self.is_admin:
            return []

        result = []
        for user in self._users.values():
            info = {
                "username": user.username,
                "role": user.role.name,
                "role_display": user.role.display_name,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            result.append(info)

        return result

    def get_audit_log(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取审计日志

        Args:
            limit: 返回的最大条数
            event_type: 事件类型过滤（可选）

        Returns:
            审计日志列表（最新的在前）
        """
        logs = list(self._audit_log)

        # 按事件类型过滤
        if event_type:
            logs = [log for log in logs if log.get("event") == event_type]

        # 返回最新的N条（反转顺序）
        return list(reversed(logs[-limit:]))

    def set_session_timeout(self, timeout_minutes: int) -> None:
        """
        设置会话超时时间

        Args:
            timeout_minutes: 超时时间（分钟）
        """
        self._session_timeout_ms = timeout_minutes * 60 * 1000
        logger.info("会话超时已设置为 %d 分钟", timeout_minutes)

    def cleanup(self) -> None:
        """清理资源"""
        if self._session_timer is not None:
            self._session_timer.stop()
            self._session_timer = None

        logger.info("PermissionManager 资源已清理")

    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except Exception:
            pass

    def __repr__(self) -> str:
        status = "已登录" if self.is_logged_in else "未登录"
        role = self.current_user_role.display_name if self.current_user_role else "-"
        return f"PermissionManager(status={status}, role={role})"
