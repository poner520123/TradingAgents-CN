/**
 * Vitest 全局 setup。
 *
 * 职责：
 * 1. 补齐 happy-dom 缺失的浏览器 API（matchMedia / ResizeObserver / IntersectionObserver）；
 * 2. 每个用例前后清理 localStorage / sessionStorage，避免认证态串味；
 * 3. 静音业务代码中大量的 console.log，避免测试输出被淹没。
 */
import { beforeEach, afterEach, vi } from 'vitest'

// ---------------------------------------------------------------------------
// 浏览器 API 补齐
// ---------------------------------------------------------------------------
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn()
    })
  })
}

if (!('ResizeObserver' in globalThis)) {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  ;(globalThis as any).ResizeObserver = ResizeObserverStub
}

if (!('IntersectionObserver' in globalThis)) {
  class IntersectionObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return []
    }
  }
  ;(globalThis as any).IntersectionObserver = IntersectionObserverStub
}

// happy-dom 未实现 scrollTo / scrollIntoView
if (!window.scrollTo) {
  window.scrollTo = (() => {}) as any
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = (() => {}) as any
}

// ---------------------------------------------------------------------------
// 存储清理
// ---------------------------------------------------------------------------
beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})

afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})

// ---------------------------------------------------------------------------
// 静音噪音日志
// ---------------------------------------------------------------------------
// 业务代码（request.ts / stores/auth.ts / utils/datetime.ts）大量输出 console.log
// 与 console.debug，在正常用例中属于噪音。
// 这里静音 log/debug/info，保留 warn/error —— 用例失败时仍能拿到诊断线索。
const originalLog = console.log
const originalDebug = console.debug
const originalInfo = console.info

beforeEach(() => {
  console.log = () => {}
  console.debug = () => {}
  console.info = () => {}
})

afterEach(() => {
  console.log = originalLog
  console.debug = originalDebug
  console.info = originalInfo
})
