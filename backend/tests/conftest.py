"""
Pytest configuration and fixtures.

Provides async test client with an isolated SQLite database
so tests run without requiring an external PostgreSQL instance.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Disable rate limiting for tests
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# Import models first to ensure they're registered with Base.metadata
from app import models as _models  # noqa: F401
from app.api.deps import get_db_session
from app.db.base import Base
from app.main import app as application

# File-based SQLite to avoid connection isolation issues with :memory:
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh SQLite database for each test.

    Creates all tables before the test and drops them after.
    A file-based database is used so all connections share the same data.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        # Create all tables through the engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP test client with a real database.
    """

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    application.dependency_overrides[get_db_session] = _override_get_db

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    application.dependency_overrides.clear()
