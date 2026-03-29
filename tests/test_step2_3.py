"""
步骤2.3 ModbusRTU/ASCII协议实现 - 验证测试

测试内容:
    Part A: ModbusRTU协议
        1. 实例化与属性
        2. CRC-16校验算法
        3. RTU帧构建 (8种功能码)
        4. RTU帧间间隔计算
        5. 响应解析 (正常 + 异常)

    Part B: ModbusASCII协议
        6. 实例化与属性
        7. LRC校验算法
        8. ASCII帧构建
        9. ASCII响应解析
        10. 异常码描述映射
"""

import struct
import sys

sys.path.insert(0, ".")

from src.protocols.enums import DeviceStatus, FunctionCode, ProtocolType
from src.protocols.modbus_ascii import ModbusASCIIProtocol
from src.protocols.modbus_rtu import _RTU_SILENCE_19200, ModbusRTUProtocol
from src.utils.exceptions import ProtocolConnectionError, ProtocolResponseError, ProtocolTimeoutError

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name} -- {detail}")


print("=" * 60)
print("ModbusRTU/ASCII Protocol Tests")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# Part A: ModbusRTU
# ═══════════════════════════════════════════════════════════════

print("\n[A1] RTU Instantiation & Properties")
rtu = ModbusRTUProtocol(port="COM3", baudrate=9600, slave_address=1, timeout=2.0)
check("protocol_type", rtu.protocol_type == ProtocolType.MODBUS_RTU)
check("port", rtu.port == "COM3")
check("baudrate", rtu.baudrate == 9600)
check("timeout", rtu.timeout == 2.0)
check("slave_address", rtu.slave_address == 1)
check("status", rtu.status == DeviceStatus.DISCONNECTED)
check("not connected", not rtu.is_connected)
check("connection_info", "COM3 @ 9600bps" in rtu.connection_info)
check("repr", "ModbusRTUProtocol" in repr(rtu))

# Test with different baudrates
rtu_115200 = ModbusRTUProtocol(baudrate=115200)
check("115200 gap fixed", rtu_115200._frame_gap > 0)
rtu_2400 = ModbusRTUProtocol(baudrate=2400)
check("2400 gap slower", rtu_2400._frame_gap > rtu_115200._frame_gap)

print("\n[A2] RTU CRC-16 Calculation")
# Known test vectors from Modbus specification
crc = ModbusRTUProtocol.calculate_crc(bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A]))
check("CRC non-zero", crc != 0)
check("CRC 16-bit", 0 < crc <= 0xFFFF)

# Verify: CRC of data + CRC should equal 0
data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])
crc_val = ModbusRTUProtocol.calculate_crc(data)
frame_with_crc = data + bytes([crc_val & 0xFF, (crc_val >> 8) & 0xFF])
check("CRC verify pass", ModbusRTUProtocol.verify_crc(frame_with_crc))

# Tampered CRC should fail
bad_frame = frame_with_crc[:-1] + bytes([(frame_with_crc[-1] ^ 0xFF)])
check("CRC verify fail", not ModbusRTUProtocol.verify_crc(bad_frame))

# Too short
check("CRC verify short", not ModbusRTUProtocol.verify_crc(b"AB"))

# Known Modbus CRC examples:
# FC03 read 10 holding registers from slave 1, address 0
data_fc03 = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])
crc_fc03 = ModbusRTUProtocol.calculate_crc(data_fc03)
check("FC03 CRC = 0xCDC5", crc_fc03 == 0xCDC5, f"actual={crc_fc03:#06x}")

print("\n[A3] RTU Frame Building")
# FC03: Read Holding Registers
frame_fc03 = rtu._build_request_frame(FunctionCode.READ_HOLDING_REGISTERS, 0, 10)
check("FC03 frame has CRC", len(frame_fc03) == 8, f"len={len(frame_fc03)}")
check("FC03 slave=1", frame_fc03[0] == 0x01)
check("FC03 FC=0x03", frame_fc03[1] == 0x03)
check("FC03 addr=0", frame_fc03[2] == 0x00 and frame_fc03[3] == 0x00)
check("FC03 qty=10", frame_fc03[4] == 0x00 and frame_fc03[5] == 0x0A)
# Verify CRC on the frame itself
check("FC03 CRC valid", ModbusRTUProtocol.verify_crc(frame_fc03))

# FC01: Read Coils
frame_fc01 = rtu._build_request_frame(FunctionCode.READ_COILS, 0, 8)
check("FC01 frame len", len(frame_fc01) == 8)
check("FC01 FC=0x01", frame_fc01[1] == 0x01)
check("FC01 CRC valid", ModbusRTUProtocol.verify_crc(frame_fc01))

# FC04: Read Input Registers
frame_fc04 = rtu._build_request_frame(FunctionCode.READ_INPUT_REGISTERS, 100, 3)
check("FC04 FC=0x04", frame_fc04[1] == 0x04)
check("FC04 CRC valid", ModbusRTUProtocol.verify_crc(frame_fc04))

# FC05: Write Single Coil ON
frame_fc05 = rtu._build_request_frame(FunctionCode.WRITE_SINGLE_COIL, 10, value=True)
check("FC05 frame len", len(frame_fc05) == 8)
check("FC05 FC=0x05", frame_fc05[1] == 0x05)
check("FC05 val=0xFF00", frame_fc05[4] == 0xFF and frame_fc05[5] == 0x00)
check("FC05 CRC valid", ModbusRTUProtocol.verify_crc(frame_fc05))

# FC06: Write Single Register
frame_fc06 = rtu._build_request_frame(FunctionCode.WRITE_SINGLE_REGISTER, 20, value=12345)
check("FC06 FC=0x06", frame_fc06[1] == 0x06)
check("FC06 val=12345", frame_fc06[4] == 0x30 and frame_fc06[5] == 0x39)
check("FC06 CRC valid", ModbusRTUProtocol.verify_crc(frame_fc06))

# FC15: Write Multiple Coils
frame_fc15 = rtu._build_request_frame(
    FunctionCode.WRITE_MULTIPLE_COILS, 0, value=[True, False, True, True, False, False, True, False, True]
)
check("FC15 FC=0x0F", frame_fc15[1] == 0x0F)
check("FC15 CRC valid", ModbusRTUProtocol.verify_crc(frame_fc15))
# Verify coil data: frame=[slave][FC][addrH][addrL][qtyH][qtyL][byteCount][coilData...][CRC_L][CRC_H]
# Offset:           0       1    2      3      4     5     6           7,8      9,10
check("FC15 coil byte0=0x4D", frame_fc15[7] == 0x4D)
check("FC15 coil byte1=0x01", frame_fc15[8] == 0x01)

# FC16: Write Multiple Registers
write_data = struct.pack(">HH", 1000, 2000)
frame_fc16 = rtu._build_request_frame(FunctionCode.WRITE_MULTIPLE_REGISTERS, 0, value=write_data)
check("FC16 FC=0x10", frame_fc16[1] == 0x10)
check("FC16 CRC valid", ModbusRTUProtocol.verify_crc(frame_fc16))

# Verify all frames start with slave address
for fc_name, frame in [
    ("FC03", frame_fc03),
    ("FC01", frame_fc01),
    ("FC04", frame_fc04),
    ("FC05", frame_fc05),
    ("FC06", frame_fc06),
    ("FC15", frame_fc15),
    ("FC16", frame_fc16),
]:
    check(f"{fc_name} starts with slave_id", frame[0] == 1)

print("\n[A4] RTU Frame Gap Calculation")
gap_9600 = ModbusRTUProtocol._calculate_frame_gap(9600)
gap_19200 = ModbusRTUProtocol._calculate_frame_gap(19200)
gap_38400 = ModbusRTUProtocol._calculate_frame_gap(38400)
check("9600 gap > 0", gap_9600 > 0)
check("19200 gap > 9600 gap (inverse)", gap_19200 < gap_9600, f"19200={gap_19200:.6f}, 9600={gap_9600:.6f}")
check("38400 gap == fixed", gap_38400 == _RTU_SILENCE_19200 * 2)

print("\n[A5] RTU Response Parsing")
# Simulate FC03 response PDU (不含地址和CRC):
# [FC=0x03][ByteCount=4][Data: 0x0064, 0x012C]
fc03_pdu = bytes([0x03, 0x04, 0x00, 0x64, 0x01, 0x2C])
result = rtu._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, fc03_pdu, 0)
check("FC03 success", result.success)
check("FC03 values", result.values == [100, 300])
check("FC03 start_address", result.start_address == 0)

# FC01 bit response
fc01_pdu = bytes([0x01, 0x02, 0xB2, 0x0D])
result_bits = rtu._parse_response_frame(FunctionCode.READ_COILS, fc01_pdu, 0)
check("FC01 success", result_bits.success)
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
check("FC01 values", result_bits.values == expected_bits)

# Exception response
exc_pdu = bytes([0x83, 0x02])
try:
    rtu._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, exc_pdu, 0)
    check("exception should raise", False)
except ProtocolResponseError as e:
    check("exception raised", True)
    check("exception code=2", e.details.get("exception_code") == 2)

# Short PDU
try:
    rtu._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, bytes([0x03]), 0)
    check("short PDU should raise", False)
except ProtocolResponseError:
    check("short PDU raised", True)

# Write response parsing (FC06)
fc06_pdu = bytes([0x06, 0x00, 0x14, 0x30, 0x39])
wr = rtu._parse_write_response(FunctionCode.WRITE_SINGLE_REGISTER, fc06_pdu, 20)
check("FC06 write success", wr.success)
check("FC06 write value=12345", wr.value == 12345)

# FC05 write
fc05_pdu = bytes([0x05, 0x00, 0x0A, 0xFF, 0x00])
wr5 = rtu._parse_write_response(FunctionCode.WRITE_SINGLE_COIL, fc05_pdu, 10)
check("FC05 write value=True", wr5.value is True)

# FC16 write
fc16_pdu = bytes([0x10, 0x00, 0x00, 0x00, 0x03])
wr16 = rtu._parse_write_response(FunctionCode.WRITE_MULTIPLE_REGISTERS, fc16_pdu, 0)
check("FC16 write success", wr16.success)
check("FC16 write value=3", wr16.value == 3)

# FC15 write
fc15_pdu = bytes([0x0F, 0x00, 0x00, 0x00, 0x09])
wr15 = rtu._parse_write_response(FunctionCode.WRITE_MULTIPLE_COILS, fc15_pdu, 0)
check("FC15 write success", wr15.success)

# Write exception
wr_exc = bytes([0x86, 0x02])
try:
    rtu._parse_write_response(FunctionCode.WRITE_SINGLE_REGISTER, wr_exc, 0)
    check("write exception should raise", False)
except ProtocolResponseError:
    check("write exception raised", True)

# Connection errors (no serial)
try:
    rtu._recv_exact(10)
    check("recv without serial should raise", False)
except (ProtocolConnectionError, AttributeError):
    check("recv without serial raised", True)

try:
    rtu._send_and_receive(b"\x01\x03\x00\x00\x00\x0a\x00\x00")
    check("send without serial should raise", False)
except ProtocolConnectionError:
    check("send without serial raised", True)


# ═══════════════════════════════════════════════════════════════
# Part B: ModbusASCII
# ═══════════════════════════════════════════════════════════════

print("\n[B1] ASCII Instantiation & Properties")
asc = ModbusASCIIProtocol(port="/dev/ttyUSB0", baudrate=9600, slave_address=5, timeout=1.5)
check("protocol_type", asc.protocol_type == ProtocolType.MODBUS_ASCII)
check("port", asc.port == "/dev/ttyUSB0")
check("baudrate", asc.baudrate == 9600)
check("slave_address", asc.slave_address == 5)
check("status disconnected", asc.status == DeviceStatus.DISCONNECTED)
check("connection_info", "/dev/ttyUSB0" in asc.connection_info)
check("repr", "ModbusASCIIProtocol" in repr(asc))

print("\n[B2] ASCII LRC Calculation")
# LRC test: data = [slave_id=5, FC03, addr=0, qty=10]
# Note: asc has slave_address=5
data = bytes([0x05, 0x03, 0x00, 0x00, 0x00, 0x0A])
lrc = ModbusASCIIProtocol.calculate_lrc(data)
check("LRC non-zero", lrc != 0)
check("LRC 8-bit", 0 <= lrc <= 0xFF)

# Verify: LRC(data + LRC) should == 0
check("LRC verify pass", ModbusASCIIProtocol.verify_lrc(data, lrc))

# Bad LRC
check("LRC verify fail", not ModbusASCIIProtocol.verify_lrc(data, (lrc ^ 0xFF) & 0xFF))

# sum = 5+3+0+0+0+10 = 18 = 0x12, ~0x12 = 0xED, 0xED+1 = 0xEE
expected_lrc = 0xEE
check(f"LRC = 0x{expected_lrc:02X}", lrc == expected_lrc, f"actual=0x{lrc:02X}")

print("\n[B3] ASCII Frame Building")
# FC03 frame
frame_fc03_asc = asc._build_request_frame(FunctionCode.READ_HOLDING_REGISTERS, 0, 10)
check("FC03 ASCII starts with ':'", frame_fc03_asc[0:1] == b":")
check("FC03 ASCII ends with CRLF", frame_fc03_asc[-2:] == b"\r\n")
# Decode content (between : and CRLF)
content = frame_fc03_asc[1:-2].decode("ascii")
check("FC03 ASCII slave=05", content[0:2] == "05")
check("FC03 ASCII FC=03", content[2:4] == "03")
check("FC03 ASCII addr=0000", content[4:8] == "0000")
check("FC03 ASCII qty=000A", content[8:12] == "000A")
check("FC03 ASCII LRC=F2", content[12:14] == f"{expected_lrc:02X}")
check("FC03 ASCII all uppercase", content == content.upper())

# FC06 frame
frame_fc06_asc = asc._build_request_frame(FunctionCode.WRITE_SINGLE_REGISTER, 20, value=12345)
content_fc06 = frame_fc06_asc[1:-2].decode("ascii")
check("FC06 ASCII FC=06", content_fc06[2:4] == "06")
check("FC06 ASCII addr=0014", content_fc06[4:8] == "0014")
check("FC06 ASCII val=3039", content_fc06[8:12] == "3039")

# FC05 frame
frame_fc05_asc = asc._build_request_frame(FunctionCode.WRITE_SINGLE_COIL, 10, value=True)
content_fc05 = frame_fc05_asc[1:-2].decode("ascii")
check("FC05 ASCII FC=05", content_fc05[2:4] == "05")
check("FC05 ASCII val=FF00", content_fc05[8:12] == "FF00")

# FC15 frame
frame_fc15_asc = asc._build_request_frame(
    FunctionCode.WRITE_MULTIPLE_COILS, 0, value=[True, False, True, True, False, False, True, False, True]
)
content_fc15 = frame_fc15_asc[1:-2].decode("ascii")
check("FC15 ASCII FC=0F", content_fc15[2:4] == "0F")

# FC16 frame
write_data = struct.pack(">HH", 1000, 2000)
frame_fc16_asc = asc._build_request_frame(FunctionCode.WRITE_MULTIPLE_REGISTERS, 0, value=write_data)
content_fc16 = frame_fc16_asc[1:-2].decode("ascii")
check("FC16 ASCII FC=10", content_fc16[2:4] == "10")

print("\n[B4] ASCII Response Parsing")
# FC03 response PDU (same binary as RTU PDU)
fc03_pdu = bytes([0x03, 0x04, 0x00, 0x64, 0x01, 0x2C])
result = asc._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, fc03_pdu, 0)
check("ASCII FC03 success", result.success)
check("ASCII FC03 values", result.values == [100, 300])

# FC01 bit response
fc01_pdu = bytes([0x01, 0x02, 0xB2, 0x0D])
result_bits = asc._parse_response_frame(FunctionCode.READ_COILS, fc01_pdu, 0)
check("ASCII FC01 success", result_bits.success)
check("ASCII FC01 values", result_bits.values == expected_bits)

# Exception
exc_pdu = bytes([0x83, 0x01])
try:
    asc._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, exc_pdu, 0)
    check("ASCII exception should raise", False)
except ProtocolResponseError as e:
    check("ASCII exception raised", True)
    check("ASCII exc code=1", e.details.get("exception_code") == 1)

# Short PDU
try:
    asc._parse_response_frame(FunctionCode.READ_HOLDING_REGISTERS, bytes([0x03]), 0)
    check("ASCII short should raise", False)
except ProtocolResponseError:
    check("ASCII short raised", True)

print("\n[B5] ASCII Write Response Parsing")
fc06_pdu = bytes([0x06, 0x00, 0x14, 0x30, 0x39])
wr = asc._parse_write_response(FunctionCode.WRITE_SINGLE_REGISTER, fc06_pdu, 20)
check("ASCII FC06 write success", wr.success)
check("ASCII FC06 value=12345", wr.value == 12345)

fc05_pdu = bytes([0x05, 0x00, 0x0A, 0xFF, 0x00])
wr5 = asc._parse_write_response(FunctionCode.WRITE_SINGLE_COIL, fc05_pdu, 10)
check("ASCII FC05 value=True", wr5.value is True)

fc16_pdu = bytes([0x10, 0x00, 0x00, 0x00, 0x03])
wr16 = asc._parse_write_response(FunctionCode.WRITE_MULTIPLE_REGISTERS, fc16_pdu, 0)
check("ASCII FC16 value=3", wr16.value == 3)

fc15_pdu = bytes([0x0F, 0x00, 0x00, 0x00, 0x09])
wr15 = asc._parse_write_response(FunctionCode.WRITE_MULTIPLE_COILS, fc15_pdu, 0)
check("ASCII FC15 value=9", wr15.value == 9)

# Write exception
wr_exc = bytes([0x86, 0x02])
try:
    asc._parse_write_response(FunctionCode.WRITE_SINGLE_REGISTER, wr_exc, 0)
    check("ASCII write exc should raise", False)
except ProtocolResponseError:
    check("ASCII write exc raised", True)

# Connection errors
try:
    asc._send_and_receive(b":01030000000AF2\r\n")
    check("ASCII send without serial should raise", False)
except ProtocolConnectionError:
    check("ASCII send without serial raised", True)

print("\n[B6] Shared Exception Descriptions")
from src.protocols.modbus_ascii import ModbusASCIIProtocol as ASCII
from src.protocols.modbus_rtu import ModbusRTUProtocol as RTU

for proto_cls, label in [(RTU, "RTU"), (ASCII, "ASCII")]:
    d1 = proto_cls._get_exception_description(0x01)
    check(f"{label} exc 0x01", "Illegal Function" in d1)
    d2 = proto_cls._get_exception_description(0x02)
    check(f"{label} exc 0x02", "Address" in d2)
    d3 = proto_cls._get_exception_description(0x04)
    check(f"{label} exc 0x04", "Slave Device Failure" in d3)
    d4 = proto_cls._get_exception_description(0xFF)
    check(f"{label} exc 0xFF", "Unknown" in d4)


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"Test Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("\nStep 2.3 ModbusRTU/ASCII -- ALL TESTS PASSED!")
