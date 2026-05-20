<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { getPageDashboard, getPageTrajectoryDailyStats } from '../api/pages'
import {
  availableDates,
  formatNumber,
  statusType,
} from '../data/traffic'

defineOptions({
  name: 'DashboardPage',
})

type TimeMode = 'all' | 'day' | 'hour'
type HotspotZoneType = 'district' | 'grid' | 'poi' | 'cluster'

const timeMode = ref<TimeMode>('all')
const selectedDate = ref(availableDates[2])
const selectedHour = ref(8)
const hotspotZoneType = ref<HotspotZoneType>('poi')
const loading = ref(false)
const dashboard = ref<Awaited<ReturnType<typeof getPageDashboard>> | null>(null)
const trajectoryDaily = ref<Awaited<ReturnType<typeof getPageTrajectoryDailyStats>>['items']>([])

const hotspotZoneOptions = [
  { label: '行政区', value: 'district' },
  { label: '网格', value: 'grid' },
  { label: '重点场所', value: 'poi' },
  { label: '聚类', value: 'cluster' },
]

const hotspotZoneLabel = computed(() => hotspotZoneOptions.find(item => item.value === hotspotZoneType.value)?.label ?? '重点场所')

const trajectoryTotal = computed(() => trajectoryDaily.value.reduce((acc, item) => ({
  gpsPoints: acc.gpsPoints + (item.total_gps_points ?? 0),
  matchedRoads: acc.matchedRoads + (item.total_matched_roads ?? 0),
  routes: acc.routes + item.trips,
}), { gpsPoints: 0, matchedRoads: 0, routes: 0 }))

const currentDailyTrajectory = computed(() => trajectoryDaily.value.find(item => item.stat_date === selectedDate.value))

const currentStats = computed(() => {
  const day = dashboard.value?.day_stats
  const hour = dashboard.value?.hour_stats
  const dailyTrajectory = currentDailyTrajectory.value
  if (timeMode.value === 'hour') {
    return {
      trips: hour?.trips ?? 0,
      gpsPoints: Math.round((dailyTrajectory?.total_gps_points ?? 0) / 24),
      matchedRoads: Math.round((dailyTrajectory?.total_matched_roads ?? 0) / 24),
      routes: hour?.trips ?? 0,
      activeVehicles: hour?.vehicles ?? 0,
      avgSpeed: Number((hour?.avg_speed ?? 0).toFixed(1)),
    }
  }
  if (timeMode.value === 'day') {
    return {
      trips: day?.trips ?? 0,
      gpsPoints: dailyTrajectory?.total_gps_points ?? 0,
      matchedRoads: dailyTrajectory?.total_matched_roads ?? 0,
      routes: day?.trips ?? 0,
      activeVehicles: day?.vehicles ?? 0,
      avgSpeed: Number((day?.avg_speed ?? 0).toFixed(1)),
    }
  }
  return {
    trips: dashboard.value?.platform_stats.total_trips ?? 0,
    gpsPoints: trajectoryTotal.value.gpsPoints,
    matchedRoads: trajectoryTotal.value.matchedRoads,
    routes: trajectoryTotal.value.routes,
    activeVehicles: dashboard.value?.platform_stats.total_vehicles ?? 0,
    avgSpeed: Number(average(dashboard.value?.network_trend.map(item => item.avg_speed ?? 0) ?? []).toFixed(1)),
  }
})

const scopeText = computed(() => {
  if (timeMode.value === 'hour')
    return `${selectedDate.value} ${selectedHour.value}:00`
  if (timeMode.value === 'day')
    return selectedDate.value
  return '全部数据'
})

const networkTrend = computed(() => dashboard.value?.network_trend ?? [])
const networkSpeedRange = computed(() => paddedRange(networkTrend.value.map(item => item.avg_speed ?? 0)))
const congestionMax = computed(() => Math.max(10, Math.ceil(Math.max(...networkTrend.value.map(item => item.congested_pct), 0) * 1.25)))
const topRoads = computed(() => dashboard.value?.top_roads ?? [])
const topHotspots = computed(() => dashboard.value?.top_hotspots ?? [])

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

async function loadDashboard() {
  loading.value = true
  try {
    const date = timeMode.value === 'all' ? undefined : selectedDate.value
    const hour = timeMode.value === 'hour' ? selectedHour.value : undefined

    const [page, trajectory] = await Promise.all([
      getPageDashboard(timeMode.value, date, hour, 12, hotspotZoneType.value),
      getPageTrajectoryDailyStats(),
    ])
    dashboard.value = page
    trajectoryDaily.value = trajectory.items
  }
  finally {
    loading.value = false
  }
}

const networkTrendOption = computed<EChartsOption>(() => ({
  color: ['#2563eb', '#FF9900'],
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0, data: ['全网均速', '拥堵率(综合)'] },
  grid: { left: 36, right: 32, top: 30, bottom: 48 },
  xAxis: { type: 'category', data: networkTrend.value.map(item => `${item.hour}:00`) },
  yAxis: [
    { type: 'value', name: 'km/h', min: networkSpeedRange.value.min, max: networkSpeedRange.value.max },
    { type: 'value', name: '%', min: 0, max: congestionMax.value },
  ],
  series: [
    { name: '全网均速', type: 'line', smooth: true, data: networkTrend.value.map(item => item.avg_speed ?? 0) },
    { name: '拥堵率(综合)', type: 'bar', yAxisIndex: 1, data: networkTrend.value.map(item => item.congested_pct) },
  ],
}))

const distanceDemandOption = computed<EChartsOption>(() => ({
  color: ['#60a5fa', '#22c55e', '#f97316'],
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { bottom: 0, data: ['短途', '中途', '长途'] },
  grid: { left: 48, right: 20, top: 28, bottom: 48 },
  xAxis: { type: 'category', data: (dashboard.value?.distance_trend ?? []).map(item => `${item.hour}:00`) },
  yAxis: { type: 'value', name: '行程数' },
  series: [
    { name: '短途', type: 'bar', stack: 'distance', data: (dashboard.value?.distance_trend ?? []).map(item => item.short_trips) },
    { name: '中途', type: 'bar', stack: 'distance', data: (dashboard.value?.distance_trend ?? []).map(item => item.medium_trips) },
    { name: '长途', type: 'bar', stack: 'distance', data: (dashboard.value?.distance_trend ?? []).map(item => item.long_trips) },
  ],
}))

watch([timeMode, selectedDate, selectedHour, hotspotZoneType], loadDashboard)

onMounted(loadDashboard)
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <div class="page-kicker">
          概览
        </div>
        <h1 class="page-title">
          运行概览
        </h1>
        <p class="page-subtitle">
          查看行程、轨迹点、道路匹配、路径、道路网络和重点场所统计。
        </p>
      </div>
      <el-space class="overview-filter" wrap>
        <el-segmented
          v-model="timeMode"
          :options="[
            { label: '全部', value: 'all' },
            { label: '按天', value: 'day' },
            { label: '按小时', value: 'hour' },
          ]"
        />
        <el-select v-if="timeMode !== 'all'" v-model="selectedDate" style="width: 140px">
          <el-option v-for="date in availableDates" :key="date" :label="date" :value="date" />
        </el-select>
        <el-select v-if="timeMode === 'hour'" v-model="selectedHour" style="width: 110px">
          <el-option v-for="hour in 24" :key="hour - 1" :label="`${hour - 1}:00`" :value="hour - 1" />
        </el-select>
      </el-space>
    </div>

    <div class="scope-line">
      <span i-carbon-time />
      当前统计范围：{{ scopeText }}
    </div>

    <div v-loading="loading" class="content-grid grid-4">
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-direction-right-01 />行程数
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.trips) }}
        </div>
        <div class="metric-foot">
          出租车行程记录
        </div>
      </div>
      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-location />轨迹点
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.gpsPoints) }}
        </div>
        <div class="metric-foot">
          车辆上报位置点
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-road />道路匹配
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.matchedRoads) }}
        </div>
        <div class="metric-foot">
          轨迹点匹配道路记录
        </div>
      </div>
      <div class="metric-card tone-purple">
        <div class="metric-top">
          <span i-carbon-direction-right-01 />行程路径
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.routes) }}
        </div>
        <div class="metric-foot">
          按行程聚合的路径
        </div>
      </div>
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-map />道路段
        </div>
        <div class="metric-value">
          {{ formatNumber(dashboard?.platform_stats.road_segments ?? 0) }}
        </div>
        <div class="metric-foot">
          当前道路网络
        </div>
      </div>
      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-location />重点场所
        </div>
        <div class="metric-value">
          {{ formatNumber(dashboard?.platform_stats.total_pois ?? 0) }}
        </div>
        <div class="metric-foot">
          OSM POI 全量（行程 300m 内匹配）
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-car />活跃车辆
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.activeVehicles) }}
        </div>
        <div class="metric-foot">
          当前范围内车辆数
        </div>
      </div>
      <div class="metric-card tone-purple">
        <div class="metric-top">
          <span i-carbon-meter />平均速度
        </div>
        <div class="metric-value">
          {{ currentStats.avgSpeed }} km/h
        </div>
        <div class="metric-foot">
          当前范围估算值
        </div>
      </div>
    </div>

    <div class="content-grid grid-2">
      <section class="panel">
        <div class="panel-title">
          <h3>全网均速与拥堵率</h3>
          <el-button text type="primary" @click="$router.push('/network-status')">
            查看全网路况
          </el-button>
        </div>
        <BaseChart :option="networkTrendOption" height="300px" />
      </section>

      <section class="panel">
        <div class="panel-title">
          <h3>小时出行距离结构</h3>
          <el-button text type="primary" @click="$router.push('/trip-features')">
            查看出行特征
          </el-button>
        </div>
        <BaseChart :option="distanceDemandOption" height="360px" />
      </section>
    </div>

    <div class="content-grid grid-2">
      <section class="panel">
        <div class="panel-title">
          <h3>重点拥堵路段</h3>
          <el-button text type="primary" @click="$router.push('/congestion')">
            查看排行
          </el-button>
        </div>
        <el-table :data="topRoads" stripe height="520">
          <el-table-column label="路段" min-width="130">
            <template #default="{ row }">
              <strong>{{ row.road_name || `道路 ${row.road_id}` }}</strong>
              <div class="muted text-xs">
                道路编号 {{ row.road_id }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="avg_speed" label="速度" width="96">
            <template #default="{ row }">
              {{ (row.avg_speed ?? 0).toFixed(1) }} km/h
            </template>
          </el-table-column>
          <el-table-column prop="congestion_idx" label="指数" width="84" />
          <el-table-column label="状态" width="108">
            <template #default="{ row }">
              <span class="status-text" :class="`tone-${statusType(row.status || '')}`">{{ row.status || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel">
        <div class="panel-title">
          <h3>高频区域</h3>
          <el-space>
            <el-select v-model="hotspotZoneType" style="width: 140px">
              <el-option v-for="option in hotspotZoneOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
            <el-button text type="primary" @click="$router.push('/hotspot')">
              查看热点
            </el-button>
          </el-space>
        </div>
        <el-table :data="topHotspots" stripe height="520">
          <el-table-column :label="hotspotZoneLabel" min-width="150">
            <template #default="{ row }">
              {{ row.zone_name || row.zone_id }}
            </template>
          </el-table-column>
          <el-table-column label="行程量" width="120">
            <template #default="{ row }">
              {{ formatNumber(row.trip_count) }}
            </template>
          </el-table-column>
          <el-table-column label="均距(km)" width="110">
            <template #default="{ row }">
              {{ row.avg_trip_distance != null ? row.avg_trip_distance.toFixed(2) : '-' }}
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>
  </div>
</template>

<style scoped>
.overview-filter {
  justify-content: flex-end;
}

.scope-line {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 8px;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  background: #fff;
  color: #475467;
  font-size: 13px;
  padding: 8px 12px;
}

.status-text {
  font-size: 13px;
  font-weight: 700;
}

.tone-success {
  color: #16a34a;
}

.tone-warning {
  color: #d97706;
}

.tone-danger {
  color: #dc2626;
}
</style>
