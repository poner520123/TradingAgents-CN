/**
 * ``stores/auth.ts`` 单元测试。
 *
 * 覆盖认证态初始化（含无效 token 清理）、登录/登出、令牌刷新与重定向路径。
 * ``@/api/auth`` 与 ``@/utils/auth`` 均被 mock，避免真实网络请求。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setupPinia } from '../helpers/pinia'

// vi.mock 会被提升到文件顶部，工厂内不能引用普通顶层变量，
// 必须通过 vi.hoisted() 创建并导出。
const { authApiMock, setupTokenRefreshTimerMock } = vi.hoisted(() => ({
  authApiMock: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    getUserInfo: vi.fn(),
    updateUserInfo: vi.fn(),
    changePassword: vi.fn()
  },
  setupTokenRefreshTimerMock: vi.fn()
}))

vi.mock('@/api/auth', () => ({
  authApi: authApiMock
}))

vi.mock('@/utils/auth', () => ({
  setupTokenRefreshTimer: () => setupTokenRefreshTimerMock(),
  isTokenExpiringSoon: () => false,
  getTokenRemainingTime: () => 3600
}))

import { useAuthStore } from '@/stores/auth'

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
  Object.values(authApiMock).forEach((fn) => fn.mockReset())
  setupTokenRefreshTimerMock.mockReset()
})

describe('stores/auth', () => {
  describe('初始化', () => {
    it('无本地 token 时处于未认证状态', () => {
      const auth = useAuthStore()
      expect(auth.isAuthenticated).toBe(false)
      expect(auth.token).toBeNull()
    })

    it('合法的本地 token 会恢复认证态', () => {
      localStorage.setItem('auth-token', fakeToken())
      localStorage.setItem('refresh-token', fakeToken())
      const auth = useAuthStore()
      expect(auth.isAuthenticated).toBe(true)
      expect(auth.token).not.toBeNull()
    })

    it('mock token 被清除', () => {
      localStorage.setItem('auth-token', 'mock-token')
      localStorage.setItem('refresh-token', 'mock-token')
      const auth = useAuthStore()
      expect(auth.isAuthenticated).toBe(false)
      expect(localStorage.getItem('auth-token')).toBeNull()
    })

    it('结构非法的 token 被清除', () => {
      localStorage.setItem('auth-token', 'not-a-jwt')
      const auth = useAuthStore()
      expect(auth.isAuthenticated).toBe(false)
      expect(localStorage.getItem('auth-token')).toBeNull()
    })
  })

  describe('setAuthInfo / clearAuthInfo', () => {
    it('setAuthInfo 写入状态与 localStorage', () => {
      const auth = useAuthStore()
      const token = fakeToken()
      auth.setAuthInfo(token, fakeToken(), { username: 'alice' } as any)

      expect(auth.isAuthenticated).toBe(true)
      expect(auth.token).toBe(token)
      expect(localStorage.getItem('auth-token')).toBe(token)
      expect(JSON.parse(localStorage.getItem('user-info')!).username).toBe('alice')
    })

    it('clearAuthInfo 清空状态与 localStorage', () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken(), fakeToken(), { username: 'alice' } as any)

      auth.clearAuthInfo()

      expect(auth.isAuthenticated).toBe(false)
      expect(auth.token).toBeNull()
      expect(auth.refreshToken).toBeNull()
      expect(auth.user).toBeNull()
      expect(localStorage.getItem('auth-token')).toBeNull()
      expect(localStorage.getItem('refresh-token')).toBeNull()
      expect(localStorage.getItem('user-info')).toBeNull()
    })
  })

  describe('login', () => {
    it('登录成功时设置认证信息并授予 admin 角色', async () => {
      authApiMock.login.mockResolvedValue({
        success: true,
        data: {
          access_token: fakeToken(),
          refresh_token: fakeToken(),
          user: { username: 'alice' }
        }
      })

      const auth = useAuthStore()
      const ok = await auth.login({ username: 'alice', password: 'admin123' })

      expect(ok).toBe(true)
      expect(auth.isAuthenticated).toBe(true)
      expect(auth.roles).toEqual(['admin'])
      expect(auth.permissions).toEqual(['*'])
      expect(auth.isAdmin).toBe(true)
      expect(setupTokenRefreshTimerMock).toHaveBeenCalled()
    })

    it('业务失败时返回 false 且不设置认证信息', async () => {
      authApiMock.login.mockResolvedValue({ success: false, message: '用户名或密码错误' })

      const auth = useAuthStore()
      const ok = await auth.login({ username: 'alice', password: 'bad' })

      expect(ok).toBe(false)
      expect(auth.isAuthenticated).toBe(false)
    })

    it('接口异常时返回 false 而不抛出', async () => {
      authApiMock.login.mockRejectedValue(new Error('network down'))

      const auth = useAuthStore()
      await expect(auth.login({ username: 'a', password: 'b' })).resolves.toBe(false)
    })

    it('并发调用时只发起一次请求', async () => {
      let resolveLogin: (v: any) => void = () => {}
      authApiMock.login.mockReturnValue(
        new Promise((resolve) => {
          resolveLogin = resolve
        })
      )

      const auth = useAuthStore()
      const first = auth.login({ username: 'a', password: 'b' })
      const second = auth.login({ username: 'a', password: 'b' })

      expect(authApiMock.login).toHaveBeenCalledTimes(1)

      resolveLogin({ success: false })
      await Promise.all([first, second])
    })

    it('结束后复位 loginLoading', async () => {
      authApiMock.login.mockResolvedValue({ success: false })

      const auth = useAuthStore()
      await auth.login({ username: 'a', password: 'b' })

      expect(auth.loginLoading).toBe(false)
    })
  })

  describe('logout', () => {
    it('登出后清除认证信息', async () => {
      authApiMock.logout.mockResolvedValue({ success: true })

      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken(), fakeToken())
      await auth.logout()

      expect(auth.isAuthenticated).toBe(false)
      expect(localStorage.getItem('auth-token')).toBeNull()
    })

    it('登出接口失败时仍清除本地认证信息', async () => {
      authApiMock.logout.mockRejectedValue(new Error('offline'))

      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken(), fakeToken())
      await auth.logout()

      expect(auth.isAuthenticated).toBe(false)
    })
  })

  describe('refreshAccessToken', () => {
    it('刷新成功时更新 token', async () => {
      const newToken = fakeToken({ sub: 'alice' })
      authApiMock.refreshToken.mockResolvedValue({
        success: true,
        data: { access_token: newToken, refresh_token: fakeToken() }
      })

      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken(), fakeToken())

      const ok = await auth.refreshAccessToken()

      expect(ok).toBe(true)
      expect(auth.token).toBe(newToken)
    })

    it('没有 refresh token 时返回 false', async () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken())
      await expect(auth.refreshAccessToken()).resolves.toBe(false)
    })

    it('refresh token 格式非法时返回 false', async () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken(), 'invalid')
      await expect(auth.refreshAccessToken()).resolves.toBe(false)
    })

    it('服务端错误时保留认证信息', async () => {
      authApiMock.refreshToken.mockRejectedValue({
        response: { status: 500 }
      })

      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken(), fakeToken())

      await expect(auth.refreshAccessToken()).resolves.toBe(false)
      expect(auth.token).not.toBeNull()
    })

    it('401 错误时清除认证信息', async () => {
      authApiMock.refreshToken.mockRejectedValue({
        response: { status: 401 }
      })

      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken(), fakeToken())

      await expect(auth.refreshAccessToken()).resolves.toBe(false)
      expect(auth.isAuthenticated).toBe(false)
    })
  })

  describe('重定向路径', () => {
    it('默认重定向到 /strategy（默认首页）', () => {
      const auth = useAuthStore()
      expect(auth.getAndClearRedirectPath()).toBe('/strategy')
    })

    it('清空后再次调用仍返回 /strategy', () => {
      const auth = useAuthStore()
      auth.getAndClearRedirectPath()
      expect(auth.getAndClearRedirectPath()).toBe('/strategy')
    })

    it('保存的重定向路径被返回并清空', () => {
      const auth = useAuthStore()
      auth.setRedirectPath('/reports/view/1')

      expect(auth.getAndClearRedirectPath()).toBe('/reports/view/1')
      expect(auth.getAndClearRedirectPath()).toBe('/strategy')
    })

    it('setRedirectPath 写入状态', () => {
      const auth = useAuthStore()
      auth.setRedirectPath('/favorites')
      expect(auth.redirectPath).toBe('/favorites')
    })
  })

  describe('权限', () => {
    it('admin 拥有所有权限', async () => {
      const auth = useAuthStore()
      await auth.fetchUserPermissions()
      expect(auth.hasPermission('any:permission')).toBe(true)
    })

    it('hasRole 依据角色数组判断', () => {
      const auth = useAuthStore()
      auth.roles = ['user']
      expect(auth.hasRole('user')).toBe(true)
      expect(auth.hasRole('admin')).toBe(false)
    })
  })

  describe('用户信息', () => {
    it('fetchUserInfo 成功后写入用户', async () => {
      authApiMock.getUserInfo.mockResolvedValue({
        success: true,
        data: { username: 'alice', total_analyses: 5 }
      })

      const auth = useAuthStore()
      const ok = await auth.fetchUserInfo()

      expect(ok).toBe(true)
      expect(auth.user?.username).toBe('alice')
    })

    it('fetchUserInfo 失败时抛出异常交由上层处理', async () => {
      authApiMock.getUserInfo.mockResolvedValue({ success: false, message: '未登录' })

      const auth = useAuthStore()
      await expect(auth.fetchUserInfo()).rejects.toThrow('未登录')
    })
  })

  describe('userStats', () => {
    it('缺省时使用默认配额与并发数', () => {
      const auth = useAuthStore()
      const stats = auth.userStats
      expect(stats.dailyQuota).toBe(1000)
      expect(stats.concurrentLimit).toBe(3)
      expect(stats.totalAnalyses).toBe(0)
    })
  })
})
