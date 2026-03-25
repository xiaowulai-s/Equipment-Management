# -*- coding: utf-8 -*-
"""
重构测试脚本
Test script for refactored code
"""

import os
import shutil
import sys
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


def test_data_layer():
    """测试数据层"""
    print("=" * 50)
    print("测试数据层...")

    from core.data import DatabaseManager, DeviceRepository
    from core.data.models import DeviceModel, RegisterMapModel

    # 使用临时数据库
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_data.db")

    try:
        # 初始化数据库
        db = DatabaseManager(db_path)

        with db.session() as session:
            repo = DeviceRepository(session)

            # 创建设备
            config = {
                "device_id": "test001",
                "name": "测试设备",
                "device_type": "传感器",
                "protocol_type": "modbus_tcp",
                "host": "127.0.0.1",
                "port": 502,
                "register_map": [{"name": "温度", "address": 0, "data_type": "uint16", "scale": 0.1, "unit": "°C"}],
            }

            device = repo.create_from_config(config)
            print(f"[OK] 创建设备: {device.name} (ID: {device.id})")

            # 查询设备
            found = repo.get_with_registers("test001")
            assert found is not None, "设备查询失败"
            print(f"[OK] 查询设备成功，寄存器数量: {len(found.register_maps)}")

        print("[PASS] 数据层测试通过")
        return True

    finally:
        db.close()
        shutil.rmtree(temp_dir)


def test_config_models():
    """测试配置模型"""
    print("=" * 50)
    print("测试配置模型...")

    from core.config_models import DeviceConfig, RegisterMapConfig, SystemConfig

    # 创建设备配置
    device_config = DeviceConfig(
        name="测试设备",
        device_type="传感器",
        protocol_type="modbus_tcp",
        host="192.168.1.100",
        port=502,
        register_map=[RegisterMapConfig(name="温度", address=0, data_type="float32", unit="°C")],
    )

    print(f"[OK] 创建设备配置: {device_config.name}")

    # 验证配置
    assert device_config.name == "测试设备"
    assert len(device_config.register_map) == 1
    assert device_config.register_map[0].name == "温度"

    print("[PASS] 配置模型测试通过")
    return True


def test_logger():
    """测试日志系统"""
    print("=" * 50)
    print("测试日志系统...")

    from core.utils.logger_v2 import get_logger, setup_logging

    logger = setup_logging(log_level="DEBUG", log_file=None, db_manager=None, console_output=True)  # 不写入文件

    logger.info("测试日志消息", extra_field="test")
    print("[PASS] 日志系统工作正常")
    return True


def test_device_manager_v2():
    """测试设备管理器v2"""
    print("=" * 50)
    print("测试设备管理器 v2...")

    from core.data import DatabaseManager
    from core.device.device_manager_v2 import DeviceManagerV2, PollPriority

    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_dm.db")
    config_path = os.path.join(temp_dir, "config.json")

    try:
        # 创建Qt应用
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)

        db = DatabaseManager(db_path)

        dm = DeviceManagerV2(config_file=config_path, db_manager=db)

        print(f"[OK] 创建设备管理器")
        print(f"[OK] 轮询间隔: {dm._poll_interval}ms")
        print(f"[OK] 最大重连次数: {dm._max_reconnect_attempts}")

        dm.cleanup()
        print("[PASS] 设备管理器 v2 测试通过")
        return True

    finally:
        db.close()
        shutil.rmtree(temp_dir)


def test_alarm_repository():
    """测试报警仓库"""
    print("=" * 50)
    print("测试报警仓库...")

    from datetime import datetime, timedelta

    from core.data import AlarmRepository, DatabaseManager
    from core.data.models import AlarmModel

    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_alarm.db")

    db = None
    try:
        db = DatabaseManager(db_path)

        with db.session() as session:
            repo = AlarmRepository(session)

            # 创建报警
            alarm = repo.create_alarm(
                rule_id="TEMP_HIGH",
                device_id="dev001",
                device_name="测试设备",
                parameter="温度",
                alarm_type="threshold_high",
                level=1,
                value=85.5,
                threshold_high=80.0,
                description="温度过高报警",
            )

            print(f"[OK] 创建报警: ID={alarm.id}, 级别={alarm.level}")

            # 查询未确认报警
            unack = repo.get_unacknowledged()
            assert len(unack) == 1
            print(f"[OK] 查询未确认报警: {len(unack)} 条")

            # 确认报警
            repo.acknowledge_alarm(alarm.id, acknowledged_by="admin")
            print("[OK] 确认报警成功")

        print("[PASS] 报警仓库测试通过")
        return True

    finally:
        if db:
            db.close()
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("开始重构代码测试")
    print("=" * 50 + "\n")

    tests = [
        ("数据层", test_data_layer),
        ("配置模型", test_config_models),
        ("日志系统", test_logger),
        ("报警仓库", test_alarm_repository),
        ("设备管理器 v2", test_device_manager_v2),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name} 测试失败: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
