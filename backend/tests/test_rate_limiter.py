"""
Rate limiter tests.
"""

from __future__ import annotations

import pytest
from app.core.rate_limiter import TokenBucket


class TestTokenBucket:
    """Unit tests for the sliding window token bucket."""

    def test_allows_requests_within_limit(self) -> None:
        bucket = TokenBucket(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert bucket.is_allowed("test-key") is True

    def test_blocks_requests_exceeding_limit(self) -> None:
        bucket = TokenBucket(max_requests=3, window_seconds=60)
        for _ in range(3):
            bucket.is_allowed("test-key")
        assert bucket.is_allowed("test-key") is False

    def test_per_key_isolation(self) -> None:
        bucket = TokenBucket(max_requests=1, window_seconds=60)
        assert bucket.is_allowed("key-a") is True
        assert bucket.is_allowed("key-a") is False
        assert bucket.is_allowed("key-b") is True

    def test_remaining_counts_down(self) -> None:
        bucket = TokenBucket(max_requests=5, window_seconds=60)
        assert bucket.remaining("test") == 5
        bucket.is_allowed("test")
        assert bucket.remaining("test") == 4

    def test_cleanup_removes_stale_entries(self) -> None:
        import time
        bucket = TokenBucket(max_requests=100, window_seconds=0.01)
        bucket.is_allowed("stale-key")
        assert "stale-key" in bucket._buckets
        time.sleep(0.02)
        bucket.cleanup()
        assert "stale-key" not in bucket._buckets
