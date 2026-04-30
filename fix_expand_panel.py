#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确修复 _expand_left_panel：删除引用 right_size 的行"""

filepath = r"ui\main_window.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 需要删除的行关键字（在 _expand_left_panel 方法内）
# 通过方法上下文定位，只删除该方法内的匹配行
new_lines = []
in_expand_method = False
skip_next_blank = False

i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.rstrip()

    # 检测方法开始
    if "_expand_left_panel" in stripped and "def " in stripped:
        in_expand_method = True
        new_lines.append(line)
        i += 1
        continue

    # 检测方法结束（遇到下一个 def 或 class）
    if in_expand_method and (stripped.startswith("def ") or stripped.startswith("class ")):
        in_expand_method = False

    # 在 _expand_left_panel 方法内，删除问题行
    if in_expand_method:
        # 删除含 right_size 的行
        if "right_size" in stripped:
            print(f"  删除行 {i+1}: {stripped[:80]}")
            i += 1
            continue
        # 删除含 scale 的行（属于已删除的 right_size 逻辑）
        if "scale" in stripped and "left_size" not in stripped:
            print(f"  删除行 {i+1}: {stripped[:80]}")
            i += 1
            continue
        # 删除残留注释
        if "# 右侧面板宽度" in stripped:
            print(f"  删除注释行 {i+1}: {stripped}")
            i += 1
            continue
        # 删除 if (left_size + right_size) 所在代码块
        if "available_for_sides" in stripped and "min_middle" not in stripped:
            # 这是旧的逻辑，需要删除此行及下一行
            print(f"  删除行 {i+1}: {stripped[:80]}")
            i += 1
            # 也删除下一行（注释行）
            if i < len(lines) and "#" in lines[i]:
                print(f"  删除行 {i+1}: {lines[i].rstrip()}")
                i += 1
            continue

    new_lines.append(line)
    i += 1

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("\n完成！请检查 _expand_left_panel 方法")
