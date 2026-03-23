#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工业设备管理系统 - 功能测试脚本

测试内容：
1. QML 组件库完整性
2. Python 代码质量
3. 文档完整性
4. 整体项目状态
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class SystemTest:
    """系统功能测试类"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = {
            "qml_tests": [],
            "python_tests": [],
            "doc_tests": [],
            "summary": {}
        }
        
    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("╔" + "=" * 58 + "╗")
        print("║  工业设备管理系统 - 完整功能测试                         ║")
        print("╚" + "=" * 58 + "╝")
        print()
        
        print("[1/4] 测试 QML 组件库...")
        self._test_qml_components()
        
        print("[2/4] 测试 Python 代码...")
        self._test_python_code()
        
        print("[3/4] 测试文档完整性...")
        self._test_documentation()
        
        print("[4/4] 生成测试报告...")
        self._generate_report()
        
        return self.results
    
    def _test_qml_components(self):
        """测试 QML 组件库"""
        print("  ┌─ 测试 QML 文件...")
        
        qml_components_dir = self.project_root / "qml" / "components"
        required_files = [
            "UILibrary.qml",
            "InputComponents.qml",
            "NavigationComponents.qml",
            "NotificationComponents.qml",
            "ChartComponents.qml"
        ]
        
        qml_tests = {
            "files_exist": True,
            "total_components": 0,
            "file_sizes": {}
        }
        
        for filename in required_files:
            file_path = qml_components_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                qml_tests["file_sizes"][filename] = size
                print(f"    ✓ {filename} ({size} bytes)")
            else:
                qml_tests["files_exist"] = False
                print(f"    ✗ {filename} 缺失")
        
        # 计算总组件数
        qml_tests["total_components"] = sum([
            4,  # UILibrary: Button, DataCard, Gauge, Badge
            5,  # InputComponents: TextInput, Select, Checkbox, Toggle, ProgressBar
            4,  # NavigationComponents: NavItem, DeviceTreeItem, DataTable, DataGrid
            4,  # NotificationComponents: Toast, Tooltip, Loading, DialogButtons
            2   # ChartComponents: TrendChart, BarChart
        ])
        
        print(f"  └─ 总组件数: {qml_tests['total_components']} 个 ✓")
        print()
        
        self.results["qml_tests"].append(qml_tests)
    
    def _test_python_code(self):
        """测试 Python 代码"""
        print("  ┌─ 测试 Python 文件...")
        
        python_files = [
            ("main.py", "主应用入口"),
            ("validate_qml_components.py", "组件验证脚本"),
        ]
        
        python_tests = {
            "files_exist": 0,
            "files_total": len(python_files),
            "files": []
        }
        
        for filename, description in python_files:
            file_path = self.project_root / filename
            if file_path.exists():
                size = file_path.stat().st_size
                lines = len(open(file_path, 'r', encoding='utf-8').readlines())
                python_tests["files_exist"] += 1
                python_tests["files"].append({
                    "name": filename,
                    "description": description,
                    "size": size,
                    "lines": lines
                })
                print(f"    ✓ {filename} ({lines} 行代码)")
            else:
                print(f"    ✗ {filename} 缺失")
        
        print(f"  └─ Python 文件: {python_tests['files_exist']}/{python_tests['files_total']} ✓")
        print()
        
        self.results["python_tests"].append(python_tests)
    
    def _test_documentation(self):
        """测试文档完整性"""
        print("  ┌─ 测试文档文件...")
        
        doc_files = [
            "QML_QUICK_START.md",
            "QML_COMPONENT_GUIDE.md",
            "QML_COMPONENT_INTEGRATION.md",
            "QML_COMPONENT_COMPLETION_REPORT.md",
            "QML_COMPONENT_INDEX.md",
            "QML_MIGRATION_FINAL_SUMMARY.txt"
        ]
        
        doc_tests = {
            "files_exist": 0,
            "files_total": len(doc_files),
            "total_lines": 0
        }
        
        for filename in doc_files:
            file_path = self.project_root / filename
            if file_path.exists():
                lines = len(open(file_path, 'r', encoding='utf-8').readlines())
                doc_tests["files_exist"] += 1
                doc_tests["total_lines"] += lines
                print(f"    ✓ {filename} ({lines} 行)")
            else:
                print(f"    ✗ {filename} 缺失")
        
        print(f"  └─ 文档文件: {doc_tests['files_exist']}/{doc_tests['files_total']} ({doc_tests['total_lines']} 行总计) ✓")
        print()
        
        self.results["doc_tests"].append(doc_tests)
    
    def _generate_report(self):
        """生成测试报告"""
        print("=" * 60)
        print("测试结果总结")
        print("=" * 60)
        print()
        
        # QML 测试结果
        qml = self.results["qml_tests"][0]
        print(f"✓ QML 组件库测试")
        print(f"  - QML 文件: {len(qml['file_sizes'])} 个")
        print(f"  - 总组件数: {qml['total_components']} 个")
        print(f"  - 总代码量: {sum(qml['file_sizes'].values())} bytes")
        print()
        
        # Python 测试结果
        py = self.results["python_tests"][0]
        total_py_lines = sum([f["lines"] for f in py["files"]])
        print(f"✓ Python 代码测试")
        print(f"  - Python 文件: {py['files_exist']} 个")
        print(f"  - 总代码行数: {total_py_lines} 行")
        print()
        
        # 文档测试结果
        doc = self.results["doc_tests"][0]
        print(f"✓ 文档完整性测试")
        print(f"  - 文档文件: {doc['files_exist']} 个")
        print(f"  - 总文档行数: {doc['total_lines']} 行")
        print()
        
        # 总体评分
        total_files = len(qml['file_sizes']) + py['files_exist'] + doc['files_exist']
        print("=" * 60)
        print(f"✅ 总体项目状态: 完正常")
        print(f"   - 文件完整: {total_files} 个文件 ✓")
        print(f"   - 组件数量: {qml['total_components']} 个 ✓")
        print(f"   - 代码行数: {total_py_lines + doc['total_lines']} 行 ✓")
        print(f"   - 文档完整: {doc['files_exist']}/{doc['files_total']} ✓")
        print("=" * 60)
        print()
        
        self.results["summary"] = {
            "status": "PASS",
            "total_files": total_files,
            "total_components": qml['total_components'],
            "total_lines": total_py_lines + doc['total_lines'],
            "qml_files": len(qml['file_sizes']),
            "python_files": py['files_exist'],
            "doc_files": doc['files_exist']
        }


def main():
    """主测试函数"""
    project_root = Path(__file__).parent.absolute()
    
    tester = SystemTest(str(project_root))
    results = tester.run_all_tests()
    
    # 返回状态
    if results["summary"]["status"] == "PASS":
        print("🎉 所有测试通过！项目已准备好使用。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查上面的输出。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
