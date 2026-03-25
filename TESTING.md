# 测试规范与流程

## 测试目录结构

```
tests/
├── __init__.py
├── run_tests.py              # 测试运行脚本
├── profile.py                # 性能分析脚本
├── test_core/                # 核心层测试
│   ├── __init__.py
│   ├── test_logger.py        # 日志系统测试
│   ├── test_theme_manager.py # 主题管理器测试
│   ├── test_theme_preference.py # 主题偏好测试
│   ├── test_serial_utils.py  # 串口工具测试
│   ├── test_device.py        # 设备管理测试
│   ├── test_alarm.py         # 报警系统测试
│   └── test_modbus_protocol.py # Modbus 协议测试
├── test_ui/                  # UI 层测试
│   ├── __init__.py
│   └── test_theme_buttons.py # 主题按钮测试
├── integration/              # 集成测试
│   ├── __init__.py
│   └── test_integration.py   # 端到端集成测试
└── performance/              # 性能测试
    ├── __init__.py
    └── test_performance.py   # 性能基准测试
```

## 测试运行

### 本地运行

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_core/ -v
python -m pytest tests/test_ui/ -v

# 运行集成测试
python -m pytest tests/integration/ -v

# 运行性能测试
python -m pytest tests/performance/ -v -s

# 生成覆盖率报告
python -m pytest tests/ --cov=core --cov=ui --cov-report=html

# 查看覆盖率报告
# 打开 htmlcov/index.html
```

### 使用测试脚本

```bash
# 运行所有测试（含覆盖率）
python tests/run_tests.py

# 简单运行测试（无覆盖率）
python tests/run_tests.py --simple
```

## 测试门禁

### 提交前检查

在提交代码前，必须通过以下检查：

```bash
# 1. 运行所有测试
python -m pytest tests/ -v

# 2. 检查代码格式
python -m black --check core/ ui/
python -m isort --check-only core/ ui/
python -m flake8 core/ ui/

# 3. 检查类型提示
python -m mypy core/ ui/
```

### CI/CD 门禁

GitHub Actions 会自动运行以下检查：

1. **单元测试** - 所有测试必须通过
2. **代码覆盖率** - 覆盖率不得低于 80%
3. **代码格式** - 符合 Black/isort/flake8 规范
4. **多版本测试** - Python 3.9-3.12 兼容性测试

## 测试编写规范

### 测试文件命名

- 测试文件必须以 `test_` 开头
- 测试类必须以 `Test` 开头
- 测试函数必须以 `test_` 开头

### 测试结构

```python
# -*- coding: utf-8 -*-
"""
模块测试
Module Tests
"""

import pytest
from module import ClassName


class TestClassName:
    """类测试"""

    @pytest.fixture
    def instance(self):
        """创建实例"""
        return ClassName()

    def test_method(self, instance):
        """测试方法"""
        assert instance.method() == expected
```

### 断言规范

- 使用 `assert` 语句进行断言
- 断言消息应清晰描述预期结果
- 优先使用具体的断言方法（如 `assert_equal`, `assert_true`）

### 测试夹具

- 使用 `@pytest.fixture` 创建测试夹具
- 合理使用 `scope` 参数（function, class, module, session）
- 使用 `tmp_path` 创建临时文件和目录

## 性能测试

### 性能基准

- **设备添加**: 100 个设备 < 10 秒
- **设备查询**: 100 次查询 < 5 秒
- **报警检查**: 1000 次检查 < 5 秒
- **批量操作**: 200 个设备 < 20 秒
- **内存使用**: 峰值 < 100MB

### 性能分析

```bash
# 运行性能分析
python tests/profile.py

# 查看性能报告
# 输出将显示最耗时的 20 个函数
```

## 覆盖率目标

- **核心模块**: 90%+
- **UI 模块**: 80%+
- **总体覆盖率**: 85%+

## 持续集成

### GitHub Actions 配置

项目使用 GitHub Actions 进行持续集成：

- **触发条件**: push 到 main/develop 分支，pull request
- **测试矩阵**: Python 3.9, 3.10, 3.11, 3.12
- **报告上传**: 测试结果和覆盖率报告自动上传

### 本地预检查

在推送到远程仓库前，建议运行：

```bash
# 安装 pre-commit
pip install pre-commit
pre-commit install

# 手动运行所有检查
pre-commit run --all-files
```

## 测试维护

### 定期审查

- 每月审查一次测试用例
- 删除过时或冗余的测试
- 更新测试以适配新的 API

### 测试数据

- 使用临时文件和目录
- 避免依赖外部资源
- 模拟网络请求和硬件设备

### Mock 和 Stub

对于依赖外部资源（数据库、网络、硬件）的测试，应使用 Mock：

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_object = Mock()
    mock_object.method.return_value = expected_value

    with patch('module.Class', mock_object):
        # 测试代码
        pass
```

## 故障排查

### 常见问题

1. **导入错误**: 确保测试路径正确，使用绝对导入
2. **Qt 应用实例**: UI 测试需要 QApplication 实例
3. **数据库锁定**: 使用临时数据库文件，测试后清理
4. **串口不可用**: 使用 Mock 模拟串口，不依赖真实硬件

### 调试技巧

```bash
# 运行单个测试
python -m pytest tests/test_module.py::TestClass::test_method -v

# 显示打印信息
python -m pytest tests/ -v -s

# 遇到错误停止
python -m pytest tests/ -x

# 显示局部变量
python -m pytest tests/ -l
```

---

**最后更新**: 2026-03-25
**维护者**: 开发团队
