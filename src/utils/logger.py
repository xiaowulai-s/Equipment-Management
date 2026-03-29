"""
日志系统 - 工业设备管理系统

设计原则:
    1. 基于 Python logging 模块，封装统一接口
    2. 支持日志分类: communication / device / alarm / system
    3. 多线程安全 (logging 模块原生支持)
    4. 支持日志轮转 (按大小, 10MB/文件, 最多5个备份)
    5. 控制台 + 文件双输出
    6. UTF-8 编码
    7. 全局单例模式，通过 get_logger(name) 获取

使用示例:
    from src.utils.logger import get_logger
    logger = get_logger("device")
    logger.info("设备已连接", extra={"device_id": "PUMP-01"})
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# 日志格式
# ═══════════════════════════════════════════════════════════════


class ColorFormatter(logging.Formatter):
    """彩色控制台日志格式化器

    不同日志级别使用不同颜色，提升可读性。
    """

    # ANSI颜色码
    COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname_colored = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


# 控制台格式: 2026-03-26 15:00:00 [INFO   ] [device   ] 消息内容
CONSOLE_FORMAT = "%(asctime)s [%(levelname_colored)s] [%(name)-10s] %(message)s"
CONSOLE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 文件格式: 2026-03-26 15:00:00.123 [INFO] [device] 消息内容 | device_id=PUMP-01
FILE_FORMAT = "%(asctime)s.%(msecs)03d [%(levelname)s] [%(name)s] %(message)s"
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ═══════════════════════════════════════════════════════════════
# 全局配置
# ═══════════════════════════════════════════════════════════════

# 全局初始化标志
_initialized = False


def setup_logging(
    log_dir: str = "logs",
    level: str = "INFO",
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    console_output: bool = True,
) -> None:
    """初始化全局日志配置

    Args:
        log_dir: 日志文件目录
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        max_file_size_mb: 单个日志文件最大大小(MB)
        backup_count: 保留的备份文件数量
        console_output: 是否输出到控制台
    """
    global _initialized
    if _initialized:
        return

    root_logger = logging.getLogger("src")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()

    # ── 控制台Handler ──
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColorFormatter(CONSOLE_FORMAT, CONSOLE_DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # ── 文件Handler (按大小轮转) ──
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    log_file = log_path / f"equipment_{date_str}.log"

    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_file_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(FILE_FORMAT, FILE_DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    _initialized = True
    root_logger.info(
        "日志系统初始化完成",
        extra={
            "log_dir": str(log_path),
            "level": level,
        },
    )


# ═══════════════════════════════════════════════════════════════
# Logger获取接口
# ═══════════════════════════════════════════════════════════════


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的Logger实例

    推荐使用以下分类名称:
        - "protocol"    : 协议层日志
        - "driver"      : 通信驱动层日志
        - "device"      : 设备管理层日志
        - "data"        : 数据持久化层日志
        - "alarm"       : 报警系统日志
        - "ui"          : UI层日志
        - "system"      : 系统级日志

    Args:
        name: Logger名称 (自动添加 "src." 前缀)

    Returns:
        logging.Logger 实例

    Example:
        >>> logger = get_logger("device")
        >>> logger.info("设备连接成功", extra={"device_id": "PUMP-01"})
    """
    full_name = f"src.{name}" if not name.startswith("src.") else name
    return logging.getLogger(full_name)
