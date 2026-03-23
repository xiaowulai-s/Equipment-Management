#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI设计系统验证脚本
验证HTML文件中的所有组件是否正确定义
"""

import re
from pathlib import Path

def check_html_file(filepath):
    """检查HTML文件中的CSS和组件定义"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checklist = {
        '色彩系统': {
            'CSS变量定义': '--color-primary-500' in content,
            '深色主题': '[data-theme="dark"]' in content,
            '浅色主题': '[data-theme="light"]' in content,
            '背景色变量': '--bg-base' in content and '--bg-raised' in content,
            '边框色变量': '--border-default' in content,
        },
        '按钮组件': {
            '主按钮样式': '.btn-primary' in content,
            '次按钮样式': '.btn-secondary' in content,
            '幽灵按钮': '.btn-ghost' in content,
            '危险按钮': '.btn-danger' in content,
            '图标按钮': '.btn-icon' in content,
        },
        '输入控件': {
            '文本输入框': '.input' in content,
            '下拉选择': '.select' in content,
            '复选框': '.checkbox' in content,
            '开关': '.toggle' in content,
        },
        '数据卡片': {
            '数据卡片容器': '.data-card' in content,
            '卡片标签': '.data-card-label' in content,
            '数据值': '.data-card-value' in content,
            '状态指示': '.data-card-status' in content,
            '趋势指示': '.data-card-trend' in content,
        },
        '仪表盘': {
            '仪表盘容器': '.gauge' in content,
            '仪表进度': '.gauge-fill' in content,
            '仪表数值': '.gauge-value' in content,
            '进度条': '.progress-bar' in content,
        },
        '数据表格': {
            '表格容器': '.data-table' in content,
            '表头': '.data-table th' in content,
            '表体': '.data-table td' in content,
            '行悬停': 'tr:hover td' in content,
        },
        '趋势图': {
            '图表容器': '.trend-chart' in content,
            'Canvas画布': '.chart-canvas' in content,
            '图例': '.chart-legend' in content,
            '绘制函数': 'drawTrendChart' in content,
        },
        '导航组件': {
            '侧边导航': '.sidebar-nav' in content,
            '导航项': '.nav-item' in content,
            '设备树': '.device-tree' in content,
            '设备项': '.device-item' in content,
        },
        '状态徽章': {
            '徽章容器': '.badge' in content,
            '成功状态': '.badge-success' in content,
            '警告状态': '.badge-warning' in content,
            '错误状态': '.badge-error' in content,
            '徽章点动画': 'badge-pulse' in content,
        },
        '交互反馈': {
            'Toast通知': '.toast' in content,
            '工具提示': '.tooltip' in content,
            '加载动画': '@keyframes spin' in content,
            '脉冲动画': '@keyframes pulse' in content,
            '滑入动画': '@keyframes slideIn' in content,
        },
    }
    
    print("=" * 70)
    print("工业设备管理系统 - UI设计系统验证报告")
    print("=" * 70)
    
    total_items = 0
    completed_items = 0
    
    for section, items in checklist.items():
        print(f"\n【{section}】")
        section_completed = 0
        
        for item, status in items.items():
            total_items += 1
            if status:
                completed_items += 1
                section_completed += 1
                print(f"  ✅ {item}")
            else:
                print(f"  ❌ {item}")
        
        completion_rate = (section_completed / len(items)) * 100
        print(f"  → 完成度: {completion_rate:.0f}% ({section_completed}/{len(items)})")
    
    print("\n" + "=" * 70)
    overall_rate = (completed_items / total_items) * 100
    print(f"总体完成度: {overall_rate:.1f}% ({completed_items}/{total_items})")
    
    if overall_rate == 100:
        print("✅ 所有组件验证通过！UI设计系统已完整集成。")
    elif overall_rate >= 90:
        print("⚠️  大部分组件已完成，建议检查缺失项。")
    else:
        print("❌ 存在重大缺失，需要进一步调整。")
    
    print("=" * 70)
    print("\n验证详情:")
    print(f"- 文件位置: {filepath}")
    print(f"- 文件大小: {len(content)} 字符")
    print(f"- 检查项数: {total_items}")
    print(f"- 通过项数: {completed_items}")
    print(f"- 失败项数: {total_items - completed_items}")

if __name__ == '__main__':
    html_file = Path('e:\\下载\\app\\equipment management\\UI设计预览.html')
    check_html_file(str(html_file))
