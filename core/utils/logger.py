# -*- coding: utf-8 -*-
"""
日志系统模块
Logger System Module
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


class AppLogger:
    """应用日志管理器"""

    _instance: Optional["AppLogger"] = None
    _loggers: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._log_dir = "logs"
        self._ensure_log_dir()
        self._initialized = True

    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self._log_dir):
            os.makedirs(self._log_dir)

    def get_logger(self, name: str = "app") -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        if logger.handlers:
            self._loggers[name] = logger
            return logger

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = RotatingFileHandler(
            os.path.join(self._log_dir, f"{name}_{today}.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        self._loggers[name] = logger
        return logger

    def set_level(self, name: str, level: int):
        """
        设置日志级别

        Args:
            name: 日志记录器名称
            level: 日志级别 (logging.DEBUG, logging.INFO, etc.)
        """
        if name in self._loggers:
            self._loggers[name].setLevel(level)


def get_logger(name: str = "app") -> logging.Logger:
    """
    便捷函数：获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return AppLogger().get_logger(name)
