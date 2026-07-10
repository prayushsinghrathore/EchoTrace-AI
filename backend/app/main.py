"""
EchoTrace AI — FastAPI Application Entry Point.

Application factory with lifecycle management, middleware, and routing.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_v1_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import add_security_headers_middleware
from app.core.rate_limiter import initialize_limiters
from app.graph.neo4j import neo4j_manager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
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

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # ── Security Headers, Metrics, and Tracing Middleware ─────────────────
    add_security_headers_middleware(app)

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
