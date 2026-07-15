"""
Security and observability middleware — headers, metrics, request tracking,
correlation IDs, and structured logging context.
"""

from __future__ import annotations

import time
import typing
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.core.metrics import metrics
from app.core.prometheus_metrics import record_request as prom_record_request

logger = get_logger(__name__)


def _bind_request_context(request: Request, request_id: str) -> None:
    """Bind structured logging context for the current request."""
    import structlog

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query_string=str(request.url.query),
        client_host=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Propagate incoming correlation ID if present
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id:
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    # Bind user context if authenticated (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        structlog.contextvars.bind_contextvars(user_id=str(user.id))
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id:
        structlog.contextvars.bind_contextvars(workspace_id=str(workspace_id))


def _try_bind_trace_context() -> None:
    """Bind OpenTelemetry trace/span IDs to logging context if available."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            if span_context.is_valid:
                import structlog

                structlog.contextvars.bind_contextvars(
                    trace_id=hex(span_context.trace_id),
                    span_id=hex(span_context.span_id),
                )
    except ImportError:
        pass  # OpenTelemetry not installed — trace context binding skipped


def add_security_headers_middleware(app: FastAPI) -> None:
    """Add enterprise security headers to all responses."""

    @app.middleware("http")
    async def security_headers(request: Request, call_next: typing.Callable) -> JSONResponse:
        start = time.time()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-ID", request_id)

        # Bind structured logging context
        _bind_request_context(request, request_id)

        # Bind trace/span IDs from OTel context
        _try_bind_trace_context()

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
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = str(round(process_time, 2))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), display-capture=(), document-domain=(), "
            "encrypted-media=(), fullscreen=(), microphone=(), "
            "midi=(), payment=(), picture-in-picture=(), "
            "publickey-credentials-get=(), screen-wake-lock=(), "
            "sync-xhr=(self), usb=(), web-share=(), "
            "xr-spatial-tracking=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # Record metrics (both JSON snapshot and Prometheus exposition format)
        metrics.record_request(
            request.method,
            request.url.path,
            response.status_code,
            round(process_time, 2),
        )
        prom_record_request(
            request.method,
            request.url.path,
            response.status_code,
            round(process_time, 2),
        )

        # Structured log on completion with full observability context
        log_kwargs = {
            "status_code": response.status_code,
            "duration_ms": round(process_time, 2),
            "content_length": response.headers.get("content-length"),
        }
        if response.status_code >= 400:
            logger.warning("Request completed with error", **log_kwargs)
        else:
            logger.info("Request completed", **log_kwargs)

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
