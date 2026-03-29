# -*- coding: utf-8 -*-
"""
自动应用 MonitorPage 集成补丁到 MainWindow

运行此脚本会自动修改 ui/main_window.py 文件，将 MonitorPage 集成进去。
"""

import os
import re


def patch_main_window():
    """应用 MonitorPage 集成补丁"""

    main_window_path = "ui/main_window.py"

    # 备份原文件
    backup_path = "ui/main_window.py.backup_before_monitor_page"
    with open(main_window_path, "r", encoding="utf-8") as f:
        content = f.read()

    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ 已备份原文件到: {backup_path}")

    # === 步骤1: 添加 MonitorPage 导入 ===
    print("\n[步骤1] 添加 MonitorPage 导入...")

    # 在 "from ui.theme_toggle_button import ThemeStatusBarButton" 之后添加
    import_marker = "from ui.theme_toggle_button import ThemeStatusBarButton"
    import_addition = "\nfrom ui.monitor_page import MonitorPage"

    if import_marker in content and "from ui.monitor_page import MonitorPage" not in content:
        content = content.replace(import_marker, import_marker + import_addition)
        print("  ✓ 添加导入: from ui.monitor_page import MonitorPage")
    else:
        print("  - 导入已存在或未找到插入点")

    # === 步骤2: 在 __init__ 方法中初始化 MonitorPage ===
    print("\n[步骤2] 在 __init__ 方法中初始化 MonitorPage...")

    # 查找并替换 __init__ 方法中的特定部分
    # 我们需要查找在主题初始化之后、_init_ui()调用之前的位置

    # 模式1: 查找 self._theme_manager = ThemeManager() 之后的位置
    init_pattern1 = r"(self\._theme_manager = ThemeManager\(\)\n)"
    init_replacement1 = r"\1        # 创建 MonitorPage 实例\n        self._monitor_page = MonitorPage()\n\n        # 连接信号：点击卡片/仪表盘/趋势图时跳转到寄存器详情\n        self._monitor_page.register_clicked.connect(self._on_register_clicked)\n"

    if re.search(init_pattern1, content) and "self._monitor_page = MonitorPage()" not in content:
        content = re.sub(init_pattern1, init_replacement1, content)
        print("  ✓ 在 __init__ 中初始化 MonitorPage")
    else:
        print("  - MonitorPage 已初始化或未找到插入点")

    # === 步骤3: 修改 _init_ui 方法中的监控页面部分 ===
    print("\n[步骤3] 修改 _init_ui 方法...")

    # 查找并替换监控页面的添加部分
    # 原代码:
    # monitor_page = self._create_monitor_page()
    # self._stacked_widget.addWidget(monitor_page)

    monitor_page_pattern = (
        r"(monitor_page = self\._create_monitor_page\(\)\n        self\._stacked_widget\.addWidget\(monitor_page\)\n)"
    )
    monitor_page_replacement = r"        # 添加 MonitorPage（替换原来的 monitor_page）\n        self._stacked_widget.addWidget(self._monitor_page)\n"

    if re.search(monitor_page_pattern, content):
        content = re.sub(monitor_page_pattern, monitor_page_replacement, content)
        print("  ✓ 替换 _init_ui 中的监控页面")
    else:
        print("  - 未找到监控页面代码或已修改")

    # === 步骤4: 更新 _on_device_selected 方法 ===
    print("\n[步骤4] 更新 _on_device_selected 方法...")

    # 原方法签名和开头
    old_device_selected = '''def _on_device_selected(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        """处理设备选择"""
        if not current:
            self._stacked_widget.setCurrentIndex(0)
            return

        device_id = current.data(0, Qt.ItemDataRole.UserRole)
        self._current_device_id = device_id
        self._update_monitor_page(device_id)
        self._stacked_widget.setCurrentIndex(1)'''

    # 新方法
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
        print("  - 未找到 _on_device_selected 方法或已修改")

    # === 步骤5: 更新 _on_device_connected 方法 ===
    print("\n[步骤5] 更新 _on_device_connected 方法...")

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
        print("  - 未找到 _on_device_connected 方法或已修改")

    # === 步骤6: 更新 _on_device_disconnected 方法 ===
    print("\n[步骤6] 更新 _on_device_disconnected 方法...")

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
        print("  - 未找到 _on_device_disconnected 方法或已修改")

    # === 步骤7: 更新 _on_device_removed 方法 ===
    print("\n[步骤7] 更新 _on_device_removed 方法...")

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
        print("  - 未找到 _on_device_removed 方法或已修改")

    # === 步骤8: 添加 _on_register_clicked 方法 ===
    print("\n[步骤8] 添加 _on_register_clicked 方法...")

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

    # 在 _on_device_removed 方法之后添加
    if "_on_register_clicked" not in content:
        # 查找 _on_device_removed 方法的结束位置
        insert_pattern = r"(\n        logger\.info\(LogMessages\.DEVICE_REMOVED\.format\(device_id=device_id\)\)\n\n)"
        content = re.sub(insert_pattern, r"\1" + on_register_clicked_method, content)
        print("  ✓ 添加 _on_register_clicked 方法")
    else:
        print("  - _on_register_clicked 方法已存在")

    # === 写入修改后的文件 ===
    with open(main_window_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("\n" + "=" * 60)
    print("✅ 补丁应用完成！")
    print("=" * 60)
    print(f"\n修改已保存到: {main_window_path}")
    print(f"原文件已备份到: {backup_path}")
    print("\n请检查修改后的代码，确认无误后可以删除备份文件。")
    print("\n运行应用测试:")
    print("  python main.py")


if __name__ == "__main__":
    import sys

    try:
        patch_main_window()
    except Exception as e:
        print(f"\n❌ 补丁应用失败: {e}")
        import traceback

        traceback.print_exc()
        print("\n请检查错误信息并手动修改文件。")
        sys.exit(1)
