"""
大数据量场景测试
模拟100+设备、1000+寄存器的大规模场景，测试系统在高负载下的性能
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
import threading
import time
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from performance_tester import PerformanceTester

from src.device.device_model import AlarmConfig, AlarmLevel, DataType, Device, Register, RegisterType
from src.protocols.protocol_types import ProtocolType, SerialParams, TcpParams


@dataclass
class LoadTestScenario:
    """负载测试场景"""

    name: str
    num_devices: int
    num_registers_per_device: int
    update_rate: int  # 更新频率（Hz）
    duration: int  # 测试持续时间（秒）
    description: str


class LargeScalePerformanceTester:
    """大数据量性能测试器"""

    def __init__(self):
        self.tester = PerformanceTester()
        self.devices: Dict[str, Device] = {}
        self.test_results = {}

    def create_test_device(self, device_id: int, num_registers: int) -> Device:
        """
        创建测试设备

        Args:
            device_id: 设备ID
            num_registers: 寄存器数量

        Returns:
            Device: 测试设备
        """
        device_name = f"Device_{device_id:03d}"

        # 创建寄存器
        registers = {}
        for i in range(num_registers):
            reg_name = f"{device_name}_Reg_{i:04d}"

            # 随机选择寄存器类型
            reg_type = random.choice(
                [
                    RegisterType.COIL,
                    RegisterType.DISCRETE_INPUT,
                    RegisterType.INPUT_REGISTER,
                    RegisterType.HOLDING_REGISTER,
                ]
            )

            # 根据类型设置数据类型
            if reg_type in [RegisterType.COIL, RegisterType.DISCRETE_INPUT]:
                data_type = DataType.BOOL
            else:
                data_type = random.choice([DataType.UINT16, DataType.INT16, DataType.FLOAT])

            # 创建报警配置
            alarm_config = None
            if reg_type in [RegisterType.INPUT_REGISTER, RegisterType.HOLDING_REGISTER]:
                # 20%的几率有报警配置
                if random.random() < 0.2:
                    alarm_config = AlarmConfig(
                        enabled=True,
                        high_high=100.0,
                        high=80.0,
                        low=20.0,
                        low_low=10.0,
                        deadband=2.0,
                    )

            register = Register(
                name=reg_name,
                address=i * 100,
                register_type=reg_type,
                data_type=data_type,
                value=0,
                alarm_config=alarm_config,
            )

            registers[reg_name] = register

        # 创建设备
        tcp_params = TcpParams(
            host=f"192.168.1.{device_id % 255}",
            port=502 + (device_id % 100),
            slave_id=device_id % 247,
            timeout=5.0,
            max_retries=3,
            retry_delay=1.0,
        )

        device = Device(
            name=device_name,
            protocol_type=ProtocolType.MODBUS_TCP,
            tcp_params=tcp_params,
            registers=registers,
        )

        return device

    def create_devices_batch(self, num_devices: int, registers_per_device: int) -> None:
        """
        批量创建测试设备

        Args:
            num_devices: 设备数量
            registers_per_device: 每个设备的寄存器数
        """
        print(f"\n创建 {num_devices} 个设备，每个设备 {registers_per_device} 个寄存器...")

        def batch_create():
            devices = {}
            for i in range(num_devices):
                device = self.create_test_device(i, registers_per_device)
                devices[device.name] = device

                if (i + 1) % 10 == 0:
                    print(f"  已创建: {i + 1}/{num_devices} 设备")

            return devices

        # 测量创建性能
        metric = self.tester.measure(batch_create, "create_devices_batch")

        self.devices = batch_create()

        print(f"✓ 设备创建完成")
        print(f"  总设备数: {len(self.devices)}")
        print(f"  总寄存器数: {sum(len(d.registers) for d in self.devices.values())}")
        print(f"  创建耗时: {metric.duration:.2f}s")
        print(f"  内存增长: {metric.memory_delta/1024/1024:.2f}MB")

    def test_device_access_performance(self) -> Dict:
        """测试设备访问性能"""
        print(f"\n{'=' * 80}")
        print("测试1: 设备访问性能")
        print(f"{'=' * 80}")

        self.tester.reset()

        # 随机访问寄存器
        def random_access():
            device_list = list(self.devices.values())
            register_list = []

            for device in device_list:
                register_list.extend(device.registers.values())

            if register_list:
                # 随机读取1000个寄存器
                for _ in range(1000):
                    reg = random.choice(register_list)
                    _ = reg.value

        stats = self.tester.benchmark(random_access, 10, "device_random_access")

        self.test_results["device_access"] = stats
        return stats

    def test_device_update_performance(self) -> Dict:
        """测试设备更新性能"""
        print(f"\n{'=' * 80}")
        print("测试2: 设备更新性能")
        print(f"{'=' * 80}")

        self.tester.reset()

        def batch_update():
            for device in self.devices.values():
                for register in device.registers.values():
                    # 模拟数据更新
                    register.update_value(random.random() * 100)

        stats = self.tester.benchmark(batch_update, 10, "device_batch_update")

        self.test_results["device_update"] = stats
        return stats

    def test_register_search_performance(self) -> Dict:
        """测试寄存器搜索性能"""
        print(f"\n{'=' * 80}")
        print("测试3: 寄存器搜索性能")
        print(f"{'=' * 80}")

        self.tester.reset()

        def search_registers():
            # 按名称搜索
            for device in self.devices.values():
                for register_name in list(device.registers.keys())[:100]:
                    reg = device.registers.get(register_name)
                    if reg:
                        _ = reg.address

        stats = self.tester.benchmark(search_registers, 10, "register_search")

        self.test_results["register_search"] = stats
        return stats

    def test_memory_usage_at_scale(self) -> Dict:
        """测试大规模内存使用"""
        print(f"\n{'=' * 80}")
        print("测试4: 内存使用统计")
        print(f"{'=' * 80}")

        total_devices = len(self.devices)
        total_registers = sum(len(d.registers) for d in self.devices.values())

        # 计算内存占用
        device_size = sum(sys.getsizeof(d) for d in self.devices.values())
        register_size = sum(sum(sys.getsizeof(r) for r in d.registers.values()) for d in self.devices.values())

        memory_info = {
            "total_devices": total_devices,
            "total_registers": total_registers,
            "device_memory_mb": device_size / 1024 / 1024,
            "register_memory_mb": register_size / 1024 / 1024,
            "total_memory_mb": (device_size + register_size) / 1024 / 1024,
            "memory_per_device_kb": device_size / total_devices / 1024 if total_devices > 0 else 0,
            "memory_per_register_b": (device_size + register_size) / total_registers if total_registers > 0 else 0,
        }

        print(f"  总设备数: {memory_info['total_devices']}")
        print(f"  总寄存器数: {memory_info['total_registers']}")
        print(f"  设备内存: {memory_info['device_memory_mb']:.2f}MB")
        print(f"  寄存器内存: {memory_info['register_memory_mb']:.2f}MB")
        print(f"  总内存: {memory_info['total_memory_mb']:.2f}MB")
        print(f"  每设备内存: {memory_info['memory_per_device_kb']:.2f}KB")
        print(f"  每寄存器内存: {memory_info['memory_per_register_b']:.2f}B")

        self.test_results["memory_usage"] = memory_info
        return memory_info

    def test_concurrent_operations(self) -> Dict:
        """测试并发操作性能"""
        print(f"\n{'=' * 80}")
        print("测试5: 并发操作性能")
        print(f"{'=' * 80}")

        self.tester.reset()

        def concurrent_updates():
            threads = []

            def thread_worker(device_list):
                for device in device_list:
                    for register in device.registers.values():
                        register.update_value(random.random() * 100)

            # 创建4个线程
            device_list = list(self.devices.values())
            chunk_size = len(device_list) // 4

            for i in range(4):
                start = i * chunk_size
                end = start + chunk_size if i < 3 else len(device_list)
                thread = threading.Thread(target=thread_worker, args=(device_list[start:end],))
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

        stats = self.tester.benchmark(concurrent_updates, 5, "concurrent_operations")

        self.test_results["concurrent"] = stats
        return stats

    def test_stress_scenario(self, duration: int = 30) -> Dict:
        """
        压力测试场景 - 持续更新所有设备和寄存器

        Args:
            duration: 测试持续时间（秒）
        """
        print(f"\n{'=' * 80}")
        print(f"测试6: 压力测试（{duration}秒）")
        print(f"{'=' * 80}")

        self.tester.reset()

        def stress_work():
            for device in self.devices.values():
                for register in device.registers.values():
                    register.update_value(random.random() * 100)

        stats = self.tester.stress_test(stress_work, duration, "stress_test")

        self.test_results["stress"] = stats
        return stats

    def print_comprehensive_report(self) -> None:
        """打印综合测试报告"""
        print(f"\n\n{'=' * 80}")
        print("大数据量性能测试综合报告")
        print(f"{'=' * 80}")

        if "device_access" in self.test_results:
            print(f"\n设备访问性能: ✓")
        if "device_update" in self.test_results:
            print(f"设备更新性能: ✓")
        if "register_search" in self.test_results:
            print(f"寄存器搜索性能: ✓")
        if "memory_usage" in self.test_results:
            mem = self.test_results["memory_usage"]
            print(f"内存使用:")
            print(f"  - 设备/寄存器: {mem['total_devices']}/{mem['total_registers']}")
            print(f"  - 总内存: {mem['total_memory_mb']:.2f}MB")
        if "concurrent" in self.test_results:
            print(f"并发操作性能: ✓")
        if "stress" in self.test_results:
            print(f"压力测试: ✓")

        print(f"\n{'=' * 80}\n")


def main():
    """主函数"""
    # 定义测试场景
    scenarios = [
        LoadTestScenario(
            name="Small Scale",
            num_devices=10,
            num_registers_per_device=50,
            update_rate=1,
            duration=10,
            description="小规模：10设备×50寄存器=500总寄存器",
        ),
        LoadTestScenario(
            name="Medium Scale",
            num_devices=50,
            num_registers_per_device=100,
            update_rate=5,
            duration=15,
            description="中等规模：50设备×100寄存器=5000总寄存器",
        ),
        LoadTestScenario(
            name="Large Scale",
            num_devices=100,
            num_registers_per_device=200,
            update_rate=10,
            duration=20,
            description="大规模：100设备×200寄存器=20000总寄存器",
        ),
    ]

    # 执行大规模测试
    for scenario in scenarios:
        print(f"\n\n{'=' * 80}")
        print(f"场景: {scenario.name}")
        print(f"描述: {scenario.description}")
        print(f"{'=' * 80}")

        tester = LargeScalePerformanceTester()

        # 创建测试数据
        tester.create_devices_batch(scenario.num_devices, scenario.num_registers_per_device)

        # 执行各种测试
        try:
            tester.test_device_access_performance()
            tester.test_device_update_performance()
            tester.test_register_search_performance()
            tester.test_memory_usage_at_scale()
            tester.test_concurrent_operations()
            tester.test_stress_scenario(5)  # 5秒压力测试

            # 打印报告
            tester.print_comprehensive_report()
        except Exception as e:
            print(f"✗ 测试出错: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
