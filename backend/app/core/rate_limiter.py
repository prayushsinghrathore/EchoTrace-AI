"""
In-memory sliding window rate limiter for authentication endpoints.

Uses a token bucket approach with per-IP tracking.
Limits are configurable through settings.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SlidingWindowEntry:
    """A single rate limit window for one client + endpoint pair."""

    timestamps: list[float] = field(default_factory=list)


class TokenBucket:
    """Sliding window counter using timestamp list per client key."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, SlidingWindowEntry] = defaultdict(SlidingWindowEntry)

    def is_allowed(self, key: str) -> bool:
        """Check and record a request. Returns True if within limit."""
        now = time.time()
        entry = self._buckets[key]

        # Prune expired timestamps
        cutoff = now - self.window_seconds
        entry.timestamps = [t for t in entry.timestamps if t > cutoff]

        if len(entry.timestamps) >= self.max_requests:
            return False

        entry.timestamps.append(now)
        return True

    def remaining(self, key: str) -> int:
        """Return how many requests remain in the current window."""
        now = time.time()
        cutoff = now - self.window_seconds
        entry = self._buckets[key]
        active = len([t for t in entry.timestamps if t > cutoff])
        return max(0, self.max_requests - active)

    def cleanup(self) -> None:
        """Remove stale entries to prevent memory leak."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._buckets = defaultdict(
            SlidingWindowEntry,
            {k: v for k, v in self._buckets.items() if v.timestamps and v.timestamps[-1] > cutoff},
        )


# ── Rate limiters for auth endpoints ────────────────────────────────────────

# These are populated from config at startup
_login_limiter: TokenBucket | None = None
_register_limiter: TokenBucket | None = None
_refresh_limiter: TokenBucket | None = None
_reset_limiter: TokenBucket | None = None

# Last cleanup timestamp
_last_cleanup: float = 0.0


def initialize_limiters() -> None:
    """Initialize rate limiters from current settings."""
    global _login_limiter, _register_limiter, _refresh_limiter, _reset_limiter

    _login_limiter = TokenBucket(
        max_requests=settings.RATE_LIMIT_LOGIN_MAX,
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW,
    )
    _register_limiter = TokenBucket(
        max_requests=settings.RATE_LIMIT_REGISTER_MAX,
        window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW,
    )
    _refresh_limiter = TokenBucket(
        max_requests=settings.RATE_LIMIT_REFRESH_MAX,
        window_seconds=settings.RATE_LIMIT_REFRESH_WINDOW,
    )
    _reset_limiter = TokenBucket(
        max_requests=settings.RATE_LIMIT_RESET_MAX,
        window_seconds=settings.RATE_LIMIT_RESET_WINDOW,
    )
    logger.info("Rate limiters initialized")


def _get_client_key(request: Request) -> str:
    """Extract a unique client key from the request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return ip


def rate_limit(endpoint: str) -> Callable:
    """
    Dependency factory: apply rate limiting to an endpoint.

    Args:
        endpoint: One of 'login', 'register', 'refresh', 'reset'.

    Usage:
        @router.post("/login")
        async def login(_: None = Depends(rate_limit("login"))):
            ...
    """
    if not settings.RATE_LIMIT_ENABLED:
        async def _noop_dependency(_request: Request) -> None:
            return None
        return _noop_dependency

    _ensure_limiters()

    limiters = {
        "login": _login_limiter,
        "register": _register_limiter,
        "refresh": _refresh_limiter,
        "reset": _reset_limiter,
    }

    limiter = limiters.get(endpoint)
    if limiter is None:
        raise ValueError(f"Unknown rate limit endpoint: {endpoint}")

    async def _rate_limit_dependency(request: Request) -> None:
        key = _get_client_key(request)
        _periodic_cleanup(limiter)

        if not limiter.is_allowed(key):
            logger.warning("Rate limit exceeded", endpoint=endpoint, key=key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after_seconds": limiter.window_seconds,
                },
            )

    return _rate_limit_dependency


def _ensure_limiters() -> None:
    """Lazily initialize limiters if not already done."""
    global _login_limiter, _register_limiter, _refresh_limiter, _reset_limiter

    if _login_limiter is None:
        initialize_limiters()


def _periodic_cleanup(limiter: TokenBucket | None) -> None:
    """Run cleanup every 60 seconds to prevent memory leaks."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup > 60 and limiter is not None:
        limiter.cleanup()
        _last_cleanup = now
