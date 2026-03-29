# -*- coding: utf-8 -*-
"""
自动集成 MonitorPage 到 MainWindow 的脚本

运行此脚本会自动修改 ui/main_window.py 文件，将 MonitorPage 集成进去。
"""

import os
import re


def integrate_monitor_page():
    """集成 MonitorPage 到 MainWindow"""

    main_window_path = "ui/main_window.py"

    # 备份原文件
    backup_path = "ui/main_window.py.backup"
    with open(main_window_path, "r", encoding="utf-8") as f:
        content = f.read()

    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"已备份原文件到: {backup_path}")

    # === 步骤1: 添加导入 ===
    print("\n步骤1: 添加导入...")

    # 在 "from ui.app_styles import AppStyles" 之后添加 MonitorPage 导入
    import_pattern = r"(from ui\.app_styles import AppStyles\n)"
    import_replacement = r"\1from ui.monitor_page import MonitorPage\n"

    if "from ui.monitor_page import MonitorPage" not in content:
        content = re.sub(import_pattern, import_replacement, content)
        print("  ✓ 添加导入: from ui.monitor_page import MonitorPage")
    else:
        print("  - 导入已存在，跳过")

    # === 步骤2: 在 __init__ 中初始化 MonitorPage ===
    print("\n步骤2: 在 __init__ 中初始化 MonitorPage...")

    # 在 __init__ 方法的末尾（在 _init_ui() 调用之前）添加 MonitorPage 初始化
    init_pattern = r"(self\._theme_manager = ThemeManager\(self\)\n)"
    init_replacement = r"\1        # 创建 MonitorPage 实例\n        self._monitor_page = MonitorPage()\n        # 连接信号：点击卡片/仪表盘/趋势图时跳转到寄存器详情\n        self._monitor_page.register_clicked.connect(self._on_register_clicked)\n"

    if "self._monitor_page = MonitorPage()" not in content:
        content = re.sub(init_pattern, init_replacement, content)
        print("  ✓ 初始化 MonitorPage 实例")
    else:
        print("  - MonitorPage 已初始化，跳过")

    # === 步骤3: 修改 _create_monitor_page 方法 ===
    print("\n步骤3: 修改 _create_monitor_page 方法...")

    # 替换整个 _create_monitor_page 方法
    old_create_monitor_page = """    def _create_monitor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self._device_title_label = QLabel(TextConstants.DEVICE_MONITOR_TITLE)
        self._device_title_label.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        self._device_title_label.setStyleSheet("color: #24292F;")
        layout.addWidget(self._device_title_label)

        info_layout = QHBoxLayout()
        self._device_name_label = QLabel(f"{TextConstants.DEVICE_NAME_LABEL} -")
        self._device_name_label.setStyleSheet("color: #57606A; font-size: 13px;")
        self._device_status_label = QLabel(f"{TextConstants.STATUS_LABEL} Not Connected")
        self._device_status_label.setStyleSheet("color: #CF222E; font-size: 13px;")
        self._last_update_label = QLabel(f"{TextConstants.LAST_UPDATE_LABEL} -")
        self._last_update_label.setStyleSheet("color: #8B949E; font-size: 12px;")

        info_layout.addWidget(self._device_name_label)
        info_layout.addWidget(self._device_status_label)
        info_layout.addStretch()
        info_layout.addWidget(self._last_update_label)
        layout.addLayout(info_layout)

        self._monitor_tabs = QTabWidget()
        self._monitor_tabs.setStyleSheet(StyleProvider.TAB_WIDGET)

        self._data_tab = self._create_data_tab()
        self._register_tab = self._create_register_tab()
        self._log_tab = self._create_log_tab()

        self._monitor_tabs.addTab(self._data_tab, TextConstants.TAB_REALTIME_DATA)
        self._monitor_tabs.addTab(self._register_tab, TextConstants.TAB_REGISTERS)
        self._monitor_tabs.addTab(self._log_tab, TextConstants.TAB_COMM_LOG)

        layout.addWidget(self._monitor_tabs)

        return page"""

    new_create_monitor_page = '''    def _create_monitor_page(self) -> QWidget:
        """创建监控页面 - 使用 MonitorPage 组件"""
        # 直接返回已初始化的 MonitorPage 实例
        return self._monitor_page'''

    if old_create_monitor_page in content:
        content = content.replace(old_create_monitor_page, new_create_monitor_page)
        print("  ✓ 替换 _create_monitor_page 方法")
    else:
        print("  - _create_monitor_page 方法未找到或已修改，跳过")

    # === 步骤4: 更新 _on_device_selected 方法 ===
    print("\n步骤4: 更新 _on_device_selected 方法...")

    # 查找并修改 _on_device_selected 方法
    old_device_selected = '''def _on_device_selected(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        """处理设备选择"""
        if not current:
            self._stacked_widget.setCurrentIndex(0)
            return

        device_id = current.data(0, Qt.ItemDataRole.UserRole)
        self._current_device_id = device_id
        self._update_monitor_page(device_id)
        self._stacked_widget.setCurrentIndex(1)'''

    new_device_selected = '''def _on_device_selected(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        """处理设备选择"""
        if not current:
            self._stacked_widget.setCurrentIndex(0)
            self._monitor_page.set_device(None)
            self._monitor_page.stop_updates()
            self._current_device_id = None
            return

        device_id = current.data(0, Qt.ItemDataRole.UserRole)
        self._current_device_id = device_id

        # 获取设备对象
        device = self._device_manager.get_device(device_id)
        if device:
            # 更新 MonitorPage
            self._monitor_page.set_device(device)
            self._monitor_page.start_updates()
            self._stacked_widget.setCurrentIndex(1)
        else:
            self._stacked_widget.setCurrentIndex(0)'''

    if old_device_selected in content:
        content = content.replace(old_device_selected, new_device_selected)
        print("  ✓ 更新 _on_device_selected 方法")
    else:
        print("  - _on_device_selected 方法未找到或已修改，跳过")

    # === 步骤5: 更新 _on_device_connected 方法 ===
    print("\n步骤5: 更新 _on_device_connected 方法...")

    old_device_connected = '''@Slot(str)
def _on_device_connected(self, device_id: str) -> None:
    """处理设备连接"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    if self._current_device_id == device_id:
        self._update_monitor_page(device_id)

    logger.info(LogMessages.DEVICE_CONNECTED.format(device_id=device_id))'''

    new_device_connected = '''@Slot(str)
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

    logger.info(LogMessages.DEVICE_CONNECTED.format(device_id=device_id))'''

    if old_device_connected in content:
        content = content.replace(old_device_connected, new_device_connected)
        print("  ✓ 更新 _on_device_connected 方法")
    else:
        print("  - _on_device_connected 方法未找到或已修改，跳过")

    # === 步骤6: 更新 _on_device_disconnected 方法 ===
    print("\n步骤6: 更新 _on_device_disconnected 方法...")

    old_device_disconnected = '''@Slot(str)
def _on_device_disconnected(self, device_id: str) -> None:
    """处理设备断开"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    if self._current_device_id == device_id:
        self._update_monitor_page(device_id)

    logger.info(LogMessages.DEVICE_DISCONNECTED.format(device_id=device_id))'''

    new_device_disconnected = '''@Slot(str)
def _on_device_disconnected(self, device_id: str) -> None:
    """处理设备断开"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    # 如果当前正在显示这个设备，清空 MonitorPage
    if self._current_device_id == device_id:
        self._monitor_page.set_device(None)
        self._monitor_page.stop_updates()

    logger.info(LogMessages.DEVICE_DISCONNECTED.format(device_id=device_id))'''

    if old_device_disconnected in content:
        content = content.replace(old_device_disconnected, new_device_disconnected)
        print("  ✓ 更新 _on_device_disconnected 方法")
    else:
        print("  - _on_device_disconnected 方法未找到或已修改，跳过")

    # === 步骤7: 更新 _on_device_removed 方法 ===
    print("\n步骤7: 更新 _on_device_removed 方法...")

    old_device_removed = '''@Slot(str)
def _on_device_removed(self, device_id: str) -> None:
    """处理设备移除"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    if self._current_device_id == device_id:
        self._stacked_widget.setCurrentIndex(0)

    logger.info(LogMessages.DEVICE_REMOVED.format(device_id=device_id))'''

    new_device_removed = '''@Slot(str)
def _on_device_removed(self, device_id: str) -> None:
    """处理设备移除"""
    self._refresh_device_list(self._search_edit.text())
    self._update_status_bar()

    # 如果当前正在显示这个设备，切换回欢迎页面并清空 MonitorPage
    if self._current_device_id == device_id:
        self._stacked_widget.setCurrentIndex(0)
        self._monitor_page.set_device(None)
        self._monitor_page.stop_updates()
        self._current_device_id = None

    logger.info(LogMessages.DEVICE_REMOVED.format(device_id=device_id))'''

    if old_device_removed in content:
        content = content.replace(old_device_removed, new_device_removed)
        print("  ✓ 更新 _on_device_removed 方法")
    else:
        print("  - _on_device_removed 方法未找到或已修改，跳过")

    # === 步骤8: 添加 _on_register_clicked 方法 ===
    print("\n步骤8: 添加 _on_register_clicked 方法...")

    on_register_clicked_method = '''    @Slot(str, int)
    def _on_register_clicked(self, device_id: str, register_address: int) -> None:
        """处理点击寄存器卡片/仪表盘/趋势图"""
        # 1. 获取设备和寄存器对象
        device = self._device_manager.get_device(device_id)
        if not device:
            logger.warning(f"设备不存在: {device_id}")
            return

        register = None
        for reg in device.registers.values():
            if reg.address == register_address:
                register = reg
                break

        if not register:
            logger.warning(f"寄存器不存在: 设备={device_id}, 地址={register_address}")
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

    '''

    # 在 _on_device_removed 方法之后添加 _on_register_clicked 方法
    if "_on_register_clicked" not in content:
        # 找到 _on_device_removed 方法的结束位置
        pattern = r"(\n        logger\.info\(LogMessages\.DEVICE_REMOVED\.format\(device_id=device_id\)\)\n\n)"
        content = re.sub(pattern, r"\1" + on_register_clicked_method, content)
        print("  ✓ 添加 _on_register_clicked 方法")
    else:
        print("  - _on_register_clicked 方法已存在，跳过")

    # === 步骤9: 删除不再需要的辅助方法 ===
    print("\n步骤9: 删除不再需要的辅助方法...")

    # 删除 _update_monitor_page 方法
    old_update_monitor_page_pattern = r"\n    def _update_monitor_page\(self, device_id: str\) -> None:.*?logger\.info\(LogMessages\.DEVICE_SELECTED\.format\(device_name=device\.name\)\)\n"
    if re.search(old_update_monitor_page_pattern, content, re.DOTALL):
        content = re.sub(old_update_monitor_page_pattern, "\n", content)
        print("  ✓ 删除 _update_monitor_page 方法")
    else:
        print("  - _update_monitor_page 方法未找到或已删除")

    # 删除 _create_data_tab, _create_register_tab, _create_log_tab 方法
    # 这些方法在新的 _create_monitor_page 中不再需要
    patterns_to_remove = [
        r"\n    def _create_data_tab\(self\) -> QWidget:.*?return tab\n",
        r"\n    def _create_register_tab\(self\) -> QWidget:.*?return tab\n",
        r"\n    def _create_log_tab\(self\) -> QWidget:.*?return tab\n",
    ]

    for pattern in patterns_to_remove:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, "\n", content)
            print(f"  ✓ 删除辅助方法")

    # === 写入修改后的文件 ===
    with open(main_window_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("\n✅ 集成完成！")
    print(f"\n修改已保存到: {main_window_path}")
    print(f"原文件已备份到: {backup_path}")
    print("\n请检查修改后的代码，确认无误后可以删除备份文件。")


if __name__ == "__main__":
    try:
        integrate_monitor_page()
    except Exception as e:
        print(f"\n❌ 集成失败: {e}")
        import traceback

        traceback.print_exc()
        print("\n请检查错误信息并手动修改文件。")
