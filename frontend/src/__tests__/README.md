# TradingAgents-CN 前端测试架构

> 测试代码位于 `frontend/src/__tests__/`。
>
> 原则：**不修改任何业务代码**。外部依赖通过 mock / 替身注入。

---

## 1. 目录结构

```
frontend/
├── vitest.config.ts           # 独立配置（不复用 vite.config.ts）
├── src/__tests__/
│   ├── setup.ts               # 全局 setup：浏览器 API 补齐、存储清理、日志静音
│   ├── helpers/
│   │   └── pinia.ts           # createPinia + setActivePinia
│   ├── utils/                 # 纯函数层
│   │   ├── market.test.ts
│   │   ├── stock.test.ts
│   │   ├── stockValidator.test.ts
│   │   ├── datetime.test.ts
│   │   └── auth.test.ts
│   ├── api/                   # 接口契约层
│   │   ├── request.test.ts    # axios 拦截器（认证/刷新/重试/端点守卫）
│   │   ├── auth.test.ts
│   │   ├── analysis.test.ts
│   │   └── strategy.test.ts
│   ├── stores/                # 状态层
│   │   ├── auth.test.ts
│   │   ├── app.test.ts
│   │   └── notifications.test.ts
│   └── router/
│       └── guards.test.ts     # 路由守卫与路由表结构
```

---

## 2. 为什么单独建 `vitest.config.ts`

| 原因 | 说明 |
|---|---|
| 性能 | `vite.config.ts` 的 `ViteImageOptimizer` 会真的处理图片资源，测试环境无意义且很慢 |
| 隔离 | 测试需要独立的 `happy-dom` 环境、setup 文件、覆盖率配置 |
| 保留必要能力 | `unplugin-auto-import` + `ElementPlusResolver` **必须保留** —— 业务代码（如 `stores/auth.ts`）依赖自动注入的 `ElMessage` 等 Element Plus 符号 |

所有插件的 `dts` 均设为 `false`，避免测试运行污染仓库中的自动生成声明文件。

---

## 3. 关键技巧

### 3.1 `axios-mock-adapter` 的注册顺序陷阱

axios-mock-adapter **按注册顺序**匹配 handler。先注册 `onAny()` 会抢在所有
具体 handler 之前命中，导致断言全部失效。

```ts
beforeEach(() => {
  mock.reset()
  // ❌ 不要在这里注册 onAny 兜底
  // mock.onAny().reply(200, { success: true })
})
```

### 3.2 模拟网络错误要用 `networkErrorOnce()`

手写 `Promise.reject(new Error('Network Error'))` 抛出的是**裸 Error**，
没有 `.config` 属性；而 `request.ts` 的 `shouldRetry(config, error)` 会在
`!config` 时直接返回 false，导致重试逻辑不触发。

```ts
mock.onGet('/api/flaky').networkErrorOnce()   // ✅ 携带 config
```

### 3.3 `vi.mock` 工厂必须用 `vi.hoisted()`

`vi.mock` 会被提升到文件顶部，工厂内不能引用普通顶层变量：

```ts
const { authApiMock } = vi.hoisted(() => ({ authApiMock: { login: vi.fn() } }))
vi.mock('@/api/auth', () => ({ authApi: authApiMock }))
```

### 3.4 element-plus 的 CSS 导入

element-plus 的 ESM 产物会 `import .css`，Node 加载器无法直接处理。
需在 vitest 配置中内联该依赖：

```ts
server: { deps: { inline: ['element-plus'] } }
```

### 3.5 路由单例的重复导航陷阱

`router` 是模块级单例。若上一个用例停留在 `/login`，再次 `push('/login')`
会被 vue-router 判定为重复导航而直接中止，守卫不会执行。
因此 `beforeEach` 先导航到一个公开页面复位。

---

## 4. 运行

```bash
cd frontend

npm test                # 单次运行
npm run test:watch      # 监听模式
npm run test:coverage   # 覆盖率报告
npx vitest run src/__tests__/api        # 只跑某个目录
npx vitest run -t "401 令牌刷新"         # 按用例名过滤
```

---

## 5. 覆盖范围

| 层 | 覆盖内容 |
|---|---|
| **utils** | 市场归一化、股票代码校验与字段兼容、日期时间格式化（时区/多格式容错）、JWT 工具 |
| **api** | 请求拦截器（Authorization / X-Request-ID / Accept-Language / 遗留端点守卫）、响应拦截器（业务错误 / 401 刷新重放 / 网络错误重试）、各 API 模块的**路径与方法映射** |
| **stores** | auth（初始化/登录/登出/刷新/重定向/权限）、app（主题/语言/侧边栏/偏好/连通性）、notifications（列表/未读/已读/WebSocket 消息与重连） |
| **router** | 路由表结构、认证守卫、页面标题、当前路由同步 |

`api/*` 层的测试是**前后端契约的主要守卫** —— 它们断言的是「前端方法 → 后端路由」
的映射，与后端 `tests/unit/routers/` 的响应结构测试互为镜像。

---

## 6. 已知缺陷的记录方式

与后端一致：主用例锁定**当前实际行为**，另加 `it.fails` 标注**目标契约**。

> 本轮已修复的缺陷（相关断言已改为正向断言）：
>
> | 位置 | 缺陷 | 修复方式 |
> |---|---|---|
> | `utils/datetime.ts` | `formatDate` / `formatTime` 因 `{...defaultOptions, ...options}` 的合并顺序，实际仍输出完整日期时间 | 抽取 `formatWithOptions` 核心函数，`formatDate`/`formatTime` 使用**独占**的选项集合（不再与默认合并） |
> | `stores/auth.ts` | `redirectPath` 初始值 `'/'` 为真值，使 `\|\| '/strategy'` 兜底失效，登录后跳回根路径 | 初始值改为 `'/strategy'` |
> | `views/Tasks/TaskCenter.vue` | 任务进度 WebSocket 路径写成 `/api/ws/task/{id}`（后端为 `/ws/tasks/{id}`），且 token 读错存储键、未拼接到 URL | 修正路径为 `/api/ws/tasks/{id}`，token 取自 `authStore` / `auth-token` 并以 query 参数传递 |
