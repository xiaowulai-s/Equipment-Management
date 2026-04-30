#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""继续清理 main_window.py：
1. 删除 __init__ 中的 _alarm_manager / _notification_service / _right_panel_saved_size
2. 删除 _setup_alarm_rules() 调用
3. 删除 docstring 中的 _alarm_manager 属性说明
4. 清理 _collapse_left_panel / _expand_left_panel 中的右侧面板逻辑
5. 删除所有对 _alarm_manager / _notification_service 的引用行
"""

import re

filepath = r"ui\main_window.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
removed = set()
while i < len(lines):
    line = lines[i]
    stripped = line.rstrip()

    # ── 跳过含 _alarm_manager 或 _notification_service 的行 ──
    if "_alarm_manager" in stripped or "_notification_service" in stripped:
        print(f"  删除引用行 {i+1}: {stripped[:80]}")
        i += 1
        continue

    # ── 跳过 _right_panel_saved_size 行（属性定义和赋值） ──
    if "_right_panel_saved_size" in stripped:
        print(f"  删除 _right_panel_saved_size 行 {i+1}: {stripped[:80]}")
        i += 1
        continue

    # ── 跳过 _setup_alarm_rules 调用 ──
    if "_setup_alarm_rules" in stripped:
        print(f"  删除 _setup_alarm_rules 调用 {i+1}: {stripped[:80]}")
        i += 1
        continue

    # ── 在 docstring 中删除 "_alarm_manager: 报警管理器" 那一行 ──
    if "_alarm_manager: 报警管理器" in stripped:
        print(f"  删除 docstring 属性 {i+1}: {stripped}")
        i += 1
        continue

    new_lines.append(line)
    i += 1

# 写回
with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"\n完成！共处理 {len(lines)} 行，输出 {len(new_lines)} 行")
print("请运行 read_lints 检查语法")
