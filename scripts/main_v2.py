# -*- coding: utf-8 -*-
"""
工业设备管理系统 v2.0
Industrial Equipment Management System v2.0
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.data import get_db_manager  # noqa: E402
from core.utils.logger_v2 import setup_logging  # noqa: E402

# 配置日志（在导入其他模块之前）
logger = setup_logging(
    log_level="INFO", log_file="logs/app.log", db_manager=None, console_output=True  # 数据库初始化后再设置
)

# 延迟导入UI，确保日志已配置
from ui.main_window_v2 import MainWindowV2  # noqa: E402


def main():
    """主函数"""
    global logger
    try:
        # 初始化数据库
        db_manager = get_db_manager("data/equipment_management.db")
        logger.info("数据库初始化完成")

        # 重新配置日志，添加数据库处理器
        logger = setup_logging(log_level="INFO", log_file="logs/app.log", db_manager=db_manager, console_output=True)

        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName("工业设备管理系统")
        app.setApplicationVersion("2.0.0")
        app.setApplicationDisplayName("工业设备管理系统 v2.0")

        # 设置高DPI支持
        app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

        # 创建主窗口
        window = MainWindowV2(db_manager=db_manager)
        window.show()

        logger.info("应用程序启动")

        # 运行应用
        exit_code = app.exec()

        # 清理
        window.cleanup()
        logger.info("应用程序关闭")

        sys.exit(exit_code)

    except Exception as e:
        logger.error("应用程序启动失败", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    main()
