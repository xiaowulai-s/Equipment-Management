# -*- coding: utf-8 -*-
"""
网关数据模型（Gateway Model）

规范控制点②③④: MCGS触摸屏为唯一TCP Server，上位机为Client
每个网关对应一个长连接，网关下挂载多个变量点

对应 devices.json 中的单个 "gateways" 条目:
{
    "id": "mcgs_gw_1",
    "name": "1号车间MCGS网关",
    "ip": "192.168.31.140",
    "port": 502,
    "variables": [...]
}
"""

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GatewayStatus(IntEnum):
    IDLE = 0
    CONNECTING = 1
    CONNECTED = 2
    POLLING = 3
    RECONNECTING = 4
    DISCONNECTED = 5
    ERROR = 6


@dataclass
class VariablePoint:
    """
    MCGS 变量点数据模型（规范控制点②⑤）

    对应 devices.json 中 gateways[].variables[] 的一个条目。
    每个变量点映射到 MCGS 触摸屏的一个数据区地址。

    地址说明:
        MCGS 变量区的 Modbus 地址从 30001 开始（保持寄存器），
        实际读取时需要 address - 1 偏移（Modbus 协议从 0 开始计数）。
    """

    name: str
    addr: int
    type: str = "float"
    unit: str = ""
    decimal_places: int = 2
    deadband: float = 0.0
    alarm_high: Optional[float] = None
    alarm_low: Optional[float] = None
    writable: bool = False
    description: str = ""

    @property
    def modbus_addr(self) -> int:
        """获取 Modbus 协议实际地址（-1 偏移）"""
        return self.addr - 1 if self.addr > 0 else 0

    @classmethod
    def from_dict(cls, data: dict) -> 'VariablePoint':
        return cls(
            name=data.get("name", ""),
            addr=data.get("addr", data.get("address", 30001)),
            type=data.get("type", "float"),
            unit=data.get("unit", ""),
            decimal_places=data.get("decimal_places", 2),
            deadband=data.get("deadband", 0.0),
            alarm_high=data.get("alarm_high", None),
            alarm_low=data.get("alarm_low", None),
            writable=data.get("writable", False),
            description=data.get("description", ""),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "addr": self.addr,
            "type": self.type,
            "unit": self.unit,
            "decimal_places": self.decimal_places,
            "deadband": self.deadband,
            "alarm_high": self.alarm_high,
            "alarm_low": self.alarm_low,
            "writable": self.writable,
            "description": self.description,
        }


@dataclass
class GatewayModel:
    """
    网关数据模型（规范控制点④核心建模）

    职责:
    1. 封装 MCGS 网关的连接配置信息
    2. 管理该网关下挂载的所有变量点
    3. 提供运行时状态跟踪

    架构位置:
        DeviceManager (v4.0 网关化)
        ├── _devices (Dict[str, DevicePollInfo])     ← 旧模式：直接设备连接
        └── _gateway_engine (GatewayEngine)           ← 新模式：网关化连接
            ├── GatewayConnection (gw_1)              ← 长连接线程
            │   └── variables: [VariablePoint, ...]   ← 变量点列表
            └── GatewayConnection (gw_2)
                └── variables: [VariablePoint, ...]
    """

    id: str
    name: str
    ip: str
    port: int = 502
    unit_id: int = 1
    timeout_ms: int = 3000
    byte_order: str = "CDAB"
    polling_interval_ms: int = 1000
    heartbeat_interval_ms: int = 10000
    max_heartbeat_failures: int = 3
    reconnect_config: Dict[str, Any] = field(default_factory=dict)
    variables: List[VariablePoint] = field(default_factory=list)

    status: GatewayStatus = GatewayStatus.IDLE
    error_message: str = ""
    poll_count: int = 0
    error_count: int = 0
    last_poll_time: Optional[float] = None
    connected_at: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'GatewayModel':
        variables = []
        for var_data in data.get("variables", []):
            try:
                variables.append(VariablePoint.from_dict(var_data))
            except Exception as e:
                logger.warning("解析变量点失败: %s, 错误: %s", var_data, e)

        reconnect_cfg = data.get("reconnect", {
            "enabled": True,
            "initial_delay_ms": 1000,
            "max_delay_ms": 30000,
            "multiplier": 2.0,
            "max_attempts": 10,
        })

        return cls(
            id=data.get("id", ""),
            name=data.get("name", data.get("ip", "")),
            ip=data.get("ip", "127.0.0.1"),
            port=data.get("port", 502),
            unit_id=data.get("unit_id", 1),
            timeout_ms=data.get("timeout_ms", 3000),
            byte_order=data.get("byte_order", "CDAB"),
            polling_interval_ms=data.get("polling_interval_ms", 1000),
            heartbeat_interval_ms=data.get("heartbeat_interval_ms", 10000),
            max_heartbeat_failures=data.get("max_heartbeat_failures", 3),
            reconnect_config=reconnect_cfg,
            variables=variables,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "unit_id": self.unit_id,
            "timeout_ms": self.timeout_ms,
            "byte_order": self.byte_order,
            "polling_interval_ms": self.polling_interval_ms,
            "heartbeat_interval_ms": self.heartbeat_interval_ms,
            "max_heartbeat_failures": self.max_heartbeat_failures,
            "reconnect": self.reconnect_config,
            "variables": [v.to_dict() for v in self.variables],
        }

    def get_variable(self, name: str) -> Optional[VariablePoint]:
        for v in self.variables:
            if v.name == name:
                return v
        return None

    def get_variable_names(self) -> List[str]:
        return [v.name for v in self.variables]

    @property
    def is_connected(self) -> bool:
        return self.status in (
            GatewayStatus.CONNECTED,
            GatewayStatus.POLLING,
        )

    @property
    def variable_count(self) -> int:
        return len(self.variables)

    @property
    def connection_key(self) -> str:
        return f"{self.ip}:{self.port}"

    def __repr__(self) -> str:
        return (
            f"GatewayModel(id={self.id}, name={self.name}, "
            f"{self.ip}:{self.port}, vars={len(self.variables)}, "
            f"status={self.status.name})"
        )
