<template>
  <div class="cross-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
          <span class="title">达人热点</span>
          <el-tag type="info" class="ml-2">178448.com</el-tag>
        </div>
        </div>
      </template>

      <!-- 交叉分析数据列表 -->
      <el-table :data="tableData" style="width: 100%" v-loading="loading" border stripe>
        <el-table-column prop="expert_name" label="达人名称" width="120" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.expert_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="股票代码" width="90" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="股票名称" width="90" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="success_rate" label="成功率" width="90" sortable>
          <template #default="scope">
            <el-tag :type="getSuccessRateType(scope.row.success_rate)">
              {{ scope.row.success_rate }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="success_count" label="分析数" width="80" sortable>
          <template #default="scope">
            <span class="font-bold" :class="{ 'text-red-500': scope.row.success_count > 0 }">
              {{ scope.row.success_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="analysis_time" label="分析时间" width="160" sortable />
        <el-table-column prop="analysis_reason" label="分析理由" min-width="250" show-overflow-tooltip />
        <el-table-column prop="analysis_price" label="分析价格" width="100">
          <template #default="scope">
            <span :class="{ 'text-red-500': parseFloat(scope.row.analysis_price) > 0 }">
              {{ scope.row.analysis_price }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="popularity_rank" label="人气" width="80" align="center">
          <template #default="scope">
            <span :class="{ 'text-red-500': scope.row.popularity_rank > 0 }">
              {{ scope.row.popularity_rank || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="capital_flow_rank" label="资金" width="80" align="center">
          <template #default="scope">
            <span :class="{ 'text-red-500': scope.row.capital_flow_rank > 0 }">
              {{ scope.row.capital_flow_rank || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Plus } from '@element-plus/icons-vue'
import { getCrossAnalysisData, type CrossAnalysisItem } from '@/api/astock'
import { favoritesApi } from '@/api/favorites'

const router = useRouter()
const loading = ref(false)
const tableData = ref<CrossAnalysisItem[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(async () => {
  await fetchData()
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getCrossAnalysisData(currentPage.value, pageSize.value)
    if (res.success) {
      tableData.value = res.data
      total.value = res.total
    }
  } catch (error) {
    console.error('Failed to fetch cross analysis data:', error)
    ElMessage.error('获取交叉分析数据失败')
  } finally {
    loading.value = false
  }
}

const analyzeStock = (row: CrossAnalysisItem) => {
  // 使用股票代码进行分析
  router.push({
    path: '/analysis/single',
    query: { stock: row.code }
  })
}

const addToFavorites = async (row: CrossAnalysisItem) => {
  if (!row.name) {
    ElMessage.warning('股票名称无效')
    return
  }

  try {
    const res = await favoritesApi.add({
      stock_name: row.name,
      symbol: row.code,
      stock_code: row.code // 兼容字段
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

const getSuccessRateType = (rate: number) => {
  if (rate >= 80) return 'danger'
  if (rate >= 60) return 'warning'
  if (rate >= 50) return 'success'
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
</script>

<style scoped>
.cross-analysis {
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
.font-bold {
  font-weight: bold;
}
</style>