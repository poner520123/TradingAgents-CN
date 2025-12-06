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

export function getCrawlerData(page: number = 1, pageSize: number = 20) {
  return request<CrawlerListResponse>({
    url: '/api/crawler/list',
    method: 'get',
    params: {
      page,
      page_size: pageSize
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
