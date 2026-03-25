# -*- coding: utf-8 -*-
"""
报警规则持久化管理器
Alarm Rule Persistence Manager
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.utils.alarm_manager import AlarmLevel, AlarmRule
from core.utils.logger import get_logger

from .models import DatabaseManager
from .repository.alarm_rule_repository import AlarmRuleRepository

logger = get_logger(__name__)


class AlarmRulePersistenceManager:
    """报警规则持久化管理器 - 负责报警规则的存储和加载"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化报警规则持久化管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self._db_manager = db_manager
        self._repository: Optional[AlarmRuleRepository] = None

    def _get_repository(self) -> AlarmRuleRepository:
        """获取数据仓库实例"""
        if self._repository is None:
            session = self._db_manager.get_session()
            self._repository = AlarmRuleRepository(session)
        return self._repository

    def save_rule(self, rule: AlarmRule) -> bool:
        """
        保存报警规则到数据库

        Args:
            rule: 报警规则对象

        Returns:
            bool: 保存成功返回 True
        """
        try:
            repo = self._get_repository()

            # 检查规则是否已存在
            existing_rule = repo.get_by_parameter(rule.device_id, rule.parameter)

            if existing_rule:
                # 更新现有规则
                return (
                    repo.update_rule(
                        existing_rule.rule_id,
                        device_name=rule.device_name,
                        alarm_type=rule.alarm_type,
                        level=rule.level,
                        threshold_high=rule.threshold_high,
                        threshold_low=rule.threshold_low,
                        description=rule.description,
                        enabled=rule.enabled,
                    )
                    is not None
                )
            else:
                # 创建新规则
                rule_id = rule.rule_id or str(uuid.uuid4())[:8]
                return (
                    repo.create_rule(
                        rule_id=rule_id,
                        device_id=rule.device_id,
                        device_name=rule.device_name,
                        parameter=rule.parameter,
                        alarm_type=rule.alarm_type,
                        level=rule.level,
                        threshold_high=rule.threshold_high,
                        threshold_low=rule.threshold_low,
                        description=rule.description,
                        enabled=rule.enabled,
                    )
                    is not None
                )

        except Exception as e:
            logger.error(f"保存报警规则失败：{str(e)}")
            return False

    def load_rule(self, device_id: str, parameter: str) -> Optional[AlarmRule]:
        """
        从数据库加载单个报警规则

        Args:
            device_id: 设备 ID
            parameter: 参数名称

        Returns:
            Optional[AlarmRule]: 报警规则对象，不存在返回 None
        """
        try:
            repo = self._get_repository()
            rule_model = repo.get_by_parameter(device_id, parameter)

            if not rule_model:
                return None

            return self._model_to_rule(rule_model)

        except Exception as e:
            logger.error(f"加载报警规则失败：{str(e)}")
            return None

    def load_all_rules(self) -> List[AlarmRule]:
        """
        从数据库加载所有报警规则

        Returns:
            List[AlarmRule]: 报警规则列表
        """
        try:
            repo = self._get_repository()
            rule_models = repo.get_enabled_rules()

            rules = []
            for model in rule_models:
                rule = self._model_to_rule(model)
                rules.append(rule)

            logger.info(f"加载了 {len(rules)} 条报警规则")
            return rules

        except Exception as e:
            logger.error(f"加载所有报警规则失败：{str(e)}")
            return []

    def load_rules_by_device(self, device_id: str) -> List[AlarmRule]:
        """
        加载指定设备的所有报警规则

        Args:
            device_id: 设备 ID

        Returns:
            List[AlarmRule]: 报警规则列表
        """
        try:
            repo = self._get_repository()
            rule_models = repo.get_by_device(device_id)

            rules = []
            for model in rule_models:
                rule = self._model_to_rule(model)
                rules.append(rule)

            return rules

        except Exception as e:
            logger.error(f"加载设备报警规则失败：{str(e)}")
            return []

    def delete_rule(self, rule_id: str) -> bool:
        """
        删除报警规则

        Args:
            rule_id: 规则 ID

        Returns:
            bool: 删除成功返回 True
        """
        try:
            repo = self._get_repository()
            return repo.delete_rule(rule_id)

        except Exception as e:
            logger.error(f"删除报警规则失败：{str(e)}")
            return False

    def delete_rules_by_device(self, device_id: str) -> int:
        """
        删除设备的所有报警规则

        Args:
            device_id: 设备 ID

        Returns:
            int: 删除的规则数量
        """
        try:
            rules = self.load_rules_by_device(device_id)
            count = 0

            for rule in rules:
                if self.delete_rule(rule.rule_id):
                    count += 1

            return count

        except Exception as e:
            logger.error(f"删除设备报警规则失败：{str(e)}")
            return 0

    def enable_rule(self, rule_id: str) -> bool:
        """
        启用报警规则

        Args:
            rule_id: 规则 ID

        Returns:
            bool: 操作成功返回 True
        """
        try:
            repo = self._get_repository()
            return repo.enable_rule(rule_id) is not None

        except Exception as e:
            logger.error(f"启用报警规则失败：{str(e)}")
            return False

    def disable_rule(self, rule_id: str) -> bool:
        """
        禁用报警规则

        Args:
            rule_id: 规则 ID

        Returns:
            bool: 操作成功返回 True
        """
        try:
            repo = self._get_repository()
            return repo.disable_rule(rule_id) is not None

        except Exception as e:
            logger.error(f"禁用报警规则失败：{str(e)}")
            return False

    def _model_to_rule(self, model: Any) -> AlarmRule:
        """
        将数据库模型转换为 AlarmRule 对象

        Args:
            model: AlarmRuleModel 实例

        Returns:
            AlarmRule: 报警规则对象
        """
        rule = AlarmRule(
            rule_id=model.rule_id,
            device_id=model.device_id,
            device_name=model.device_name,
            parameter=model.parameter,
            alarm_type=model.alarm_type,
            level=model.level,
            threshold_high=model.threshold_high,
            threshold_low=model.threshold_low,
            description=model.description,
            enabled=model.enabled,
        )

        return rule

    def export_rules(self) -> List[Dict[str, Any]]:
        """
        导出所有规则为字典列表

        Returns:
            List[Dict]: 规则字典列表
        """
        try:
            repo = self._get_repository()
            return repo.get_all_rules_with_devices()

        except Exception as e:
            logger.error(f"导出报警规则失败：{str(e)}")
            return []

    def import_rules(self, rules_data: List[Dict[str, Any]]) -> int:
        """
        导入规则

        Args:
            rules_data: 规则字典列表

        Returns:
            int: 成功导入的规则数量
        """
        count = 0

        for rule_data in rules_data:
            try:
                rule = AlarmRule(
                    rule_id=rule_data.get("rule_id"),
                    device_id=rule_data.get("device_id"),
                    device_name=rule_data.get("device_name"),
                    parameter=rule_data.get("parameter"),
                    alarm_type=rule_data.get("alarm_type"),
                    level=rule_data.get("level", 1),
                    threshold_high=rule_data.get("threshold_high"),
                    threshold_low=rule_data.get("threshold_low"),
                    description=rule_data.get("description", ""),
                    enabled=rule_data.get("enabled", True),
                )

                if self.save_rule(rule):
                    count += 1

            except Exception as e:
                logger.error(f"导入规则 {rule_data.get('rule_id')} 失败：{str(e)}")
                continue

        logger.info(f"成功导入 {count} 条报警规则")
        return count

    def close(self):
        """关闭管理器，释放资源"""
        try:
            if self._repository:
                self._repository._session.close()
                self._repository = None
            logger.info("报警规则持久化管理器已关闭")
        except Exception as e:
            logger.error(f"关闭管理器失败：{str(e)}")
