"""
打包脚本
用于构建和打包工业设备管理系统
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并打印输出"""
    print(f"\n{'=' * 80}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print(f"{'=' * 80}\n")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"✗ 命令执行失败，返回码: {result.returncode}")
        sys.exit(1)

    return result


def check_dependencies():
    """检查依赖项"""
    print("检查依赖项...")

    # 检查Python版本
    if sys.version_info < (3, 10):
        print("✗ 需要Python 3.10或更高版本")
        sys.exit(1)
    print(f"✓ Python版本: {sys.version}")

    # 检查PyInstaller
    try:
        import PyInstaller

        print(f"✓ PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("✗ 未安装PyInstaller，正在安装...")
        run_command("pip install pyinstaller", "安装PyInstaller")

    # 检查项目依赖
    try:
        from PySide6 import QtCore

        print(f"✓ PySide6版本: {QtCore.__version__}")
    except ImportError:
        print("✗ 未安装PySide6")
        sys.exit(1)

    try:
        import sqlalchemy

        print(f"✓ SQLAlchemy版本: {sqlalchemy.__version__}")
    except ImportError:
        print("✗ 未安装SQLAlchemy")
        sys.exit(1)

    print("\n✓ 所有依赖项检查通过\n")


def clean_build():
    """清理构建目录"""
    print("清理构建目录...")

    dirs_to_remove = [
        "build",
        "dist",
        "__pycache__",
    ]

    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                pycache_path = os.path.join(root, d)
                try:
                    shutil.rmtree(pycache_path)
                    print(f"  删除: {pycache_path}")
                except Exception as e:
                    print(f"  警告: 无法删除 {pycache_path}: {e}")

    for d in dirs_to_remove:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f"  删除: {d}")
            except Exception as e:
                print(f"  警告: 无法删除 {d}: {e}")

    print("✓ 清理完成\n")


def build_executable(mode="single"):
    """
    构建可执行文件

    Args:
        mode: 'single' (单文件) 或 'dir' (目录模式)
    """
    print(f"开始构建可执行文件 (模式: {mode})...")

    # 检查spec文件
    spec_file = "build.spec"
    if not os.path.exists(spec_file):
        print(f"✗ 未找到spec文件: {spec_file}")
        sys.exit(1)

    # 构建命令
    if mode == "single":
        cmd = f"pyinstaller --clean {spec_file}"
    else:
        # 目录模式需要修改spec文件
        print("注意: 目录模式需要手动修改build.spec文件")
        cmd = f"pyinstaller --clean --onefile {spec_file}"

    run_command(cmd, "PyInstaller构建")

    print("✓ 构建完成\n")


def create_package():
    """创建分发包"""
    print("创建分发包...")

    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("✗ 未找到dist目录")
        sys.exit(1)

    # 查找可执行文件
    exe_files = list(dist_dir.glob("*.exe")) if os.name == "nt" else list(dist_dir.glob("*"))

    if not exe_files:
        print("✗ 未找到可执行文件")
        sys.exit(1)

    exe_file = exe_files[0]
    print(f"找到可执行文件: {exe_file}")

    # 创建发布目录
    release_dir = Path("release")
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()

    # 复制可执行文件
    dest_exe = release_dir / exe_file.name
    shutil.copy2(exe_file, dest_exe)
    print(f"复制到: {dest_exe}")

    # 复制文档
    docs_to_copy = [
        "README.md",
        "新架构说明_v2.md",
        "docs/用户文档.md",
    ]

    for doc in docs_to_copy:
        if os.path.exists(doc):
            dest_doc = release_dir / "docs" / os.path.basename(doc)
            dest_doc.parent.mkdir(exist_ok=True)
            shutil.copy2(doc, dest_doc)
            print(f"复制文档: {doc} -> {dest_doc}")

    # 创建使用说明
    readme_content = """# 工业设备管理系统

## 快速开始

1. 双击运行 `EquipmentManagement.exe`
2. 首次运行会自动创建配置文件
3. 点击菜单栏 "设备" -> "添加设备" 来配置设备
4. 选择设备并点击 "连接" 开始数据采集

## 配置文件位置

配置文件位于:
- Windows: `%APPDATA%/EquipmentManagement/config.json`
- 其他系统: `~/.config/EquipmentManagement/config.json`

## 日志文件位置

日志文件位于:
- Windows: `%APPDATA%/EquipmentManagement/logs/`
- 其他系统: `~/.config/EquipmentManagement/logs/`

## 技术支持

详见 `docs/` 目录下的文档。
"""

    with open(release_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\n✓ 分发包创建完成: {release_dir.absolute()}")
    print(f"\n发布包内容:")
    for item in release_dir.rglob("*"):
        if item.is_file():
            size_mb = item.stat().st_size / 1024 / 1024
            print(f"  {item.relative_to(release_dir)} ({size_mb:.2f}MB)")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("工业设备管理系统 - 打包工具")
    print("=" * 80 + "\n")

    # 检查依赖
    check_dependencies()

    # 清理
    clean_build()

    # 构建
    build_executable(mode="single")

    # 创建分发包
    create_package()

    print("\n" + "=" * 80)
    print("打包完成！")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
