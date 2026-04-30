# -*- coding: utf-8 -*-
"""
配置导入导出服务
Config Import/Export Service - extracted from DeviceManager
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from core.data import DatabaseManager, DeviceRepository
from core.utils.logger import get_logger

if TYPE_CHECKING:
    from .device_manager import DeviceManager

logger = get_logger(__name__)


class ConfigImporterExporter:
    """配置导入导出服务 - 管理设备配置的导入/导出/JSON兼容"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config_file: str = "config.json",
    ) -> None:
        self._db_manager = db_manager
        self._config_file = config_file

    def export_devices_config(
        self,
        device_ids: Optional[List[str]] = None,
        file_path: str = "",
    ) -> bool:
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

            export_data = {
                "version": "2.0",
                "export_time": datetime.now().isoformat(),
                "devices": [repo.to_config(device) for device in devices],
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info("设备配置导出成功", file_path=file_path, device_count=len(export_data["devices"]))
            return True
        except Exception as e:
            logger.error("设备配置导出失败", file_path=file_path, error=str(e))
            return False

    def import_devices_config(
        self,
        file_path: str,
        overwrite: bool = False,
        create_device_internal=None,
        devices_dict: Optional[Dict] = None,
    ) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            if "devices" not in import_data:
                logger.error("导入文件格式错误：缺少devices字段", file_path=file_path)
                return False

            success_count = 0

            with self._db_manager.session() as session:
                repo = DeviceRepository(session)

                for device_config in import_data["devices"]:
                    device_id = device_config.get("device_id")

                    if not device_id:
                        logger.error("导入设备配置缺少device_id", file_path=file_path)
                        continue

                    existing_device = repo.get_by_id(device_id)
                    if existing_device:
                        if overwrite:
                            repo.update_from_config(device_id, device_config)
                            if devices_dict and device_id in devices_dict:
                                try:
                                    devices_dict[device_id].device.disconnect()
                                except Exception:
                                    pass
                                del devices_dict[device_id]
                            if create_device_internal:
                                create_device_internal(device_id, device_config)
                            logger.info("更新设备配置", device_id=device_id, file_path=file_path)
                        else:
                            logger.warning("设备已存在，跳过导入", device_id=device_id, file_path=file_path)
                            continue
                    else:
                        repo.create_from_config(device_config)
                        if create_device_internal and devices_dict and device_id not in devices_dict:
                            create_device_internal(device_id, device_config)
                        logger.info("导入新设备", device_id=device_id, file_path=file_path)

                    success_count += 1

            logger.info(
                "设备配置导入成功",
                file_path=file_path,
                success_count=success_count,
                total_count=len(import_data["devices"]),
            )
            return True
        except Exception as e:
            logger.error("设备配置导入失败", file_path=file_path, error=str(e))
            return False
