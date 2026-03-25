# -*- coding: utf-8 -*-
"""
UI 模块
UI Module
"""

from .styles import AppStyles
from .device_type_dialogs import DeviceTypeDialog, DeviceTypeEditDialog
from .add_device_dialog import AddDeviceDialog
from .batch_operations_dialog import BatchOperationsDialog
from .alarm_config_dialog import AlarmRuleConfigDialog, RuleEditDialog
from .register_config_dialog import RegisterConfigDialog, RegisterEditDialog

__all__ = [
    'AppStyles',
    'DeviceTypeDialog',
    'DeviceTypeEditDialog',
    'AddDeviceDialog',
    'BatchOperationsDialog',
    'AlarmRuleConfigDialog',
    'RuleEditDialog',
    'RegisterConfigDialog',
    'RegisterEditDialog',
]
