"""Unit tests for the sliding window rate limiter."""

from __future__ import annotations

import pytest

from tengu.exceptions import RateLimitError
from tengu.security.rate_limiter import SlidingWindowRateLimiter


class TestSlidingWindowRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_within_limit(self):
        limiter = SlidingWindowRateLimiter(max_per_minute=5, max_concurrent=3)
        # Should not raise for first 5 calls
        for _ in range(5):
            await limiter.acquire("test")
            await limiter.release("test")

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        limiter = SlidingWindowRateLimiter(max_per_minute=2, max_concurrent=10)

        await limiter.acquire("test")
        await limiter.acquire("test")
        # Third call should exceed rate limit
        with pytest.raises(RateLimitError):
            await limiter.acquire("test")

    @pytest.mark.asyncio
    async def test_concurrent_limit_exceeded(self):
        limiter = SlidingWindowRateLimiter(max_per_minute=100, max_concurrent=2)

        # Acquire 2 slots without releasing
        await limiter.acquire("nmap")
        await limiter.acquire("nmap")

        # Third concurrent acquisition should fail
        with pytest.raises(RateLimitError):
            await limiter.acquire("nmap")

    @pytest.mark.asyncio
    async def test_release_allows_new_acquisition(self):
        limiter = SlidingWindowRateLimiter(max_per_minute=100, max_concurrent=1)

        await limiter.acquire("test")
        await limiter.release("test")

        # Should work after release
        await limiter.acquire("test")
        await limiter.release("test")

    @pytest.mark.asyncio
    async def test_different_tools_have_separate_limits(self):
        limiter = SlidingWindowRateLimiter(max_per_minute=100, max_concurrent=1)

        await limiter.acquire("nmap")
        # Different tool should have its own concurrent slot
        await limiter.acquire("nuclei")

        await limiter.release("nmap")
        await limiter.release("nuclei")

    @pytest.mark.asyncio
    async def test_get_stats(self):
        limiter = SlidingWindowRateLimiter(max_per_minute=10, max_concurrent=3)
        await limiter.acquire("test")

        stats = limiter.get_stats("test")
        assert stats["active_concurrent"] == 1
        assert stats["max_concurrent"] == 3
        assert stats["max_per_minute"] == 10

        await limiter.release("test")
