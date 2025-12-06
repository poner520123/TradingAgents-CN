<template>
  <div class="crawler-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">爬虫分析</span>
            <el-tag type="info" class="ml-2">178448.com</el-tag>
          </div>
          <div class="header-right">
            <el-input-number v-model="crawlPages" :min="1" :max="10" size="default" class="mr-2" />
            <el-button type="primary" :loading="crawling" @click="handleStartCrawl">
              {{ crawling ? '爬取中...' : '开始爬取' }}
            </el-button>
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
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" plain @click="analyzeStock(scope.row)">
              <el-icon class="mr-1"><DataAnalysis /></el-icon>智能分析
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis } from '@element-plus/icons-vue'
import { getCrawlerData, startCrawl, type CrawlerData } from '@/api/crawler'
import { getStockCodeByName, loadStockNameCodeMap } from '@/utils/stockNameCodeMap'

const router = useRouter()
const loading = ref(false)
const crawling = ref(false)
const tableData = ref<CrawlerData[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const crawlPages = ref(1)

// 页面加载时初始化股票名称到代码的映射
onMounted(async () => {
  await loadStockNameCodeMap()
  await fetchData()
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getCrawlerData(currentPage.value, pageSize.value)
    if (res.success) {
      tableData.value = res.data
      total.value = res.total
      // 为每个股票获取股票代码
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
  // 遍历所有股票数据，为没有股票代码的股票获取代码
  for (const item of tableData.value) {
    if (!item.stock_code) {
      try {
        // 从本地映射中获取股票代码
        const code = await getStockCodeByName(item.stock_name)
        if (code) {
          item.stock_code = code
        }
      } catch (error) {
        console.error(`Failed to get stock code for ${item.stock_name}:`, error)
      }
    }
  }
}

const handleStartCrawl = async () => {
  crawling.value = true
  try {
    const res = await startCrawl(crawlPages.value)
    if (res.success) {
      ElMessage.success(`开始爬取前 ${crawlPages.value} 页数据，请稍后刷新查看`)
      // Refresh after a short delay to see initial results
      setTimeout(() => {
        fetchData()
      }, 2000)
    } else {
      ElMessage.error(res.message || '启动爬取失败')
    }
  } catch (error) {
    console.error('Failed to start crawl:', error)
    ElMessage.error('启动爬取失败')
  } finally {
    crawling.value = false
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

onMounted(() => {
  fetchData()
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
