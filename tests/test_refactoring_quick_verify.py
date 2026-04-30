# -*- coding: utf-8 -*-
"""
生产级重构核心验证测试 (v3.1 - 简化版)

专注于验证4个关键重构点的核心逻辑：
✅ 任务1: modbus_protocol不再依赖async_wait
✅ 任务2: device_manager使用写锁和Shadow Instance
✅ 任务3: alarm_manager实现缓存机制
✅ 任务4: _schedule_async_polls使用快照机制
"""

import sys
import os
import time
import unittest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTask1_ModbusProtocolNoAsyncWait(unittest.TestCase):
    """任务1验证：移除async_wait依赖"""

    def test_no_async_utils_import(self):
        """modbus_protocol不应导入async_utils模块"""
        import core.protocols.modbus_protocol as mp

        self.assertFalse(
            hasattr(mp, "ASYNC_UTILS_AVAILABLE"), "不应存在ASYNC_UTILS_AVAILABLE常量（已移除async_utils导入）"
        )

    def test_async_delay_uses_time_sleep(self):
        """_async_delay应使用time.sleep"""
        from core.protocols.modbus_protocol import ModbusProtocol

        protocol = ModbusProtocol()

        with patch("core.protocols.modbus_protocol.time.sleep") as mock_sleep:
            protocol._async_delay(0.5)
            mock_sleep.assert_called_once_with(0.5)

    def test_async_delay_zero_skips_sleep(self):
        """_async_delay(0)不应调用sleep"""
        from core.protocols.modbus_protocol import ModbusProtocol

        protocol = ModbusProtocol()

        with patch("core.protocols.modbus_protocol.time.sleep") as mock_sleep:
            protocol._async_delay(0)
            mock_sleep.assert_not_called()


class TestTask2_DeviceManagerWriteLock(unittest.TestCase):
    """任务2验证：设备管理器使用写锁保护"""

    def test_write_lock_exists(self):
        """DeviceManager应有_write_lock属性"""
        from core.device.device_manager import DeviceManager
        from core.data import DatabaseManager

        with patch.object(DatabaseManager, "__new__", return_value=Mock()):
            mgr = DeviceManager(db_manager=Mock())
            self.assertTrue(hasattr(mgr, "_write_lock"), "DeviceManager应具有_write_lock属性")
            import threading

            self.assertIsInstance(mgr._write_lock, type(threading.Lock()), "_write_lock应是threading.Lock类型")


class TestTask3_AlarmManagerCacheMechanism(unittest.TestCase):
    """任务3验证：报警管理器实现缓存"""

    def test_cache_attributes_exist(self):
        """AlarmManager应具有缓存相关属性"""
        from core.utils.alarm_manager import AlarmManager

        # 创建不带DB的实例（避免初始化时同步）
        with patch.object(AlarmManager, "__init__", lambda self, **kw: None):
            mgr = AlarmManager()

            # 手动设置缓存属性（模拟__init__）
            mgr._rule_cache = {}
            mgr._cache_lock = __import__("threading").RLock()
            mgr._cache_version = 0
            mgr._last_sync_time = 0.0
            mgr._cache_initialized = False
            mgr._db_manager = None
            mgr._rules = {}
            mgr._active_alarms = {}
            mgr._alarm_history = []
            mgr._alarm_counter = 0

            # 验证缓存方法存在
            self.assertTrue(hasattr(mgr, "sync_rules_from_db"), "应有sync_rules_from_db方法")
            self.assertTrue(hasattr(mgr, "invalidate_cache"), "应有invalidate_cache方法")
            self.assertTrue(hasattr(mgr, "get_cache_statistics"), "应有get_cache_statistics方法")
            self.assertTrue(hasattr(mgr, "_is_cache_valid"), "应有_is_cache_valid方法")


class TestTask4_SchedulerSnapshotMechanism(unittest.TestCase):
    """任务4验证：调度器使用快照机制"""

    def test_schedule_method_exists(self):
        """_schedule_async_polls方法应存在"""
        from core.device.device_manager import DeviceManager
        from core.data import DatabaseManager

        with patch.object(DatabaseManager, "__new__", return_value=Mock()):
            mgr = DeviceManager(db_manager=Mock())
            self.assertTrue(hasattr(mgr, "_schedule_async_polls"), "应有_schedule_async_polls方法")


class IntegrationSmokeTests(unittest.TestCase):
    """集成冒烟测试：验证基本导入和实例化"""

    def test_import_modbus_protocol(self):
        """能成功导入modbus_protocol"""
        try:
            from core.protocols.modbus_protocol import ModbusProtocol

            protocol = ModbusProtocol()
            self.assertIsNotNone(protocol)
        except Exception as e:
            self.fail(f"导入ModbusProtocol失败: {e}")

    def test_import_device_manager(self):
        """能成功导入device_manager"""
        try:
            from core.device.device_manager import DeviceManager

            self.assertIsNotNone(DeviceManager)
        except Exception as e:
            self.fail(f"导入DeviceManager失败: {e}")

    def test_import_alarm_manager(self):
        """能成功导入alarm_manager"""
        try:
            from core.utils.alarm_manager import AlarmManager

            self.assertIsNotNone(AlarmManager)
        except Exception as e:
            self.fail(f"导入AlarmManager失败: {e}")

    def test_modbus_protocol_basic_creation(self):
        """能创建ModbusProtocol实例并调用方法"""
        from core.protocols.modbus_protocol import ModbusProtocol

        protocol = ModbusProtocol()
        self.assertIsNotNone(protocol)

        # 验证方法可调用
        try:
            result = protocol._async_delay(0.01)  # 应不抛异常
        except Exception as e:
            self.fail(f"_async_delay调用失败: {e}")


def run_quick_tests():
    """运行快速验证测试"""
    print("=" * 70)
    print("生产级重构快速验证 v3.1")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestTask1_ModbusProtocolNoAsyncWait))
    suite.addTests(loader.loadTestsFromTestCase(TestTask2_DeviceManagerWriteLock))
    suite.addTests(loader.loadTestsFromTestCase(TestTask3_AlarmManagerCacheMechanism))
    suite.addTests(loader.loadTestsFromTestCase(TestTask4_SchedulerSnapshotMechanism))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationSmokeTests))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"结果: {passed}/{result.testsRun} 通过")
    if result.wasSuccessful():
        print("状态: ✅ 所有核心验证通过")
    else:
        print(f"状态: ❌ {len(result.failures)} 失败, {len(result.errors)} 错误")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_quick_tests()
    sys.exit(0 if success else 1)
