#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 _collapse_left_panel 和 _expand_left_panel：移除右侧面板逻辑"""

filepath = r"ui\main_window.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # ── 修复 _collapse_left_panel ──
    if "_collapse_left_panel" in line and "def " in line:
        # 写入方法定义行
        new_lines.append(line)
        i += 1
        # 写入方法体，跳过右侧面板相关行
        while i < len(lines):
            current = lines[i]
            # 遇到下一个 def 或类定义，停止
            if current.strip().startswith("def ") or current.strip().startswith("class "):
                break
            # 跳过含 current_sizes[2] 的行
            if "current_sizes[2]" in current:
                i += 1
                continue
            # 将 setSizes([0, total - current_sizes[2], current_sizes[2]]) 替换为 setSizes([0, total])
            if "setSizes([0, total - current_sizes[2], current_sizes[2]])" in current:
                current = current.replace(
                    "setSizes([0, total - current_sizes[2], current_sizes[2]])", "setSizes([0, total])"
                )
            new_lines.append(current)
            i += 1
        continue

    # ── 修复 _expand_left_panel 中的 right_size 引用 ──
    if "right_size" in line and ("=" in line or "setSizes" in line):
        # 跳过 right_size 赋值行
        if "right_size = " in line:
            i += 1
            continue
        # 替换含 right_size 的 setSizes 行
        if "setSizes([left_size, middle_width, right_size])" in line:
            line = line.replace(
                "setSizes([left_size, middle_width, right_size])", "setSizes([left_size, middle_width])"
            )
        # 替换含 right_size 的其他行
        if "right_size" in line:
            # 注释掉或删除此行
            i += 1
            continue

    new_lines.append(line)
    i += 1

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("完成！请检查 _collapse_left_panel 和 _expand_left_panel 方法")
