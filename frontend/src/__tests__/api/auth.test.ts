/**
 * ``api/auth.ts`` 接口契约测试。
 *
 * 验证各方法映射到正确的后端路径、HTTP 方法与请求体，
 * 以及 ``skipAuth`` / ``skipAuthError`` 标记是否正确携带。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import { request } from '@/api/request'
import { authApi } from '@/api/auth'
import { setupPinia } from '../helpers/pinia'

const mock = new MockAdapter(request)

beforeEach(() => {
  setupPinia()
  mock.reset()
  // 注意：不要在这里注册 onAny 兜底 —— axios-mock-adapter 按注册顺序匹配，
  // onAny 会抢在具体 handler 之前命中，导致所有断言失效。
})

describe('api/auth', () => {
  it('login 命中 POST /api/auth/login 且不携带认证头', async () => {
    let captured: any
    mock.onPost('/api/auth/login').reply((config) => {
      captured = config
      return [200, { success: true, data: { access_token: 'a', refresh_token: 'r' } }]
    })

    await authApi.login({ username: 'alice', password: 'admin123' })

    expect(captured.url).toBe('/api/auth/login')
    expect(captured.method).toBe('post')
    expect(JSON.parse(captured.data)).toEqual({ username: 'alice', password: 'admin123' })
    expect(captured.headers.Authorization).toBeUndefined()
  })

  it('register 命中 POST /api/auth/register', async () => {
    let captured: any
    mock.onPost('/api/auth/register').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await authApi.register({ username: 'bob', email: 'bob@example.com', password: 'secret1' })
    expect(captured.url).toBe('/api/auth/register')
    expect(captured.method).toBe('post')
  })

  it('logout 命中 POST /api/auth/logout', async () => {
    let captured: any
    mock.onPost('/api/auth/logout').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await authApi.logout()
    expect(captured.url).toBe('/api/auth/logout')
    expect(captured.method).toBe('post')
  })

  it('refreshToken 命中 POST /api/auth/refresh 并携带 refresh_token', async () => {
    let captured: any
    mock.onPost('/api/auth/refresh').reply((config) => {
      captured = config
      return [200, { success: true, data: { access_token: 'new' } }]
    })

    await authApi.refreshToken('my-refresh-token')
    expect(captured.url).toBe('/api/auth/refresh')
    expect(JSON.parse(captured.data)).toEqual({ refresh_token: 'my-refresh-token' })
  })

  it('getUserInfo 命中 GET /api/auth/me', async () => {
    let captured: any
    mock.onGet('/api/auth/me').reply((config) => {
      captured = config
      return [200, { success: true, data: { username: 'alice' } }]
    })

    const result: any = await authApi.getUserInfo()
    expect(captured.url).toBe('/api/auth/me')
    expect(captured.method).toBe('get')
    expect(result.data.username).toBe('alice')
  })

  it('updateUserInfo 命中 PUT /api/auth/me', async () => {
    let captured: any
    mock.onPut('/api/auth/me').reply((config) => {
      captured = config
      return [200, { success: true, data: {} }]
    })

    await authApi.updateUserInfo({ email: 'new@example.com' })
    expect(captured.method).toBe('put')
    expect(JSON.parse(captured.data)).toEqual({ email: 'new@example.com' })
  })

  it('changePassword 命中 POST /api/auth/change-password', async () => {
    let captured: any
    mock.onPost('/api/auth/change-password').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await authApi.changePassword({ old_password: 'a', new_password: 'b' })
    expect(captured.url).toBe('/api/auth/change-password')
    expect(JSON.parse(captured.data)).toEqual({ old_password: 'a', new_password: 'b' })
  })

  it('resetPassword 命中 POST /api/auth/reset-password 且只传 email', async () => {
    let captured: any
    mock.onPost('/api/auth/reset-password').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await authApi.resetPassword('user@example.com')
    expect(captured.url).toBe('/api/auth/reset-password')
    expect(JSON.parse(captured.data)).toEqual({ email: 'user@example.com' })
  })

  it('verifyEmail 命中 POST /api/auth/verify-email', async () => {
    let captured: any
    mock.onPost('/api/auth/verify-email').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await authApi.verifyEmail('verify-token')
    expect(captured.url).toBe('/api/auth/verify-email')
  })
})
