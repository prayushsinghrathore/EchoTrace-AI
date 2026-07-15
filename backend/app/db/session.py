"""
Database session management.

Provides async and sync database sessions with connection pooling
and proper lifecycle management.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Async Engine & Session ──────────────────────────────────────────────────

# Build connect_args based on SSL configuration
_async_connect_args: dict[str, str] = {}
if settings.DB_SSL_MODE == "require":
    _async_connect_args["ssl"] = "require"

async_engine = create_async_engine(
    str(settings.ASYNC_DATABASE_URI),
    connect_args=_async_connect_args,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
    # Enable query cache for compiled statement reuse
    # The cache is shared across all connections in the pool
    query_cache_size=500,
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


def get_pool_status() -> dict:
    """
    Return connection pool health metrics.

    Returns:
        Dict with pool utilization, checked_out, size, overflow, etc.
    """
    pool = async_engine.pool
    try:
        return {
            "size": pool.size(),  # type: ignore[attr-defined]
            "checked_in": pool.checkedin(),  # type: ignore[attr-defined]
            "checked_out": pool.checkedout(),  # type: ignore[attr-defined]
            "overflow": pool.overflow(),  # type: ignore[attr-defined]
            "total": pool.total(),  # type: ignore[attr-defined]
        }
    except Exception as exc:
        logger.warning("Failed to read pool status", error=str(exc))
        return {
            "size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total": 0,
            "error": str(exc),
        }


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
# Created lazily — the sync engine is only needed during Alembic migrations
# (which run as a separate process). At application runtime it saves ~10 MB.

_sync_engine_instance: Any = None
_sync_session_local: Any = None


def _ensure_sync_engine():
    """Lazily create the sync engine when first requested."""
    global _sync_engine_instance, _sync_session_local
    if _sync_engine_instance is not None:
        return _sync_engine_instance, _sync_session_local

    _sync_connect_args: dict[str, str] = {}
    if settings.DB_SSL_MODE == "require":
        _sync_connect_args["sslmode"] = "require"

    _sync_engine_instance = create_engine(
        str(settings.SYNC_DATABASE_URI),
        connect_args=_sync_connect_args,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        echo=settings.DB_ECHO,
        pool_pre_ping=True,
    )

    _sync_session_local = sessionmaker(
        bind=_sync_engine_instance,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )
    return _sync_engine_instance, _sync_session_local


def sync_engine():
    """Get the sync engine, creating it lazily."""
    engine, _ = _ensure_sync_engine()
    return engine


def get_sync_session() -> Generator[Session, None, None]:
    """
    Provide a sync database session.

    Yields:
        A sync SQLAlchemy session.
    """
    _, local = _ensure_sync_engine()
    session = local()
    try:
        yield session
    finally:
        session.close()
