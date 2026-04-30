# -*- coding: utf-8 -*-
"""
core.engine — 通信引擎层

规范控制点④：MCGS触摸屏为唯一TCP Server，上位机为Client
规范控制点8️⃣：通信-解析-UI三者运行在独立线程空间

模块职责:
- GatewayEngine: 网关通信引擎，管理多网关并发长连接
- ReconnectPolicy: 指数退避重连策略
- HeartbeatManager: 应用层心跳管理（3次无响应强制重置Socket）

数据流:
    GatewayEngine → [TCPDriver → ModbusProtocol] → DataBus.publish()
"""

from core.engine.reconnect_policy import ReconnectPolicy
from core.engine.heartbeat_manager import HeartbeatManager, HeartbeatState
from core.engine.gateway_engine import GatewayEngine, GatewayConfig, GatewayConnection, GatewayState

__all__ = ['ReconnectPolicy', 'HeartbeatManager', 'HeartbeatState', 'GatewayEngine', 'GatewayConfig', 'GatewayConnection', 'GatewayState']
