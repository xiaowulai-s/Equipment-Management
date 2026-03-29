"""
pytest全局fixture

提供公共测试环境、临时数据库、模拟设备等。
"""

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """项目根目录路径"""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """测试用临时数据目录"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def test_db_path(tmp_path: Path) -> str:
    """测试用临时数据库路径"""
    db_path = tmp_path / "test_equipment.db"
    return str(db_path)


@pytest.fixture
def sample_device_config() -> dict:
    """示例设备配置"""
    return {
        "name": "测试泵站-01",
        "device_id": "PUMP-TEST-001",
        "device_type": "泵站控制器",
        "protocol": "modbus_tcp",
        "connection": {
            "host": "192.168.1.100",
            "port": 502,
            "timeout": 3.0,
        },
        "poll_interval": 1.0,
        "auto_reconnect": True,
    }
