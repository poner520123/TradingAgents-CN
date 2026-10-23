"""
``app.middleware.rate_limit`` 速率限制与每日配额中间件测试。

使用 fakeredis 作为计数器后端。

限流拒绝时的响应
----------------
``RateLimitMiddleware`` / ``QuotaMiddleware`` 需要拒绝请求时，会把 ``HTTPException``
转换为等价�� JSON 响应（``{"detail": ...}`` + 原始状态码）返回。

原因：Starlette 的中间件栈为::

    ServerErrorMiddleware → 用户中间件 → ExceptionMiddleware → 路由

负责把 HTTPException 转换成 JSON 响应的 ``ExceptionMiddleware`` 位于**用户中间件之内**，
若在用户中间件中直接 ``raise HTTPException``，它不会被捕获，最终由最外层的
``ServerErrorMiddleware`` 处理，客户端会收到 **500** 而非预期的 **429**。
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request

from app.middleware.rate_limit import QuotaMiddleware, RateLimitMiddleware


def _build_app(middlewares) -> FastAPI:
    application = FastAPI()
    for mw in middlewares:
        application.add_middleware(mw)

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

    @application.get("/api/auth/login")
    async def login():
        return {"ok": True}

    @application.get("/api/analysis/single")
    async def single(request: Request):
        return {"user_id": getattr(request.state, "user_id", None)}

    @application.get("/api/other")
    async def other():
        return {"ok": True}

    return application


@pytest.fixture
async def client():
    import httpx

    app = _build_app([RateLimitMiddleware, QuotaMiddleware])
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.contract
class TestRateLimit:
    async def test_requests_under_limit_pass(self, client):
        for _ in range(5):
            response = await client.get("/api/auth/login")
            assert response.status_code == 200

    async def test_limit_blocks_request(self, client):
        """登录端点限额为 5 次/分钟，第 6 次起被拦截。"""
        statuses = [(await client.get("/api/auth/login")).status_code for _ in range(6)]
        assert statuses[:5] == [200] * 5
        assert statuses[5] == 429

    async def test_limit_returns_429_status_code(self, client):
        for _ in range(5):
            await client.get("/api/auth/login")
        assert (await client.get("/api/auth/login")).status_code == 429

    async def test_429_body_carries_error_code(self, client):
        for _ in range(5):
            await client.get("/api/auth/login")
        body = (await client.get("/api/auth/login")).json()
        assert body["detail"]["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert body["detail"]["error"]["rate_limit"] == 5
        assert body["detail"]["error"]["current_count"] == 6

    async def test_health_check_is_exempt(self, client):
        for _ in range(20):
            assert (await client.get("/api/health")).status_code == 200

    async def test_different_endpoints_have_separate_counters(self, client):
        """登录与单股分析使用不同的计数器键，互不影响。"""
        for _ in range(5):
            await client.get("/api/auth/login")
        assert (await client.get("/api/auth/login")).status_code == 429
        assert (await client.get("/api/analysis/single")).status_code == 200

    async def test_default_limit_applies_to_unlisted_endpoints(self, client):
        """未在白名单中的端点使用默认限额 100。"""
        statuses = [(await client.get("/api/other")).status_code for _ in range(101)]
        assert statuses[:100] == [200] * 100
        assert statuses[100] == 429

    async def test_counter_is_shared_per_client_ip(self, client):
        """未认证时按客户端 IP 计数，同一 IP 的请求共享配额。"""
        for _ in range(5):
            await client.get("/api/auth/login")
        assert (await client.get("/api/auth/login")).status_code == 429


@pytest.mark.contract
class TestQuota:
    async def test_unauthenticated_requests_bypass_quota(self, client):
        """无 user_id 时不计入配额（QuotaMiddleware 直接放行）。

        注意请求数受**速率限制**（/api/analysis/single 为 10 次/分钟）约束，
        因此这里只发 10 次。
        """
        for _ in range(10):
            assert (await client.get("/api/analysis/single")).status_code == 200

    async def test_quota_only_applies_to_listed_endpoints(self, client):
        for _ in range(30):
            assert (await client.get("/api/other")).status_code == 200

    async def test_quota_exceeded_returns_429(self, client, make_client):
        """配额超限同样返回 429 + DAILY_QUOTA_EXCEEDED。"""
        from starlette.types import ASGIApp, Receive, Scope, Send

        class AuthMarkerMiddleware:
            """
            模拟认证中间件：在 scope.state 中写入 user_id。

            Starlette 中**后添加**的用户中间件位于更外层、先于 QuotaMiddleware 执行，
            因此 QuotaMiddleware 读取 request.state.user_id 时能取到值。
            """

            def __init__(self, app: ASGIApp) -> None:
                self.app = app

            async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                if scope["type"] == "http":
                    scope.setdefault("state", {})["user_id"] = "user-1"
                await self.app(scope, receive, send)

        application = FastAPI()
        # 配额设为 2，便于在测试内触发
        application.add_middleware(QuotaMiddleware, daily_quota=2)
        application.add_middleware(AuthMarkerMiddleware)

        @application.get("/api/analysis/single")
        async def single():
            return {"ok": True}

        import httpx

        transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            assert (await c.get("/api/analysis/single")).status_code == 200
            assert (await c.get("/api/analysis/single")).status_code == 200
            response = await c.get("/api/analysis/single")
            assert response.status_code == 429
            body = response.json()
            assert body["detail"]["error"]["code"] == "DAILY_QUOTA_EXCEEDED"
            assert body["detail"]["error"]["daily_quota"] == 2


@pytest.mark.contract
class TestRedisUnavailable:
    async def test_requests_pass_when_redis_is_down(self, monkeypatch):
        """Redis 不可用时中间件必须放行，而不是阻断业务。"""
        import httpx

        from app.middleware import rate_limit as rate_limit_module

        app = _build_app([RateLimitMiddleware, QuotaMiddleware])
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

        class _Unavailable:
            is_available = False

        # 注意：中间件模块通过 `from ... import get_redis_service` 绑定了函数对象，
        # 必须 patch 中间件模块自身的命名空间。
        monkeypatch.setattr(rate_limit_module, "get_redis_service", lambda: _Unavailable())

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            for _ in range(20):
                assert (await c.get("/api/auth/login")).status_code == 200
