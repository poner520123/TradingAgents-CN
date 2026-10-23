"""
``app.routers.quotes`` 行情接口契约测试。

行情数据来自外部数据源，测试中用替身服务替代 ``get_quotes_service``，
只验证路由层的入参校验与响应结构。
"""

from __future__ import annotations

from typing import Dict, List

import pytest

from app.routers import quotes
from tests.fakes.factories import quotes_payload


class FakeQuotesService:
    """行情服务替身。"""

    def __init__(self, payload: Dict[str, Dict] = None, single: Dict = None):
        self.payload = payload if payload is not None else quotes_payload()
        self.single = single
        self.requested: List[str] = []

    async def get_quotes(self, codes: List[str]) -> Dict[str, Dict]:
        self.requested = list(codes)
        return {c: self.payload[c] for c in codes if c in self.payload}

    async def fetch_single_stock(self, code: str):
        return self.single


@pytest.fixture
def fake_service(monkeypatch):
    service = FakeQuotesService()
    monkeypatch.setattr(quotes, "get_quotes_service", lambda: service)
    return service


@pytest.fixture
async def client(make_client):
    return await make_client(quotes.router, prefix="/api")


@pytest.mark.contract
class TestBatchQuotes:
    async def test_returns_quote_map(self, client, fake_service):
        response = await client.post("/api/quotes/batch", json=["600519", "300750"])
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert set(body["data"]) == {"600519", "300750"}
        assert body["data"]["600519"]["pct_chg"] == 1.23

    async def test_passes_codes_to_service(self, client, fake_service):
        await client.post("/api/quotes/batch", json=["600519"])
        assert fake_service.requested == ["600519"]

    async def test_unknown_codes_are_omitted(self, client, fake_service):
        body = (await client.post("/api/quotes/batch", json=["999999"])).json()
        assert body["success"] is True
        assert body["data"] == {}

    async def test_empty_list_is_accepted(self, client, fake_service):
        response = await client.post("/api/quotes/batch", json=[])
        assert response.status_code == 200
        assert response.json()["data"] == {}

    async def test_invalid_body_returns_422(self, client):
        response = await client.post("/api/quotes/batch", json={"codes": ["600519"]})
        assert response.status_code == 422


@pytest.mark.contract
class TestPctChanges:
    async def test_parses_comma_separated_codes(self, client, fake_service):
        response = await client.get("/api/quotes/pct-changes", params={"codes": "600519,300750"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert set(body["data"]) == {"600519", "300750"}

    async def test_only_returns_pct_chg_and_close(self, client, fake_service):
        body = (await client.get("/api/quotes/pct-changes", params={"codes": "600519"})).json()
        entry = body["data"]["600519"]
        assert set(entry) == {"pct_chg", "close"}

    async def test_strips_whitespace(self, client, fake_service):
        await client.get("/api/quotes/pct-changes", params={"codes": "600519 , 300750"})
        assert fake_service.requested == ["600519", "300750"]

    async def test_missing_codes_returns_business_failure(self, client):
        response = await client.get("/api/quotes/pct-changes")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "请提供股票代码"

    async def test_empty_codes_returns_business_failure(self, client):
        body = (await client.get("/api/quotes/pct-changes", params={"codes": ""})).json()
        assert body["success"] is False


@pytest.mark.contract
class TestSingleQuote:
    async def test_returns_single_quote(self, client, monkeypatch):
        from tests.fakes.factories import quote_payload

        service = FakeQuotesService(single=quote_payload(code="600519"))
        monkeypatch.setattr(quotes, "get_quotes_service", lambda: service)

        response = await client.get("/api/quotes/single/600519")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["code"] == "600519"

    async def test_unavailable_quote_returns_business_failure(self, client, monkeypatch):
        service = FakeQuotesService(single=None)
        monkeypatch.setattr(quotes, "get_quotes_service", lambda: service)

        response = await client.get("/api/quotes/single/600519")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "600519" in body["message"]
