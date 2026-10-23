/**
 * ``utils/auth.ts`` 令牌工具单元测试。
 *
 * 覆盖 JWT 有效性判定、载荷解析、剩余有效期与临期判定。
 * 这些函数决定前端何时触发自动刷新，是登录态可靠性的基础。
 */
import { describe, it, expect } from 'vitest'
import {
  isTokenValid,
  parseToken,
  getTokenRemainingTime,
  isTokenExpiringSoon,
  isAuthError
} from '@/utils/auth'

/** 构造一个 JWT（不做真实签名，测试只关心结构与 payload）。 */
function makeToken(payload: Record<string, unknown>): string {
  const encode = (obj: unknown) =>
    btoa(unescape(encodeURIComponent(JSON.stringify(obj))))
      .replace(/=+$/, '')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
  return `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode(payload)}.signature`
}

describe('utils/auth', () => {
  describe('isTokenValid', () => {
    it('结构合法且未过期的 token 有效', () => {
      const token = makeToken({ sub: 'alice', exp: Math.floor(Date.now() / 1000) + 3600 })
      expect(isTokenValid(token)).toBe(true)
    })

    it('mock token 被拒绝', () => {
      expect(isTokenValid('mock-token')).toBe(false)
      expect(isTokenValid('mock-anything')).toBe(false)
    })

    it('非 3 段结构被拒绝', () => {
      expect(isTokenValid('abc')).toBe(false)
      expect(isTokenValid('a.b.c.d')).toBe(false)
    })

    it('空值被拒绝', () => {
      expect(isTokenValid(null)).toBe(false)
      expect(isTokenValid('')).toBe(false)
    })

    it('已过期的 token 被拒绝', () => {
      const token = makeToken({ sub: 'alice', exp: Math.floor(Date.now() / 1000) - 10 })
      expect(isTokenValid(token)).toBe(false)
    })

    it('payload 无法解析时被拒绝', () => {
      expect(isTokenValid('aaa.!!!not-base64!!!.ccc')).toBe(false)
    })

    it('无 exp 字段的 token 视为有效', () => {
      const token = makeToken({ sub: 'alice' })
      expect(isTokenValid(token)).toBe(true)
    })
  })

  describe('parseToken', () => {
    it('解析出 payload', () => {
      const token = makeToken({ sub: 'alice', roles: ['admin'] })
      const payload = parseToken(token)
      expect(payload.sub).toBe('alice')
      expect(payload.roles).toEqual(['admin'])
    })

    it('非法 token 返回 null', () => {
      expect(parseToken('not-a-token')).toBeNull()
      expect(parseToken('')).toBeNull()
    })
  })

  describe('getTokenRemainingTime', () => {
    it('返回剩余秒数', () => {
      const exp = Math.floor(Date.now() / 1000) + 120
      const remaining = getTokenRemainingTime(makeToken({ exp }))
      expect(remaining).toBeGreaterThan(100)
      expect(remaining).toBeLessThanOrEqual(120)
    })

    it('已过期返回 0', () => {
      const exp = Math.floor(Date.now() / 1000) - 60
      expect(getTokenRemainingTime(makeToken({ exp }))).toBe(0)
    })

    it('无 exp 或非法 token 返回 0', () => {
      expect(getTokenRemainingTime(makeToken({ sub: 'a' }))).toBe(0)
      expect(getTokenRemainingTime('garbage')).toBe(0)
    })
  })

  describe('isTokenExpiringSoon', () => {
    it('剩余时间少于阈值时为真', () => {
      const exp = Math.floor(Date.now() / 1000) + 60
      expect(isTokenExpiringSoon(makeToken({ exp }), 300)).toBe(true)
    })

    it('剩余时间充足时为假', () => {
      const exp = Math.floor(Date.now() / 1000) + 3600
      expect(isTokenExpiringSoon(makeToken({ exp }), 300)).toBe(false)
    })

    it('已过期的 token 不算临期', () => {
      const exp = Math.floor(Date.now() / 1000) - 60
      expect(isTokenExpiringSoon(makeToken({ exp }), 300)).toBe(false)
    })
  })

  describe('isAuthError', () => {
    it('HTTP 401 判定为认证错误', () => {
      expect(isAuthError({ response: { status: 401 } })).toBe(true)
    })

    it('业务错误码 40101 判定为认证错误', () => {
      expect(isAuthError({ code: 40101 })).toBe(true)
      expect(isAuthError({ response: { data: { code: 40102 } } })).toBe(true)
    })

    it('消息包含关键词时判定为认证错误', () => {
      expect(isAuthError({ message: '登录已过期，请重新登录' })).toBe(true)
      expect(isAuthError({ response: { data: { message: '认证失败' } } })).toBe(true)
    })

    it('普通错误不算认证错误', () => {
      expect(isAuthError({ response: { status: 500 }, message: '服务器内部错误' })).toBe(false)
      expect(isAuthError(null)).toBe(false)
    })
  })
})
