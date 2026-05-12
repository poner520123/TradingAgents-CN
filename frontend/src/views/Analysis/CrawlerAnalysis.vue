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
          <el-button 
            type="info" 
            size="default" 
            disabled
          >
            自动爬取中 (每5分钟)
          </el-button>
        </div>
        </div>
      </template>

      <!-- 筛选条件表单 -->
      <div class="filter-form" style="margin-bottom: 20px;">
        <el-form :inline="true" :model="filterForm" class="filter-form">
          <el-form-item label="伏击人">
            <el-select 
              v-model="filterForm.user_name" 
              placeholder="请选择伏击人" 
              clearable
              filterable
              style="width: 200px;"
            >
              <el-option
                v-for="user in topUsers"
                :key="user.user_name"
                :label="`${user.user_name} (${user.success_rate}, ${user.record_count}条)`"
                :value="user.user_name"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="成功率">
            <el-input-number 
              v-model="filterForm.min_success_rate" 
              :min="0" 
              :max="100" 
              :step="5"
              placeholder="最低成功率"
              style="width: 120px;"
            />
          </el-form-item>
          <el-form-item label="伏击理由">
            <el-input v-model="filterForm.reason" placeholder="请输入伏击理由" clearable />
          </el-form-item>
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="filterForm.date_range"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              default-time="00:00:00"
              style="width: 240px;"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleFilter">筛选</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

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
        
        <el-table-column prop="reason" label="伏击理由" min-width="200" show-overflow-tooltip />
        <el-table-column prop="time" label="发布时间" width="160" sortable />
        <el-table-column prop="price" label="伏击价" width="100" />

        
        <el-table-column label="AI分析" width="120" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" plain @click="analyzeStock(scope.row)">
              <el-icon><DataAnalysis /></el-icon>
            </el-button>
            <el-button size="small" type="success" plain @click="addToFavorites(scope.row)" title="加入自选">
              <el-icon><Plus /></el-icon>
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

    <!-- 爬虫状态悬浮框 -->
    <div v-if="crawlerStatus.visible" class="crawler-status-float" :class="{ 'completed': crawlerStatus.finished }">
      <div class="status-header">
        <el-icon v-if="!crawlerStatus.finished" class="is-loading"><Loading /></el-icon>
        <el-icon v-else class="success-icon"><CircleCheckFilled /></el-icon>
        <span class="status-title">{{ crawlerStatus.title }}</span>
        <el-icon class="close-icon" @click="closeCrawlerStatus"><Close /></el-icon>
      </div>
      <div class="status-content">
        <p class="current-action">{{ crawlerStatus.currentAction }}</p>
        <div class="progress-bar" v-if="crawlerStatus.total > 0">
           <el-progress 
            :percentage="crawlerStatus.percentage" 
            :status="crawlerStatus.finished ? 'success' : ''"
            :stroke-width="6"
            :show-text="false"
          />
          <span class="progress-text">{{ crawlerStatus.current }}/{{ crawlerStatus.total }}</span>
        </div>
        <div class="log-container" ref="logContainer">
          <div v-for="(log, index) in crawlerLogs" :key="index" class="log-item">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-msg">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Plus, Loading, Close, CircleCheckFilled } from '@element-plus/icons-vue'
import { getCrawlerData, startCrawl, getTopUsers, type CrawlerData, type TopUser } from '@/api/crawler'
import { favoritesApi } from '@/api/favorites'
import { getStockCodeByName, loadStockNameCodeMap, getStockCodesByNames } from '@/utils/stockNameCodeMap'
import { useNotificationStore } from '@/stores/notifications'
import { formatDateTime } from '@/utils/datetime'

const router = useRouter()
const loading = ref(false)
const tableData = ref<CrawlerData[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 筛选表单数据
const filterForm = ref({
  user_name: '',
  min_success_rate: null,
  reason: '',
  date_range: null as [Date, Date] | null
})

// 爬虫状态管理
interface CrawlerStatus {
  visible: boolean
  title: string
  currentAction: string
  current: number
  total: number
  percentage: number
  finished: boolean
}

const crawlerStatus = ref<CrawlerStatus>({
  visible: false,
  title: '爬虫任务',
  currentAction: '准备中...',
  current: 0,
  total: 0,
  percentage: 0,
  finished: false
})

interface LogItem {
  time: string
  message: string
}

const crawlerLogs = ref<LogItem[]>([])
const logContainer = ref<HTMLElement | null>(null)

// 顶级用户列表
const topUsers = ref<TopUser[]>([])
const loadingTopUsers = ref(false)

// 页面加载时初始化股票名称到代码的映射
onMounted(async () => {
  await loadStockNameCodeMap()
  await fetchTopUsers()
  await fetchData()
})

const fetchTopUsers = async () => {
  loadingTopUsers.value = true
  try {
    const res = await getTopUsers(30)
    if (res.success) {
      topUsers.value = res.data
    }
  } catch (error) {
    console.error('Failed to fetch top users:', error)
  } finally {
    loadingTopUsers.value = false
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    // 构建筛选参数
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      user_name: filterForm.value.user_name,
      min_success_rate: filterForm.value.min_success_rate,
      reason: filterForm.value.reason
    }

    // 添加日期范围筛选
    if (filterForm.value.date_range) {
      params.start_date = filterForm.value.date_range[0].toISOString().split('T')[0]
      params.end_date = filterForm.value.date_range[1].toISOString().split('T')[0]
    }

    const res = await getCrawlerData(params)
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



const analyzeStock = (row: CrawlerData) => {
  // 如果有股票代码，直接使用股票代码，否则使用股票名称
  const stockParam = row.stock_code || row.stock_name
  router.push({
    path: '/analysis/single',
    query: { stock: stockParam }
  })
}

const addToFavorites = async (row: CrawlerData) => {
  if (!row.stock_name) {
    ElMessage.warning('股票名称无效')
    return
  }

  try {
    const res = await favoritesApi.add({
      stock_name: row.stock_name,
      symbol: row.stock_code,
      stock_code: row.stock_code // 兼容字段
    })
    
    ElMessage.success(res.message || '已添加到自选股')
  } catch (error: any) {
    console.error('Failed to add favorite:', error)
    // 如果是重复添加，通常API会返回特定错误，这里简单处理
    const msg = error.response?.data?.detail || error.message || '添加自选股失败'
    if (msg.includes('duplicate') || msg.includes('exists')) {
      ElMessage.warning('该股票已在自选股中')
    } else {
      ElMessage.error(msg)
    }
  }
}

const getSuccessRateType = (rate: string) => {
  if (!rate) return 'info'
  const val = parseFloat(rate.replace('%', ''))
  if (val >= 80) return 'danger'
  if (val >= 60) return 'warning'
  if (val >= 50) return 'success'
  return 'info'
}



const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchData()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchData()
}

// 处理进度更新
const handleProgressUpdate = (notification: any) => {
  if (!crawlerStatus.value.visible) {
    crawlerStatus.value.visible = true
    crawlerStatus.value.finished = false
    crawlerStatus.value.percentage = 0
    crawling.value = true
  }
  
  const data = notification.data || {}
  crawlerStatus.value.currentAction = notification.content
  
  if (data.page && data.total_pages) {
    crawlerStatus.value.current = data.page
    crawlerStatus.value.total = data.total_pages
    crawlerStatus.value.percentage = Math.floor((data.current_step / data.total_pages) * 100)
  }
  
  addLog(notification.content)
}

// 处理爬虫完成
const handleCrawlerCompleted = (notification: any) => {
  crawlerStatus.value.currentAction = '爬取完成'
  crawlerStatus.value.percentage = 100
  crawlerStatus.value.finished = true
  crawling.value = false
  
  addLog(notification.content)
  
  // 刷新数据
  fetchData()
  
  // 3秒后自动关闭状态框，除非用户鼠标悬停（暂未实现悬停保持）
  setTimeout(() => {
    // crawlerStatus.value.visible = false
  }, 5000)
}

const addLog = (msg: string) => {
  const time = new Date().toLocaleTimeString()
  crawlerLogs.value.unshift({ time, message: msg })
  // 只保留最近5条日志
  if (crawlerLogs.value.length > 5) {
    crawlerLogs.value.pop()
  }
}

const handleFilter = () => {
  // 重置页码到第一页
  currentPage.value = 1
  fetchData()
}

const resetFilter = () => {
  // 重置筛选表单
  filterForm.value = {
    user_name: '',
    min_success_rate: null,
    reason: '',
    date_range: null
  }
  // 重置页码到第一页
  currentPage.value = 1
  fetchData()
}

const closeCrawlerStatus = () => {
  crawlerStatus.value.visible = false
}

// 组件卸载时清理资源
onUnmounted(() => {
  // 清理轮询定时器
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
  }
})

// 轮询定时器
const pollingTimer = ref<number | null>(null)

// 开始轮询检查数据更新
const startPolling = () => {
  // 每5分钟检查一次数据更新
  pollingTimer.value = window.setInterval(async () => {
    console.log('🔄 检查数据更新...')
    // 只在当前页面是第一页时才自动刷新
    if (currentPage.value === 1) {
      await fetchData()
    }
  }, 5 * 60 * 1000) // 5分钟
  console.log('✅ 开始自动数据更新检查 (每5分钟)')
}

// 页面加载时启动轮询
onMounted(async () => {
  await loadStockNameCodeMap()
  await fetchTopUsers()
  await fetchData()
  startPolling()
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
.text-green-500 {
  color: #67c23a;
}
.font-bold {
  font-weight: bold;
}

/* 爬虫状态悬浮框样式 */
.crawler-status-float {
  position: fixed;
  top: 80px;
  right: 20px;
  width: 320px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 2000;
  border: 1px solid var(--el-border-color-lighter);
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &.completed {
    border-color: var(--el-color-success-light-5);
    background: rgba(240, 249, 235, 0.95);
  }

  .status-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--el-fill-color-light);

    .status-title {
      font-weight: 600;
      color: var(--el-text-color-primary);
      flex: 1;
      margin-left: 8px;
    }

    .is-loading {
      color: var(--el-color-primary);
      animation: rotate 1.5s linear infinite;
    }
    
    .success-icon {
      color: var(--el-color-success);
      font-size: 18px;
    }

    .close-icon {
      cursor: pointer;
      color: var(--el-text-color-secondary);
      transition: color 0.2s;
      
      &:hover {
        color: var(--el-color-danger);
      }
    }
  }

  .status-content {
    padding: 16px;

    .current-action {
      margin: 0 0 12px 0;
      font-size: 14px;
      color: var(--el-text-color-primary);
      font-weight: 500;
    }

    .progress-bar {
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      
      .el-progress {
        flex: 1;
      }
      
      .progress-text {
        font-size: 12px;
        color: var(--el-text-color-secondary);
        width: 40px;
        text-align: right;
      }
    }

    .log-container {
      background: var(--el-fill-color-lighter);
      border-radius: 6px;
      padding: 8px;
      max-height: 120px;
      overflow-y: auto;
      
      .log-item {
        display: flex;
        gap: 8px;
        font-size: 12px;
        line-height: 1.6;
        margin-bottom: 4px;
        
        &:last-child {
          margin-bottom: 0;
        }

        .log-time {
          color: var(--el-text-color-placeholder);
          white-space: nowrap;
        }
        
        .log-msg {
          color: var(--el-text-color-regular);
        }
      }
    }
  }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
