"""
工业设备管理系统 - 程序入口 (新架构)

启动流程:
    1. 初始化日志系统
    2. 初始化数据库
    3. 创建 QApplication
    4. 应用主题样式
    5. 启动主窗口
"""

import json
import sys
from pathlib import Path


def main() -> int:
    """应用程序主入口"""
    # ── Step 1: 初始化日志系统 ──
    from core.utils.logger_v2 import get_logger, setup_logging

    setup_logging(log_level="INFO")
    logger = get_logger("system")
    logger.info("工业设备管理系统启动中...")

    # ── Step 2: 加载配置 (从 config.json) ──
    _PROJECT_ROOT = Path(__file__).resolve().parent
    config_path = _PROJECT_ROOT / "config.json"

    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info("配置加载完成")
        except Exception as e:
            logger.warning(f"配置加载失败，使用默认配置: {e}")
    else:
        logger.info("配置文件不存在，使用默认配置")

    # ── Step 3: 初始化数据库 ──
    from core.data import DatabaseManager

    try:
        db_path = config.get("database", {}).get("path", "data/equipment_management.db")
        db_manager = DatabaseManager(db_path)
        logger.info(f"数据库初始化完成: {db_path}")
    except Exception as e:
        logger.critical(f"数据库初始化失败: {e}")
        return 1

    # ── Step 4: 创建Qt应用 ──
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    # 高DPI支持
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("工业设备管理系统")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("IndustrialEquip")

    # ── Step 5: 启动主窗口 ──
    from ui.main_window_v2 import MainWindowV2

    # 创建并显示主窗口
    window = MainWindowV2(db_manager=db_manager)
    min_w = config.get("ui", {}).get("window_min_width", 1280)
    min_h = config.get("ui", {}).get("window_min_height", 720)
    window.setMinimumSize(min_w, min_h)
    window.show()

    logger.info("系统启动完成")
    exit_code = app.exec()

    logger.info(f"系统关闭 (exit_code={exit_code})")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
