"""
性能测试工具 - PerformanceTester
用于测试UI组件性能、内存使用、渲染速度等指标
"""

import statistics
import sys
import time
import tracemalloc
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

import psutil


@dataclass
class PerformanceMetric:
    """性能指标数据类"""

    name: str
    duration: float  # 执行时间（秒）
    memory_before: int  # 峰值内存前（字节）
    memory_after: int  # 峰值内存后（字节）
    memory_delta: int  # 内存增长（字节）
    peak_memory: int  # 峰值内存（字节）
    cpu_percent: float  # CPU使用率（%）
    success: bool  # 是否成功
    error: str = ""  # 错误信息


class PerformanceStats:
    """性能统计类"""

    def __init__(self, max_samples: int = 100):
        self.max_samples = max_samples
        self.metrics: deque = deque(maxlen=max_samples)
        self._process = psutil.Process()

    def add_metric(self, metric: PerformanceMetric) -> None:
        """添加性能指标"""
        self.metrics.append(metric)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.metrics:
            return {}

        durations = [m.duration for m in self.metrics]
        memory_deltas = [m.memory_delta for m in self.metrics]
        cpu_percents = [m.cpu_percent for m in self.metrics]

        return {
            "total_samples": len(self.metrics),
            "duration": {
                "min": min(durations),
                "max": max(durations),
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "std": statistics.stdev(durations) if len(durations) > 1 else 0,
            },
            "memory_delta": {
                "min": min(memory_deltas),
                "max": max(memory_deltas),
                "mean": statistics.mean(memory_deltas),
                "total": sum(memory_deltas),
            },
            "cpu_percent": {
                "min": min(cpu_percents),
                "max": max(cpu_percents),
                "mean": statistics.mean(cpu_percents),
            },
            "success_rate": sum(1 for m in self.metrics if m.success) / len(self.metrics),
        }

    def get_current_memory(self) -> int:
        """获取当前内存使用（字节）"""
        return self._process.memory_info().rss

    def get_current_cpu(self) -> float:
        """获取当前CPU使用率（%）"""
        return self._process.cpu_percent()


class PerformanceTester:
    """性能测试器"""

    def __init__(self, max_samples: int = 100):
        self.stats = PerformanceStats(max_samples)
        self._process = psutil.Process()

    def measure(self, func: Callable[..., Any], name: str, *args, **kwargs) -> PerformanceMetric:
        """
        测量函数执行性能

        Args:
            func: 要测试的函数
            name: 测试名称
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            PerformanceMetric: 性能指标
        """
        # 开始内存跟踪
        tracemalloc.start()

        # 记录开始状态
        start_time = time.time()
        start_memory = self._process.memory_info().rss
        peak_memory = tracemalloc.get_traced_memory()[0]
        start_cpu = self._process.cpu_percent()

        success = True
        error_msg = ""

        try:
            # 执行函数
            result = func(*args, **kwargs)
        except Exception as e:
            success = False
            error_msg = str(e)
        finally:
            # 记录结束状态
            end_time = time.time()
            end_memory = self._process.memory_info().rss
            final_peak_memory = tracemalloc.get_traced_memory()[0]
            tracemalloc.stop()

            # 计算CPU使用率（需要间隔时间）
            time.sleep(0.01)  # 小延迟以获得CPU百分比
            end_cpu = self._process.cpu_percent()

            # 创建性能指标
            metric = PerformanceMetric(
                name=name,
                duration=end_time - start_time,
                memory_before=start_memory,
                memory_after=end_memory,
                memory_delta=end_memory - start_memory,
                peak_memory=max(final_peak_memory, peak_memory),
                cpu_percent=end_cpu - start_cpu,
                success=success,
                error=error_msg,
            )

            # 添加到统计
            self.stats.add_metric(metric)

        return metric

    def benchmark(
        self, func: Callable[..., Any], iterations: int = 10, name: str = "benchmark", *args, **kwargs
    ) -> Dict[str, Any]:
        """
        基准测试 - 多次执行函数并统计

        Args:
            func: 要测试的函数
            iterations: 迭代次数
            name: 测试名称
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            统计信息字典
        """
        print(f"\n{'=' * 60}")
        print(f"基准测试: {name}")
        print(f"迭代次数: {iterations}")
        print(f"{'=' * 60}")

        for i in range(iterations):
            metric_name = f"{name}_iteration_{i}"
            metric = self.measure(func, metric_name, *args, **kwargs)

            status = "✓" if metric.success else "✗"
            print(
                f"{status} 迭代 {i+1}/{iterations}: "
                f"时间={metric.duration*1000:.2f}ms, "
                f"内存={metric.memory_delta/1024:.2f}KB, "
                f"CPU={metric.cpu_percent:.1f}%"
            )

            if not metric.success:
                print(f"  错误: {metric.error}")

        # 获取统计信息
        stats = self.stats.get_statistics()
        self._print_statistics(stats)

        return stats

    def stress_test(
        self, func: Callable[..., Any], duration: float, name: str = "stress_test", *args, **kwargs
    ) -> Dict[str, Any]:
        """
        压力测试 - 在指定时间内持续执行函数

        Args:
            func: 要测试的函数
            duration: 测试持续时间（秒）
            name: 测试名称
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            统计信息字典
        """
        print(f"\n{'=' * 60}")
        print(f"压力测试: {name}")
        print(f"持续时间: {duration}秒")
        print(f"{'=' * 60}")

        start_time = time.time()
        iteration = 0

        while (time.time() - start_time) < duration:
            metric_name = f"{name}_iteration_{iteration}"
            metric = self.measure(func, metric_name, *args, **kwargs)

            if iteration % 10 == 0:  # 每10次打印一次
                print(
                    f"迭代 {iteration}: "
                    f"时间={metric.duration*1000:.2f}ms, "
                    f"内存={metric.memory_delta/1024:.2f}KB"
                )

            iteration += 1

        print(f"\n总计执行: {iteration} 次")
        print(f"平均吞吐量: {iteration/duration:.2f} 次/秒")

        # 获取统计信息
        stats = self.stats.get_statistics()
        self._print_statistics(stats)

        return stats

    def memory_leak_test(
        self, func: Callable[..., Any], iterations: int = 100, name: str = "memory_leak_test", *args, **kwargs
    ) -> Dict[str, Any]:
        """
        内存泄漏测试 - 检测函数是否存在内存泄漏

        Args:
            func: 要测试的函数
            iterations: 迭代次数
            name: 测试名称
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            包含内存泄漏分析的字典
        """
        print(f"\n{'=' * 60}")
        print(f"内存泄漏测试: {name}")
        print(f"迭代次数: {iterations}")
        print(f"{'=' * 60}")

        memory_deltas: List[int] = []
        peak_memories: List[int] = []

        for i in range(iterations):
            metric_name = f"{name}_iteration_{i}"
            metric = self.measure(func, metric_name, *args, **kwargs)

            memory_deltas.append(metric.memory_delta)
            peak_memories.append(metric.peak_memory)

            if i % 10 == 0:
                print(
                    f"迭代 {i}: 内存增长={metric.memory_delta/1024:.2f}KB, "
                    f"峰值内存={metric.peak_memory/1024/1024:.2f}MB"
                )

        # 分析内存趋势
        # 使用线性回归检测内存增长趋势
        if len(peak_memories) > 2:
            x = list(range(len(peak_memories)))
            y = peak_memories

            # 简单线性回归
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_x2 = sum(xi * xi for xi in x)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n

            print(f"\n内存趋势分析:")
            print(f"  斜率（每次迭代内存变化）: {slope/1024:.2f} KB/迭代")

            if slope > 1024:  # 每次迭代增长超过1KB，可能存在泄漏
                print(f"  ⚠️  警告: 检测到潜在内存泄漏!")
            else:
                print(f"  ✓ 内存稳定，未检测到明显泄漏")

            # 预测1000次迭代后的内存
            predicted_memory = slope * 1000 + intercept
            print(f"  预测1000次迭代后内存: {predicted_memory/1024/1024:.2f} MB")

        return {
            "memory_deltas": memory_deltas,
            "peak_memories": peak_memories,
            "total_delta": sum(memory_deltas),
            "slope": slope if "slope" in locals() else 0,
        }

    def _print_statistics(self, stats: Dict[str, Any]) -> None:
        """打印统计信息"""
        print(f"\n{'=' * 60}")
        print(f"统计结果:")
        print(f"{'=' * 60}")

        if "duration" in stats:
            d = stats["duration"]
            print(f"执行时间 (ms):")
            print(f"  最小: {d['min']*1000:.2f}ms")
            print(f"  最大: {d['max']*1000:.2f}ms")
            print(f"  平均: {d['mean']*1000:.2f}ms")
            print(f"  中位数: {d['median']*1000:.2f}ms")
            print(f"  标准差: {d['std']*1000:.2f}ms")

        if "memory_delta" in stats:
            m = stats["memory_delta"]
            print(f"\n内存增长 (KB):")
            print(f"  最小: {m['min']/1024:.2f}KB")
            print(f"  最大: {m['max']/1024:.2f}KB")
            print(f"  平均: {m['mean']/1024:.2f}KB")
            print(f"  总计: {m['total']/1024:.2f}KB")

        if "cpu_percent" in stats:
            c = stats["cpu_percent"]
            print(f"\nCPU使用率 (%):")
            print(f"  最小: {c['min']:.2f}%")
            print(f"  最大: {c['max']:.2f}%")
            print(f"  平均: {c['mean']:.2f}%")

        if "success_rate" in stats:
            print(f"\n成功率: {stats['success_rate']*100:.2f}%")

        print(f"{'=' * 60}\n")

    def reset(self) -> None:
        """重置统计"""
        self.stats.metrics.clear()


# 快捷函数
def quick_measure(func: Callable[..., Any], *args, **kwargs) -> PerformanceMetric:
    """快速测量单个函数性能"""
    tester = PerformanceTester()
    return tester.measure(func, func.__name__, *args, **kwargs)


def quick_benchmark(func: Callable[..., Any], iterations: int = 10, *args, **kwargs) -> Dict[str, Any]:
    """快速基准测试"""
    tester = PerformanceTester()
    return tester.benchmark(func, iterations, func.__name__, *args, **kwargs)


if __name__ == "__main__":
    # 示例：测试一个简单函数
    def test_function(n: int) -> int:
        """测试函数 - 计算斐波那契数列"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    tester = PerformanceTester()

    # 基准测试
    stats = tester.benchmark(test_function, 10, "fibonacci_benchmark", 10000)

    # 压力测试
    tester.reset()
    stats = tester.stress_test(test_function, 5, "fibonacci_stress", 1000)

    # 内存泄漏测试
    tester.reset()
    result = tester.memory_leak_test(test_function, 50, "fibonacci_memory", 5000)
