"""``app.core.redis_client.RedisService`` 测试。

覆盖 JSON 存取、TTL 计数、队列操作、集合操作、分布式锁，
以及「Redis 不可用时优雅降级」这一关键容错契约。
"""

from __future__ import annotations

import pytest

from app.core.redis_client import RedisKeys, RedisService, get_redis_service


@pytest.fixture
def service(redis_client, monkeypatch):
    """绑定到 fakeredis 的 RedisService 实例。"""
    from app.core import redis_client as redis_module

    monkeypatch.setattr(redis_module, "_redis_service", None, raising=False)
    svc = RedisService()
    assert svc.is_available is True
    return svc


class TestRedisKeys:
    """键名常量契约 —— 前后端/服务间共享，不能随意变更。"""

    def test_user_scoped_keys(self):
        assert RedisKeys.USER_PENDING_QUEUE == "user:{user_id}:pending"
        assert RedisKeys.USER_PROCESSING_SET == "user:{user_id}:processing"

    def test_task_keys(self):
        assert RedisKeys.TASK_PROGRESS == "task:{task_id}:progress"
        assert RedisKeys.TASK_RESULT == "task:{task_id}:result"
        assert RedisKeys.TASK_LOCK == "task:{task_id}:lock"

    def test_quota_key(self):
        assert RedisKeys.USER_DAILY_QUOTA == "quota:{user_id}:{date}"


class TestJsonOperations:
    async def test_set_and_get_json(self, service):
        await service.set_json("k1", {"a": 1, "b": "中文"})
        assert await service.get_json("k1") == {"a": 1, "b": "中文"}

    async def test_get_missing_key_returns_none(self, service):
        assert await service.get_json("missing") is None

    async def test_set_with_ttl(self, service):
        await service.set_with_ttl("k2", "value", ttl=60)
        assert await service.redis.get("k2") == "value"

    async def test_increment_with_ttl(self, service):
        assert await service.increment_with_ttl("counter", ttl=60) == 1
        assert await service.increment_with_ttl("counter", ttl=60) == 2

    async def test_increment_with_ttl_sets_expiry(self, service):
        await service.increment_with_ttl("counter2", ttl=30)
        assert await service.redis.ttl("counter2") > 0


class TestQueueOperations:
    async def test_add_and_pop_from_queue(self, service):
        await service.add_to_queue("q", {"task_id": "t1"})
        item = await service.pop_from_queue("q", timeout=1)
        assert item == {"task_id": "t1"}

    async def test_pop_from_empty_queue_returns_none(self, service):
        assert await service.pop_from_queue("empty", timeout=1) is None

    async def test_get_queue_length(self, service):
        await service.add_to_queue("q2", {"a": 1})
        await service.add_to_queue("q2", {"a": 2})
        assert await service.get_queue_length("q2") == 2


class TestSetOperations:
    async def test_add_remove_and_size(self, service):
        await service.add_to_set("s", "x")
        assert bool(await service.is_in_set("s", "x")) is True
        assert await service.get_set_size("s") == 1
        await service.remove_from_set("s", "x")
        assert bool(await service.is_in_set("s", "x")) is False


class TestDistributedLock:
    """``acquire_lock`` 返回锁值（uuid 字符串），``release_lock`` 需要该锁值做 CAS 释放。"""

    async def test_acquire_returns_lock_value(self, service):
        lock_value = await service.acquire_lock("lock:1", timeout=10)
        assert isinstance(lock_value, str) and lock_value

    async def test_second_acquire_fails_while_held(self, service):
        assert await service.acquire_lock("lock:2", timeout=10) is not None
        assert await service.acquire_lock("lock:2", timeout=10) is None

    async def test_release_allows_reacquire(self, service):
        lock_value = await service.acquire_lock("lock:3", timeout=10)
        await service.release_lock("lock:3", lock_value)
        assert await service.acquire_lock("lock:3", timeout=10) is not None

    async def test_release_with_wrong_value_does_not_delete_lock(self, service):
        """CAS 语义：锁值不匹配时不能释放他人的锁。"""
        await service.acquire_lock("lock:4", timeout=10)
        result = await service.release_lock("lock:4", "not-the-owner")
        assert result == 0
        assert await service.acquire_lock("lock:4", timeout=10) is None

    async def test_release_of_unheld_lock_is_safe(self, service):
        assert await service.release_lock("lock:never-held", "whatever") == 0


class TestGracefulDegradation:
    """Redis 不可用时，所有方法必须静默降级而不是抛异常。"""

    @pytest.fixture
    def unavailable_service(self, monkeypatch):
        from app.core import redis_client as redis_module

        monkeypatch.setattr(redis_module, "redis_service", None, raising=False)
        svc = RedisService()
        # 强制标记为不可用
        svc._available = False
        svc.redis = None
        return svc

    async def test_is_available_false(self, unavailable_service):
        assert unavailable_service.is_available is False

    async def test_json_ops_become_noop(self, unavailable_service):
        await unavailable_service.set_json("k", {"a": 1})
        assert await unavailable_service.get_json("k") is None

    async def test_queue_ops_return_safe_defaults(self, unavailable_service):
        await unavailable_service.add_to_queue("q", {"a": 1})
        assert await unavailable_service.pop_from_queue("q") is None
        assert await unavailable_service.get_queue_length("q") == 0

    async def test_lock_returns_none(self, unavailable_service):
        assert await unavailable_service.acquire_lock("lock") is None
        assert await unavailable_service.release_lock("lock", "v") is None

    async def test_increment_returns_zero(self, unavailable_service):
        assert await unavailable_service.increment_with_ttl("c") == 0


class TestSingleton:
    def test_get_redis_service_returns_instance(self, service):
        assert isinstance(get_redis_service(), RedisService)
