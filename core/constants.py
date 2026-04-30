# -*- coding: utf-8 -*-
"""
项目中文字符串常量
Centralized Chinese string constants for future i18n support
"""

FAULT_TYPE_NAMES = {
    "communication_timeout": "通信超时",
    "connection_refused": "连接被拒绝",
    "invalid_response": "无效响应",
    "device_offline": "设备离线",
    "protocol_error": "协议错误",
    "unknown": "未知错误",
}

ALARM_LEVEL_NAMES = {
    "info": "信息",
    "warning": "警告",
    "critical": "严重",
    "emergency": "紧急",
}

ALARM_LEVEL_NAMES_BY_INT = {
    0: "信息",
    1: "警告",
    2: "错误",
    3: "严重",
}

DEVICE_STATUS_NAMES = {
    0: "离线",
    1: "在线",
    2: "报警",
    3: "错误",
}

ERROR_KEYWORDS = {
    "timeout": ["timeout", "timed out", "超时"],
    "connection_refused": ["connection refused", "connect failed", "连接被拒绝", "连接失败"],
    "invalid_response": ["invalid", "wrong", "无效", "错误"],
    "device_offline": ["offline", "disconnected", "离线", "断开"],
    "protocol_error": ["protocol", "modbus", "协议"],
}

PARITY_OPTIONS = ["无校验", "偶校验", "奇校验"]

DEFAULT_GROUP_NAME = "默认分组"

ERROR_ENHANCE_PREFIXES = {
    "communication_timeout_tcp": "TCP连接超时",
    "communication_timeout_serial": "串口连接超时",
    "communication_timeout": "通信超时",
    "connection_refused": "连接被拒绝",
    "invalid_response": "无效响应",
    "device_offline": "设备离线",
    "protocol_error": "协议错误",
    "port_error": "端口错误",
    "host_error": "主机地址错误",
    "connect_failed": "连接失败",
}
