# -*- coding: utf-8 -*-
"""
工业设备管理系统 - 主程序入口
Industrial Equipment Management System

使用 PySide6 + QML 框架构建现代化工业设备监控界面
"""

import sys
import os
from pathlib import Path

# 尝试导入PySide6
try:
    from PySide6.QtCore import QObject, Slot, QTimer, QUrl, Signal
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickView
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("警告: PySide6 未安装，尝试使用 PyQt5...")

# 备用导入PyQt5
if not PYSIDE6_AVAILABLE:
    try:
        from PyQt5.QtCore import QObject, Slot, QTimer, pyqtSignal, QUrl
        from PyQt5.QtGui import QGuiApplication
        from PyQt5.QtQml import QQmlApplicationEngine
        from PyQt5.QtQuick import QQuickView
        from PyQt5 import QtCore
        PYQT5_AVAILABLE = True
    except ImportError:
        PYQT5_AVAILABLE = False

# 导入项目模块
from Backend import Backend
from logging_config import setup_logging, LogLevel

# 添加项目路径
SCRIPT_DIR = Path(__file__).parent.absolute()
QML_DIR = SCRIPT_DIR / "qml"

# 初始化日志系统
setup_logging(
    log_dir=str(SCRIPT_DIR / "logs"),
    log_level=LogLevel.INFO.value,
    max_bytes=50 * 1024 * 1024,  # 50MB
    backup_count=10,
    console_output=True
)

def get_qml_path(filename):
    """获取QML文件的绝对路径"""
    return QML_DIR / filename

def main():
    """主函数"""
    print("=" * 60)
    print("工业设备管理系统 v1.0.1")
    print("=" * 60)
    print(f"QML目录: {QML_DIR}")
    print()

    if not QML_DIR.exists():
        print(f"错误: QML目录不存在: {QML_DIR}")
        print("请确保 qml 文件夹存在于此目录下")
        input("按Enter键退出...")
        sys.exit(1)

    # 检查QML文件
    main_qml = get_qml_path("MainView.qml")
    if not main_qml.exists():
        print(f"错误: 主界面文件不存在: {main_qml}")
        input("按Enter键退出...")
        sys.exit(1)

    # 检查QML组件
    components_dir = QML_DIR / "components"
    if not components_dir.exists():
        print(f"警告: 组件目录不存在: {components_dir}")

    # 初始化Qt应用
    app = None

    if PYSIDE6_AVAILABLE:
        print("使用 PySide6 框架")
        app = QGuiApplication(sys.argv)
        app.setApplicationName("工业设备管理系统")
        app.setOrganizationName("Industrial Equipment Co.")
        app.setApplicationVersion("1.0.1")

        # 创建QML引擎
        engine = QQmlApplicationEngine()

        # 注册QML路径
        engine.addImportPath(str(QML_DIR))
        engine.addImportPath(str(QML_DIR / "components"))

        # 创建并注册后端
        backend = Backend()
        engine.rootContext().setContextProperty("backend", backend)

        # 设置额外的QML上下文属性
        engine.rootContext().setContextProperty("mainApp", app)

        # 加载主界面
        main_qml_url = QUrl.fromLocalFile(str(main_qml.absolute()))
        engine.load(main_qml_url)

        if not engine.rootObjects():
            print("错误: 无法加载QML界面")
            return 1

        # 运行应用
        return app.exec()

    elif PYQT5_AVAILABLE:
        print("使用 PyQt5 框架")
        app = QGuiApplication(sys.argv)
        app.setApplicationName("工业设备管理系统")
        app.setOrganizationName("Industrial Equipment Co.")
        app.setApplicationVersion("1.0.1")

        # 创建QML引擎
        engine = QQmlApplicationEngine()

        # 注册QML路径
        engine.addImportPath(str(QML_DIR))
        engine.addImportPath(str(QML_DIR / "components"))

        # 创建并注册后端
        backend = Backend()
        engine.rootContext().setContextProperty("backend", backend)

        # 设置额外的QML上下文属性
        engine.rootContext().setContextProperty("mainApp", app)

        # 加载主界面
        main_qml_url = QUrl(str(main_qml.absolute()))
        engine.load(main_qml_url)

        if not engine.rootObjects():
            print("错误: 无法加载QML界面")
            return 1

        # 运行应用
        return app.exec()

    else:
        print("错误: 未找到 PySide6 或 PyQt5")
        print("请安装 PySide6 或 PyQt5:")
        print("  pip install PySide6")
        print("  或")
        print("  pip install PyQt5")
        input("按Enter键退出...")
        return 1

if __name__ == "__main__":
    sys.exit(main() or 0)
