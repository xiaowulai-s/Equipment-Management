"""
步骤4.3 数据采集引擎 - 验证测试

覆盖范围:
    1. CollectorStats: 统计记录/重置/序列化/线程安全
    2. reg_type_is_bit: 辅助函数
    3. create_protocol: 协议工厂
    4. PollWorker: 创建/信号/停止/写入/字节提取
    5. DataCollector: 生命周期/启停/单设备控制/写入/统计/查询
    6. 边界测试

注意: 使用 unittest.mock 模拟协议层, 不依赖实际设备
"""

import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0
failures = []


def test(name, condition):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        failures.append(name)
        print(f"  FAIL: {name}")


# ── 准备 Qt 环境 ──
from PySide6.QtCore import QCoreApplication

app = QCoreApplication.instance()
if app is None:
    app = QCoreApplication(sys.argv)

from unittest.mock import MagicMock

from src.device.data_collector import CollectorStats, DataCollector, PollWorker, create_protocol, reg_type_is_bit
from src.device.device import Device, PollConfig, SerialParams, TcpParams
from src.device.device_manager import DeviceManager
from src.device.register import Register
from src.protocols.base_protocol import ReadResult, WriteResult
from src.protocols.enums import DataType, DeviceStatus, FunctionCode, ProtocolType, RegisterType

# ═══════════════════════════════════════════════════════════
# 第1节: CollectorStats
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("第1节: CollectorStats")
print("=" * 60)

stats = CollectorStats()
test("Stats初始: success_rate=100", stats.success_rate == 100.0)
test("Stats初始: uptime=0", stats.uptime_seconds == 0.0)
test("Stats初始: total_polls=0", stats.to_dict()["total_polls"] == 0)

stats.start()
stats.record_poll(True, 10, 5.0)
stats.record_poll(True, 10, 8.0)
stats.record_poll(False, 0, 0.0)
d = stats.to_dict()
test("Stats: total_polls=3", d["total_polls"] == 3)
test("Stats: success_polls=2", d["success_polls"] == 2)
test("Stats: failed_polls=1", d["failed_polls"] == 1)
test("Stats: success_rate≈66.67", abs(d["success_rate"] - 66.67) < 0.1)
test("Stats: total_registers_read=20", d["total_registers_read"] == 20)
test("Stats: avg_latency≈6.5", abs(d["avg_latency_ms"] - 6.5) < 0.1)
test("Stats: uptime>0", d["uptime_seconds"] > 0)

stats.record_write(True)
stats.record_write(True)
stats.record_write(False)
d2 = stats.to_dict()
test("Stats: total_writes=3", d2["total_writes"] == 3)
test("Stats: write_successes=2", d2["write_successes"] == 2)
test("Stats: write_failures=1", d2["write_failures"] == 1)

stats.reset()
d3 = stats.to_dict()
test("Stats重置: total_polls=0", d3["total_polls"] == 0)
test("Stats重置: uptime=0", d3["uptime_seconds"] == 0.0)

stats5 = CollectorStats()
stats5.start()
stats5.record_poll(True, 5, 1.0)
j = json.dumps(stats5.to_dict())
test("Stats序列化: JSON", "success_rate" in j)

# 边界
stats_fail = CollectorStats()
stats_fail.record_poll(False, 0, 0.0)
test("全部失败: success_rate=0", stats_fail.success_rate == 0.0)

stats_ok = CollectorStats()
stats_ok.record_poll(True, 10, 1.0)
test("全部成功: success_rate=100", stats_ok.success_rate == 100.0)

stats_ut = CollectorStats()
test("uptime未start=0", stats_ut.uptime_seconds == 0.0)

stats_ns = CollectorStats()
stats_ns.record_poll(True, 5, 1.0)
test("Stats未启动: 可以记录", stats_ns.to_dict()["total_polls"] == 1)
test("Stats未启动: uptime=0", stats_ns.uptime_seconds == 0.0)

# 延迟采样窗口 (101次采样, 只保留100个)
stats_lat = CollectorStats()
stats_lat.start()
for i in range(101):
    stats_lat.record_poll(True, 1, float(i))
d_lat = stats_lat.to_dict()
test("延迟窗口: total=101", d_lat["total_polls"] == 101)
test("延迟窗口: avg≈50.5", abs(d_lat["avg_latency_ms"] - 50.5) < 0.1)

# 多次reset
stats_mr = CollectorStats()
stats_mr.record_poll(True, 1, 1.0)
stats_mr.reset()
stats_mr.record_poll(True, 2, 2.0)
test("多次reset: total=1", stats_mr.to_dict()["total_polls"] == 1)


# ═══════════════════════════════════════════════════════════
# 第2节: CollectorStats 线程安全
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第2节: 线程安全")
print("=" * 60)

stats_ts = CollectorStats()
stats_ts.start()
errors_ts = []


def poll_thread():
    try:
        for i in range(50):
            stats_ts.record_poll(True, 10, float(i))
    except Exception as e:
        errors_ts.append(str(e))


threads = [threading.Thread(target=poll_thread) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=5)

d_ts = stats_ts.to_dict()
test("线程安全: total_polls=250", d_ts["total_polls"] == 250)
test("线程安全: success_polls=250", d_ts["success_polls"] == 250)
test("线程安全: no errors", len(errors_ts) == 0)


# ═══════════════════════════════════════════════════════════
# 第3节: reg_type_is_bit
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第3节: reg_type_is_bit")
print("=" * 60)

test("reg_type_is_bit(0x01)=True", reg_type_is_bit(0x01))
test("reg_type_is_bit(0x02)=True", reg_type_is_bit(0x02))
test("reg_type_is_bit(0x03)=False", not reg_type_is_bit(0x03))
test("reg_type_is_bit(0x04)=False", not reg_type_is_bit(0x04))
test("reg_type_is_bit(0x05)=False", not reg_type_is_bit(0x05))
test("reg_type_is_bit(0x06)=False", not reg_type_is_bit(0x06))


# ═══════════════════════════════════════════════════════════
# 第4节: create_protocol 工厂
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第4节: create_protocol")
print("=" * 60)

dev_tcp = Device(
    name="TCP设备",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="192.168.1.100", port=502),
)
proto = create_protocol(dev_tcp)
test("create_protocol: TCP类型", proto.protocol_type == ProtocolType.MODBUS_TCP)
test("create_protocol: 有效", proto is not None)

dev_rtu = Device(
    name="RTU设备",
    protocol_type=ProtocolType.MODBUS_RTU,
    slave_id=1,
    serial_params=SerialParams(port="COM3", baud_rate=9600),
)
proto_rtu = create_protocol(dev_rtu)
test("create_protocol: RTU类型", proto_rtu.protocol_type == ProtocolType.MODBUS_RTU)

dev_ascii = Device(
    name="ASCII设备",
    protocol_type=ProtocolType.MODBUS_ASCII,
    slave_id=1,
    serial_params=SerialParams(port="COM4", baud_rate=9600),
)
proto_ascii = create_protocol(dev_ascii)
test("create_protocol: ASCII类型", proto_ascii.protocol_type == ProtocolType.MODBUS_ASCII)


# ═══════════════════════════════════════════════════════════
# 第5节: Mock协议 + PollWorker
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第5节: PollWorker")
print("=" * 60)


def make_mock_protocol(connected=False):
    proto = MagicMock()
    proto.is_connected = connected
    proto.protocol_type = ProtocolType.MODBUS_TCP
    proto.connect_to_device = MagicMock()
    proto.disconnect_from_device = MagicMock()
    proto.read_holding_registers = MagicMock(
        return_value=ReadResult(
            function_code=0x03,
            start_address=0,
            values=[100, 200, 300],
            raw_data=b"\x00\x64\x00\xc8\x01\x2c",
            success=True,
        )
    )
    proto.read_coils = MagicMock(
        return_value=ReadResult(
            function_code=0x01,
            start_address=0,
            values=[1, 0, 1],
            raw_data=b"\x05",
            success=True,
        )
    )
    proto.read_input_registers = MagicMock(
        return_value=ReadResult(
            function_code=0x04,
            start_address=0,
            values=[500, 600],
            raw_data=b"\x01\xf4\x02\x58",
            success=True,
        )
    )
    proto.read_discrete_inputs = MagicMock(
        return_value=ReadResult(
            function_code=0x02,
            start_address=0,
            values=[0, 1],
            raw_data=b"\x02",
            success=True,
        )
    )
    proto.write_single_register = MagicMock(
        return_value=WriteResult(
            function_code=0x06,
            address=0,
            value=100,
            success=True,
        )
    )
    proto.write_single_coil = MagicMock(
        return_value=WriteResult(
            function_code=0x05,
            address=0,
            value=1,
            success=True,
        )
    )
    return proto


mock_proto = make_mock_protocol()
test("Mock协议: 创建成功", mock_proto is not None)
test("Mock协议: 默认未连接", not mock_proto.is_connected)

dev_pw = Device(
    name="PW设备",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="127.0.0.1"),
    poll_config=PollConfig(interval_ms=200, timeout_ms=500, retry_count=0),
)
dev_pw.add_register(Register(name="R1", address=0))
dev_pw.add_register(Register(name="R2", address=1))
mock_pw = make_mock_protocol()

pw = PollWorker(device=dev_pw, protocol=mock_pw, poll_interval_ms=100, timeout_ms=500, retry_count=0)
test("PollWorker: device_id", pw.device_id == dev_pw.id)

# 写入 (未连接)
mock_pw.is_connected = False
result = pw.write_register("R1", 100)
test("写入: 未连接失败", not result.success)

# 写入 (连接)
mock_pw.is_connected = True
result2 = pw.write_register("R1", 50)
test("写入: 连接时成功", result2.success)

# 写入不存在的寄存器
result3 = pw.write_register("R999", 100)
test("写入: 不存在返回失败", not result3.success)

# 写入只读寄存器
dev_ro = Device(
    name="RO设备", protocol_type=ProtocolType.MODBUS_TCP, slave_id=1, tcp_params=TcpParams(host="127.0.0.1")
)
dev_ro.add_register(Register(name="RO_REG", address=0, read_only=True))
pw_ro = PollWorker(device=dev_ro, protocol=make_mock_protocol(connected=True))
test("写入: 只读失败", not pw_ro.write_register("RO_REG", 100).success)
test("写入: R1可写", dev_pw.get_register("R1").writable)

# stop
pw2 = PollWorker(device=dev_pw, protocol=mock_pw, poll_interval_ms=200)
pw2.stop()
test("PollWorker: stop_flag已设置", pw2._stop_flag.is_set())


# ═══════════════════════════════════════════════════════════
# 第6节: _extract_register_bytes
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第6节: _extract_register_bytes")
print("=" * 60)

dev_ext = Device(name="Ext", protocol_type=ProtocolType.MODBUS_TCP, slave_id=1, tcp_params=TcpParams(host="127.0.0.1"))
pw_ext = PollWorker(device=dev_ext, protocol=make_mock_protocol(), poll_interval_ms=200)
raw = b"\x00\x01\x00\x02\x00\x03\x00\x04"

test("extract: 0,2", pw_ext._extract_register_bytes(raw, 0, 2) == b"\x00\x01\x00\x02")
test("extract: 2,2", pw_ext._extract_register_bytes(raw, 2, 2) == b"\x00\x03\x00\x04")
test("extract: 越界", pw_ext._extract_register_bytes(raw, 3, 2) == b"\x00\x04")
test("extract: 空", pw_ext._extract_register_bytes(b"", 0, 2) == b"")
test("extract: 负偏移", pw_ext._extract_register_bytes(raw, -1, 2) == b"")
test("extract: 1,1", pw_ext._extract_register_bytes(raw, 1, 1) == b"\x00\x02")


# ═══════════════════════════════════════════════════════════
# 第7节: DataCollector 生命周期 (最小等待)
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第7节: DataCollector 生命周期")
print("=" * 60)

mgr = DeviceManager()
collector = DataCollector(mgr)
test("Collector: not running", not collector.is_running)
test("Collector: devices=0", collector.active_device_count == 0)
test("Collector: stats空", collector.stats["total_polls"] == 0)

# 空启动
collector.start()
test("Collector空启动: not running", not collector.is_running)

# 添加设备
dev1 = Device(
    name="D1",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="127.0.0.1", port=502),
    poll_config=PollConfig(interval_ms=200, timeout_ms=500, retry_count=0),
)
dev1.add_register(Register(name="温度", address=0, scale=0.1, unit="°C"))
mgr.add_device(dev1)

collector.start()
time.sleep(0.05)
test("Collector启动: is_running", collector.is_running)
test("Collector启动: devices=1", collector.active_device_count == 1)

collector.stop()
time.sleep(0.05)
test("Collector停止: not running", not collector.is_running)
test("Collector停止: devices=0", collector.active_device_count == 0)

# 重启
collector.start()
time.sleep(0.05)
test("Collector重启: is_running", collector.is_running)
collector.stop()
time.sleep(0.05)

# repr
test("repr: DataCollector", "DataCollector" in repr(collector))
test("repr: running=False", "running=False" in repr(collector))

# 重复停止不崩溃
collector.stop()
test("重复停止: 不崩溃", True)

# 边界: stop_device 不存在
test("停不存在的设备: False", not collector.stop_device("nonexistent"))

# 边界: write_register 无worker
wr_none = collector.write_register("nonexistent", "R1", 100)
test("无worker写入: 失败", not wr_none.success)


# ═══════════════════════════════════════════════════════════
# 第8节: 单设备控制
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第8节: 单设备控制")
print("=" * 60)

mgr2 = DeviceManager()
for name, sid in [("A", 1), ("B", 2)]:
    d = Device(
        name=f"设备{name}",
        protocol_type=ProtocolType.MODBUS_TCP,
        slave_id=sid,
        tcp_params=TcpParams(host="127.0.0.1"),
        poll_config=PollConfig(interval_ms=200, retry_count=0),
    )
    d.add_register(Register(name="V1", address=0))
    mgr2.add_device(d)
dev_a, dev_b = mgr2.get_all_devices()

col2 = DataCollector(mgr2)
col2.start()
time.sleep(0.05)
test("单控: 启动后2个", col2.active_device_count == 2)

col2.stop_device(dev_a.id)
time.sleep(0.05)
test("单控: 停A后1个", col2.active_device_count == 1)
test("单控: B在轮询", col2.is_device_polling(dev_b.id))
test("单控: A不在轮询", not col2.is_device_polling(dev_a.id))

ok = col2.start_device(dev_a.id)
time.sleep(0.05)
test("单控: 重新启动A成功", ok)
test("单控: 2个设备", col2.active_device_count == 2)

test("单控: 重复启动返回False", not col2.start_device(dev_a.id))
test("单控: 不存在返回False", not col2.start_device("nonexistent"))

col2.restart_device(dev_a.id)
time.sleep(0.05)
test("单控: 重启成功", col2.is_device_polling(dev_a.id))

col2.stop()
time.sleep(0.05)


# ═══════════════════════════════════════════════════════════
# 第9节: 查询方法
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第9节: 查询方法")
print("=" * 60)

mgr_q = DeviceManager()
dev_q1 = Device(
    name="Q设备",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="127.0.0.1"),
    poll_config=PollConfig(interval_ms=200, retry_count=0),
)
dev_q1.add_register(Register(name="Q1", address=0))
mgr_q.add_device(dev_q1)

col_q = DataCollector(mgr_q)
test("查询: is_polling=False", not col_q.is_device_polling(dev_q1.id))
test("查询: polling_devices=[]", col_q.get_polling_devices() == [])
test("查询: device_stats=None(不存在)", col_q.get_device_stats("xxx") is None)

stats_dict = col_q.get_stats()
test("查询: stats有total_polls", "total_polls" in stats_dict)

ds = col_q.get_device_stats(dev_q1.id)
test("查询: device_stats有device_name", ds is not None and ds["device_name"] == "Q设备")
test("查询: device_stats有register_count", ds["register_count"] == 1)
test("查询: device_stats is_polling=False", not ds["is_polling"])

col_q.reset_stats()
test("查询: reset后total=0", col_q.get_stats()["total_polls"] == 0)


# ═══════════════════════════════════════════════════════════
# 第10节: 信号测试 (最小等待)
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第10节: 信号测试")
print("=" * 60)

mgr_s = DeviceManager()
dev_s = Device(
    name="信号设备",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="127.0.0.1"),
    poll_config=PollConfig(interval_ms=100, retry_count=0),
)
dev_s.add_register(Register(name="S1", address=0))
mgr_s.add_device(dev_s)

col_s = DataCollector(mgr_s)
started_signals = []
stopped_signals = []
col_s.started.connect(lambda: started_signals.append(1))
col_s.stopped.connect(lambda: stopped_signals.append(1))

col_s.start()
time.sleep(0.05)
test("信号: started已发射", len(started_signals) >= 1)
test("信号: active=1", col_s.active_device_count == 1)

col_s.stop()
time.sleep(0.05)
test("信号: stopped已发射", len(stopped_signals) >= 1)


# ═══════════════════════════════════════════════════════════
# 第11节: 多设备并行
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第11节: 多设备并行")
print("=" * 60)

mgr_m = DeviceManager()
for i in range(3):
    d = Device(
        name=f"并行{i}",
        protocol_type=ProtocolType.MODBUS_TCP,
        slave_id=i + 1,
        tcp_params=TcpParams(host="127.0.0.1"),
        poll_config=PollConfig(interval_ms=200, retry_count=0),
    )
    d.add_register(Register(name=f"R{i}", address=0))
    mgr_m.add_device(d)

col_m = DataCollector(mgr_m)
col_m.start()
time.sleep(0.05)
test("并行: 3个在轮询", col_m.active_device_count == 3)

polling = col_m.get_polling_devices()
col_m.stop_device(polling[0])
time.sleep(0.05)
test("并行: 停一个后2个", col_m.active_device_count == 2)

col_m.stop()
time.sleep(0.05)
test("并行: 全部停止", col_m.active_device_count == 0)


# ═══════════════════════════════════════════════════════════
# 第12节: 写入路由
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第12节: 写入路由")
print("=" * 60)

mgr_w = DeviceManager()
dev_w = Device(
    name="写入设备",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="127.0.0.1"),
    poll_config=PollConfig(interval_ms=200, retry_count=0),
)
dev_w.add_register(Register(name="WR", address=0, read_only=False))
mgr_w.add_device(dev_w)

col_w = DataCollector(mgr_w)
col_w.start()
time.sleep(0.05)

wr1 = col_w.write_register("nonexistent", "WR", 100)
test("写入路由: 不存在设备失败", not wr1.success)

col_w.stop()
time.sleep(0.05)


# ═══════════════════════════════════════════════════════════
# 第13节: 动态设备管理
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第13节: 动态设备管理")
print("=" * 60)

mgr_dyn = DeviceManager()
dev_dyn1 = Device(
    name="动态1",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="127.0.0.1"),
    poll_config=PollConfig(interval_ms=200, retry_count=0),
)
dev_dyn1.add_register(Register(name="D1", address=0))
mgr_dyn.add_device(dev_dyn1)

col_dyn = DataCollector(mgr_dyn)
col_dyn.start()
time.sleep(0.05)
test("动态: 1个设备", col_dyn.active_device_count == 1)

dev_dyn2 = Device(
    name="动态2",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=2,
    tcp_params=TcpParams(host="127.0.0.1"),
    poll_config=PollConfig(interval_ms=200, retry_count=0),
)
dev_dyn2.add_register(Register(name="D2", address=0))
mgr_dyn.add_device(dev_dyn2)
col_dyn.start_device(dev_dyn2.id)
time.sleep(0.05)
test("动态: 运行中添加后2个", col_dyn.active_device_count == 2)

col_dyn.stop_device(dev_dyn1.id)
time.sleep(0.05)
test("动态: 移除后1个", col_dyn.active_device_count == 1)
col_dyn.stop()
time.sleep(0.05)


# ═══════════════════════════════════════════════════════════
# 第14节: PollWorker 线程运行
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("第14节: PollWorker 线程")
print("=" * 60)

dev_thr = Device(
    name="线程设备",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    tcp_params=TcpParams(host="127.0.0.1"),
    poll_config=PollConfig(interval_ms=100, retry_count=0),
)
dev_thr.add_register(Register(name="T1", address=0))

mock_thr = make_mock_protocol(connected=True)
pw_thr = PollWorker(device=dev_thr, protocol=mock_thr, poll_interval_ms=50, timeout_ms=500, retry_count=0)

status_list = []
pw_thr.status_changed.connect(lambda did, st: status_list.append((did, st)))

pw_thr.start()
time.sleep(0.15)
pw_thr.stop()
pw_thr.wait(3000)

test("线程: 已完成", pw_thr.isFinished())
test("线程: 有状态变更(DISC)", len(status_list) >= 1)


# ═══════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
total = passed + failed
print(f"总计: {total}  PASS: {passed}  FAIL: {failed}")
if failures:
    print("失败项:")
    for f in failures:
        print(f"  - {f}")
if failed == 0:
    print("ALL PASSED ✓")
else:
    print(f"WARNING: {failed} 项测试失败!")
print("=" * 60)
