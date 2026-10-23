"""
``app.routers.auth_db`` 认证接口契约测试。

用 ``FakeUserService`` 替换真实的用户服务（后者依赖 bcrypt + MongoDB），
验证：登录、令牌刷新、当前用户查询、登出、管理员专属操作与鉴权失败分支。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

import pytest

from app.routers import auth_db


class FakeUserService:
    """用户服务替身。"""

    def __init__(self, users: Optional[dict] = None):
        # username -> SimpleNamespace
        self.users = users or {}
        self.login_calls: list = []
        self.created: list = []

    def _make(self, username, is_admin=False, is_active=True):
        return SimpleNamespace(
            id=f"id-{username}",
            username=username,
            email=f"{username}@example.com",
            is_admin=is_admin,
            is_active=is_active,
            preferences=SimpleNamespace(model_dump=lambda: {"ui_theme": "light"}),
            model_dump=lambda **kw: {
                "id": f"id-{username}",
                "username": username,
                "email": f"{username}@example.com",
                "is_admin": is_admin,
                "is_active": is_active,
            },
        )

    def add(self, username, is_admin=False, is_active=True):
        user = self._make(username, is_admin, is_active)
        self.users[username] = user
        return user

    # --- 同步接口（get_current_user 使用）---
    def get_user_by_username(self, username):
        return self.users.get(username)

    # --- 异步接口 ---
    async def authenticate_user(self, username, password):
        self.login_calls.append((username, password))
        if password == "wrong":
            return None
        return self.users.get(username)

    async def update_user(self, username, user_update):
        return self.users.get(username)

    async def change_password(self, username, old_password, new_password):
        return old_password == "admin123"

    async def reset_password(self, username, new_password):
        return username in self.users

    async def create_user(self, user_create):
        if user_create.username in self.users:
            return None
        user = self.add(user_create.username)
        self.created.append(user_create.username)
        return user

    async def list_users(self, skip=0, limit=100):
        return list(self.users.values())[skip : skip + limit]


@pytest.fixture
def fake_service(monkeypatch):
    service = FakeUserService()
    monkeypatch.setattr(auth_db, "user_service", service)
    return service


@pytest.fixture
async def client(make_client):
    return await make_client(auth_db.router, prefix="/api/auth")


@pytest.mark.contract
class TestLogin:
    async def test_successful_login_returns_tokens(self, client, fake_service):
        fake_service.add("alice")
        response = await client.post(
            "/api/auth/login", json={"username": "alice", "password": "admin123"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "登录成功"
        assert body["data"]["access_token"]
        assert body["data"]["refresh_token"]
        assert body["data"]["expires_in"] == 3600
        assert body["data"]["user"]["username"] == "alice"

    async def test_wrong_password_returns_401(self, client, fake_service):
        fake_service.add("alice")
        response = await client.post(
            "/api/auth/login", json={"username": "alice", "password": "wrong"}
        )
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    async def test_unknown_user_returns_401(self, client, fake_service):
        response = await client.post(
            "/api/auth/login", json={"username": "ghost", "password": "admin123"}
        )
        assert response.status_code == 401

    async def test_missing_field_returns_422(self, client, fake_service):
        response = await client.post("/api/auth/login", json={"username": "alice"})
        assert response.status_code == 422

    async def test_empty_password_is_rejected(self, client, fake_service):
        response = await client.post(
            "/api/auth/login", json={"username": "alice", "password": ""}
        )
        assert response.status_code == 400
        assert "用户名和密码不能为空" in response.json()["detail"]


@pytest.mark.contract
class TestRefreshToken:
    async def test_valid_token_is_refreshed(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("alice")
        refresh = AuthService.create_access_token(sub="alice", expires_delta=3600)

        response = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["access_token"]
        assert body["data"]["refresh_token"]

    async def test_invalid_token_returns_401(self, client, fake_service):
        response = await client.post("/api/auth/refresh", json={"refresh_token": "garbage"})
        assert response.status_code == 401

    async def test_empty_token_returns_401(self, client, fake_service):
        response = await client.post("/api/auth/refresh", json={"refresh_token": ""})
        assert response.status_code == 401

    async def test_inactive_user_cannot_refresh(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("bob", is_active=False)
        refresh = AuthService.create_access_token(sub="bob", expires_delta=3600)
        response = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert response.status_code == 401


@pytest.mark.contract
class TestCurrentUser:
    async def test_me_requires_authorization_header(self, client, fake_service):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_me_rejects_non_bearer_scheme(self, client, fake_service):
        response = await client.get("/api/auth/me", headers={"Authorization": "Basic abc"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authorization format"

    async def test_me_returns_user_payload(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("alice")
        token = AuthService.create_access_token(sub="alice")
        response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["username"] == "alice"
        assert body["data"]["roles"] == ["user"]
        assert body["data"]["is_admin"] is False

    async def test_admin_user_gets_admin_role(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("root", is_admin=True)
        token = AuthService.create_access_token(sub="root")
        body = (
            await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        ).json()
        assert body["data"]["roles"] == ["admin"]

    async def test_inactive_user_is_rejected(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("ghost", is_active=False)
        token = AuthService.create_access_token(sub="ghost")
        response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "User is inactive"

    async def test_unknown_user_is_rejected(self, client, fake_service):
        from app.services.auth_service import AuthService

        token = AuthService.create_access_token(sub="nobody")
        response = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "User not found"


@pytest.mark.contract
class TestLogout:
    async def test_logout_requires_auth(self, client, fake_service):
        response = await client.post("/api/auth/logout")
        assert response.status_code == 401

    async def test_logout_succeeds(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("alice")
        token = AuthService.create_access_token(sub="alice")
        response = await client.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


@pytest.mark.contract
class TestAdminOnlyOperations:
    async def test_reset_password_denied_for_normal_user(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("alice")
        token = AuthService.create_access_token(sub="alice")
        response = await client.post(
            "/api/auth/reset-password",
            json={"username": "bob", "new_password": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "权限不足"

    async def test_reset_password_allowed_for_admin(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("root", is_admin=True)
        fake_service.add("bob")
        token = AuthService.create_access_token(sub="root")
        response = await client.post(
            "/api/auth/reset-password",
            json={"username": "bob", "new_password": "newpass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_list_users_denied_for_normal_user(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("alice")
        token = AuthService.create_access_token(sub="alice")
        response = await client.get(
            "/api/auth/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    async def test_list_users_allowed_for_admin(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("root", is_admin=True)
        fake_service.add("alice")
        token = AuthService.create_access_token(sub="root")
        response = await client.get(
            "/api/auth/users", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["total"] == 2

    async def test_create_user_denied_for_normal_user(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("alice")
        token = AuthService.create_access_token(sub="alice")
        response = await client.post(
            "/api/auth/create-user",
            json={"username": "carl", "email": "carl@example.com", "password": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    async def test_create_user_allowed_for_admin(self, client, fake_service):
        from app.services.auth_service import AuthService

        fake_service.add("root", is_admin=True)
        token = AuthService.create_access_token(sub="root")
        response = await client.post(
            "/api/auth/create-user",
            json={"username": "carl", "email": "carl@example.com", "password": "carlpass"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["username"] == "carl"
        assert "carl" in fake_service.created

    async def test_create_user_rejects_short_password(self, client, fake_service):
        """密码长度由 UserCreate 模型校验（>=6 位），越界时返回 500（业务异常被兜底）。"""
        from app.services.auth_service import AuthService

        fake_service.add("root", is_admin=True)
        token = AuthService.create_access_token(sub="root")
        response = await client.post(
            "/api/auth/create-user",
            json={"username": "carl", "email": "carl@example.com", "password": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 500
