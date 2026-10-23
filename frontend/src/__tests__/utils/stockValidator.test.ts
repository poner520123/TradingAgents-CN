/**
 * ``utils/stockValidator.ts`` 单元测试。
 *
 * 覆盖 A 股代码格式校验：位数、前缀白名单、空白与非数字字符清洗。
 */
import { describe, it, expect } from 'vitest'
import {
  validateAStock,
  validateStockCode,
  getStockCodeFormatHelp,
  getStockCodeExamples,
  formatStockCode
} from '@/utils/stockValidator'

describe('utils/stockValidator', () => {
  describe('validateAStock', () => {
    it.each(['600519', '000001', '300750', '688981', '830799', '430047'])(
      '合法代码 %s 通过校验',
      (code) => {
        const result = validateAStock(code)
        expect(result.valid).toBe(true)
        expect(result.market).toBe('A股')
        expect(result.normalizedCode).toBe(code)
      }
    )

    it.each(['60051', '6005199', '', 'abcdef'])('非法位数 %s 判定为无效', (code) => {
      const result = validateAStock(code)
      expect(result.valid).toBe(false)
      expect(result.message).toContain('6位数字')
    })

    it.each(['123456', '110000', '900001'])('非法前缀 %s 被拒绝', (code) => {
      const result = validateAStock(code)
      expect(result.valid).toBe(false)
      expect(result.message).toContain('前缀')
    })

    it('去除空格与特殊字符后再校验', () => {
      const result = validateAStock(' 600519 ')
      expect(result.valid).toBe(true)
      expect(result.normalizedCode).toBe('600519')
    })

    it('带连字符的代码清洗后仍可识别', () => {
      const result = validateAStock('600-519')
      expect(result.valid).toBe(true)
      expect(result.normalizedCode).toBe('600519')
    })

    it('非数字内容清洗后为空，判定无效', () => {
      const result = validateAStock('abc-def')
      expect(result.valid).toBe(false)
    })
  })

  describe('validateStockCode', () => {
    it('空输入返回明确提示', () => {
      const result = validateStockCode('')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('请输入股票代码')
    })

    it('空白输入同样被拒绝', () => {
      expect(validateStockCode('   ').valid).toBe(false)
    })

    it('合法 A 股代码通过', () => {
      expect(validateStockCode('600519').valid).toBe(true)
    })

    it('带市场提示时行为一致（当前仅支持 A股）', () => {
      expect(validateStockCode('600519', 'A股').valid).toBe(true)
      expect(validateStockCode('AAPL', 'A股').valid).toBe(false)
    })
  })

  describe('辅助函数', () => {
    it('格式说明包含示例代码', () => {
      const help = getStockCodeFormatHelp('A股')
      expect(help).toContain('000001')
      expect(help).toContain('600519')
    })

    it('示例列表为 4 只股票', () => {
      const examples = getStockCodeExamples('A股')
      expect(examples).toHaveLength(4)
      expect(examples).toContain('000001')
    })

    it('格式化返回规范化代码', () => {
      expect(formatStockCode(' 600519 ', 'A股')).toBe('600519')
    })

    it('格式化非法代码时原样返回', () => {
      expect(formatStockCode('ABC', 'A股')).toBe('ABC')
    })
  })
})
