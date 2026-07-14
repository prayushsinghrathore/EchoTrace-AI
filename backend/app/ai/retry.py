"""
HTTP utility helpers for AI providers.

Provides retry with exponential backoff, timeout handling,
and common error transformation for LLM API calls.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


async def call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json: dict[str, Any] | None = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> httpx.Response:
    """
    Make an HTTP request with exponential backoff retry.

    Retries on transient errors (timeout, 429, 5xx).
    Does NOT retry on 4xx errors (client errors).

    Args:
        client: httpx async client.
        method: HTTP method.
        url: Request URL.
        json: Optional JSON body.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds (doubles each retry).
        max_delay: Maximum delay in seconds.

    Returns:
        httpx.Response on success.

    Raises:
        TimeoutError: If all retries are exhausted due to timeouts.
        RuntimeError: If all retries are exhausted due to HTTP errors.
    """
    last_exc: Exception | None = None
    last_status: int | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = await client.request(method, url, json=json)

            # Success
            if response.status_code < 500:
                response.raise_for_status()
                return response

            # Server error or rate limit — retry
            last_status = response.status_code
            logger.warning(
                "Provider request failed, retrying",
                status=response.status_code,
                attempt=attempt,
                max_retries=max_retries,
            )

        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning(
                "Provider request timed out, retrying",
                attempt=attempt,
                max_retries=max_retries,
            )

        except httpx.HTTPStatusError as exc:
            # 4xx errors are not retried (except 429)
            if exc.response.status_code < 500 and exc.response.status_code != 429:
                raise
            last_status = exc.response.status_code
            last_exc = exc
            logger.warning(
                "Provider transient error, retrying",
                status=exc.response.status_code,
                attempt=attempt,
                max_retries=max_retries,
            )

        # Exponential backoff with jitter
        if attempt < max_retries:
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            import random
            jitter = random.uniform(0, delay * 0.1)
            await asyncio.sleep(delay + jitter)

    # All retries exhausted
    if last_status and last_status >= 500:
        raise RuntimeError(f"Provider returned status {last_status} after {max_retries} retries")
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Provider request failed after {max_retries} retries")
