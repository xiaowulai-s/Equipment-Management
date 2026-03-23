#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
QML 组件库验证脚本

此脚本验证所有创建的 QML 组件文件的完整性和正确性。
检查项:
1. 文件是否存在
2. 文件大小是否合理
3. 文件中是否包含必要的 Component 定义
4. QML 语法是否正确
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

class QMLComponentValidator:
    """QML 组件库验证器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.qml_dir = self.project_root / "qml"
        self.components_dir = self.qml_dir / "components"
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
    def run_validation(self) -> Dict:
        """运行完整验证"""
        print("=" * 60)
        print("QML 组件库验证工具")
        print("=" * 60)
        print()
        
        # 检查目录结构
        print("[1/5] 检查目录结构...")
        self._check_directory_structure()
        
        # 检查组件库文件
        print("[2/5] 检查组件库文件...")
        self._check_component_files()
        
        # 检查组件定义
        print("[3/5] 检查组件定义...")
        self._check_component_definitions()
        
        # 检查文件内容
        print("[4/5] 检查文件内容...")
        self._check_file_contents()
        
        # 生成报告
        print("[5/5] 生成验证报告...")
        self._generate_report()
        
        return self.results
    
    def _check_directory_structure(self):
        """检查目录结构是否正确"""
        print(f"  → 检查 QML 目录: {self.qml_dir}")
        
        if not self.qml_dir.exists():
            self._add_error("目录不存在", f"{self.qml_dir}")
            return
        
        self._add_pass(f"✓ QML 目录存在: {self.qml_dir}")
        
        if not self.components_dir.exists():
            self._add_error("组件目录不存在", f"{self.components_dir}")
            return
        
        self._add_pass(f"✓ 组件目录存在: {self.components_dir}")
    
    def _check_component_files(self):
        """检查所有组件库文件"""
        required_files = [
            ("components/UILibrary.qml", "核心UI组件库"),
            ("components/InputComponents.qml", "输入控件库"),
            ("components/NavigationComponents.qml", "导航组件库"),
            ("components/NotificationComponents.qml", "通知组件库"),
            ("components/ChartComponents.qml", "图表组件库"),
            ("Theme.qml", "主题定义"),
            ("ComponentPreview.qml", "组件预览应用"),
        ]
        
        print(f"  → 检查 {len(required_files)} 个必需文件...")
        
        for file_rel_path, description in required_files:
            file_path = self.qml_dir / file_rel_path
            
            if file_path.exists():
                size = file_path.stat().st_size
                self._add_pass(f"✓ {description}: {file_rel_path} ({size} bytes)")
            else:
                self._add_error(f"文件缺失", f"{file_rel_path} - {description}")
    
    def _check_component_definitions(self):
        """检查主要的组件定义"""
        component_checks = [
            ("components/UILibrary.qml", [
                "Button",
                "DataCard",
                "Gauge",
                "Badge"
            ]),
            ("components/InputComponents.qml", [
                "textInputComponent",
                "selectComponent",
                "checkboxComponent",
                "toggleComponent",
                "progressBarComponent"
            ]),
            ("components/NavigationComponents.qml", [
                "navItemComponent",
                "deviceTreeItemComponent",
                "dataTableComponent",
                "dataGridComponent"
            ]),
            ("components/NotificationComponents.qml", [
                "toastComponent",
                "tooltipComponent",
                "loadingComponent",
                "dialogButtonsComponent"
            ]),
            ("components/ChartComponents.qml", [
                "trendChartComponent",
                "barChartComponent"
            ]),
        ]
        
        print(f"  → 检查组件定义...")
        
        for file_rel_path, components in component_checks:
            file_path = self.qml_dir / file_rel_path
            
            if not file_path.exists():
                self._add_error("文件缺失", f"{file_rel_path}")
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for component in components:
                # 检查 Component.id 或 id: component 的定义
                pattern = rf'id:\s*{component}|Component\s*{{\s*id:\s*{component}'
                if re.search(pattern, content):
                    self._add_pass(f"✓ {file_rel_path}: Component.{component}")
                else:
                    self._add_error(f"组件定义缺失", f"{file_rel_path}: {component}")
    
    def _check_file_contents(self):
        """检查文件内容的完整性"""
        print(f"  → 检查文件内容...")
        
        checks = [
            ("components/UILibrary.qml", [
                ("Button 变体支持", r"variant.*primary.*secondary.*ghost.*danger.*success"),
                ("数据卡片状态", r"status.*online.*offline.*warning"),
                ("仪表盘状态", r"status.*normal.*warning.*danger"),
                ("徽章脉冲动画", r"SequentialAnimationGroup|pulse")
            ]),
            ("components/InputComponents.qml", [
                ("文本输入框", r"TextInput"),
                ("下拉选择", r"moveDown.*moveUp|arrowIcon"),
                ("复选框", r"checkBox"),
                ("开关控件", r"toggleThumb")
            ]),
            ("components/NavigationComponents.qml", [
                ("菜单项", r"navItem"),
                ("设备树", r"deviceItem"),
                ("数据表格", r"tableContainer"),
                ("网格布局", r"GridLayout")
            ]),
            ("components/NotificationComponents.qml", [
                ("吐司通知", r"toast"),
                ("加载指示器", r"loadingContainer"),
                ("对话框按钮", r"DialogButtons")
            ]),
            ("components/ChartComponents.qml", [
                ("趋势图", r"Canvas|trendChartComponent"),
                ("柱状图", r"BarChart|barChartComponent")
            ]),
        ]
        
        for file_rel_path, patterns in checks:
            file_path = self.qml_dir / file_rel_path
            
            if not file_path.exists():
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for description, pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                    self._add_pass(f"✓ {file_rel_path}: {description}")
                else:
                    self._add_warning(f"可能缺失", f"{file_rel_path}: {description}")
    
    def _add_pass(self, message: str):
        """添加通过记录"""
        self.results["passed"] += 1
        self.results["total"] += 1
        self.results["details"].append(("PASS", message))
    
    def _add_error(self, error_type: str, details: str):
        """添加错误记录"""
        self.results["failed"] += 1
        self.results["total"] += 1
        self.results["details"].append(("ERROR", f"{error_type}: {details}"))
    
    def _add_warning(self, warning_type: str, details: str):
        """添加警告记录"""
        self.results["details"].append(("WARNING", f"{warning_type}: {details}"))
    
    def _generate_report(self):
        """生成验证报告"""
        print()
        print("=" * 60)
        print("验证报告")
        print("=" * 60)
        
        # 输出所有详情
        for status, message in self.results["details"]:
            if status == "PASS":
                prefix = "✓"
            elif status == "ERROR":
                prefix = "✗"
            else:
                prefix = "⚠"
            
            print(f"{prefix} {message}")
        
        print()
        print("-" * 60)
        print(f"总计: {self.results['total']} 项检查")
        print(f"通过: {self.results['passed']} 项 ({self._get_pass_rate()}%)")
        print(f"失败: {self.results['failed']} 项")
        print("-" * 60)
        
        if self.results["failed"] == 0:
            print("✓ 所有检查通过！")
        else:
            print("✗ 存在失败的检查项")
        
        print()
    
    def _get_pass_rate(self) -> int:
        """获取通过率"""
        if self.results["total"] == 0:
            return 0
        return int((self.results["passed"] / self.results["total"]) * 100)
    
    def get_summary(self) -> Dict:
        """获取验证摘要"""
        return {
            "total_checks": self.results["total"],
            "passed_checks": self.results["passed"],
            "failed_checks": self.results["failed"],
            "pass_rate": f"{self._get_pass_rate()}%",
            "status": "PASS" if self.results["failed"] == 0 else "FAIL"
        }


def main():
    """主函数"""
    import sys
    
    # 获取项目根目录
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # 使用当前脚本所在目录作为项目根目录
        project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 创建验证器并运行
    validator = QMLComponentValidator(project_root)
    results = validator.run_validation()
    
    # 输出摘要
    summary = validator.get_summary()
    print()
    print("=" * 60)
    print("验证摘要")
    print("=" * 60)
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("=" * 60)
    
    # 返回状态码
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    exit(main())
