"""``app.routers.health`` 健康检查接口契约测试。"""

from __future__ import annotations

import pytest

from app.routers import health


@pytest.fixture
async def client(make_client):
    return await make_client(health.router, prefix="/api")


@pytest.mark.contract
class TestHealthEndpoint:
    async def test_health_returns_unified_envelope(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "服务运行正常"
        assert body["data"]["status"] == "ok"
        assert body["data"]["service"] == "TA API"
        assert isinstance(body["data"]["timestamp"], int)

    async def test_health_reports_version(self, client):
        body = (await client.get("/api/health")).json()
        assert body["data"]["version"], "版本号不应为空"

    async def test_version_matches_version_file(self, client):
        from pathlib import Path

        version_file = Path(__file__).resolve().parents[3] / "VERSION"
        body = (await client.get("/api/health")).json()
        if version_file.exists():
            assert body["data"]["version"] == version_file.read_text(encoding="utf-8").strip()


@pytest.mark.contract
class TestKubernetesProbes:
    async def test_healthz(self, client):
        response = await client.get("/api/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    async def test_readyz(self, client):
        response = await client.get("/api/readyz")
        assert response.status_code == 200
        assert response.json() == {"ready": True}
