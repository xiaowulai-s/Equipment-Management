# -*- coding: utf-8 -*-
"""
性能测试
Performance Tests
"""

import sys
import time
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.data.models import AlarmRuleModel, DatabaseManager, DeviceModel, HistoricalDataModel
from core.device.device_manager import DeviceManager
from core.utils.alarm_manager import AlarmManager


@pytest.fixture(scope="module")
def db_manager():
    """创建数据库管理器实例"""
    db = DatabaseManager()
    # DatabaseManager 在__init__中自动初始化
    yield db
    db.close()


@pytest.fixture(scope="module")
def device_manager(db_manager):
    """创建设备管理器实例"""
    return DeviceManager(db_manager)


class TestPerformance:
    """性能测试类"""

    def test_device_add_performance(self, device_manager):
        """测试添加设备的性能"""
        start_time = time.time()

        # 添加 100 个设备
        devices = []
        for i in range(100):
            device = DeviceModel(
                name=f"PerfTestDevice_{i}",
                device_type="PLC",
                protocol="modbus_tcp",
                ip=f"192.168.1.{100 + i}",
                port=502,
                slave_id=i + 1,
            )
            device_manager.add_device(device)
            devices.append(device)

        elapsed = time.time() - start_time

        # 验证性能：100 个设备应该在 10 秒内完成
        assert elapsed < 10.0, f"添加 100 个设备耗时 {elapsed:.2f}秒，超过预期"

        # 清理
        for device in devices:
            device_manager.remove_device(device.id)

        print(f"\n添加 100 个设备耗时：{elapsed:.2f}秒")

    def test_device_query_performance(self, device_manager):
        """测试设备查询性能"""
        # 先添加一些设备
        devices = []
        for i in range(50):
            device = DeviceModel(
                name=f"QueryTestDevice_{i}",
                device_type="Sensor",
                protocol="modbus_tcp",
                ip=f"192.168.2.{100 + i}",
                port=502,
                slave_id=i + 1,
            )
            device_manager.add_device(device)
            devices.append(device)

        # 测试查询性能
        start_time = time.time()

        # 查询 100 次
        for _ in range(100):
            device_manager.list_devices()

        elapsed = time.time() - start_time

        # 验证性能：100 次查询应该在 5 秒内完成
        assert elapsed < 5.0, f"100 次查询耗时 {elapsed:.2f}秒，超过预期"

        # 清理
        for device in devices:
            device_manager.remove_device(device.id)

        print(f"\n100 次设备查询耗时：{elapsed:.2f}秒")

    def test_alarm_check_performance(self, alarm_manager, device_manager):
        """测试报警检查性能"""
        # 添加设备
        device = DeviceModel(
            name="AlarmPerfDevice", device_type="PLC", protocol="modbus_tcp", ip="192.168.3.100", port=502, slave_id=1
        )
        device_manager.add_device(device)

        # 添加多个报警规则
        rules = []
        for i in range(20):
            rule = AlarmRuleModel(
                device_id=device.id,
                register_address=40001 + i,
                condition="greater_than",
                threshold=50 + i,
                alarm_type="high_limit",
                enabled=True,
            )
            alarm_manager.add_alarm_rule(rule)
            rules.append(rule)

        # 测试报警检查性能
        start_time = time.time()

        # 检查 1000 次
        for i in range(1000):
            alarm_manager.check_alarm(device.id, 40001, 75)

        elapsed = time.time() - start_time

        # 验证性能：1000 次报警检查应该在 5 秒内完成
        assert elapsed < 5.0, f"1000 次报警检查耗时 {elapsed:.2f}秒，超过预期"

        # 清理
        for rule in rules:
            alarm_manager.remove_alarm_rule(rule.id)
        device_manager.remove_device(device.id)

        print(f"\n1000 次报警检查耗时：{elapsed:.2f}秒")

    def test_bulk_device_operations(self, device_manager):
        """测试批量设备操作性能"""
        # 批量添加
        start_time = time.time()

        devices = []
        for i in range(200):
            device = DeviceModel(
                name=f"BulkDevice_{i}",
                device_type="PLC",
                protocol="modbus_tcp",
                ip=f"192.168.4.{i % 256}",
                port=502,
                slave_id=i + 1,
            )
            device_manager.add_device(device)
            devices.append(device)

        bulk_add_time = time.time() - start_time

        # 批量删除
        start_time = time.time()

        for device in devices:
            device_manager.remove_device(device.id)

        bulk_delete_time = time.time() - start_time

        # 验证性能
        total_time = bulk_add_time + bulk_delete_time
        assert total_time < 20.0, f"批量操作耗时 {total_time:.2f}秒，超过预期"

        print(f"\n批量添加 200 个设备耗时：{bulk_add_time:.2f}秒")
        print(f"批量删除 200 个设备耗时：{bulk_delete_time:.2f}秒")


class TestMemoryUsage:
    """内存使用测试类"""

    def test_device_manager_memory(self, device_manager):
        """测试设备管理器的内存使用"""
        import tracemalloc

        tracemalloc.start()

        # 创建和删除大量设备
        for i in range(500):
            device = DeviceModel(
                name=f"MemoryTestDevice_{i}",
                device_type="Sensor",
                protocol="modbus_tcp",
                ip=f"10.0.{i // 256}.{i % 256}",
                port=502,
                slave_id=i + 1,
            )
            device_manager.add_device(device)
            device_manager.remove_device(device.id)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 验证内存使用：峰值应该小于 100MB
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 100, f"内存峰值使用 {peak_mb:.2f}MB，超过预期"

        print(f"\n内存峰值使用：{peak_mb:.2f}MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
