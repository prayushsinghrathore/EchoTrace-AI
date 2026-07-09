"""
Health check endpoint.

Provides comprehensive system health information including:
- Application status and version
- Database connectivity
- Neo4j connectivity
- Uptime tracking
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import settings
from app.core.logging import get_logger
from app.graph.neo4j import check_neo4j_connection
from app.schemas.health import HealthResponse, ServiceStatus

logger = get_logger(__name__)

router = APIRouter(tags=["health"])

# Application start time for uptime tracking
_start_time: float = time.time()


@router.get(
    "",
    response_model=HealthResponse,
    summary="System Health Check",
    description="Returns the current health status of the application and its dependencies.",
)
async def health_check(
    db: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """
    Perform a comprehensive health check.

    Tests connectivity to:
    - PostgreSQL database
    - Neo4j graph database

    Returns:
        HealthResponse with overall status and per-service details.
    """
    services: list[ServiceStatus] = []
    all_healthy = True

    # ── PostgreSQL Check ──────────────────────────────────────────────────
    pg_status = await _check_postgresql(db)
    services.append(pg_status)
    if pg_status.status != "healthy":
        all_healthy = False

    # ── Neo4j Check ──────────────────────────────────────────────────────
    neo4j_status = await _check_neo4j()
    services.append(neo4j_status)
    if neo4j_status.status != "healthy":
        all_healthy = False

    # ── Determine Overall Status ─────────────────────────────────────────
    overall_status = "healthy" if all_healthy else "degraded"

    uptime = time.time() - _start_time

    logger.info(
        "Health check completed",
        status=overall_status,
        services=[s.name for s in services if s.status == "healthy"],
    )

    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(UTC),
        services=services,
        uptime_seconds=round(uptime, 2),
    )


async def _check_postgresql(db: AsyncSession) -> ServiceStatus:
    """
    Check PostgreSQL database connectivity.

    Args:
        db: Async database session.

    Returns:
        ServiceStatus for PostgreSQL.
    """
    start = time.time()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        return ServiceStatus(
            name="postgresql",
            status="healthy",
            latency_ms=round(latency, 2),
            details=None,
        )
    except Exception as exc:
        latency = (time.time() - start) * 1000
        logger.error("PostgreSQL health check failed", error=str(exc))
        return ServiceStatus(
            name="postgresql",
            status="unhealthy",
            latency_ms=round(latency, 2),
            details=str(exc),
        )


async def _check_neo4j() -> ServiceStatus:
    """
    Check Neo4j graph database connectivity.

    Returns:
        ServiceStatus for Neo4j.
    """
    start = time.time()
    try:
        result = await check_neo4j_connection()
        latency = (time.time() - start) * 1000
        if result:
            return ServiceStatus(
                name="neo4j",
                status="healthy",
                latency_ms=round(latency, 2),
                details=None,
            )
        return ServiceStatus(
            name="neo4j",
            status="unhealthy",
            latency_ms=round(latency, 2),
            details="Connection returned false",
        )
    except Exception as exc:
        latency = (time.time() - start) * 1000
        logger.error("Neo4j health check failed", error=str(exc))
        return ServiceStatus(
            name="neo4j",
            status="unhealthy",
            latency_ms=round(latency, 2),
            details=str(exc),
        )
