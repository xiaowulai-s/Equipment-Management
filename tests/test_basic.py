# -*- coding: utf-8 -*-
"""
基础单元测试框架 (Basic Unit Test Framework)

提供项目的基础测试工具和示例测试用例。

运行方式:
    python -m pytest tests/ -v

或运行单个测试文件:
    python -m pytest tests/test_design_tokens.py -v
"""

from __future__ import annotations

import sys
import os
import unittest
from pathlib import Path


# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestDesignTokens(unittest.TestCase):
    """DesignTokens 系统单元测试"""

    def test_colors_exist(self):
        """测试颜色常量是否存在"""
        from ui.design_tokens import Colors

        self.assertTrue(hasattr(Colors, "TEXT_PRIMARY"))
        self.assertTrue(hasattr(Colors, "ACCENT_PRIMARY"))
        self.assertTrue(hasattr(Colors, "STATUS_ERROR"))

    def test_colors_format(self):
        """测试颜色值格式是否正确"""
        from ui.design_tokens import Colors

        # 应该是有效的十六进制颜色
        color = Colors.TEXT_PRIMARY
        self.assertTrue(color.startswith("#"))
        self.assertTrue(len(color) == 7)

    def test_typography_exists(self):
        """测试字体样式是否存在"""
        from ui.design_tokens import Typography

        self.assertTrue(hasattr(Typography, "BODY"))
        self.assertTrue(hasattr(Typography, "TITLE_MEDIUM"))
        self.assertTrue(len(Typography.BODY) == 3)  # (name, size, weight)

    def test_spacing_values(self):
        """测试间距值是否为正整数"""
        from ui.design_tokens import Spacing

        self.assertGreater(Spacing.XS, 0)
        self.assertGreater(Spacing.SM, 0)
        self.assertLessEqual(Spacing.XS, Spacing.SM)
        self.assertLessEqual(Spacing.SM, Spacing.MD)

    def test_radius_values(self):
        """测试圆角值是否合理"""
        from ui.design_tokens import Radius

        self.assertEqual(Radius.NONE, 0)
        self.assertGreater(Radius.FULL, 100)

    def test_dt_alias(self):
        """测试便捷别名DT"""
        from ui.design_tokens import DT, Colors, Typography, Spacing, Radius

        self.assertEqual(DT.C, Colors)
        self.assertEqual(DT.T, Typography)
        self.assertEqual(DT.S, Spacing)
        self.assertEqual(DT.R, Radius)

    def test_adjust_color(self):
        """测试颜色调整功能"""
        from ui.design_tokens import Colors

        result = Colors.adjust_color("#FF0000", -50)
        self.assertTrue(result.startswith("#"))


class TestAsyncUtils(unittest.TestCase):
    """异步工具集单元测试"""

    def test_async_utils_import(self):
        """测试异步工具是否可导入"""
        try:
            from ui.async_utils import async_sleep, async_wait, run_async

            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"无法导入async_utils: {e}")


class TestAnimationScheduler(unittest.TestCase):
    """动画调度器单元测试"""

    def test_scheduler_singleton(self):
        """测试单例模式"""
        from ui.animation_scheduler import AnimationScheduler

        inst1 = AnimationScheduler.get_instance()
        inst2 = AnimationScheduler.get_instance()

        self.assertIs(inst1, inst2)

    def test_scheduler_initial_state(self):
        """测试初始状态"""
        from ui.animation_scheduler import AnimationScheduler

        scheduler = AnimationScheduler.get_instance()

        self.assertFalse(scheduler.is_running)
        self.assertEqual(scheduler.active_count, 0)


class TestWindowManagers(unittest.TestCase):
    """窗口管理器单元测试"""

    def test_base_manager_exists(self):
        """测试基础管理器类是否存在"""
        from ui.window_managers import BaseWindowManager

        self.assertTrue(BaseWindowManager is not None)

    def test_ui_manager_exists(self):
        """测试UI管理器是否存在"""
        from ui.window_managers import UIManager

        self.assertTrue(UIManager is not None)

    def test_device_list_manager_exists(self):
        """测试设备列表管理器是否存在"""
        from ui.window_managers import DeviceListManager

        self.assertTrue(DeviceListManager is not None)


class TestMigrationHelper(unittest.TestCase):
    """迁移助手单元测试"""

    def test_migrator_exists(self):
        """测试迁移器是否存在"""
        from ui.migration_helper import TokenMigrator

        self.assertTrue(TokenMigrator is not None)

    def test_migrator_analyze_file(self):
        """测试文件分析功能"""
        from ui.migration_helper import TokenMigrator

        migrator = TokenMigrator()
        result = migrator.analyze_file("ui/design_tokens.py")

        self.assertIn("file", result)
        self.assertIn("total_issues", result)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
