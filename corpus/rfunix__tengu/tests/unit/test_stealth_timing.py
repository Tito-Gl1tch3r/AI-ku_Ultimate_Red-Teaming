"""Unit tests for stealth timing controller."""

from __future__ import annotations

import pytest

from tengu.stealth.timing import TimingController


class TestTimingControllerProperties:
    def test_default_min_delay(self):
        tc = TimingController()
        assert tc.min_delay_ms == 100

    def test_default_max_delay(self):
        tc = TimingController()
        assert tc.max_delay_ms == 3000

    def test_default_jitter_percent(self):
        tc = TimingController()
        assert tc.jitter_percent == 30

    def test_custom_min_delay(self):
        tc = TimingController(min_delay_ms=50)
        assert tc.min_delay_ms == 50

    def test_custom_max_delay(self):
        tc = TimingController(max_delay_ms=5000)
        assert tc.max_delay_ms == 5000

    def test_custom_jitter_percent(self):
        tc = TimingController(jitter_percent=10)
        assert tc.jitter_percent == 10

    def test_zero_min_delay_allowed(self):
        tc = TimingController(min_delay_ms=0, max_delay_ms=0)
        assert tc.min_delay_ms == 0

    def test_properties_are_read_only_int(self):
        tc = TimingController(min_delay_ms=200, max_delay_ms=1000, jitter_percent=20)
        assert isinstance(tc.min_delay_ms, int)
        assert isinstance(tc.max_delay_ms, int)
        assert isinstance(tc.jitter_percent, int)


class TestTimingControllerWait:
    @pytest.mark.asyncio
    async def test_wait_completes_with_zero_delay(self):
        tc = TimingController(min_delay_ms=0, max_delay_ms=0, jitter_percent=0)
        # Should complete almost instantly
        await tc.wait()

    @pytest.mark.asyncio
    async def test_wait_completes_with_small_delay(self):
        tc = TimingController(min_delay_ms=1, max_delay_ms=5, jitter_percent=0)
        await tc.wait()

    @pytest.mark.asyncio
    async def test_wait_returns_none(self):
        tc = TimingController(min_delay_ms=0, max_delay_ms=1)
        result = await tc.wait()
        assert result is None
