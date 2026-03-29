"""
批量重构对话框脚本
用于快速重构所有对话框文件以使用新的UI组件库
"""

import re
from pathlib import Path


def refactor_dialog_file(file_path: Path) -> None:
    """重构单个对话框文件"""
    content = file_path.read_text(encoding="utf-8")
    original_content = content

    # 1. 更新导入
    if "from ui.widgets import" not in content:
        if "from ui.app_styles import AppStyles" in content:
            content = content.replace(
                "from ui.app_styles import AppStyles",
                """from ui.widgets import (
    PrimaryButton,
    SecondaryButton,
    SuccessButton,
    DangerButton,
    LineEdit,
    ComboBox,
    DataTable,
)
from ui.app_styles import AppStyles""",
            )
        elif "from ui.app_styles" in content:
            content = content.replace(
                "from ui.app_styles",
                """from ui.widgets import (
    PrimaryButton,
    SecondaryButton,
    SuccessButton,
    DangerButton,
    LineEdit,
    ComboBox,
    DataTable,
)
from ui.app_styles""",
            )

    # 2. 替换 QPushButton -> PrimaryButton
    content = re.sub(r'QPushButton\("确定"\)', 'PrimaryButton("确定")', content)
    content = re.sub(r'QPushButton\("取消"\)', 'SecondaryButton("取消")', content)
    content = re.sub(r'QPushButton\("保存"\)', 'PrimaryButton("保存")', content)
    content = re.sub(r'QPushButton\("删除"\)', 'DangerButton("删除")', content)
    content = re.sub(r'QPushButton\("导出"\)', 'SuccessButton("导出")', content)
    content = re.sub(r'QPushButton\("连接"\)', 'SuccessButton("连接")', content)
    content = re.sub(r'QPushButton\("断开"\)', 'DangerButton("断开")', content)
    content = re.sub(r'QPushButton\("测试"\)', 'SecondaryButton("测试")', content)

    # 3. 替换 QLineEdit -> LineEdit
    content = re.sub(r"QLineEdit\(\)", 'LineEdit("")', content)
    content = re.sub(r'QLineEdit\("([^"]+)"\)', r'LineEdit("\1")', content)

    # 4. 替换 QComboBox -> ComboBox
    content = re.sub(r"QComboBox\(\)", "ComboBox()", content)

    # 5. 移除内联样式调用
    content = re.sub(r"\.setStyleSheet\(AppStyles\.\w+\)", "", content)
    content = re.sub(r"\.setStyleSheet\(AppStyles\.get_\w+\(\w+\)\)", "", content)

    # 6. 移除 QTableWidget, QTableWidgetItem 导入
    content = re.sub(
        r"from PySide6\.QtWidgets import \([^)]+QTableWidget[^)]+\)",
        lambda m: m.group(0).replace("QTableWidget,", "").replace("QTableWidgetItem,", ""),
        content,
    )

    # 7. 如果有变化，写入文件
    if content != original_content:
        file_path.write_text(content, encoding="utf-8")
        print(f"✓ 重构完成: {file_path.name}")
        return True
    else:
        print(f"- 无需重构: {file_path.name}")
        return False


def main():
    """批量重构所有对话框"""
    dialog_files = [
        "ui/batch_operations_dialog.py",
        "ui/data_export_dialog.py",
        "ui/device_type_dialogs.py",
        "ui/log_viewer_dialog.py",
        "ui/register_config_dialog.py",
        "ui/dialogs/settings_dialog.py",
    ]

    project_root = Path(__file__).parent
    success_count = 0

    for dialog_file in dialog_files:
        file_path = project_root / dialog_file
        if file_path.exists():
            if refactor_dialog_file(file_path):
                success_count += 1
        else:
            print(f"✗ 文件不存在: {dialog_file}")

    print(f"\n总计重构: {success_count}/{len(dialog_files)} 个对话框")


if __name__ == "__main__":
    main()
