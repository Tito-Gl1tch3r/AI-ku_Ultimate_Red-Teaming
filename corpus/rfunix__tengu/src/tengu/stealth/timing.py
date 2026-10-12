"""Timing controller — jitter and delays between requests to evade rate detection."""

from __future__ import annotations

import asyncio
import random

import structlog

logger = structlog.get_logger(__name__)


class TimingController:
    """Applies randomised delays with jitter to blend into normal traffic patterns."""

    def __init__(
        self,
        min_delay_ms: int = 100,
        max_delay_ms: int = 3000,
        jitter_percent: int = 30,
    ) -> None:
        self._min_delay_ms = min_delay_ms
        self._max_delay_ms = max_delay_ms
        self._jitter_percent = jitter_percent

    async def wait(self) -> None:
        """Wait for a randomized delay with jitter."""
        base = random.uniform(self._min_delay_ms, self._max_delay_ms)
        jitter = base * (self._jitter_percent / 100) * random.uniform(-1, 1)
        delay_ms = max(0, base + jitter)
        delay_s = delay_ms / 1000
        logger.debug("Timing jitter applied", delay_ms=f"{delay_ms:.0f}")
        await asyncio.sleep(delay_s)

    @property
    def min_delay_ms(self) -> int:
        return self._min_delay_ms

    @property
    def max_delay_ms(self) -> int:
        return self._max_delay_ms

    @property
    def jitter_percent(self) -> int:
        return self._jitter_percent
