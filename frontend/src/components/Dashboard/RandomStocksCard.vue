<template>
  <el-card class="random-stocks-card">
    <template #header>
      <div class="card-header">
        <h3>📈 达人热点</h3>
        <div class="refresh-info">
          <el-button type="text" size="small" @click="refreshStocks" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <span class="refresh-time">
            下次刷新: {{ nextRefreshTime }}
          </span>
        </div>
      </div>
    </template>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="15" animated />
    </div>

    <div v-else-if="randomStocks.length === 0" class="empty-state">
      <el-empty description="暂无股票数据" :image-size="60">
        <el-button type="primary" size="small" @click="refreshStocks">
          刷新数据
        </el-button>
      </el-empty>
    </div>

    <div v-else class="stocks-grid">
      <div
        v-for="stock in randomStocks"
        :key="stock.stock_code || stock.stock_name"
        class="stock-item"
        @click="goToStockAnalysis(stock)"
      >
        <div class="stock-info">
          <div class="stock-name">{{ stock.stock_name }}</div>
          <div class="stock-code">{{ stock.stock_code || '未知' }}</div>
        </div>
        <div class="stock-time">
          {{ formatTime(stock.crawled_at || stock.time) }}
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { getCrawlerData, type CrawlerData } from '@/api/crawler'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()

// 配置项
const REFRESH_INTERVAL = 5 * 60 * 1000 // 5分钟
const MAX_STOCKS = 100 // 从最新100条中选择
const DISPLAY_COUNT = 15 // 显示15条

// 响应式数据
const loading = ref(true)
const refreshing = ref(false)
const allStocks = ref<CrawlerData[]>([])
const randomStocks = ref<CrawlerData[]>([])
const refreshTimer = ref<number | null>(null)
const lastRefreshTime = ref<Date>(new Date())

// 计算下次刷新时间
const nextRefreshTime = computed(() => {
  const nextTime = new Date(lastRefreshTime.value.getTime() + REFRESH_INTERVAL)
  return nextTime.toLocaleTimeString()
})

// 格式化时间
const formatTime = (time: string) => {
  return formatDateTime(time)
}

// 从数组中随机选择n个元素
const getRandomElements = <T>(arr: T[], count: number): T[] => {
  if (arr.length <= count) return [...arr]
  
  const shuffled = [...arr].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
}

// 加载爬虫数据
const loadCrawlerData = async () => {
  try {
    loading.value = true
    const response = await getCrawlerData(1, MAX_STOCKS)
    
    if (response.success && response.data) {
      allStocks.value = response.data
      // 按时间倒序排序（最新的在前）
      allStocks.value.sort((a, b) => {
        const timeA = new Date(a.crawled_at || a.time).getTime()
        const timeB = new Date(b.crawled_at || b.time).getTime()
        return timeB - timeA
      })
      
      // 随机选择15个股票
      const selected = getRandomElements(allStocks.value, DISPLAY_COUNT)
      // 然后按时间倒序排序，确保显示时从左到右从上到下时间由近到远排列
      randomStocks.value = selected.sort((a, b) => {
        const timeA = new Date(a.crawled_at || a.time).getTime()
        const timeB = new Date(b.crawled_at || b.time).getTime()
        return timeB - timeA
      })
    }
  } catch (error) {
    console.error('加载爬虫数据失败:', error)
  } finally {
    loading.value = false
    refreshing.value = false
    lastRefreshTime.value = new Date()
  }
}

// 刷新股票数据
const refreshStocks = () => {
  refreshing.value = true
  loadCrawlerData()
}

// 跳转到股票分析页面
const goToStockAnalysis = (stock: CrawlerData) => {
  // 如果有股票代码，直接使用股票代码，否则使用股票名称
  const stockParam = stock.stock_code || stock.stock_name
  router.push({
    path: '/analysis/single',
    query: { 
      stock: stockParam,
      level: '1' // 默认1级快速分析
    }
  })
}

// 设置自动刷新
const setupAutoRefresh = () => {
  refreshTimer.value = window.setInterval(() => {
    loadCrawlerData()
  }, REFRESH_INTERVAL)
}

// 生命周期
onMounted(() => {
  loadCrawlerData()
  setupAutoRefresh()
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})
</script>

<style lang="scss" scoped>
.random-stocks-card {
  margin-bottom: 24px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0;

    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .refresh-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .refresh-time {
        font-size: 12px;
        color: var(--el-text-color-placeholder);
      }
    }
  }

  .loading-state {
    padding: 16px 0;
  }

  .empty-state {
    text-align: center;
    padding: 40px 0;
  }

  .stocks-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
    margin-top: 16px;
  }

  .stock-item {
    padding: 16px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    background-color: var(--el-fill-color-blank);

    &:hover {
      border-color: var(--el-color-primary);
      background-color: var(--el-color-primary-light-9);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .stock-info {
      margin-bottom: 8px;

      .stock-name {
        font-size: 15px;
        font-weight: 600;
        color: var(--el-text-color-primary);
        margin-bottom: 4px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .stock-code {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }

    .stock-time {
      font-size: 11px;
      color: var(--el-text-color-placeholder);
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .random-stocks-card {
    .stocks-grid {
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 10px;
    }

    .stock-item {
      padding: 12px;

      .stock-name {
        font-size: 14px;
      }
    }
  }
}
</style>