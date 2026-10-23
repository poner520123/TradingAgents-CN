import { request } from './request'

export type StrategyKey = 'tcld' | 'zb' | 'cyb'

export interface StrategyRow {
  selected_date: string
  code: string
  name: string
  price: string
  highest_price: string
  closing_price: string
  highest_pct: number | null
  closing_pct: number | null
}

export interface StrategyStats {
  highest_total: number
  closing_total: number
  count: number
}

export interface StrategyMonthlyResponse {
  success: boolean
  strategy: StrategyKey
  strategy_title: string
  month: number
  has_data: boolean
  message: string
  rows: StrategyRow[]
  stats: StrategyStats | null
  cached?: boolean
}

/**
 * 获取单个策略的月度信号数据
 * @param strategy 策略标识 tcld / zb / cyb
 * @param month 月份，例如 202609
 */
export function getStrategyMonthly(strategy: StrategyKey, month: number) {
  return request<StrategyMonthlyResponse>({
    url: '/api/strategy/monthly',
    method: 'get',
    params: { strategy, month }
  })
}
