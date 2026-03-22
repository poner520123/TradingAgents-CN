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
        :class="{ 'limit-up': stock.limit_up === '1' || parseFloat(stock.increase.replace('%', '')) >= 9.0 }"
        @click="goToStockAnalysis(stock)"
      >
        <div class="stock-info">
          <div class="stock-name">
            {{ stock.stock_name }}
            <span v-if="stock.limit_up === '1' || parseFloat(stock.increase.replace('%', '')) >= 9.0" class="limit-up-badge">
              <el-icon><Top /></el-icon>
              涨停
            </span>
          </div>
          <div class="stock-code">{{ stock.stock_code || '未知' }}</div>
        </div>
        <div class="stock-details">
          <div class="stock-increase" :class="{ 'increase-up': parseFloat(stock.increase.replace('%', '')) > 0 }">
            {{ stock.increase }}
          </div>
          <div class="stock-reason">{{ stock.reason || '无' }}</div>
        </div>
        <div class="stock-time">
          {{ formatTime(stock.crawled_at || stock.time) }}
        </div>
        
        <!-- 悬浮添加按钮 -->
        <div class="hover-add-btn" @click.stop="addToFavorites(stock)">
          <el-button type="primary" size="small" circle>
            <el-icon><Plus /></el-icon>
          </el-button>
          <span class="add-text">加自选</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Plus, Top } from '@element-plus/icons-vue'
import { getCrawlerData, type CrawlerData } from '@/api/crawler'
import { favoritesApi } from '@/api/favorites'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()

// 配置项
const REFRESH_INTERVAL = 5 * 60 * 1000 // 5分钟
const MAX_STOCKS = 50 // 从最新50条中选择
const DISPLAY_COUNT = 10 // 显示10条

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
      let stocks = response.data
      // 按时间倒序排序（最新的在前）
      stocks.sort((a, b) => {
        const timeA = new Date(a.crawled_at || a.time).getTime()
        const timeB = new Date(b.crawled_at || b.time).getTime()
        return timeB - timeA
      })
      
      // 去重逻辑：根据股票代码或股票名称去重
      const uniqueStocks = new Map<string, CrawlerData>()
      for (const stock of stocks) {
        // 使用股票代码作为主键，如果没有则使用股票名称
        const key = stock.stock_code || stock.stock_name
        if (key && !uniqueStocks.has(key)) {
          uniqueStocks.set(key, stock)
        }
      }
      
      // 将Map转换为数组
      const uniqueStocksArray = Array.from(uniqueStocks.values())
      
      // 随机选择DISPLAY_COUNT个股票
      const selected = getRandomElements(uniqueStocksArray, DISPLAY_COUNT)
      // 然后按时间倒序排序，确保显示时从左到右从上到下时间由近到远排列
      randomStocks.value = selected.sort((a, b) => {
        const timeA = new Date(a.crawled_at || a.time).getTime()
        const timeB = new Date(b.crawled_at || b.time).getTime()
        return timeB - timeA
      })
      
      // 更新allStocks为去重后的数据
      allStocks.value = uniqueStocksArray
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

// 添加到自选股
const addToFavorites = async (stock: CrawlerData) => {
  if (!stock.stock_name) {
    ElMessage.warning('股票名称无效')
    return
  }
  
  try {
    const res = await favoritesApi.add({
      stock_name: stock.stock_name,
      symbol: stock.stock_code,
      stock_code: stock.stock_code
    })
    ElMessage.success(res.message || '已添加到自选股')
  } catch (error: any) {
    console.error('Failed to add favorite:', error)
    const msg = error.response?.data?.detail || error.message || '添加自选股失败'
    if (msg.includes('duplicate') || msg.includes('exists')) {
      ElMessage.warning('该股票已在自选股中')
    } else {
      ElMessage.error(msg)
    }
  }
}

// 设置自动刷新

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
    position: relative;

    &:hover {
      border-color: var(--el-color-primary);
      background-color: var(--el-color-primary-light-9);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    &.limit-up {
      border-color: #f56c6c;
      background-color: rgba(245, 108, 108, 0.05);

      .stock-name {
        color: #f56c6c;
      }
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
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .limit-up-badge {
        background-color: #f56c6c;
        color: white;
        padding: 2px 6px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 2px;
      }

      .stock-code {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }

    .stock-details {
      margin-bottom: 8px;
    }

    .stock-increase {
      font-size: 13px;
      font-weight: 500;
      color: var(--el-text-color-regular);
      margin-bottom: 4px;

      &.increase-up {
        color: #f56c6c;
      }
    }

    .stock-reason {
      font-size: 12px;
      color: var(--el-text-color-placeholder);
      line-height: 1.4;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }

    .stock-time {
      font-size: 11px;
      color: var(--el-text-color-placeholder);
    }

    .hover-add-btn {
      position: absolute;
      top: 8px;
      right: 8px;
      display: flex;
      align-items: center;
      gap: 4px;
      opacity: 0;
      transition: opacity 0.3s ease;
      background: rgba(255, 255, 255, 0.9);
      padding: 2px 6px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

      .add-text {
        font-size: 12px;
        color: var(--el-color-primary);
        font-weight: 500;
      }
    }

    &:hover .hover-add-btn {
      opacity: 1;
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