"""
Repository 模式 - 泛型数据仓库基类

设计原则:
    1. 泛型CRUD: 所有仓库继承 BaseRepository[T], 自动获得基础增删改查
    2. 仅flush不commit: 事务控制权交给 DatabaseManager.session() 上下文
    3. 不捕获异常: 让异常传播到 session 上下文或上层服务
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """泛型CRUD仓库基类

    用法:
        class DeviceRepo(BaseRepository[DeviceModel]):
            def __init__(self, session: Session):
                super().__init__(session, DeviceModel)

            def get_by_name(self, name: str) -> Optional[DeviceModel]:
                return self._session.query(DeviceModel)
                    .filter(DeviceModel.name == name).first()
    """

    def __init__(self, session: Session, model_class: Type[T]) -> None:
        self._session = session
        self._model_class = model_class

    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """按主键查询"""
        return self._session.get(self._model_class, entity_id)

    def get_all(self) -> List[T]:
        """查询全部"""
        return self._session.query(self._model_class).all()

    def create(self, entity: T) -> T:
        """新增 (flush, 不commit)"""
        self._session.add(entity)
        self._session.flush()
        return entity

    def update(self, entity: T) -> T:
        """更新 (merge + flush, 不commit)"""
        merged = self._session.merge(entity)
        self._session.flush()
        return merged

    def delete(self, entity: T) -> None:
        """删除 (flush, 不commit)"""
        self._session.delete(entity)
        self._session.flush()

    def delete_by_id(self, entity_id: Any) -> bool:
        """按主键删除"""
        entity = self.get_by_id(entity_id)
        if entity is None:
            return False
        self.delete(entity)
        return True

    def count(self) -> int:
        """计数"""
        return self._session.query(self._model_class).count()

    def exists(self, entity_id: Any) -> bool:
        """是否存在"""
        return self.get_by_id(entity_id) is not None
