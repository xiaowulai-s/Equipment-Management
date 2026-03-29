import json
import sys
import threading

sys.path.insert(0, "e:/下载/app/equipment management")
from src.device.data_collector import CollectorStats, reg_type_is_bit

# CollectorStats
s = CollectorStats()
assert s.success_rate == 100.0 and s.uptime_seconds == 0.0 and s.to_dict()["total_polls"] == 0
s.start()
s.record_poll(True, 10, 5.0)
s.record_poll(True, 10, 8.0)
s.record_poll(False, 0, 0.0)
d = s.to_dict()
assert d["total_polls"] == 3 and d["success_polls"] == 2 and d["failed_polls"] == 1
assert abs(d["success_rate"] - 66.67) < 0.1 and d["total_registers_read"] == 20 and abs(d["avg_latency_ms"] - 6.5) < 0.1
s.record_write(True)
s.record_write(True)
s.record_write(False)
d2 = s.to_dict()
assert d2["total_writes"] == 3 and d2["write_successes"] == 2 and d2["write_failures"] == 1
s.reset()
assert s.to_dict()["total_polls"] == 0 and s.to_dict()["uptime_seconds"] == 0.0
assert "success_rate" in json.dumps(s.to_dict())
print("[1/6] CollectorStats basic+writes+reset+json")

sf = CollectorStats()
sf.record_poll(False, 0, 0)
assert sf.success_rate == 0.0
so = CollectorStats()
so.record_poll(True, 10, 1)
assert so.success_rate == 100.0
assert CollectorStats().uptime_seconds == 0.0
sn = CollectorStats()
sn.record_poll(True, 5, 1)
assert sn.to_dict()["total_polls"] == 1
print("[2/6] CollectorStats edge cases")

sl = CollectorStats()
sl.start()
for i in range(101):
    sl.record_poll(True, 1, float(i))
dl = sl.to_dict()
assert dl["total_polls"] == 101 and abs(dl["avg_latency_ms"] - 50.5) < 0.1
print("[3/6] Latency window")

st = CollectorStats()
st.start()
errs = []


def pt():
    try:
        for i in range(50):
            st.record_poll(True, 10, float(i))
    except Exception as e:
        errs.append(str(e))


ts = [threading.Thread(target=pt) for _ in range(5)]
for t in ts:
    t.start()
for t in ts:
    t.join(timeout=5)
assert st.to_dict()["total_polls"] == 250 and len(errs) == 0
print("[4/6] Thread safety")

assert reg_type_is_bit(1) and reg_type_is_bit(2) and not reg_type_is_bit(3) and not reg_type_is_bit(4)
print("[5/6] reg_type_is_bit")

from src.device.data_collector import create_protocol
from src.device.device import Device, SerialParams, TcpParams
from src.protocols.enums import ProtocolType

pt = create_protocol(
    Device(name="T", protocol_type=ProtocolType.MODBUS_TCP, slave_id=1, tcp_params=TcpParams(host="1.2.3.4", port=502))
)
assert pt.protocol_type == ProtocolType.MODBUS_TCP
pr = create_protocol(
    Device(
        name="R",
        protocol_type=ProtocolType.MODBUS_RTU,
        slave_id=1,
        serial_params=SerialParams(port="COM3", baud_rate=9600),
    )
)
assert pr.protocol_type == ProtocolType.MODBUS_RTU
pa = create_protocol(
    Device(
        name="A",
        protocol_type=ProtocolType.MODBUS_ASCII,
        slave_id=1,
        serial_params=SerialParams(port="COM4", baud_rate=9600),
    )
)
assert pa.protocol_type == ProtocolType.MODBUS_ASCII
print("[6/6] create_protocol factory")

print("\n=== PART 1: 6/6 ALL PASSED ===")
