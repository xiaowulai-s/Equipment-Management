# -*- coding: utf-8 -*-
"""
性能分析脚本
Performance Profiling Script
"""

import cProfile
import io
import pstats
import sys
from pathlib import Path
from pstats import SortKey

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data.models import DatabaseManager, DeviceModel
from core.device.device_manager import DeviceManager


def profile_device_operations():
    """分析设备操作性能"""
    db_manager = DatabaseManager()
    db_manager.initialize()
    device_manager = DeviceManager(db_manager)

    # 分析添加设备
    profiler = cProfile.Profile()
    profiler.enable()

    # 添加 50 个设备
    devices = []
    for i in range(50):
        device = DeviceModel(
            name=f"ProfileDevice_{i}",
            device_type="PLC",
            protocol="modbus_tcp",
            ip=f"192.168.1.{100 + i}",
            port=502,
            slave_id=i + 1,
        )
        device_manager.add_device(device)
        devices.append(device)

    profiler.disable()

    # 输出统计信息
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats(SortKey.CUMULATIVE)
    stats.print_stats(20)  # 打印前 20 个最耗时的函数

    print("=" * 80)
    print("设备添加性能分析（50 个设备）")
    print("=" * 80)
    print(stream.getvalue())

    # 清理
    for device in devices:
        device_manager.remove_device(device.id)

    db_manager.close()


def profile_database_queries():
    """分析数据库查询性能"""
    db_manager = DatabaseManager()
    db_manager.initialize()
    device_manager = DeviceManager(db_manager)

    # 先添加一些设备
    devices = []
    for i in range(30):
        device = DeviceModel(
            name=f"QueryProfileDevice_{i}",
            device_type="Sensor",
            protocol="modbus_tcp",
            ip=f"192.168.2.{100 + i}",
            port=502,
            slave_id=i + 1,
        )
        device_manager.add_device(device)
        devices.append(device)

    # 分析查询操作
    profiler = cProfile.Profile()
    profiler.enable()

    # 执行 50 次查询
    for _ in range(50):
        device_manager.list_devices()
        device_manager.get_device(devices[0].id)

    profiler.disable()

    # 输出统计信息
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats(SortKey.CUMULATIVE)
    stats.print_stats(20)

    print("\n" + "=" * 80)
    print("数据库查询性能分析（50 次查询）")
    print("=" * 80)
    print(stream.getvalue())

    # 清理
    for device in devices:
        device_manager.remove_device(device.id)

    db_manager.close()


if __name__ == "__main__":
    print("开始性能分析...\n")

    profile_device_operations()
    profile_database_queries()

    print("\n性能分析完成！")
