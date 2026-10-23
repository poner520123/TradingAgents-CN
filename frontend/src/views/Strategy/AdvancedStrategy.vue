<template>
  <div class="advanced-strategy">
    <!-- 顶部标题栏 -->
    <header class="strategy-header">
      <div class="header-left">
        <span class="header-icon">✦</span>
        <div class="header-titles">
          <h1 class="header-title">龙头复盘神器</h1>
          <span class="header-subtitle">· 高级策略</span>
        </div>
      </div>
      <div class="header-right">
        <span class="header-tip">⚡ 数据 · 仅供参考</span>
        <el-button type="success" plain :loading="refreshing" @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          <span>全部刷新</span>
        </el-button>
      </div>
    </header>

    <!-- 主体：三块策略 + 右侧说明 -->
    <div class="strategy-body">
      <div class="panel-grid">
        <section
          v-for="(panel, index) in panels"
          :key="panel.key"
          class="strategy-card"
          :class="[`theme-${panel.theme}`, { 'span-rows': index === 0 }]"
        >
          <div class="card-header">
            <h2 class="card-title">
              <span class="card-badge">{{ panel.icon }}</span>
              {{ panel.title }}
            </h2>
            <div class="card-nav">
              <el-button size="small" plain @click="shiftMonth(panel, -1)">◀ 上月</el-button>
              <span class="month-chip">{{ monthChip(panel) }}</span>
              <el-button size="small" plain @click="shiftMonth(panel, 1)">下月 ▶</el-button>
            </div>
          </div>

          <div class="card-body">
            <el-table
              v-loading="panel.loading"
              :data="panel.rows"
              height="100%"
              size="small"
              stripe
              :row-class-name="rowClassName"
              @row-contextmenu="openContextMenu"
            >
              <el-table-column prop="selected_date" label="日期" align="center" min-width="92" />
              <el-table-column prop="code" label="代码" align="center" min-width="80" />
              <el-table-column prop="name" label="名称" align="center" min-width="98" show-overflow-tooltip />
              <el-table-column prop="price" label="当日收盘价" align="center" min-width="98">
                <template #default="{ row }">
                  <span>{{ row.price || '--' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="次日最高价" align="center" min-width="120">
                <template #default="{ row }">
                  <span :class="pctClass(row.highest_pct)">{{ row.highest_price || '--' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="次日收盘价" align="center" min-width="120">
                <template #default="{ row }">
                  <span :class="pctClass(row.closing_pct)">{{ row.closing_price || '--' }}</span>
                </template>
              </el-table-column>
              <template #empty>
                <div class="table-empty">{{ panel.message || '∅ 该月份无数据' }}</div>
              </template>
            </el-table>
          </div>

          <div class="card-footer">
            <span class="footer-label">当前合计</span>
            <div class="footer-values">
              <span class="footer-item">
                <em>次日最高</em>
                <b :class="pillClass(panel.stats?.highest_total ?? null)">
                  {{ formatPct(panel.stats?.highest_total ?? null) }}
                </b>
              </span>
              <span class="footer-item">
                <em>次日收盘</em>
                <b :class="pillClass(panel.stats?.closing_total ?? null)">
                  {{ formatPct(panel.stats?.closing_total ?? null) }}
                </b>
              </span>
            </div>
          </div>
        </section>
      </div>

      <!-- 策略方法说明 -->
      <aside class="desc-panel">
        <div class="desc-header">✦ 策略方法说明</div>
        <div class="desc-body">
          <p class="desc-tip">{{ DESC_TITLE }}</p>
          <el-link type="primary" :href="QR_URL" target="_blank" class="desc-link">⛓ {{ QR_URL }}</el-link>
          <el-divider />
          <p v-for="(para, i) in DESC_PARAGRAPHS" :key="i" class="desc-para">{{ para }}</p>
        </div>
      </aside>
    </div>

    <!-- 底部状态栏 -->
    <footer class="strategy-status">
      <span>{{ statusText }}</span>
      <span class="status-time">{{ lastUpdated }}</span>
    </footer>

    <!-- 行右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="row-context-menu"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      @click.stop
    >
      <div class="menu-title">{{ contextMenu.row?.code }} {{ contextMenu.row?.name }}</div>
      <div class="menu-item" @click="handleAddFavorite">♥ 加入自选</div>
      <div class="menu-item" @click="handleCopyCode">⧉ 复制代码</div>
      <div class="menu-item" @click="handleOpenQuote">⇱ 浏览器打开行情</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getStrategyMonthly } from '@/api/strategy'
import type { StrategyKey, StrategyRow, StrategyStats } from '@/api/strategy'
import { favoritesApi } from '@/api/favorites'

const DESC_TITLE = '✱ 微信扫一扫关注微信公众号，了解策略'
const QR_URL = 'http://weixin.qq.com/r/mp/vRPp8f7EF6NorbqS90av'
const DESC_PARAGRAPHS = [
  '本策略的核心构建逻辑基于多维度专业体系。以多因子权重模型为基础框架，整合量价背离算法、'
  + '动态波动率过滤模块与板块资金流向追踪系统，同时嵌入尾盘量能突变捕捉函数，'
  + '对当日行情数据进行实时校准。',
  '本策略确保信号输出具备稳定性与辨识度，最终在每个交易日14:55左右输出的信号。',
  '郑重声明：以下展示的个股信号，仅为当日策略系统输出结果，“不构成任何投资建议或交易引导”。'
  + '任何策略均无法适用于所有行情阶段，其成功率受市场环境、使用者对本策略逻辑的理解程度、'
  + '实际操作纪律及心态等多重因素影响。信号分享仅用于风格适配性参考与准确性核对，'
  + '投资者据此操作需自行承担全部风险。'
]

interface PanelState {
  key: StrategyKey
  title: string
  icon: string
  theme: 'primary' | 'success' | 'warning'
  month: number
  loading: boolean
  hasData: boolean
  message: string
  rows: StrategyRow[]
  stats: StrategyStats | null
}

const currentMonth = (): number => {
  const now = new Date()
  return now.getFullYear() * 100 + now.getMonth() + 1
}

const createPanel = (
  key: StrategyKey,
  title: string,
  icon: string,
  theme: PanelState['theme']
): PanelState => ({
  key,
  title,
  icon,
  theme,
  month: currentMonth(),
  loading: false,
  hasData: false,
  message: '',
  rows: [],
  stats: null
})

const panels = ref<PanelState[]>([
  createPanel('tcld', '题材轮动策略', '✧', 'primary'),
  createPanel('zb', '飞云主板策略', '◈', 'success'),
  createPanel('cyb', '飞云创业板策略', '◈', 'warning')
])

const refreshing = ref(false)
const statusText = ref('● 数据加载中…')
const lastUpdated = ref('')

const contextMenu = reactive<{ visible: boolean; x: number; y: number; row: StrategyRow | null }>({
  visible: false,
  x: 0,
  y: 0,
  row: null
})

const formatPct = (value: number | null): string => {
  if (value === null || value === undefined) return '--'
  return value >= 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`
}

const pctClass = (value: number | null): string => {
  if (value === null || value === undefined) return ''
  return value >= 0 ? 'pct-up' : 'pct-down'
}

const pillClass = (value: number | null): string => {
  if (value === null || value === undefined) return 'pill-empty'
  return value >= 0 ? 'pill-up' : 'pill-down'
}

const rowClassName = ({ row }: { row: StrategyRow }): string => {
  const value = row.highest_pct
  if (value === null || value === undefined) return ''
  return value >= 0 ? 'row-up' : 'row-down'
}

const monthChip = (panel: PanelState): string => {
  if (panel.loading) return `当前时间数据：${panel.month}  ⟳ 加载中`
  if (!panel.hasData) return `当前时间数据：${panel.month}  ∅`
  return `当前时间数据：${panel.month}  ▤ ${panel.rows.length}条`
}

const shiftMonth = (panel: PanelState, delta: number) => {
  let year = Math.floor(panel.month / 100)
  let month = (panel.month % 100) + delta
  if (month === 0) {
    year -= 1
    month = 12
  } else if (month === 13) {
    year += 1
    month = 1
  }
  panel.month = year * 100 + month
  loadPanel(panel)
}

const loadPanel = async (panel: PanelState) => {
  panel.loading = true
  try {
    const res = await getStrategyMonthly(panel.key, panel.month)
    panel.rows = res?.rows ?? []
    panel.stats = res?.stats ?? null
    panel.hasData = !!res?.has_data
    panel.message = res?.message || (res?.has_data ? '' : '∅ 该月份无数据')
  } catch (error) {
    panel.rows = []
    panel.stats = null
    panel.hasData = false
    panel.message = '数据加载失败，请稍后重试'
  } finally {
    panel.loading = false
  }
}

const refreshAll = async () => {
  refreshing.value = true
  statusText.value = '⟳ 正在刷新全部策略…'
  await Promise.all(panels.value.map(panel => loadPanel(panel)))
  refreshing.value = false
  statusText.value = '⟳ 已刷新'
  lastUpdated.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

const openContextMenu = (row: StrategyRow, _column: unknown, event: MouseEvent) => {
  event.preventDefault()
  contextMenu.row = row
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.visible = true
}

const closeContextMenu = () => {
  contextMenu.visible = false
}

const handleAddFavorite = async () => {
  const row = contextMenu.row
  closeContextMenu()
  if (!row?.code) return
  try {
    await favoritesApi.add({
      symbol: row.code,
      stock_code: row.code,
      stock_name: row.name,
      market: 'A股'
    })
    ElMessage.success(`已加入自选: ${row.code} ${row.name}`)
  } catch (error) {
    ElMessage.error('加入自选失败')
  }
}

const handleCopyCode = async () => {
  const code = contextMenu.row?.code ?? ''
  closeContextMenu()
  if (!code) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(code)
    } else {
      const input = document.createElement('textarea')
      input.value = code
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    ElMessage.success(`已复制 ${code}`)
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handleOpenQuote = () => {
  const code = contextMenu.row?.code ?? ''
  closeContextMenu()
  if (!code) return
  window.open(`https://basic.10jqka.com.cn/${code}`, '_blank')
}

const summary = computed(() => {
  const total = panels.value.reduce((sum, panel) => sum + panel.rows.length, 0)
  return total
})

onMounted(async () => {
  window.addEventListener('click', closeContextMenu)
  window.addEventListener('contextmenu', closeContextMenu)
  await refreshAll()
  statusText.value = `● 共 ${summary.value} 条信号`
})

onUnmounted(() => {
  window.removeEventListener('click', closeContextMenu)
  window.removeEventListener('contextmenu', closeContextMenu)
})
</script>

<style lang="scss" scoped>
.advanced-strategy {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: calc(100vh - 200px);
  min-height: 680px;
}

/* 顶部标题栏 */
.strategy-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-radius: 10px;
  background: linear-gradient(120deg, #2b6cb0 0%, #409eff 55%, #67c23a 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.25);

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-icon {
    font-size: 22px;
  }

  .header-titles {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .header-title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
  }

  .header-subtitle {
    font-size: 14px;
    opacity: 0.9;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .header-tip {
    font-size: 13px;
    opacity: 0.95;
  }
}

/* 主体布局 */
.strategy-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 320px);
  gap: 14px;
}

.panel-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px;
  min-height: 0;
}

/* 策略卡片 */
.strategy-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;

  &.span-rows {
    grid-row: span 2;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 12px;
    border-bottom: 1px solid #f0f2f5;
    flex-wrap: wrap;
  }

  .card-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .card-badge {
    font-size: 15px;
  }

  .card-nav {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .month-chip {
    padding: 4px 12px;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 600;
    color: #fff;
    background: #409eff;
    white-space: nowrap;
  }

  &.theme-success .month-chip {
    background: #67c23a;
  }

  &.theme-warning .month-chip {
    background: #e6a23c;
  }

  .card-body {
    flex: 1;
    min-height: 0;
    position: relative;
    padding: 0 6px;
  }

  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 8px 12px;
    border-top: 1px solid #f0f2f5;
    background: #fafafa;
  }

  .footer-label {
    font-size: 13px;
    font-weight: 700;
    color: #303133;
  }

  .footer-values {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .footer-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #606266;

    em {
      font-style: normal;
    }

    b {
      display: inline-block;
      min-width: 78px;
      text-align: center;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 700;
      color: #fff;
      background: #909399;
    }
  }
}

.pill-up {
  background: #e2484a !important;
}

.pill-down {
  background: #1aa15c !important;
}

.pill-empty {
  background: #c0c4cc !important;
}

.table-empty {
  padding: 18px 0;
  color: #909399;
  font-size: 13px;
}

:deep(.pct-up) {
  color: #e2484a;
  font-weight: 600;
}

:deep(.pct-down) {
  color: #1aa15c;
  font-weight: 600;
}

:deep(.row-up) {
  background: rgba(226, 72, 74, 0.04);
}

:deep(.row-down) {
  background: rgba(26, 161, 92, 0.04);
}

/* 右侧说明面板 */
.desc-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;

  .desc-header {
    padding: 10px 14px;
    font-size: 15px;
    font-weight: 600;
    color: #2b6cb0;
    border-bottom: 1px solid #f0f2f5;
    background: linear-gradient(90deg, #ecf5ff 0%, #fff 100%);
  }

  .desc-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 12px 14px;
  }

  .desc-tip {
    margin: 0 0 8px;
    font-size: 13px;
    font-weight: 600;
    color: #e2484a;
  }

  .desc-link {
    font-size: 12px;
    word-break: break-all;
  }

  .desc-para {
    margin: 0 0 12px;
    font-size: 13px;
    line-height: 1.9;
    color: #3b4252;
    text-align: justify;
    text-indent: 2em;
  }
}

/* 底部状态栏 */
.strategy-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-radius: 6px;
  background: #606266;
  color: #fff;
  font-size: 13px;
}

.status-time {
  opacity: 0.85;
}

/* 右键菜单 */
.row-context-menu {
  position: fixed;
  z-index: 3000;
  min-width: 180px;
  padding: 6px 0;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);

  .menu-title {
    padding: 4px 14px 8px;
    font-size: 12px;
    color: #909399;
    border-bottom: 1px solid #f0f2f5;
  }

  .menu-item {
    padding: 8px 14px;
    font-size: 13px;
    color: #303133;
    cursor: pointer;

    &:hover {
      background: #ecf5ff;
      color: #409eff;
    }
  }
}

/* 响应式 */
@media (max-width: 1200px) {
  .advanced-strategy {
    height: auto;
    min-height: 0;
  }

  .strategy-body {
    grid-template-columns: minmax(0, 1fr);
  }

  .panel-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: none;
  }

  .strategy-card {
    height: 460px;

    &.span-rows {
      grid-row: auto;
    }
  }

  .desc-panel {
    height: 320px;
  }
}
</style>
