<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import type { AdsNetworkStatusHourlyMetric } from '../api/ads'
import { getAdsNetworkStatusHourly } from '../api/ads'
import { availableDates, formatNumber, speedTone } from '../data/traffic'

defineOptions({
  name: 'NetworkStatusPage',
})

const selectedDate = ref(availableDates[2])
const loading = ref(false)
const networkStatus = ref<AdsNetworkStatusHourlyMetric[]>([])

const normalizedStatus = computed(() => networkStatus.value)
const avgSmooth = computed(() => average(normalizedStatus.value.map(item => item.smooth_pct)))
const avgBasicallySmooth = computed(() => average(normalizedStatus.value.map(item => item.basically_smooth_pct)))
const avgCongested = computed(() => average(normalizedStatus.value.map(item => item.light_congested_pct + item.moderate_congested_pct + item.severe_congested_pct)))
const avgSevere = computed(() => average(normalizedStatus.value.map(item => item.severe_congested_pct)))
const avgSpeed = computed(() => average(normalizedStatus.value.map(item => item.network_avg_speed ?? 0)))
const totalRoads = computed(() => Math.max(...normalizedStatus.value.map(item => item.total_roads), 0))
const speedRange = computed(() => paddedRange(normalizedStatus.value.map(item => item.network_avg_speed ?? 0)))

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0
}

function paddedRange(values: number[]) {
  const valid = values.filter(value => Number.isFinite(value) && value > 0)
  if (!valid.length)
    return { min: 0, max: 100 }
  const min = Math.min(...valid)
  const max = Math.max(...valid)
  const padding = Math.max((max - min) * 0.18, 1)
  return {
    min: Math.max(0, Math.floor(min - padding)),
    max: Math.ceil(max + padding),
  }
}

async function loadNetworkStatus() {
  loading.value = true
  try {
    const { items } = await getAdsNetworkStatusHourly(selectedDate.value)
    networkStatus.value = items
  }
  finally {
    loading.value = false
  }
}

function colorByPct(value: number) {
  if (value >= 70)
    return '#22c55e'
  if (value >= 58)
    return '#f59e0b'
  return '#ef4444'
}

const statusStackOption = computed<EChartsOption>(() => ({
  color: ['#008000', '#99CC00', '#FFFF00', '#FF9900', '#FF0000'],
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { bottom: 0, data: ['畅通率', '基本畅通率', '轻度拥堵率', '中度拥堵率', '严重拥堵率'] },
  grid: { left: 42, right: 20, top: 28, bottom: 48 },
  xAxis: { type: 'category', data: normalizedStatus.value.map(item => `${item.hour}:00`) },
  yAxis: { type: 'value', name: '%', min: 0, max: 100 },
  series: [
    { name: '畅通率', type: 'bar', stack: 'status', data: normalizedStatus.value.map(item => item.smooth_pct) },
    { name: '基本畅通率', type: 'bar', stack: 'status', data: normalizedStatus.value.map(item => item.basically_smooth_pct) },
    { name: '轻度拥堵率', type: 'bar', stack: 'status', data: normalizedStatus.value.map(item => item.light_congested_pct) },
    { name: '中度拥堵率', type: 'bar', stack: 'status', data: normalizedStatus.value.map(item => item.moderate_congested_pct) },
    { name: '严重拥堵率', type: 'bar', stack: 'status', data: normalizedStatus.value.map(item => item.severe_congested_pct) },
  ],
}))

const speedTrendOption = computed<EChartsOption>(() => ({
  color: ['#2563eb'],
  tooltip: { trigger: 'axis' },
  grid: { left: 42, right: 20, top: 28, bottom: 32 },
  xAxis: { type: 'category', data: normalizedStatus.value.map(item => `${item.hour}:00`) },
  yAxis: { type: 'value', name: 'km/h', min: speedRange.value.min, max: speedRange.value.max },
  series: [
    {
      name: '全网均速',
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.12 },
      data: normalizedStatus.value.map(item => item.network_avg_speed ?? 0),
    },
  ],
}))

watch(selectedDate, loadNetworkStatus)

onMounted(loadNetworkStatus)
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <div class="page-kicker">
          全网运行态势
        </div>
        <h1 class="page-title">
          全网路况汇总
        </h1>
        <p class="page-subtitle">
          查看指定日期 24 小时道路畅通、缓行、拥堵占比，以及全网平均速度变化。
        </p>
      </div>
      <el-space wrap>
        <span class="filter-label">统计日期</span>
        <el-select v-model="selectedDate" style="width: 140px">
          <el-option v-for="date in availableDates" :key="date" :label="date" :value="date" />
        </el-select>
      </el-space>
    </div>

    <div v-loading="loading" class="content-grid grid-4">
      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-checkmark-outline />平均畅通率
        </div>
        <div class="metric-value" :style="{ color: colorByPct(avgSmooth) }">
          {{ avgSmooth.toFixed(1) }}%
        </div>
        <div class="metric-foot">
          全天分时均值
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-warning-alt />平均基本畅通率
        </div>
        <div class="metric-value warning">
          {{ avgBasicallySmooth.toFixed(1) }}%
        </div>
        <div class="metric-foot">
          基本畅通道路占比
        </div>
      </div>
      <div class="metric-card tone-purple">
        <div class="metric-top">
          <span i-carbon-traffic-incident />平均拥堵率
        </div>
        <div class="metric-value danger">
          {{ avgCongested.toFixed(1) }}%
        </div>
        <div class="metric-foot">
          严重拥堵 {{ avgSevere.toFixed(1) }}%
        </div>
      </div>
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-meter />日均速度
        </div>
        <div class="metric-value">
          {{ avgSpeed.toFixed(1) }} km/h
        </div>
        <div class="metric-foot">
          道路总数 {{ formatNumber(totalRoads) }}
        </div>
      </div>
    </div>

    <section class="panel">
      <div class="panel-title">
        <h3>24 小时状态结构</h3>
        <span class="muted">畅通 / 基本畅通 / 轻度拥堵 / 中度拥堵 / 严重拥堵</span>
      </div>
      <BaseChart :option="statusStackOption" height="360px" />
    </section>

    <section class="panel">
      <div class="panel-title">
        <h3>全网平均速度</h3>
        <span class="muted">用于观察早晚高峰速度下降</span>
      </div>
      <BaseChart :option="speedTrendOption" height="280px" />
    </section>

    <section class="panel">
      <div class="panel-title">
        <h3>小时级明细</h3>
        <span class="muted">支持按历史时刻回看运行状态</span>
      </div>
      <el-table v-loading="loading" :data="normalizedStatus" height="520" stripe>
        <el-table-column prop="hour" label="时段" width="80">
          <template #default="{ row }">
            {{ row.hour }}:00
          </template>
        </el-table-column>
        <el-table-column label="道路总数">
          <template #default="{ row }">
            {{ formatNumber(row.total_roads) }}
          </template>
        </el-table-column>
        <el-table-column label="畅通数">
          <template #default="{ row }">
            {{ formatNumber(row.smooth_roads) }}
          </template>
        </el-table-column>
        <el-table-column prop="smooth_pct" label="畅通率" sortable>
          <template #default="{ row }">
            {{ row.smooth_pct.toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column label="基本畅通数">
          <template #default="{ row }">
            {{ formatNumber(row.basically_smooth_roads) }}
          </template>
        </el-table-column>
        <el-table-column prop="basically_smooth_pct" label="基本畅通率" sortable>
          <template #default="{ row }">
            {{ row.basically_smooth_pct.toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="light_congested_pct" label="轻度拥堵率" sortable>
          <template #default="{ row }">
            <span class="warning">{{ row.light_congested_pct.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="moderate_congested_pct" label="中度拥堵率" sortable>
          <template #default="{ row }">
            <span class="danger">{{ row.moderate_congested_pct.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="严重拥堵">
          <template #default="{ row }">
            {{ formatNumber(row.severe_congested_roads) }}
          </template>
        </el-table-column>
        <el-table-column prop="network_avg_speed" label="全网均速" sortable width="130">
          <template #default="{ row }">
            <el-tag :type="speedTone(row.network_avg_speed ?? 0)" effect="light">
              {{ (row.network_avg_speed ?? 0).toFixed(1) }} km/h
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.filter-label {
  color: #475467;
  font-size: 13px;
  font-weight: 650;
}

.warning {
  color: #f59e0b;
}

.danger {
  color: #ef4444;
}
</style>
