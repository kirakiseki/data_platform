<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { getPageHotspotZones } from '../api/pages'
import type { HotspotZoneItem } from '../api/pages'
import { availableDates, formatNumber } from '../data/traffic'

defineOptions({
  name: 'HotspotMapPage',
})

type TimeMode = 'all' | 'day' | 'hour'
type MapLayer = 'poi' | 'grid' | 'cluster'

interface MapPoint {
  id: string
  name: string
  type: string
  lon: number
  lat: number
  tripCount: number
  pickupCount: number
  dropoffCount: number
  clusterId?: string
}

const mapContainer = ref<HTMLDivElement>()
const timeMode = ref<TimeMode>('all')
const activeLayer = ref<MapLayer>('poi')
const selectedDate = ref(availableDates[2])
const selectedHour = ref(8)
const initError = ref('')
const loading = ref(false)
const hotspotZones = ref<HotspotZoneItem[]>([])
const totalZones = ref(0)

let map: any = null
let pointLayer: any = null
let heatLayer: any = null

const layerOptions = [
  { label: '重点场所', value: 'poi' },
  { label: '网格区域', value: 'grid' },
  { label: '自然热点', value: 'cluster' },
]

const mapPoints = computed(() => {
  return hotspotZones.value
    .filter(item => item.center_lon != null && item.center_lat != null)
    .map((item): MapPoint => ({
      id: item.zone_id,
      name: item.zone_name || (activeLayer.value === 'cluster' ? `聚类 #${item.zone_id}` : item.zone_id),
      type: layerOptions.find(option => option.value === activeLayer.value)?.label ?? item.zone_type,
      lon: item.center_lon ?? 0,
      lat: item.center_lat ?? 0,
      tripCount: item.trip_count,
      pickupCount: item.pickup_count,
      dropoffCount: item.dropoff_count,
      clusterId: activeLayer.value === 'cluster' ? item.zone_id : undefined,
    }))
})

const topPlaces = computed(() => [...mapPoints.value]
  .sort((a, b) => b.tripCount - a.tripCount)
  .slice(0, 8))

const totalTrips = computed(() => mapPoints.value.reduce((sum, item) => sum + item.tripCount, 0))

const pickupDropoffOption = computed<EChartsOption>(() => ({
  color: ['#2563eb', '#f97316'],
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { bottom: 0, data: ['上车', '下车'] },
  grid: { left: 100, right: 24, top: 24, bottom: 48 },
  xAxis: { type: 'value', name: '次数' },
  yAxis: { type: 'category', inverse: true, data: topPlaces.value.map(item => item.name) },
  series: [
    { name: '上车', type: 'bar', stack: 'count', data: topPlaces.value.map(item => item.pickupCount) },
    { name: '下车', type: 'bar', stack: 'count', data: topPlaces.value.map(item => item.dropoffCount) },
  ],
}))

function scopeText() {
  if (timeMode.value === 'hour')
    return `${selectedDate.value} ${selectedHour.value}:00`
  if (timeMode.value === 'day')
    return selectedDate.value
  return '全部数据'
}

function pointColor() {
  if (activeLayer.value === 'poi')
    return '#2563eb'
  if (activeLayer.value === 'grid')
    return '#16a34a'
  return '#f97316'
}

async function loadHotspotZones() {
  loading.value = true
  try {
    const hour = timeMode.value === 'hour' ? selectedHour.value : undefined
    const result = await getPageHotspotZones(activeLayer.value, selectedDate.value, hour, 200)
    hotspotZones.value = result.items
    totalZones.value = result.total
    await nextTick()
    refreshMap()
  }
  finally {
    loading.value = false
  }
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
  pointLayer = L.layerGroup().addTo(map)
  window.setTimeout(() => {
    map.invalidateSize()
    refreshMap()
  }, 200)
}

function refreshMap() {
  const L = (window as any).L
  if (!L || !map || !pointLayer)
    return
  pointLayer.clearLayers()
  if (heatLayer) {
    map.removeLayer(heatLayer)
    heatLayer = null
  }
  if (!mapPoints.value.length) return

  const maxTrips = Math.max(...mapPoints.value.map(item => item.tripCount), 1)

  // 用 leaflet.heat 渲染密度热力图，强度按行程量归一化
  if (typeof (L as any).heatLayer === 'function') {
    const heatData = mapPoints.value.map((item) => {
      const intensity = Math.max(0.2, Math.min(1, item.tripCount / maxTrips))
      return [item.lat, item.lon, intensity]
    })
    heatLayer = (L as any).heatLayer(heatData, {
      radius: 28,
      blur: 22,
      maxZoom: 17,
      minOpacity: 0.35,
      gradient: { 0.2: '#1d4ed8', 0.4: '#22c55e', 0.6: '#f59e0b', 0.8: '#ef4444', 1: '#7f1d1d' },
    }).addTo(map)
  }

  const topPoints = [...mapPoints.value].sort((a, b) => b.tripCount - a.tripCount)

  topPoints.forEach((item) => {
    L.circleMarker([item.lat, item.lon], {
      radius: 4,
      color: '#ffffff',
      weight: 1,
      fillColor: pointColor(),
      fillOpacity: 0.95,
    }).bindPopup(`
      <strong>${item.name}</strong><br/>
      类型：${item.type}<br/>
      行程量：${formatNumber(item.tripCount)}<br/>
      上车：${formatNumber(item.pickupCount)}，下车：${formatNumber(item.dropoffCount)}
    `).addTo(pointLayer)
  })

  const bounds = L.latLngBounds(mapPoints.value.map(item => [item.lat, item.lon]))
  map.fitBounds(bounds.pad(0.2), { maxZoom: 13 })
}

watch([activeLayer, timeMode, selectedDate, selectedHour], loadHotspotZones)

onMounted(async () => {
  const ready = await waitForLeaflet()
  if (!ready) {
    initError.value = 'Leaflet 地图库加载失败，请检查网络连接'
    return
  }
  await nextTick()
  initMap()
})

onMounted(loadHotspotZones)

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
          空间热点
        </div>
        <h1 class="page-title">
          重点区域地图
        </h1>
        <p class="page-subtitle">
          在地图上查看重点场所、网格区域和自然热点的上车、下车与行程集中情况。
        </p>
      </div>
      <el-space wrap>
        <el-segmented v-model="activeLayer" :options="layerOptions" />
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

    <div v-loading="loading" class="content-grid grid-3">
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-location />当前对象
        </div>
        <div class="metric-value">
          {{ totalZones }}
        </div>
        <div class="metric-foot">
          {{ layerOptions.find(item => item.value === activeLayer)?.label }}
        </div>
      </div>
      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-chart-relationship />行程量
        </div>
        <div class="metric-value">
          {{ formatNumber(totalTrips) }}
        </div>
        <div class="metric-foot">
          {{ scopeText() }}
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-map />最高热点
        </div>
        <div class="metric-value">
          {{ topPlaces[0]?.name || '-' }}
        </div>
        <div class="metric-foot">
          {{ topPlaces[0] ? formatNumber(topPlaces[0].tripCount) : 0 }} 次
        </div>
      </div>
    </div>

    <section class="panel map-panel">
      <div class="map-toolbar">
        <div>
          <h3>热点分布地图</h3>
          <span>热力图按行程量加权（蓝 → 绿 → 黄 → 红），叠加 Top 行程标记点。当前范围：{{ scopeText() }}。</span>
        </div>
      </div>
      <el-empty v-if="initError" :description="initError" />
      <div v-else v-loading="loading" class="map-frame">
        <div ref="mapContainer" class="map-container" />
      </div>
    </section>

    <section class="panel">
      <div class="panel-title">
        <h3>上下车对比</h3>
        <span class="muted">排行前 8 的热点对象</span>
      </div>
      <BaseChart v-loading="loading" :option="pickupDropoffOption" height="380px" />
      <el-table v-loading="loading" :data="topPlaces" stripe>
        <el-table-column prop="name" label="区域" min-width="160" />
        <el-table-column prop="type" label="类型" width="110" />
        <el-table-column label="行程数">
          <template #default="{ row }">
            {{ formatNumber(row.tripCount) }}
          </template>
        </el-table-column>
        <el-table-column label="上车">
          <template #default="{ row }">
            {{ formatNumber(row.pickupCount) }}
          </template>
        </el-table-column>
        <el-table-column label="下车">
          <template #default="{ row }">
            {{ formatNumber(row.dropoffCount) }}
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

:deep(.cluster-label) {
  background: rgba(15, 23, 42, 0.78);
  border: none;
  border-radius: 4px;
  padding: 1px 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  pointer-events: none;
}

:deep(.cluster-label::before) {
  display: none;
}
</style>
