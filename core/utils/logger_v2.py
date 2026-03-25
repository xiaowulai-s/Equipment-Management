# -*- coding: utf-8 -*-
"""
结构化日志系统
Structured Logging System
"""

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from core.data.models import DatabaseManager, SystemLogModel


class DatabaseLogHandler(logging.Handler):
    """数据库日志处理器 - 将日志写入数据库"""

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self._db_manager = db_manager

    def emit(self, record: logging.LogRecord) -> None:
        """写入日志到数据库"""
        try:
            # 获取异常信息
            exception_info = None
            if record.exc_info:
                exception_info = self.formatException(record.exc_info)

            log_entry = SystemLogModel(
                level=record.levelname,
                logger=record.name,
                message=self.format(record),
                module=record.module,
                function=record.funcName,
                line=record.lineno,
                exception=exception_info,
            )

            # 使用新会话写入
            session = self._db_manager.get_session()
            try:
                session.add(log_entry)
                session.commit()
            except:
                session.rollback()
            finally:
                session.close()

        except Exception:
            self.handleError(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    db_manager: Optional[DatabaseManager] = None,
    console_output: bool = True,
) -> structlog.stdlib.BoundLogger:
    """
    配置结构化日志系统

    Args:
        log_level: 日志级别 DEBUG/INFO/WARNING/ERROR/CRITICAL
        log_file: 日志文件路径
        db_manager: 数据库管理器（用于写入数据库）
        console_output: 是否输出到控制台
    """

    # 配置标准库日志
    handlers: list = []

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")  # 10MB
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # 数据库处理器
    if db_manager:
        db_handler = DatabaseLogHandler(db_manager)
        db_handler.setLevel(logging.WARNING)  # 数据库只记录警告及以上级别
        handlers.append(db_handler)

    # 配置根日志记录器
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取结构化日志记录器"""
    return structlog.get_logger(name)


class LoggerMixin:
    """日志混入类 - 为类提供结构化日志功能"""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """获取日志记录器"""
        return structlog.get_logger(self.__class__.__name__)
