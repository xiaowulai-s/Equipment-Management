# 类型提示规范

## 基本原则

### 1. 函数参数和返回值必须标注类型

```python
# ✅ 正确
def add_device(device_id: str, config: dict) -> bool:
    """添加设备"""
    pass

# ❌ 错误
def add_device(device_id, config):
    """添加设备"""
    pass
```

### 2. 使用 typing 模块的高级类型

```python
from typing import Dict, List, Optional, Union, Callable, Any

# 可选参数
def get_device(device_id: str) -> Optional[Device]:
    """获取设备，可能返回 None"""
    pass

# 联合类型
def parse_value(value: Union[int, float, str]) -> float:
    """解析数值"""
    pass

# 字典和列表
def get_devices() -> Dict[str, Device]:
    """获取所有设备"""
    pass

def get_device_ids() -> List[str]:
    """获取设备 ID 列表"""
    pass

# 回调函数
def set_callback(func: Callable[[str], bool]) -> None:
    """设置回调函数"""
    pass
```

### 3. 类属性类型标注

```python
class DeviceManager:
    """设备管理器"""

    _devices: Dict[str, Device]  # 设备字典
    _poll_interval: int  # 轮询间隔（毫秒）
    _initialized: bool  # 是否已初始化

    def __init__(self, config_file: str = "config.json"):
        self._config_file = config_file
        self._devices = {}
        self._poll_interval = 1000
        self._initialized = False
```

### 4. 泛型类型

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    """通用仓库类"""

    def get(self, id: str) -> Optional[T]:
        """获取对象"""
        pass

    def save(self, obj: T) -> bool:
        """保存对象"""
        pass
```

### 5. 协议和抽象类型

```python
from typing import Protocol

class Drawable(Protocol):
    """可绘制协议"""

    def draw(self) -> None:
        """绘制"""
        ...

def render(obj: Drawable) -> None:
    """渲染可绘制对象"""
    obj.draw()
```

## 特殊情况处理

### 1. 避免使用 Any

```python
# ❌ 尽量避免
def process(data: Any) -> Any:
    pass

# ✅ 使用 Union 或泛型
def process(data: Union[int, str, dict]) -> Union[int, str, dict]:
    pass
```

### 2. 自引用类型

```python
from __future__ import annotations

class Node:
    """树节点"""

    def __init__(self, value: int):
        self.value = value
        self.children: List[Node] = []
```

### 3. 装饰器类型

```python
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec('P')
R = TypeVar('R')

def logged(func: Callable[P, R]) -> Callable[P, R]:
    """日志装饰器"""
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.info(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

## 文档字符串规范

### 1. Google 风格

```python
def add_device(
    device_id: str,
    config: Dict[str, Any],
    validate: bool = True
) -> bool:
    """
    添加设备到管理系统

    Args:
        device_id: 设备唯一标识符
        config: 设备配置字典，包含设备名称、类型、通信参数等
        validate: 是否验证配置有效性，默认为 True

    Returns:
        bool: 添加成功返回 True，失败返回 False

    Raises:
        ValueError: 当设备 ID 已存在或配置无效时
        DeviceError: 当设备创建失败时

    Example:
        >>> manager = DeviceManager()
        >>> manager.add_device("device_001", {"name": "泵 A"})
        True
    """
    pass
```

### 2. 类文档字符串

```python
class DeviceManager(QObject):
    """
    设备管理器

    负责管理所有设备的生命周期，包括：
    - 设备添加和删除
    - 设备连接和断开
    - 设备数据轮询
    - 设备状态监控

    Attributes:
        _devices: 设备字典，键为设备 ID，值为 Device 对象
        _poll_timer: 轮询定时器
        _poll_interval: 轮询间隔（毫秒）

    Signals:
        device_added: 设备添加时触发，参数为设备 ID
        device_removed: 设备删除时触发，参数为设备 ID
        device_connected: 设备连接时触发，参数为设备 ID
        device_disconnected: 设备断开时触发，参数为设备 ID
        device_data_updated: 设备数据更新时触发，参数为设备 ID 和数据字典
        device_error: 设备发生错误时触发，参数为设备 ID 和错误信息
    """

    device_added = Signal(str)
    device_removed = Signal(str)
    # ...
```

## 检查清单

提交代码前检查：

- [ ] 所有函数参数都有类型提示
- [ ] 所有函数返回值都有类型提示
- [ ] 所有类属性都有类型标注
- [ ] 使用了适当的 typing 模块类型
- [ ] 避免了 Any 类型的使用
- [ ] 文档字符串完整（包含 Args、Returns、Raises）
- [ ] 复杂类型有清晰的注释说明

## 工具配置

### mypy 配置

已在 `pyproject.toml` 中配置：

```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # 暂不强制
check_untyped_defs = true
ignore_missing_imports = true
```

### 运行类型检查

```bash
# 安装 mypy
pip install mypy

# 运行检查
mypy core/
mypy ui/

# 生成 HTML 报告
mypy --html-report mypy_report core/ ui/
```

## 渐进式迁移

由于项目已有代码较多，采用渐进式迁移：

1. **阶段 1**：新代码必须包含完整类型提示
2. **阶段 2**：修改旧代码时补充类型提示
3. **阶段 3**：逐步为所有代码添加类型提示
4. **阶段 4**：开启 mypy 严格检查
