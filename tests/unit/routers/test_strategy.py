"""
``app.routers.strategy`` 龙头复盘策略接口契约测试。

该路由代理上游 NDJSON 文件，用例通过替换 ``requests.get`` 来模拟上游响应，
覆盖：正常解析、404 无数据、未知策略、上游异常与进程内缓存。
"""

from __future__ import annotations

import json

import pytest

from app.routers import strategy


class FakeResponse:
    """``requests.Response`` 替身。"""

    def __init__(self, content: bytes = b"", status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _ndjson(*records) -> bytes:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in records).encode("utf-8")


@pytest.fixture(autouse=True)
def clear_strategy_cache():
    """每个用例前后清空进程内缓存，避免相互影响。"""
    strategy._cache.clear()
    yield
    strategy._cache.clear()


@pytest.fixture
async def client(make_client):
    return await make_client(strategy.router, prefix="/api")


@pytest.fixture
def fake_get(monkeypatch):
    """替换 ``requests.get``，返回可配置的响应。"""

    def _install(content: bytes = b"", status_code: int = 200, raiser=None):
        calls: list = []

        def _get(url, **kwargs):
            calls.append(url)
            if raiser is not None:
                raise raiser
            return FakeResponse(content, status_code)

        monkeypatch.setattr(strategy.requests, "get", _get)
        return calls

    return _install


@pytest.mark.contract
class TestMonthlyStrategy:
    async def test_parses_upstream_rows(self, client, fake_get):
        fake_get(
            _ndjson(
                {
                    "selected_date": "2026-09-01",
                    "code": "600519",
                    "name": "贵州茅台",
                    "price": "1680.5",
                    "highest_price": "1710.2",
                    "closing_price": "1705.0",
                },
                {
                    "selected_date": "2026-09-02",
                    "code": "300750",
                    "name": "宁德时代",
                    "price": "210.0",
                    "highest_price": "215.5",
                    "closing_price": "212.0",
                },
            )
        )

        response = await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202609})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["has_data"] is True
        assert body["strategy_title"] == "题材轮动策略"
        assert len(body["rows"]) == 2
        assert body["rows"][0]["code"] == "600519"
        assert body["rows"][0]["name"] == "贵州茅台"

    async def test_uses_correct_upstream_url(self, client, fake_get):
        calls = fake_get(_ndjson({"code": "600519"}))
        await client.get("/api/strategy/monthly", params={"strategy": "cyb", "month": 202609})
        assert calls == ["https://gp.domekj.top/peizhi/cyb_202609.txt"]

    async def test_computes_monthly_totals(self, client, fake_get):
        fake_get(
            _ndjson(
                {"code": "A", "highest_price": "1.0[2.50%]", "closing_price": "1.0[1.00%]"},
                {"code": "B", "highest_price": "1.0[3.50%]", "closing_price": "1.0[2.00%]"},
            )
        )
        body = (
            await client.get("/api/strategy/monthly", params={"strategy": "zb", "month": 202609})
        ).json()
        assert body["stats"]["highest_total"] == 6.0
        assert body["stats"]["closing_total"] == 3.0
        assert body["stats"]["count"] == 2

    async def test_zero_price_is_normalized_to_empty_string(self, client, fake_get):
        fake_get(_ndjson({"code": "600519", "price": "0", "highest_price": "0", "closing_price": "0"}))
        body = (
            await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202609})
        ).json()
        assert body["rows"][0]["price"] == ""
        assert body["rows"][0]["highest_price"] == ""

    async def test_404_means_no_data(self, client, fake_get):
        fake_get(b"", status_code=404)
        response = await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202601})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["has_data"] is False
        assert body["rows"] == []
        assert body["message"] == "该月份无数据"

    async def test_empty_body_means_no_data(self, client, fake_get):
        fake_get(b"")
        body = (
            await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202609})
        ).json()
        assert body["has_data"] is False


@pytest.mark.contract
class TestErrorHandling:
    async def test_unknown_strategy_is_rejected(self, client, fake_get):
        response = await client.get("/api/strategy/monthly", params={"strategy": "unknown", "month": 202609})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "未知策略" in body["message"]

    async def test_missing_strategy_param_returns_422(self, client):
        response = await client.get("/api/strategy/monthly", params={"month": 202609})
        assert response.status_code == 422

    async def test_missing_month_param_returns_422(self, client):
        response = await client.get("/api/strategy/monthly", params={"strategy": "tcld"})
        assert response.status_code == 422

    async def test_upstream_failure_is_reported(self, client, fake_get):
        fake_get(raiser=RuntimeError("connection reset"))
        response = await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202609})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["has_data"] is False
        assert "数据获取失败" in body["message"]


@pytest.mark.contract
class TestCaching:
    async def test_second_call_is_served_from_cache(self, client, fake_get):
        calls = fake_get(_ndjson({"code": "600519", "name": "贵州茅台"}))
        first = await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202609})
        second = await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202609})

        assert len(calls) == 1, "缓存命中时不应重复请求上游"
        assert second.json()["cached"] is True
        assert "cached" not in first.json()

    async def test_different_months_are_cached_separately(self, client, fake_get):
        calls = fake_get(_ndjson({"code": "600519"}))
        await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202609})
        await client.get("/api/strategy/monthly", params={"strategy": "tcld", "month": 202610})
        assert len(calls) == 2


class TestParsePercent:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("6.76[-0.88%]", -0.88),
            ("1.0[2.50%]", 2.5),
            ("no brackets", None),
            ("", None),
            (None, None),
        ],
    )
    def test_parse_percent(self, raw, expected):
        assert strategy.parse_percent(raw) == expected
