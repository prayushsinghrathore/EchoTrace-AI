"""
Optional Redis-backed caching layer.

Provides a centralized caching interface that degrades gracefully when
Redis is unavailable. Designed as an optional enhancement — the application
continues to function without Redis, relying on in-memory caching instead.

Cache operations are safe to call from anywhere in the application and
will never raise exceptions due to Redis connectivity issues.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import suppress
from typing import Any

from app.core.config import settings

_REDIS_AVAILABLE: bool = False
_redis_client: Any = None

# Lightweight check — only validates the redis package is installed.
# The actual client and connection are created lazily in _get_client().
try:
    import redis  # noqa: F401

    _REDIS_AVAILABLE = True
except ImportError:
    pass


async def _get_client() -> Any:
    """Create the Redis client on first use. Returns None if unavailable."""
    global _redis_client
    if not settings.REDIS_ENABLED or not _REDIS_AVAILABLE:
        return None
    if _redis_client is None:
        import redis.asyncio as aioredis

        with suppress(Exception):
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
                health_check_interval=30,
            )
    return _redis_client


async def get(key: str) -> Any | None:
    """Get a value from cache. Returns None on miss or error."""
    client = await _get_client()
    if client is None:
        return None
    with suppress(Exception):
        value = await client.get(key)
        if value is not None:
            return json.loads(value)
    return None


async def set(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    """Set a cached value with optional TTL. Silently ignores errors."""
    client = await _get_client()
    if client is None:
        return
    with suppress(Exception):
        serialized = json.dumps(value, default=str)
        if ttl_seconds is not None:
            await client.setex(key, ttl_seconds, serialized)
        else:
            await client.set(key, serialized)


async def delete(key: str) -> None:
    """Delete a cached key. Silently ignores errors."""
    client = await _get_client()
    if client is None:
        return
    with suppress(Exception):
        await client.delete(key)


async def clear_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern (e.g. ``evidence:*``)."""
    client = await _get_client()
    if client is None:
        return
    with suppress(Exception):
        cursor, keys = await client.scan(cursor=0, match=pattern, count=100)
        if keys:
            await client.delete(*keys)


async def close() -> None:
    """Close the Redis connection pool."""
    if _redis_client is not None:
        with suppress(Exception):
            await _redis_client.close()


def cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Build a deterministic cache key from arguments.

    Example:
        cache_key("evidence:list", workspace_id="ws_1", page=1)
        -> "evidence:list:ws_1:1:a1b2c3..."
    """
    parts = [str(a) for a in args]
    parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    serialized = ":".join(parts)
    suffix = hashlib.md5(serialized.encode(), usedforsecurity=False).hexdigest()[:12]
    return f"{prefix}:{suffix}"
