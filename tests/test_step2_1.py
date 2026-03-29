"""步骤2.1 验证测试 - 枚举 + 协议基类"""

import sys

sys.path.insert(0, ".")

# ── 1. 枚举测试 ──
from src.protocols.enums import DataType, DeviceStatus, Endian, FunctionCode, ProtocolType, RegisterType

pt = ProtocolType.from_string("modbus_tcp")
assert pt == ProtocolType.MODBUS_TCP
pt2 = ProtocolType.from_string("Modbus-TCP")
assert pt2 == ProtocolType.MODBUS_TCP
print("[枚举] ProtocolType.from_string: OK")

assert FunctionCode.READ_HOLDING_REGISTERS.is_read is True
assert FunctionCode.READ_HOLDING_REGISTERS.is_write is False
assert FunctionCode.WRITE_SINGLE_REGISTER.is_write is True
assert FunctionCode.READ_HOLDING_REGISTERS.is_register_access is True
assert FunctionCode.READ_COILS.is_bit_access is True
print(f"[枚举] FC03描述: {FunctionCode.READ_HOLDING_REGISTERS.description}")

assert DeviceStatus.CONNECTED.is_connected is True
assert DeviceStatus.DISCONNECTED.is_connected is False
print(f"[枚举] DeviceStatus: {DeviceStatus.CONNECTED.display_text}")

assert RegisterType.HOLDING_REGISTER.read_function_code == FunctionCode.READ_HOLDING_REGISTERS
assert RegisterType.COIL.read_function_code == FunctionCode.READ_COILS
print("[枚举] RegisterType映射: OK")

assert DataType.FLOAT32.register_count == 2
assert DataType.FLOAT32.byte_size == 4
assert DataType.UINT16.format_char == "H"
assert DataType.FLOAT32.format_char == "f"
print("[枚举] DataType属性: OK")

# ── 2. 编解码测试 ──
import struct

from src.protocols.base_protocol import BaseProtocol, ReadResult, WriteResult

raw = bytes([0x00, 0x64, 0x01, 0x2C])
values = BaseProtocol._decode_registers(raw, 2, DataType.UINT16)
assert values == [100, 300], f"Expected [100, 300], got {values}"
print(f"[编解码] UINT16解码: {values}")

float_bytes = struct.pack(">f", 25.5)
values = BaseProtocol._decode_registers(float_bytes, 2, DataType.FLOAT32)
assert abs(values[0] - 25.5) < 0.01
print(f"[编解码] FLOAT32解码: {values[0]}")

int32_bytes = struct.pack(">i", -1000)
values = BaseProtocol._decode_registers(int32_bytes, 2, DataType.INT32)
assert values[0] == -1000
print(f"[编解码] INT32解码: {values[0]}")

encoded = BaseProtocol._encode_registers([100, 200], DataType.UINT16)
assert encoded == bytes([0x00, 0x64, 0x00, 0xC8])
print(f"[编解码] UINT16编码: {encoded.hex()}")

encoded = BaseProtocol._encode_registers([25.5], DataType.FLOAT32)
decoded = struct.unpack(">f", encoded)[0]
assert abs(decoded - 25.5) < 0.01
print(f"[编解码] FLOAT32编码->解码: {decoded}")

# BOOL解码
bool_raw = bytes([0xFF, 0x00, 0x00, 0x00])
bool_vals = BaseProtocol._decode_registers(bool_raw, 2, DataType.BOOL)
assert bool_vals[0] is True
assert bool_vals[1] is False
print(f"[编解码] BOOL解码: {bool_vals}")

# ── 3. 结果容器测试 ──
result = ReadResult(
    function_code=3,
    start_address=0,
    values=[100, 200, 300],
    raw_data=b"\x00\x64\x01\x2c\x01\x2c",
)
d = result.to_dict()
assert d["success"] is True
assert d["values"] == [100, 200, 300]
print(f"[结果] ReadResult.to_dict: success={d['success']}, values={d['values']}")

err = ReadResult.error("超时", function_code=3, address=100)
assert err.success is False
assert err.error_message == "超时"
print(f"[结果] ReadResult.error: {err.error_message}")

wr = WriteResult(function_code=6, address=1, value=500)
wd = wr.to_dict()
assert wd["success"] is True
assert wd["value"] == 500
print(f"[结果] WriteResult.to_dict: value={wd['value']}")

# ── 4. 地址校验 ──
try:
    BaseProtocol._validate_address_range(0xFFFF, 10, 2000)
    assert False, "应抛出异常"
except Exception as e:
    print(f"[校验] 地址溢出检测: {e.error_code}")

try:
    BaseProtocol._validate_address_range(0, 0, 100)
    assert False, "应抛出异常"
except Exception as e:
    print(f"[校验] 数量为0检测: {e.error_code}")

try:
    BaseProtocol._validate_address(0x10000)
    assert False, "应抛出异常"
except Exception as e:
    print(f"[校验] 地址超限检测: {e.error_code}")

print()
print("=== 步骤2.1 全部测试通过 ===")
