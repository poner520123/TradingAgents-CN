"""``app.core.response`` 统一响应格式契约测试。"""

from __future__ import annotations

from datetime import datetime

from app.core.response import fail, ok


class TestOk:
    def test_envelope_shape(self):
        payload = ok({"a": 1}, "成功")
        assert payload["success"] is True
        assert payload["data"] == {"a": 1}
        assert payload["message"] == "成功"
        assert "timestamp" in payload
        assert "code" not in payload

    def test_defaults(self):
        payload = ok()
        assert payload["data"] is None
        assert payload["message"] == "ok"

    def test_timestamp_is_iso8601(self):
        payload = ok()
        datetime.fromisoformat(payload["timestamp"])  # 不抛异常即为合法 ISO 格式


class TestFail:
    def test_envelope_shape(self):
        payload = fail("出错了", 400, {"field": "code"})
        assert payload["success"] is False
        assert payload["message"] == "出错了"
        assert payload["code"] == 400
        assert payload["data"] == {"field": "code"}
        assert "timestamp" in payload

    def test_defaults(self):
        payload = fail()
        assert payload["success"] is False
        assert payload["message"] == "error"
        assert payload["code"] == 500
        assert payload["data"] is None


class TestConsistency:
    def test_ok_and_fail_share_common_keys(self):
        """前端 ``request.ts`` 依据 success 字段分支，两种响应必须共享核心键。"""
        common = {"success", "data", "message", "timestamp"}
        assert common.issubset(set(ok()))
        assert common.issubset(set(fail()))

    def test_only_failure_carries_code(self):
        assert "code" not in ok()
        assert "code" in fail()
