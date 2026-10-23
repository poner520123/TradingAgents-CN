"""
分析任务接口的端到端契约测试（集成层）。

覆盖「提交分析 → 轮询状态 → 读取结果 → 取消/删除」的完整生命周期。
分析引擎本身（LangGraph + LLM）被替身替换，只验证接口编排与状态流转。

替身需严格匹配真实服务签名（见 ``app.services.simple_analysis_service``）：
* ``get_task_status(task_id)`` —— **不带** user_id
* 状态对象中的结果字段名为 ``result_data``
* ``cancel_task`` 走的是 QueueService（``get_queue_service`` 依赖）
* ``delete_task`` 需要 ``svc.memory_manager.remove_task``
"""

from __future__ import annotations

import pytest

from app.routers import analysis


class FakeMemoryManager:
    def __init__(self):
        self.removed: list = []

    async def remove_task(self, task_id):
        self.removed.append(task_id)
        return True


class FakeAnalysisService:
    """分析服务替身：模拟任务状态机。"""

    def __init__(self):
        self.tasks: dict = {}
        self.executed: list = []
        self.memory_manager = FakeMemoryManager()

    async def create_analysis_task(self, user_id, request):
        task_id = f"task-{len(self.tasks) + 1}"
        symbol = getattr(request, "symbol", None) or getattr(request, "stock_code", None)
        self.tasks[task_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "symbol": symbol,
            "status": "pending",
            "progress": 0,
            "result_data": None,
        }
        return {
            "task_id": task_id,
            "symbol": symbol,
            "status": "pending",
            "message": "任务已创建",
        }

    async def execute_analysis_background(self, task_id, user_id, request):
        self.executed.append(task_id)
        task = self.tasks[task_id]
        task["status"] = "completed"
        task["progress"] = 100
        task["result_data"] = {
            "summary": "## 摘要\n技术面良好",
            "recommendation": "买入",
            "decision": {"action": "买入", "target_price": 1850.0},
            "tokens_used": 1234,
        }

    async def get_task_status(self, task_id):
        task = self.tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "symbol": task["symbol"],
            "result_data": task["result_data"],
        }

    async def list_user_tasks(self, user_id, **kwargs):
        return list(self.tasks.values())

    async def get_user_analysis_history(self, user_id, **kwargs):
        return list(self.tasks.values())


class FakeQueueService:
    """队列服务替身（cancel_task 依赖）。"""

    def __init__(self):
        self.tasks: dict = {}
        self.cancelled: list = []

    async def get_task(self, task_id):
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id):
        self.cancelled.append(task_id)
        return True

    async def get_user_queue_status(self, user_id):
        return {"pending": 0, "processing": 0}


@pytest.fixture
def service(monkeypatch):
    fake = FakeAnalysisService()
    monkeypatch.setattr(analysis, "get_simple_analysis_service", lambda: fake)
    return fake


@pytest.fixture
def queue_service():
    return FakeQueueService()


@pytest.fixture
def auth():
    from app.routers.auth_db import get_current_user

    async def _fake_current_user():
        return {"id": "user-1", "username": "alice", "is_admin": False, "roles": ["user"]}

    return {get_current_user: _fake_current_user}


@pytest.fixture
async def client(make_client, auth, queue_service):
    overrides = dict(auth)
    overrides[analysis.get_queue_service] = lambda: queue_service
    return await make_client(
        analysis.router, prefix="/api/analysis", dependency_overrides=overrides
    )


async def _submit(client, symbol="600519"):
    return await client.post(
        "/api/analysis/single",
        json={"symbol": symbol, "parameters": {"analysis_date": "2026-09-01T00:00:00"}},
    )


@pytest.mark.integration
class TestAnalysisLifecycle:
    async def test_submit_creates_task_and_runs_in_background(self, client, service):
        response = await _submit(client)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "分析任务已在后台启动"
        assert body["data"]["task_id"] == "task-1"
        assert body["data"]["symbol"] == "600519"

        # BackgroundTasks 在响应返回前执行完毕
        assert service.executed == ["task-1"]
        assert service.tasks["task-1"]["status"] == "completed"

    async def test_status_endpoint_reflects_completion(self, client, service):
        await _submit(client)
        response = await client.get("/api/analysis/tasks/task-1/status")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "completed"
        assert body["data"]["progress"] == 100

    async def test_status_of_unknown_task_returns_404(self, client, service):
        response = await client.get("/api/analysis/tasks/does-not-exist/status")
        assert response.status_code == 404

    async def test_status_falls_back_to_mongodb(self, client, service, async_db):
        """内存中无记录时，从 MongoDB 的 analysis_tasks 集合恢复状态。"""
        await async_db["analysis_tasks"].insert_one(
            {
                "task_id": "task-from-db",
                "status": "running",
                "progress": 42,
                "symbol": "000001",
            }
        )
        response = await client.get("/api/analysis/tasks/task-from-db/status")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "running"
        assert body["data"]["progress"] == 42
        assert body["data"]["symbol"] == "000001"
        assert body["data"]["source"] == "mongodb_tasks"

    async def test_result_endpoint_returns_analysis(self, client, service):
        await _submit(client)
        response = await client.get("/api/analysis/tasks/task-1/result")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["recommendation"] == "买入"
        assert body["data"]["decision"]["target_price"] == 1850.0


@pytest.mark.integration
class TestAnalysisRequestValidation:
    async def test_invalid_parameters_type_returns_422(self, client, service):
        response = await client.post(
            "/api/analysis/single", json={"symbol": "600519", "parameters": "not-an-object"}
        )
        assert response.status_code == 422

    async def test_invalid_nested_field_type_returns_422(self, client, service):
        response = await client.post(
            "/api/analysis/single",
            json={"symbol": "600519", "parameters": {"research_depth": 123}},
        )
        assert response.status_code == 422

    async def test_symbol_is_optional(self, client, service):
        """symbol / stock_code 均为可选，缺失时不报 422（由服务层兜底）。"""
        response = await client.post("/api/analysis/single", json={})
        assert response.status_code == 200


@pytest.mark.integration
class TestTaskManagement:
    async def test_cancel_task_requires_ownership(self, client, service, queue_service):
        queue_service.tasks["task-1"] = {"user": "another-user"}
        response = await client.post("/api/analysis/tasks/task-1/cancel")
        assert response.status_code == 400

    async def test_cancel_task(self, client, service, queue_service):
        queue_service.tasks["task-1"] = {"user": "user-1"}
        response = await client.post("/api/analysis/tasks/task-1/cancel")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert queue_service.cancelled == ["task-1"]

    async def test_delete_task_removes_from_memory_and_db(self, client, service, async_db):
        await async_db["analysis_tasks"].insert_one({"task_id": "task-1", "symbol": "600519"})

        response = await client.delete("/api/analysis/tasks/task-1")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["message"] == "任务已删除"
        assert service.memory_manager.removed == ["task-1"]
        assert await async_db["analysis_tasks"].count_documents({"task_id": "task-1"}) == 0

    async def test_delete_unknown_task_is_idempotent(self, client, service):
        response = await client.delete("/api/analysis/tasks/nope")
        assert response.status_code == 200
        assert response.json()["message"] == "任务未找到"


@pytest.mark.integration
class TestAuthentication:
    async def test_endpoints_require_authentication(self, make_client):
        from fastapi import HTTPException

        from app.routers.auth_db import get_current_user

        async def _raise():
            raise HTTPException(status_code=401, detail="No authorization header")

        client = await make_client(
            analysis.router,
            prefix="/api/analysis",
            dependency_overrides={get_current_user: _raise},
        )
        response = await client.post("/api/analysis/single", json={"symbol": "600519"})
        assert response.status_code == 401
