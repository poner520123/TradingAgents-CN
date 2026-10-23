"""
``app.routers.favorites`` 自选股接口契约测试。

使用 mongomock 提供的 MongoDB 替身，验证完整的增删改查流程与鉴权。
"""

from __future__ import annotations

import pytest

from app.routers import favorites


@pytest.fixture
async def client(make_client, auth):
    return await make_client(favorites.router, prefix="/api", dependency_overrides=auth)


@pytest.fixture
def auth():
    """
    替换认证依赖。

    必须通过 FastAPI 的 ``dependency_overrides`` 注入 —— 直接 monkeypatch 模块属性
    无效，因为路由定义时依赖函数已被绑定进 dependant。
    """
    from app.routers.auth_db import get_current_user

    async def _fake_current_user():
        return {"id": "user-1", "username": "alice", "is_admin": False, "roles": ["user"]}

    return {get_current_user: _fake_current_user}


@pytest.mark.contract
class TestAddFavorite:
    async def test_add_returns_unified_envelope(self, client, auth):
        response = await client.post(
            "/api/favorites/",
            json={"stock_code": "600519", "stock_name": "贵州茅台", "market": "A股"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "添加成功"
        assert body["data"]["stock_code"] == "600519"

    async def test_added_favorite_appears_in_list(self, client, auth):
        await client.post(
            "/api/favorites/", json={"stock_code": "600519", "stock_name": "贵州茅台"}
        )
        body = (await client.get("/api/favorites/")).json()
        assert body["success"] is True
        codes = [f["stock_code"] for f in body["data"]]
        assert "600519" in codes

    async def test_duplicate_add_returns_400(self, client, auth):
        payload = {"stock_code": "600519", "stock_name": "贵州茅台"}
        await client.post("/api/favorites/", json=payload)
        response = await client.post("/api/favorites/", json=payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "该股票已在自选股中"

    async def test_missing_stock_name_returns_422(self, client, auth):
        response = await client.post("/api/favorites/", json={"stock_code": "600519"})
        assert response.status_code == 422


@pytest.mark.contract
class TestListAndCheck:
    async def test_list_is_empty_initially(self, client, auth):
        body = (await client.get("/api/favorites/")).json()
        assert body["success"] is True
        assert body["data"] == []

    async def test_check_reports_membership(self, client, auth):
        await client.post(
            "/api/favorites/", json={"stock_code": "600519", "stock_name": "贵州茅台"}
        )
        body = (await client.get("/api/favorites/check/600519")).json()
        assert body["success"] is True
        assert body["data"]["is_favorite"] is True

    async def test_check_reports_non_membership(self, client, auth):
        body = (await client.get("/api/favorites/check/000001")).json()
        assert body["data"]["is_favorite"] is False

    async def test_tags_are_aggregated(self, client, auth):
        await client.post(
            "/api/favorites/",
            json={"stock_code": "600519", "stock_name": "贵州茅台", "tags": ["白酒", "核心"]},
        )
        await client.post(
            "/api/favorites/",
            json={"stock_code": "000858", "stock_name": "五粮液", "tags": ["白酒"]},
        )
        body = (await client.get("/api/favorites/tags")).json()
        assert body["success"] is True
        assert "白酒" in body["data"]
        assert "核心" in body["data"]


@pytest.mark.contract
class TestUpdateAndRemove:
    async def test_update_notes_and_tags(self, client, auth):
        await client.post(
            "/api/favorites/", json={"stock_code": "600519", "stock_name": "贵州茅台"}
        )
        response = await client.put(
            "/api/favorites/600519", json={"notes": "长期持有", "tags": ["核心"]}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "更新成功"

        body = (await client.get("/api/favorites/")).json()
        item = next(f for f in body["data"] if f["stock_code"] == "600519")
        assert item["notes"] == "长期持有"
        assert "核心" in item["tags"]

    async def test_update_missing_favorite_returns_404(self, client, auth):
        response = await client.put("/api/favorites/999999", json={"notes": "x"})
        assert response.status_code == 404
        assert response.json()["detail"] == "自选股不存在"

    async def test_remove_favorite(self, client, auth):
        await client.post(
            "/api/favorites/", json={"stock_code": "600519", "stock_name": "贵州茅台"}
        )
        response = await client.delete("/api/favorites/600519")
        assert response.status_code == 200
        assert response.json()["message"] == "移除成功"

        body = (await client.get("/api/favorites/")).json()
        assert body["data"] == []

    async def test_remove_missing_favorite_returns_404(self, client, auth):
        response = await client.delete("/api/favorites/999999")
        assert response.status_code == 404


@pytest.mark.contract
class TestAuthentication:
    async def test_all_endpoints_require_authentication(self, make_client):
        """未认证时所有受保护端点都应返回 401。"""
        from fastapi import HTTPException

        from app.routers.auth_db import get_current_user

        async def _raise():
            raise HTTPException(status_code=401, detail="No authorization header")

        client = await make_client(
            favorites.router, prefix="/api", dependency_overrides={get_current_user: _raise}
        )

        assert (await client.get("/api/favorites/")).status_code == 401
        assert (
            await client.post(
                "/api/favorites/", json={"stock_code": "600519", "stock_name": "x"}
            )
        ).status_code == 401
        assert (await client.put("/api/favorites/600519", json={})).status_code == 401
        assert (await client.delete("/api/favorites/600519")).status_code == 401
        assert (await client.get("/api/favorites/check/600519")).status_code == 401
        assert (await client.get("/api/favorites/tags")).status_code == 401
