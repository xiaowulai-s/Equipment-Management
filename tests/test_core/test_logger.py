# -*- coding: utf-8 -*-
"""
日志系统测试
Logger System Tests
"""

import pytest

from core.utils.logger import AppLogger, get_logger


class TestLogger:
    """日志系统测试类"""

    def test_get_logger(self):
        """测试获取日志记录器"""
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"

    def test_logger_singleton(self):
        """测试 AppLogger 单例模式"""
        logger1 = AppLogger()
        logger2 = AppLogger()
        assert logger1 is logger2

    def test_logger_levels(self):
        """测试日志级别"""
        logger = get_logger("test_levels")

        # 测试不同级别的日志
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # 验证日志记录器级别
        assert logger.level == 10  # DEBUG

    def test_logger_set_level(self):
        """测试设置日志级别"""
        logger = get_logger("test_set_level")
        app_logger = AppLogger()

        # 设置级别为 ERROR
        app_logger.set_level("test_set_level", 40)  # ERROR
        assert logger.level == 40


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
