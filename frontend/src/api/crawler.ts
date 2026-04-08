import { request } from './request'

export interface CrawlerData {
  user_name: string
  success_count: string
  success_rate: string
  stock_name: string
  stock_code?: string
  reason: string
  time: string
  price: string
  current_price: string
  increase: string
  limit_up: string
  limit_up_date: string
  concepts: string
  crawled_at: string
}

export interface CrawlerListResponse {
  success: boolean
  data: CrawlerData[]
  total: number
  page: number
  page_size: number
  message: string
}

export interface CrawlerFilterParams {
  page?: number
  page_size?: number
  user_name?: string
  min_success_rate?: number | null
  reason?: string
  start_date?: string
  end_date?: string
}

export function getCrawlerData(params: CrawlerFilterParams = {}) {
  return request<CrawlerListResponse>({
    url: '/api/crawler/list',
    method: 'get',
    params: {
      page: 1,
      page_size: 20,
      ...params
    }
  })
}

export function startCrawl(pages: number = 1, force: boolean = false) {
  return request<{success: boolean, message: string}>({
    url: '/api/crawler/crawl',
    method: 'post',
    data: {
      pages,
      force
    }
  })
}
