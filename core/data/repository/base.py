# -*- coding: utf-8 -*-
"""
数据仓库基类
Base Repository Pattern
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """基础数据仓库"""

    def __init__(self, session: Session, model_class: Type[T]):
        self._session = session
        self._model_class = model_class

    def get_by_id(self, id: Any) -> Optional[T]:
        """根据ID获取"""
        return self._session.query(self._model_class).get(id)

    def get_all(self) -> List[T]:
        """获取所有记录"""
        return self._session.query(self._model_class).all()

    def create(self, entity: T) -> T:
        """创建记录"""
        self._session.add(entity)
        self._session.flush()
        return entity

    def update(self, entity: T) -> T:
        """更新记录"""
        self._session.merge(entity)
        self._session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """删除记录"""
        self._session.delete(entity)
        self._session.flush()

    def delete_by_id(self, id: Any) -> bool:
        """根据ID删除"""
        entity = self.get_by_id(id)
        if entity:
            self.delete(entity)
            return True
        return False

    def count(self) -> int:
        """获取记录数"""
        return self._session.query(self._model_class).count()

    def exists(self, id: Any) -> bool:
        """检查记录是否存在"""
        return self.get_by_id(id) is not None
