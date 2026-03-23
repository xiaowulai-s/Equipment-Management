# -*- coding: utf-8 -*-
"""
工业设备管理系统 - 配置管理模块
实现产品Profile配置文件的加载、解析和管理
"""

import json
import yaml
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

from DeviceModels import Device, Register, RegisterType, DeviceStatus

# 用户设置默认值
DEFAULT_USER_SETTINGS = {
    "language": "zh_CN",
    "theme": "dark",
    "auto_connect": True,
    "auto_refresh": True,
    "font_size": "medium",
    "data_refresh_rate": 1000,  # 毫秒
    "show_communication_log": True,
    "log_level": "INFO",
    "max_log_size": 50,  # MB
    "log_backup_count": 10,
    "alarm_sound_enabled": True,
    "alarm_email_enabled": False,
    "email_settings": {
        "smtp_server": "",
        "smtp_port": 587,
        "username": "",
        "password": "",
        "recipient": ""
    },
    "data_export_format": "csv",
    "export_include_headers": True,
    "export_directory": "exports"
}

# 使用统一日志配置
from logging_config import get_logger
logger = get_logger(__name__)


@dataclass
class ProductProfile:
    """产品配置文件数据模型"""
    product_id: str                 # 产品ID
    product_name: str               # 产品名称
    description: str                # 产品描述
    version: str                    # 配置版本
    registers: List[Dict]           # 寄存器配置列表
    communication: Dict[str, Any]   # 通信配置
    ui_layout: Dict[str, Any]       # UI布局配置
    alarms: List[Dict]              # 报警配置
    commands: List[Dict]            # 命令配置


class ConfigManager:
    """
    配置管理器
    负责加载、解析和管理产品Profile配置文件和用户自定义设置
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 产品配置
        self.profiles: Dict[str, ProductProfile] = {}
        self.load_all_profiles()
        
        # 用户设置
        self.user_settings_path = self.config_dir / "user_settings.json"
        self.user_settings: Dict[str, Any] = DEFAULT_USER_SETTINGS.copy()
        self.load_user_settings()

    def load_profile(self, profile_file: str) -> Optional[ProductProfile]:
        """
        加载单个产品配置文件
        
        Args:
            profile_file: 配置文件路径
            
        Returns:
            ProductProfile: 产品配置对象，如果加载失败返回None
        """
        try:
            file_path = self.config_dir / profile_file
            if not file_path.exists():
                logger.error(f"配置文件不存在: {file_path}")
                return None

            # 确定文件格式
            ext = file_path.suffix.lower()
            with open(file_path, 'r', encoding='utf-8') as f:
                if ext in ['.json']:
                    config_data = json.load(f)
                elif ext in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    logger.error(f"不支持的配置文件格式: {ext}")
                    return None

            # 解析配置数据
            profile = ProductProfile(
                product_id=config_data.get("product_id", ""),
                product_name=config_data.get("product_name", ""),
                description=config_data.get("description", ""),
                version=config_data.get("version", "1.0"),
                registers=config_data.get("registers", []),
                communication=config_data.get("communication", {}),
                ui_layout=config_data.get("ui_layout", {}),
                alarms=config_data.get("alarms", []),
                commands=config_data.get("commands", [])
            )

            # 验证配置完整性
            if not self._validate_profile(profile):
                return None

            self.profiles[profile.product_id] = profile
            logger.info(f"已加载配置文件: {profile_file} -> 产品ID: {profile.product_id}")
            return profile

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return None

    def load_all_profiles(self) -> List[ProductProfile]:
        """
        加载所有配置文件
        
        Returns:
            List[ProductProfile]: 加载的产品配置列表
        """
        profiles = []
        for ext in ['.json', '.yaml', '.yml']:
            for file_path in self.config_dir.glob(f"*{ext}"):
                profile = self.load_profile(file_path.name)
                if profile:
                    profiles.append(profile)
        return profiles

    def get_profile(self, product_id: str) -> Optional[ProductProfile]:
        """
        根据产品ID获取配置文件
        
        Args:
            product_id: 产品ID
            
        Returns:
            ProductProfile: 产品配置对象，如果不存在返回None
        """
        return self.profiles.get(product_id)

    def create_profile(self, profile: ProductProfile, file_name: Optional[str] = None) -> bool:
        """
        创建新的配置文件
        
        Args:
            profile: 产品配置对象
            file_name: 文件名，如果为None则使用product_id
            
        Returns:
            bool: 创建成功返回True，否则返回False
        """
        try:
            if file_name is None:
                file_name = f"{profile.product_id}.json"

            file_path = self.config_dir / file_name
            if file_path.exists():
                logger.error(f"配置文件已存在: {file_path}")
                return False

            # 转换为字典
            profile_dict = {
                "product_id": profile.product_id,
                "product_name": profile.product_name,
                "description": profile.description,
                "version": profile.version,
                "registers": profile.registers,
                "communication": profile.communication,
                "ui_layout": profile.ui_layout,
                "alarms": profile.alarms,
                "commands": profile.commands
            }

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(profile_dict, f, ensure_ascii=False, indent=2)

            self.profiles[profile.product_id] = profile
            logger.info(f"已创建配置文件: {file_path}")
            return True

        except Exception as e:
            logger.error(f"创建配置文件失败: {e}")
            return False

    def update_profile(self, profile: ProductProfile) -> bool:
        """
        更新配置文件
        
        Args:
            profile: 产品配置对象
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            # 查找现有配置文件
            file_path = None
            for ext in ['.json', '.yaml', '.yml']:
                potential_path = self.config_dir / f"{profile.product_id}{ext}"
                if potential_path.exists():
                    file_path = potential_path
                    break

            if not file_path:
                logger.error(f"配置文件不存在: {profile.product_id}")
                return False

            # 转换为字典
            profile_dict = {
                "product_id": profile.product_id,
                "product_name": profile.product_name,
                "description": profile.description,
                "version": profile.version,
                "registers": profile.registers,
                "communication": profile.communication,
                "ui_layout": profile.ui_layout,
                "alarms": profile.alarms,
                "commands": profile.commands
            }

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    json.dump(profile_dict, f, ensure_ascii=False, indent=2)
                else:
                    yaml.dump(profile_dict, f, default_flow_style=False, allow_unicode=True)

            self.profiles[profile.product_id] = profile
            logger.info(f"已更新配置文件: {file_path}")
            return True

        except Exception as e:
            logger.error(f"更新配置文件失败: {e}")
            return False

    def delete_profile(self, product_id: str) -> bool:
        """
        删除配置文件
        
        Args:
            product_id: 产品ID
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        try:
            # 查找并删除配置文件
            file_deleted = False
            for ext in ['.json', '.yaml', '.yml']:
                file_path = self.config_dir / f"{product_id}{ext}"
                if file_path.exists():
                    file_path.unlink()
                    file_deleted = True
                    logger.info(f"已删除配置文件: {file_path}")
                    break

            if not file_deleted:
                logger.error(f"配置文件不存在: {product_id}")
                return False

            # 从内存中移除
            if product_id in self.profiles:
                del self.profiles[product_id]

            return True

        except Exception as e:
            logger.error(f"删除配置文件失败: {e}")
            return False

    def _validate_profile(self, profile: ProductProfile) -> bool:
        """
        验证配置文件的完整性
        
        Args:
            profile: 产品配置对象
            
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        if not profile.product_id:
            logger.error("产品ID不能为空")
            return False

        if not profile.product_name:
            logger.error("产品名称不能为空")
            return False

        if not profile.registers:
            logger.warning(f"产品 {profile.product_id} 没有配置寄存器")

        return True

    def load_user_settings(self) -> bool:
        """
        加载用户设置
        
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            if self.user_settings_path.exists():
                with open(self.user_settings_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 合并设置，保留默认值中不存在的键
                    self.user_settings = {**self.user_settings, **loaded_settings}
                    logger.info(f"已加载用户设置: {self.user_settings_path}")
            return True
        except Exception as e:
            logger.error(f"加载用户设置失败: {e}")
            return False

    def save_user_settings(self) -> bool:
        """
        保存用户设置
        
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            with open(self.user_settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.user_settings, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存用户设置: {self.user_settings_path}")
            return True
        except Exception as e:
            logger.error(f"保存用户设置失败: {e}")
            return False

    def get_user_setting(self, key: str, default: Any = None) -> Any:
        """
        获取用户设置
        
        Args:
            key: 设置键名
            default: 默认值
            
        Returns:
            Any: 设置值，如果不存在返回默认值
        """
        # 支持嵌套键，如 "email_settings.smtp_server"
        keys = key.split('.')
        value = self.user_settings
        
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    return default
            return value
        except KeyError:
            return default

    def set_user_setting(self, key: str, value: Any) -> bool:
        """
        设置用户设置
        
        Args:
            key: 设置键名
            value: 设置值
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        try:
            # 支持嵌套键，如 "email_settings.smtp_server"
            keys = key.split('.')
            settings = self.user_settings
            
            for k in keys[:-1]:
                if k not in settings or not isinstance(settings[k], dict):
                    settings[k] = {}
                settings = settings[k]
            
            settings[keys[-1]] = value
            logger.debug(f"已更新用户设置: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"设置用户设置失败: {e}")
            return False

    def reset_user_settings(self) -> bool:
        """
        重置用户设置为默认值
        
        Returns:
            bool: 重置成功返回True，否则返回False
        """
        try:
            self.user_settings = DEFAULT_USER_SETTINGS.copy()
            logger.info("已重置用户设置为默认值")
            return self.save_user_settings()
        except Exception as e:
            logger.error(f"重置用户设置失败: {e}")
            return False

    def create_device_from_profile(self, product_id: str, device_id: str, ip_address: str, 
                                 port: int = 502, slave_id: int = 1) -> Optional[Device]:
        """
        根据配置文件创建设备对象
        
        Args:
            product_id: 产品ID
            device_id: 设备ID
            ip_address: IP地址
            port: 端口
            slave_id: 从机ID
            
        Returns:
            Device: 设备对象，如果创建失败返回None
        """
        profile = self.get_profile(product_id)
        if not profile:
            logger.error(f"产品配置不存在: {product_id}")
            return None

        try:
            device = Device(
                id=device_id,
                name=f"{profile.product_name}-{device_id}",
                ip_address=ip_address,
                port=port,
                slave_id=slave_id,
                status=DeviceStatus.OFFLINE,
                group=profile.product_name,
                description=profile.description
            )

            # 根据配置文件添加寄存器
            for reg_config in profile.registers:
                # 确定寄存器类型
                reg_type_map = {
                    "holding_register": RegisterType.HOLDING_REGISTER,
                    "input_register": RegisterType.INPUT_REGISTER,
                    "coil": RegisterType.COIL,
                    "discrete_input": RegisterType.DISCRETE_INPUT
                }
                reg_type = reg_type_map.get(reg_config.get("type", "holding_register"), RegisterType.HOLDING_REGISTER)

                register = Register(
                    address=reg_config.get("address", 0),
                    name=reg_config.get("name", ""),
                    value=reg_config.get("default_value", 0.0),
                    unit=reg_config.get("unit", ""),
                    register_type=reg_type,
                    raw_value=0,
                    status=0,
                    min_value=reg_config.get("min_value", 0.0),
                    max_value=reg_config.get("max_value", 100.0),
                    scale=reg_config.get("scale", 1.0)
                )

                device.add_register(register)

            logger.info(f"已根据配置创建设备: {device_id} -> 产品: {product_id}")
            return device

        except Exception as e:
            logger.error(f"创建设备失败: {e}")
            return None


# 创建配置目录
def create_config_dir(config_dir: str = "config"):
    """创建配置目录"""
    config_path = Path(config_dir)
    if not config_path.exists():
        config_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"已创建配置目录: {config_path}")


# 导出模块
__all__ = ['ConfigManager', 'ProductProfile', 'create_config_dir']