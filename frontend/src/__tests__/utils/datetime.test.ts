/**
 * ``utils/datetime.ts`` 单元测试。
 *
 * 该模块负责把后端返回的多种时间格式统一转换为 Asia/Shanghai 本地时间，
 * 关键契约：
 * - 无时区信息的后端时间串按 UTC+8 解释；
 * - 兼容 "YYYY-MM-DD  HH:MM"（双空格、无秒）等非标准格式；
 * - 空值统一返回 '-'。
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  formatDateTime,
  formatDateTimeWithRelative,
  formatDate,
  formatTime,
  formatRelativeTime
} from '@/utils/datetime'

afterEach(() => {
  vi.useRealTimers()
})

describe('utils/datetime', () => {
  describe('formatDateTime', () => {
    it('空值返回占位符', () => {
      expect(formatDateTime(null)).toBe('-')
      expect(formatDateTime(undefined)).toBe('-')
      expect(formatDateTime('')).toBe('-')
    })

    it('带时区的时间串被正确解析', () => {
      const result = formatDateTime('2026-09-01T10:30:00+08:00')
      expect(result).toContain('2026')
      expect(result).toContain('10:30')
    })

    it('无时区的时间串按 UTC+8 解释', () => {
      const withTz = formatDateTime('2026-09-01T10:30:00+08:00')
      const withoutTz = formatDateTime('2026-09-01T10:30:00')
      expect(withoutTz).toBe(withTz)
    })

    it('修复双空格且无秒的格式', () => {
      const result = formatDateTime('2026-09-01  10:30')
      expect(result).toContain('10:30:00')
    })

    it('修复单空格且无秒的格式', () => {
      const result = formatDateTime('2026-09-01 10:30')
      expect(result).toContain('10:30:00')
    })

    it('formatDateTime 缺少秒时补齐为 00', () => {
      expect(formatDateTime('2026-09-01  10:30')).toContain('10:30:00')
    })

    it('秒级时间戳被正确转换', () => {
      const ts = Math.floor(new Date('2026-09-01T10:30:00+08:00').getTime() / 1000)
      const result = formatDateTime(ts)
      expect(result).toContain('10:30')
    })

    it('毫秒级时间戳被正确转换', () => {
      const ms = new Date('2026-09-01T10:30:00+08:00').getTime()
      const result = formatDateTime(ms)
      expect(result).toContain('10:30')
    })

    it('无法解析时原样返回输入', () => {
      expect(formatDateTime('not-a-date')).toBe('not-a-date')
    })

    it('自定义选项可以覆盖默认值', () => {
      const result = formatDateTime('2026-09-01T10:30:00+08:00', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
      expect(result).toContain('10:30')
    })
  })

  describe('formatDate / formatTime', () => {
    it('formatDate 只输出日期部分', () => {
      const result = formatDate('2026-09-01T10:30:00+08:00')
      expect(result).toContain('2026')
      expect(result).toContain('09')
      expect(result).toContain('01')
      expect(result).not.toContain('10:30')
    })

    it('formatTime 只输出时间部分', () => {
      const result = formatTime('2026-09-01T10:30:00+08:00')
      expect(result).toContain('10:30')
      expect(result).not.toContain('2026')
    })

    it('formatDate 缺少秒时仍能正确解析出日期', () => {
      // "2026-09-01  10:30"（双空格、无秒）需被修复为合法时间串后取日期部分
      expect(formatDate('2026-09-01  10:30')).toBe('2026/09/01')
    })

    it('formatTime 空值返回占位符', () => {
      expect(formatTime(undefined)).toBe('-')
    })

    it('formatDate 空值返回占位符', () => {
      expect(formatDate(null)).toBe('-')
    })

    it('formatDate 至少输出年月日', () => {
      const result = formatDate('2026-09-01T10:30:00+08:00')
      expect(result).toMatch(/2026/)
      expect(result).toMatch(/09/)
      expect(result).toMatch(/01/)
    })
  })

  describe('formatRelativeTime', () => {
    it('过去的分钟级时间显示分钟前', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-09-01T12:00:00+08:00'))
      expect(formatRelativeTime('2026-09-01T11:30:00+08:00')).toBe('30分钟前')
    })

    it('过去的天级时间显示天前', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-09-05T12:00:00+08:00'))
      expect(formatRelativeTime('2026-09-01T11:30:00+08:00')).toBe('4天前')
    })

    it('未来时间显示后缀', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-09-01T12:00:00+08:00'))
      expect(formatRelativeTime('2026-09-01T12:30:00+08:00')).toBe('30分钟后')
    })

    it('10 秒内视为即将执行', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-09-01T12:00:00+08:00'))
      expect(formatRelativeTime('2026-09-01T12:00:05+08:00')).toBe('即将执行')
    })

    it('空值返回占位符', () => {
      expect(formatRelativeTime(null)).toBe('-')
    })
  })

  describe('formatDateTimeWithRelative', () => {
    it('同时包含绝对时间与相对描述', () => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-09-01T12:00:00+08:00'))
      const result = formatDateTimeWithRelative('2026-09-01T11:30:00+08:00')
      expect(result).toContain('11:30')
      expect(result).toContain('30分钟前')
    })

    it('空值返回占位符', () => {
      expect(formatDateTimeWithRelative('')).toBe('-')
    })
  })
})
