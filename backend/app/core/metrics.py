"""
Application metrics collector — latency, requests, errors, cache, AI.

Provides in-memory metrics aggregation with labeled dimensions.
Designed for single-process deployments. Replace with Prometheus
client for multi-process deployments.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Any


class MetricsCollector:
    """
    Thread-safe in-memory metrics collector.

    Tracks:
    - Request counts by method, path, status
    - Latency histograms
    - AI token usage and cost
    - Cache hit/miss rates
    - WebSocket connections
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._request_count: int = 0
        self._request_by_method: dict[str, int] = defaultdict(int)
        self._request_by_path: dict[str, int] = defaultdict(int)
        self._request_by_status: dict[str, int] = defaultdict(int)
        self._latency_total: float = 0.0
        self._latency_count: int = 0
        self._latency_buckets: dict[str, int] = defaultdict(int)
        self._ai_input_tokens: int = 0
        self._ai_output_tokens: int = 0
        self._ai_total_cost: float = 0.0
        self._ai_request_count: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._error_count: int = 0
        self._db_latency_total: float = 0.0
        self._db_latency_count: int = 0
        self._start_time: float = time.time()

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self._request_count += 1
            self._request_by_method[method.upper()] += 1
            # Group paths by prefix to avoid cardinality explosion
            path_group = self._group_path(path)
            self._request_by_path[path_group] += 1
            status_group = f"{status_code // 100}xx"
            self._request_by_status[status_group] += 1
            self._latency_total += latency_ms
            self._latency_count += 1
            bucket = self._latency_bucket(latency_ms)
            self._latency_buckets[bucket] += 1

            if status_code >= 400:
                self._error_count += 1

    def record_ai_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        with self._lock:
            self._ai_input_tokens += input_tokens
            self._ai_output_tokens += output_tokens
            self._ai_total_cost += cost
            self._ai_request_count += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_misses += 1

    def record_db_latency(self, latency_ms: float) -> None:
        with self._lock:
            self._db_latency_total += latency_ms
            self._db_latency_count += 1

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            uptime = time.time() - self._start_time
            avg_latency = round(self._latency_total / self._latency_count, 2) if self._latency_count > 0 else 0.0
            avg_db = round(self._db_latency_total / self._db_latency_count, 2) if self._db_latency_count > 0 else 0.0
            total_cache = self._cache_hits + self._cache_misses
            cache_rate = round(self._cache_hits / total_cache * 100, 1) if total_cache > 0 else 0.0
            rps = round(self._request_count / uptime, 2) if uptime > 0 else 0.0

            return {
                "uptime_seconds": round(uptime, 2),
                "requests": {
                    "total": self._request_count,
                    "by_method": dict(self._request_by_method),
                    "by_path": dict(self._request_by_path),
                    "by_status": dict(self._request_by_status),
                    "per_second": rps,
                },
                "latency": {
                    "average_ms": avg_latency,
                    "count": self._latency_count,
                    "buckets": dict(self._latency_buckets),
                },
                "ai": {
                    "total_requests": self._ai_request_count,
                    "total_input_tokens": self._ai_input_tokens,
                    "total_output_tokens": self._ai_output_tokens,
                    "total_cost_usd": round(self._ai_total_cost, 6),
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate_pct": cache_rate,
                },
                "database": {
                    "average_latency_ms": avg_db,
                    "query_count": self._db_latency_count,
                },
                "errors": {
                    "total": self._error_count,
                },
            }

    def reset(self) -> None:
        with self._lock:
            self._request_count = 0
            self._request_by_method.clear()
            self._request_by_path.clear()
            self._request_by_status.clear()
            self._latency_total = 0.0
            self._latency_count = 0
            self._latency_buckets.clear()
            self._ai_input_tokens = 0
            self._ai_output_tokens = 0
            self._ai_total_cost = 0.0
            self._ai_request_count = 0
            self._cache_hits = 0
            self._cache_misses = 0
            self._error_count = 0
            self._db_latency_total = 0.0
            self._db_latency_count = 0
            self._start_time = time.time()

    @staticmethod
    def _group_path(path: str) -> str:
        """Group dynamic paths into metric-safe prefixes."""
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            # Group /api/v1/{resource}/{uuid} -> /api/v1/{resource}/:id
            prefix = "/".join(parts[:3])  # api/v1/{resource}
            return f"/{prefix}/:id"
        return path

    @staticmethod
    def _latency_bucket(ms: float) -> str:
        if ms < 5:
            return "0-5ms"
        elif ms < 10:
            return "5-10ms"
        elif ms < 50:
            return "10-50ms"
        elif ms < 100:
            return "50-100ms"
        elif ms < 500:
            return "100-500ms"
        elif ms < 1000:
            return "500-1000ms"
        elif ms < 5000:
            return "1-5s"
        else:
            return "5s+"


metrics = MetricsCollector()
