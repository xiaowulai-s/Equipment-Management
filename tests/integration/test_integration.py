# -*- coding: utf-8 -*-
"""
集成测试
Integration Tests
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication

from core.data.models import AlarmRuleModel, DatabaseManager, DeviceModel
from core.device.device_manager import DeviceManager
from core.utils.alarm_manager import AlarmManager


@pytest.fixture(scope="module")
def app():
    """创建 QApplication 实例"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(scope="module")
def db_manager():
    """创建数据库管理器实例"""
    db = DatabaseManager()
    # DatabaseManager 在__init__中自动初始化
    yield db
    # 清理测试数据
    db.close()


@pytest.fixture(scope="module")
def device_manager(db_manager):
    """创建设备管理器实例"""
    return DeviceManager(db_manager)


@pytest.fixture(scope="module")
def alarm_manager(db_manager):
    """创建报警管理器实例"""
    return AlarmManager(db_manager)


class TestDeviceIntegration:
    """设备集成测试类"""

    def test_add_device_to_database(self, device_manager, db_manager):
        """测试添加设备到数据库"""
        device = DeviceModel(
            name="IntegrationTestDevice",
            device_type="PLC",
            protocol="modbus_tcp",
            ip="192.168.1.100",
            port=502,
            slave_id=1,
        )

        # 添加设备
        success = device_manager.add_device(device)
        assert success is True

        # 验证设备在数据库中
        devices = device_manager.list_devices()
        assert len(devices) > 0

        # 清理
        device_manager.remove_device(device.id)

    def test_device_crud_operations(self, device_manager):
        """测试设备的增删改查操作"""
        # Create
        device = DeviceModel(
            name="CRUDTestDevice", device_type="Sensor", protocol="modbus_tcp", ip="192.168.1.101", port=502, slave_id=2
        )

        success = device_manager.add_device(device)
        assert success is True

        # Read
        retrieved = device_manager.get_device(device.id)
        assert retrieved is not None
        assert retrieved.name == "CRUDTestDevice"

        # Update
        retrieved.name = "UpdatedCRUDTestDevice"
        success = device_manager.update_device(retrieved)
        assert success is True

        # Verify update
        updated = device_manager.get_device(device.id)
        assert updated.name == "UpdatedCRUDTestDevice"

        # Delete
        success = device_manager.remove_device(device.id)
        assert success is True

        # Verify delete
        deleted = device_manager.get_device(device.id)
        assert deleted is None


class TestAlarmIntegration:
    """报警系统集成测试类"""

    def test_alarm_rule_persistence(self, alarm_manager, db_manager):
        """测试报警规则的持久化"""
        rule = AlarmRuleModel(
            device_id="test_device_1",
            register_address=40001,
            condition="greater_than",
            threshold=100,
            alarm_type="high_limit",
            enabled=True,
        )

        # 添加报警规则
        success = alarm_manager.add_alarm_rule(rule)
        assert success is True

        # 验证规则已保存
        rules = alarm_manager.get_alarm_rules("test_device_1")
        assert len(rules) > 0

        # 清理
        alarm_manager.remove_alarm_rule(rule.id)

    def test_alarm_trigger_workflow(self, alarm_manager):
        """测试报警触发工作流程"""
        # 创建报警规则
        rule = AlarmRuleModel(
            device_id="test_device_2",
            register_address=40002,
            condition="greater_than",
            threshold=50,
            alarm_type="high_limit",
            enabled=True,
        )

        alarm_manager.add_alarm_rule(rule)

        # 测试触发报警
        triggered = alarm_manager.check_alarm("test_device_2", 40002, 75)
        assert triggered is True

        # 测试不触发报警
        not_triggered = alarm_manager.check_alarm("test_device_2", 40002, 25)
        assert not_triggered is False

        # 清理
        alarm_manager.remove_alarm_rule(rule.id)


class TestEndToEnd:
    """端到端集成测试类"""

    def test_full_device_workflow(self, device_manager, alarm_manager):
        """测试完整的设备工作流程"""
        # 1. 添加设备
        device = DeviceModel(
            name="E2E_Device", device_type="PLC", protocol="modbus_tcp", ip="192.168.1.200", port=502, slave_id=10
        )

        success = device_manager.add_device(device)
        assert success is True

        # 2. 为设备添加报警规则
        rule = AlarmRuleModel(
            device_id=device.id,
            register_address=40001,
            condition="greater_than",
            threshold=80,
            alarm_type="high_limit",
            enabled=True,
        )

        success = alarm_manager.add_alarm_rule(rule)
        assert success is True

        # 3. 验证设备和报警规则都存在
        devices = device_manager.list_devices()
        assert any(d.id == device.id for d in devices)

        rules = alarm_manager.get_alarm_rules(device.id)
        assert len(rules) > 0

        # 4. 测试报警触发
        triggered = alarm_manager.check_alarm(device.id, 40001, 90)
        assert triggered is True

        # 5. 禁用报警规则
        alarm_manager.disable_alarm_rule(rule.id)
        rules = alarm_manager.get_alarm_rules(device.id)
        assert len(rules) == 1
        assert rules[0].enabled is False

        # 6. 清理
        alarm_manager.remove_alarm_rule(rule.id)
        device_manager.remove_device(device.id)

        # 7. 验证清理完成
        assert device_manager.get_device(device.id) is None
        assert len(alarm_manager.get_alarm_rules(device.id)) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
