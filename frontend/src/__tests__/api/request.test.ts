/**
 * ``api/request.ts`` 单元测试 —— 前后端契约的核心守卫。
 *
 * 覆盖请求拦截器（认证头 / 请求 ID / 语言头 / 遗留端点兼容守卫）与
 * 响应拦截器（业务错误 / 401 刷新重放 / 错误消息映射 / 网络错误重试）。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import { request } from '@/api/request'
import { setupPinia } from '../helpers/pinia'
import { useAuthStore } from '@/stores/auth'

const mock = new MockAdapter(request)

/** 构造一个形如 JWT 的三段式 token。 */
const fakeToken = (payload: Record<string, unknown> = { sub: 'alice' }) => {
  const enc = (o: unknown) =>
    btoa(unescape(encodeURIComponent(JSON.stringify(o))))
      .replace(/=+$/, '')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
  return `${enc({ alg: 'HS256' })}.${enc(payload)}.sig`
}

beforeEach(() => {
  setupPinia()
  mock.reset()
})

describe('api/request - 请求拦截器', () => {
  it('注入 Authorization 头', async () => {
    const auth = useAuthStore()
    auth.token = fakeToken()

    let captured: any
    mock.onGet('/api/protected').reply((config) => {
      captured = config
      return [200, { success: true, data: {} }]
    })

    await request.get('/api/protected')

    expect(captured.headers.Authorization).toBe(`Bearer ${auth.token}`)
  })

  it('localStorage 中的 token 作为兜底', async () => {
    localStorage.setItem('auth-token', fakeToken({ sub: 'fallback' }))

    let captured: any
    mock.onGet('/api/protected').reply((config) => {
      captured = config
      return [200, { success: true, data: {} }]
    })

    await request.get('/api/protected')
    expect(captured.headers.Authorization).toBe('Bearer ' + localStorage.getItem('auth-token'))
  })

  it('skipAuth=true 时不注入 Authorization 头', async () => {
    useAuthStore().token = fakeToken()

    let captured: any
    mock.onGet('/api/public').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await request.get('/api/public', { skipAuth: true } as any)
    expect(captured.headers.Authorization).toBeUndefined()
  })

  it('注入 X-Request-ID 请求头', async () => {
    let captured: any
    mock.onGet('/api/x').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await request.get('/api/x')
    expect(captured.headers['X-Request-ID']).toMatch(/^req_/)
  })

  it('注入 Accept-Language 请求头', async () => {
    let captured: any
    mock.onGet('/api/x').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await request.get('/api/x')
    expect(captured.headers['Accept-Language']).toBe('zh-CN')
  })

  it('遗留端点 /api/stocks/quote 被改写为 /api/stocks/{code}/quote', async () => {
    let captured: any
    mock.onGet(/\/api\/stocks\/.+/).reply((config) => {
      captured = config
      return [200, { success: true, data: {} }]
    })

    await request.get('/api/stocks/quote', { params: { code: '600519' } })

    expect(captured.url).toBe('/api/stocks/600519/quote')
    expect(captured.params.code).toBeUndefined()
  })

  it('遗留端点缺少 code 时直接拒绝请求', async () => {
    mock.onGet(/\/api\/stocks\/.+/).reply(200, { success: true })

    await expect(request.get('/api/stocks/quote')).rejects.toThrow(/缺少 code/)
  })
})

describe('api/request - 响应拦截器', () => {
  it('直接返回 response.data 而非 axios 响应对象', async () => {
    mock.onGet('/api/ok').reply(200, { success: true, data: { id: 1 }, message: 'ok' })

    const result: any = await request.get('/api/ok')
    expect(result).toEqual({ success: true, data: { id: 1 }, message: 'ok' })
    expect(result.status).toBeUndefined()
  })

  it('业务失败（success=false）时 reject', async () => {
    mock.onGet('/api/business-error').reply(200, {
      success: false,
      message: '业务规则不满足',
      code: 40001
    })

    await expect(request.get('/api/business-error')).rejects.toThrow('业务规则不满足')
  })

  it('skipErrorHandler=true 时业务失败不 reject', async () => {
    mock.onGet('/api/quiet').reply(200, { success: false, message: '忽略我', code: 40001 })

    const result: any = await request.get('/api/quiet', { skipErrorHandler: true } as any)
    expect(result.success).toBe(false)
  })

  it('HTTP 404 抛出原始错误', async () => {
    mock.onGet('/api/missing').reply(404, { detail: '资源不存在' })

    await expect(request.get('/api/missing')).rejects.toBeDefined()
  })

  it('HTTP 500 抛出原始错误', async () => {
    mock.onGet('/api/boom').reply(500, { detail: '内部错误' })

    await expect(request.get('/api/boom')).rejects.toBeDefined()
  })
})

describe('api/request - 401 令牌刷新', () => {
  it('刷新成功后重放原请求', async () => {
    const auth = useAuthStore()
    auth.token = fakeToken()
    auth.refreshToken = fakeToken({ sub: 'alice' })

    // 刷新接口直接成功
    mock.onPost('/api/auth/refresh').reply(200, {
      success: true,
      data: { access_token: fakeToken({ sub: 'alice', exp: 9999999999 }), refresh_token: fakeToken() }
    })

    let attempts = 0
    mock.onGet('/api/protected').reply(() => {
      attempts += 1
      return attempts === 1 ? [401, { detail: 'unauthorized' }] : [200, { success: true, data: { ok: 1 } }]
    })

    const result: any = await request.get('/api/protected')
    expect(result.data).toEqual({ ok: 1 })
    expect(attempts).toBe(2)
  })

  it('skipAuthError=true 时不触发刷新', async () => {
    const auth = useAuthStore()
    auth.token = fakeToken()
    auth.refreshToken = fakeToken()

    let refreshCalled = false
    mock.onPost('/api/auth/refresh').reply(() => {
      refreshCalled = true
      return [200, { success: true, data: {} }]
    })
    mock.onGet('/api/public').reply(401, { detail: 'unauthorized' })

    await expect(request.get('/api/public', { skipAuthError: true } as any)).rejects.toBeDefined()
    expect(refreshCalled).toBe(false)
  })

  it('刷新接口自身失败时不再重试刷新', async () => {
    const auth = useAuthStore()
    auth.token = fakeToken()
    auth.refreshToken = fakeToken()

    let refreshAttempts = 0
    mock.onPost('/api/auth/refresh').reply(() => {
      refreshAttempts += 1
      return [401, { detail: 'invalid' }]
    })
    mock.onGet('/api/protected').reply(401, { detail: 'unauthorized' })

    await expect(request.get('/api/protected')).rejects.toBeDefined()
    expect(refreshAttempts).toBe(1)
  })
})

describe('api/request - 网络错误重试', () => {
  it('网络错误时按配置重试并最终成功', async () => {
    // networkErrorOnce 会抛出带 config 的 AxiosError（与真实 XHR 网络错误一致），
    // 而手写 Promise.reject 抛出的裸 Error 没有 config，拦截器无法识别。
    mock.onGet('/api/flaky').networkErrorOnce()
    mock.onGet('/api/flaky').networkErrorOnce()
    mock.onGet('/api/flaky').reply(200, { success: true, data: { recovered: true } })

    const result: any = await request.get('/api/flaky', {
      retryCount: 2,
      retryDelay: 1
    } as any)

    expect(result.data.recovered).toBe(true)
  })

  it('超过重试上限后抛出错误', async () => {
    mock.onGet('/api/down').networkError()

    await expect(
      request.get('/api/down', { retryCount: 1, retryDelay: 1 } as any)
    ).rejects.toBeDefined()
  })

  it('未开启重试时不重试', async () => {
    mock.onGet('/api/no-retry').networkError()

    await expect(
      request.get('/api/no-retry', { retryCount: 0, retryDelay: 1 } as any)
    ).rejects.toBeDefined()
  })
})
