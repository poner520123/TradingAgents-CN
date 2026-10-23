# TradingAgents-CN 测试架构

> 本目录为**后端**测试套件。前端测试位于 `frontend/src/__tests__/`。
>
> 原则：**不修改任何业务代码**。所有替身（fake）通过 monkeypatch / 依赖注入注入，
> 被测源码保持原样。

---

## 1. 总体分层

```
┌──────────────────────────────────────────────────────────────────────┐
│  契约层 (contract)   路由路径 / 入参校验 / 响应结构 / 鉴权与权限       │
│  ── tests/unit/routers/          45 个后端路由中覆盖 7 个关键域       │
├──────────────────────────────────────────────────────────────────────┤
│  行为层 (unit)      纯函数 / 状态机 / 策略判定                        │
│  ── tests/unit/core/             统一响应、限流、Redis 封装          │
│  ── tests/unit/services/         JWT 令牌服务                        │
│  ── tests/unit/tradingagents/    市场识别、图路由、信号解析            │
├──────────────────────────────────────────────────────────────────────┤
│  横切层 (middleware)  Trace-ID、速率限制、每日配额                    │
│  ── tests/unit/middleware/                                          │
├──────────────────────────────────────────────────────────────────────┤
│  集成层 (integration) 跨模块流程：提交→轮询→取结果→取消/删除           │
│  ── tests/integration/                                               │
└──────────────────────────────────────────────────────────────────────┘
```

**测试金字塔比例**：unit 71% · contract 24% · integration 5%。

---

## 2. 目录结构

```
tests/
├── conftest.py              # 全局 fixtures（DB/Redis/鉴权/客户端工厂）
├── pytest.ini               # 根目录配置（见仓库根 pytest.ini）
├── fakes/
│   ├── __init__.py
│   ├── async_mongo.py       # motor ↔ mongomock 的异步适配层
│   └── factories.py         # 请求/响应数据构造器
├── unit/
│   ├── core/                # app/core
│   ├── middleware/          # app/middleware
│   ├── routers/             # app/routers  ← 前后端接口契约主战场
│   ├── services/            # app/services
│   └── tradingagents/       # tradingagents（LangGraph 核心库）
└── integration/
    └── test_analysis_flow.py
```

---

## 3. 关键设计决策

### 3.1 外部依赖全部替身化

| 生产依赖 | 测试替身 | 注入方式 |
|---|---|---|
| MongoDB (motor) | `mongomock` + `AsyncDatabaseProxy` | monkeypatch `app.core.database.mongo_db` |
| MongoDB (同步 pymongo) | `mongomock` | 替换 `user_service.users_collection` 等属性 |
| Redis | `fakeredis.aioredis.FakeRedis` | monkeypatch `app.core.database.redis_client` |
| LLM | `FakeLLM` | 直接构造 `SignalProcessor(FakeLLM(...))` |
| 上游 HTTP (策略数据) | `FakeResponse` | monkeypatch `app.routers.strategy.requests.get` |
| 行情服务 | `FakeQuotesService` | monkeypatch `app.routers.quotes.get_quotes_service` |
| 分析引擎 | `FakeAnalysisService` | monkeypatch `app.routers.analysis.get_simple_analysis_service` |

**为什么 patch 模块级全局变量可行**：业务代码统一通过 `get_mongo_db()` / `get_redis_client()`
访问数据库，这两个函数直接读取 `app.core.database` 的模块级变量，因此 patch 全局即可整体生效，
无需修改任何被测源码。

### 3.2 路由测试不挂载全部 45 个路由

`app.main:app` 的 `lifespan` 会启动 APScheduler、爬虫、实时行情入库等后台任务，
测试环境不可接受。因此 `tests/conftest.py::build_test_app` 构建**只含被测路由**的最小应用。

代价是中间件链不在默认覆盖范围内 —— 由 `tests/unit/middleware/` 与
`tests/integration/` 显式验证。

### 3.3 依赖替换必须用 `dependency_overrides`

FastAPI 在**路由定义时**就把 `Depends(get_current_user)` 的函数对象绑定进路由的 dependant，
因此 `monkeypatch.setattr(module, "get_current_user", fake)` **完全无效**。
正确做法：

```python
app.dependency_overrides[get_current_user] = fake_current_user
```

`make_client(router, prefix, dependency_overrides={...})` 已封装该能力。

### 3.4 mongomock → motor 适配层

`tests/fakes/async_mongo.py` 把同步 mongomock 包装成 motor 兼容的 awaitable 形式。
两个易错点已在实现中处理并在测试中固化：

- **游标的 `sort`/`limit`/`skip` 是同步链式方法**（不是协程），否则
  `db.coll.find(...).sort(...).limit(...)` 会拿到 coroutine 对象；
- **`db.collection_name` 属性访问会绕过 `__getitem__`**，必须通过 `__getattr__`
  重新包装，否则 `await db.system_configs.find_one(...)` 会炸。

### 3.5 数据库使用 session 作用域 + 每例清空

部分服务是模块级单例并缓存 `self.db`（如 `favorites_service._get_db()`）。
若每个用例新建数据库，单例会持有上一个用例的库对象造成数据串味。
因此数据库为 **session 级**作用域，隔离由 `clean_database` fixture 在每个用例前清空集合保证。

### 3.6 导入性能垫片（测试环境专用）

`user_service` / `stock_map_service` 在**模块导入阶段**就调用 `collection.create_index()`，
而 `tradingagents.dataflows.data_source_manager` 在导入阶段探测 MongoDB 可用性。
本机无 MongoDB 时，每次导入 `app.routers.*` 要白等 30 秒
（`app/routers/__init__.py` 会导入全部 45 个路由）。

`tests/conftest.py` 通过两项**测试侧垫片**解决（不触碰业务代码）：

1. 环境变量 `MONGO_SERVER_SELECTION_TIMEOUT_MS=200` 等；
2. `pymongo.MongoClient` 代理，**强制覆盖** `serverSelectionTimeoutMS`
   （`get_mongo_db_sync()` 显式传入了 5000ms，`setdefault` 不生效）。

效果：路由测试从 103s → 14s。

---

## 4. 标记与运行

```bash
# 全量
pytest

# 按标记
pytest -m contract          # 接口契约
pytest -m integration       # 集成流程
pytest -m "not slow"        # 排除慢用例

# 指定目录 / 单个用例
pytest tests/unit/routers
pytest tests/unit/routers/test_auth.py::TestLogin::test_successful_login_returns_tokens

# 覆盖率
pytest --cov=app --cov=tradingagents --cov-report=html
```

`pytest.ini` 中 `testpaths = tests` 是必需的 —— 仓库根目录存在约 40 个
一次性调试脚本（`test_api.py` 等），默认收集规则会把它们当成测试收集并失败。

---

## 5. 已知缺陷的记录方式

测试过程中发现了若干**真实缺陷**。处理原则是：

- 主用例锁定**当前实际行为**（保证测试长期为绿）；
- 另加 `@pytest.mark.xfail(strict=True)` 用例标注**目标契约**；
  缺陷修复后该用例会变成 XPASS，`strict=True` 会让它失败，从而提醒同步更新。

> 本轮已修复的缺陷（相关 xfail 已移除，改为正向断言）：
>
> | 位置 | 缺陷 | 修复方式 |
> |---|---|---|
> | `app/middleware/rate_limit.py` | 用户中间件中抛出的 `HTTPException` 绕过 `ExceptionMiddleware`，限流返回 **500** 而非 429 | 中间件内把 `HTTPException` 转成等价 `JSONResponse`（`_http_exception_response`） |
> | `app/middleware/request_id.py` | 500 响应丢失 `X-Trace-ID`（500 由位于所有用户中间件之外的 `ServerErrorMiddleware` 生成） | 抽取 `app/middleware/error_handler.py`，由 500 处理器补齐 Trace-ID 响应头 |
> | `tradingagents/agents/managers/risk_manager.py` | `fundamentals_report` 误取 `state["news_report"]`，基本面报告从未进入记忆检索键 | 改为 `state["fundamentals_report"]`（回归用例 `test_risk_manager.py`） |
> | `tradingagents/dataflows/interface.py` | 缺少 `get_reddit_sentiment`，美股情绪工具恒定降级为「获取失败」 | 新增该函数（含词边界情绪打分与中文标签映射） |

---

## 6. 覆盖范围

### 已覆盖的路由（7 / 45）

| 路由 | 前缀 | 覆盖点 |
|---|---|---|
| `health` | `/api` | 探针响应结构、版本号与 VERSION 文件一致 |
| `auth_db` | `/api/auth` | 登录/刷新/登出/当前用户/管理员专属操作/全部鉴权失败分支 |
| `quotes` | `/api/quotes` | 批量行情、涨跌幅、单只行情、入参校验 |
| `strategy` | `/api/strategy` | 月度策略解析、404 无数据、未知策略、上游异常、缓存命中 |
| `favorites` | `/api/favorites` | 自选股完整 CRUD、标签聚合、鉴权 |
| `paper` | `/api/paper` | 多币种账户、持仓/订单、手续费计算、账户重置、旧结构迁移 |
| `analysis` | `/api/analysis` | 提交→状态→结果→取消/删除全生命周期、状态从 MongoDB 恢复 |

### 已覆盖的核心库

| 模块 | 覆盖点 |
|---|---|
| `tradingagents/graph/conditional_logic.py` | 分析师工具调用防死循环、辩论/风险辩论轮转与终止条件 |
| `tradingagents/graph/signal_processing.py` | JSON 解析、动作归一化、价格提取与推算、货币感知 |
| `tradingagents/utils/stock_utils.py` | A股/港股/美股识别、币种映射、港股代码标准化 |
| `app/core/response.py` | 统一响应信封结构 |
| `app/core/rate_limiter.py` | 滑动窗口限流、Tushare 等级 × 安全边际 |
| `app/core/redis_client.py` | JSON/队列/集合/分布式锁 + Redis 不可用时的降级 |
| `app/core/scheduler_jobs.py` | 声明式定时任务表：注册/暂停/开关语义、任务 id 唯一性、配置项存在性 |
| `app/services/auth_service.py` | JWT 签发、校验、过期、伪造拒绝 |
| `tradingagents/agents/managers/risk_manager.py` | 风险委员会读取四份分析师报告（回归） |
| `tradingagents/dataflows/interface.py` | `get_reddit_sentiment` 情绪打分与降级（回归） |
| `app/middleware/*` | Trace-ID、速率限制、每日配额 |

---

## 7. 扩展指引

新增测试时：

1. **路由契约测试**放 `tests/unit/routers/test_<域>.py`，
   使用 `make_client(router, prefix=...)` 工厂；
2. **鉴权相关**一律用 `dependency_overrides`，不要 monkeypatch 模块属性；
3. **需要数据库**时用 `async_db` / `mongo_db` fixture 预置数据；
4. **外部服务**优先在 `tests/fakes/factories.py` 增加数据构造器，保持用例可读；
5. 断言**响应结构**而非具体实现细节，避免重构即失败；
6. 发现缺陷时按第 5 节的方式记录，不要直接写"符合预期"的错误断言。
