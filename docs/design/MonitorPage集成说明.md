# -*- coding: utf-8 -*-
"""
MonitorPage集成到MainWindow的示例说明

本文件说明了如何将MonitorPage组件集成到现有的MainWindow中。
"""

## 概述

MonitorPage是一个独立的监控页面组件，包含：
- 实时数据选项卡（数据卡片 + 仪表盘）
- 历史趋势选项卡（趋势图）

## 集成步骤

### 1. 在MainWindow中导入MonitorPage

在 `ui/main_window.py` 顶部添加导入：

```python
from ui.monitor_page import MonitorPage
```

### 2. 在MainWindow.__init__中初始化MonitorPage

在MainWindow的初始化方法中，创建MonitorPage实例：

```python
class MainWindow(QMainWindow):
    def __init__(self, device_manager: DeviceManager, alarm_manager: AlarmManager, ...):
        super().__init__()

        # ... 其他初始化代码 ...

        # 创建MonitorPage实例
        self._monitor_page = MonitorPage()

        # 连接信号：点击卡片/仪表盘/趋势图时跳转到寄存器详情
        self._monitor_page.register_clicked.connect(self._on_register_clicked)
```

### 3. 在设备选择变化时更新MonitorPage

在MainWindow的设备选择处理方法中，更新MonitorPage的当前设备：

```python
def _on_device_selected(self, device_id: str):
    """当用户选择设备时"""
    device = self._device_manager.get_device(device_id)
    if device:
        self._monitor_page.set_device(device)
        self._monitor_page.start_updates()
```

### 4. 在设备连接/断开时更新MonitorPage

在设备连接/断开的信号处理中，更新MonitorPage的显示：

```python
def _on_device_connected(self, device: Device):
    """当设备连接时"""
    self._monitor_page.set_device(device)
    self._monitor_page.start_updates()

def _on_device_disconnected(self, device_id: str):
    """当设备断开时"""
    self._monitor_page.set_device(None)
    self._monitor_page.stop_updates()
```

### 5. 在实时数据更新时刷新MonitorPage

在MainWindow接收到设备数据更新信号时，刷新MonitorPage：

```python
def _on_device_data_updated(self, device_id: str):
    """当设备数据更新时"""
    if self._monitor_page._current_device and self._monitor_page._current_device.device_id == device_id:
        self._monitor_page.update_data()
```

### 6. 将MonitorPage添加到UI布局中

在MainWindow的UI构建方法中，将MonitorPage添加到stacked widget：

```python
def _init_ui(self):
    """初始化UI"""
    # ... 其他UI构建代码 ...

    # 创建stacked widget用于页面切换
    self._stacked_widget = QStackedWidget()

    # 添加各种页面
    from ui.welcome_page import WelcomePage
    self._welcome_page = WelcomePage()
    self._stacked_widget.addWidget(self._welcome_page)

    # 添加MonitorPage
    self._stacked_widget.addWidget(self._monitor_page)

    # ... 其他页面 ...

    # 设置中央widget
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    layout.addWidget(self._stacked_widget)
    self.setCentralWidget(central_widget)
```

### 7. 实现点击卡片/仪表盘/趋势图的回调

实现 `_on_register_clicked` 方法，处理点击事件：

```python
def _on_register_clicked(self, device_id: str, register_address: int):
    """当用户点击寄存器卡片/仪表盘/趋势图时"""
    # 1. 找到对应的设备和寄存器
    device = self._device_manager.get_device(device_id)
    if not device:
        return

    register = None
    for reg in device.registers.values():
        if reg.address == register_address:
            register = reg
            break

    if not register:
        return

    # 2. 打开寄存器详情对话框
    from ui.register_details_dialog import RegisterDetailsDialog

    dialog = RegisterDetailsDialog(device, register, parent=self)
    dialog.exec()
```

## 注意事项

1. **线程安全**: MonitorPage的 `update_data()` 方法应该在主线程中调用
2. **性能**: 如果设备数量较多，考虑减少刷新频率（默认1秒）
3. **内存**: TrendChart保留60秒的数据，可以根据需要调整
4. **报警状态**: MonitorPage根据 `alarm_config` 自动更新组件的状态颜色

## 测试清单

- [ ] 选择设备时MonitorPage正确显示该设备的数据
- [ ] 实时数据正确更新（每1秒）
- [ ] 报警状态正确显示（正常/警告/错误）
- [ ] 点击卡片/仪表盘/趋势图能打开寄存器详情
- [ ] 设备断开时MonitorPage正确清空
- [ ] 设备重新连接时MonitorPage正确恢复显示
- [ ] 历史趋势图正确显示最近60秒的数据

## 未来改进

1. **自定义布局**: 允许用户自定义组件的位置和大小
2. **主题切换**: 支持深色/浅色主题切换
3. **数据导出**: 支持导出实时数据和历史趋势
4. **数据回放**: 支持历史数据回放功能
5. **多设备同时监控**: 支持同时监控多个设备
