"""
FastAPI dependency injection.

Provides reusable dependencies for route handlers.
Following FastAPI's dependency injection pattern for clean separation.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.logging import get_logger
from app.db.session import get_async_session

logger = get_logger(__name__)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async for session in get_async_session():
        yield session


def get_settings() -> Settings:
    """
    Dependency that provides application settings.

    Usage:
        @router.get("/config")
        async def get_config(settings: Settings = Depends(get_settings)):
            ...
    """
    return settings


async def get_request_id(request: Request) -> str | None:
    """
    Extract correlation ID from request headers.

    Returns:
        The X-Request-ID header value, or None.
    """
    return request.headers.get("X-Request-ID")
