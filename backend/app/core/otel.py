"""
OpenTelemetry instrumentation for EchoTrace AI.

Configures distributed tracing, metrics export, and context propagation
via the OpenTelemetry Protocol (OTLP). All instrumentation is optional:
if OTel dependencies are not installed, the module degrades gracefully
and a no-op tracer provider is used instead.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("echotrace.otel")

# ── Sentinel used when OTel is unavailable ─────────────────────────────────
_OTEL_AVAILABLE: bool = False
_tracer_provider: Any = None
_meter_provider: Any = None

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except ImportError:
    logger.info(
        "OpenTelemetry packages not installed — tracing disabled. "
        "Install opentelemetry-distro, opentelemetry-exporter-otlp, "
        "opentelemetry-instrumentation-fastapi, "
        "opentelemetry-instrumentation-httpx, and "
        "opentelemetry-instrumentation-sqlalchemy to enable."
    )


def setup_opentelemetry(app: Any = None) -> None:
    """
    Initialise OpenTelemetry tracing, metrics, and instrumentation.

    Args:
        app: The FastAPI application instance (optional, for auto-instrumentation).
    """
    if not _OTEL_AVAILABLE or not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry instrumentation skipped (disabled or unavailable).")
        return

    from opentelemetry import trace

    resource = Resource.create(
        attributes={
            "service.name": "echotrace-backend",
            "service.version": settings.VERSION,
            "service.namespace": "echotrace-ai",
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True,
    )
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    global _tracer_provider
    _tracer_provider = provider

    logger.info(
        "OpenTelemetry initialised",
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
    )

    # ── FastAPI auto-instrumentation ───────────────────────────────────
    if app is not None:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logger.debug("FastAPI instrumented for OpenTelemetry")

    # ── HTTPX instrumentation ──────────────────────────────────────────
    try:
        HTTPXClientInstrumentor().instrument()
        logger.debug("HTTPX instrumented for OpenTelemetry")
    except Exception as exc:
        logger.debug("HTTPX instrumentation skipped", error=str(exc))

    # ── SQLAlchemy instrumentation ─────────────────────────────────────
    try:
        from app.db.session import async_engine

        SQLAlchemyInstrumentor().instrument(
            engine=async_engine.sync_engine,
            tracer_provider=provider,
        )
        logger.debug("SQLAlchemy instrumented for OpenTelemetry")
    except Exception as exc:
        logger.debug("SQLAlchemy instrumentation skipped", error=str(exc))


def shutdown_opentelemetry() -> None:
    """Shut down the OpenTelemetry provider gracefully."""
    if not _OTEL_AVAILABLE or not settings.OTEL_ENABLED:
        return
    from opentelemetry import trace

    if _tracer_provider is not None:
        trace.get_tracer_provider().shutdown()  # type: ignore[attr-defined]
        logger.debug("OpenTelemetry shut down")
