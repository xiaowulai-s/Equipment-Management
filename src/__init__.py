"""
工业设备管理系统 - 核心源码包

四层解耦架构:
    - protocols/       协议层: ModbusTCP/RTU/ASCII协议实现
    - communication/   通信驱动层: TCP/串口驱动
    - device/          设备管理层: 设备模型、工厂、管理器
    - data/            数据持久化层: SQLite + Repository模式
    - alarm/           报警系统
    - utils/           工具模块
"""

__version__ = "1.5.5"
__author__ = "Industrial Equipment Management Team"
