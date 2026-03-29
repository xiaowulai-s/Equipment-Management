"""
步骤2.2 ModbusTCP协议实现 - 验证测试

测试内容:
    1. 实例化与属性校验
    2. MBAP头构建与事务ID管理
    3. PDU帧构建 (8种功能码)
    4. 响应解析 (正常 + 异常)
    5. 参数校验 (IP/端口/地址范围)
    6. 异常码描述映射
    7. 位数据解包
"""

import struct
import sys

sys.path.insert(0, ".")

from src.protocols.enums import DataType, DeviceStatus, Endian, FunctionCode, ProtocolType
from src.protocols.modbus_tcp import _MODBUS_PROTOCOL_ID, ModbusTCPProtocol
from src.utils.exceptions import ProtocolConnectionError, ProtocolResponseError, ProtocolTimeoutError

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")


# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("ModbusTCP协议测试")
print("=" * 60)

# ── 1. 实例化与属性 ──
print("\n[1] 实例化与属性")
proto = ModbusTCPProtocol(host="192.168.1.100", port=502, timeout=5.0, slave_address=1)
check("protocol_type", proto.protocol_type == ProtocolType.MODBUS_TCP)
check("host", proto.host == "192.168.1.100")
check("port", proto.port == 502)
check("timeout", proto.timeout == 5.0)
check("slave_address", proto.slave_address == 1)
check("status", proto.status == DeviceStatus.DISCONNECTED)
check("not connected", not proto.is_connected)
check("connection_info", proto.connection_info == "192.168.1.100:502")
check("repr", "ModbusTCPProtocol" in repr(proto))

# ── 2. 属性校验 ──
print("\n[2] 属性校验")
proto.host = "10.0.0.1"
check("host setter", proto.host == "10.0.0.1")

proto.port = 503
check("port setter", proto.port == 503)

proto.slave_address = 247
check("slave max", proto.slave_address == 247)

try:
    proto.port = 0
    check("port=0 应抛异常", False)
except ValueError:
    check("port=0 ValueError", True)

try:
    proto.port = 70000
    check("port=70000 应抛异常", False)
except ValueError:
    check("port=70000 ValueError", True)

try:
    proto.slave_address = 0
    check("slave=0 应抛异常", False)
except ValueError:
    check("slave=0 ValueError", True)

# ── 3. 事务ID管理 ──
print("\n[3] 事务ID管理")
tid1 = proto._next_transaction_id()
tid2 = proto._next_transaction_id()
tid3 = proto._next_transaction_id()
check("事务ID递增", tid1 < tid2 < tid3)
check("事务ID差值", tid2 - tid1 == 1 and tid3 - tid2 == 1)

# ── 4. PDU帧构建 ──
print("\n[4] PDU帧构建")

# FC03: 读保持寄存器 [FC:01][Addr:0000][Qty:000A]
pdu_fc03 = proto._build_pdu(FunctionCode.READ_HOLDING_REGISTERS, 0, 10)
check(
    "FC03 PDU长度",
    len(pdu_fc03) == 5,
    f"实际={len(pdu_fc03)}",
)
fc, addr, qty = struct.unpack(">BHH", pdu_fc03)
check("FC03 功能码", fc == 0x03)
check("FC03 地址", addr == 0)
check("FC03 数量", qty == 10)

# FC01: 读线圈
pdu_fc01 = proto._build_pdu(FunctionCode.READ_COILS, 100, 8)
fc, addr, qty = struct.unpack(">BHH", pdu_fc01)
check("FC01 功能码", fc == 0x01)
check("FC01 地址", addr == 100)
check("FC01 数量", qty == 8)

# FC02: 读离散输入
pdu_fc02 = proto._build_pdu(FunctionCode.READ_DISCRETE_INPUTS, 0, 4)
fc, addr, qty = struct.unpack(">BHH", pdu_fc02)
check("FC02 功能码", fc == 0x02)

# FC04: 读输入寄存器
pdu_fc04 = proto._build_pdu(FunctionCode.READ_INPUT_REGISTERS, 5, 3)
fc, addr, qty = struct.unpack(">BHH", pdu_fc04)
check("FC04 功能码", fc == 0x04)

# FC05: 写单个线圈 ON
pdu_fc05_on = proto._build_pdu(FunctionCode.WRITE_SINGLE_COIL, 10, value=True)
fc, addr, val = struct.unpack(">BHH", pdu_fc05_on)
check("FC05 功能码", fc == 0x05)
check("FC05 地址=10", addr == 10)
check("FC05 ON值=0xFF00", val == 0xFF00)

# FC05: 写单个线圈 OFF
pdu_fc05_off = proto._build_pdu(FunctionCode.WRITE_SINGLE_COIL, 10, value=False)
fc, addr, val = struct.unpack(">BHH", pdu_fc05_off)
check("FC05 OFF值=0x0000", val == 0x0000)

# FC06: 写单个寄存器
pdu_fc06 = proto._build_pdu(FunctionCode.WRITE_SINGLE_REGISTER, 20, value=12345)
fc, addr, val = struct.unpack(">BHH", pdu_fc06)
check("FC06 功能码", fc == 0x06)
check("FC06 地址=20", addr == 20)
check("FC06 值=12345", val == 12345)

# FC15: 写多个线圈
pdu_fc15 = proto._build_pdu(
    FunctionCode.WRITE_MULTIPLE_COILS,
    0,
    value=[True, False, True, True, False, False, True, False, True],
)
fc, addr, qty, bc = struct.unpack(">BHHB", pdu_fc15[:6])
check("FC15 功能码", fc == 0x0F)
check("FC15 数量=9", qty == 9)
check("FC15 字节数=2", bc == 2)
# 验证位打包: T,F,T,T,F,F,T,F,T
# LSB first:
# Byte 0: bit0=T(1),bit1=F(0),bit2=T(1),bit3=T(1),bit4=F(0),bit5=F(0),bit6=T(1),bit7=F(0)
#        = 0b01001101 = 0x4D
# Byte 1: bit8=T(1), rest=0
#        = 0b00000001 = 0x01
coils_data = pdu_fc15[6:]
check("FC15 位数据", coils_data[0] == 0x4D and coils_data[1] == 0x01, f"actual={coils_data.hex()}")

# FC16: 写多个寄存器
write_data = struct.pack(">HH", 1000, 2000)  # 两个寄存器值
pdu_fc16 = proto._build_pdu(
    FunctionCode.WRITE_MULTIPLE_REGISTERS,
    0,
    value=write_data,
)
fc, addr, qty, bc = struct.unpack(">BHHB", pdu_fc16[:6])
check("FC16 功能码", fc == 0x10)
check("FC16 寄存器数=2", qty == 2)
check("FC16 字节数=4", bc == 4)
reg_data = pdu_fc16[6:]
check("FC16 寄存器数据", struct.unpack(">HH", reg_data) == (1000, 2000))

# ── 5. 完整ADU帧构建 ──
print("\n[5] 完整ADU帧构建")
proto_adu = ModbusTCPProtocol(host="192.168.1.100", port=502, slave_address=1)
frame = proto_adu._build_request_frame(FunctionCode.READ_HOLDING_REGISTERS, 100, 5)
check("ADU帧长度", len(frame) == 12, f"实际={len(frame)}")
tid, pid, length, uid = struct.unpack(">HHHB", frame[:7])
check("ADU Transaction ID > 0", tid > 0)
check("ADU Protocol ID = 0", pid == 0)
check("ADU Length = 6", length == 6, f"实际={length}")
check("ADU Unit ID = 1", uid == 1)
check("ADU FC = 0x03", frame[7] == 0x03)
resp_addr, resp_qty = struct.unpack(">HH", frame[8:12])
check("ADU 地址=100", resp_addr == 100)
check("ADU 数量=5", resp_qty == 5)

# ── 6. 响应解析 ──
print("\n[6] 响应解析")

# 6a. FC03正常响应
# 模拟: UnitID=1, FC=0x03, ByteCount=6, Data=[0x0064,0x012C,0x0258]
fc03_response = bytes(
    [
        0x01,  # Unit ID
        0x03,  # FC
        0x06,  # Byte Count = 6
        0x00,
        0x64,  # 100
        0x01,
        0x2C,  # 300
        0x02,
        0x58,  # 600
    ]
)
result = proto._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, fc03_response, 0)
check("FC03响应 success", result.success)
check("FC03响应 values", result.values == [100, 300, 600], f"实际={result.values}")
check("FC03响应 start_address", result.start_address == 0)

# 6b. FC01正常响应 (位操作)
# 模拟: UnitID=1, FC=0x01, ByteCount=2, Data=[0b10110010, 0b00001101]
fc01_response = bytes(
    [
        0x01,  # Unit ID
        0x01,  # FC
        0x02,  # Byte Count = 2
        0xB2,  # 10110010
        0x0D,  # 00001101
    ]
)
result_bits = proto._parse_response_frame(FunctionCode.READ_COILS, fc01_response, 0)
check("FC01响应 success", result_bits.success)
# LSB first: 0,1,0,0,1,1,0,1,  1,0,1,1,0,0,0,0
expected_bits = [
    False,
    True,
    False,
    False,
    True,
    True,
    False,
    True,
    True,
    False,
    True,
    True,
    False,
    False,
    False,
    False,
]
check("FC01响应 values", result_bits.values == expected_bits, f"actual={result_bits.values}")

# 6c. 异常响应
# 模拟: UnitID=1, FC=0x83, ExceptionCode=0x02
error_response = bytes([0x01, 0x83, 0x02])
try:
    proto._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, error_response, 0)
    check("异常响应应抛异常", False)
except ProtocolResponseError as e:
    check("异常响应 ProtocolResponseError", True)
    check("异常码=0x02", e.details.get("exception_code") == 0x02)
    check("异常描述含'地址'", "地址" in str(e))

# 6d. 数据过短
try:
    proto._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, bytes([0x01]), 0)
    check("过短响应应抛异常", False)
except ProtocolResponseError:
    check("过短响应 ProtocolResponseError", True)

# ── 7. 写入响应解析 ──
print("\n[7] 写入响应解析")

# FC06回显: UnitID=1, FC=0x06, Addr=20, Value=12345
fc06_resp = bytes([0x01, 0x06, 0x00, 0x14, 0x30, 0x39])
wr = proto._parse_write_response(FunctionCode.WRITE_SINGLE_REGISTER, fc06_resp, 20)
check("FC06写入 success", wr.success)
check("FC06写入 address=20", wr.address == 20)
check("FC06写入 value=12345", wr.value == 12345)

# FC05回显 (ON)
fc05_resp = bytes([0x01, 0x05, 0x00, 0x0A, 0xFF, 0x00])
wr5 = proto._parse_write_response(FunctionCode.WRITE_SINGLE_COIL, fc05_resp, 10)
check("FC05写入 value=True", wr5.value is True)

# FC16回显: UnitID=1, FC=0x10, StartAddr=0, Qty=3
fc16_resp = bytes([0x01, 0x10, 0x00, 0x00, 0x00, 0x03])
wr16 = proto._parse_write_response(FunctionCode.WRITE_MULTIPLE_REGISTERS, fc16_resp, 0)
check("FC16写入 success", wr16.success)
check("FC16写入 value=3", wr16.value == 3)

# FC15回显
fc15_resp = bytes([0x01, 0x0F, 0x00, 0x00, 0x00, 0x09])
wr15 = proto._parse_write_response(FunctionCode.WRITE_MULTIPLE_COILS, fc15_resp, 0)
check("FC15写入 success", wr15.success)
check("FC15写入 value=9", wr15.value == 9)

# 写入异常响应
fc06_err = bytes([0x01, 0x86, 0x02])
try:
    proto._parse_write_response(FunctionCode.WRITE_SINGLE_REGISTER, fc06_err, 0)
    check("写入异常响应应抛异常", False)
except ProtocolResponseError as e:
    check("写入异常 ProtocolResponseError", True)

# ── 8. 辅助方法 ──
print("\n[8] 辅助方法")

# 异常码描述
desc = ModbusTCPProtocol._get_exception_description(0x01)
check("异常码0x01", desc == "非法功能码 (Illegal Function)")

desc2 = ModbusTCPProtocol._get_exception_description(0x04)
check("异常码0x04", "从站设备故障" in desc2)

desc3 = ModbusTCPProtocol._get_exception_description(0xFF)
check("未知异常码", "未知" in desc3)

# 寄存器解包
regs = ModbusTCPProtocol._unpack_registers(bytes([0x00, 0x64, 0x01, 0x2C]))
check("寄存器解包", regs == [100, 300], f"实际={regs}")

# 位解包
bits = ModbusTCPProtocol._unpack_bits(bytes([0x05]), 8)
check("位解包8位", bits == [True, False, True, False, False, False, False, False])

bits2 = ModbusTCPProtocol._unpack_bits(bytes([0x05, 0x03]), 12)
check("位解包12位", len(bits2) == 12)

# ── 9. IP校验 ──
print("\n[9] IP校验")
ModbusTCPProtocol._validate_host("192.168.1.1")
check("IPv4合法", True)
ModbusTCPProtocol._validate_host("::1")
check("IPv6合法", True)
ModbusTCPProtocol._validate_host("localhost")
check("主机名合法", True)

try:
    ModbusTCPProtocol._validate_host("")
    check("空地址应抛异常", False)
except ValueError:
    check("空地址 ValueError", True)

try:
    ModbusTCPProtocol._validate_host("host!@#invalid")
    check("非法主机名应抛异常", False)
except ValueError:
    check("非法主机名 ValueError", True)

# ── 10. _recv_exact 不完整 ──
print("\n[10] 连接错误处理")
try:
    proto._recv_exact(10)
    check("未连接时recv应抛异常", False)
except ProtocolConnectionError:
    check("未连接 ProtocolConnectionError", True)

try:
    proto._send_and_receive(b"\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x0a")
    check("未连接时send应抛异常", False)
except ProtocolConnectionError:
    check("未连接 send ProtocolConnectionError", True)


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"测试结果: {passed} 通过, {failed} 失败")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("\n✅ 步骤2.2 ModbusTCP协议实现 — 全部测试通过!")
