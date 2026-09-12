"""
AI result cache — in-memory cache keyed by SHA256 hash.

Cache keys are computed as:
    SHA256(evidence_text + prompt_text + model + version)

Results are stored with a configurable TTL.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AICache:
    """
    In-memory LRU cache for AI operation results.

    Thread-safe for single-process deployments. For multi-process
    or distributed deployments, replace with Redis or similar.
    """

    def __init__(self, max_size: int = 500, ttl: int | None = None) -> None:
        self._max_size = max_size
        self._ttl = ttl or settings.AI_CACHE_TTL_SECONDS
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._redis: Any | None = None

    def _make_key(
        self,
        evidence_text: str,
        prompt_text: str,
        model: str,
        version: str,
    ) -> str:
        """Generate a SHA256 cache key from inputs."""
        content = f"{evidence_text}|{prompt_text}|{model}|{version}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(
        self,
        evidence_text: str,
        prompt_text: str,
        model: str,
        version: str,
    ) -> tuple[bool, Any | None]:
        """
        Retrieve a cached result.

        Returns:
            Tuple of (hit: bool, result: Any | None).
        """
        if not settings.AI_CACHE_ENABLED:
            return False, None

        key = self._make_key(evidence_text, prompt_text, model, version)

        if key not in self._cache:
            self._misses += 1
            return False, None

        entry = self._cache[key]

        if time.time() - entry.timestamp > self._ttl:
            del self._cache[key]
            self._misses += 1
            return False, None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        logger.debug("AI cache hit", key=key[:16], model=model)
        return True, entry.result

    async def get_async(self, evidence_text: str, prompt_text: str, model: str, version: str) -> tuple[bool, Any | None]:
        """Read Redis first, then use the local cache as a development fallback."""
        if not settings.AI_CACHE_ENABLED:
            return False, None
        key = self._make_key(evidence_text, prompt_text, model, version)
        client = await self._redis_client()
        if client is not None:
            try:
                value = await client.get(self._redis_key(key))
                if value is not None:
                    self._hits += 1
                    return True, json.loads(value)
            except Exception as exc:
                logger.warning("Redis AI cache read failed", error=str(exc))
        return self.get(evidence_text, prompt_text, model, version)

    def set(
        self,
        evidence_text: str,
        prompt_text: str,
        model: str,
        version: str,
        result: Any,
    ) -> None:
        """Store a result in the cache."""
        if not settings.AI_CACHE_ENABLED:
            return

        key = self._make_key(evidence_text, prompt_text, model, version)

        # Evict oldest if at capacity
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(result=result, timestamp=time.time())
        logger.debug("AI cache set", key=key[:16], model=model)

    async def set_async(
        self, evidence_text: str, prompt_text: str, model: str, version: str, result: Any
    ) -> None:
        """Write to Redis and retain a local copy for resilience."""
        self.set(evidence_text, prompt_text, model, version, result)
        if not settings.AI_CACHE_ENABLED:
            return
        client = await self._redis_client()
        if client is not None:
            try:
                key = self._make_key(evidence_text, prompt_text, model, version)
                await client.setex(
                    self._redis_key(key), self._ttl, json.dumps(result, default=str)
                )
            except Exception as exc:
                logger.warning("Redis AI cache write failed", error=str(exc))

    def _redis_key(self, key: str) -> str:
        return f"{settings.REDIS_CACHE_PREFIX}:ai:{key}"

    async def _redis_client(self) -> Any | None:
        if not settings.REDIS_ENABLED:
            return None
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(
                    settings.REDIS_URL, encoding="utf-8", decode_responses=True,
                    socket_connect_timeout=2, socket_timeout=2,
                )
            except ImportError:
                return None
        return self._redis

    def invalidate(self, evidence_text: str, prompt_text: str, model: str, version: str) -> None:
        """Remove a specific entry from the cache."""
        key = self._make_key(evidence_text, prompt_text, model, version)
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("AI cache cleared")

    async def close(self) -> None:
        """Close the optional Redis client during application shutdown."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    @property
    def stats(self) -> dict[str, int | float]:
        """Return cache hit/miss statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0.0,
        }


class CacheEntry:
    """A single cache entry with TTL tracking."""

    def __init__(self, result: Any, timestamp: float) -> None:
        self.result = result
        self.timestamp = timestamp


# Global cache instance
ai_cache = AICache()
