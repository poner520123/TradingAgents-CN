/**
 * ``utils/stock.ts`` 单元测试。
 *
 * 覆盖新旧字段（symbol / stock_code / code / full_symbol）兼容逻辑、
 * 代码校验与市场推断。该模块被前后端字段标准化流程大量依赖。
 */
import { describe, it, expect } from 'vitest'
import {
  getStockSymbol,
  getFullSymbol,
  createSymbolObject,
  normalizeSymbols,
  validateSymbol,
  formatSymbol,
  extractSymbol,
  inferMarketCode,
  buildFullSymbol,
  normalizeStockObject,
  normalizeStockArray
} from '@/utils/stock'

describe('utils/stock', () => {
  describe('getStockSymbol', () => {
    it('按 symbol > stock_code > code 优先级取值', () => {
      expect(getStockSymbol({ symbol: '600519', stock_code: '000001', code: '300750' })).toBe('600519')
      expect(getStockSymbol({ stock_code: '000001', code: '300750' })).toBe('000001')
      expect(getStockSymbol({ code: '300750' })).toBe('300750')
    })

    it('缺失时返回空串', () => {
      expect(getStockSymbol({})).toBe('')
      expect(getStockSymbol(null)).toBe('')
      expect(getStockSymbol(undefined)).toBe('')
    })
  })

  describe('getFullSymbol', () => {
    it('优先返回 full_symbol', () => {
      expect(getFullSymbol({ full_symbol: '600519.SH', symbol: '600519' })).toBe('600519.SH')
    })

    it('回退到其它字段', () => {
      expect(getFullSymbol({ symbol: '600519' })).toBe('600519')
      expect(getFullSymbol({})).toBe('')
    })
  })

  describe('createSymbolObject', () => {
    it('同时填充三个兼容字段', () => {
      const obj = createSymbolObject('600519')
      expect(obj).toEqual({ symbol: '600519', stock_code: '600519', code: '600519' })
    })

    it('传入完整代码时追加 full_symbol', () => {
      const obj = createSymbolObject('600519', '600519.SH')
      expect(obj.full_symbol).toBe('600519.SH')
    })
  })

  describe('normalizeSymbols', () => {
    it('混合字符串与对象并去重', () => {
      const result = normalizeSymbols([
        '600519',
        { symbol: '600519' },
        { stock_code: '000001' },
        { code: '300750' }
      ])
      expect(result).toEqual(['600519', '000001', '300750'])
    })

    it('过滤空值', () => {
      expect(normalizeSymbols(['', null as any, { symbol: '' }])).toEqual([])
    })
  })

  describe('validateSymbol', () => {
    it('A股要求 6 位数字', () => {
      expect(validateSymbol('600519', 'A股')).toBe(true)
      expect(validateSymbol('60051', 'A股')).toBe(false)
    })

    it('美股要求 1-5 位字母且大小写不敏感', () => {
      expect(validateSymbol('AAPL', '美股')).toBe(true)
      expect(validateSymbol('aapl', 'US')).toBe(true)
      expect(validateSymbol('ABCDEF', '美股')).toBe(false)
    })

    it('港股接受 4-5 位数字或 .HK 后缀', () => {
      expect(validateSymbol('0700', '港股')).toBe(true)
      expect(validateSymbol('0700.HK', 'HK')).toBe(true)
    })

    it('未指定市场时通用校验三种格式', () => {
      expect(validateSymbol('600519')).toBe(true)
      expect(validateSymbol('AAPL')).toBe(true)
      expect(validateSymbol('0700.HK')).toBe(true)
      expect(validateSymbol('!!!')).toBe(false)
    })

    it('空值无效', () => {
      expect(validateSymbol('')).toBe(false)
    })
  })

  describe('formatSymbol', () => {
    it('美股统一大写', () => {
      expect(formatSymbol('aapl', '美股')).toBe('AAPL')
    })

    it('港股补 .HK 后缀', () => {
      expect(formatSymbol('0700', '港股')).toBe('0700.HK')
      expect(formatSymbol('0700.HK', '港股')).toBe('0700.HK')
    })

    it('A股仅去除空白', () => {
      expect(formatSymbol(' 600519 ', 'A股')).toBe('600519')
    })

    it('空值返回空串', () => {
      expect(formatSymbol('')).toBe('')
    })
  })

  describe('extractSymbol', () => {
    it('去掉市场后缀', () => {
      expect(extractSymbol('000001.SZ')).toBe('000001')
      expect(extractSymbol('600519.SH')).toBe('600519')
      expect(extractSymbol('0700.HK')).toBe('0700')
    })

    it('空值返回空串', () => {
      expect(extractSymbol('')).toBe('')
    })
  })

  describe('inferMarketCode', () => {
    it.each([
      ['000001', 'SZ'],
      ['002415', 'SZ'],
      ['300750', 'SZ'],
      ['600519', 'SH'],
      ['601398', 'SH'],
      ['688981', 'SH'],
      ['830799', 'BJ'],
      ['430047', 'BJ']
    ])('%s 推断为 %s', (code, expected) => {
      expect(inferMarketCode(code)).toBe(expected)
    })

    it('非 6 位数字返回 null', () => {
      expect(inferMarketCode('12345')).toBeNull()
      expect(inferMarketCode('')).toBeNull()
    })

    it('未知前缀返回 null', () => {
      expect(inferMarketCode('123456')).toBeNull()
    })
  })

  describe('buildFullSymbol', () => {
    it('自动推断市场后缀', () => {
      expect(buildFullSymbol('600519')).toBe('600519.SH')
      expect(buildFullSymbol('000001')).toBe('000001.SZ')
    })

    it('显式指定市场优先', () => {
      expect(buildFullSymbol('600519', 'SZ')).toBe('600519.SZ')
    })

    it('无法推断时原样返回', () => {
      expect(buildFullSymbol('123456')).toBe('123456')
    })

    it('空值返回空串', () => {
      expect(buildFullSymbol('')).toBe('')
    })
  })

  describe('normalizeStockObject / normalizeStockArray', () => {
    it('补齐兼容字段但保留原有属性', () => {
      const result = normalizeStockObject({ code: '600519', name: '贵州茅台' })
      expect(result.symbol).toBe('600519')
      expect(result.stock_code).toBe('600519')
      expect(result.code).toBe('600519')
      expect(result.name).toBe('贵州茅台')
    })

    it('数组逐项规范化', () => {
      const result = normalizeStockArray([{ code: '600519' }, { symbol: '000001' }])
      expect(result[0].symbol).toBe('600519')
      expect(result[1].symbol).toBe('000001')
    })

    it('非数组输入原样返回', () => {
      expect(normalizeStockArray(null as any)).toBeNull()
    })
  })
})
