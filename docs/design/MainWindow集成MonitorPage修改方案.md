# MainWindow 集成 MonitorPage 修改方案

## 概述
将 `ui/monitor_page.py` 中的 MonitorPage 组件集成到 `ui/main_window.py` 的 MainWindow 中。

## 修改步骤

### 步骤1: 添加导入
在 `ui/main_window.py` 顶部添加导入：

```python
# 在现有导入之后添加:
from ui.monitor_page import MonitorPage
```

### 步骤2: 在 `__init__` 中初始化 MonitorPage
在 `MainWindow.__init__` 方法中，创建 MonitorPage 实例：

```python
class MainWindow(QMainWindow):
    def __init__(self, device_manager: DeviceManager, alarm_manager: AlarmManager, ...):
        super().__init__()

        # ... 现有的初始化代码 ...

        # 创建 MonitorPage 实例
        self._monitor_page = MonitorPage()

        # 连接信号：点击卡片/仪表盘/趋势图时跳转到寄存器详情
        self._monitor_page.register_clicked.connect(self._on_register_clicked)
```

### 步骤3: 修改 `_init_ui` 方法
将 `_create_monitor_page()` 方法改为直接使用 MonitorPage：

```python
def _init_ui(self) -> None:
    """初始化UI"""
    self.setWindowTitle(TextConstants.WINDOW_TITLE)
    self.setMinimumSize(1600, 900)

    self._create_menu_bar()

    central_widget = QWidget()
    self.setCentralWidget(central_widget)

    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)

    splitter = QSplitter(Qt.Orientation.Horizontal)

    # 左侧面板：设备列表
    left_widget = self._create_left_panel()
    splitter.addWidget(left_widget)

    # 右侧面板：使用 MonitorPage
    self._stacked_widget = QStackedWidget()
    self._stacked_widget.setStyleSheet(AppStyles.STACKED_WIDGET)

    # 添加欢迎页面
    welcome_page = self._create_welcome_page()
    self._stacked_widget.addWidget(welcome_page)

    # 添加 MonitorPage（替换原来的 monitor_page）
    self._stacked_widget.addWidget(self._monitor_page)

    splitter.addWidget(self._stacked_widget)

    splitter.setStretchFactor(0, 20)
    splitter.setStretchFactor(1, 80)
    splitter.setSizes([400, 1200])
    splitter.setStyleSheet(AppStyles.SPLITTER)

    main_layout.addWidget(splitter)

    self._create_status_bar()
```

### 步骤4: 删除或注释原来的 `_create_monitor_page` 方法
原来的 `_create_monitor_page()` 方法已经不需要了，可以删除或注释掉：

```python
# 删除或注释这个方法
# def _create_monitor_page(self) -> QWidget:
#     ...
```

### 步骤5: 更新 `_on_device_selected` 方法
在设备选择变化时更新 MonitorPage：

```python
def _on_device_selected(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
    """处理设备选择"""
    if not current:
        self._stacked_widget.setCurrentIndex(0)  # 显示欢迎页面
        return

    device_id = current.data(0, Qt.ItemDataRole.UserRole)
    self._current_device_id = device_id

    # 获取设备对象
    device = self._device_manager.get_device(device_id)
    if device:
        # 更新 MonitorPage
        self._monitor_page.set_device(device)
        self._monitor_page.start_updates()

        # 切换到监控页面
        self._stacked_widget.setCurrentIndex(1)
    else:
        self._stacked_widget.setCurrentIndex(0)
```

### 步骤6: 更新设备连接/断开的信号处理
在设备连接/断开时更新 MonitorPage：

```python
@Slot(str)
def _on_device_connected(self, device_id: str) -> None:
    """处理设备连接"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    # 如果当前正在显示这个设备，更新 MonitorPage
    if self._current_device_id == device_id:
        device = self._device_manager.get_device(device_id)
        if device:
            self._monitor_page.set_device(device)
            self._monitor_page.start_updates()

    logger.info(LogMessages.DEVICE_CONNECTED.format(device_id=device_id))

@Slot(str)
def _on_device_disconnected(self, device_id: str) -> None:
    """处理设备断开"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    # 如果当前正在显示这个设备，清空 MonitorPage
    if self._current_device_id == device_id:
        self._monitor_page.set_device(None)
        self._monitor_page.stop_updates()

    logger.info(LogMessages.DEVICE_DISCONNECTED.format(device_id=device_id))
```

### 步骤7: 添加 `_on_register_clicked` 方法
处理点击卡片/仪表盘/趋势图的事件：

```python
@Slot(str, int)
def _on_register_clicked(self, device_id: str, register_address: int) -> None:
    """处理点击寄存器卡片/仪表盘/趋势图"""
    # 1. 获取设备和寄存器对象
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
    from ui.register_config_dialog import RegisterConfigDialog

    dialog = RegisterConfigDialog(
        device=device,
        register=register,
        alarm_manager=self._alarm_manager,
        parent=self
    )

    if dialog.exec():
        # 对话框关闭后，刷新 MonitorPage
        self._monitor_page.set_device(device)
```

### 步骤8: 在设备移除时处理
```python
@Slot(str)
def _on_device_removed(self, device_id: str) -> None:
    """处理设备移除"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    # 如果当前正在显示这个设备，切换回欢迎页面
    if self._current_device_id == device_id:
        self._stacked_widget.setCurrentIndex(0)
        self._monitor_page.set_device(None)
        self._monitor_page.stop_updates()
        self._current_device_id = None

    logger.info(LogMessages.DEVICE_REMOVED.format(device_id=device_id))
```

## 修改总结

| 修改项 | 说明 |
|--------|------|
| **添加导入** | `from ui.monitor_page import MonitorPage` |
| **初始化实例** | 在 `__init__` 中创建 `self._monitor_page` |
| **连接信号** | `register_clicked` 信号连接到 `_on_register_clicked` |
| **修改 UI 构建方法** | 将 `_create_monitor_page()` 改为直接使用 MonitorPage |
| **更新设备选择** | 在 `_on_device_selected` 中调用 `set_device()` 和 `start_updates()` |
| **更新连接/断开** | 在相应方法中更新 MonitorPage |
| **添加回调** | 实现 `_on_register_clicked` 方法处理点击事件 |
| **处理设备移除** | 在设备移除时清空 MonitorPage |

## 测试检查清单

- [ ] 启动应用，设备列表正常显示
- [ ] 选择设备时，MonitorPage 正确显示该设备的数据
- [ ] 实时数据每秒更新（卡片、仪表盘、趋势图）
- [ ] 报警状态正确显示（正常/警告/错误）
- [ ] 点击卡片/仪表盘/趋势图能打开寄存器详情对话框
- [ ] 设备断开时，MonitorPage 显示欢迎界面
- [ ] 设备重新连接时，MonitorPage 恢复显示
- [ ] 设备移除时，切换回欢迎页面
- [ ] 历史趋势图显示最近60秒的数据
- [ ] 关闭应用时，MonitorPage 正确停止更新

## 注意事项

1. **线程安全**：MonitorPage 的 `update_data()` 方法在主线程中调用，确保设备数据更新也在主线程或通过信号传递
2. **内存管理**：切换设备时，MonitorPage 会自动清空旧组件，不需要手动管理内存
3. **性能**：如果设备数量较多或寄存器很多，考虑减少刷新频率
4. **错误处理**：在 `_on_register_clicked` 中添加错误处理，防止设备或寄存器不存在时崩溃
