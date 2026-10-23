"""
``app.routers.paper`` 模拟交易接口契约测试。

覆盖：账户初始化（多币种）、持仓/订单查询、市场代码自动识别、手续费计算。
"""

from __future__ import annotations

import pytest

from app.routers import paper


@pytest.fixture
async def client(make_client, auth):
    return await make_client(paper.router, prefix="/api", dependency_overrides=auth)


@pytest.fixture
def auth():
    """
    替换认证依赖。

    必须通过 FastAPI 的 ``dependency_overrides`` 注入 —— 直接 monkeypatch 模块属性
    无效，因为路由定义时依赖函数已被绑定进 dependant。
    """
    from app.routers.auth_db import get_current_user

    async def _fake_current_user():
        return {"id": "user-1", "username": "trader", "is_admin": False, "roles": ["user"]}

    return {get_current_user: _fake_current_user}


class TestDetectMarketAndCode:
    """市场与代码标准化。"""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("600519", ("CN", "600519")),
            ("000001", ("CN", "000001")),
            ("300750", ("CN", "300750")),
            ("0700.HK", ("HK", "00700")),
            ("00700.HK", ("HK", "00700")),
            ("0700", ("HK", "00700")),
            ("AAPL", ("US", "AAPL")),
            ("aapl", ("US", "AAPL")),
            ("123", ("CN", "000123")),
        ],
    )
    def test_detection(self, raw, expected):
        assert paper._detect_market_and_code(raw) == expected


class TestCalculateCommission:
    """手续费计算。"""

    def test_no_rules_means_no_commission(self):
        assert paper._calculate_commission("CN", "buy", 10000, {}) == 0.0

    def test_rate_and_minimum(self):
        rules = {"commission": {"rate": 0.0003, "min": 5.0}}
        # 10000 * 0.0003 = 3.0 < min 5.0 → 取 5.0
        assert paper._calculate_commission("CN", "buy", 10000, rules) == 5.0
        # 100000 * 0.0003 = 30.0 > min
        assert paper._calculate_commission("CN", "buy", 100000, rules) == 30.0

    def test_stamp_duty_only_on_sell(self):
        rules = {"commission": {"rate": 0.0003, "min": 5.0, "stamp_duty_rate": 0.001}}
        buy = paper._calculate_commission("CN", "buy", 100000, rules)
        sell = paper._calculate_commission("CN", "sell", 100000, rules)
        assert sell == pytest.approx(buy + 100.0)

    def test_hk_extra_fees(self):
        """港股附加费用（交易征费/交易费/结算费）同样位于 commission 子字典内。"""
        rules = {
            "commission": {
                "rate": 0.0,
                "min": 0.0,
                "transaction_levy_rate": 0.00005,
                "trading_fee_rate": 0.00005,
                "settlement_fee_rate": 0.002,
            }
        }
        fee = paper._calculate_commission("HK", "buy", 100000, rules)
        assert fee == pytest.approx(100000 * (0.00005 + 0.00005 + 0.002))

    def test_us_sec_fee_only_on_sell(self):
        rules = {"commission": {"rate": 0.0, "min": 0.0, "sec_fee_rate": 0.0001}}
        assert paper._calculate_commission("US", "buy", 100000, rules) == 0.0
        assert paper._calculate_commission("US", "sell", 100000, rules) == pytest.approx(10.0)


@pytest.mark.contract
class TestAccount:
    async def test_account_is_created_on_first_access(self, client, auth, async_db):
        response = await client.get("/api/paper/account")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True

        accounts = await async_db["paper_accounts"].find_one({"user_id": "user-1"})
        assert accounts is not None
        assert accounts["cash"]["CNY"] == 1_000_000.0
        assert accounts["cash"]["HKD"] == 1_000_000.0
        assert accounts["cash"]["USD"] == 100_000.0
        assert accounts["realized_pnl"] == {"CNY": 0.0, "HKD": 0.0, "USD": 0.0}

    async def test_legacy_scalar_account_is_migrated(self, client, auth, async_db):
        """旧版单标量 cash/realized_pnl 账户应被迁移为多币种结构。"""
        await async_db["paper_accounts"].insert_one(
            {"user_id": "user-1", "cash": 500000.0, "realized_pnl": 1200.0}
        )
        await client.get("/api/paper/account")

        account = await async_db["paper_accounts"].find_one({"user_id": "user-1"})
        assert account["cash"] == {"CNY": 500000.0, "HKD": 0.0, "USD": 0.0}
        assert account["realized_pnl"] == {"CNY": 1200.0, "HKD": 0.0, "USD": 0.0}


@pytest.mark.contract
class TestPositionsAndOrders:
    async def test_positions_empty_by_default(self, client, auth, async_db):
        response = await client.get("/api/paper/positions")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["items"] == []

    async def test_orders_empty_by_default(self, client, auth, async_db):
        response = await client.get("/api/paper/orders")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["items"] == []

    async def test_positions_are_enriched_with_market_value(self, client, auth, async_db):
        await async_db["paper_positions"].insert_one(
            {
                "user_id": "user-1",
                "code": "600519",
                "market": "CN",
                "currency": "CNY",
                "quantity": 100,
                "avg_cost": 1500.0,
            }
        )
        await async_db["market_quotes"].insert_one({"code": "600519", "close": 1680.0})

        body = (await client.get("/api/paper/positions")).json()
        item = body["data"]["items"][0]
        assert item["code"] == "600519"
        assert item["quantity"] == 100
        assert item["last_price"] == 1680.0
        assert item["market_value"] == 168000.0
        assert item["unrealized_pnl"] == 18000.0

    async def test_orders_limit_is_validated(self, client, auth):
        response = await client.get("/api/paper/orders", params={"limit": 0})
        assert response.status_code == 422


@pytest.mark.contract
class TestOrderValidation:
    async def test_invalid_side_returns_422(self, client, auth):
        response = await client.post(
            "/api/paper/order", json={"code": "600519", "side": "hold", "quantity": 100}
        )
        assert response.status_code == 422

    async def test_non_positive_quantity_returns_422(self, client, auth):
        response = await client.post(
            "/api/paper/order", json={"code": "600519", "side": "buy", "quantity": 0}
        )
        assert response.status_code == 422

    async def test_missing_code_returns_422(self, client, auth):
        response = await client.post(
            "/api/paper/order", json={"side": "buy", "quantity": 100}
        )
        assert response.status_code == 422

    async def test_reset_requires_confirmation(self, client, auth, async_db):
        response = await client.post("/api/paper/reset", params={"confirm": "false"})
        assert response.status_code == 400
        assert "confirm=true" in response.json()["detail"]

    async def test_reset_clears_positions_and_orders(self, client, auth, async_db):
        await async_db["paper_accounts"].insert_one({"user_id": "user-1", "cash": 1.0})
        await async_db["paper_positions"].insert_one({"user_id": "user-1", "code": "600519"})
        await async_db["paper_orders"].insert_one({"user_id": "user-1", "code": "600519"})

        response = await client.post("/api/paper/reset", params={"confirm": "true"})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["cash"]["CNY"] == 1_000_000.0

        assert await async_db["paper_positions"].count_documents({"user_id": "user-1"}) == 0
        assert await async_db["paper_orders"].count_documents({"user_id": "user-1"}) == 0
