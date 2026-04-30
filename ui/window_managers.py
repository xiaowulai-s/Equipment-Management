# -*- coding: utf-8 -*-
"""
窗口管理器基类 (Window Manager Base Class)

提供统一的管理器接口规范。
"""

from __future__ import annotations
from typing import Optional, Any
from PySide6.QtWidgets import QWidget


class BaseWindowManager:
    """
    窗口管理器抽象基类

    所有专职管理器都应继承此类，确保接口一致性。

    职责:
    - 封装特定领域的UI创建和管理逻辑
    - 提供清晰的公共接口
    - 降低MainWindow的复杂度
    """

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._widgets: dict = {}
        self._initialized = False

    @property
    def parent(self) -> QWidget:
        """获取父窗口"""
        return self._parent

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized

    def create(self) -> Any:
        """
        创建UI组件

        Returns:
            Any: 创建的主控件或布局
        """
        raise NotImplementedError("子类必须实现 create() 方法")

    def cleanup(self) -> None:
        """清理资源"""
        self._widgets.clear()
        self._initialized = False

    def get_widget(self, name: str) -> Optional[QWidget]:
        """
        获取指定名称的控件

        Args:
            name: 控件名称

        Returns:
            Optional[QWidget]: 控件实例，不存在则返回 None
        """
        return self._widgets.get(name)

    def register_widget(self, name: str, widget: QWidget) -> None:
        """
        注册控件

        Args:
            name: 控件名称（唯一标识）
            widget: 控件实例
        """
        self._widgets[name] = widget

    def get_all_widgets(self) -> dict:
        """获取所有注册的控件"""
        return self._widgets.copy()

    def update_ui(self, data: dict = None) -> None:
        """
        更新UI显示

        Args:
            data: 更新数据（可选）
        """
        pass


class UIManager(BaseWindowManager):
    """
    UI创建管理器

    负责:
    - 菜单栏创建
    - 工具栏创建
    - 状态栏创建
    - 折叠按钮创建
    """

    def create(self):
        """创建所有基础UI组件"""
        self._create_collapse_buttons()
        self._initialized = True

    def _create_collapse_buttons(self):
        """创建折叠/展开按钮"""
        from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QLabel
        from ui.design_tokens import DT

        # 左侧折叠按钮
        self._collapse_btn = QPushButton("◀")
        self._collapse_btn.setObjectName("left_collapse_btn")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.setCursor(DT.C.CURSOR_POINTER)
        self.register_widget("collapse_btn", self._collapse_btn)

        # 右侧展开按钮
        self._expand_btn = QPushButton("▶")
        self._expand_btn.setObjectName("left_expand_btn")
        self._expand_btn.setFixedSize(24, 24)
        self._expand_btn.setCursor(DT.C.CURSOR_POINTER)
        self._expand_btn.hide()
        self.register_widget("expand_btn", self._expand_btn)


class DeviceListManager(BaseWindowManager):
    """
    设备列表管理器

    负责:
    - 设备树创建和管理
    - 设备选择处理
    - 设备状态显示
    """

    def create(self):
        """创建设备列表组件"""
        from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView
        from ui.design_tokens import DT

        # 设备树
        self._device_tree = QTreeWidget()
        self._device_tree.setHeaderLabels(["设备列表"])
        self._device_tree.header().setStretchLastSection(True)
        self._device_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._device_tree.setColumnWidth(0, 200)
        self._device_tree.setMinimumWidth(180)
        self._device_tree.setMaximumWidth(350)

        self.register_widget("device_tree", self._device_tree)
        self._initialized = True
        return self._device_tree

    def add_device(self, device_id: str, name: str, port: str):
        """添加设备到列表"""
        from PySide6.QtWidgets import QTreeWidgetItem

        item = QTreeWidgetItem(self._device_tree)
        item.setText(0, f"{name} ({port})")
        item.setData(0, 1, device_id)  # 存储device_id
        return item

    def clear_devices(self):
        """清空设备列表"""
        self._device_tree.clear()


class MonitorManager(BaseWindowManager):
    """
    监控页面管理器

    负责:
    - 监控页面协调
    - 数据卡片更新
    - 图表数据更新
    - 寄存器表格更新
    """

    def create(self):
        """创建监控页面（通过Controller）"""
        self._initialized = True

    def update_monitor_page(
        self,
        device_id: str,
        status_badge=None,
        title_label=None,
        name_label=None,
        last_update_label=None,
        register_table=None,
    ):
        """更新监控页面显示"""
        if status_badge:
            badge_status_map = {"success": "online", "warning": "warning", "info": "warning", "error": "error"}
            badge_type = badge_status_map.get(status_badge.get("type", "info"), "offline")
            status_badge["widget"].set_status(badge_type)

        if last_update_label:
            from datetime import datetime

            last_update_label.setText(f"更新时间 {datetime.now().strftime('%H:%M:%S')}")

    def update_register_table(self, register_table, registers: list):
        """更新寄存器表格"""
        if not register_table:
            return

        from PySide6.QtWidgets import QTableWidgetItem

        register_table.setRowCount(len(registers))
        for row, reg in enumerate(registers):
            for col, key in enumerate(["name", "address", "value", "unit"]):
                register_table.setItem(row, col, QTableWidgetItem(str(reg.get(key, ""))))


class StatusBarManager(BaseWindowManager):
    """
    状态栏管理器

    负责:
    - 状态栏创建
    - 状态信息更新
    - 统计数据显示
    """

    def create(self):
        """创建状态栏"""
        self._initialized = True

    def update_status(
        self,
        msg_label=None,
        total_label=None,
        online_label=None,
        offline_label=None,
        error_label=None,
        time_label=None,
        total=0,
        online=0,
        offline=0,
        error=0,
    ):
        """更新状态栏显示"""
        if total_label:
            total_label.setText(f"总计: {total}")
        if online_label:
            online_label.setText(f"在线: {online}")
        if offline_label:
            offline_label.setText(f"离线: {offline}")
        if error_label:
            error_label.setText(f"错误: {error}")
        if time_label:
            from datetime import datetime

            time_label.setText(f"更新时间: {datetime.now().strftime('%H:%M:%S')}")


class EventHandler(BaseWindowManager):
    """
    事件处理器

    负责:
    - 统一的事件分发和处理
    - 信号连接管理
    - 回调函数注册
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._callbacks: dict = {}

    def connect_signals(self, signal_map: dict):
        """
        批量连接信号

        Args:
            signal_map: {信号对象: 回调函数} 的映射字典
        """
        for signal, callback in signal_map.items():
            signal.connect(callback)

    def register_callback(self, event_name: str, callback):
        """
        注册回调函数

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        self._callbacks[event_name] = callback

    def emit_event(self, event_name: str, *args, **kwargs):
        """
        触发事件

        Args:
            event_name: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        if event_name in self._callbacks:
            self._callbacks[event_name](*args, **kwargs)


if __name__ == "__main__":
    print("✅ Window Manager System loaded")
    print("\n📦 Available managers:")
    print("  - UIManager: UI creation manager")
    print("  - DeviceListManager: Device list management")
    print("  - MonitorManager: Monitor page management")
    print("  - StatusBarManager: Status bar management")
    print("  - EventHandler: Event handling center")
