<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { ElMessage } from 'element-plus'
import { analyticsApi, type AnalyticsQuery } from '@/api/analytics'
import type {
  AnalyticsDistribution,
  AnalyticsHeatmap,
  AnalyticsOverview,
  AnalyticsPeriod,
  AnalyticsTrends,
} from '@/types/analytics'

const period = ref<Exclude<AnalyticsPeriod, 'today'>>('7d')
const lineId = ref('')
const customRange = ref<Date[]>([])
const autoRefresh = ref(true)
const fullscreen = ref(false)
const loading = ref(false)
const overview = ref<AnalyticsOverview | null>(null)
const trends = ref<AnalyticsTrends>({ granularity: 'day', start: '', end: '', items: [] })
const distribution = ref<AnalyticsDistribution>({ start: '', end: '', total_defects: 0, items: [] })
const heatmap = ref<AnalyticsHeatmap>({ start: '', end: '', angle_bin_degrees: 10, axial_bin_count: 10, coordinate_basis: 'normalized_bbox_center', items: [] })
const barElement = ref<HTMLDivElement>()
const trendElement = ref<HTMLDivElement>()
const heatmapElement = ref<HTMLDivElement>()
const pieElement = ref<HTMLDivElement>()
const charts: ECharts[] = []
let refreshTimer: ReturnType<typeof globalThis.setInterval> | undefined

function selectedQuery(): AnalyticsQuery {
  return {
    period: period.value,
    start_time: period.value === 'custom' ? customRange.value[0]?.toISOString() : undefined,
    end_time: period.value === 'custom' ? customRange.value[1]?.toISOString() : undefined,
    line_id: lineId.value || undefined,
  }
}

function dateLabel(value: string): string {
  return value ? new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) : ''
}

function initChart(element: HTMLDivElement | undefined): ECharts | null {
  if (!element) return null
  const chart = echarts.init(element)
  charts.push(chart)
  return chart
}

function renderCharts(): void {
  charts.splice(0).forEach((chart) => chart.dispose())
  const labels = trends.value.items.map((item) => dateLabel(item.bucket_start))
  const bar = initChart(barElement.value)
  bar?.setOption({
    tooltip: { trigger: 'axis' }, legend: { data: ['划痕', '点蚀'] }, xAxis: { type: 'category', data: labels }, yAxis: { type: 'value' },
    series: [
      { name: '划痕', type: 'bar', data: trends.value.items.map((item) => item.scratch_count) },
      { name: '点蚀', type: 'bar', data: trends.value.items.map((item) => item.pitted_surface_count) },
    ],
  })
  const trend = initChart(trendElement.value)
  trend?.setOption({
    tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: labels }, yAxis: { type: 'value', name: '缺陷率 %' },
    series: [{ name: '缺陷率', type: 'line', smooth: true, data: trends.value.items.map((item) => item.defect_rate) }],
  })
  const heat = initChart(heatmapElement.value)
  heat?.setOption({
    tooltip: { position: 'top' }, xAxis: { type: 'category', name: '圆周角度', data: Array.from({ length: 36 }, (_, index) => `${index * 10}°`) },
    yAxis: { type: 'category', name: '轴向分区', data: Array.from({ length: 10 }, (_, index) => String(index + 1)) },
    visualMap: { min: 0, max: Math.max(1, ...heatmap.value.items.map((item) => item.count)), calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{ type: 'heatmap', data: heatmap.value.items.map((item) => [item.angle_bucket, item.axial_bucket, item.count]) }],
  })
  const pie = initChart(pieElement.value)
  pie?.setOption({
    tooltip: { trigger: 'item' }, legend: { bottom: 0 },
    series: [{ type: 'pie', radius: '62%', data: distribution.value.items.map((item) => ({ name: `${item.type === 'scratch' ? '划痕' : '点蚀'}·${item.level === 'minor' ? '轻微' : '严重'}`, value: item.count })) }],
  })
}

async function load(): Promise<void> {
  if (period.value === 'custom' && customRange.value.length !== 2) {
    ElMessage.warning('请选择完整的自定义时间范围')
    return
  }
  loading.value = true
  try {
    const query = selectedQuery()
    const [card, trend, pie, heat] = await Promise.all([
      analyticsApi.overview({ ...query, period: 'today' }), analyticsApi.trends(query), analyticsApi.distribution(query), analyticsApi.heatmap(query),
    ])
    overview.value = card
    trends.value = trend
    distribution.value = pie
    heatmap.value = heat
    await nextTick()
    renderCharts()
  } finally { loading.value = false }
}

function setPeriod(next: Exclude<AnalyticsPeriod, 'today'>): void {
  period.value = next
  if (next !== 'custom') void load()
}

function exportCsv(): void {
  const title = '日期,检测总数,NG数量,缺陷检出率(%),划痕,点蚀'
  const rows = trends.value.items.map((item) => [dateLabel(item.bucket_start), item.total_detections, item.ng_detections, item.defect_rate, item.scratch_count, item.pitted_surface_count].join(','))
  const blob = new Blob([`\uFEFF${[title, ...rows].join('\n')}`], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `缺陷统计_${period.value}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

function resizeCharts(): void { charts.forEach((chart) => chart.resize()) }

function refreshClock(): void {
  if (refreshTimer) globalThis.clearInterval(refreshTimer)
  if (autoRefresh.value) refreshTimer = globalThis.setInterval(() => { void load() }, 60_000)
}

onMounted(() => { void load(); refreshClock(); globalThis.addEventListener('resize', resizeCharts) })
onBeforeUnmount(() => { if (refreshTimer) globalThis.clearInterval(refreshTimer); charts.forEach((chart) => chart.dispose()); globalThis.removeEventListener('resize', resizeCharts) })
</script>

<template>
  <section v-loading="loading" class="analytics-page" :class="{ 'screen-mode': fullscreen }">
    <header class="toolbar">
      <h2>数据统计分析</h2>
      <div class="toolbar-actions">
        <el-button-group><el-button :type="period === '7d' ? 'primary' : 'default'" @click="setPeriod('7d')">7天</el-button><el-button :type="period === '30d' ? 'primary' : 'default'" @click="setPeriod('30d')">30天</el-button><el-button :type="period === '90d' ? 'primary' : 'default'" @click="setPeriod('90d')">90天</el-button><el-button :type="period === 'custom' ? 'primary' : 'default'" @click="setPeriod('custom')">自定义</el-button></el-button-group>
        <el-date-picker v-if="period === 'custom'" v-model="customRange" type="datetimerange" range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间" @change="load" />
        <el-input v-model="lineId" clearable placeholder="全部产线" class="line-input" @change="load" />
        <el-switch v-model="autoRefresh" active-text="60秒自动刷新" inactive-text="关闭自动刷新" @change="refreshClock" />
        <el-button @click="exportCsv">导出 CSV</el-button><el-button type="primary" @click="fullscreen = !fullscreen; nextTick(resizeCharts)">{{ fullscreen ? '退出大屏' : '1080p 大屏' }}</el-button>
      </div>
    </header>
    <p class="rate-note">缺陷检出率口径：{{ overview?.rate_definition }}</p>
    <div class="cards"><el-card><el-statistic title="今日检测总数" :value="overview?.total_detections ?? 0" /></el-card><el-card><el-statistic title="今日 NG 数量" :value="overview?.ng_detections ?? 0" /></el-card><el-card><el-statistic title="今日缺陷检出率" :value="overview?.defect_rate ?? 0" suffix="%" /></el-card></div>
    <div class="charts"><el-card><template #header>划痕 vs 点蚀</template><div ref="barElement" class="chart" /></el-card><el-card><template #header>缺陷率趋势</template><div ref="trendElement" class="chart" /></el-card><el-card><template #header>360° 缺陷热力图</template><div ref="heatmapElement" class="chart" /></el-card><el-card><template #header>类型 × 等级分布</template><div ref="pieElement" class="chart" /></el-card></div>
    <el-card><template #header>统计数据表</template><el-table :data="trends.items"><el-table-column label="日期"><template #default="scope">{{ dateLabel(scope.row.bucket_start) }}</template></el-table-column><el-table-column prop="total_detections" label="检测总数" /><el-table-column prop="ng_detections" label="NG 数量" /><el-table-column prop="defect_rate" label="缺陷率 %" /><el-table-column prop="scratch_count" label="划痕" /><el-table-column prop="pitted_surface_count" label="点蚀" /></el-table></el-card>
  </section>
</template>

<style scoped>
.analytics-page { display: grid; gap: 16px; }.toolbar, .toolbar-actions, .cards { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }.toolbar { justify-content: space-between; }.toolbar h2 { margin: 0; }.line-input { width: 130px; }.rate-note { color: #606266; margin: 0; }.cards { display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); }.charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }.chart { height: 320px; }.screen-mode { position: fixed; z-index: 1000; inset: 0; padding: 24px; overflow: auto; background: #f5f7fa; }.screen-mode .chart { height: 380px; } @media (max-width: 900px) { .cards, .charts { grid-template-columns: 1fr; } }
</style>
