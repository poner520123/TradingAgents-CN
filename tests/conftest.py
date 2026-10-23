"""
pytest 全局 fixtures。

设计原则
--------
1. **零外部依赖**：MongoDB → mongomock，Redis → fakeredis，HTTP 上游 → mock。
2. **隔离性**：每个测试用例拿到干净的 Mongo 集合与 Redis 命名空间。
3. **不触碰业务代码**：所有替身通过 monkeypatch 注入到 ``app.core.database`` 的
   模块级全局变量上（业务代码统一通过 ``get_mongo_db()`` / ``get_redis_client()`` 访问），
   因此无需修改任何被测源码。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, Iterator, Optional

import pytest

# 允许以 `pytest` 直接运行（无需先安装项目）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 测试期间不连接真实服务
os.environ.setdefault("MONGODB_ENABLED", "false")
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only-0123456789")
os.environ.setdefault("DEBUG", "true")

# 缩短数据库探测超时。
# 背景：``tradingagents.dataflows.data_source_manager`` 与
# ``tradingagents.config.database_manager`` 在**模块导入阶段**就会探测 MongoDB/Redis
# 可用性，默认 server selection 超时为 5 秒 × 多个数据源 ≈ 30 秒，
# 导致每导入一次 ``app.routers.*`` 都要空等（``app/routers/__init__.py`` 导入全部 45 个路由）。
# 这些是项目已支持的环境变量，此处仅为测试环境提速，不改变业务逻辑。
os.environ.setdefault("MONGO_SERVER_SELECTION_TIMEOUT_MS", "200")
os.environ.setdefault("MONGO_CONNECT_TIMEOUT_MS", "500")
os.environ.setdefault("MONGO_SOCKET_TIMEOUT_MS", "500")
os.environ.setdefault("TA_USE_APP_CACHE", "false")

import fakeredis.aioredis  # noqa: E402
import httpx  # noqa: E402
import pymongo  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from tests.fakes.async_mongo import (  # noqa: E402
    AsyncDatabaseProxy,
    make_async_database,
    make_async_mongo_client,
)


# --------------------------------------------------------------------------- #
# pymongo 快速失败垫片
# --------------------------------------------------------------------------- #
# 背景：``app.services.user_service`` / ``app.services.stock_map_service`` 在 **模块导入
# 阶段**就会调用 ``collection.create_index()``，这会触发真实的 server selection。
# 当本机没有 MongoDB 时，pymongo 默认等待 30 秒才抛错，导致每导入一次
# ``app.routers.*`` 就白等 30 秒（``app/routers/__init__.py`` 会导入全部 45 个路由）。
#
# 这里把 pymongo 客户端的连接超时压到 200ms，让它快速失败并回退到内存模式。
# 仅为测试环境垫片，不修改任何业务代码。
_OriginalMongoClient = pymongo.MongoClient


class _FastFailMongoClient(_OriginalMongoClient):  # type: ignore[misc,valid-type]
    """连接不可用时快速失败，避免 30 秒 / 5 秒的 server selection 超时。"""

    def __init__(self, *args, **kwargs):
        # 注意：这里必须**强制覆盖**而非 setdefault —— ``app.core.database.get_mongo_db_sync()``
        # 与 ``tradingagents.config.database_manager`` 都显式传入了 5000ms 的
        # serverSelectionTimeoutMS，setdefault 不会生效。
        kwargs["serverSelectionTimeoutMS"] = 200
        kwargs["connectTimeoutMS"] = 500
        kwargs["socketTimeoutMS"] = 3000
        super().__init__(*args, **kwargs)


pymongo.MongoClient = _FastFailMongoClient  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# MongoDB
# --------------------------------------------------------------------------- #
# 说明：数据库使用 **session 级** 作用域。原因是部分服务是模块级单例且会缓存
# ``self.db``（例如 ``favorites_service._get_db()``），若每个用例都新建数据库，
# 单例会持有上一个用例的库对象，导致数据串味。
# 隔离通过 ``clean_database`` fixture 在每个用例前清空集合来保证。
@pytest.fixture(scope="session")
def mongo_client():
    """同步 mongomock 客户端（供 user_service 等同步代码使用）。"""
    client = make_async_mongo_client()
    yield client
    client.close()


@pytest.fixture(scope="session")
def mongo_db(mongo_client):
    """同步 mongomock 数据库。"""
    return mongo_client["tradingagents_test"]


@pytest.fixture(scope="session")
def async_db(mongo_db) -> AsyncDatabaseProxy:
    """motor 兼容的异步数据库代理。"""
    return make_async_database(mongo_db)


@pytest.fixture(autouse=True)
def clean_database(mongo_db):
    """每个用例开始前清空所有集合，保证用例间互不影响。"""
    for name in list(mongo_db.list_collection_names()):
        mongo_db.drop_collection(name)
    yield


@pytest.fixture
def redis_client() -> AsyncIterator[Any]:
    """fakeredis 异步客户端（decode_responses=True，与生产一致）。"""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    # fakeredis 关闭是同步的，忽略其返回值


@pytest.fixture(autouse=True)
def clean_redis(redis_client):
    """每个用例前清空 Redis 键空间。"""
    yield


@pytest.fixture(autouse=True)
def patch_database_globals(monkeypatch, async_db, redis_client, mongo_client):
    """
    将测试替身注入 ``app.core.database`` 的模块级全局变量。

    业务代码统一通过 ``get_mongo_db()`` / ``get_redis_client()`` 取用，
    这两个函数直接读取模块级变量，因此 patch 全局即可整体生效。
    """
    from app.core import database as db_module

    monkeypatch.setattr(db_module, "mongo_client", mongo_client, raising=False)
    monkeypatch.setattr(db_module, "mongo_db", async_db, raising=False)
    monkeypatch.setattr(db_module, "redis_client", redis_client, raising=False)
    monkeypatch.setattr(db_module, "redis_pool", None, raising=False)
    monkeypatch.setattr(db_module, "_sync_mongo_client", mongo_client, raising=False)
    monkeypatch.setattr(db_module, "_sync_mongo_db", mongo_client["tradingagents_test"], raising=False)

    # 强制重建 RedisService 单例，使其绑定到测试用的 fakeredis
    from app.core import redis_client as redis_module

    monkeypatch.setattr(redis_module, "redis_service", None, raising=False)

    yield

    # 复位单例，避免污染后续测试
    monkeypatch.setattr(redis_module, "redis_service", None, raising=False)


# --------------------------------------------------------------------------- #
# 用户 / 认证
# --------------------------------------------------------------------------- #
@pytest.fixture
def active_user(mongo_db):
    """在 users 集合中创建一个激活的普通用户，并让 user_service 指向 mock 库。"""
    from app.services import user_service as user_module
    from tests.fakes.factories import user_doc

    doc = user_doc(username="testuser", is_admin=False, is_active=True)
    mongo_db.users.insert_one(doc)

    service = user_module.user_service
    original = (service.client, service.db, service.users_collection)
    service.client = mongo_db.client
    service.db = mongo_db
    service.users_collection = mongo_db.users
    try:
        yield doc
    finally:
        service.client, service.db, service.users_collection = original


@pytest.fixture
def admin_user(mongo_db):
    """在 users 集合中创建一个激活的管理员用户。"""
    from app.services import user_service as user_module
    from tests.fakes.factories import user_doc

    doc = user_doc(username="adminuser", is_admin=True, is_active=True)
    mongo_db.users.insert_one(doc)

    service = user_module.user_service
    original = (service.client, service.db, service.users_collection)
    service.client = mongo_db.client
    service.db = mongo_db
    service.users_collection = mongo_db.users
    try:
        yield doc
    finally:
        service.client, service.db, service.users_collection = original


@pytest.fixture
def auth_token() -> str:
    """一个签名有效、subject 为 ``testuser`` 的访问令牌。"""
    from app.services.auth_service import AuthService

    return AuthService.create_access_token(sub="testuser", expires_minutes=30)


@pytest.fixture
def auth_headers(auth_token: str) -> Dict[str, str]:
    """普通用户的 Authorization 头。"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers() -> Dict[str, str]:
    """管理员的 Authorization 头。"""
    from app.services.auth_service import AuthService

    token = AuthService.create_access_token(sub="adminuser", expires_minutes=30)
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# FastAPI 测试客户端
# --------------------------------------------------------------------------- #
def build_test_app(
    router=None,
    prefix: str = "",
    *,
    with_cors: bool = True,
    extra_routers: Optional[list] = None,
    dependency_overrides: Optional[Dict[Any, Any]] = None,
) -> FastAPI:
    """
    构建一个**只挂载被测路由**的最小 FastAPI 应用。

    不复用 ``app.main:app``，原因：
    - ``app.main`` 的 lifespan 会启动 APScheduler、爬虫、行情入库等后台任务，
      测试环境不可接受；
    - 45 个路由一起挂载会让失败定位困难。

    代价是「中间件链」不在默认范围内，需要单独用
    ``tests/integration/test_middleware_chain.py`` 显式验证。

    ``dependency_overrides`` 用于替换 ``Depends(...)`` 注入的依赖
    （例如 ``get_current_user``）。注意：直接 monkeypatch 模块属性是**无效**的，
    因为 FastAPI 在路由定义时就把依赖函数对象绑定进了路由的 dependant。
    """
    app = FastAPI(title="TA Test App", version="test")

    if with_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if router is not None:
        app.include_router(router, prefix=prefix)
    for extra in extra_routers or []:
        app.include_router(extra)

    for dependency, override in (dependency_overrides or {}).items():
        app.dependency_overrides[dependency] = override

    return app


@pytest.fixture
async def make_client() -> AsyncIterator[Callable[..., httpx.AsyncClient]]:
    """
    工厂 fixture：``make_client(router, prefix="/api")`` → ``httpx.AsyncClient``。

    使用 ``httpx.ASGITransport`` 直接在进程内调用 ASGI 应用，无需启动真实服务。
    """
    clients: list[httpx.AsyncClient] = []

    async def _make(router=None, prefix: str = "", **kwargs) -> httpx.AsyncClient:
        app = build_test_app(router, prefix, **kwargs)
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        clients.append(client)
        return client

    yield _make

    for client in clients:
        await client.aclose()


@pytest.fixture
async def client(make_client) -> AsyncIterator[httpx.AsyncClient]:
    """挂载全部业务路由的通用客户端（不含 lifespan）。"""
    from app.routers import (
        analysis,
        auth_db,
        favorites,
        health,
        paper,
        quotes,
        strategy,
    )

    app = FastAPI(title="TA Test App", version="test")
    app.include_router(health.router, prefix="/api")
    app.include_router(auth_db.router, prefix="/api/auth")
    app.include_router(quotes.router, prefix="/api")
    app.include_router(strategy.router, prefix="/api")
    app.include_router(favorites.router, prefix="/api")
    app.include_router(paper.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api/analysis")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# --------------------------------------------------------------------------- #
# 环境清理
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    """清理可能影响测试的进程级环境变量。"""
    for key in (
        "TA_USE_APP_CACHE",
        "USE_MONGODB_STORAGE",
        "DOCKER_CONTAINER",
        "TA_CACHE_STRATEGY",
    ):
        monkeypatch.delenv(key, raising=False)
    yield
