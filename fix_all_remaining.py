#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全面清理 main_window.py 残留：
1. 删除 _on_alarm_rules_changed 方法
2. 删除 _on_alarm_triggered 方法
3. 修复 _update_tree_adaptive_sizes 中的 self._modbus_generator / sizes[2] 残留
"""

import re

filepath = r"ui\main_window.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.rstrip()

    # ── 删除 _on_alarm_rules_changed 方法 ──
    if "_on_alarm_rules_changed" in stripped and stripped.startswith("    def "):
        print(f"  删除方法: _on_alarm_rules_changed (行 {i+1})")
        indent = len(line) - len(line.lstrip())
        i += 1
        while i < len(lines):
            next_line = lines[i]
            next_stripped = next_line.strip()
            # 方法结束：遇到下一个 def/class，且缩进 <= 方法缩进
            if (next_stripped.startswith("def ") or next_stripped.startswith("class ")) and (
                len(next_line) - len(next_line.lstrip())
            ) <= indent:
                break
            i += 1
        continue

    # ── 删除 _on_alarm_triggered 方法 ──
    if "_on_alarm_triggered" in stripped and stripped.startswith("    def "):
        print(f"  删除方法: _on_alarm_triggered (行 {i+1})")
        indent = len(line) - len(line.lstrip())
        i += 1
        while i < len(lines):
            next_line = lines[i]
            next_stripped = next_line.strip()
            if (next_stripped.startswith("def ") or next_stripped.startswith("class ")) and (
                len(next_line) - len(next_line.lstrip())
            ) <= indent:
                break
            i += 1
        continue

    # ── 修复 _update_tree_adaptive_sizes 中的残留行 ──
    # 将 sizes[2] 相关行替换为正确逻辑
    if "self._modbus_generator" in stripped:
        print(f"  修复行 {i+1}: 移除 self._modbus_generator 引用")
        i += 1
        continue

    # 将 setSizes([left_width, middle_width, right_width]) 替换为 setSizes([left_width, middle_width])
    if "setSizes([left_width, middle_width, right_width])" in stripped:
        line = line.replace("setSizes([left_width, middle_width, right_width])", "setSizes([left_width, middle_width])")
        # 同时删除上一行（right_width = ... 行）已被跳过，这里需要补全 middle_width 计算
        # 实际上 right_width 行已经被上面的 self._modbus_generator 检查跳过了
        # 所以这里只需要修正 setSizes 调用

    # 检查是否有 right_width = sizes[2] ... 的残留（已被 self._modbus_generator 检查处理）
    # 检查是否有 sizes[2] 的残留
    if "sizes[2]" in stripped:
        print(f"  修复行 {i+1}: 移除 sizes[2] 引用")
        i += 1
        continue

    new_lines.append(line)
    i += 1

# 第二遍：修复 _update_tree_adaptive_sizes 中的 right_width 变量
# 由于第一遍已删除 right_width = ... 行，需要补上 middle_width 的正确计算
content = "".join(new_lines)

# 将残余的 middle_width = total - left_width - right_width 替换为 middle_width = total - left_width
content = content.replace("middle_width = total - left_width - right_width", "middle_width = total - left_width")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("\n完成！请运行 read_lints 检查")
