# -*- coding: utf-8 -*-
"""
变量点数据模型（Variable Model）

规范控制点②⑤: MCGS变量区映射

本模块提供 VariablePoint 数据类型及其集合操作。
核心类 VariablePoint 定义在 gateway_model.py 中（网关-变量紧密耦合），
此处仅做便捷导出和扩展。
"""

from core.device.gateway_model import VariablePoint, GatewayStatus


__all__ = ['VariablePoint', 'GatewayStatus']
