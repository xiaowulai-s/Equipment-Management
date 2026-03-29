# -*- coding: utf-8 -*-
"""
项目代码变化监控脚本
Monitor project code changes
"""

import os
import subprocess
from datetime import datetime


def run_command(cmd, cwd=None):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)


def get_git_changes(project_path):
    """获取 git 变化"""
    stdout, stderr = run_command("git status --short", project_path)
    if stderr and "not a git repository" in stderr.lower():
        return None, "Not a git repository"

    changes = []
    for line in stdout.strip().split("\n"):
        if line.strip():
            # 解析 git status 输出
            status = line[:2].strip()
            file_path = line[3:].strip() if len(line) > 3 else ""
            changes.append({"status": status, "file": file_path})
    return changes, None


def get_recent_commits(project_path, count=5):
    """获取最近的提交"""
    cmd = f"git log --oneline -{count} --no-decorate"
    stdout, stderr = run_command(cmd, project_path)
    if stderr:
        return []

    commits = []
    for line in stdout.strip().split("\n"):
        if line.strip():
            parts = line.split(" ", 1)
            if len(parts) >= 2:
                commits.append({"hash": parts[0], "message": parts[1]})
    return commits


def get_file_stats(project_path):
    """获取文件统计"""
    stats = {"python_files": 0, "ui_files": 0, "test_files": 0, "docs_files": 0, "total_lines": 0}

    for root, dirs, files in os.walk(project_path):
        # 跳过虚拟环境
        if "venv" in root or "__pycache__" in root or ".git" in root:
            continue

        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, project_path)

            if file.endswith(".py"):
                if "test" in rel_path.lower():
                    stats["test_files"] += 1
                elif rel_path.startswith("ui/"):
                    stats["ui_files"] += 1
                else:
                    stats["python_files"] += 1

                # 统计代码行数
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        stats["total_lines"] += len(f.readlines())
                except Exception:
                    pass
            elif file.endswith(".md") or file.endswith(".rst"):
                stats["docs_files"] += 1

    return stats


def generate_summary(project_path):
    """生成变更摘要"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 获取变化
    changes, error = get_git_changes(project_path)

    summary = []
    summary.append(f"[项目代码监控报告] - {timestamp}")
    summary.append("=" * 60)

    if error:
        summary.append(f"[警告] Git 状态: {error}")
    else:
        # 统计变化
        modified = [c for c in changes if "M" in c["status"]]
        added = [c for c in changes if "A" in c["status"] or "??" in c["status"]]
        deleted = [c for c in changes if "D" in c["status"]]

        summary.append("\n[文件变更统计]")
        summary.append(f"   修改: {len(modified)} 个文件")
        summary.append(f"   新增: {len(added)} 个文件")
        summary.append(f"   删除: {len(deleted)} 个文件")

        # 最近提交
        commits = get_recent_commits(project_path)
        if commits:
            summary.append("\n[最近提交]")
            for commit in commits[:3]:
                msg = commit["message"]
                if len(msg) > 50:
                    msg = msg[:50] + "..."
                summary.append(f"   - {commit['hash'][:8]}: {msg}")

        # 文件统计
        stats = get_file_stats(project_path)
        summary.append("\n[项目统计]")
        summary.append(f"   Python 文件: {stats['python_files']}")
        summary.append(f"   UI 文件: {stats['ui_files']}")
        summary.append(f"   测试文件: {stats['test_files']}")
        summary.append(f"   文档文件: {stats['docs_files']}")
        summary.append(f"   总代码行数: ~{stats['total_lines']:,}")

        # 关键变化
        summary.append("\n[关键变更]")
        core_changes = [c for c in modified if c["file"].startswith("core/")]
        ui_changes = [c for c in modified if c["file"].startswith("ui/")]
        test_changes = [c for c in modified if "test" in c["file"].lower()]

        if core_changes:
            summary.append(f"   核心模块: {len(core_changes)} 个文件")
        if ui_changes:
            summary.append(f"   UI 模块: {len(ui_changes)} 个文件")
        if test_changes:
            summary.append(f"   测试: {len(test_changes)} 个文件")

    summary.append("\n" + "=" * 60)

    return "\n".join(summary)


if __name__ == "__main__":
    # 项目路径
    project_path = os.path.dirname(os.path.abspath(__file__))

    # 生成并打印摘要
    report = generate_summary(project_path)
    print(report)
