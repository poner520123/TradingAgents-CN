/**
 * ``stores/app.ts`` 单元测试。
 *
 * 覆盖主题/语言/侧边栏/偏好等 UI 状态，以及 API 连通性探测。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useAppStore } from '@/stores/app'
import { setupPinia } from '../helpers/pinia'

beforeEach(() => {
  setupPinia()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('stores/app', () => {
  describe('初始状态', () => {
    it('默认主题为 auto、语言为 zh-CN', () => {
      const app = useAppStore()
      expect(app.theme).toBe('auto')
      expect(app.language).toBe('zh-CN')
    })

    it('默认偏好为标准分析深度', () => {
      const app = useAppStore()
      expect(app.preferences.defaultMarket).toBe('A股')
      expect(app.preferences.defaultDepth).toBe('3')
      expect(app.preferences.autoRefresh).toBe(true)
      expect(app.preferences.refreshInterval).toBe(30)
    })

    it('侧边栏默认展开且宽度 135', () => {
      const app = useAppStore()
      expect(app.sidebarCollapsed).toBe(false)
      expect(app.sidebarWidth).toBe(135)
    })
  })

  describe('加载状态', () => {
    it('setLoading 同时设置进度', () => {
      const app = useAppStore()
      app.setLoading(true, 42)
      expect(app.loading).toBe(true)
      expect(app.loadingProgress).toBe(42)
    })

    it('setLoadingProgress 被限制在 0-100', () => {
      const app = useAppStore()
      app.setLoadingProgress(150)
      expect(app.loadingProgress).toBe(100)
      app.setLoadingProgress(-10)
      expect(app.loadingProgress).toBe(0)
    })
  })

  describe('主题', () => {
    it('toggleTheme 在 light/dark/auto 之间循环', () => {
      const app = useAppStore()
      app.setTheme('light')
      app.toggleTheme()
      expect(app.theme).toBe('dark')
      app.toggleTheme()
      expect(app.theme).toBe('auto')
      app.toggleTheme()
      expect(app.theme).toBe('light')
    })

    it('setTheme 写入 document 与 localStorage', () => {
      const app = useAppStore()
      app.setTheme('dark')
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
      expect(localStorage.getItem('app-theme')).toBe('dark')
    })

    it('auto 主题跟随系统深色偏好', () => {
      const app = useAppStore()
      app.setTheme('auto')
      // setup.ts 中 matchMedia 固定返回 matches: false
      expect(app.isDarkTheme).toBe(false)
    })

    it('显式 dark 主题的 isDarkTheme 为 true', () => {
      const app = useAppStore()
      app.setTheme('dark')
      expect(app.isDarkTheme).toBe(true)
    })
  })

  describe('语言', () => {
    it('setLanguage 更新状态与 document.lang', () => {
      const app = useAppStore()
      app.setLanguage('en-US')
      expect(app.language).toBe('en-US')
      expect(document.documentElement.lang).toBe('en-US')
      expect(localStorage.getItem('app-language')).toBe('en-US')
    })
  })

  describe('侧边栏', () => {
    it('toggleSidebar 切换折叠状态', () => {
      const app = useAppStore()
      app.toggleSidebar()
      expect(app.sidebarCollapsed).toBe(true)
    })

    it('折叠时实际宽度为 64', () => {
      const app = useAppStore()
      app.setSidebarCollapsed(true)
      expect(app.actualSidebarWidth).toBe(64)
    })

    it('展开时实际宽度为设定值', () => {
      const app = useAppStore()
      app.setSidebarCollapsed(false)
      app.setSidebarWidth(200)
      expect(app.actualSidebarWidth).toBe(200)
    })

    it('宽度被限制在 100-400 之间', () => {
      const app = useAppStore()
      app.setSidebarWidth(50)
      expect(app.sidebarWidth).toBe(100)
      app.setSidebarWidth(9999)
      expect(app.sidebarWidth).toBe(400)
    })
  })

  describe('偏好设置', () => {
    it('updatePreferences 合并并持久化', () => {
      const app = useAppStore()
      app.updatePreferences({ defaultDepth: '5' })
      expect(app.preferences.defaultDepth).toBe('5')
      expect(app.preferences.defaultMarket).toBe('A股')

      const stored = JSON.parse(localStorage.getItem('user-preferences')!)
      expect(stored.defaultDepth).toBe('5')
    })

    it('resetPreferences 恢复默认值', () => {
      const app = useAppStore()
      app.updatePreferences({ defaultDepth: '5', autoRefresh: false })
      app.resetPreferences()
      expect(app.preferences.defaultDepth).toBe('3')
      expect(app.preferences.autoRefresh).toBe(true)
    })
  })

  describe('路由与标题', () => {
    it('currentPageTitle 读取路由 meta', () => {
      const app = useAppStore()
      app.setCurrentRoute({ meta: { title: '仪表板' } } as any)
      expect(app.currentPageTitle).toBe('仪表板')
    })

    it('无路由时标题回退为 TA', () => {
      const app = useAppStore()
      expect(app.currentPageTitle).toBe('TA')
    })
  })

  describe('API 连通性', () => {
    it('健康检查成功时标记为已连接', async () => {
      const app = useAppStore()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, json: async () => ({ version: '1.0.0' }) })
      )

      const connected = await app.checkApiConnection()
      expect(connected).toBe(true)
      expect(app.apiConnected).toBe(true)
    })

    it('健康检查失败时标记为未连接', async () => {
      const app = useAppStore()
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))

      const connected = await app.checkApiConnection()
      expect(connected).toBe(false)
      expect(app.apiConnected).toBe(false)
    })

    it('网络异常时返回 false 而不抛出', async () => {
      const app = useAppStore()
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

      await expect(app.checkApiConnection()).resolves.toBe(false)
    })

    it('fetchApiVersion 记录后端版本号', async () => {
      const app = useAppStore()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, json: async () => ({ version: '1.0.0-preview' }) })
      )

      await app.fetchApiVersion()
      expect(app.apiVersion).toBe('1.0.0-preview')
    })
  })

  describe('重置', () => {
    it('resetAppState 清空加载态与当前路由', () => {
      const app = useAppStore()
      app.setLoading(true, 50)
      app.setCurrentRoute({ meta: { title: 'x' } } as any)

      app.resetAppState()

      expect(app.loading).toBe(false)
      expect(app.loadingProgress).toBe(0)
      expect(app.currentRoute).toBeNull()
    })
  })
})
