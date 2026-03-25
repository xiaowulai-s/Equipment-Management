# -*- coding: utf-8 -*-
"""
文档生成脚本
Documentation Generation Script
"""

import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """安装文档生成依赖"""
    print("=" * 60)
    print("安装文档生成依赖...")
    print("=" * 60)

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "Sphinx>=7.0.0",
            "sphinx-rtd-theme>=2.0.0",
            "sphinx-autodoc-typehints>=2.0.0",
            "myst-parser>=2.0.0",
            "sphinx-copybutton>=0.5.0",
        ]
    )


def build_html():
    """构建 HTML 文档"""
    print("\n" + "=" * 60)
    print("构建 HTML 文档...")
    print("=" * 60)

    docs_dir = Path(__file__).parent / "docs"
    build_dir = docs_dir / "_build" / "html"

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-d",
            str(docs_dir / "_build" / "doctrees"),
            "-E",
            str(docs_dir),
            str(build_dir),
        ]
    )

    print(f"\n✅ 文档构建完成！")
    print(f"📄 打开文档：{build_dir / 'index.html'}")

    # 自动打开文档
    try:
        import webbrowser

        webbrowser.open(f"file:///{build_dir / 'index.html'}")
    except Exception as e:
        print(f"⚠️ 无法自动打开文档：{e}")


def build_pdf():
    """构建 PDF 文档（需要 LaTeX）"""
    print("\n" + "=" * 60)
    print("构建 PDF 文档...")
    print("=" * 60)

    docs_dir = Path(__file__).parent / "docs"
    build_dir = docs_dir / "_build" / "latex"

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "latex",
            "-d",
            str(docs_dir / "_build" / "doctrees"),
            str(docs_dir),
            str(build_dir),
        ]
    )

    print(f"\n✅ LaTeX 文件生成完成！")
    print(f"📄 PDF 文件位置：{build_dir}")
    print("⚠️ 需要使用 pdflatex 编译生成的 .tex 文件")


def clean():
    """清理构建文件"""
    print("\n" + "=" * 60)
    print("清理构建文件...")
    print("=" * 60)

    docs_dir = Path(__file__).parent / "docs"
    build_dir = docs_dir / "_build"

    if build_dir.exists():
        import shutil

        shutil.rmtree(build_dir)
        print(f"✅ 已清理：{build_dir}")
    else:
        print("ℹ️ 没有需要清理的文件")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="文档生成工具")
    parser.add_argument("--install", action="store_true", help="安装文档生成依赖")
    parser.add_argument("--build", action="store_true", help="构建 HTML 文档")
    parser.add_argument("--pdf", action="store_true", help="构建 PDF 文档")
    parser.add_argument("--clean", action="store_true", help="清理构建文件")
    parser.add_argument("--all", action="store_true", help="执行所有操作（安装依赖 + 构建文档）")

    args = parser.parse_args()

    if args.all:
        install_dependencies()
        build_html()
    elif args.install:
        install_dependencies()
    elif args.build:
        build_html()
    elif args.pdf:
        build_pdf()
    elif args.clean:
        clean()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python docs/generate_docs.py --install")
        print("  python docs/generate_docs.py --build")
        print("  python docs/generate_docs.py --all")


if __name__ == "__main__":
    main()
