/**
 * ``api/strategy.ts`` 接口契约测试（龙头复盘神器 · 高级策略）。
 *
 * 该模块对应后端 ``app/routers/strategy.py`` 的 ``GET /api/strategy/monthly``。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import { request } from '@/api/request'
import { getStrategyMonthly, type StrategyKey } from '@/api/strategy'
import { setupPinia } from '../helpers/pinia'

const mock = new MockAdapter(request)

beforeEach(() => {
  setupPinia()
  mock.reset()
})

describe('api/strategy', () => {
  it('请求路径为 /api/strategy/monthly', async () => {
    let captured: any
    mock.onGet('/api/strategy/monthly').reply((config) => {
      captured = config
      return [200, { success: true, strategy: 'tcld', month: 202609, has_data: true, rows: [], stats: null }]
    })

    await getStrategyMonthly('tcld', 202609)

    expect(captured.url).toBe('/api/strategy/monthly')
    expect(captured.method).toBe('get')
  })

  it('通过 query 传递 strategy 与 month', async () => {
    let captured: any
    mock.onGet('/api/strategy/monthly').reply((config) => {
      captured = config
      return [200, { success: true }]
    })

    await getStrategyMonthly('cyb', 202610)

    expect(captured.params).toEqual({ strategy: 'cyb', month: 202610 })
  })

  it.each<StrategyKey>(['tcld', 'zb', 'cyb'])('策略 %s 均可请求', async (strategy) => {
    let captured: any
    mock.onGet('/api/strategy/monthly').reply((config) => {
      captured = config
      return [200, { success: true, strategy }]
    })

    const result: any = await getStrategyMonthly(strategy, 202609)
    expect(captured.params.strategy).toBe(strategy)
    expect(result.strategy).toBe(strategy)
  })

  it('成功响应原样透传 rows 与 stats', async () => {
    const payload = {
      success: true,
      strategy: 'tcld',
      strategy_title: '题材轮动策略',
      month: 202609,
      has_data: true,
      message: '',
      rows: [
        {
          selected_date: '2026-09-01',
          code: '600519',
          name: '贵州茅台',
          price: '1680.5',
          highest_price: '1710.2',
          closing_price: '1705.0',
          highest_pct: 1.5,
          closing_pct: 0.9
        }
      ],
      stats: { highest_total: 12.5, closing_total: 8.1, count: 1 }
    }
    mock.onGet('/api/strategy/monthly').reply(200, payload)

    const result: any = await getStrategyMonthly('tcld', 202609)

    expect(result.rows).toHaveLength(1)
    expect(result.rows[0].code).toBe('600519')
    expect(result.stats.highest_total).toBe(12.5)
    expect(result.stats.count).toBe(1)
  })

  it('后端返回业务失败时 reject', async () => {
    mock.onGet('/api/strategy/monthly').reply(200, {
      success: false,
      message: '未知策略: xxx',
      has_data: false,
      rows: [],
      stats: null
    })

    await expect(getStrategyMonthly('xxx' as StrategyKey, 202609)).rejects.toThrow('未知策略')
  })

  it('缓存命中时透传 cached 标记', async () => {
    mock.onGet('/api/strategy/monthly').reply(200, {
      success: true,
      cached: true,
      has_data: true,
      rows: [],
      stats: null
    })

    const result: any = await getStrategyMonthly('zb', 202609)
    expect(result.cached).toBe(true)
  })
})
