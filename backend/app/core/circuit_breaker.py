"""
Simple in-memory circuit breaker for external API calls.

Prevents cascading failures by failing fast when a dependency
is unhealthy, and recovering gracefully after a cooldown period.

Usage:
    breaker = CircuitBreaker("openai", failure_threshold=5, recovery_timeout=30)

    async with breaker:
        result = await call_openai_api()
"""
from __future__ import annotations

import time
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """
    State machine: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (probing).

    - CLOSED: requests pass through; failures increment a counter.
    - OPEN: requests are rejected immediately with CircuitBreakerOpenError.
    - HALF_OPEN: one probe request is allowed; success -> CLOSED, failure -> OPEN.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_retries: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_retries = half_open_max_retries

        self._state: str = "CLOSED"
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._half_open_attempts: int = 0

    @property
    def state(self) -> str:
        """Current state: CLOSED, OPEN, or HALF_OPEN."""
        return self._state

    async def __aenter__(self) -> CircuitBreaker:
        if self._state == "OPEN":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                logger.info("Circuit %s -> HALF_OPEN (probing)", self.name)
            else:
                raise CircuitBreakerOpenError(self.name)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            # Failure
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == "HALF_OPEN":
                self._half_open_attempts += 1
                if self._half_open_attempts >= self.half_open_max_retries:
                    self._state = "OPEN"
                    logger.warning(
                        "Circuit %s -> OPEN (half-open retries exhausted)",
                        self.name,
                    )
            elif self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                logger.warning(
                    "Circuit %s -> OPEN (failure_count=%d)",
                    self.name,
                    self._failure_count,
                )
        else:
            # Success
            if self._state == "HALF_OPEN":
                logger.info("Circuit %s -> CLOSED (probe succeeded)", self.name)
            self._state = "CLOSED"
            self._failure_count = 0
            self._half_open_attempts = 0

    def reset(self) -> None:
        """Manually reset the breaker to CLOSED."""
        self._state = "CLOSED"
        self._failure_count = 0
        self._half_open_attempts = 0


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker rejects a request."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Circuit breaker '{name}' is OPEN — request rejected")
        self.breaker_name = name


# ── Global breaker instances ─────────────────────────────────────────────────

ai_provider_breaker = CircuitBreaker(
    "ai-provider", failure_threshold=5, recovery_timeout=30.0
)
