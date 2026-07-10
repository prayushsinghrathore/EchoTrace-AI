"""
Centralized logging configuration.

Uses structlog for structured, production-grade logging with:
- JSON output in production, pretty console in development
- Correlation IDs for request tracing
- Automatic context propagation via contextvars
- Trace/span IDs from OpenTelemetry context
- Performance-optimized async support

Context fields automatically included in all log entries:
  request_id, correlation_id, trace_id, span_id, user_id, workspace_id,
  investigation_id, method, path, status_code, duration_ms, environment,
  service, version
"""

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

from app.core.config import settings


def _add_env_info(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    """
    Add environment metadata to every log record.

    Injected as an early processor so all subsequent processors (including
    JSONRenderer) can use the enriched context.
    """
    event_dict["environment"] = settings.ENVIRONMENT
    event_dict["service"] = "echotrace-backend"
    event_dict["version"] = settings.VERSION
    return event_dict


def setup_logging() -> None:
    """
    Configure structured logging across the entire application.

    In production: JSON-formatted logs for log aggregation systems (Loki,
    CloudWatch, ELK, etc.).
    In development: Colored console output with rich formatting.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _add_env_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
    ]

    if settings.is_production or settings.is_staging:
        _processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.stdlib.filter_by_level,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        _processors = [
            *shared_processors,
            structlog.stdlib.filter_by_level,
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(colors=True, sort_keys=False),
        ]

    structlog.configure(
        processors=_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG),
    )

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name, typically ``__name__``.

    Returns:
        A bound structlog logger.
    """
    return structlog.get_logger(name or __name__)


# Default application logger
logger = get_logger("echotrace")
