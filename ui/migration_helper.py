# -*- coding: utf-8 -*-
"""
DesignTokens 迁移助手 (DesignTokens Migration Helper)

提供自动化工具，帮助将硬编码的颜色、字体、间距等迁移到 DesignTokens 系统。

使用示例:
    from ui.migration_helper import TokenMigrator

    migrator = TokenMigrator()

    # 分析文件中的硬编码
    report = migrator.analyze_file("ui/main_window_v2.py")
    print(report)

    # 自动替换（需要人工审核）
    migrator.migrate_file("ui/main_window_v2.py", dry_run=True)
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardcodedItem:
    """硬编码项"""

    file_path: str
    line_number: int
    line_content: str
    item_type: str  # "color", "font", "spacing", "radius"
    value: str
    suggested_replacement: str
    confidence: float  # 0-1, 替换置信度


class TokenMigrator:
    """
    DesignTokens 迁移器

    功能:
        - 检测代码中的硬编码值
        - 提供DesignTokens替代建议
        - 生成迁移报告
    """

    # 颜色模式 (匹配 #XXXXXX 或 rgb/rgba)
    COLOR_PATTERN = re.compile(r"(?:#(?:[0-9A-Fa-f]{3}){1,2}|rgba?\([^)]+\))", re.IGNORECASE)

    # 字体大小模式
    FONT_SIZE_PATTERN = re.compile(r"font-size:\s*(\d+)px", re.IGNORECASE)

    # 间距模式
    SPACING_PATTERN = re.compile(r"(?:margin|padding):\s*(\d+)px", re.IGNORECASE)

    # 圆角模式
    RADIUS_PATTERN = re.compile(r"border-radius:\s*(\d+)px", re.IGNORECASE)

    # 已知的颜色映射表
    COLOR_MAPPINGS: Dict[str, str] = {
        "#24292F": "DT.C.TEXT_PRIMARY",
        "#57606A": "DT.C.TEXT_SECONDARY",
        "#8B949E": "DT.C.TEXT_TERTIARY",
        "#9CA3AF": "DT.C.TEXT_DISABLED",
        "#0969DA": "DT.C.ACCENT_PRIMARY",
        "#1A7F37": "DT.C.STATUS_SUCCESS",
        "#BF8700": "DT.C.STATUS_WARNING",
        "#CF222E": "DT.C.STATUS_ERROR",
        "#D0D7DE": "DT.C.BORDER_DEFAULT",
        "#E5E7EB": "DT.C.DIVIDER",
        "#F3F4F6": "DT.C.BG_HOVER",
        "#F6F8FA": "DT.C.BG_SECONDARY",
        "#FFFFFF": "DT.C.BG_PRIMARY",
        "#4CAF50": "DT.C.DEVICE_ONLINE",
        "#F44336": "DT.C.DEVICE_ERROR",
        "#FF9800": "DT.C.DEVICE_WARNING",
        "#9E9E9E": "DT.C.DEVICE_OFFLINE",
    }

    def __init__(self):
        self.issues: List[HardcodedItem] = []

    def analyze_file(self, file_path: str) -> Dict:
        """
        分析单个文件中的硬编码

        Args:
            file_path: 文件路径

        Returns:
            Dict: 分析结果 {
                'file': str,
                'total_issues': int,
                'colors': int,
                'fonts': int,
                'spacings': int,
                'radii': int,
                'items': List[HardcodedItem]
            }
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": f"文件不存在: {file_path}"}

        items: List[HardcodedItem] = []

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            return {"error": f"读取文件失败: {e}"}

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # 检测颜色
            for match in self.COLOR_PATTERN.finditer(line):
                color_value = match.group()
                if color_value.upper() in [k.upper() for k in self.COLOR_MAPPINGS.keys()]:
                    replacement = next(
                        (v for k, v in self.COLOR_MAPPINGS.items() if k.upper() == color_value.upper()), None
                    )
                    if replacement:
                        items.append(
                            HardcodedItem(
                                file_path=str(file_path),
                                line_number=line_num,
                                line_content=line,
                                item_type="color",
                                value=color_value,
                                suggested_replacement=replacement,
                                confidence=0.95,
                            )
                        )

            # 检测字体大小
            font_match = self.FONT_SIZE_PATTERN.search(line)
            if font_match:
                size = font_match.group(1)
                items.append(
                    HardcodedItem(
                        file_path=str(file_path),
                        line_number=line_num,
                        line_content=line,
                        item_type="font_size",
                        value=f"{size}px",
                        suggested_replacement=f"DT.Typography.BODY[1] (需确认)",
                        confidence=0.6,
                    )
                )

        self.issues.extend(items)

        return {
            "file": str(file_path),
            "total_issues": len(items),
            "colors": sum(1 for i in items if i.item_type == "color"),
            "fonts": sum(1 for i in items if i.item_type == "font_size"),
            "spacings": sum(1 for i in items if i.item_type == "spacing"),
            "radii": sum(1 for i in items if i.item_type == "radius"),
            "items": items,
        }

    def analyze_directory(self, dir_path: str, pattern: str = "*.py") -> Dict:
        """
        分析目录中的所有Python文件

        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式

        Returns:
            Dict: 汇总报告
        """
        directory = Path(dir_path)
        files = list(directory.rglob(pattern))

        results = []
        total_issues = 0

        for file_path in files:
            result = self.analyze_file(str(file_path))
            if "error" not in result:
                results.append(result)
                total_issues += result["total_issues"]

        return {
            "directory": str(dir_path),
            "files_analyzed": len(results),
            "total_issues": total_issues,
            "details": results,
        }

    def generate_migration_report(self, output_file: str = "migration_report.md") -> None:
        """
        生成完整的迁移报告

        Args:
            output_file: 输出文件名
        """
        report = f"""# DesignTokens 迁移报告

## 📊 总体统计

- **分析文件数**: {len(self.issues)}
- **发现硬编码**: {len(self.issues)} 处
- **颜色硬编码**: {sum(1 for i in self.issues if i.item_type == 'color')} 处
- **字体硬编码**: {sum(1 for i in self.issues if i.item_type == 'font_size')} 处

## 📝 详细列表

| 文件 | 行号 | 类型 | 当前值 | 建议替换 | 置信度 |
|------|------|------|--------|----------|--------|
"""

        for item in self.issues[:50]:  # 只显示前50个
            short_path = item.file_path.split("equipment management")[-1]
            report += f"| `{short_path}` | L{item.line_number} | {item.item_type} | `{item.value}` | {item.suggested_replacement} | {item.confidence:.0%} |\n"

        if len(self.issues) > 50:
            report += f"\n... 还有 {len(self.issues) - 50} 个项目未显示\n"

        report += """

## 🚀 迁移步骤

### 第一阶段：颜色常量 (高优先级)

1. 在文件顶部添加导入:
```python
from ui.design_tokens import DT
```

2. 替换颜色值:
```python
# 修改前
label.setStyleSheet("color: #24292F;")

# 修改后
label.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
```

### 第二阶段：字体样式 (中优先级)

```python
# 修改前
label.setFont(QFont("", 16, QFont.Weight.Bold))

# 修改后
label.setFont(DT.Typography.get_font(*DT.T.TITLE_MEDIUM))
```

### 第三阶段：间距和圆角 (低优先级)

```python
# 修改前
layout.setContentsMargins(16, 16, 16, 16)

# 修改后
layout.setContentsMargins(DT.S.MD, DT.S.MD, DT.S.MD, DT.S.MD)
```
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info("迁移报告已生成: %s", output_file)


def quick_scan(directory: str = "ui") -> None:
    """快速扫描并打印摘要"""
    migrator = TokenMigrator()
    result = migrator.analyze_directory(directory)

    print("\n" + "=" * 60)
    print("🎨 DesignTokens 硬编码扫描结果")
    print("=" * 60)
    print(f"\n📂 扫描目录: {directory}")
    print(f"📄 分析文件: {result.get('files_analyzed', 0)} 个")
    print(f"⚠️ 发现问题: {result.get('total_issues', 0)} 处")

    print("\n📊 分类统计:")
    for detail in result.get("details", []):
        short_file = detail["file"].split("equipment management")[-1]
        print(f"   • {short_file}: {detail['total_issues']} 个问题")

    if result.get("total_issues", 0) > 0:
        print("\n💡 使用以下命令生成详细迁移报告:")
        print("   from ui.migration_helper import quick_scan, TokenMigrator")
        print("   migrator = TokenMigrator()")
        print("   migrator.generate_migration_report()")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    quick_scan()
