"""
Neo4j graph database connection management.

Provides async connection pooling, session management, and health checks
for the Neo4j graph database.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Neo4jConnectionManager:
    """
    Manages Neo4j driver lifecycle and session creation.

    Implements connection pooling with proper async context management.
    Follows the singleton pattern for the driver instance.
    """

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """
        Initialize the Neo4j driver with connection pooling.

        Should be called during application startup.
        Safe to call multiple times — only initializes once.
        """
        if self._initialized:
            return

        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=20,
                connection_acquisition_timeout=30,
                connection_timeout=15,
            )

            # Verify connectivity
            await self._driver.verify_connectivity()
            self._initialized = True
            logger.info(
                "Neo4j connection established",
                uri=settings.NEO4J_URI,
                database=settings.NEO4J_DATABASE,
            )

        except Exception as exc:
            logger.error(
                "Failed to initialize Neo4j connection",
                error=str(exc),
                uri=settings.NEO4J_URI,
            )
            raise

    async def close(self) -> None:
        """
        Close the Neo4j driver and release all connections.

        Should be called during application shutdown.
        """
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._initialized = False
            logger.info("Neo4j connection closed")

    @property
    def driver(self) -> AsyncDriver:
        """Get the Neo4j driver instance."""
        if not self._driver:
            raise RuntimeError(
                "Neo4j driver not initialized. Call `initialize()` first."
            )
        return self._driver

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async Neo4j session from the connection pool.

        Yields:
            An async Neo4j session for executing queries.

        Example:
            async with neo4j_manager.get_session() as session:
                result = await session.run("MATCH (n) RETURN n LIMIT 1")
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized.")

        async with self._driver.session(
            database=settings.NEO4J_DATABASE,
            fetch_size=100,
        ) as session:
            yield session

    async def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Execute a read-only Cypher query.

        Args:
            query: The Cypher query string.
            parameters: Optional query parameters.

        Returns:
            List of records from the query.
        """
        async with self.get_session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Execute a write Cypher query.

        Args:
            query: The Cypher query string.
            parameters: Optional query parameters.

        Returns:
            List of records from the query.
        """
        async with self.get_session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()


# Global Neo4j connection manager instance
neo4j_manager = Neo4jConnectionManager()


async def check_neo4j_connection() -> bool:
    """
    Verify Neo4j connectivity by running a simple query.

    Returns:
        True if Neo4j is reachable and responding.
    """
    try:
        if not neo4j_manager._driver:
            await neo4j_manager.initialize()
        async with neo4j_manager.get_session() as session:
            result = await session.run("RETURN 1 AS health")
            record = await result.single()
            return record is not None and record.get("health") == 1
    except Exception as exc:
        logger.error("Neo4j connectivity check failed", error=str(exc))
        return False
