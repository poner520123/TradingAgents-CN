/**
 * 路由守卫测试。
 *
 * 验证 ``router.beforeEach`` 的三条关键规则：
 * 1. 需要认证的页面在未登录时跳转 /login 并记录原始路径；
 * 2. 已登录用户访问 /login 时跳转默认首页 /strategy；
 * 3. 正常导航时设置页面标题并同步当前路由到 appStore。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setupPinia } from '../helpers/pinia'

// 视图组件全部 mock 掉：路由表使用动态 import，测试不需要真实组件
vi.mock('@/views/Dashboard/index.vue', () => ({ default: {} }))
vi.mock('@/views/Auth/Login.vue', () => ({ default: {} }))

import router, { routes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const fakeToken = 'header.eyJzdWIiOiJhbGljZSJ9.sig'

beforeEach(async () => {
  setupPinia()
  // router 是模块级单例，若上一个用例停留在 /login，再次 push('/login') 会被
  // vue-router 判定为重复导航而直接中止，守卫不会执行。
  // 因此先导航到一个公开页面以复位当前位置。
  await router.push('/about').catch(() => {})
})

describe('router/guards', () => {
  describe('路由表结构', () => {
    it('根路径重定向到 /strategy', () => {
      const root = routes.find((r) => r.path === '/')
      expect(root?.redirect).toBe('/strategy')
    })

    it('/queue 重定向到 /tasks', () => {
      const queue = routes.find((r) => r.path === '/queue')
      expect(queue?.redirect).toBe('/tasks')
    })

    it('受保护页面声明了 requiresAuth', () => {
      const protectedRoutes = routes.filter((r) => r.meta?.requiresAuth)
      expect(protectedRoutes.length).toBeGreaterThan(0)
      for (const route of protectedRoutes) {
        expect(route.meta?.requiresAuth).toBe(true)
      }
    })

    it('学习中心与关于页无需认证', () => {
      const learning = routes.find((r) => r.path === '/learning')
      expect(learning?.meta?.requiresAuth).toBe(false)

      const about = routes.find((r) => r.path === '/about')
      expect(about?.meta?.requiresAuth).toBe(false)
    })

    it('登录页不出现在侧边栏', () => {
      const login = routes.find((r) => r.path === '/login')
      expect(login?.meta?.hideInMenu).toBe(true)
    })
  })

  describe('认证守卫', () => {
    it('未登录访问受保护页面时跳转 /login', async () => {
      const auth = useAuthStore()
      expect(auth.isAuthenticated).toBe(false)

      await router.push('/dashboard').catch(() => {})

      expect(router.currentRoute.value.path).toBe('/login')
    })

    it('跳转登录页时保存原始路径', async () => {
      const auth = useAuthStore()

      await router.push('/reports').catch(() => {})

      expect(auth.redirectPath).toBe('/reports')
    })

    it('已登录用户访问登录页时跳转到默认首页', async () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      await router.push('/login').catch(() => {})

      expect(router.currentRoute.value.path).toBe('/strategy')
    })

    it('已登录用户可正常访问受保护页面', async () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      await router.push('/dashboard').catch(() => {})

      expect(router.currentRoute.value.path).toBe('/dashboard')
    })

    it('未登录也可访问公开页面', async () => {
      await router.push('/about').catch(() => {})
      expect(router.currentRoute.value.path).toBe('/about')
    })
  })

  describe('副作用', () => {
    it('导航时设置页面标题', async () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      await router.push('/dashboard').catch(() => {})

      expect(document.title).toBe('仪表板 - TA')
    })

    it('导航时同步当前路由到 appStore', async () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)
      const app = useAppStore()

      await router.push('/favorites').catch(() => {})

      expect(app.currentRoute?.path).toBe('/favorites')
    })
  })
})
