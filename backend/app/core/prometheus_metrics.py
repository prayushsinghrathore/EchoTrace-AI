"""
Prometheus exposition-format metrics for EchoTrace AI.

Provides Prometheus-format metric counters, histograms, and gauges
that Prometheus can scrape via its exposition format. Designed to
complement the in-memory MetricsCollector (which serves JSON).

Uses the prometheus_client library (installed separately).
This module is optional — if prometheus_client is not installed,
/metrics/prometheus will return an empty response with a warning.
"""

from __future__ import annotations

_PROMETHEUS_AVAILABLE: bool = False

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest

    # ── Backend Request Metrics ──────────────────────────────────────────
    requests_total = Counter(
        "echotrace_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    errors_total = Counter(
        "echotrace_errors_total",
        "Total HTTP errors (5xx)",
        ["method", "path"],
    )
    latency_seconds = Histogram(
        "echotrace_latency_seconds",
        "Request latency in seconds",
        ["method", "path"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    requests_in_progress = Gauge(
        "echotrace_requests_in_progress",
        "Currently in-flight requests",
    )
    db_latency_seconds = Histogram(
        "echotrace_db_latency_seconds",
        "Database query latency in seconds",
        ["db"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    )

    # ── AI Metrics ───────────────────────────────────────────────────────
    ai_tokens_total = Counter(
        "echotrace_ai_tokens_total",
        "AI token usage",
        ["model", "type"],
    )
    ai_cost_total = Counter(
        "echotrace_ai_cost_total",
        "AI cost in USD",
        ["model"],
    )
    ai_requests_total = Counter(
        "echotrace_ai_requests_total",
        "Total AI inference requests",
        ["model"],
    )

    # ── Auth / Security Metrics ──────────────────────────────────────────
    failed_logins_total = Counter(
        "echotrace_failed_logins_total",
        "Failed login attempts",
    )
    auth_failures_total = Counter(
        "echotrace_auth_failures_total",
        "Authentication failures (invalid tokens, expired, etc.)",
    )
    rate_limit_hits_total = Counter(
        "echotrace_rate_limit_hits_total",
        "Rate limit violations",
        ["endpoint"],
    )

    # ── Cache Metrics ────────────────────────────────────────────────────
    cache_operations_total = Counter(
        "echotrace_cache_operations_total",
        "Cache operations (hit/miss)",
        ["result"],
    )

    # ── WebSocket Metrics ────────────────────────────────────────────────
    websocket_connections = Gauge(
        "echotrace_websocket_connections",
        "Current WebSocket connections",
        ["workspace"],
    )
    websocket_messages_total = Counter(
        "echotrace_websocket_messages_total",
        "Total WebSocket messages",
        ["direction"],
    )

    _PROMETHEUS_AVAILABLE = True

except ImportError:
    # prometheus_client not installed — all Prometheus instrumentation
    # will be no-ops. Install prometheus-client to enable.
    pass


def record_request(method: str, path: str, status_code: int, latency_ms: float) -> None:
    """Record an HTTP request in Prometheus metrics."""
    if not _PROMETHEUS_AVAILABLE:
        return
    status_group = f"{status_code // 100}xx"
    requests_total.labels(method=method, path=_safe_path(path), status=status_group).inc()
    latency_seconds.labels(method=method, path=_safe_path(path)).observe(latency_ms / 1000.0)
    if status_code >= 500:
        errors_total.labels(method=method, path=_safe_path(path)).inc()


def record_db_latency(latency_ms: float, db_name: str = "postgresql") -> None:
    """Record database query latency."""
    if not _PROMETHEUS_AVAILABLE:
        return
    db_latency_seconds.labels(db=db_name).observe(latency_ms / 1000.0)


def record_ai_usage(model: str, input_tokens: int, output_tokens: int, cost: float) -> None:
    """Record AI model usage."""
    if not _PROMETHEUS_AVAILABLE:
        return
    ai_requests_total.labels(model=model).inc()
    ai_tokens_total.labels(model=model, type="input").inc(input_tokens)
    ai_tokens_total.labels(model=model, type="output").inc(output_tokens)
    ai_cost_total.labels(model=model).inc(cost)


def record_failed_login() -> None:
    """Record a failed login attempt."""
    if not _PROMETHEUS_AVAILABLE:
        return
    failed_logins_total.inc()


def record_auth_failure() -> None:
    """Record an authentication failure."""
    if not _PROMETHEUS_AVAILABLE:
        return
    auth_failures_total.inc()


def record_rate_limit_hit(endpoint: str = "unknown") -> None:
    """Record a rate limit violation."""
    if not _PROMETHEUS_AVAILABLE:
        return
    rate_limit_hits_total.labels(endpoint=endpoint).inc()


def record_cache_operation(hit: bool) -> None:
    """Record a cache hit or miss."""
    if not _PROMETHEUS_AVAILABLE:
        return
    cache_operations_total.labels(result="hit" if hit else "miss").inc()


def set_requests_in_progress(count: int) -> None:
    """Set gauge for in-progress requests."""
    if not _PROMETHEUS_AVAILABLE:
        return
    requests_in_progress.set(count)


def render_prometheus_metrics() -> bytes:
    """Render all Prometheus metrics in exposition format."""
    if not _PROMETHEUS_AVAILABLE:
        return b"# prometheus_client not installed\n"
    return generate_latest()


def _safe_path(path: str) -> str:
    """Collapse dynamic path segments to limit cardinality."""
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        resource = parts[2] if len(parts) > 2 else "root"
        return f"/api/v1/{resource}/:id" if len(parts) > 3 else f"/api/v1/{resource}"
    return path
