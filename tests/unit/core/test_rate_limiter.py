"""``app.core.rate_limiter`` 滑动窗口限流器测试。"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core.rate_limiter import (
    AKShareRateLimiter,
    BaoStockRateLimiter,
    RateLimiter,
    TushareRateLimiter,
    get_akshare_rate_limiter,
    get_baostock_rate_limiter,
    get_tushare_rate_limiter,
    reset_all_limiters,
)


class TestRateLimiter:
    async def test_allows_calls_below_limit(self):
        limiter = RateLimiter(max_calls=3, time_window=60, name="test")
        for _ in range(3):
            await limiter.acquire()
        assert limiter.get_stats()["current_calls"] == 3
        assert limiter.get_stats()["total_calls"] == 3
        assert limiter.get_stats()["total_waits"] == 0

    async def test_blocks_when_limit_reached(self):
        """窗口内超出配额时必须阻塞等待。窗口取 0.3s 以避免测试耗时过长。"""
        limiter = RateLimiter(max_calls=1, time_window=0.3, name="test")
        await limiter.acquire()

        start = time.time()
        await limiter.acquire()  # 应等待窗口滑出
        elapsed = time.time() - start

        assert elapsed >= 0.2
        assert limiter.get_stats()["total_waits"] == 1

    async def test_old_calls_are_evicted_from_window(self):
        limiter = RateLimiter(max_calls=2, time_window=0.05, name="test")
        await limiter.acquire()
        await limiter.acquire()
        await asyncio.sleep(0.08)
        await limiter.acquire()  # 窗口已滑出，不应阻塞
        assert limiter.get_stats()["total_waits"] == 0

    async def test_stats_report_configuration(self):
        limiter = RateLimiter(max_calls=7, time_window=30, name="cfg")
        stats = limiter.get_stats()
        assert stats["name"] == "cfg"
        assert stats["max_calls"] == 7
        assert stats["time_window"] == 30
        assert stats["avg_wait_time"] == 0

    def test_reset_stats_clears_counters(self):
        limiter = RateLimiter(max_calls=1, time_window=60, name="test")
        limiter.total_calls = 42
        limiter.total_waits = 7
        limiter.reset_stats()
        assert limiter.total_calls == 0
        assert limiter.total_waits == 0
        assert limiter.total_wait_time == 0.0


class TestTushareRateLimiter:
    @pytest.mark.parametrize(
        "tier,expected_calls",
        [
            ("free", 80),       # 100 * 0.8
            ("basic", 160),     # 200 * 0.8
            ("standard", 320),  # 400 * 0.8
            ("premium", 480),   # 600 * 0.8
            ("vip", 640),       # 800 * 0.8
        ],
    )
    def test_tier_limits_with_safety_margin(self, tier, expected_calls):
        limiter = TushareRateLimiter(tier=tier, safety_margin=0.8)
        assert limiter.max_calls == expected_calls
        assert limiter.time_window == 60

    def test_safety_margin_scales_limit(self):
        limiter = TushareRateLimiter(tier="standard", safety_margin=0.5)
        assert limiter.max_calls == 200

    def test_unknown_tier_falls_back_to_standard(self):
        limiter = TushareRateLimiter(tier="nonexistent")
        assert limiter.tier == "standard"
        assert limiter.max_calls == 320


class TestOtherLimiters:
    def test_akshare_defaults(self):
        limiter = AKShareRateLimiter()
        assert limiter.max_calls == 60
        assert limiter.time_window == 60

    def test_baostock_defaults(self):
        limiter = BaoStockRateLimiter()
        assert limiter.max_calls == 100
        assert limiter.time_window == 60


class TestSingletons:
    def setup_method(self):
        reset_all_limiters()

    def teardown_method(self):
        reset_all_limiters()

    def test_getters_return_same_instance(self):
        assert get_tushare_rate_limiter() is get_tushare_rate_limiter()
        assert get_akshare_rate_limiter() is get_akshare_rate_limiter()
        assert get_baostock_rate_limiter() is get_baostock_rate_limiter()

    def test_reset_creates_new_instances(self):
        first = get_akshare_rate_limiter()
        reset_all_limiters()
        assert get_akshare_rate_limiter() is not first
