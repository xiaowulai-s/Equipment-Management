#!/usr/bin/env python
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
    from PySide6.QtCore import QObject, Slot, QTimer, QUrl
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

# 添加项目路径
SCRIPT_DIR = Path(__file__).parent.absolute()
QML_DIR = SCRIPT_DIR / "qml"

def get_qml_path(filename):
    """获取QML文件的绝对路径"""
    return QML_DIR / filename

def main():
    """主函数"""
    print("=" * 60)
    print("工业设备管理系统 v1.0.0")
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

        # 创建QML引擎
        engine = QQmlApplicationEngine()

        # 注册QML路径
        engine.addImportPath(str(QML_DIR))

        # 创建Theme单例对象并注入到QML
        class Theme(QObject):
            # 主色调
            primary500 = "#2196F3"
            primary400 = "#42A5F5"
            primary600 = "#1E88E5"
            accent500 = "#00BCD4"
            # 功能色
            success500 = "#4CAF50"
            warning500 = "#FFC107"
            error500 = "#F44336"
            # 深色主题
            bgBase = "#0F1419"
            bgRaised = "#161B22"
            bgOverlay = "#1C2128"
            bgHover = "#21262D"
            bgActive = "#30363D"
            # 文本色
            textPrimary = "#E6EDF3"
            textSecondary = "#8B949E"
            textTertiary = "#6E7681"
            # 边框色
            borderDefault = "#30363D"
            # 字体
            fontSans = "Inter, -apple-system, sans-serif"
            fontMono = "JetBrains Mono, monospace"
            # 字号
            fontH4 = 18
            fontH3 = 20
            fontBody = 15
            fontBodySm = 14
            fontCaption = 13
            fontDataLg = 32
            fontData = 24
            # 间距
            space1 = 4
            space2 = 8
            space3 = 12
            space4 = 16
            space5 = 20
            space6 = 24
            space8 = 32
            # 圆角
            radiusMd = 6
            radiusLg = 8

        theme = Theme()
        engine.rootContext().setContextProperty("Theme", theme)

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

        # 创建QML引擎
        engine = QQmlApplicationEngine()

        # 注册QML路径
        engine.addImportPath(str(QML_DIR))

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