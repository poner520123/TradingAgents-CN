"""``app.services.auth_service`` JWT 令牌服务测试。"""

from __future__ import annotations

import time

import jwt
import pytest

from app.core.config import settings
from app.services.auth_service import AuthService, TokenData


class TestCreateAccessToken:
    def test_token_is_valid_jwt_with_subject(self):
        token = AuthService.create_access_token(sub="alice")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "alice"
        assert "exp" in payload

    def test_token_has_three_segments(self):
        token = AuthService.create_access_token(sub="alice")
        assert len(token.split(".")) == 3

    def test_expires_minutes_is_respected(self):
        token = AuthService.create_access_token(sub="alice", expires_minutes=10)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["exp"] - int(time.time()) <= 10 * 60 + 5

    def test_expires_delta_is_in_seconds(self):
        token = AuthService.create_access_token(sub="alice", expires_delta=3600)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["exp"] - int(time.time()) <= 3600 + 5

    def test_default_expiry_comes_from_settings(self):
        token = AuthService.create_access_token(sub="alice")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["exp"] - int(time.time()) <= settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 5

    def test_different_subjects_produce_different_tokens(self):
        assert AuthService.create_access_token(sub="a") != AuthService.create_access_token(sub="b")


class TestVerifyToken:
    def test_valid_token_returns_token_data(self):
        token = AuthService.create_access_token(sub="bob")
        data = AuthService.verify_token(token)
        assert isinstance(data, TokenData)
        assert data.sub == "bob"
        assert data.exp > 0

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "not-a-token",
            "a.b.c",
            "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.wrongsignature",
        ],
    )
    def test_invalid_tokens_return_none(self, bad):
        assert AuthService.verify_token(bad) is None

    def test_token_signed_with_other_secret_is_rejected(self):
        forged = jwt.encode({"sub": "attacker", "exp": int(time.time()) + 600}, "other-secret", algorithm="HS256")
        assert AuthService.verify_token(forged) is None

    def test_expired_token_returns_none(self):
        expired = jwt.encode(
            {"sub": "bob", "exp": int(time.time()) - 60},
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        assert AuthService.verify_token(expired) is None
