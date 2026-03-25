# -*- coding: utf-8 -*-
"""
测试运行脚本
Test Runner Script
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """运行所有测试并生成覆盖率报告"""
    project_root = Path(__file__).parent.parent

    # 安装必要的测试依赖
    print("=" * 60)
    print("安装测试依赖...")
    print("=" * 60)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pytest>=7.0.0", "pytest-cov>=4.0.0", "pytest-qt>=4.2.0"]
    )

    # 运行测试并生成覆盖率报告
    print("\n" + "=" * 60)
    print("运行测试...")
    print("=" * 60)

    test_dir = project_root / "tests"

    # 运行 pytest 并生成覆盖率报告
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_dir),
            "-v",
            "--cov=core",
            "--cov=ui",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-config=.coveragerc",
        ],
        cwd=project_root,
    )

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print(f"\n覆盖率报告已生成：{project_root / 'htmlcov' / 'index.html'}")
    else:
        print("\n" + "=" * 60)
        print("❌ 部分测试失败，请查看上面的错误信息")
        print("=" * 60)
        sys.exit(1)

    return result.returncode


def run_tests_simple():
    """简单运行测试（不生成覆盖率报告）"""
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "tests"

    result = subprocess.run([sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short"], cwd=project_root)

    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="运行测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--simple", action="store_true", help="简单运行测试（无覆盖率）")

    args = parser.parse_args()

    if args.simple:
        exit_code = run_tests_simple()
    else:
        exit_code = run_tests()

    sys.exit(exit_code)
