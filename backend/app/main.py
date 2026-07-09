"""
EchoTrace AI — FastAPI Application Entry Point.

Application factory with lifecycle management, middleware, and routing.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_v1_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.rate_limiter import initialize_limiters
from app.graph.neo4j import neo4j_manager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager.

    Handles startup and shutdown events.
    """
    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging()
    initialize_limiters()
    logger.info(
        "Starting EchoTrace AI",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Initialize Neo4j connection
    try:
        await neo4j_manager.initialize()
        logger.info("Neo4j connection initialized")
    except Exception as exc:
        logger.warning(
            "Neo4j initialization failed — service will run without graph DB",
            error=str(exc),
        )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("Shutting down EchoTrace AI")

    await neo4j_manager.close()

    # Dispose database connections
    from app.db.session import async_engine, sync_engine
    await async_engine.dispose()
    sync_engine.dispose()

    logger.info("Shutdown complete")


def create_application() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application with all middleware,
    routers, and exception handlers.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Production-grade traceability and knowledge graph platform",
        docs_url=f"{settings.API_V1_PREFIX}/docs" if not settings.is_production else None,
        redoc_url=f"{settings.API_V1_PREFIX}/redoc" if not settings.is_production else None,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ───────────────────────────────────────────────────────

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # ── Request Lifecycle & Tracing Middleware ───────────────────────────
    @app.middleware("http")
    async def add_request_tracing(request: Request, call_next: callable) -> JSONResponse:  # type: ignore[valid-type]
        """Add X-Request-ID, X-Process-Time headers and structured logging."""
        start_time = time.time()

        # Generate or propagate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Add request context to logs
        import structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error", path=request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )

        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=round(process_time * 1000, 2),
        )

        return response

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # ── Root Endpoint ────────────────────────────────────────────────────
    @app.get("/")
    async def root() -> dict:
        """Root endpoint with basic API information."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": f"{settings.API_V1_PREFIX}/docs",
        }

    return app


# Application instance
app = create_application()
