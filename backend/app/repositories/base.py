"""
Generic repository pattern — data access layer.

Provides a standard CRUD interface that all repositories extend.
Ensures consistent data access patterns across the application.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic repository with standard CRUD and query operations.
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get(self, id: Any) -> ModelType | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def find_one(self, **filters: Any) -> ModelType | None:
        """Find a single record matching all filters."""
        stmt = select(self.model)
        for field, value in filters.items():
            if not hasattr(self.model, field):
                continue
            stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_many(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        descending: bool = False,
        **filters: Any,
    ) -> list[ModelType]:
        stmt = select(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            stmt = stmt.order_by(col.desc() if descending else col.asc())
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, id: Any, **kwargs: Any) -> ModelType | None:
        stmt = (
            sa_update(self.model)
            .where(self.model.id == id)  # type: ignore[attr-defined]
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: Any, hard: bool = False) -> bool:
        if hard or not hasattr(self.model, "deleted_at"):
            result = await self.session.execute(
                sa_delete(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
            )
        else:
            from sqlalchemy import func as sa_func
            result = await self.session.execute(
                sa_update(self.model)
                .where(self.model.id == id)  # type: ignore[attr-defined]
                .values(deleted_at=sa_func.now())
            )
        await self.session.flush()
        return result.rowcount > 0

    async def count(self, **filters: Any) -> int:
        from sqlalchemy.sql.functions import count as sa_count
        stmt = select(sa_count(self.model.id))  # type: ignore[attr-defined]
        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, **filters: Any) -> bool:
        from sqlalchemy import exists as sa_exists
        stmt = sa_exists(
            select(self.model).where(
                *[getattr(self.model, field) == value for field, value in filters.items()]
            )
        ).select()
        result = await self.session.execute(stmt)
        return result.scalar() or False
