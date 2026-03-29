"""步骤4.1 设备模型验证测试"""

import sys

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
print("1. AlarmConfig 测试")
print("=" * 60)
from src.device.register import AlarmConfig

ac = AlarmConfig(high_high=200.0, high=100.0, low=0.0, low_low=-50.0, deadband=2.0)
test("高高报触发 (200)", ac.check_alarm(200) == "high_high")
test("高高报触发 (250)", ac.check_alarm(250) == "high_high")
test("高报触发 (100)", ac.check_alarm(100) == "high")
test("高报触发 (150)", ac.check_alarm(150) == "high")
test("低报触发 (0)", ac.check_alarm(0) == "low")
test("低报触发 (-10)", ac.check_alarm(-10) == "low")
test("低低报触发 (-50)", ac.check_alarm(-50) == "low_low")
test("低低报触发 (-100)", ac.check_alarm(-100) == "low_low")
test("正常范围 (50)", ac.check_alarm(50) is None)
test("禁用报警", AlarmConfig(enabled=False).check_alarm(999) is None)

test("高报清除 (97<100-2)", ac.check_alarm_clear(97, "high"))
test("高报不清除 (99<100-2不成立)", not ac.check_alarm_clear(99, "high"))
test("低报清除 (3>0+2)", ac.check_alarm_clear(3, "low"))
test("低报不清除 (1>0+2不成立)", not ac.check_alarm_clear(1, "low"))

d = ac.to_dict()
ac2 = AlarmConfig.from_dict(d)
test("序列化往返", ac2.high_high == 200.0 and ac2.deadband == 2.0)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("2. AlarmLevel 测试")
print("=" * 60)
from src.device.register import AlarmLevel

test("severity(none)=0", AlarmLevel.severity("none") == 0)
test("severity(low)=1", AlarmLevel.severity("low") == 1)
test("severity(low_low)=2", AlarmLevel.severity("low_low") == 2)
test("severity(high)=3", AlarmLevel.severity("high") == 3)
test("severity(high_high)=4", AlarmLevel.severity("high_high") == 4)
test("display_text(none)='正常'", AlarmLevel.display_text("none") == "正常")
test("display_text(high)='高报'", AlarmLevel.display_text("high") == "高报")
test("display_text(low_low)='低低报'", AlarmLevel.display_text("low_low") == "低低报")
test("color(none)='#4CAF50'", AlarmLevel.color("none") == "#4CAF50")
test("color(high_high)='#F44336'", AlarmLevel.color("high_high") == "#F44336")

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("3. Register 基础属性测试")
print("=" * 60)
from src.device.register import Register
from src.protocols.enums import DataType, Endian, RegisterType

reg = Register(
    name="温度",
    address=100,
    register_type=RegisterType.INPUT_REGISTER,
    data_type=DataType.FLOAT32,
    unit="°C",
    scale=0.1,
    offset=-50,
    alarm_config=AlarmConfig(high=80.0, low=10.0),
    group="温度组",
)

test("name='温度'", reg.name == "温度")
test("address=100", reg.address == 100)
test("register_type=input_register", reg.register_type == RegisterType.INPUT_REGISTER)
test("data_type=float32", reg.data_type == DataType.FLOAT32)
test("quantity=2 (float32占2寄存器)", reg.quantity == 2)
test("unit='°C'", reg.unit == "°C")
test("scale=0.1", reg.scale == 0.1)
test("offset=-50", reg.offset == -50)
test("group='温度组'", reg.group == "温度组")
test("end_address=101", reg.end_address == 101)
test("writable=False (INPUT_REGISTER)", not reg.writable)
test("not is_alarmed", not reg.is_alarmed)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("4. Register 值转换测试")
print("=" * 60)

reg2 = Register(name="压力", address=0, scale=0.01, offset=0, unit="MPa")
reg2.update_raw_value(5000)
test("raw_value=5000", reg2.raw_value == 5000)
test("eng_value=50.0 (5000*0.01)", abs(reg2.engineering_value - 50.0) < 0.001)
test("eng_to_raw(50.0)=5000", reg2.engineering_to_raw(50.0) == 5000)
test("format='50.00 MPa'", reg2.format_engineering_value() == "50.00 MPa")
test("last_update is not None", reg2.last_update is not None)
test("quality='good'", reg2.quality == "good")

# 带offset的转换
reg3 = Register(name="温度K", scale=0.1, offset=273.15, unit="K")
reg3.update_raw_value(300)  # 300*0.1+273.15 = 303.15
test("带offset: 300*0.1+273.15=303.15", abs(reg3.engineering_value - 303.15) < 0.001)

# bad quality
reg2.set_bad_quality()
test("bad quality", reg2.quality == "bad")
test("format bad='---'", reg2.format_engineering_value() == "---")

# clear
reg2.clear_value()
test("cleared: raw=0", reg2.raw_value == 0)
test("cleared: quality=uncertain", reg2.quality == "uncertain")

# 直接设置工程值
reg2.update_engineering_value(25.0)
test("eng_to_raw: (25-0)/0.01=2500", reg2.raw_value == 2500)
test("eng_value=25.0", abs(reg2.engineering_value - 25.0) < 0.001)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("5. Register 报警测试")
print("=" * 60)

alarm_signals = []
test_reg = Register(name="电压", scale=1, alarm_config=AlarmConfig(high=240.0, low=200.0, deadband=3.0))


def on_alarm_triggered(level, value, msg):
    alarm_signals.append(("triggered", level, value))


def on_alarm_cleared(old_level, msg):
    alarm_signals.append(("cleared", old_level))


test_reg.alarm_triggered.connect(on_alarm_triggered)
test_reg.alarm_cleared.connect(on_alarm_cleared)

# 正常值 → 不触发
test_reg.update_engineering_value(220.0)
test("正常值无报警", test_reg.current_alarm == "none")
test("无信号", len(alarm_signals) == 0)

# 超高报
test_reg.update_engineering_value(250.0)
test("触发高报", test_reg.current_alarm == "high")
test("1个信号", len(alarm_signals) == 1)
test("信号=triggered,high,250", alarm_signals[0] == ("triggered", "high", 250.0))

# 回到正常范围但未过死区 (240-3=237)
test_reg.update_engineering_value(238.0)
test("未过死区, 保持报警", test_reg.current_alarm == "high")
test("信号数不变", len(alarm_signals) == 1)

# 过死区 (237以下)
test_reg.update_engineering_value(230.0)
test("过死区, 报警清除", test_reg.current_alarm == "none")
test("2个信号", len(alarm_signals) == 2)
test("信号=cleared,high", alarm_signals[1] == ("cleared", "high"))

# 低报
test_reg.update_engineering_value(199.0)
test("触发低报", test_reg.current_alarm == "low")

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("6. Register 序列化测试")
print("=" * 60)

reg4 = Register(
    name="流量",
    address=40001,
    register_type=RegisterType.HOLDING_REGISTER,
    data_type=DataType.UINT32,
    unit="L/min",
    scale=1.0,
    offset=0,
    alarm_config=AlarmConfig(high=1000.0),
)
reg4.update_raw_value(500)

d = reg4.to_dict()
test("to_dict有name", d["name"] == "流量")
test("to_dict有address", d["address"] == 40001)
test("to_dict有alarm_config", "high" in d["alarm_config"])
test("to_dict有raw_value", d["raw_value"] == 500)
test("to_dict有last_update", d["last_update"] is not None)

reg4_restored = Register.from_dict(d)
test("from_dict: name", reg4_restored.name == "流量")
test("from_dict: address", reg4_restored.address == 40001)
test("from_dict: data_type", reg4_restored.data_type == DataType.UINT32)
test("from_dict: raw_value", reg4_restored.raw_value == 500)
test("from_dict: alarm_config.high", reg4_restored.alarm_config.high == 1000.0)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("7. Register 地址重叠与__eq__/__hash__测试")
print("=" * 60)

r1 = Register(name="R1", address=0, register_type=RegisterType.HOLDING_REGISTER)
r2 = Register(name="R2", address=2, register_type=RegisterType.HOLDING_REGISTER)
r3 = Register(name="R3", address=0, register_type=RegisterType.HOLDING_REGISTER)
r4 = Register(name="R4", address=0, register_type=RegisterType.INPUT_REGISTER)

test("R1和R2不重叠", not r1.overlaps(r2))
test("R1和R3重叠 (同地址)", r1.overlaps(r3))
test("R1和R4不重叠 (不同类型)", not r1.overlaps(r4))

test("R1==R3 (同地址同类型)", r1 == r3)
test("R1!=R2", r1 != r2)
test("R1!=R4 (不同类型)", r1 != r4)

s = {r1, r2, r3}
test("set去重: R1和R3只算1个", len(s) == 2)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("8. Register 属性校验测试")
print("=" * 60)

try:
    r = Register()
    r.address = -1
    test("address=-1 应抛异常", False)
except ValueError:
    test("address=-1 抛ValueError", True)

try:
    r = Register()
    r.address = 70000
    test("address=70000 应抛异常", False)
except ValueError:
    test("address=70000 抛ValueError", True)

try:
    r = Register()
    r.quantity = 0
    test("quantity=0 应抛异常", False)
except ValueError:
    test("quantity=0 抛ValueError", True)

# COIL writable
coil_reg = Register(register_type=RegisterType.COIL, read_only=False)
test("COIL writable=True", coil_reg.writable)
coil_reg.read_only = True
test("COIL read_only → writable=False", not coil_reg.writable)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("9. TcpParams / SerialParams / PollConfig 测试")
print("=" * 60)
from src.device.device import PollConfig, SerialParams, TcpParams

tcp = TcpParams(host="192.168.1.100", port=502, ssl_enabled=True)
d = tcp.to_dict()
tcp2 = TcpParams.from_dict(d)
test("TcpParams roundtrip", tcp2.host == "192.168.1.100" and tcp2.port == 502 and tcp2.ssl_enabled)

serial = SerialParams(port="COM3", baud_rate=115200)
d = serial.to_dict()
serial2 = SerialParams.from_dict(d)
test("SerialParams roundtrip", serial2.port == "COM3" and serial2.baud_rate == 115200)

poll = PollConfig(interval_ms=500, retry_count=5)
d = poll.to_dict()
poll2 = PollConfig.from_dict(d)
test("PollConfig roundtrip", poll2.interval_ms == 500 and poll2.retry_count == 5)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("10. Device 基础属性测试")
print("=" * 60)
from src.device.device import Device
from src.protocols.enums import DeviceStatus, ProtocolType

dev = Device(
    name="PLC-001",
    protocol_type=ProtocolType.MODBUS_TCP,
    slave_id=1,
    description="主PLC",
    location="车间A",
    tags=["重要", "温度"],
)

test("id是UUID格式", len(dev.id) == 36)
test("name='PLC-001'", dev.name == "PLC-001")
test("protocol=modbus_tcp", dev.protocol_type == ProtocolType.MODBUS_TCP)
test("slave_id=1", dev.slave_id == 1)
test("description='主PLC'", dev.description == "主PLC")
test("location='车间A'", dev.location == "车间A")
test("tags=['重要','温度']", dev.tags == ["重要", "温度"])
test("enabled=True", dev.enabled)
test("register_count=0", dev.register_count == 0)
test("is_connected=False", not dev.is_connected)
test("is_error=False", not dev.is_error)
test("status=disconnected", dev.device_status == DeviceStatus.DISCONNECTED)

# 属性setter校验
try:
    dev.name = ""
    test("name='' 应抛异常", False)
except ValueError:
    test("name='' 抛ValueError", True)

try:
    dev.slave_id = 300
    test("slave_id=300 应抛异常", False)
except ValueError:
    test("slave_id=300 抛ValueError", True)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("11. Device 寄存器管理测试")
print("=" * 60)

dev2 = Device(name="DEV-002")

reg_a = Register(name="温度", address=0, register_type=RegisterType.HOLDING_REGISTER, group="温度组")
reg_b = Register(name="压力", address=10, register_type=RegisterType.HOLDING_REGISTER, group="压力组")
reg_c = Register(name="湿度", address=20, register_type=RegisterType.INPUT_REGISTER, group="环境组")

dev2.add_register(reg_a)
dev2.add_register(reg_b)
dev2.add_register(reg_c)

test("register_count=3", dev2.register_count == 3)
test("register_names有3个", len(dev2.register_names) == 3)
test("get_register('温度')存在", dev2.get_register("温度") is not None)
test("get_register('不存在')=None", dev2.get_register("不存在") is None)
test("get_registers_by_group('温度组')=1个", len(dev2.get_registers_by_group("温度组")) == 1)
test("get_register_groups()=3个", len(dev2.get_register_groups()) == 3)

# 地址重叠检测
try:
    dev2.add_register(Register(name="冲突", address=0, register_type=RegisterType.HOLDING_REGISTER))
    test("地址重叠应抛异常", False)
except ValueError:
    test("地址重叠抛ValueError", True)

# 同名检测
try:
    dev2.add_register(Register(name="温度", address=100))
    test("同名应抛异常", False)
except ValueError:
    test("同名抛ValueError", True)

# 移除寄存器
dev2.remove_register("湿度")
test("remove后count=2", dev2.register_count == 2)
test("remove后get=None", dev2.get_register("湿度") is None)

# 不存在
try:
    dev2.remove_register("不存在")
    test("不存在应抛异常", False)
except KeyError:
    test("不存在抛KeyError", True)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("12. Device 值更新与统计测试")
print("=" * 60)

dev3 = Device(name="DEV-003")
dev3.add_register(Register(name="V1", address=0, scale=0.1))
dev3.add_register(Register(name="V2", address=1, scale=0.1))

dev3.update_register_value("V1", 100)
test("V1 eng=10.0", abs(dev3.get_register("V1").engineering_value - 10.0) < 0.001)

dev3.batch_update_values({"V1": 200, "V2": 300})
test("batch: V1=20.0", abs(dev3.get_register("V1").engineering_value - 20.0) < 0.001)
test("batch: V2=30.0", abs(dev3.get_register("V2").engineering_value - 30.0) < 0.001)

count = dev3.batch_update_values({"V1": 400, "未知": 999})
test("batch: 成功1个 (未知被跳过)", count == 1)

dev3.record_poll_success()
dev3.record_poll_success()
dev3.record_poll_failure()
test("total_polls=3", dev3.total_polls == 3)
test("failed_polls=1", dev3.failed_polls == 1)
test("success_rate≈66.7%", abs(dev3.success_rate - 66.6667) < 0.1)

dev3.reset_statistics()
test("reset: total=0", dev3.total_polls == 0)
test("reset: failed=0", dev3.failed_polls == 0)

# clear_all
dev3.clear_all_values()
test("clear: V1 raw=0", dev3.get_register("V1").raw_value == 0)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("13. Device 状态变更测试")
print("=" * 60)

status_changes = []
dev4 = Device(name="DEV-004")
dev4.status_changed.connect(lambda s: status_changes.append(s))

dev4.set_status(DeviceStatus.CONNECTING)
test("status=connecting", dev4.device_status == DeviceStatus.CONNECTING)
test("1个信号", len(status_changes) == 1)

dev4.set_status(DeviceStatus.CONNECTING)  # 重复,不发射
test("重复状态不发射", len(status_changes) == 1)

dev4.set_status(DeviceStatus.CONNECTED)
test("status=connected", dev4.is_connected)
test("last_online已设置", dev4.last_online is not None)
test("2个信号", len(status_changes) == 2)

dev4.set_error("连接超时")
test("status=error", dev4.is_error)
test("error_msg='连接超时'", dev4.last_error == "连接超时")
test("error_count=1", dev4.error_count == 1)
test("3个信号", len(status_changes) == 3)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("14. Device 信号转发测试")
print("=" * 60)

value_signals = []
alarm_signals_dev = []
alarm_clear_signals = []

dev5 = Device(name="DEV-005")
dev5.value_changed.connect(lambda n, r, e, t: value_signals.append((n, r, e)))
dev5.alarm_triggered.connect(lambda dn, rn, v, l: alarm_signals_dev.append((dn, rn, v, l)))
dev5.alarm_cleared.connect(lambda dn, rn, l: alarm_clear_signals.append((dn, rn, l)))

reg_with_alarm = Register(name="报警寄存器", alarm_config=AlarmConfig(high=100.0))
dev5.add_register(reg_with_alarm)

dev5.update_register_value("报警寄存器", 1500)  # raw=1500, eng=1500 (scale=1)
test("值转发: 1个信号", len(value_signals) == 1)
test("值转发: name='报警寄存器'", value_signals[0][0] == "报警寄存器")

# 报警触发 (eng=1500 > 100)
test("报警转发: 1个信号", len(alarm_signals_dev) == 1)
test("报警转发: dev='DEV-005'", alarm_signals_dev[0][0] == "DEV-005")
test("报警转发: reg='报警寄存器'", alarm_signals_dev[0][1] == "报警寄存器")

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("15. Device 批量读取请求生成测试")
print("=" * 60)

dev6 = Device(name="DEV-006")
dev6.add_register(Register(name="HR0", address=0, register_type=RegisterType.HOLDING_REGISTER, quantity=1))
dev6.add_register(Register(name="HR1", address=1, register_type=RegisterType.HOLDING_REGISTER, quantity=1))
dev6.add_register(Register(name="HR5", address=5, register_type=RegisterType.HOLDING_REGISTER, quantity=2))
dev6.add_register(Register(name="IR0", address=0, register_type=RegisterType.INPUT_REGISTER, quantity=1))

requests = dev6.get_read_requests()
test("3个请求 (2*HR+IR)", len(requests) == 3)

hr_req = [r for r in requests if r["register_type"] == RegisterType.HOLDING_REGISTER][0]
# HR0(addr=0,qty=1,end=0) + HR1(addr=1,qty=1,end=1) 合并: addr<=0+1
# HR5(addr=5,qty=2,end=6) 与上一个 end=1, addr=5 > 1+1=2, 不合并
# 所以应该是2个HR请求
test(
    "HR requests=2 (0-1 + 5-6)", len([r for r in requests if r["register_type"] == RegisterType.HOLDING_REGISTER]) == 2
)

# 第一个HR请求: addr=0, count=2, 2个寄存器
hr_first = [r for r in requests if r["register_type"] == RegisterType.HOLDING_REGISTER][0]
test("HR first: start=0, count=2", hr_first["start_address"] == 0 and hr_first["count"] == 2)
test("HR first: 2个寄存器", len(hr_first["register_names"]) == 2)

# 第二个HR请求: addr=5, count=2, 1个寄存器
hr_second = [r for r in requests if r["register_type"] == RegisterType.HOLDING_REGISTER][1]
test("HR second: start=5, count=2", hr_second["start_address"] == 5 and hr_second["count"] == 2)

ir_req = [r for r in requests if r["register_type"] == RegisterType.INPUT_REGISTER][0]
test("IR: start=0, count=1", ir_req["start_address"] == 0 and ir_req["count"] == 1)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("16. Device 标签测试")
print("=" * 60)

dev7 = Device(name="DEV-007", tags=["A"])
dev7.add_tag("B")
test("add_tag 'B'", dev7.has_tag("B"))
dev7.add_tag("A")  # 重复
test("重复tag不增加", len(dev7.tags) == 2)
dev7.remove_tag("A")
test("remove_tag 'A'", not dev7.has_tag("A"))
test("tags=['B']", dev7.tags == ["B"])

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("17. Device 序列化测试")
print("=" * 60)

dev8 = Device(
    name="序列化测试设备",
    protocol_type=ProtocolType.MODBUS_RTU,
    slave_id=5,
    description="测试",
    location="位置X",
    tags=["测试"],
    serial_params=SerialParams(port="COM5", baud_rate=19200),
    poll_config=PollConfig(interval_ms=2000),
)
dev8.add_register(Register(name="R1", address=0, data_type=DataType.INT16))
dev8.add_register(Register(name="R2", address=10, data_type=DataType.FLOAT32))

d = dev8.to_dict()
test("to_dict: name", d["name"] == "序列化测试设备")
test("to_dict: protocol=modbus_rtu", d["protocol_type"] == "modbus_rtu")
test("to_dict: slave_id=5", d["slave_id"] == 5)
test("to_dict: serial port=COM5", d["serial_params"]["port"] == "COM5")
test("to_dict: poll interval=2000", d["poll_config"]["interval_ms"] == 2000)
test("to_dict: 2个寄存器", len(d["registers"]) == 2)

dev8_restored = Device.from_dict(d)
test("from_dict: name", dev8_restored.name == "序列化测试设备")
test("from_dict: protocol=RTU", dev8_restored.protocol_type == ProtocolType.MODBUS_RTU)
test("from_dict: slave_id=5", dev8_restored.slave_id == 5)
test("from_dict: serial port=COM5", dev8_restored.serial_params.port == "COM5")
test("from_dict: register_count=2", dev8_restored.register_count == 2)
test("from_dict: R1 address=0", dev8_restored.get_register("R1").address == 0)

# JSON roundtrip
json_str = dev8.to_json(indent=None)
dev8_from_json = Device.from_json(json_str)
test("JSON roundtrip: name", dev8_from_json.name == "序列化测试设备")
test("JSON roundtrip: 2 registers", dev8_from_json.register_count == 2)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("18. Device __eq__/__hash__ 与 get_summary 测试")
print("=" * 60)

dev_a = Device(name="A", device_id="same-id")
dev_b = Device(name="B", device_id="same-id")
dev_c = Device(name="C")

test("同ID相等", dev_a == dev_b)
test("不同ID不等", dev_a != dev_c)
test("hash可用", hash(dev_a) == hash(dev_b))

summary = dev8.get_summary()
test("summary有name", summary["name"] == "序列化测试设备")
test("summary有status", "status" in summary)
test("summary有registers", summary["registers"] == 2)
test("summary有alarms", "alarms" in summary)
test("summary有success_rate", "success_rate" in summary)

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("19. Device connection_params 测试")
print("=" * 60)

dev_tcp = Device(protocol_type=ProtocolType.MODBUS_TCP, tcp_params=TcpParams(host="10.0.0.1"))
test("TCP设备返回TcpParams", isinstance(dev_tcp.connection_params, TcpParams))
test("host=10.0.0.1", dev_tcp.connection_params.host == "10.0.0.1")

dev_rtu = Device(protocol_type=ProtocolType.MODBUS_RTU, serial_params=SerialParams(port="COM7"))
test("RTU设备返回SerialParams", isinstance(dev_rtu.connection_params, SerialParams))
test("port=COM7", dev_rtu.connection_params.port == "COM7")

# ═══════════════════════════════════════════════════════════
print()
print("=" * 60)
print("20. Register 报警升级测试")
print("=" * 60)

upgrade_signals = []
test_reg2 = Register(name="升级测试", alarm_config=AlarmConfig(high=100.0, high_high=200.0, deadband=5.0))


def on_trigger(level, value, msg):
    upgrade_signals.append(("triggered", level, value))


def on_clear(old, msg):
    upgrade_signals.append(("cleared", old))


test_reg2.alarm_triggered.connect(on_trigger)
test_reg2.alarm_cleared.connect(on_clear)

# 正常
test_reg2.update_engineering_value(50)
test("升级: 正常无报警", test_reg2.current_alarm == "none")

# 高报
test_reg2.update_engineering_value(120)
test("升级: 高报", test_reg2.current_alarm == "high")
test("升级: 1个triggered", len(upgrade_signals) == 1)

# 升级到高高报
test_reg2.update_engineering_value(250)
test("升级: 高高报", test_reg2.current_alarm == "high_high")
test("升级: 2个triggered (升级信号)", len(upgrade_signals) == 2)
test("升级: 信号level=high_high", upgrade_signals[1][1] == "high_high")

# 降到高报范围 (不高高报了, 但保持更高报警)
test_reg2.update_engineering_value(150)
test("降级但保持: 仍为high_high", test_reg2.current_alarm == "high_high")
test("降级但保持: 无新信号", len(upgrade_signals) == 2)

# 回到正常
test_reg2.update_engineering_value(50)
test("升级: 回到正常", test_reg2.current_alarm == "none")
test("升级: 1个cleared", len([s for s in upgrade_signals if s[0] == "cleared"]) == 1)

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
