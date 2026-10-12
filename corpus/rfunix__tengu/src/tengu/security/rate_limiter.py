"""Rate limiting for tool invocations.

Prevents abuse and accidental DoS from rapid-fire scan requests.
Uses a sliding window algorithm backed by in-memory state (no Redis needed
for single-server deployments).
"""

from __future__ import annotations

import asyncio
import time
from collections import deque

import structlog

from tengu.exceptions import RateLimitError

logger = structlog.get_logger(__name__)


class SlidingWindowRateLimiter:
    """Sliding window rate limiter with per-tool tracking."""

    def __init__(
        self,
        max_per_minute: int = 10,
        max_concurrent: int = 3,
    ) -> None:
        self._max_per_minute = max_per_minute
        self._max_concurrent = max_concurrent
        self._window_seconds = 60

        # timestamps of recent calls per tool (or "global")
        self._call_times: dict[str, deque[float]] = {}
        # count of currently running scans per tool
        self._active: dict[str, int] = {}
        self._lock = asyncio.Lock()

    def _get_window(self, key: str) -> deque[float]:
        if key not in self._call_times:
            self._call_times[key] = deque()
        return self._call_times[key]

    def _cleanup_window(self, window: deque[float]) -> None:
        """Remove timestamps older than the sliding window."""
        cutoff = time.monotonic() - self._window_seconds
        while window and window[0] < cutoff:
            window.popleft()

    async def acquire(self, tool: str = "global") -> None:
        """Acquire rate limit token. Raises RateLimitError if limit exceeded."""
        async with self._lock:
            window = self._get_window(tool)
            self._cleanup_window(window)

            active = self._active.get(tool, 0)

            if active >= self._max_concurrent:
                raise RateLimitError(
                    f"Too many concurrent scans for '{tool}' "
                    f"({active}/{self._max_concurrent}). Wait for running scans to finish."
                )

            if len(window) >= self._max_per_minute:
                oldest = window[0]
                wait = self._window_seconds - (time.monotonic() - oldest)
                raise RateLimitError(
                    f"Rate limit for '{tool}': {len(window)}/{self._max_per_minute} "
                    f"calls in the last minute. Retry in ~{wait:.0f}s."
                )

            window.append(time.monotonic())
            self._active[tool] = active + 1
            logger.debug("Rate limit token acquired", tool=tool, active=active + 1)

    async def release(self, tool: str = "global") -> None:
        """Release a concurrent slot after a scan completes."""
        async with self._lock:
            current = self._active.get(tool, 0)
            self._active[tool] = max(0, current - 1)
            logger.debug("Rate limit token released", tool=tool, active=self._active[tool])

    def get_stats(self, tool: str = "global") -> dict[str, int]:
        """Return current rate limit statistics for a tool."""
        window = self._get_window(tool)
        self._cleanup_window(window)
        return {
            "calls_in_window": len(window),
            "max_per_minute": self._max_per_minute,
            "active_concurrent": self._active.get(tool, 0),
            "max_concurrent": self._max_concurrent,
        }


# Global rate limiter instance
_rate_limiter: SlidingWindowRateLimiter | None = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Return the global rate limiter (lazy-initialized from config)."""
    global _rate_limiter
    if _rate_limiter is None:
        from tengu.config import get_config

        cfg = get_config()
        _rate_limiter = SlidingWindowRateLimiter(
            max_per_minute=cfg.rate_limiting.max_scans_per_minute,
            max_concurrent=cfg.rate_limiting.max_concurrent_scans,
        )
    return _rate_limiter


class rate_limited:  # noqa: N801
    """Async context manager for rate limiting a scan operation.

    Usage:
        async with rate_limited("nmap"):
            result = await run_nmap(...)
    """

    def __init__(self, tool: str) -> None:
        self._tool = tool
        self._limiter = get_rate_limiter()

    async def __aenter__(self) -> None:
        await self._limiter.acquire(self._tool)

    async def __aexit__(self, *_: object) -> None:
        await self._limiter.release(self._tool)
