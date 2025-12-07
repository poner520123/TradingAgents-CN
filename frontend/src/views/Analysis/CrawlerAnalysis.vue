<template>
  <div class="crawler-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">爬虫分析</span>
            <el-tag type="info" class="ml-2">178448.com</el-tag>
          </div>
          <div class="header-right" style="display: flex; align-items: center; gap: 10px;">
            <el-input-number v-model="crawlPages" :min="1" :max="20" size="default" style="width: 120px;" />
            <div class="crawl-controls" style="display: flex; align-items: center; gap: 10px;">
              <el-switch 
                v-model="autoCrawlEnabled" 
                @change="handleAutoCrawlToggle" 
              />
              <span>定时爬取</span>
              <el-select v-model="autoCrawlInterval" placeholder="选择间隔" size="small" @change="handleIntervalChange" style="width: 120px;">
                <el-option label="3分钟" :value="3" />
                <el-option label="5分钟" :value="5" />
                <el-option label="10分钟" :value="10" />
                <el-option label="30分钟" :value="30" />
                <el-option label="1小时" :value="60" />
              </el-select>
              <el-button 
                type="danger" 
                size="small" 
                @click="handleStopCrawl" 
                :disabled="!crawling && !autoCrawlEnabled"
              >
                关闭爬虫
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <!-- 爬虫数据列表 -->
      <el-table :data="tableData" style="width: 100%" v-loading="loading" border stripe>
        <el-table-column prop="stock_code" label="股票代码" width="120" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.stock_code || '未知' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="stock_name" label="股票名称" width="120" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.stock_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_name" label="伏击人" width="100" />
        <el-table-column prop="success_rate" label="成功率" width="100">
          <template #default="scope">
            <el-tag :type="getSuccessRateType(scope.row.success_rate)">{{ scope.row.success_rate }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="concepts" label="题材概念" min-width="200">
          <template #default="scope">
            <div class="concepts-wrapper">
              <el-tag 
                v-for="(concept, index) in parseConcepts(scope.row.concepts)" 
                :key="index" 
                size="small" 
                class="mr-1 mb-1"
                effect="plain"
              >
                {{ concept }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="伏击理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="time" label="发布时间" width="160" sortable />
        <el-table-column prop="price" label="伏击价" width="100" />
        <el-table-column prop="increase" label="涨幅" width="100">
           <template #default="scope">
            <span :class="getIncreaseClass(scope.row.increase)">{{ scope.row.increase }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="AI分析" width="120" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" plain @click="analyzeStock(scope.row)">
              <el-icon><DataAnalysis /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis } from '@element-plus/icons-vue'
import { getCrawlerData, startCrawl, type CrawlerData } from '@/api/crawler'
import { getStockCodeByName, loadStockNameCodeMap, getStockCodesByNames } from '@/utils/stockNameCodeMap'
import { useNotificationStore } from '@/stores/notifications'

const router = useRouter()
const loading = ref(false)
const crawling = ref(false)
const tableData = ref<CrawlerData[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const crawlPages = ref(5)

// WebSocket连接引用
let ws: WebSocket | null = null

// 自动爬取相关
const autoCrawlEnabled = ref(false)
const autoCrawlInterval = ref(5) // 分钟
let crawlTimer: number | null = null

// 页面加载时初始化股票名称到代码的映射
onMounted(async () => {
  await loadStockNameCodeMap()
  await fetchData()
  
  // 添加WebSocket消息监听
  const token = localStorage.getItem('auth-token') || ''
  if (token) {
    ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/notifications?token=${token}`)
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        if (message.type === 'notification' && message.data?.type === 'crawler') {
          console.log('[CrawlerAnalysis] 收到爬虫完成通知，自动刷新数据')
          fetchData()
        }
      } catch (error) {
        console.error('[CrawlerAnalysis] 解析WebSocket消息失败:', error)
      }
    }
    
    ws.onerror = (error) => {
      console.error('[CrawlerAnalysis] WebSocket连接错误:', error)
    }
    
    ws.onclose = () => {
      console.log('[CrawlerAnalysis] WebSocket连接关闭')
    }
  }
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getCrawlerData(currentPage.value, pageSize.value)
    if (res.success) {
      tableData.value = res.data
      total.value = res.total
      // 为没有股票代码的股票获取代码
      await fetchStockCodes()
    }
  } catch (error) {
    console.error('Failed to fetch crawler data:', error)
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const fetchStockCodes = async () => {
  // 收集所有没有股票代码的股票名称
  const missingCodes = tableData.value.filter(item => !item.stock_code).map(item => item.stock_name)
  
  if (missingCodes.length === 0) {
    return
  }
  
  try {
    // 使用批量请求获取所有缺失的股票代码
    const codeMap = await getStockCodesByNames(missingCodes)
    
    // 更新表格数据
    tableData.value.forEach(item => {
      if (!item.stock_code && codeMap[item.stock_name]) {
        item.stock_code = codeMap[item.stock_name]
      }
    })
  } catch (error) {
    console.error('Failed to fetch stock codes in batch:', error)
    // 如果批量请求失败，尝试使用本地映射
    try {
      // 等待本地映射加载完成
      const localMap = await loadStockNameCodeMap()
      
      // 使用本地映射更新股票代码
      tableData.value.forEach(item => {
        if (!item.stock_code && localMap[item.stock_name]) {
          item.stock_code = localMap[item.stock_name]
        }
      })
    } catch (localError) {
      console.error('Failed to use local stock code map:', localError)
    }
  }
}

const handleStartCrawl = async () => {
  crawling.value = true
  try {
    const res = await startCrawl(crawlPages.value)
    if (res.success) {
      ElMessage.success(`开始爬取前 ${crawlPages.value} 页数据，请稍后刷新查看`)
      // 由于实际爬取在后台进行，我们需要保持爬取状态一段时间
      setTimeout(() => {
        fetchData()
      }, 2000)
      // 30秒后重置状态，模拟实际爬取时间
      setTimeout(() => {
        if (crawling.value) {
          crawling.value = false
        }
      }, 30000)
    } else {
      ElMessage.error(res.message || '启动爬取失败')
      crawling.value = false
    }
  } catch (error) {
    console.error('Failed to start crawl:', error)
    ElMessage.error('启动爬取失败')
    crawling.value = false
  }
}

// 自动爬取开关切换
const handleAutoCrawlToggle = () => {
  if (autoCrawlEnabled.value) {
    startAutoCrawl()
    ElMessage.success(`已开启自动爬取，每 ${autoCrawlInterval.value} 分钟执行一次`)
  } else {
    stopAutoCrawl()
    ElMessage.info('已关闭自动爬取')
  }
}

// 自动爬取间隔改变
const handleIntervalChange = () => {
  if (autoCrawlEnabled.value) {
    stopAutoCrawl()
    startAutoCrawl()
    ElMessage.success(`自动爬取间隔已更新为 ${autoCrawlInterval.value} 分钟`)
  }
}

// 启动自动爬取
const startAutoCrawl = () => {
  stopAutoCrawl() // 先停止已有的定时器
  const intervalMs = autoCrawlInterval.value * 60 * 1000
  crawlTimer = window.setInterval(() => {
    handleStartCrawl()
  }, intervalMs)
}

// 停止自动爬取
const stopAutoCrawl = () => {
  if (crawlTimer) {
    clearInterval(crawlTimer)
    crawlTimer = null
  }
}

// 关闭爬虫
const handleStopCrawl = () => {
  // 停止当前爬取状态
  crawling.value = false
  
  // 停止自动爬取
  if (autoCrawlEnabled.value) {
    autoCrawlEnabled.value = false
    stopAutoCrawl()
  }
  
  ElMessage.success('爬虫已关闭')
}

const analyzeStock = (row: CrawlerData) => {
  // 如果有股票代码，直接使用股票代码，否则使用股票名称
  const stockParam = row.stock_code || row.stock_name
  router.push({
    path: '/analysis/single',
    query: { stock: stockParam }
  })
}

const parseConcepts = (conceptsStr: string) => {
  if (!conceptsStr) return []
  return conceptsStr.split(',').filter(c => c && c.trim())
}

const getSuccessRateType = (rate: string) => {
  if (!rate) return 'info'
  const val = parseFloat(rate.replace('%', ''))
  if (val >= 80) return 'danger'
  if (val >= 60) return 'warning'
  if (val >= 50) return 'success'
  return 'info'
}

const getIncreaseClass = (increase: string) => {
  if (!increase) return ''
  if (increase.includes('+') || parseFloat(increase) > 0) return 'text-red-500 font-bold'
  if (increase.includes('-') || parseFloat(increase) < 0) return 'text-green-500 font-bold'
  return ''
}

const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchData()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchData()
}

// 组件卸载时清理资源
onUnmounted(() => {
  // 清理定时器
  if (crawlTimer) {
    clearInterval(crawlTimer)
    crawlTimer = null
  }
  
  // 关闭WebSocket连接
  if (ws) {
    try {
      ws.close()
      console.log('[CrawlerAnalysis] WebSocket连接已关闭')
    } catch (error) {
      console.error('[CrawlerAnalysis] 关闭WebSocket连接失败:', error)
    }
    ws = null
  }
})
</script>

<style scoped>
.crawler-analysis {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left {
  display: flex;
  align-items: center;
}
.title {
  font-size: 18px;
  font-weight: bold;
}
.ml-2 {
  margin-left: 8px;
}
.mr-1 {
  margin-right: 4px;
}
.mr-2 {
  margin-right: 8px;
}
.mb-1 {
  margin-bottom: 4px;
}
.concepts-wrapper {
  display: flex;
  flex-wrap: wrap;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.text-red-500 {
  color: #f56c6c;
}
.text-green-500 {
  color: #67c23a;
}
.font-bold {
  font-weight: bold;
}
</style>
