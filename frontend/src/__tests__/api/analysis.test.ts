/**
 * ``api/analysis.ts`` 接口契约测试。
 *
 * 重点验证「前端方法 → 后端路由」的映射是否正确，
 * 因为这些路径直接对应后端 ``app/routers/analysis.py`` 的路由定义。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import { request } from '@/api/request'
import { analysisApi } from '@/api/analysis'
import { setupPinia } from '../helpers/pinia'

const mock = new MockAdapter(request)

beforeEach(() => {
  setupPinia()
  mock.reset()
  // 注意：不要在这里注册 onAny 兜底 —— axios-mock-adapter 按注册顺序匹配，
  // onAny 会抢在具体 handler 之前命中，导致所有断言失效。
})

describe('api/analysis', () => {
  describe('任务提交', () => {
    it('startSingleAnalysis 命中 POST /api/analysis/single', async () => {
      let captured: any
      mock.onPost('/api/analysis/single').reply((config) => {
        captured = config
        return [200, { success: true, data: { task_id: 'task-1' } }]
      })

      const result: any = await analysisApi.startSingleAnalysis({
        symbol: '600519',
        parameters: { research_depth: '标准' }
      })

      expect(captured.url).toBe('/api/analysis/single')
      expect(captured.method).toBe('post')
      expect(JSON.parse(captured.data).symbol).toBe('600519')
      expect(result.data.task_id).toBe('task-1')
    })

    it('startAnalysis 与 startSingleAnalysis 命中同一端点', async () => {
      const urls: string[] = []
      mock.onPost('/api/analysis/single').reply((config) => {
        urls.push(config.url!)
        return [200, { success: true }]
      })

      await analysisApi.startAnalysis({
        market_type: 'A股',
        stock_symbol: '600519',
        analysis_date: '2026-09-01',
        analysis_type: 'comprehensive',
        data_sources: ['akshare'],
        analysis_depth: 3,
        include_news: true,
        include_financials: true
      })

      expect(urls).toEqual(['/api/analysis/single'])
    })

    it('startBatchAnalysis 命中 POST /api/analysis/batch', async () => {
      let captured: any
      mock.onPost('/api/analysis/batch').reply((config) => {
        captured = config
        return [200, { success: true, data: { batch_id: 'b-1', total_tasks: 2 } }]
      })

      const result: any = await analysisApi.startBatchAnalysis({
        title: '批量分析',
        symbols: ['600519', '000001']
      })

      expect(captured.url).toBe('/api/analysis/batch')
      expect(JSON.parse(captured.data).symbols).toEqual(['600519', '000001'])
      expect(result.data.batch_id).toBe('b-1')
    })
  })

  describe('任务查询', () => {
    it('getTaskStatus 命中 GET /api/analysis/tasks/{id}/status', async () => {
      let captured: any
      mock.onGet(/\/api\/analysis\/tasks\/.+\/status/).reply((config) => {
        captured = config
        return [200, { success: true, data: { status: 'completed', progress: 100 } }]
      })

      const result: any = await analysisApi.getTaskStatus('task-1')

      expect(captured.url).toBe('/api/analysis/tasks/task-1/status')
      expect(result.data.status).toBe('completed')
    })

    it('getTaskResult 命中 GET /api/analysis/tasks/{id}/result', async () => {
      let captured: any
      mock.onGet(/\/api\/analysis\/tasks\/.+\/result/).reply((config) => {
        captured = config
        return [200, { success: true, data: { recommendation: '买入' } }]
      })

      const result: any = await analysisApi.getTaskResult('task-1')

      expect(captured.url).toBe('/api/analysis/tasks/task-1/result')
      expect(result.data.recommendation).toBe('买入')
    })

    it('getTaskList 命中 GET /api/analysis/tasks 并携带分页参数', async () => {
      let captured: any
      mock.onGet('/api/analysis/tasks').reply((config) => {
        captured = config
        return [200, { success: true, data: [] }]
      })

      await analysisApi.getTaskList({ status: 'running', limit: 20, offset: 0 })

      expect(captured.url).toBe('/api/analysis/tasks')
      expect(captured.params).toEqual({ status: 'running', limit: 20, offset: 0 })
    })

    it('getTaskDetails 命中 GET /api/analysis/tasks/{id}/details', async () => {
      let captured: any
      mock.onGet(/\/api\/analysis\/tasks\/.+\/details/).reply((config) => {
        captured = config
        return [200, { success: true, data: {} }]
      })

      await analysisApi.getTaskDetails('task-9')
      expect(captured.url).toBe('/api/analysis/tasks/task-9/details')
    })

    it('getBatch 命中 GET /api/analysis/batches/{id}', async () => {
      let captured: any
      mock.onGet(/\/api\/analysis\/batches\/.+/).reply((config) => {
        captured = config
        return [200, { success: true, data: {} }]
      })

      await analysisApi.getBatch('batch-1')
      expect(captured.url).toBe('/api/analysis/batches/batch-1')
    })

    it('getHistory 命中 GET /api/analysis/user/history 并携带筛选参数', async () => {
      let captured: any
      mock.onGet('/api/analysis/user/history').reply((config) => {
        captured = config
        return [200, { success: true, data: { total: 0 } }]
      })

      await analysisApi.getHistory({ page: 1, page_size: 20, symbol: '600519' })

      expect(captured.url).toBe('/api/analysis/user/history')
      expect(captured.params).toEqual({ page: 1, page_size: 20, symbol: '600519' })
    })
  })

  describe('任务操作', () => {
    it('markTaskAsFailed 命中 POST /api/analysis/tasks/{id}/mark-failed', async () => {
      let captured: any
      mock.onPost(/\/api\/analysis\/tasks\/.+\/mark-failed/).reply((config) => {
        captured = config
        return [200, { success: true, message: '已标记失败' }]
      })

      const result: any = await analysisApi.markTaskAsFailed('task-1')

      expect(captured.url).toBe('/api/analysis/tasks/task-1/mark-failed')
      expect(result.message).toBe('已标记失败')
    })

    it('deleteTask 命中 DELETE /api/analysis/tasks/{id}', async () => {
      let captured: any
      mock.onDelete(/\/api\/analysis\/tasks\/.+/).reply((config) => {
        captured = config
        return [200, { success: true, message: '任务已删除' }]
      })

      const result: any = await analysisApi.deleteTask('task-1')

      expect(captured.method).toBe('delete')
      expect(captured.url).toBe('/api/analysis/tasks/task-1')
      expect(result.message).toBe('任务已删除')
    })

    it('deleteAnalysis 命中 DELETE /api/analysis/{id}', async () => {
      let captured: any
      mock.onDelete(/\/api\/analysis\/[^/]+$/).reply((config) => {
        captured = config
        return [200, { success: true, message: '已删除' }]
      })

      await analysisApi.deleteAnalysis('analysis-1')
      expect(captured.url).toBe('/api/analysis/analysis-1')
    })

    it('shareAnalysis 命中 POST /api/analysis/{id}/share', async () => {
      let captured: any
      mock.onPost(/\/api\/analysis\/.+\/share/).reply((config) => {
        captured = config
        return [200, { success: true, data: { share_url: 'https://x', share_code: 'ABC' } }]
      })

      const result: any = await analysisApi.shareAnalysis('analysis-1', { public: true })

      expect(captured.url).toBe('/api/analysis/analysis-1/share')
      expect(JSON.parse(captured.data)).toEqual({ public: true })
      expect(result.data.share_code).toBe('ABC')
    })
  })

  describe('导出', () => {
    it('exportAnalysis 以 blob 形式请求并携带 format 参数', async () => {
      let captured: any
      mock.onGet(/\/api\/analysis\/.+\/export/).reply((config) => {
        captured = config
        return [200, 'binary-content']
      })

      await analysisApi.exportAnalysis('analysis-1', 'excel')

      expect(captured.params).toEqual({ format: 'excel' })
      expect(captured.responseType).toBe('blob')
    })

    it('exportAnalysis 默认导出 pdf', async () => {
      let captured: any
      mock.onGet(/\/api\/analysis\/.+\/export/).reply((config) => {
        captured = config
        return [200, 'binary-content']
      })

      await analysisApi.exportAnalysis('analysis-1')
      expect(captured.params).toEqual({ format: 'pdf' })
    })
  })

  describe('错误传播', () => {
    it('后端返回 404 时 reject', async () => {
      mock.onGet(/\/api\/analysis\/tasks\/.+\/status/).reply(404, { detail: '任务不存在' })

      await expect(analysisApi.getTaskStatus('missing')).rejects.toBeDefined()
    })
  })
})
