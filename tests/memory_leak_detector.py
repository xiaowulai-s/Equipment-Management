"""
内存泄漏检测工具 - MemoryLeakDetector
专门用于检测Python/PyQt应用中的内存泄漏问题
"""

import gc
import inspect
import sys
import tracemalloc
import weakref
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import psutil


@dataclass
class MemorySnapshot:
    """内存快照"""

    name: str
    timestamp: float
    rss: int  # 进程内存（字节）
    peak_memory: int  # 峰值内存（字节）
    object_count: int  # 对象总数
    reference_count: int  # 引用计数（近似值）


class MemoryLeakDetector:
    """内存泄漏检测器"""

    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self._process = psutil.Process()
        self._weak_refs: Dict[str, List[weakref.ref]] = defaultdict(list)

    def start_tracking(self):
        """开始内存跟踪"""
        tracemalloc.start()
        gc.collect()  # 强制垃圾回收

    def stop_tracking(self):
        """停止内存跟踪"""
        tracemalloc.stop()

    def take_snapshot(self, name: str) -> MemorySnapshot:
        """
        拍摄内存快照

        Args:
            name: 快照名称

        Returns:
            MemorySnapshot: 内存快照
        """
        gc.collect()  # 先执行垃圾回收

        snapshot = MemorySnapshot(
            name=name,
            timestamp=psutil.time.time(),
            rss=self._process.memory_info().rss,
            peak_memory=tracemalloc.get_traced_memory()[0],
            object_count=len(gc.get_objects()),
            reference_count=0,  # 引用计数难以准确获取
        )

        self.snapshots.append(snapshot)
        return snapshot

    def analyze_memory_growth(self, start_idx: int = 0, end_idx: Optional[int] = None) -> Dict[str, Any]:
        """
        分析内存增长

        Args:
            start_idx: 起始快照索引
            end_idx: 结束快照索引（None表示最后一个）

        Returns:
            分析结果字典
        """
        if end_idx is None:
            end_idx = len(self.snapshots) - 1

        if start_idx >= len(self.snapshots) or end_idx >= len(self.snapshots):
            return {"error": "Invalid snapshot indices"}

        start = self.snapshots[start_idx]
        end = self.snapshots[end_idx]

        # 计算内存增长
        rss_growth = end.rss - start.rss
        peak_growth = end.peak_memory - start.peak_memory
        object_growth = end.object_count - start.object_count
        time_elapsed = end.timestamp - start.timestamp

        # 计算增长率
        rss_growth_rate = rss_growth / time_elapsed if time_elapsed > 0 else 0
        object_growth_rate = object_growth / time_elapsed if time_elapsed > 0 else 0

        # 线性回归分析
        slope, intercept = self._calculate_trend(
            [s.timestamp for s in self.snapshots[start_idx : end_idx + 1]],
            [s.rss for s in self.snapshots[start_idx : end_idx + 1]],
        )

        # 判断是否存在泄漏
        is_leaking = slope > 0 and abs(slope) > 1024  # 每秒增长超过1KB

        return {
            "start_snapshot": start.name,
            "end_snapshot": end.name,
            "time_elapsed": time_elapsed,
            "rss_growth": rss_growth,
            "rss_growth_rate": rss_growth_rate,
            "peak_growth": peak_growth,
            "object_growth": object_growth,
            "object_growth_rate": object_growth_rate,
            "trend_slope": slope,  # 内存变化斜率
            "is_leaking": is_leaking,
            "severity": self._assess_severity(slope) if is_leaking else "none",
        }

    def compare_snapshots(self, name1: str, name2: str) -> Dict[str, Any]:
        """
        比较两个快照

        Args:
            name1: 第一个快照名称
            name2: 第二个快照名称

        Returns:
            比较结果
        """
        snap1 = next((s for s in self.snapshots if s.name == name1), None)
        snap2 = next((s for s in self.snapshots if s.name == name2), None)

        if not snap1 or not snap2:
            return {"error": "Snapshot not found"}

        return {
            "snapshot1": snap1.name,
            "snapshot2": snap2.name,
            "time_diff": snap2.timestamp - snap1.timestamp,
            "rss_diff": snap2.rss - snap1.rss,
            "object_count_diff": snap2.object_count - snap1.object_count,
        }

    def get_top_memory_allocations(self, limit: int = 10) -> List[tuple]:
        """
        获取内存分配最多的位置

        Args:
            limit: 返回数量限制

        Returns:
            (filename, lineno, size) 列表
        """
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")[:limit]

        return [
            (stat.traceback[0].filename, stat.traceback[0].lineno, stat.size / 1024) for stat in top_stats  # 转换为KB
        ]

    def detect_object_retention(self, obj: Any, label: str = "object") -> None:
        """
        检测对象是否被保留（未释放）

        Args:
            obj: 要检测的对象
            label: 对象标签
        """
        weak_ref = weakref.ref(obj)
        self._weak_refs[label].append(weak_ref)

        # 定期检查引用是否还存在
        # 注意：弱引用不会阻止对象被回收

    def check_retained_objects(self) -> Dict[str, int]:
        """
        检查被保留的对象

        Returns:
            {label: count} 字典
        """
        result = {}

        for label, refs in self._weak_refs.items():
            # 清理已释放的引用
            alive_refs = [ref for ref in refs if ref() is not None]
            result[label] = len(alive_refs)

            # 仍然存活
            self._weak_refs[label] = [weakref.ref(ref()) for ref in alive_refs]

        return result

    def trace_object_references(self, obj: Any, max_depth: int = 5) -> List[str]:
        """
        追踪对象引用链

        Args:
            obj: 要追踪的对象
            max_depth: 最大深度

        Returns:
            引用链描述列表
        """
        return gc.get_referrers(obj)[:10]  # 返回前10个引用者

    def detect_circular_references(self) -> List[List[Any]]:
        """
        检测循环引用

        Returns:
            循环引用列表
        """
        gc.collect()  # 先执行垃圾回收
        return gc.garbage  # 返回无法回收的对象

    def print_report(self) -> None:
        """打印内存报告"""
        print("\n" + "=" * 80)
        print("内存泄漏检测报告")
        print("=" * 80)

        if len(self.snapshots) < 2:
            print("需要至少2个快照进行分析")
            return

        print(f"\n快照数量: {len(self.snapshots)}")
        print(f"{'名称':<20} {'时间':<15} {'RSS(MB)':<12} {'对象数':<10}")
        print("-" * 80)

        for snap in self.snapshots:
            print(f"{snap.name:<20} {snap.timestamp:<15.2f} " f"{snap.rss/1024/1024:<12.2f} {snap.object_count:<10}")

        # 分析整体趋势
        analysis = self.analyze_memory_growth()
        print("\n" + "-" * 80)
        print("总体分析:")
        print(f"  内存增长: {analysis['rss_growth']/1024/1024:.2f} MB")
        print(f"  时间跨度: {analysis['time_elapsed']:.2f} 秒")
        print(f"  内存增长率: {analysis['rss_growth_rate']/1024:.2f} KB/s")
        print(f"  趋势斜率: {analysis['trend_slope']/1024:.2f} KB/s")
        print(f"  是否泄漏: {'是' if analysis['is_leaking'] else '否'}")

        if analysis["is_leaking"]:
            print(f"  严重程度: {analysis['severity']}")

        # 检查保留的对象
        retained = self.check_retained_objects()
        if retained:
            print("\n" + "-" * 80)
            print("保留的对象:")
            for label, count in retained.items():
                print(f"  {label}: {count}")

        # 检查循环引用
        circular = self.detect_circular_references()
        if circular:
            print("\n" + "-" * 80)
            print(f"检测到 {len(circular)} 个循环引用")

        # 顶级内存分配
        print("\n" + "-" * 80)
        print("顶级内存分配:")
        top_allocs = self.get_top_memory_allocations(5)
        for filename, lineno, size in top_allocs:
            print(f"  {os.path.basename(filename)}:{lineno} - {size:.2f} KB")

        print("=" * 80 + "\n")

    def _calculate_trend(self, x: List[float], y: List[float]) -> tuple:
        """
        计算线性趋势（简单线性回归）

        Returns:
            (slope, intercept) 斜率和截距
        """
        if len(x) != len(y) or len(x) < 2:
            return 0, 0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        return slope, intercept

    def _assess_severity(self, slope: float) -> str:
        """评估泄漏严重程度"""
        slope_kb = slope / 1024

        if slope_kb > 1024:  # > 1MB/s
            return "critical"
        elif slope_kb > 256:  # > 256KB/s
            return "high"
        elif slope_kb > 64:  # > 64KB/s
            return "medium"
        else:
            return "low"


def detect_widget_leaks():
    """
    检测PyQt窗口组件的泄漏

    这是一个常用的场景函数，用于检测QWidget及其子类是否正确释放
    """
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

    detector = MemoryLeakDetector()
    detector.start_tracking()

    # 初始快照
    detector.take_snapshot("initial")

    # 创建并销毁组件
    widgets = []

    def create_and_destroy():
        nonlocal widgets

        # 创建组件
        for i in range(10):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(QLabel(f"Label {i}"))
            widgets.append(widget)

        # 拍摄快照
        detector.take_snapshot(f"created_{len(widgets)}")

        # 销毁组件
        widgets.clear()

        # 拍摄快照
        detector.take_snapshot("destroyed")

        # 强制垃圾回收
        gc.collect()

        # 拍摄最终快照
        detector.take_snapshot("final")

        # 打印报告
        detector.print_report()

    # 延迟执行
    timer = QTimer()
    timer.singleShot(1000, create_and_destroy)

    return detector


if __name__ == "__main__":
    import os

    # 示例：检测内存泄漏
    detector = MemoryLeakDetector()
    detector.start_tracking()

    # 创建对象并跟踪
    objects = []

    detector.take_snapshot("initial")

    for i in range(5):
        # 创建一些对象
        obj = {"id": i, "data": list(range(1000))}
        objects.append(obj)
        detector.take_snapshot(f"iteration_{i}")

    # 清理对象
    objects.clear()
    detector.take_snapshot("after_clear")

    # 垃圾回收
    gc.collect()
    detector.take_snapshot("after_gc")

    # 打印报告
    detector.print_report()

    detector.stop_tracking()
