# -*- coding: utf-8 -*-
"""
项目功能更新通知脚本
生成详细的功能更新摘要
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)


def get_recent_changes(project_path, since_minutes=5):
    """获取最近的变化"""
    # 获取最近的提交详情
    cmd = f'git log --since="{since_minutes} minutes ago" --oneline --no-decorate'
    stdout, _ = run_command(cmd, project_path)

    changes = []
    for line in stdout.strip().split("\n"):
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) >= 2:
                changes.append({"hash": parts[0], "message": parts[1]})
    return changes


def get_changed_files(project_path, since_minutes=5):
    """获取变更的文件列表"""
    cmd = f"git diff --name-only HEAD~1 HEAD"
    stdout, _ = run_command(cmd, project_path)

    files = {"core": [], "ui": [], "tests": [], "docs": [], "config": [], "other": []}

    for line in stdout.strip().split("\n"):
        if not line.strip():
            continue

        if line.startswith("core/"):
            files["core"].append(line)
        elif line.startswith("ui/"):
            files["ui"].append(line)
        elif "test" in line.lower():
            files["tests"].append(line)
        elif line.endswith(".md") or line.startswith("docs/"):
            files["docs"].append(line)
        elif line in ["requirements.txt", "pyproject.toml", ".flake8", ".gitignore"]:
            files["config"].append(line)
        else:
            files["other"].append(line)

    return files


def categorize_changes(commits):
    """按类型分类变更"""
    categories = {
        "feat": [],  # 新功能
        "fix": [],  # Bug修复
        "docs": [],  # 文档
        "refactor": [],  # 重构
        "test": [],  # 测试
        "chore": [],  # 构建/工具
        "other": [],  # 其他
    }

    for commit in commits:
        msg = commit["message"].lower()
        if msg.startswith("feat"):
            categories["feat"].append(commit)
        elif msg.startswith("fix"):
            categories["fix"].append(commit)
        elif msg.startswith("docs"):
            categories["docs"].append(commit)
        elif msg.startswith("refactor"):
            categories["refactor"].append(commit)
        elif msg.startswith("test"):
            categories["test"].append(commit)
        elif msg.startswith("chore"):
            categories["chore"].append(commit)
        else:
            categories["other"].append(commit)

    return categories


def generate_update_summary(project_path):
    """生成功能更新摘要"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取最近变化
    changes = get_recent_changes(project_path, since_minutes=5)

    summary = []
    summary.append(f"[项目功能更新] - {timestamp}")
    summary.append("=" * 60)

    if not changes:
        summary.append("\n[状态] 过去5分钟没有新的代码提交")
    else:
        summary.append(f"\n[更新概览] 最近5分钟有 {len(changes)} 个提交")

        # 分类变更
        categories = categorize_changes(changes)

        if categories["feat"]:
            summary.append("\n[新增功能]")
            for c in categories["feat"][:3]:
                msg = c["message"].replace("feat:", "").replace("feat", "").strip()
                summary.append(f"   - {msg}")

        if categories["fix"]:
            summary.append("\n[Bug修复]")
            for c in categories["fix"][:3]:
                msg = c["message"].replace("fix:", "").replace("fix", "").strip()
                summary.append(f"   - {msg}")

        if categories["refactor"]:
            summary.append("\n[代码重构]")
            for c in categories["refactor"][:3]:
                msg = c["message"].replace("refactor:", "").replace("refactor", "").strip()
                summary.append(f"   - {msg}")

        if categories["docs"]:
            summary.append("\n[文档更新]")
            for c in categories["docs"][:3]:
                msg = c["message"].replace("docs:", "").replace("docs", "").strip()
                summary.append(f"   - {msg}")

    # 获取变更文件
    changed_files = get_changed_files(project_path)

    summary.append("\n[变更文件分布]")
    total = sum(len(v) for v in changed_files.values())
    if total > 0:
        if changed_files["core"]:
            summary.append(f"   核心模块: {len(changed_files['core'])} 个")
        if changed_files["ui"]:
            summary.append(f"   UI界面: {len(changed_files['ui'])} 个")
        if changed_files["tests"]:
            summary.append(f"   测试文件: {len(changed_files['tests'])} 个")
        if changed_files["docs"]:
            summary.append(f"   文档: {len(changed_files['docs'])} 个")
        if changed_files["config"]:
            summary.append(f"   配置: {len(changed_files['config'])} 个")
    else:
        summary.append("   暂无文件变更")

    # 项目健康状态
    summary.append("\n[项目健康度]")

    # 检查测试文件比例
    test_count = len(changed_files["tests"])
    core_count = len(changed_files["core"])
    if core_count > 0:
        ratio = test_count / core_count
        if ratio >= 0.5:
            summary.append("   测试覆盖: 良好")
        elif ratio >= 0.3:
            summary.append("   测试覆盖: 一般")
        else:
            summary.append("   测试覆盖: 建议增加测试")

    # 检查文档更新
    if changed_files["docs"]:
        summary.append("   文档同步: 已更新")
    else:
        summary.append("   文档同步: 无变更")

    summary.append("\n" + "=" * 60)

    return "\n".join(summary)


if __name__ == "__main__":
    project_path = os.path.dirname(os.path.abspath(__file__))
    report = generate_update_summary(project_path)
    print(report)
