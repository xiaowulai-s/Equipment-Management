# -*- coding: utf-8 -*-
"""Shared repository base class."""

from __future__ import annotations

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic CRUD repository bound to one SQLAlchemy model.

    The repository exposes thin session-backed helpers and leaves query
    specialization to concrete subclasses.
    """

    def __init__(self, session: Session, model_class: Type[T]) -> None:
        self._session = session
        self._model_class = model_class

    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """Return one entity by primary key."""
        return self._session.get(self._model_class, entity_id)

    def get_all(self) -> List[T]:
        """Return all entities for the model."""
        return self._session.query(self._model_class).all()

    def create(self, entity: T) -> T:
        """Add and flush a new entity."""
        self._session.add(entity)
        self._session.flush()
        return entity

    def update(self, entity: T) -> T:
        """Merge and flush an entity."""
        merged = self._session.merge(entity)
        self._session.flush()
        return merged

    def delete(self, entity: T) -> None:
        """Delete and flush an entity."""
        self._session.delete(entity)
        self._session.flush()

    def delete_by_id(self, entity_id: Any) -> bool:
        """Delete one entity by primary key."""
        entity = self.get_by_id(entity_id)
        if entity is None:
            return False
        self.delete(entity)
        return True

    def count(self) -> int:
        """Return entity count."""
        return self._session.query(self._model_class).count()

    def exists(self, entity_id: Any) -> bool:
        """Return whether one entity exists by primary key."""
        return self.get_by_id(entity_id) is not None
