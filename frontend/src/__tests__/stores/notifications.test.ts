/**
 * ``stores/notifications.ts`` 单元测试。
 *
 * 覆盖通知列表、未读计数、WebSocket 连接/消息处理/自动重连。
 * WebSocket 用替身实现，``notificationsApi`` 被 mock。
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setupPinia } from '../helpers/pinia'

const { notificationsApiMock } = vi.hoisted(() => ({
  notificationsApiMock: {
    getUnreadCount: vi.fn(),
    getList: vi.fn(),
    markRead: vi.fn(),
    markAllRead: vi.fn()
  }
}))

vi.mock('@/api/notifications', () => ({
  notificationsApi: notificationsApiMock
}))

import { useNotificationStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'

/** WebSocket 替身：记录实例，便于手动触发事件。 */
class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  url: string
  onopen: (() => void) | null = null
  onclose: ((event: any) => void) | null = null
  onerror: ((event: any) => void) | null = null
  onmessage: ((event: any) => void) | null = null
  closed = false

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
  }

  emitOpen() {
    this.onopen?.()
  }

  emitClose(code = 1006) {
    this.onclose?.({ code, reason: 'closed' })
  }

  emitMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
}

const fakeToken = 'header.eyJzdWIiOiJhbGljZSJ9.sig'

beforeEach(() => {
  setupPinia()
  FakeWebSocket.instances = []
  Object.values(notificationsApiMock).forEach((fn) => fn.mockReset())
  vi.stubGlobal('WebSocket', FakeWebSocket as any)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('stores/notifications', () => {
  describe('未读计数', () => {
    it('refreshUnreadCount 读取后端计数', async () => {
      notificationsApiMock.getUnreadCount.mockResolvedValue({ data: { count: 7 } })

      const store = useNotificationStore()
      await store.refreshUnreadCount()

      expect(store.unreadCount).toBe(7)
      expect(store.hasUnread).toBe(true)
    })

    it('接口异常时保持 0 且不抛出', async () => {
      notificationsApiMock.getUnreadCount.mockRejectedValue(new Error('offline'))

      const store = useNotificationStore()
      await expect(store.refreshUnreadCount()).resolves.toBeUndefined()
      expect(store.unreadCount).toBe(0)
    })
  })

  describe('通知列表', () => {
    it('loadList 填充列表并复位 loading', async () => {
      notificationsApiMock.getList.mockResolvedValue({
        data: { items: [{ id: 'n1', title: '标题', content: '内容', type: 'info', status: 'unread' }] }
      })

      const store = useNotificationStore()
      await store.loadList()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].id).toBe('n1')
      expect(store.loading).toBe(false)
    })

    it('loadList 失败时列表置空', async () => {
      notificationsApiMock.getList.mockRejectedValue(new Error('offline'))

      const store = useNotificationStore()
      await store.loadList()

      expect(store.items).toEqual([])
      expect(store.loading).toBe(false)
    })
  })

  describe('已读标记', () => {
    it('markRead 更新条目状态并递减计数', async () => {
      notificationsApiMock.markRead.mockResolvedValue({ success: true })

      const store = useNotificationStore()
      store.addNotification({ title: 'a', content: 'b', type: 'info' })
      expect(store.unreadCount).toBe(1)

      await store.markRead(store.items[0].id)

      expect(store.items[0].status).toBe('read')
      expect(store.unreadCount).toBe(0)
    })

    it('markAllRead 全部置为已读', async () => {
      notificationsApiMock.markAllRead.mockResolvedValue({ success: true })

      const store = useNotificationStore()
      store.addNotification({ title: 'a', content: 'b', type: 'info' })
      store.addNotification({ title: 'c', content: 'd', type: 'info' })

      await store.markAllRead()

      expect(store.items.every((i) => i.status === 'read')).toBe(true)
      expect(store.unreadCount).toBe(0)
    })
  })

  describe('addNotification', () => {
    it('新通知插入列表头部且未读数 +1', () => {
      const store = useNotificationStore()
      store.addNotification({ id: 'x', title: '标题', content: '内容', type: 'info' })

      expect(store.items[0].id).toBe('x')
      expect(store.items[0].status).toBe('unread')
      expect(store.unreadCount).toBe(1)
    })

    it('未指定 id 时自动生成', () => {
      const store = useNotificationStore()
      store.addNotification({ title: '标题', content: '内容', type: 'info' })

      expect(store.items[0].id).toBeTruthy()
      expect(store.items[0].created_at).toBeTruthy()
    })

    it('已读状态的通知不增加未读数', () => {
      const store = useNotificationStore()
      store.addNotification({ title: '标题', content: '内容', type: 'info', status: 'read' })

      expect(store.unreadCount).toBe(0)
    })
  })

  describe('WebSocket', () => {
    it('无 token 时不建立连接', () => {
      const store = useNotificationStore()
      store.connectWebSocket()

      expect(FakeWebSocket.instances).toHaveLength(0)
      expect(store.wsConnected).toBe(false)
    })

    it('有 token 时建立连接并携带 token 参数', () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      const store = useNotificationStore()
      store.connectWebSocket()

      expect(FakeWebSocket.instances).toHaveLength(1)
      expect(FakeWebSocket.instances[0].url).toContain('/api/ws/notifications')
      expect(FakeWebSocket.instances[0].url).toContain(`token=${encodeURIComponent(fakeToken)}`)
    })

    it('连接成功后 wsConnected 为 true', () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      const store = useNotificationStore()
      store.connectWebSocket()
      FakeWebSocket.instances[0].emitOpen()

      expect(store.wsConnected).toBe(true)
      expect(store.connected).toBe(true)
    })

    it('收到 notification 消息时写入列表', () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      const store = useNotificationStore()
      store.connectWebSocket()
      FakeWebSocket.instances[0].emitOpen()
      FakeWebSocket.instances[0].emitMessage({
        type: 'notification',
        data: { id: 'w1', title: '涨停提醒', content: '600519 涨停', type: 'warning' }
      })

      expect(store.items).toHaveLength(1)
      expect(store.items[0].title).toBe('涨停提醒')
      expect(store.unreadCount).toBe(1)
    })

    it('heartbeat 与 connected 消息不产生通知', () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      const store = useNotificationStore()
      store.connectWebSocket()
      FakeWebSocket.instances[0].emitMessage({ type: 'heartbeat' })
      FakeWebSocket.instances[0].emitMessage({ type: 'connected', data: { ok: true } })

      expect(store.items).toHaveLength(0)
    })

    it('连接关闭后 wsConnected 变为 false', () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      const store = useNotificationStore()
      store.connectWebSocket()
      FakeWebSocket.instances[0].emitOpen()
      FakeWebSocket.instances[0].emitClose()

      expect(store.wsConnected).toBe(false)
    })

    it('断开后清理重连定时器', () => {
      vi.useFakeTimers()
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      const store = useNotificationStore()
      store.connectWebSocket()
      FakeWebSocket.instances[0].emitClose()

      store.disconnectWebSocket()
      vi.advanceTimersByTime(60000)

      // 断开后不应再触发重连
      expect(FakeWebSocket.instances).toHaveLength(1)
      expect(store.wsConnected).toBe(false)
    })

    it('重新连接会先关闭旧连接', () => {
      const auth = useAuthStore()
      auth.setAuthInfo(fakeToken, fakeToken)

      const store = useNotificationStore()
      store.connectWebSocket()
      store.connectWebSocket()

      expect(FakeWebSocket.instances).toHaveLength(2)
      expect(FakeWebSocket.instances[0].closed).toBe(true)
    })
  })

  describe('抽屉', () => {
    it('setDrawerVisible 切换显示状态', () => {
      const store = useNotificationStore()
      store.setDrawerVisible(true)
      expect(store.drawerVisible).toBe(true)
      store.setDrawerVisible(false)
      expect(store.drawerVisible).toBe(false)
    })
  })
})
