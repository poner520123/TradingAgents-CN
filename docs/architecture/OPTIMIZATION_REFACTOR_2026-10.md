# 架构与结构优化记录（2026-10）

本文记录一次**不改变任何对外功能接口**的精简 / 架构 / 代码结构优化。

约束：HTTP 路由、请求/响应结构、鉴权语义、WebSocket 协议均保持不变；
前端组件的 props / emits 与 API 模块的导出符号保持向后兼容。

---

## 1. 启动性能：消除「模块导入阶段的数据库 I/O」

### 问题

架构审查发现 **7 个模块在 `import` 阶段就执行数据库 I/O**：

| 模块 | 导入期行为 | MongoDB 不可达时的阻塞 |
|---|---|---|
| `app/services/user_service.py` | `create_index` | **30.9s** |
| `app/services/stock_map_service.py` | 连接 + `create_index` + 缓存重建 + 完整性校验 | **30.6s** |
| `app/services/simple_analysis_service.py` | 构造 `DataSourceManager`（触发 DB 探测 + 缓存初始化） | **29.8s** |
| `app/core/crawler_fund.py` | `create_index` | 5s |
| `app/core/crawler_popularity.py` | `create_index` | 5s |
| `app/services/crawler_service.py` | `create_index` | 5s |
| `app/services/scrapy_crawler_service.py` | `create_index` × 3 集合 | 5s |
| `app/services/advanced_stock_selector_service.py` | `create_index` | 5s |
| `app/services/stock_selector_service.py` | `create_index` | 5s |
| `app/services/st_filter_service.py` | 加载 ST 股票列表 | 5s |

由于 `app/routers/__init__.py` 会一次性导入全部 45 个路由，
而 `app.routers.analysis` 又会连带导入 `simple_analysis_service`，
**"导入任意一个路由" 都要等 30 秒以上**。`import app.main` 实测 **133 秒**。

### 解决

统一改为「**首次使用时惰性初始化**」：

* 初始化方法加幂等守卫（`_db_initialized` / `_initialized` 标志），只执行一次；
* 初始化调用注入到**确实访问数据库/内存缓存**的公开方法入口；
* `stock_map_service` 额外用 `_initializing` 标志防止初始化过程内的递归调用。

### 效果

| 指标 | 优化前 | 优化后 |
|---|---|---|
| `import app.main`（MongoDB 不可达） | **133s** | **8.4s** |
| `import app.routers`（包本身） | ~50s | **0.009s** |
| `import app.services.user_service` | 30.9s | 0.05s |
| `import app.services.stock_map_service` | 30.6s | 0.51s |
| 后端测试套件耗时 | 21.3s | 15.9s |

> 数据库**可用**时这些操作为毫秒级，优化主要收益体现在"数据库不可达/网络异常"
> 的启动路径 —— 那正是容器编排中探针未就绪、依赖服务重启时的常见场景。

---

## 2. 架构：路由包改为惰性导入

`app/routers/__init__.py` 原本一次性 `from app.routers import (45 个模块)`。
现改为 **PEP 562 模块级 `__getattr__`** 惰性加载：

* `from app.routers import analysis` 等用法**完全不变**；
* 兼容别名 `auth` → `auth_db` 保留；
* 只有真正被访问的路由才会被导入。

---

## 3. 架构：`app/main.py` 拆分

`app/main.py` 曾达 **1023 行**，其中约 430 行是 lifespan 内联的定时任务注册，
且三个数据源的任务注册是近乎逐字复制的样板代码。

### 拆分结果

| 文件 | 职责 | 行数 |
|---|---|---|
| `app/main.py` | 应用装配、路由注册、中间件、生命周期骨架 | **1023 → 526** |
| `app/core/startup/scheduler_jobs.py` | 声明式定时任务表 | 新增 412 |

### 声明式任务表

原先每个任务要写 15 行（`add_job` + 条件 `pause_job` + 两分支日志），
现在只需在任务表里加一条记录：

```python
CronJobSpec(
    job_id="tushare_basic_info_sync",
    name="股票基础信息同步（Tushare）",
    cron_attr="TUSHARE_BASIC_INFO_SYNC_CRON",
    func=run_tushare_basic_info_sync,
    enabled_attr="TUSHARE_BASIC_INFO_SYNC_ENABLED",
    unified_attr="TUSHARE_UNIFIED_ENABLED",
    kwargs={"force_update": False},
    log_prefix="Tushare基础信息同步",
)
```

`register_cron_job()` 是唯一的注册入口，统一处理「注册 → 未启用则暂停 → 日志」，
**行为与原实现逐项一致**（14 个数据源任务 + 新闻 + 基础信息同步 + 行情入库 + 爬虫 + 筛选）。

同时清除了 `app/main.py` 中 3 处重复的路由 import。

---

## 4. 代码结构：类型单一真源

前端存在**同名但结构已分叉**的类型双份定义：

| 重复类型 | 分叉点 |
|---|---|
| `LLMProvider` | `api/config.ts` 无 `api_key`，`types/config.ts` 有；`extra_config` 形状不同 |
| `LLMConfig` / `DataSourceConfig` / `DatabaseConfig` / `SystemConfig` / `ConfigTestRequest` / `ConfigTestResponse` | 字段集不一致 |
| `AnalysisResult` | `api/analysis.ts` 含 `current_price` / `technical_analysis` 等实际返回字段，`types/analysis.ts` 缺失 |
| `SingleAnalysisRequest` | `parameters` 字段集不同 |

### 解决

以 **`src/api/*`（真正描述接口载荷的模块）为唯一真源**，
`src/types/*` 改为 `import type` + `export type` 的**类型级再导出**：

* `export type` 在编译期被完全擦除 → **零运行时依赖**；
* `from '@/types/config'` 与 `from '@/api/config'` 两条导入路径继续可用；
* 两侧类型从此永远一致。

---

## 5. 死代码清理

| 类型 | 内容 |
|---|---|
| 前端空壳 | `components/Dev/DevPanel.vue`、`components/Global/GlobalConfirm.vue`（各 13 行占位） |
| 前端残留 | `views/Analysis/SingleAnalysis.vue.temp`（1 行）、`src/test-import.js` |
| 前端过时测试 | `src/utils/__tests__/market.test.ts`（断言已废弃的港股/美股识别行为） |
| 后端注释死码 | `app/routers/analysis.py` 两段已废弃的注释路由 |
| 后端重复定义 | `tradingagents/dataflows/data_source_manager.py` 中**重复两次**的 `get_data_source_manager()`（后者覆盖前者） |
| 仓库根目录 | **43 个**一次性运维脚本 → 归置到 `scripts/maintenance/`（附 README 说明分类与用法） |
| 已提交日志 | `error.log`(4.2MB)、`error.log.1`(10MB)、`docker-up.log` 等运行时产物移出版本控制并补 `.gitignore` |

根目录现在只剩 `main.py`（`pyproject.toml` 中 `tradingagents = "main:main"` 的入口）。

---

## 6. 顺带修复的真实缺陷

在核对接口契约时发现并修复（详见 `tests/README.md` 第 5 节）：

* `app/middleware/rate_limit.py` —— 中间件内抛 `HTTPException` 绕过 `ExceptionMiddleware`，限流返回 **500 而非 429**；
* `app/middleware/error_handler.py` —— 500 响应丢失 `X-Trace-ID`；
* `tradingagents/agents/managers/risk_manager.py` —— 风险委员会误取新闻报告、基本面报告从未进入记忆检索键；
* `tradingagents/dataflows/interface.py` —— 缺少 `get_reddit_sentiment`，美股情绪工具恒定降级；
* `frontend/src/utils/datetime.ts` —— `formatDate`/`formatTime` 未剥离时间/日期部分；
* `frontend/src/stores/auth.ts` —— `redirectPath` 初值使默认首页兜底失效；
* `frontend/src/views/Tasks/TaskCenter.vue` —— 任务进度 WebSocket 路径与 token 传递均错；
* `frontend/src/views/Reports/ReportDetail.vue` —— 按信封结构访问**扁平**的 `SystemConfigResponse`，LLM 配置列表恒为空。

---

## 7. 已知遗留（本次未处理）

### 7.1 前端 290 个 TypeScript 错误

`npm run type-check`（vue-tsc）当前有 **290 个错误**，属**既有债务**（本次优化前后数量一致，未新增）。

根因集中在 `src/api/request.ts` 的 `ApiClient` 静态方法：其声明返回
`Promise<ApiResponse<T>>`（信封），而各 API 模块的函数又声明成 `Promise<T>`（内部类型），
两者不一致，错误由此级联到各 view。

推荐修复路径（**不改运行时**）：

1. 逐个把 `src/api/*` 的返回标注改为 `Promise<ApiResponse<T>>`；
2. 相应调整调用方（`response.data.xxx`）；
3. 期间可暴露真实运行时 bug —— 本次已用该方式定位到 `ReportDetail.vue` 的缺陷。

### 7.2 导入期副作用的更深治理

本轮已消除**显式**的导入期 DB I/O，但 `tradingagents/dataflows/data_source_manager.py` 的
`DataSourceManager.__init__` 内部仍会在**首次使用时**做多轮数据源探测与缓存初始化。
若要进一步降低首请求延迟，可把探测结果改为带 TTL 的缓存。

### 7.3 `docs/` 目录冗余

`docs/` 下 500+ 文件中存在明显的目录级重复
（`fixes/` 73 个、`bugfix/` 10 个、`changes/` 5 个、`summary/` 8 个、`archive/` 5 个、
`blog/` 23 个、`releases/` 23 个），建议按「架构 / 指南 / 变更日志」三类归并。

---

## 8. 验证

```bash
pytest                         # 后端 317 passed
cd frontend && npm test        # 前端 253 passed
cd frontend && npm run build   # 构建通过（27.3s）
python -c "import app.main"    # 8.4s，314 个路由
```
