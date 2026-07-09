"""
Database session management.

Provides async and sync database sessions with connection pooling
and proper lifecycle management.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Async Engine & Session ──────────────────────────────────────────────────

async_engine = create_async_engine(
    str(settings.ASYNC_DATABASE_URI),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    Yields:
        An async SQLAlchemy session.

    Ensures proper cleanup by closing the session after use.
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def check_database_connection() -> bool:
    """
    Verify the database connection is healthy.

    Returns:
        True if the database is reachable.
    """
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as exc:
        logger.error("Database connection check failed", error=str(exc))
        return False


# ── Sync Engine & Session (for Alembic and scripts) ─────────────────────────

sync_engine = create_engine(
    str(settings.SYNC_DATABASE_URI),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)


def get_sync_session() -> Generator[Session, None, None]:
    """
    Provide a sync database session.

    Yields:
        A sync SQLAlchemy session.
    """
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
