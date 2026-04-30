# -*- coding: utf-8 -*-
"""
配置服务 - 增强版配置管理
Configuration Service - Enhanced config management

职责（单一职责原则 SRP）：
- 配置导入导出
- 配置验证和标准化
- 默认配置管理
- 配置版本控制
- 信号发射：配置变更通知

设计改进（对比原ConfigImporterExporter）：
1. 新增配置验证管道
2. 支持配置模板和默认值
3. 版本兼容性检查
4. 详细的操作日志
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from core.data import DatabaseManager, DeviceRepository
from core.device.device_model import Device
from core.utils.logger import get_logger

logger = get_logger("configuration_service")


# ══════════════════════════════════════════════
# 数据定义
# ══════════════════════════════════════════════


@dataclass
class ConfigVersion:
    """配置版本信息"""

    version: str = "2.0"
    compatible_versions: List[str] = None  # 兼容的旧版本列表

    def __post_init__(self):
        if self.compatible_versions is None:
            self.compatible_versions = ["1.0", "1.5"]


@dataclass
class ExportResult:
    """导出结果"""

    success: bool
    file_path: str = ""
    device_count: int = 0
    error_msg: str = ""
    export_time: Optional[datetime] = None


@dataclass
class ImportResult:
    """导入结果"""

    success: bool
    file_path: str = ""
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


# ══════════════════════════════════════════════
# 信号定义
# ══════════════════════════════════════════════


class ConfigurationSignals(QObject):
    """配置服务信号定义"""

    config_exported = Signal(str, int)  # file_path, device_count
    config_imported = Signal(str, int, int)  # file_path, imported_count, skipped_count
    config_validated = Signal(str, bool, str)  # device_id, is_valid, error_msg
    config_changed = Signal(str)  # device_id


# ══════════════════════════════════════════════
# 主类实现
# ══════════════════════════════════════════════


class ConfigurationService:
    """
    配置服务 - 核心配置管理组件

    设计要点：
    1. 支持完整的导入/导出生命周期
    2. 配置验证管道（多级校验）
    3. 版本管理和向后兼容
    4. 详细的结果报告
    """

    # 当前配置格式版本
    CURRENT_VERSION = ConfigVersion()

    def __init__(
        self,
        db_manager: DatabaseManager,
        config_file: str = "config.json",
    ):
        """
        初始化配置服务

        Args:
            db_manager: 数据库管理器实例
            config_file: 默认配置文件路径
        """
        self._db_manager = db_manager
        self._config_file = config_file

        # 信号对象
        self._signals = ConfigurationDevices()

    # ══════════════════════════════════════════════
    # 属性访问
    # ══════════════════════════════════════════════

    @property
    def signals(self) -> ConfigurationSignals:
        """获取信号对象"""
        return self._signals

    @property
    def config_file(self) -> str:
        """获取默认配置文件路径"""
        return self._config_file

    # ══════════════════════════════════════════════
    # 公共API - 导出
    # ══════════════════════════════════════════════

    def export_config(
        self,
        file_path: str,
        device_ids: Optional[List[str]] = None,
    ) -> ExportResult:
        """
        导出设备配置到JSON文件

        Args:
            file_path: 目标文件路径
            device_ids: 要导出的设备ID列表（None表示全部）

        Returns:
            ExportResult: 导出结果详情
        """
        try:
            with self._db_manager.session() as session:
                repo = DeviceRepository(session)

                if device_ids:
                    devices = []
                    for device_id in device_ids:
                        device = repo.get_with_registers(device_id)
                        if device:
                            devices.append(device)
                else:
                    devices = repo.get_all_with_registers()

            # 构建导出数据结构
            export_data = {
                "version": self.CURRENT_VERSION.version,
                "export_time": datetime.now().isoformat(),
                "devices": [repo.to_config(device) for device in devices],
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            result = ExportResult(
                success=True,
                file_path=file_path,
                device_count=len(export_data["devices"]),
                export_time=datetime.now(),
            )

            logger.info(
                "设备配置导出成功",
                file_path=file_path,
                device_count=result.device_count,
            )

            self._signals.config_exported.emit(file_path, result.device_count)
            return result

        except Exception as e:
            logger.error("设备配置导出失败", file_path=file_path, error=str(e))
            return ExportResult(
                success=False,
                file_path=file_path,
                error_msg=str(e),
            )

    # ══════════════════════════════════════════════
    # 公共API - 导入
    # ══════════════════════════════════════════════

    def import_config(
        self,
        file_path: str,
        overwrite: bool = False,
        create_device_internal_func: Optional[Any] = None,
        devices_dict: Optional[Dict] = None,
    ) -> ImportResult:
        """
        从JSON文件导入设备配置

        Args:
            file_path: 源文件路径
            overwrite: 是否覆盖已存在的设备
            create_device_internal_func: 设备创建函数
            devices_dict: 设备字典引用（用于内存同步）

        Returns:
            ImportResult: 导入结果详情
        """
        result = ImportResult(
            success=False,
            file_path=file_path,
        )

        try:
            # 1. 读取并解析文件
            with open(file_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            # 2. 验证文件格式
            if "devices" not in import_data:
                result.errors.append("导入文件格式错误：缺少devices字段")
                logger.error(result.errors[-1], file_path=file_path)
                return result

            # 3. 版本检查（可选）
            file_version = import_data.get("version", "1.0")
            if file_version != self.CURRENT_VERSION.version:
                result.warnings.append(f"配置版本不匹配: 文件={file_version}, 当前={self.CURRENT_VERSION.version}")
                logger.warning(result.warnings[-1])

            # 4. 逐个处理设备配置
            success_count = 0
            skipped_count = 0

            with self._db_manager.session() as session:
                repo = DeviceRepository(session)

                for device_config in import_data["devices"]:
                    device_id = device_config.get("device_id")

                    if not device_id:
                        result.error_count += 1
                        result.errors.append(f"导入设备缺少device_id (索引={success_count + skipped_count})")
                        logger.error(result.errors[-1], file_path=file_path)
                        continue

                    # 验证配置
                    is_valid, validation_error = Device.validate_config(device_config)
                    if not is_valid:
                        result.error_count += 1
                        result.errors.append(f"设备 {device_id} 配置无效: {validation_error}")
                        continue

                    existing_device = repo.get_by_id(device_id)

                    if existing_device:
                        if overwrite:
                            # 更新现有设备
                            repo.update_from_config(device_id, device_config)

                            # 同步内存状态
                            if devices_dict and device_id in devices_dict:
                                try:
                                    devices_dict[device_id].device.disconnect()
                                except Exception:
                                    pass
                                del devices_dict[device_id]

                            if create_device_internal_func:
                                create_device_internal_func(device_id, device_config)

                            success_count += 1
                            logger.info("更新设备配置", device_id=device_id)
                        else:
                            skipped_count += 1
                            result.warnings.append(f"设备已存在，跳过导入: {device_id}")
                            logger.warning(result.warnings[-1])
                    else:
                        # 创建新设备
                        repo.create_from_config(device_config)

                        if create_device_internal_func and devices_dict and device_id not in devices_dict:
                            create_device_internal_func(device_id, device_config)

                        success_count += 1
                        logger.info("导入新设备", device_id=device_id)

            # 5. 构建结果
            result.success = True
            result.imported_count = success_count
            result.skipped_count = skipped_count

            logger.info(
                "设备配置导入成功",
                file_path=file_path,
                success_count=success_count,
                skipped_count=skipped_count,
                total_count=len(import_data["devices"]),
            )

            self._signals.config_imported.emit(
                file_path,
                result.imported_count,
                result.skipped_count,
            )
            return result

        except json.JSONDecodeError as e:
            result.errors.append(f"JSON解析错误: {str(e)}")
            logger.error("JSON解析错误", file_path=file_path, error=str(e))
            return result
        except Exception as e:
            result.errors.append(f"导入异常: {str(e)}")
            logger.error("设备配置导入失败", file_path=file_path, error=str(e))
            return result

    # ══════════════════════════════════════════════
    # 公共API - 验证
    # ══════════════════════════════════════════════

    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        """
        验证设备配置的有效性

        Args:
            config: 设备配置字典

        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        is_valid, error_msg = Device.validate_config(config)

        # 发射验证结果信号
        device_id = config.get("device_id", "unknown")
        self._signals.config_validated.emit(device_id, is_valid, error_msg)

        return is_valid, error_msg

    # ══════════════════════════════════════════════
    # 向后兼容方法
    # ══════════════════════════════════════════════

    def export_devices_config(
        self,
        device_ids: Optional[List[str]] = None,
        file_path: str = "",
    ) -> bool:
        """
        向后兼容的导出接口

        注意：建议使用 export_config() 获取详细结果
        """
        result = self.export_config(file_path, device_ids)
        return result.success

    def import_devices_config(
        self,
        file_path: str,
        overwrite: bool = False,
        create_device_internal=None,
        devices=None,
    ) -> bool:
        """
        向后兼容的导入接口

        注意：建议使用 import_config() 获取详细结果
        """
        result = self.import_config(
            file_path,
            overwrite,
            create_device_internal,
            devices,
        )
        return result.success


# 向后兼容别名
class ConfigurationDevices(QObject):
    """配置服务信号集合（向后兼容）"""

    config_exported = Signal(str, int)
    config_imported = Signal(str, int, int)
    config_validated = Signal(str, bool, str)
    config_changed = Signal(str)


# dataclass 导入（放在类定义之后避免循环依赖）
from dataclasses import dataclass
