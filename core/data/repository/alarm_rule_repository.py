# -*- coding: utf-8 -*-
"""
报警规则数据仓库
Alarm Rule Repository
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..models import AlarmRuleModel
from .base import BaseRepository


class AlarmRuleRepository(BaseRepository[AlarmRuleModel]):
    """报警规则数据仓库"""

    def __init__(self, session: Session):
        super().__init__(session, AlarmRuleModel)

    def get_by_device(self, device_id: str) -> List[AlarmRuleModel]:
        """获取设备的报警规则"""
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.device_id == device_id).all()

    def get_by_parameter(self, device_id: str, parameter: str) -> Optional[AlarmRuleModel]:
        """获取设备特定参数的报警规则"""
        return (
            self._session.query(AlarmRuleModel)
            .filter(and_(AlarmRuleModel.device_id == device_id, AlarmRuleModel.parameter == parameter))
            .first()
        )

    def get_enabled_rules(self) -> List[AlarmRuleModel]:
        """获取所有启用的规则"""
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.enabled == True).all()

    def get_rules_by_level(self, level: int) -> List[AlarmRuleModel]:
        """获取指定级别的规则"""
        return self._session.query(AlarmRuleModel).filter(AlarmRuleModel.level == level).all()

    def create_rule(
        self,
        rule_id: str,
        device_id: str,
        device_name: str,
        parameter: str,
        alarm_type: str,
        level: int,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        description: str = "",
        enabled: bool = True,
    ) -> AlarmRuleModel:
        """创建报警规则"""
        rule = AlarmRuleModel(
            rule_id=rule_id,
            device_id=device_id,
            device_name=device_name,
            parameter=parameter,
            alarm_type=alarm_type,
            level=level,
            threshold_high=threshold_high,
            threshold_low=threshold_low,
            description=description,
            enabled=enabled,
        )
        return self.create(rule)

    def update_rule(self, rule_id: str, **kwargs) -> Optional[AlarmRuleModel]:
        """更新报警规则"""
        rule = self._session.query(AlarmRuleModel).filter(AlarmRuleModel.rule_id == rule_id).first()

        if not rule:
            return None

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        return self.update(rule)

    def delete_rule(self, rule_id: str) -> bool:
        """删除报警规则"""
        rule = self._session.query(AlarmRuleModel).filter(AlarmRuleModel.rule_id == rule_id).first()

        if rule:
            self.delete(rule)
            return True
        return False

    def enable_rule(self, rule_id: str) -> Optional[AlarmRuleModel]:
        """启用报警规则"""
        return self.update_rule(rule_id, enabled=True)

    def disable_rule(self, rule_id: str) -> Optional[AlarmRuleModel]:
        """禁用报警规则"""
        return self.update_rule(rule_id, enabled=False)

    def get_all_rules_with_devices(self) -> List[Dict[str, Any]]:
        """获取所有规则及其设备信息"""
        rules = self._session.query(AlarmRuleModel).all()
        return [rule.to_dict() for rule in rules]

    def cleanup_invalid_rules(self) -> int:
        """清理无效规则（设备已删除的）"""
        # 这个需要在 DeviceManager 中实现级联删除
        # 这里只做标记清理
        invalid_rules = (
            self._session.query(AlarmRuleModel)
            .filter(~AlarmRuleModel.device_id.in_(self._session.query(DeviceModel.id)))
            .all()
        )

        count = len(invalid_rules)
        for rule in invalid_rules:
            self.delete(rule)

        return count
