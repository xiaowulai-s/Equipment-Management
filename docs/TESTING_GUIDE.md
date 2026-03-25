# 测试指南

## 测试环境配置

### 安装测试依赖

```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock
```

### 测试目录结构

```
tests/
├── __init__.py
├── test_core/           # 核心模块测试
│   ├── __init__.py
│   ├── test_logger.py   # 日志系统测试
│   ├── test_device.py   # 设备管理测试
│   ├── test_protocol.py # 协议层测试
│   └── test_comm.py     # 通信层测试
├── test_ui/             # UI 模块测试
│   ├── __init__.py
│   ├── test_main_window.py
│   └── test_dialogs.py
└── conftest.py          # pytest 配置和共享 fixtures
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行特定模块测试

```bash
# 运行核心模块测试
pytest tests/test_core/

# 运行日志系统测试
pytest tests/test_core/test_logger.py

# 运行 UI 模块测试
pytest tests/test_ui/
```

### 运行特定测试

```bash
# 运行特定测试类
pytest tests/test_core/test_logger.py::TestLogger

# 运行特定测试方法
pytest tests/test_core/test_logger.py::TestLogger::test_get_logger
```

### 生成覆盖率报告

```bash
# 生成 HTML 报告
pytest --cov=core --cov=ui --cov-report=html

# 生成终端报告
pytest --cov=core --cov=ui --cov-report=term-missing

# 同时生成两种报告
pytest --cov=core --cov=ui --cov-report=html --cov-report=term-missing
```

### 详细输出

```bash
# 详细输出
pytest -v

# 显示局部变量
pytest -l

# 显示打印输出
pytest -s
```

## 编写测试

### 测试文件命名

- 文件名：`test_*.py`
- 测试类：`Test*`
- 测试函数：`test_*`

### 测试示例

```python
# -*- coding: utf-8 -*-
"""
设备管理器测试
"""

import pytest
from core.device.device_manager import DeviceManager
from core.device.device_model import DeviceStatus


class TestDeviceManager:
    """设备管理器测试类"""

    @pytest.fixture
    def manager(self):
        """测试夹具：创建设备管理器"""
        return DeviceManager("test_config.json")

    def test_add_device(self, manager):
        """测试添加设备"""
        config = {
            "name": "测试设备",
            "type": "pump",
            "protocol": "modbus_tcp",
            "ip": "127.0.0.1",
            "port": 502
        }

        device_id = manager.add_device(config)
        assert device_id is not None
        assert device_id in manager.get_all_devices()

    def test_remove_device(self, manager):
        """测试删除设备"""
        config = {
            "name": "测试设备",
            "type": "pump",
        }

        device_id = manager.add_device(config)
        assert manager.remove_device(device_id) is True
        assert device_id not in manager.get_all_devices()

    def test_connect_device(self, manager):
        """测试连接设备（仿真模式）"""
        config = {
            "name": "测试设备",
            "type": "pump",
            "simulation": True  # 启用仿真
        }

        device_id = manager.add_device(config)
        assert manager.connect_device(device_id) is True

        # 验证设备状态
        device = manager.get_device(device_id)
        assert device.status == DeviceStatus.CONNECTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 使用夹具（Fixtures）

```python
# tests/conftest.py

import pytest
from core.device.device_manager import DeviceManager


@pytest.fixture
def device_manager():
    """创建设备管理器实例"""
    return DeviceManager("test_config.json")


@pytest.fixture
def sample_device_config():
    """示例设备配置"""
    return {
        "device_id": "test_001",
        "name": "测试设备",
        "type": "pump",
        "protocol": "modbus_tcp",
        "ip": "127.0.0.1",
        "port": 502,
        "simulation": True
    }


@pytest.fixture
def connected_device(device_manager, sample_device_config):
    """已连接的设备"""
    device_id = device_manager.add_device(sample_device_config)
    device_manager.connect_device(device_id)
    return device_manager.get_device(device_id)
```

### 参数化测试

```python
import pytest


@pytest.mark.parametrize("protocol,expected", [
    ("modbus_tcp", True),
    ("modbus_rtu", True),
    ("modbus_ascii", True),
    ("invalid", False),
])
def test_protocol_validation(protocol, expected):
    """测试协议验证"""
    config = {
        "name": "测试设备",
        "protocol": protocol,
    }

    result = validate_protocol(config)
    assert result == expected
```

## 持续集成

### GitHub Actions 配置

```yaml
# .github/workflows/tests.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest --cov=core --cov=ui --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

## 测试最佳实践

### ✅ 推荐

- 测试应该独立，不依赖其他测试
- 使用夹具复用测试代码
- 测试名称应该清晰描述测试内容
- 使用参数化测试减少重复代码
- 测试应该覆盖正常情况和异常情况

### ❌ 避免

- 测试之间相互依赖
- 硬编码测试数据
- 测试过于复杂
- 只测试正常流程，不测试异常流程
- 测试包含断言以外的逻辑

## 覆盖率目标

- **总体覆盖率**: ≥ 80%
- **核心模块覆盖率**: ≥ 85%
- **UI 模块覆盖率**: ≥ 70%

## 测试检查清单

提交代码前：

- [ ] 为新功能编写了测试
- [ ] 所有测试通过
- [ ] 代码覆盖率满足要求
- [ ] 测试代码遵循规范
- [ ] 测试文档已更新
