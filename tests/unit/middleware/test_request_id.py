"""``app.middleware.request_id`` Trace-ID 中间件测试。"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI, Request

from app.middleware.error_handler import global_exception_handler
from app.middleware.request_id import RequestIDMiddleware


@pytest.fixture
def app():
    """
    装配与生产一致的应用结构。

    注意：``ServerErrorMiddleware`` 位于所有用户中间件**之外**，
    ``RequestIDMiddleware`` 无法给 500 响应补头 —— 只有 500 处理器能补。
    因此这里注册与 ``app/main.py`` 相同的全局异常处理器。
    """
    application = FastAPI()
    application.add_middleware(RequestIDMiddleware)
    application.add_exception_handler(Exception, global_exception_handler)

    @application.get("/ping")
    async def ping(request: Request):
        return {
            "request_id": getattr(request.state, "request_id", None),
            "trace_id": getattr(request.state, "trace_id", None),
        }

    @application.get("/boom")
    async def boom():
        raise ValueError("boom")

    return application


@pytest.fixture
async def client(app):
    import httpx

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.contract
class TestRequestIdHeaders:
    async def test_response_contains_trace_headers(self, client):
        response = await client.get("/ping")
        assert response.status_code == 200
        assert "X-Trace-ID" in response.headers
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers

    async def test_trace_id_and_request_id_are_equal(self, client):
        response = await client.get("/ping")
        assert response.headers["X-Trace-ID"] == response.headers["X-Request-ID"]

    async def test_trace_id_is_a_uuid(self, client):
        response = await client.get("/ping")
        uuid.UUID(response.headers["X-Trace-ID"])  # 非法 UUID 会抛异常

    async def test_trace_id_is_exposed_on_request_state(self, client):
        body = (await client.get("/ping")).json()
        assert body["request_id"] == body["trace_id"]
        assert body["trace_id"]

    async def test_each_request_gets_a_unique_id(self, client):
        first = (await client.get("/ping")).headers["X-Trace-ID"]
        second = (await client.get("/ping")).headers["X-Trace-ID"]
        assert first != second

    async def test_process_time_is_numeric(self, client):
        value = (await client.get("/ping")).headers["X-Process-Time"]
        assert float(value) >= 0

    async def test_error_responses_carry_trace_headers(self, client):
        """
        出错请求同样可以通过 X-Trace-ID 与日志关联。

        实现方式：500 响应由 ``ServerErrorMiddleware`` 生成（位于用户中间件之外），
        因此 Trace-ID 头由全局异常处理器补齐，而非由 RequestIDMiddleware 补齐。
        """
        response = await client.get("/boom")
        assert response.status_code == 500
        assert "X-Trace-ID" in response.headers
        assert "X-Request-ID" in response.headers
        uuid.UUID(response.headers["X-Trace-ID"])

    async def test_error_body_contains_request_id(self, client):
        """500 响应体中的 request_id 与响应头一致。"""
        response = await client.get("/boom")
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert body["error"]["request_id"] == response.headers["X-Trace-ID"]
