<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { getPageTrajectoryDailyStats, getPageTrajectorySamples } from '../api/pages'
import type { TrajectoryDailyStatsItem, TrajectoryRouteSource, TrajectorySampleItem } from '../api/pages'
import { availableDates, formatNumber } from '../data/traffic'

defineOptions({
  name: 'TrajectoryMapPage',
})

type TimeMode = 'all' | 'day' | 'hour'

interface TrajectorySample {
  id: string
  name: string
  date: string
  hour: number
  trips: number
  color: string
  segments: [number, number][][]
}

const mapContainer = ref<HTMLDivElement>()
const timeMode = ref<TimeMode>('all')
const selectedDate = ref(availableDates[2])
const selectedHour = ref(8)
const routeSource = ref<TrajectoryRouteSource>('matched')
const initError = ref('')
const loading = ref(false)
const dailyStats = ref<TrajectoryDailyStatsItem[]>([])
const trajectorySamples = ref<TrajectorySample[]>([])

const routeSourceOptions = [
  { label: '地图匹配轨迹', value: 'matched' },
  { label: '原始 GPS 轨迹', value: 'raw' },
]

let map: any = null
let trajectoryLayer: any = null

const currentDaily = computed(() => dailyStats.value.find(item => item.stat_date === selectedDate.value) ?? dailyStats.value[0])
const totalStats = computed(() => dailyStats.value.reduce((acc, item) => ({
  gpsPoints: acc.gpsPoints + (item.total_gps_points ?? 0),
  matchedRoads: acc.matchedRoads + (item.total_matched_roads ?? 0),
  routes: acc.routes + item.trips,
  vehicles: Math.max(acc.vehicles, item.total_vehicles),
}), { gpsPoints: 0, matchedRoads: 0, routes: 0, vehicles: 0 }))

const visibleTrajectories = computed(() => trajectorySamples.value.filter((item) => {
  if (timeMode.value === 'all')
    return true
  if (timeMode.value === 'day')
    return item.date === selectedDate.value
  return item.date === selectedDate.value && item.hour === selectedHour.value
}))

const currentStats = computed(() => {
  if (timeMode.value === 'hour') {
    return {
      gpsPoints: Math.round((currentDaily.value?.total_gps_points ?? 0) / 24),
      matchedRoads: Math.round((currentDaily.value?.total_matched_roads ?? 0) / 24),
      routes: visibleTrajectories.value.length,
      vehicles: currentDaily.value?.total_vehicles ?? 0,
    }
  }
  if (timeMode.value === 'day') {
    return {
      gpsPoints: currentDaily.value?.total_gps_points ?? 0,
      matchedRoads: currentDaily.value?.total_matched_roads ?? 0,
      routes: currentDaily.value?.trips ?? 0,
      vehicles: currentDaily.value?.total_vehicles ?? 0,
    }
  }
  return {
    gpsPoints: totalStats.value.gpsPoints,
    matchedRoads: totalStats.value.matchedRoads,
    routes: totalStats.value.routes,
    vehicles: totalStats.value.vehicles,
  }
})

const pointOption = computed<EChartsOption>(() => ({
  color: ['#2563eb', '#22c55e'],
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0, data: ['轨迹点', '道路匹配记录'] },
  grid: { left: 64, right: 24, top: 26, bottom: 48 },
  xAxis: { type: 'category', data: dailyStats.value.map(item => item.stat_date.slice(5)) },
  yAxis: { type: 'value', name: '记录数' },
  series: [
    { name: '轨迹点', type: 'line', smooth: true, data: dailyStats.value.map(item => item.total_gps_points ?? 0) },
    { name: '道路匹配记录', type: 'line', smooth: true, data: dailyStats.value.map(item => item.total_matched_roads ?? 0) },
  ],
}))

const sampleColors = ['#2563eb', '#16a34a', '#f97316', '#7c3aed', '#0891b2', '#dc2626', '#0f766e', '#9333ea']

function collectLineCoords(geometry: any, out: [number, number][][]) {
  if (!geometry) return
  if (geometry.type === 'LineString' && Array.isArray(geometry.coordinates)) {
    const seg = geometry.coordinates
      .filter((p: any) => Array.isArray(p) && p.length >= 2)
      .map((p: [number, number]) => [p[1], p[0]] as [number, number])
    if (seg.length >= 2) out.push(seg)
    return
  }
  if (geometry.type === 'MultiLineString' && Array.isArray(geometry.coordinates)) {
    geometry.coordinates.forEach((line: any[]) => {
      const seg = line
        .filter((p: any) => Array.isArray(p) && p.length >= 2)
        .map((p: [number, number]) => [p[1], p[0]] as [number, number])
      if (seg.length >= 2) out.push(seg)
    })
    return
  }
  if (geometry.type === 'GeometryCollection' && Array.isArray(geometry.geometries)) {
    geometry.geometries.forEach((g: any) => collectLineCoords(g, out))
  }
}

function pointsFromRouteLine(routeLine: any): [number, number][][] {
  const segments: [number, number][][] = []
  collectLineCoords(routeLine, segments)
  return segments
}

function toTrajectorySample(item: TrajectorySampleItem, index: number): TrajectorySample | null {
  const segments = pointsFromRouteLine(item.route_line)
  if (!segments.length)
    return null
  return {
    id: String(item.trip_id),
    name: `行程 ${item.trip_id}`,
    date: item.trip_date,
    hour: item.start_hour ?? 0,
    trips: 1,
    color: sampleColors[index % sampleColors.length],
    segments,
  }
}

async function loadTrajectoryData() {
  loading.value = true
  try {
    const [daily, samples] = await Promise.all([
      getPageTrajectoryDailyStats(),
      getPageTrajectorySamples(
        timeMode.value === 'all' ? undefined : selectedDate.value,
        timeMode.value === 'hour' ? selectedHour.value : undefined,
        8,
        routeSource.value,
      ),
    ])
    dailyStats.value = daily.items
    trajectorySamples.value = samples.items
      .map(toTrajectorySample)
      .filter((item): item is TrajectorySample => Boolean(item))
    await nextTick()
    refreshMap()
  }
  finally {
    loading.value = false
  }
}

function scopeText() {
  if (timeMode.value === 'hour')
    return `${selectedDate.value} ${selectedHour.value}:00`
  if (timeMode.value === 'day')
    return selectedDate.value
  return '全部数据'
}

function waitForLeaflet(maxRetries = 25): Promise<boolean> {
  return new Promise((resolve) => {
    let retries = 0
    const check = () => {
      if ((window as any).L)
        return resolve(true)
      retries += 1
      if (retries >= maxRetries)
        return resolve(false)
      window.setTimeout(check, 120)
    }
    check()
  })
}

function initMap() {
  if (!mapContainer.value)
    return
  const L = (window as any).L
  if (!L) {
    initError.value = 'Leaflet 地图库加载失败'
    return
  }

  map = L.map(mapContainer.value, { zoomControl: false }).setView([45.755, 126.635], 12)
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map)
  trajectoryLayer = L.layerGroup().addTo(map)
  window.setTimeout(() => {
    map.invalidateSize()
    refreshMap()
  }, 200)
}

function refreshMap() {
  const L = (window as any).L
  if (!L || !map || !trajectoryLayer)
    return
  trajectoryLayer.clearLayers()

  visibleTrajectories.value.forEach((item) => {
    item.segments.forEach((seg) => {
      L.polyline(seg, {
        color: item.color,
        weight: 5,
        opacity: 0.82,
      }).bindPopup(`
        <strong>${item.name}</strong><br/>
        时间：${item.date} ${item.hour}:00<br/>
        行程量：${formatNumber(item.trips)}
      `).addTo(trajectoryLayer)
    })

    const firstSeg = item.segments[0]
    const lastSeg = item.segments[item.segments.length - 1]
    if (firstSeg?.length) {
      const start = firstSeg[0]
      L.circleMarker(start, { radius: 5, color: item.color, fillColor: '#ffffff', fillOpacity: 1, weight: 3 }).addTo(trajectoryLayer)
    }
    if (lastSeg?.length) {
      const end = lastSeg[lastSeg.length - 1]
      L.circleMarker(end, { radius: 7, color: item.color, fillColor: item.color, fillOpacity: 0.9, weight: 2 }).addTo(trajectoryLayer)
    }
  })

  if (visibleTrajectories.value.length) {
    const allPoints = visibleTrajectories.value.flatMap(item => item.segments.flat())
    if (allPoints.length) {
      const bounds = L.latLngBounds(allPoints)
      map.fitBounds(bounds.pad(0.16), { maxZoom: 13 })
    }
  }
}

watch([timeMode, selectedDate, selectedHour, routeSource], loadTrajectoryData)

onMounted(async () => {
  const ready = await waitForLeaflet()
  if (!ready) {
    initError.value = 'Leaflet 地图库加载失败，请检查网络连接'
    return
  }
  await nextTick()
  initMap()
})

onMounted(loadTrajectoryData)

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <div class="page-kicker">
          轨迹数据
        </div>
        <h1 class="page-title">
          轨迹分布
        </h1>
        <p class="page-subtitle">
          按全部数据、日期或小时查看轨迹点、道路匹配记录，并在地图上展示典型行程路径。
        </p>
      </div>
      <el-space wrap>
        <el-segmented v-model="routeSource" :options="routeSourceOptions" />
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

    <div v-loading="loading" class="content-grid grid-4">
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-location />轨迹点
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.gpsPoints) }}
        </div>
        <div class="metric-foot">
          {{ scopeText() }}
        </div>
      </div>
      <div class="metric-card tone-green">
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
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-direction-right-01 />行程路径
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.routes) }}
        </div>
        <div class="metric-foot">
          按行程聚合后的路径
        </div>
      </div>
      <div class="metric-card tone-purple">
        <div class="metric-top">
          <span i-carbon-car />活跃车辆
        </div>
        <div class="metric-value">
          {{ formatNumber(currentStats.vehicles) }}
        </div>
        <div class="metric-foot">
          当前统计范围车辆数
        </div>
      </div>
    </div>

    <section class="panel map-panel">
      <div class="map-toolbar">
        <div>
          <h3>典型轨迹地图</h3>
          <span>
            当前范围：{{ scopeText() }}，
            模式：{{ routeSource === 'matched' ? '地图匹配轨迹（严格沿道路）' : '原始 GPS 轨迹（基于 GPS 点直接相连）' }}，
            展示 {{ visibleTrajectories.length }} 条路径。
          </span>
        </div>
      </div>
      <el-empty v-if="initError" :description="initError" />
      <div v-else v-loading="loading" class="map-frame">
        <div ref="mapContainer" class="map-container" />
      </div>
    </section>

    <section class="panel">
      <div class="panel-title">
        <h3>轨迹点与道路匹配记录</h3>
        <span class="muted">按日统计</span>
      </div>
      <BaseChart v-loading="loading" :option="pointOption" height="360px" />
      <el-table v-loading="loading" :data="dailyStats" stripe>
        <el-table-column prop="stat_date" label="日期" />
        <el-table-column label="行程数">
          <template #default="{ row }">
            {{ formatNumber(row.trips) }}
          </template>
        </el-table-column>
        <el-table-column label="轨迹点">
          <template #default="{ row }">
            {{ formatNumber(row.total_gps_points ?? 0) }}
          </template>
        </el-table-column>
        <el-table-column label="道路匹配记录">
          <template #default="{ row }">
            {{ formatNumber(row.total_matched_roads ?? 0) }}
          </template>
        </el-table-column>
        <el-table-column label="活跃车辆">
          <template #default="{ row }">
            {{ formatNumber(row.total_vehicles) }}
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.map-panel {
  min-height: 540px;
  padding: 0;
  overflow: hidden;
}

.map-toolbar {
  border-bottom: 1px solid #e4e7ec;
  padding: 16px 18px;
}

.map-toolbar h3 {
  margin: 0;
  color: #101828;
  font-size: 16px;
}

.map-toolbar span {
  color: #667085;
  font-size: 13px;
}

.map-frame {
  height: 480px;
}

.map-container {
  width: 100%;
  height: 100%;
}
</style>
