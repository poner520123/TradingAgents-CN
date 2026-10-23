/**
 * ``utils/market.ts`` 单元测试。
 *
 * 该模块当前被裁剪为**只支持 A 股**（三个函数恒定返回 'A股'），
 * 这里的断言锁定该既有行为，避免后续重构时被无意破坏。
 */
import { describe, it, expect } from 'vitest'
import {
  normalizeMarketForAnalysis,
  exchangeCodeToMarket,
  getMarketByStockCode
} from '@/utils/market'

describe('utils/market', () => {
  describe('normalizeMarketForAnalysis', () => {
    it.each([
      ['A股'],
      ['港股'],
      ['美股'],
      [undefined],
      [null],
      [123]
    ])('输入 %s 一律归一化为 A股', (input) => {
      expect(normalizeMarketForAnalysis(input as any)).toBe('A股')
    })
  })

  describe('exchangeCodeToMarket', () => {
    it.each(['sz', 'sh', 'bj', 'sse', 'szse', 'bse', ''])(
      '交易所代码 %s 归一化为 A股',
      (code) => {
        expect(exchangeCodeToMarket(code)).toBe('A股')
      }
    )
  })

  describe('getMarketByStockCode', () => {
    it.each(['600519', '000001', '300750', 'AAPL', '0700.HK', '123'])(
      '股票代码 %s 归一化为 A股',
      (code) => {
        expect(getMarketByStockCode(code)).toBe('A股')
      }
    )
  })

  it('default 导出提供同样的三个函数', async () => {
    const market = (await import('@/utils/market')).default
    expect(market.normalizeMarketForAnalysis('美股')).toBe('A股')
    expect(market.exchangeCodeToMarket('sh')).toBe('A股')
    expect(market.getMarketByStockCode('AAPL')).toBe('A股')
  })
})
