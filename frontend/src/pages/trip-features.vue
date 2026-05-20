<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import type { AdsTripDistanceHourlyMetric, AdsTripSpeedHourlyMetric, AdsTripTimeslotDailyMetric } from '../api/ads'
import { getAdsTripDistanceHourly, getAdsTripSpeedHourly, getAdsTripTimeslotDaily } from '../api/ads'
import { getPageTripOd } from '../api/pages'
import type { TripOdItem } from '../api/pages'
import { availableDates, formatNumber, speedTone } from '../data/traffic'

defineOptions({
  name: 'TripFeaturesPage',
})

const activeTab = ref('distance')
const selectedDate = ref(availableDates[2])
const loading = ref(false)
const distanceHourly = ref<AdsTripDistanceHourlyMetric[]>([])
const speedHourly = ref<AdsTripSpeedHourlyMetric[]>([])
const timeSlotDaily = ref<AdsTripTimeslotDailyMetric[]>([])
const odPairs = ref<TripOdItem[]>([])
const mapContainer = ref<HTMLDivElement>()
const initError = ref('')

let map: any = null
let odLayer: any = null

const tabOptions = [
  { label: '距离', value: 'distance' },
  { label: '速度', value: 'speed' },
  { label: '时段', value: 'slot' },
  { label: '方向', value: 'od' },
]
const peakDistance = computed(() => Math.max(...distanceHourly.value.map(item => item.short_trips + item.medium_trips + item.long_trips), 0))
const avgDistance = computed(() => average(distanceHourly.value.map(item => item.avg_distance ?? 0)))
const avgSpeed = computed(() => average(speedHourly.value.map(item => item.avg_speed ?? 0)))

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0
}

async function loadTripFeatures() {
  loading.value = true
  try {
    const [distance, speed, slots, od] = await Promise.all([
      getAdsTripDistanceHourly(selectedDate.value),
      getAdsTripSpeedHourly(selectedDate.value),
      getAdsTripTimeslotDaily(),
      getPageTripOd(selectedDate.value, 30),
    ])
    distanceHourly.value = distance.items
    speedHourly.value = speed.items
    timeSlotDaily.value = slots.items
    odPairs.value = od.items
    await nextTick()
    refreshMap()
  }
  finally {
    loading.value = false
  }
}

const distanceOption = computed<EChartsOption>(() => ({
  color: ['#60a5fa', '#22c55e', '#f97316'],
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { bottom: 0, data: ['短途', '中途', '长途'] },
  grid: { left: 48, right: 20, top: 28, bottom: 48 },
  xAxis: { type: 'category', data: distanceHourly.value.map(item => `${item.hour}:00`) },
  yAxis: { type: 'value', name: '行程数' },
  series: [
    { name: '短途', type: 'bar', stack: 'distance', data: distanceHourly.value.map(item => item.short_trips) },
    { name: '中途', type: 'bar', stack: 'distance', data: distanceHourly.value.map(item => item.medium_trips) },
    { name: '长途', type: 'bar', stack: 'distance', data: distanceHourly.value.map(item => item.long_trips) },
  ],
}))

const speedOption = computed<EChartsOption>(() => ({
  color: ['#2563eb', '#22c55e', '#f97316'],
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0, data: ['平均速度', '较高速度', '异常高速'] },
  grid: { left: 48, right: 20, top: 28, bottom: 48 },
  xAxis: { type: 'category', data: speedHourly.value.map(item => `${item.hour}:00`) },
  yAxis: { type: 'value', name: 'km/h' },
  series: [
    { name: '平均速度', type: 'line', smooth: true, data: speedHourly.value.map(item => item.avg_speed ?? 0) },
    { name: '较高速度', type: 'line', smooth: true, data: speedHourly.value.map(item => item.speed_p85 ?? 0) },
    { name: '异常高速', type: 'line', smooth: true, data: speedHourly.value.map(item => item.speed_p95 ?? 0) },
  ],
}))

const slotOption = computed<EChartsOption>(() => ({
  color: ['#60a5fa', '#22c55e', '#f97316', '#64748b'],
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { bottom: 0, data: ['早高峰', '白天', '晚高峰', '夜间'] },
  grid: { left: 52, right: 20, top: 28, bottom: 48 },
  xAxis: { type: 'category', data: timeSlotDaily.value.map(item => item.stat_date) },
  yAxis: { type: 'value', name: '行程数' },
  series: [
    { name: '早高峰', type: 'bar', stack: 'slot', data: timeSlotDaily.value.map(item => item.morning_rush) },
    { name: '白天', type: 'bar', stack: 'slot', data: timeSlotDaily.value.map(item => item.daytime) },
    { name: '晚高峰', type: 'bar', stack: 'slot', data: timeSlotDaily.value.map(item => item.evening_rush) },
    { name: '夜间', type: 'bar', stack: 'slot', data: timeSlotDaily.value.map(item => item.night) },
  ],
}))

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

  map = L.map(mapContainer.value, { zoomControl: false }).setView([45.755, 126.635], 11)
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map)
  odLayer = L.layerGroup().addTo(map)
  window.setTimeout(() => {
    map.invalidateSize()
    refreshMap()
  }, 200)
}

function flowColor(direction: string | null): string {
  return ({
    commute_outbound: '#2563eb',
    commute_inbound: '#7c3aed',
    local: '#16a34a',
    transit: '#f97316',
  } as Record<string, string>)[direction || ''] ?? '#475569'
}

// 用二次贝塞尔曲线近似画一条向终点弯曲的 OD 流向线
function curvedPath(originLat: number, originLng: number, destLat: number, destLng: number, segments = 28): [number, number][] {
  const mx = (originLat + destLat) / 2
  const my = (originLng + destLng) / 2
  const dx = destLat - originLat
  const dy = destLng - originLng
  // 法向偏移：长度比例 + 垂直方向，制造弧度
  const offset = 0.18
  const ctrlLat = mx + (-dy) * offset
  const ctrlLng = my + dx * offset
  const points: [number, number][] = []
  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const lat = (1 - t) ** 2 * originLat + 2 * (1 - t) * t * ctrlLat + t ** 2 * destLat
    const lng = (1 - t) ** 2 * originLng + 2 * (1 - t) * t * ctrlLng + t ** 2 * destLng
    points.push([lat, lng])
  }
  return points
}

function refreshMap() {
  const L = (window as any).L
  if (!L || !map || !odLayer)
    return
  odLayer.clearLayers()
  const maxTrips = Math.max(...odPairs.value.map(item => item.trip_count), 1)

  // 用半透明热区先表达起终点密度（O+D 都参与），让稀疏的 Top-N 不显得空旷
  if (typeof (L as any).heatLayer === 'function') {
    const heatPoints: [number, number, number][] = []
    odPairs.value.forEach((item) => {
      if (item.origin_lat != null && item.origin_lon != null) {
        heatPoints.push([item.origin_lat, item.origin_lon, item.trip_count / maxTrips])
      }
      if (item.dest_lat != null && item.dest_lon != null) {
        heatPoints.push([item.dest_lat, item.dest_lon, item.trip_count / maxTrips])
      }
    })
    if (heatPoints.length) {
      (L as any).heatLayer(heatPoints, {
        radius: 24,
        blur: 18,
        minOpacity: 0.25,
        gradient: { 0.2: '#bfdbfe', 0.5: '#60a5fa', 0.8: '#1d4ed8', 1: '#1e3a8a' },
      }).addTo(odLayer)
    }
  }

  // 流向线：颜色按 flow_direction 区分，粗细按行程量缩放，弧线表示方向
  odPairs.value.forEach((item) => {
    if (item.origin_lat == null || item.origin_lon == null || item.dest_lat == null || item.dest_lon == null)
      return
    const ratio = item.trip_count / maxTrips
    const weight = 2.5 + ratio * 6
    const color = flowColor(item.flow_direction)
    const popup = `
      <strong>${item.origin_name || '起点'} → ${item.dest_name || '终点'}</strong><br/>
      行程量：${formatNumber(item.trip_count)}<br/>
      均距：${(item.avg_distance ?? 0).toFixed(1)} km<br/>
      均时：${(item.avg_duration ?? 0).toFixed(1)} min<br/>
      特征：${flowDirectionLabel(item.flow_direction)}
    `
    const path = curvedPath(item.origin_lat, item.origin_lon, item.dest_lat, item.dest_lon)
    // 外发光层
    L.polyline(path, { color, weight: weight + 4, opacity: 0.18 }).addTo(odLayer)
    L.polyline(path, { color, weight, opacity: 0.9 }).bindPopup(popup).addTo(odLayer)

    // 终点附近添加一个三角箭头
    const tail = path[path.length - 1]
    const tailPrev = path[path.length - 6] ?? path[0]
    const angle = Math.atan2(tail[0] - tailPrev[0], tail[1] - tailPrev[1])
    const arrow = L.marker(tail, {
      icon: L.divIcon({
        className: 'od-arrow',
        html: `<div style="transform: rotate(${(Math.PI / 2 - angle) * 180 / Math.PI}deg); color: ${color};">▲</div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    })
    arrow.bindPopup(popup).addTo(odLayer)

    // 起点小空心环
    L.circleMarker([item.origin_lat, item.origin_lon], {
      radius: 5, color, weight: 2.5, fillColor: '#ffffff', fillOpacity: 1,
    }).bindPopup(popup).addTo(odLayer)
  })

  // 自适应缩放到所有 OD 端点
  const allPts: [number, number][] = odPairs.value.flatMap((item) => {
    const arr: [number, number][] = []
    if (item.origin_lat != null && item.origin_lon != null) arr.push([item.origin_lat, item.origin_lon])
    if (item.dest_lat != null && item.dest_lon != null) arr.push([item.dest_lat, item.dest_lon])
    return arr
  })
  if (allPts.length) {
    const bounds = L.latLngBounds(allPts)
    map.fitBounds(bounds.pad(0.2), { maxZoom: 12 })
  }
}

function flowDirectionLabel(value: string | null) {
  return ({
    commute_outbound: '通勤外出',
    commute_inbound: '通勤返回',
    local: '本地出行',
    transit: '枢纽接驳',
  } as Record<string, string>)[value || ''] ?? '综合流向'
}

onMounted(async () => {
  const ready = await waitForLeaflet()
  if (!ready) {
    initError.value = 'Leaflet 地图库加载失败，请检查网络连接'
    return
  }
  await nextTick()
  initMap()
})

watch(selectedDate, loadTripFeatures)

onMounted(loadTripFeatures)

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
          出行特征统计
        </div>
        <h1 class="page-title">
          出行特征分析
        </h1>
        <p class="page-subtitle">
          查看出租车行程的距离分布、时段分布、速度分布和主要出行方向。
        </p>
      </div>
      <el-space wrap>
        <el-segmented v-model="activeTab" :options="tabOptions" />
        <el-select v-model="selectedDate" style="width: 140px">
          <el-option v-for="date in availableDates" :key="date" :label="date" :value="date" />
        </el-select>
      </el-space>
    </div>

    <div v-loading="loading" class="content-grid grid-4">
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-direction-right-01 />平均出行距离
        </div>
        <div class="metric-value">
          {{ avgDistance.toFixed(1) }} km
        </div>
        <div class="metric-foot">
          按时段汇总后的出行距离
        </div>
      </div>
      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-meter />平均速度
        </div>
        <div class="metric-value">
          {{ avgSpeed.toFixed(1) }} km/h
        </div>
        <div class="metric-foot">
          用于识别低速和异常高速时段
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-time />高峰小时需求
        </div>
        <div class="metric-value">
          {{ formatNumber(peakDistance) }}
        </div>
        <div class="metric-foot">
          短中长途小时样本峰值
        </div>
      </div>
      <div class="metric-card tone-purple">
        <div class="metric-top">
          <span i-carbon-chart-relationship />重点出行方向
        </div>
        <div class="metric-value">
          {{ odPairs.length }}
        </div>
        <div class="metric-foot">
          行政区、网格、重点场所多口径分析
        </div>
      </div>
    </div>

    <section class="panel map-panel">
      <div class="map-toolbar">
        <div>
          <h3>重点出行方向地图</h3>
          <span>
            底图叠加 OD 起终点密度热区；弧线为流向（颜色：
            <span class="legend-dot" style="background:#2563eb" />通勤外出
            <span class="legend-dot" style="background:#7c3aed" />通勤返回
            <span class="legend-dot" style="background:#16a34a" />本地
            <span class="legend-dot" style="background:#f97316" />枢纽接驳）；
            线宽按行程量缩放，箭头指向终点。
          </span>
        </div>
      </div>
      <el-empty v-if="initError" :description="initError" />
      <div v-else class="map-frame">
        <div ref="mapContainer" class="map-container" />
      </div>
    </section>

    <section v-if="activeTab === 'distance'" class="panel">
      <div class="panel-title">
        <h3>小时级距离结构</h3>
        <span class="muted">短途 &lt;3km，中途 3-10km，长途 &gt;10km</span>
      </div>
      <BaseChart :option="distanceOption" height="340px" />
      <el-table v-loading="loading" :data="distanceHourly" height="420" stripe>
        <el-table-column prop="hour" label="时段" width="90">
          <template #default="{ row }">
            {{ row.hour }}:00
          </template>
        </el-table-column>
        <el-table-column label="短途" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.short_trips) }}
          </template>
        </el-table-column>
        <el-table-column label="中途" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.medium_trips) }}
          </template>
        </el-table-column>
        <el-table-column label="长途" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.long_trips) }}
          </template>
        </el-table-column>
        <el-table-column prop="avg_distance" label="平均距离(km)" sortable>
          <template #default="{ row }">
            {{ (row.avg_distance ?? 0).toFixed(1) }}
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section v-else-if="activeTab === 'speed'" class="panel">
      <div class="panel-title">
        <h3>速度分位分析</h3>
        <span class="muted">用于评估不同时间段的通行效率和异常速度</span>
      </div>
      <BaseChart :option="speedOption" height="320px" />
      <el-table v-loading="loading" :data="speedHourly" height="560" stripe>
        <el-table-column prop="hour" label="时段" width="90">
          <template #default="{ row }">
            {{ row.hour }}:00
          </template>
        </el-table-column>
        <el-table-column prop="avg_speed" label="平均速度" sortable width="130">
          <template #default="{ row }">
            <el-tag :type="speedTone(row.avg_speed ?? 0)" effect="light">
              {{ (row.avg_speed ?? 0).toFixed(1) }} km/h
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="speed_p50" label="中位速度" sortable>
          <template #default="{ row }">
            {{ (row.speed_p50 ?? 0).toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column prop="speed_p85" label="较高速度" sortable>
          <template #default="{ row }">
            {{ (row.speed_p85 ?? 0).toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column prop="speed_p95" label="异常高速" sortable>
          <template #default="{ row }">
            {{ (row.speed_p95 ?? 0).toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column prop="overspeed_ratio" label="超速比例" sortable>
          <template #default="{ row }">
            {{ ((row.overspeed_ratio ?? 0) * 100).toFixed(1) }}%
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section v-else-if="activeTab === 'slot'" class="panel">
      <div class="panel-title">
        <h3>日级时段分布</h3>
        <span class="muted">早高峰 / 白天 / 晚高峰 / 夜间</span>
      </div>
      <BaseChart :option="slotOption" height="340px" />
      <el-table v-loading="loading" :data="timeSlotDaily" stripe>
        <el-table-column prop="stat_date" label="日期" />
        <el-table-column label="早高峰">
          <template #default="{ row }">
            {{ formatNumber(row.morning_rush) }}
          </template>
        </el-table-column>
        <el-table-column label="白天">
          <template #default="{ row }">
            {{ formatNumber(row.daytime) }}
          </template>
        </el-table-column>
        <el-table-column label="晚高峰">
          <template #default="{ row }">
            {{ formatNumber(row.evening_rush) }}
          </template>
        </el-table-column>
        <el-table-column label="夜间">
          <template #default="{ row }">
            {{ formatNumber(row.night) }}
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section v-else class="panel">
      <div class="panel-title">
        <h3>重点出行方向</h3>
        <span class="muted">面向跨区通勤、枢纽接驳和商圈出行</span>
      </div>
      <el-table :data="odPairs" stripe>
        <el-table-column prop="rank" label="排名" width="80" />
        <el-table-column label="出行方向" min-width="220">
          <template #default="{ row }">
            <strong>{{ row.origin_name || '-' }}</strong>
            <span class="arrow">→</span>
            <strong>{{ row.dest_name || '-' }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="行程量" width="140">
          <template #default="{ row }">
            {{ formatNumber(row.trip_count) }}
          </template>
        </el-table-column>
        <el-table-column prop="avg_distance" label="均距(km)" width="120">
          <template #default="{ row }">
            {{ (row.avg_distance ?? 0).toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column label="主要特征">
          <template #default="{ row }">
            {{ flowDirectionLabel(row.flow_direction) }}
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.arrow {
  margin: 0 10px;
  color: #409eff;
  font-weight: 760;
}

.map-panel {
  min-height: 460px;
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
  height: 540px;
}

.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  margin: 0 4px 0 8px;
  vertical-align: middle;
}

:deep(.od-arrow) {
  background: transparent;
  border: none;
  font-size: 14px;
  line-height: 14px;
  text-shadow: 0 0 4px rgba(255, 255, 255, 0.6);
}

.map-container {
  width: 100%;
  height: 100%;
}
</style>
