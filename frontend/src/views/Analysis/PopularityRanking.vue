<template>
  <div class="popularity-ranking">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">人气排行榜</span>
            <el-tag type="info" class="ml-2">eastmoney.com</el-tag>
          </div>
        </div>
      </template>

      <!-- 人气排行榜数据列表 -->
      <el-table :data="tableData" style="width: 100%" v-loading="loading" border stripe>
        <el-table-column prop="rank" label="排名" width="80" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.rank }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="股票代码" width="120" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="股票名称" width="120" fixed>
          <template #default="scope">
            <span class="font-bold">{{ scope.row.name }}</span>
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
import { DataAnalysis, Plus, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { getPopularityData, type PopularityItem } from '@/api/astock'
import { favoritesApi } from '@/api/favorites'

const router = useRouter()
const loading = ref(false)
const tableData = ref<PopularityItem[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(async () => {
  await fetchData()
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getPopularityData(currentPage.value, pageSize.value)
    if (res.success) {
      tableData.value = res.data
      total.value = res.count
    }
  } catch (error) {
    console.error('Failed to fetch popularity data:', error)
    ElMessage.error('获取人气排行榜数据失败')
  } finally {
    loading.value = false
  }
}

const analyzeStock = (row: PopularityItem) => {
  // 使用股票代码进行分析
  router.push({
    path: '/analysis/single',
    query: { stock: row.code }
  })
}

const addToFavorites = async (row: PopularityItem) => {
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
.popularity-ranking {
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