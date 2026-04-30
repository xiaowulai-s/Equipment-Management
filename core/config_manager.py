# -*- coding: utf-8 -*-
"""
配置管理器 (重构版)
Configuration Manager with Pydantic Validation
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_models import AlarmRuleConfig, ApplicationConfig, DeviceConfig, SystemConfig


class ConfigManager:
    """
    配置管理器 - 支持Pydantic验证和配置热重载
    """

    def __init__(self, config_file: str = "config.json"):
        self._config_file = config_file
        self._config: SystemConfig = SystemConfig()
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not os.path.exists(self._config_file):
            # 创建默认配置
            self._save_config()
            return

        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 使用 Pydantic 验证和解析
            self._config = SystemConfig(**data)
        except Exception as e:
            print(f"加载配置失败: {e}，使用默认配置")
            self._config = SystemConfig()
            self._save_config()

    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._config_file) or ".", exist_ok=True)

            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def reload(self) -> None:
        """热重载配置"""
        self._load_config()

    def save(self) -> None:
        """保存当前配置"""
        self._save_config()

    # ========== 应用配置 ==========

    @property
    def application(self) -> ApplicationConfig:
        """获取应用配置"""
        return self._config.application

    def update_application(self, **kwargs) -> None:
        """更新应用配置"""
        for key, value in kwargs.items():
            if hasattr(self._config.application, key):
                setattr(self._config.application, key, value)
        self._save_config()

    # ========== 设备配置 ==========

    def get_all_devices(self) -> List[DeviceConfig]:
        """获取所有设备配置"""
        return self._config.devices

    def get_device(self, device_id: str) -> Optional[DeviceConfig]:
        """根据ID获取设备配置"""
        for device in self._config.devices:
            if device.device_id == device_id:
                return device
        return None

    def add_device(self, device_config: DeviceConfig) -> str:
        """添加设备配置"""
        import uuid

        if not device_config.device_id:
            device_config.device_id = str(uuid.uuid4())[:8]

        self._config.devices.append(device_config)
        self._save_config()
        return device_config.device_id

    def update_device(self, device_id: str, **kwargs) -> bool:
        """更新设备配置"""
        device = self.get_device(device_id)
        if not device:
            return False

        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)

        self._save_config()
        return True

    def remove_device(self, device_id: str) -> bool:
        """移除设备配置"""
        for i, device in enumerate(self._config.devices):
            if device.device_id == device_id:
                del self._config.devices[i]
                self._save_config()
                return True
        return False

    # ========== 报警规则配置 ==========

    def get_all_alarm_rules(self) -> List[AlarmRuleConfig]:
        """获取所有报警规则"""
        return self._config.alarm_rules

    def get_alarm_rule(self, rule_id: str) -> Optional[AlarmRuleConfig]:
        """根据ID获取报警规则"""
        for rule in self._config.alarm_rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def add_alarm_rule(self, rule_config: AlarmRuleConfig) -> None:
        """添加报警规则"""
        self._config.alarm_rules.append(rule_config)
        self._save_config()

    def update_alarm_rule(self, rule_id: str, **kwargs) -> bool:
        """更新报警规则"""
        rule = self.get_alarm_rule(rule_id)
        if not rule:
            return False

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        self._save_config()
        return True

    def remove_alarm_rule(self, rule_id: str) -> bool:
        """移除报警规则"""
        for i, rule in enumerate(self._config.alarm_rules):
            if rule.rule_id == rule_id:
                del self._config.alarm_rules[i]
                self._save_config()
                return True
        return False

    # ========== 导入导出 ==========

    def export_to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return self._config.model_dump()

    def import_from_dict(self, data: Dict[str, Any]) -> bool:
        """从字典导入"""
        try:
            self._config = SystemConfig(**data)
            self._save_config()
            return True
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False

    def validate_device_config(self, config_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """验证设备配置"""
        try:
            DeviceConfig(**config_dict)
            return True, None
        except Exception as e:
            return False, str(e)
