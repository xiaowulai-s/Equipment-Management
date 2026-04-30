# -*- coding: utf-8 -*-
"""
设备模板管理器
Device Template Manager - 从模板创建/克隆设备
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from core.utils.logger import get_logger

logger = get_logger(__name__)

TEMPLATE_FILE = "device_templates.json"


class DeviceTemplateManager:
    """设备模板管理器 - 支持创建、管理、应用设备模板"""

    def __init__(self, template_file: str = TEMPLATE_FILE) -> None:
        self._template_file = template_file
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        if os.path.exists(self._template_file):
            try:
                with open(self._template_file, "r", encoding="utf-8") as f:
                    self._templates = json.load(f)
            except Exception as e:
                logger.error("加载设备模板失败", error=str(e))
                self._templates = {}

    def _save_templates(self) -> None:
        try:
            with open(self._template_file, "w", encoding="utf-8") as f:
                json.dump(self._templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存设备模板失败", error=str(e))

    def create_template(self, name: str, config: Dict[str, Any], description: str = "") -> str:
        """从设备配置创建模板"""
        template_id = str(uuid.uuid4())[:8]
        template_config = {k: v for k, v in config.items() if k not in ("device_id", "name")}

        self._templates[template_id] = {
            "template_id": template_id,
            "name": name,
            "description": description,
            "config": template_config,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }
        self._save_templates()
        logger.info("设备模板已创建", template_id=template_id, name=name)
        return template_id

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return self._templates.get(template_id)

    def get_all_templates(self) -> List[Dict[str, Any]]:
        return list(self._templates.values())

    def delete_template(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            self._save_templates()
            return True
        return False

    def create_device_from_template(
        self,
        template_id: str,
        device_id: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """从模板创建设备配置"""
        template = self._templates.get(template_id)
        if not template:
            logger.error("模板不存在", template_id=template_id)
            return None

        config = dict(template["config"])
        config["device_id"] = device_id

        if overrides:
            config.update(overrides)

        logger.info("从模板创建设备配置", template_id=template_id, device_id=device_id)
        return config

    def clone_device_config(self, source_config: Dict[str, Any], new_device_id: str) -> Dict[str, Any]:
        """克隆设备配置（生成新ID，清除连接状态）"""
        new_config = dict(source_config)
        new_config["device_id"] = new_device_id

        if "name" in new_config:
            new_config["name"] = f"{new_config['name']} (副本)"

        new_config.pop("use_simulator", None)

        return new_config
