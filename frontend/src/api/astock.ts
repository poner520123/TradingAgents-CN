import { request } from './request'

// ========== 人气排行榜 ==========

export interface PopularityItem {
  rank: number
  code: string
  name: string
  price: number
  change_ratio: string
  rank_change?: number
  crawled_at?: string
}

export interface PopularityListResponse {
  success: boolean
  data: PopularityItem[]
  total: number
  page: number
  page_size: number
  message: string
}

// ========== 资金流向 ==========

export interface CapitalFlowItem {
  code: string
  name: string
  price: number
  change_ratio: string
  main_flow: number
  main_flow_text: string
  crawled_at?: string
}

export interface CapitalFlowListResponse {
  success: boolean
  data: CapitalFlowItem[]
  total: number
  page: number
  page_size: number
  message: string
}

// ========== 专家排行 ==========

export interface ExpertRankingItem {
  expert_name: string
  name: string
  code: string
  analysis_reason: string
  analysis_time: string
  analysis_price: string
  success_count: number
  success_rate: number
  source_url: string
  crawled_at?: string
}

export interface ExpertRankingListResponse {
  success: boolean
  data: ExpertRankingItem[]
  total: number
  page: number
  page_size: number
  message: string
}

// ========== 交叉分析 ==========

export interface CrossAnalysisItem {
  expert_name: string
  name: string
  code: string
  analysis_reason: string
  analysis_time: string
  analysis_price: string
  success_count: number
  success_rate: number
  source_url: string
  popularity_rank?: number
  capital_flow_rank?: number
  limit_up?: boolean
  crawled_at?: string
}

export interface CrossAnalysisListResponse {
  success: boolean
  data: CrossAnalysisItem[]
  total: number
  page: number
  page_size: number
  message: string
}

// ========== API请求函数 ==========

/**
 * 获取人气排行榜数据
 * @param page 当前页码
 * @param pageSize 每页数据条数
 */
export function getPopularityData(page: number = 1, pageSize: number = 20) {
  return request<PopularityListResponse>({
    url: '/api/ranking/popularity',
    method: 'get',
    params: {
      limit: pageSize
    }
  })
}

/**
 * 获取资金流向数据
 * @param page 当前页码
 * @param pageSize 每页数据条数
 */
export function getCapitalFlowData(page: number = 1, pageSize: number = 20) {
  return request<CapitalFlowListResponse>({
    url: '/api/ranking/fund',
    method: 'get',
    params: {
      limit: pageSize
    }
  })
}

/**
 * 获取专家排行数据
 * @param page 当前页码
 * @param pageSize 每页数据条数
 */
export function getExpertRankingData(page: number = 1, pageSize: number = 20) {
  return request<ExpertRankingListResponse>({
    url: '/api/astock/expert-ranking',
    method: 'get',
    params: {
      page,
      page_size: pageSize
    }
  })
}

/**
 * 获取交叉分析数据
 * @param page 当前页码
 * @param pageSize 每页数据条数
 */
export function getCrossAnalysisData(page: number = 1, pageSize: number = 20) {
  return request<CrossAnalysisListResponse>({
    url: '/api/astock/cross-analysis',
    method: 'get',
    params: {
      page,
      page_size: pageSize
    }
  })
}

/**
 * 手动触发Scrapy爬虫任务
 */
export function runAstockCrawlers() {
  return request<{success: boolean, message: string}>({
    url: '/api/astock/run-crawlers',
    method: 'post'
  })
}