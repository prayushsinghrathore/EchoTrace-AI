"""
Security and observability middleware — headers, metrics, request tracking.
"""

from __future__ import annotations

import time
import typing
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.core.metrics import metrics

logger = get_logger(__name__)


def add_security_headers_middleware(app: FastAPI) -> None:
    """Add enterprise security headers to all responses."""

    @app.middleware("http")
    async def security_headers(request: Request, call_next: typing.Callable) -> JSONResponse:
        start = time.time()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind request context for structured logging
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
            logger.exception("Unhandled error", path=request.url.path, request_id=request_id)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )

        process_time = (time.time() - start) * 1000

        # Security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time, 2))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # Structured log on completion
        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=round(process_time, 2),
        )

        # Record metrics
        metrics.record_request(request.method, request.url.path, response.status_code, round(process_time, 2))

        return response


def add_trusted_hosts_middleware(app: FastAPI, allowed_hosts: list[str] | None = None) -> None:
    """Add trusted hosts middleware if configured."""
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    if allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts,
        )


def add_cors_middleware(app: FastAPI, origins: list[str]) -> None:
    """Add CORS middleware with secure defaults."""
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization", "Content-Type", "X-Request-ID",
            "X-Real-IP", "X-Forwarded-For",
        ],
        expose_headers=["X-Request-ID", "X-Process-Time"],
        max_age=600,
    )
