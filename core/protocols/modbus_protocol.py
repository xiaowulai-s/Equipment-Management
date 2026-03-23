# -*- coding: utf-8 -*-
"""
Modbus协议实现
Modbus Protocol Implementation
"""

import struct
import time
from typing import Optional, List, Dict, Any
from .base_protocol import BaseProtocol


class ModbusProtocol(BaseProtocol):
    """
    Modbus协议实现
    Modbus Protocol Implementation
    """

    # 功能码
    FC_READ_HOLDING_REGISTERS = 0x03
    FC_READ_INPUT_REGISTERS = 0x04
    FC_WRITE_SINGLE_REGISTER = 0x06
    FC_WRITE_MULTIPLE_REGISTERS = 0x10

    def __init__(self, driver=None, parent=None, mode="TCP", unit_id=1):
        super().__init__(driver, parent)
        self._mode = mode  # "TCP" or "RTU"
        self._unit_id = unit_id
        self._transaction_id = 0
        self._retry_count = 3
        self._retry_interval = 0.5

    @staticmethod
    def crc16(data: bytes) -> int:
        """
        计算CRC16校验
        Calculate CRC16 checksum
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc

    def _build_tcp_header(self, length: int) -> bytes:
        """
        构建Modbus TCP头部
        Build Modbus TCP header
        """
        self._transaction_id = (self._transaction_id + 1) % 65536
        return struct.pack(
            '>HHH',
            self._transaction_id,  # Transaction ID
            0x0000,               # Protocol ID (0 = Modbus)
            length                # Length (bytes to follow)
        )

    def _build_rtu_frame(self, pdu: bytes) -> bytes:
        """
        构建Modbus RTU帧
        Build Modbus RTU frame
        """
        frame = bytes([self._unit_id]) + pdu
        crc = self.crc16(frame)
        return frame + struct.pack('<H', crc)

    def initialize(self) -> bool:
        """
        初始化协议
        Initialize protocol
        """
        if not self._driver:
            self.error_occurred.emit("未设置通信驱动")
            return False
        return True

    def read_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        读取保持寄存器
        Read holding registers (FC 03)
        """
        return self._read_registers(address, count, self.FC_READ_HOLDING_REGISTERS)

    def read_input_registers(self, address: int, count: int) -> Optional[List[int]]:
        """
        读取输入寄存器
        Read input registers (FC 04)
        """
        return self._read_registers(address, count, self.FC_READ_INPUT_REGISTERS)

    def _read_registers(self, address: int, count: int, function_code: int) -> Optional[List[int]]:
        """
        读取寄存器的内部方法
        Internal method for reading registers
        """
        if not self._driver or not self._driver.is_connected():
            self.error_occurred.emit("设备未连接")
            return None

        for attempt in range(self._retry_count):
            try:
                # 构建请求PDU
                pdu = struct.pack('>BHH', function_code, address, count)

                # 根据模式构建完整帧
                if self._mode == "TCP":
                    request = self._build_tcp_header(6 + 1) + pdu
                else:
                    request = self._build_rtu_frame(pdu)

                # 发送请求
                self.command_sent.emit(request)
                if not self._driver.send_data(request):
                    if attempt == self._retry_count - 1:
                        return None
                    time.sleep(self._retry_interval)
                    continue

                # 等待响应
                time.sleep(0.1)
                response = self._driver._get_buffer()

                if response:
                    self.response_received.emit(response)
                    return self._parse_read_response(response, function_code, count)

            except Exception as e:
                self.error_occurred.emit(f"读取寄存器失败: {str(e)}")
                if attempt == self._retry_count - 1:
                    return None
                time.sleep(self._retry_interval)

        return None

    def _parse_read_response(self, response: bytes, function_code: int, count: int) -> Optional[List[int]]:
        """
        解析读取响应
        Parse read response
        """
        try:
            if self._mode == "TCP":
                # TCP模式：跳过MBAP头（7字节）
                if len(response) < 9:
                    return None
                pdu = response[7:]
            else:
                # RTU模式：验证CRC
                if len(response) < 5:
                    return None
                expected_crc = struct.unpack('<H', response[-2:])[0]
                actual_crc = self.crc16(response[:-2])
                if expected_crc != actual_crc:
                    self.error_occurred.emit("CRC校验失败")
                    return None
                pdu = response[1:-2]

            # 解析PDU
            if len(pdu) < 2:
                return None

            fc = pdu[0]
            if fc != function_code and fc != (function_code | 0x80):
                return None

            if fc & 0x80:
                # 异常响应
                self.error_occurred.emit(f"Modbus异常: 代码 {pdu[1]}")
                return None

            byte_count = pdu[1]
            if len(pdu) < 2 + byte_count:
                return None

            # 解析寄存器值
            registers = []
            for i in range(count):
                if 2 + i * 2 + 1 < len(pdu):
                    reg_val = struct.unpack('>H', pdu[2 + i * 2:4 + i * 2])[0]
                    registers.append(reg_val)

            return registers

        except Exception as e:
            self.error_occurred.emit(f"解析响应失败: {str(e)}")
            return None

    def write_register(self, address: int, value: int) -> bool:
        """
        写入单个寄存器
        Write single register (FC 06)
        """
        if not self._driver or not self._driver.is_connected():
            self.error_occurred.emit("设备未连接")
            return False

        for attempt in range(self._retry_count):
            try:
                # 构建请求PDU
                pdu = struct.pack('>BHH', self.FC_WRITE_SINGLE_REGISTER, address, value)

                # 根据模式构建完整帧
                if self._mode == "TCP":
                    request = self._build_tcp_header(6 + 1) + pdu
                else:
                    request = self._build_rtu_frame(pdu)

                # 发送请求
                self.command_sent.emit(request)
                if not self._driver.send_data(request):
                    if attempt == self._retry_count - 1:
                        return False
                    time.sleep(self._retry_interval)
                    continue

                # 等待响应
                time.sleep(0.1)
                return True

            except Exception as e:
                self.error_occurred.emit(f"写入寄存器失败: {str(e)}")
                if attempt == self._retry_count - 1:
                    return False
                time.sleep(self._retry_interval)

        return False

    def write_registers(self, address: int, values: List[int]) -> bool:
        """
        写入多个寄存器
        Write multiple registers (FC 10)
        """
        if not self._driver or not self._driver.is_connected():
            self.error_occurred.emit("设备未连接")
            return False

        for attempt in range(self._retry_count):
            try:
                count = len(values)
                byte_count = count * 2

                # 构建请求PDU
                pdu = struct.pack('>BHHB', self.FC_WRITE_MULTIPLE_REGISTERS, address, count, byte_count)
                for value in values:
                    pdu += struct.pack('>H', value)

                # 根据模式构建完整帧
                if self._mode == "TCP":
                    request = self._build_tcp_header(6 + 3 + byte_count) + pdu
                else:
                    request = self._build_rtu_frame(pdu)

                # 发送请求
                self.command_sent.emit(request)
                if not self._driver.send_data(request):
                    if attempt == self._retry_count - 1:
                        return False
                    time.sleep(self._retry_interval)
                    continue

                # 等待响应
                time.sleep(0.1)
                return True

            except Exception as e:
                self.error_occurred.emit(f"写入多个寄存器失败: {str(e)}")
                if attempt == self._retry_count - 1:
                    return False
                time.sleep(self._retry_interval)

        return False

    def poll_data(self) -> Dict[str, Any]:
        """
        轮询数据
        Poll data from device
        """
        result = {}

        if not self._register_map:
            return result

        # 按地址范围分组，进行批量读取
        # 这里简化处理，实际可以优化为批量读取策略
        for reg in self._register_map:
            addr = reg.get("address", 0)
            name = reg.get("name", f"reg_{addr}")
            scale = reg.get("scale", 1.0)
            data_type = reg.get("type", "uint16")

            # 读取单个寄存器
            values = self.read_registers(addr, 1)
            if values and len(values) > 0:
                raw_value = values[0]

                # 根据数据类型解析
                if data_type == "int16":
                    value = struct.unpack('h', struct.pack('H', raw_value))[0]
                else:
                    value = raw_value

                # 应用缩放因子
                value = value * scale

                result[name] = {
                    "raw": raw_value,
                    "value": value,
                    "address": addr
                }

        if result:
            self.data_updated.emit(result)

        return result

    def set_mode(self, mode: str):
        """
        设置模式 (TCP/RTU)
        Set mode (TCP/RTU)
        """
        self._mode = mode

    def set_unit_id(self, unit_id: int):
        """
        设置单元ID
        Set unit ID
        """
        self._unit_id = unit_id
