"""
Operations endpoints — health, readiness, liveness, metrics, rate limits, security.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.core.prometheus_metrics import render_prometheus_metrics
from app.graph.neo4j import check_neo4j_connection
from app.models.user import User
from app.schemas.health import HealthResponse, ServiceStatus

logger = get_logger(__name__)

router = APIRouter(tags=["operations"])

_start_time: float = time.time()


# ── Health ────────────────────────────────────────────────────────────────────
# Note: /health is served by health.py (dedicated endpoint)


@router.get("/live")
async def liveness() -> dict:
    """Kubernetes liveness probe — always returns 200."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/ready")
async def readiness(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Kubernetes readiness probe — checks database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


# ── Metrics ───────────────────────────────────────────────────────────────────


@router.get("/metrics")
async def get_metrics(
    _user: User = Depends(get_current_user),
) -> dict:
    """Application metrics snapshot (JSON). Requires authentication."""
    return metrics.get_snapshot()


@router.get("/metrics/prometheus")
async def get_prometheus_metrics(
    _user: User = Depends(get_current_user),
) -> Response:
    """
    Prometheus exposition-format metrics.

    Returns metrics in Prometheus text-based exposition format for scraping.
    Requires authentication. Use this endpoint as the Prometheus scrape target.
    """
    data = render_prometheus_metrics()
    return Response(
        content=data,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ── Rate Limits ────────────────────────────────────────────────────────────────


@router.get("/rate-limits")
async def get_rate_limits(
    _user: User = Depends(get_current_user),
) -> dict:
    """Current rate limit configuration."""
    return {
        "limits": {
            "guest": {"ai": settings.AI_RATE_LIMIT_MAX, "window_seconds": settings.AI_RATE_LIMIT_WINDOW},
            "authenticated": {"ai": settings.AI_RATE_LIMIT_MAX * 2, "window_seconds": settings.AI_RATE_LIMIT_WINDOW},
            "investigator": {"ai": settings.AI_RATE_LIMIT_MAX * 5, "window_seconds": settings.AI_RATE_LIMIT_WINDOW},
            "admin": {"ai": settings.AI_RATE_LIMIT_MAX * 10, "window_seconds": settings.AI_RATE_LIMIT_WINDOW},
        },
        "auth": {
            "login": {"max": settings.RATE_LIMIT_LOGIN_MAX, "window": settings.RATE_LIMIT_LOGIN_WINDOW},
            "register": {"max": settings.RATE_LIMIT_REGISTER_MAX, "window": settings.RATE_LIMIT_REGISTER_WINDOW},
        },
    }


# ── WebSocket Endpoint ────────────────────────────────────────────────────────


@router.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time events."""
    from app.core.websocket import authenticate_websocket, ws_manager

    auth_result = await authenticate_websocket(websocket)
    if auth_result is None:
        return

    user_id, workspace_id = auth_result
    await ws_manager.connect(websocket, workspace_id, user_id)

    try:
        while True:
            # Keep connection alive — listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket, workspace_id)


# ── Private Helpers ────────────────────────────────────────────────────────────


async def _check_postgres(db: AsyncSession) -> ServiceStatus:
    start = time.time()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        metrics.record_db_latency(latency)
        return ServiceStatus(name="postgresql", status="healthy", latency_ms=round(latency, 2), details=None)
    except Exception as exc:
        return ServiceStatus(name="postgresql", status="unhealthy", details=str(exc), latency_ms=None)


async def _check_neo4j() -> ServiceStatus:
    start = time.time()
    try:
        result = await check_neo4j_connection()
        latency = (time.time() - start) * 1000
        status_str = "healthy" if result else "unhealthy"
        return ServiceStatus(name="neo4j", status=status_str, latency_ms=round(latency, 2), details=None)
    except Exception as exc:
        return ServiceStatus(name="neo4j", status="unhealthy", latency_ms=None, details=str(exc))


async def _check_ai_provider() -> ServiceStatus:
    start = time.time()
    try:
        from app.ai.service import AIService
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            svc = AIService(db)
            result = await svc.health_check()
        latency = (time.time() - start) * 1000
        return ServiceStatus(
            name=f"ai_provider_{result.get('provider', 'unknown')}",
            status="healthy" if result.get("provider_healthy") else "degraded",
            latency_ms=round(latency, 2),
            details=f"model={result.get('model', '?')}" if result.get("provider_healthy") else "AI provider unavailable",
        )
    except Exception as exc:
        return ServiceStatus(name="ai_provider", status="unhealthy", latency_ms=None, details=str(exc)[:200])
