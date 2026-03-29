"""步骤4.2 设备管理器验证测试"""

import json
import os
import sys
import tempfile

sys.path.insert(0, ".")

passed = 0
failed = 0


def test(description, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {description}")
    else:
        failed += 1
        print(f"  FAIL: {description}")


# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("1. 基本CRUD测试")
print("=" * 60)
from src.device import Device, DeviceManager, Register
from src.device.device import PollConfig, SerialParams, TcpParams
from src.device.register import AlarmConfig
from src.protocols.enums import DataType, DeviceStatus, ProtocolType, RegisterType
from src.utils.exceptions import DeviceConfigError, DeviceDuplicateError, DeviceNotFoundError

mgr = DeviceManager()

dev1 = Device(name="PLC-001", protocol_type=ProtocolType.MODBUS_TCP, slave_id=1)
dev2 = Device(name="PLC-002", protocol_type=ProtocolType.MODBUS_RTU, slave_id=2)
dev3 = Device(name="PLC-003", protocol_type=ProtocolType.MODBUS_TCP, slave_id=3)

# add
mgr.add_device(dev1)
mgr.add_device(dev2)
test("add后count=2", mgr.device_count == 2)
test("has_device(dev1.id)", mgr.has_device(dev1.id))
test("has_device_name('PLC-001')", mgr.has_device_name("PLC-001"))
test("get_device(dev1.id)存在", mgr.get_device(dev1.id) is dev1)
test("get_device_by_name('PLC-001')", mgr.get_device_by_name("PLC-001") is dev1)

# duplicate ID
try:
    mgr.add_device(Device(name="其他", device_id=dev1.id))
    test("重复ID应抛异常", False)
except DeviceDuplicateError:
    test("重复ID抛DeviceDuplicateError", True)

# duplicate name
try:
    mgr.add_device(Device(name="PLC-001"))
    test("重复名称应抛异常", False)
except DeviceDuplicateError:
    test("重复名称抛DeviceDuplicateError", True)

# empty name
try:
    mgr.add_device(Device(name=""))
    test("空名称应抛异常", False)
except DeviceConfigError:
    test("空名称抛DeviceConfigError", True)

# get non-existent
test("get_device('不存在')=None", mgr.get_device("不存在") is None)
test("get_device_by_name('不存在')=None", mgr.get_device_by_name("不存在") is None)

# update
mgr.update_device(dev1.id, description="主控制器", slave_id=5)
test("update: description已更新", mgr.get_device(dev1.id).description == "主控制器")
test("update: slave_id=5", mgr.get_device(dev1.id).slave_id == 5)

# update with invalid value
try:
    mgr.update_device(dev1.id, slave_id=300)
    test("slave_id=300应抛异常", False)
except DeviceConfigError:
    test("update slave_id=300抛DeviceConfigError", True)

# update name (unique check)
mgr.update_device(dev2.id, name="RTU-002")
test("update name: 旧名不存在", not mgr.has_device_name("PLC-002"))
test("update name: 新名存在", mgr.has_device_name("RTU-002"))

# update name conflict
try:
    mgr.update_device(dev1.id, name="RTU-002")
    test("rename冲突应抛异常", False)
except DeviceDuplicateError:
    test("rename冲突抛DeviceDuplicateError", True)

# update non-existent
try:
    mgr.update_device("不存在", name="X")
    test("update不存在的设备应抛异常", False)
except DeviceNotFoundError:
    test("update不存在抛DeviceNotFoundError", True)

# remove
removed = mgr.remove_device(dev1.id)
test("remove返回被移除的设备", removed is dev1)
test("remove后count=1", mgr.device_count == 1)
test("remove后不存在", not mgr.has_device(dev1.id))

# remove non-existent
try:
    mgr.remove_device("不存在")
    test("remove不存在应抛异常", False)
except DeviceNotFoundError:
    test("remove不存在抛DeviceNotFoundError", True)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("2. 搜索与过滤测试")
print("=" * 60)

mgr.clear()
mgr.add_device(
    Device(name="温度控制器", protocol_type=ProtocolType.MODBUS_TCP, tags=["温度", "车间A"], location="车间A-1F")
)
mgr.add_device(
    Device(name="压力控制器", protocol_type=ProtocolType.MODBUS_TCP, tags=["压力", "车间A"], location="车间A-2F")
)
mgr.add_device(
    Device(name="流量计", protocol_type=ProtocolType.MODBUS_RTU, tags=["流量", "车间B"], location="车间B-1F")
)
mgr.add_device(
    Device(name="温度传感器", protocol_type=ProtocolType.MODBUS_RTU, tags=["温度", "车间B"], location="车间B-2F")
)

test("总数=4", mgr.device_count == 4)

# 按名称搜索
r = mgr.find_devices(name="温度")
test("name='温度': 2个", len(r) == 2)
test("name='温度': 包含温度控制器", any(d.name == "温度控制器" for d in r))

r = mgr.find_devices(name="温度控制器")
test("name='温度控制器': 精确匹配1个", len(r) == 1)

# 按协议搜索
r = mgr.find_devices(protocol=ProtocolType.MODBUS_TCP)
test("protocol=TCP: 2个", len(r) == 2)

r = mgr.find_devices(protocol=ProtocolType.MODBUS_RTU)
test("protocol=RTU: 2个", len(r) == 2)

# 按标签搜索
r = mgr.find_devices(tag="温度")
test("tag='温度': 2个", len(r) == 2)

r = mgr.find_devices(tag="车间A")
test("tag='车间A': 2个", len(r) == 2)

# 按位置搜索
r = mgr.find_devices(location="车间B")
test("location='车间B': 2个", len(r) == 2)

# 组合搜索
r = mgr.find_devices(name="温度", protocol=ProtocolType.MODBUS_RTU)
test("温度+RTU: 1个", len(r) == 1)
test("温度+RTU: 温度传感器", r[0].name == "温度传感器")

# 无结果
r = mgr.find_devices(name="不存在")
test("无结果: 0个", len(r) == 0)

# enabled_only
mgr.get_device_by_name("温度控制器").enabled = False
r = mgr.find_devices(enabled_only=True)
test("enabled_only: 3个", len(r) == 3)

# 便捷方法
test("get_devices_by_protocol(TCP)=2", len(mgr.get_devices_by_protocol(ProtocolType.MODBUS_TCP)) == 2)
test("get_devices_by_tag('温度')=2", len(mgr.get_devices_by_tag("温度")) == 2)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("3. 按状态搜索测试")
print("=" * 60)

d1 = mgr.get_device_by_name("温度控制器")
d2 = mgr.get_device_by_name("压力控制器")

d1.set_status(DeviceStatus.CONNECTED)
d2.set_status(DeviceStatus.ERROR)

test("get_connected_devices=1", len(mgr.get_connected_devices()) == 1)
test("get_devices_by_status(ERROR)=1", len(mgr.get_devices_by_status(DeviceStatus.ERROR)) == 1)
test("get_enabled_devices=3", len(mgr.get_enabled_devices()) == 3)

# 报警设备
r1 = Register(name="报警R", alarm_config=AlarmConfig(high=100))
d1.add_register(r1)
d1.update_register_value("报警R", 5000)  # eng=5000 > 100 → 报警
test("get_alarmed_devices=1", len(mgr.get_alarmed_devices()) == 1)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("4. 信号聚合转发测试")
print("=" * 60)

status_signals = []
value_signals = []
alarm_trigger_signals = []
alarm_clear_signals = []

mgr2 = DeviceManager()
mgr2.device_status_changed.connect(lambda did, s: status_signals.append((did, s)))
mgr2.device_value_changed.connect(lambda did, rn, r, e: value_signals.append((did, rn, r, e)))
mgr2.device_alarm_triggered.connect(lambda did, rn, v, l: alarm_trigger_signals.append((did, rn, v, l)))
mgr2.device_alarm_cleared.connect(lambda did, rn, l: alarm_clear_signals.append((did, rn, l)))

dev_t = Device(name="TestDev", slave_id=1)
dev_t.add_register(Register(name="V1", address=0, scale=0.1))
dev_t.add_register(Register(name="V2", address=10, alarm_config=AlarmConfig(high=100)))

mgr2.add_device(dev_t)

# 状态信号
dev_t.set_status(DeviceStatus.CONNECTING)
test("status信号: 1个", len(status_signals) == 1)
test("status信号: dev_id正确", status_signals[0][0] == dev_t.id)
test("status信号: status=CONNECTING", status_signals[0][1] == DeviceStatus.CONNECTING)

# 值信号
dev_t.update_register_value("V1", 100)
test("value信号: 1个", len(value_signals) == 1)
test("value信号: reg_name=V1", value_signals[0][1] == "V1")
test("value信号: raw=100", value_signals[0][2] == 100)

# 报警信号
dev_t.update_register_value("V2", 5000)
test("alarm_trigger: 1个", len(alarm_trigger_signals) == 1)
test("alarm_trigger: dev_id正确", alarm_trigger_signals[0][0] == dev_t.id)
test("alarm_trigger: reg=V2", alarm_trigger_signals[0][1] == "V2")

# 报警清除信号
dev_t.update_register_value("V2", 50)
test("alarm_clear: 1个", len(alarm_clear_signals) == 1)

# 移除设备后信号不再转发
mgr2.remove_device(dev_t.id)
old_count = len(status_signals)
dev_t.set_status(DeviceStatus.CONNECTED)
test("移除后不再转发信号", len(status_signals) == old_count)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("5. 批量操作测试")
print("=" * 60)

mgr3 = DeviceManager()
devices_batch = [
    Device(name="Batch-1", protocol_type=ProtocolType.MODBUS_TCP),
    Device(name="Batch-2", protocol_type=ProtocolType.MODBUS_RTU),
    Device(name="Batch-1", protocol_type=ProtocolType.MODBUS_TCP),  # 重复名称
]

ok, errs = mgr3.add_devices(devices_batch)
test("批量添加: 成功2", ok == 2)
test("批量添加: 失败1", len(errs) == 1)

ok, errs = mgr3.remove_devices(["不存在ID", list(mgr3.devices.keys())[0]])
test("批量移除: 成功1", ok == 1)
test("批量移除: 失败1", len(errs) == 1)

mgr3.clear()
for i in range(5):
    mgr3.add_device(Device(name=f"E{i}", protocol_type=ProtocolType.MODBUS_TCP))
    mgr3.get_device_by_name(f"E{i}").enabled = False

cnt = mgr3.enable_all()
test("enable_all: 5个", cnt == 5)
test("所有已启用", all(d.enabled for d in mgr3))

cnt = mgr3.disable_all()
test("disable_all: 5个", cnt == 5)
test("所有已禁用", all(not d.enabled for d in mgr3))

mgr3.enable_all()
cnt = mgr3.set_all_status(DeviceStatus.CONNECTED)
test("set_all_status(CONNECTED): 5个", cnt == 5)
test("全部已连接", all(d.is_connected for d in mgr3))

# reset + clear
for d in mgr3:
    d.record_poll_success()
    d.record_poll_failure()
mgr3.reset_all_statistics()
test("reset_all_statistics: total=0", all(d.total_polls == 0 for d in mgr3))

mgr3.clear_all_values()
test("clear_all_values: 无异常", True)
test("clear后count=0", mgr3.device_count == 5)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("6. device_count_changed信号测试")
print("=" * 60)

count_signals = []
mgr4 = DeviceManager()
mgr4.device_count_changed.connect(lambda c: count_signals.append(c))

mgr4.add_device(Device(name="C1"))
mgr4.add_device(Device(name="C2"))
mgr4.remove_device(mgr4.get_device_by_name("C1").id)

test("count信号: add+add+remove = 3次", len(count_signals) == 3)
test("count信号值: [1,2,1]", count_signals == [1, 2, 1])

mgr4.clear()
test("clear后count信号", len(count_signals) == 4)  # +1 from clear

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("7. device_added/removed/updated信号测试")
print("=" * 60)

added_signals = []
removed_signals = []
updated_signals = []

mgr5 = DeviceManager()
mgr5.device_added.connect(lambda d: added_signals.append(d.name))
mgr5.device_removed.connect(lambda did: removed_signals.append(did))
mgr5.device_updated.connect(lambda did: updated_signals.append(did))

dev_x = Device(name="X1")
mgr5.add_device(dev_x)
test("added信号: 1个", len(added_signals) == 1)
test("added信号: name=X1", added_signals[0] == "X1")

did = dev_x.id
mgr5.update_device(did, description="updated")
test("updated信号: 1个", len(updated_signals) == 1)
test("updated信号: did正确", updated_signals[0] == did)

mgr5.remove_device(did)
test("removed信号: 1个", len(removed_signals) == 1)
test("removed信号: did正确", removed_signals[0] == did)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("8. 寄存器操作代理测试")
print("=" * 60)

mgr6 = DeviceManager()
dev_r = Device(name="RegDev")
mgr6.add_device(dev_r)

mgr6.add_register_to_device(dev_r.id, Register(name="R1", address=0))
mgr6.add_register_to_device(dev_r.id, Register(name="R2", address=1))

test("通过manager添加寄存器: count=2", dev_r.register_count == 2)

reg = mgr6.get_register(dev_r.id, "R1")
test("get_register: 存在", reg is not None)
test("get_register: name=R1", reg.name == "R1")

test("get_register不存在设备: None", mgr6.get_register("不存在", "R1") is None)

mgr6.remove_register_from_device(dev_r.id, "R1")
test("remove后count=1", dev_r.register_count == 1)

# 不存在设备
try:
    mgr6.add_register_to_device("不存在", Register(name="R"))
    test("不存在的设备应抛异常", False)
except DeviceNotFoundError:
    test("不存在的设备抛DeviceNotFoundError", True)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("9. 统计信息测试")
print("=" * 60)

mgr7 = DeviceManager()
mgr7.add_device(Device(name="D1", protocol_type=ProtocolType.MODBUS_TCP))
mgr7.add_device(Device(name="D2", protocol_type=ProtocolType.MODBUS_TCP))
mgr7.add_device(Device(name="D3", protocol_type=ProtocolType.MODBUS_RTU))

d1 = mgr7.get_device_by_name("D1")
d2 = mgr7.get_device_by_name("D2")
d1.set_status(DeviceStatus.CONNECTED)
d2.set_status(DeviceStatus.ERROR)
d1.add_register(Register(name="R1", address=0))
d1.add_register(Register(name="R2", address=1))
d2.add_register(Register(name="R3", address=0))

stats = mgr7.get_statistics()
test("stats.total=3", stats["total"] == 3)
test("stats.enabled=3", stats["enabled"] == 3)
test("stats.connected=1", stats["connected"] == 1)
test("stats.error=1", stats["error"] == 1)
test("stats.by_protocol: TCP=2", stats["by_protocol"].get("modbus_tcp") == 2)
test("stats.by_protocol: RTU=1", stats["by_protocol"].get("modbus_rtu") == 1)
test("stats.total_registers=3", stats["total_registers"] == 3)

# success_rate
d1.record_poll_success()
d1.record_poll_failure()
test("success_rate=50%", abs(mgr7.get_overall_success_rate() - 50.0) < 0.1)

# 空管理器
mgr_empty = DeviceManager()
stats_empty = mgr_empty.get_statistics()
test("空stats: total=0", stats_empty["total"] == 0)
test("空success_rate=100%", abs(mgr_empty.get_overall_success_rate() - 100.0) < 0.1)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("10. JSON持久化测试")
print("=" * 60)

mgr8 = DeviceManager()
dev_p = Device(
    name="持久化设备",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=10,
    description="测试持久化",
    location="测试位置",
    tags=["持久化"],
)
dev_p.add_register(Register(name="R1", address=0, scale=0.1, unit="MPa"))
dev_p.add_register(Register(name="R2", address=10, data_type=DataType.FLOAT32))
dev_p.update_register_value("R1", 500)  # eng=50.0

mgr8.add_device(dev_p)

# save_to_file
tmpdir = tempfile.mkdtemp()
filepath = os.path.join(tmpdir, "devices.json")
mgr8.save_to_file(filepath)
test("文件已创建", os.path.exists(filepath))

# load_from_file (替换模式)
mgr9 = DeviceManager()
loaded, skipped = mgr9.load_from_file(filepath, merge=False)
test("load: 成功1", loaded == 1)
test("load: 跳过0", skipped == 0)
test("load后count=1", mgr9.device_count == 1)

restored = mgr9.get_device_by_name("持久化设备")
test("load: name正确", restored.name == "持久化设备")
test("load: slave_id=10", restored.slave_id == 10)
test("load: register_count=2", restored.register_count == 2)
test("load: R1 eng=50.0", abs(restored.get_register("R1").engineering_value - 50.0) < 0.1)
test("load: tags=['持久化']", restored.tags == ["持久化"])

# load_from_file (合并模式)
mgr9.add_device(Device(name="额外设备"))
loaded2, _ = mgr9.load_from_file(filepath, merge=True)
test("merge: 跳过1 (名称重复)", loaded2 == 0)
test("merge后count=2", mgr9.device_count == 2)

# load不存在的文件
try:
    mgr9.load_from_file("不存在.json")
    test("不存在文件应抛异常", False)
except FileNotFoundError:
    test("不存在文件抛FileNotFoundError", True)

# export_to_json / import_from_json
json_str = mgr8.export_to_json()
test("export_to_json非空", len(json_str) > 0)

mgr10 = DeviceManager()
loaded3, skipped3 = mgr10.import_from_json(json_str, merge=False)
test("import: 成功1", loaded3 == 1)
test("import后name正确", mgr10.get_device_by_name("持久化设备") is not None)

# 清理
os.remove(filepath)
os.rmdir(tmpdir)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("11. clear与生命周期测试")
print("=" * 60)

mgr11 = DeviceManager()
for i in range(3):
    mgr11.add_device(Device(name=f"CL{i}"))

cnt = mgr11.clear()
test("clear: 移除3个", cnt == 3)
test("clear后count=0", mgr11.device_count == 0)
test("clear后devices为空", len(mgr11.devices) == 0)

# clear空管理器
cnt2 = mgr11.clear()
test("clear空: 0个", cnt2 == 0)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("12. 魔术方法测试")
print("=" * 60)

mgr12 = DeviceManager()
dev_m = Device(name="Magic")
mgr12.add_device(dev_m)

test("len(mgr)=1", len(mgr12) == 1)
test("dev_id in mgr", dev_m.id in mgr12)
test("'不存在' not in mgr", "不存在" not in mgr12)
test("iter: 可迭代", list(mgr12)[0] is dev_m)
test("repr包含count", "1" in repr(mgr12))

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("13. 属性和便捷访问测试")
print("=" * 60)

mgr13 = DeviceManager()
mgr13.add_device(Device(name="A1"))
mgr13.add_device(Device(name="B2"))
mgr13.add_device(Device(name="C3"))

test("device_ids: 3个", len(mgr13.device_ids) == 3)
test("device_names: 3个", len(mgr13.device_names) == 3)
test("device_names包含A1", "A1" in mgr13.device_names)
test("devices: dict副本", isinstance(mgr13.devices, dict))
test("devices: 3个", len(mgr13.devices) == 3)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("14. 空管理器安全操作测试")
print("=" * 60)

mgr14 = DeviceManager()
test("空: count=0", mgr14.device_count == 0)
test("空: get=None", mgr14.get_device("x") is None)
test("空: find=[]", mgr14.find_devices() == [])
test("空: by_protocol=[]", mgr14.get_devices_by_protocol(ProtocolType.MODBUS_TCP) == [])
test("空: by_status=[]", mgr14.get_devices_by_status(DeviceStatus.CONNECTED) == [])
test("空: by_tag=[]", mgr14.get_devices_by_tag("x") == [])
test("空: connected=[]", mgr14.get_connected_devices() == [])
test("空: alarmed=[]", mgr14.get_alarmed_devices() == [])
test("空: enabled=[]", mgr14.get_enabled_devices() == [])
test("空: enable_all=0", mgr14.enable_all() == 0)
test("空: disable_all=0", mgr14.disable_all() == 0)
test("空: set_all_status=0", mgr14.set_all_status(DeviceStatus.CONNECTED) == 0)
test("空: export非空", len(mgr14.export_to_json()) > 0)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("15. 完整集成测试 (多设备+寄存器+报警+持久化)")
print("=" * 60)

# 构建完整场景
mgr_full = DeviceManager()

# 3个设备, 各有不同配置和寄存器
d_temp = Device(name="温度站", protocol_type=ProtocolType.MODBUS_TCP, slave_id=1, tags=["重要"], location="1号车间")
d_temp.add_register(Register(name="T1", address=0, scale=0.1, unit="C", alarm_config=AlarmConfig(high=80, low=10)))
d_temp.add_register(Register(name="T2", address=1, scale=0.1, unit="C"))

d_press = Device(
    name="压力站",
    protocol_type=ProtocolType.MODBUS_RTU,
    slave_id=2,
    serial_params=SerialParams(port="COM3"),
    tags=["重要"],
    location="2号车间",
)
d_press.add_register(Register(name="P1", address=100, scale=0.01, unit="MPa", alarm_config=AlarmConfig(high=1.5)))

d_flow = Device(name="流量站", protocol_type=ProtocolType.MODBUS_TCP, slave_id=3, location="3号车间")
d_flow.add_register(Register(name="F1", address=200, data_type=DataType.UINT32, scale=0.001, unit="m3/h"))

mgr_full.add_device(d_temp)
mgr_full.add_device(d_press)
mgr_full.add_device(d_flow)

# 更新值
d_temp.add_register(Register(name="T3", address=2))
d_temp.update_register_value("T1", 650)  # eng=65.0 (正常)
d_press.update_register_value("P1", 20000)  # eng=200.0 (报警: >1.5)
d_flow.update_register_value("F1", 50000)  # eng=50.0

test("集成: count=3", mgr_full.device_count == 3)
test("集成: d_temp register_count=3", d_temp.register_count == 3)
test("集成: d_temp T1 eng=65.0", abs(d_temp.get_register("T1").engineering_value - 65.0) < 0.1)
test("集成: d_press P1 is_alarmed", d_press.get_register("P1").is_alarmed)

# 统计
stats = mgr_full.get_statistics()
test("集成: stats.total=3", stats["total"] == 3)
test("集成: stats.alarmed=1", stats["alarmed"] == 1)
test("集成: stats.total_registers=5", stats["total_registers"] == 5)

# 搜索
r = mgr_full.find_devices(tag="重要")
test("集成: find(tag=重要)=2", len(r) == 2)

r = mgr_full.find_devices(location="车间")
test("集成: find(location=车间)=3", len(r) == 3)

r = mgr_full.get_alarmed_devices()
test("集成: alarmed_devices=1", len(r) == 1)

# 持久化往返
tmpdir2 = tempfile.mkdtemp()
fp2 = os.path.join(tmpdir2, "full.json")
mgr_full.save_to_file(fp2)

mgr_reload = DeviceManager()
mgr_reload.load_from_file(fp2, merge=False)
test("集成: reload count=3", mgr_reload.device_count == 3)
test("集成: reload d_temp", mgr_reload.get_device_by_name("温度站") is not None)
test(
    "集成: reload T1 eng=65.0",
    abs(mgr_reload.get_register(mgr_reload.get_device_by_name("温度站").id, "T1").engineering_value - 65.0) < 0.1,
)

os.remove(fp2)
os.rmdir(tmpdir2)

# ═══════════════════════════════════════════════════════════
# 汇总
print()
print("=" * 60)
total = passed + failed
print(f"总计: {total} 项, 通过: {passed}, 失败: {failed}")
if failed == 0:
    print("ALL PASSED!")
else:
    print(f"WARNING: {failed} 项失败!")
    sys.exit(1)
