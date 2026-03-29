"""
数据库连接管理器

设计原则:
    1. 单例/多例模式: 按db_path缓存实例, 内存数据库不复用
    2. 上下文session: session() 自动 commit/rollback/close
    3. SQLite优化: WAL模式, 外键约束, 同步策略可配
    4. 线程安全: check_same_thread=False, 支持跨线程访问
    5. 路径解析: 构造参数 > 环境变量 > pytest内存 > 默认路径

SQLite配置:
    PRAGMA foreign_keys=ON    — 外键约束
    PRAGMA journal_mode=WAL    — 写前日志 (并发优化)
    PRAGMA synchronous=NORMAL  — 性能与安全平衡
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

Base = declarative_base()


def utc_now() -> datetime:
    """返回时区感知的UTC时间戳"""
    return datetime.now(timezone.utc)


class DatabaseManager:
    """SQLite数据库连接/会话管理器

    Usage:
        db = DatabaseManager()              # 默认路径
        db = DatabaseManager(":memory:")    # 内存数据库
        db = DatabaseManager("custom.db")   # 自定义路径

        with db.session() as session:
            session.add(model)
            # 自动 commit / rollback / close

    注意:
        - 同一路径共享同一实例 (除 :memory:)
        - 内存数据库不复用, 每次新建
        - session() 是事务安全的上下文管理器
    """

    _instances: Dict[str, DatabaseManager] = {}

    def __new__(cls, db_path: Optional[str] = None) -> DatabaseManager:
        resolved = cls._resolve_db_path(db_path)
        if resolved == ":memory:":
            # 内存数据库不复用
            instance = super().__new__(cls)
            instance._initialized = False
            return instance
        if resolved not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[resolved] = instance
        return cls._instances[resolved]

    def __init__(self, db_path: Optional[str] = None) -> None:
        if getattr(self, "_initialized", False):
            return

        db_path = self._resolve_db_path(db_path)

        # 确保目录存在
        if db_path != ":memory:":
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

        self._db_path = db_path

        # 创建引擎
        if db_path == ":memory:":
            self._engine = create_engine(
                "sqlite://",
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                future=True,
            )
        else:
            self._engine = create_engine(
                f"sqlite:///{db_path}",
                echo=False,
                connect_args={"check_same_thread": False},
                future=True,
            )

        # 注册 SQLite 连接配置事件
        event.listen(self._engine, "connect", self._configure_sqlite)

        # 创建会话工厂
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

        # 建表
        Base.metadata.create_all(self._engine)

        self._initialized = True
        logger.info(f"数据库已初始化: {db_path}")

    # ═══════════════════════════════════════════════════════════
    # 会话管理
    # ═══════════════════════════════════════════════════════════

    @contextmanager
    def session(self) -> Iterator[Session]:
        """事务安全会话上下文管理器

        使用方式:
            with db.session() as session:
                session.add(model)
                # 正常退出自动commit, 异常自动rollback+close
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("数据库事务执行失败, 已回滚: %s", self._db_path)
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """获取原始session (调用者负责生命周期)

        用于长生命周期场景 (如服务层缓存session).
        调用者必须手动 commit/rollback/close.
        """
        return self._session_factory()

    # ═══════════════════════════════════════════════════════════
    # 生命周期
    # ═══════════════════════════════════════════════════════════

    def close(self) -> None:
        """释放数据库引擎"""
        if self._engine:
            self._engine.dispose()
        if getattr(self, "_db_path", None) == ":memory:":
            self._initialized = False

    @classmethod
    def reset_instance(cls) -> None:
        """清除单例缓存 (仅用于测试)"""
        cls._instances = {}

    # ═══════════════════════════════════════════════════════════
    # 属性
    # ═══════════════════════════════════════════════════════════

    @property
    def db_path(self) -> str:
        return self._db_path

    @property
    def engine(self):
        return self._engine

    # ═══════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _resolve_db_path(db_path: Optional[str] = None) -> str:
        """解析数据库路径 (优先级: 参数 > 环境变量 > pytest内存 > 默认)"""
        if db_path:
            return db_path

        env_path = os.getenv("EQUIPMENT_MANAGEMENT_DB_PATH")
        if env_path:
            return env_path

        # pytest 环境自动使用内存数据库
        if os.getenv("PYTEST_CURRENT_TEST"):
            return ":memory:"

        return os.path.join("data", "equipment_management.db")

    @staticmethod
    def _configure_sqlite(dbapi_connection: Any, _: Any) -> None:
        """配置 SQLite 连接参数"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            logger.debug("journal_mode=WAL 设置失败, 使用默认模式")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def get_db_manager(db_path: Optional[str] = None) -> DatabaseManager:
    """获取数据库管理器实例 (便捷函数)"""
    return DatabaseManager(db_path)


def init_database(db_path: Optional[str] = None) -> DatabaseManager:
    """初始化数据库并返回管理器 (便捷函数)"""
    return DatabaseManager(db_path)
