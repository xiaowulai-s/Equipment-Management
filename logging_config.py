# -*- coding: utf-8 -*-
"""
工业设备管理系统 - 统一日志配置
实现系统级别的日志管理和配置
"""

import logging
import logging.config
import os
from pathlib import Path
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> None:
    """
    设置统一的日志配置
    
    Args:
        log_dir: 日志文件存储目录
        log_level: 日志级别
        max_bytes: 单个日志文件最大大小
        backup_count: 日志文件备份数量
        console_output: 是否在控制台输出日志
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 日志文件名
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = log_path / f"equipment_management_{current_date}.log"
    
    # 日志格式
    log_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 日志配置字典
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
        },
        "handlers": {
            "file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": str(log_file),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {
                "handlers": [],
                "level": log_level,
                "propagate": True
            },
            # 第三方库日志配置
            "pymodbus": {
                "level": logging.WARNING,
                "handlers": [],
                "propagate": True
            },
            "PyQt6": {
                "level": logging.WARNING,
                "handlers": [],
                "propagate": True
            },
        },
    }
    
    # 添加控制台输出
    if console_output:
        logging_config["handlers"]["console_handler"] = {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
    
    # 为所有处理器添加所有处理程序
    all_handlers = list(logging_config["handlers"].keys())
    for logger_config in logging_config["loggers"].values():
        logger_config["handlers"] = all_handlers
    
    # 应用日志配置
    logging.config.dictConfig(logging_config)
    
    # 记录日志配置信息
    logger = logging.getLogger("logging_config")
    logger.info(f"日志系统初始化完成，日志文件路径: {log_file}")
    logger.info(f"日志级别: {logging.getLevelName(log_level)}")
    logger.info(f"控制台输出: {console_output}")


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)
