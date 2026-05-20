<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import type { AdsHotspotMonitorDailyMetric } from '../api/ads'
import { getAdsHotspotMonitorDaily } from '../api/ads'
import { getPageHotspotZones } from '../api/pages'
import type { HotspotZoneItem } from '../api/pages'
import { availableDates, formatNumber } from '../data/traffic'

defineOptions({
  name: 'HotspotPage',
})

type HotspotTab = 'district' | 'grid' | 'poi' | 'cluster'
type TimeMode = 'all' | 'day' | 'hour'

const activeTab = ref<HotspotTab>('district')
const timeMode = ref<TimeMode>('all')
const selectedDate = ref(availableDates[2])
const selectedHour = ref(8)
const monitorLoading = ref(false)
const zoneLoading = ref(false)
const hotspotMonitor = ref<AdsHotspotMonitorDailyMetric[]>([])
const hotspotZones = ref<HotspotZoneItem[]>([])
const totalZones = ref(0)
const mapContainer = ref<HTMLDivElement>()
const initError = ref('')

let map: any = null
let hotspotLayer: any = null
let heatLayer: any = null

interface HotspotMapPoint {
  id: string
  name: string
  type: string
  lon: number
  lat: number
  tripCount: number
}

const tabs = [
  { label: '行政区', value: 'district' },
  { label: '网格', value: 'grid' },
  { label: '重点场所', value: 'poi' },
  { label: '聚类', value: 'cluster' },
]

const currentData = computed(() => activeTab.value === 'cluster'
  ? []
  : hotspotZones.value.map(item => ({
      zoneId: item.zone_id,
      zoneName: item.zone_name || item.zone_id,
      zoneType: item.zone_type,
      tripCount: item.trip_count,
      pickupCount: item.pickup_count,
      dropoffCount: item.dropoff_count,
      vehicleCount: item.vehicle_count ?? 0,
      avgTripDistance: item.avg_trip_distance ?? 0,
      avgDuration: item.avg_duration ?? 0,
      lon: item.center_lon,
      lat: item.center_lat,
    })))
const currentClusters = computed(() => hotspotZones.value.map((item, index) => ({
  clusterId: item.zone_id,
  clusterType: item.zone_name || `热点 ${index + 1}`,
  centerLon: item.center_lon ?? 0,
  centerLat: item.center_lat ?? 0,
  tripCount: item.trip_count,
  pickupCount: item.pickup_count,
  dropoffCount: item.dropoff_count,
  avgDuration: item.avg_duration ?? 0,
})))
const visualRows = computed(() => {
  if (activeTab.value === 'cluster') {
    return currentClusters.value.map(item => ({
      id: String(item.clusterId),
      name: item.clusterType,
      meta: `${item.centerLon.toFixed(2)}, ${item.centerLat.toFixed(2)}`,
      tripCount: item.tripCount,
    })).slice(0, 50)
  }
  return currentData.value.map(item => ({
    id: item.zoneId,
    name: item.zoneName,
    meta: zoneTypeLabel(item.zoneType),
    tripCount: item.tripCount,
  })).slice(0, 50)
})
const totalTrips = computed(() => activeTab.value === 'cluster'
  ? currentClusters.value.reduce((sum, item) => sum + item.tripCount, 0)
  : currentData.value.reduce((sum, item) => sum + item.tripCount, 0))
const maxTrips = computed(() => Math.max(...(activeTab.value === 'cluster'
  ? currentClusters.value.map(item => item.tripCount)
  : currentData.value.map(item => item.tripCount)), 0))
const currentMonitor = computed(() => hotspotMonitor.value.filter(item => item.zone_type === activeTab.value))
const monitorHotspotCount = computed(() => {
  if (currentMonitor.value.length > 0)
    return currentMonitor.value.reduce((sum, item) => sum + item.hotspot_count, 0)
  return totalZones.value
})
const monitorTotalTrips = computed(() => {
  if (currentMonitor.value.length > 0)
    return currentMonitor.value.reduce((sum, item) => sum + item.total_trip_count, 0)
  return totalTrips.value
})
const strongestMonitorZone = computed(() => currentMonitor.value.reduce<AdsHotspotMonitorDailyMetric | undefined>(
  (max, item) => !max || (item.max_hotspot_trip_count ?? 0) > (max.max_hotspot_trip_count ?? 0) ? item : max,
  undefined,
))
const topHotspot = computed<{ name: string, count: number }>(() => {
  if (strongestMonitorZone.value) {
    return {
      name: strongestMonitorZone.value.max_hotspot_zone_name || strongestMonitorZone.value.max_hotspot_zone_id || '-',
      count: strongestMonitorZone.value.max_hotspot_trip_count ?? 0,
    }
  }
  if (activeTab.value === 'cluster') {
    if (!currentClusters.value.length) return { name: '-', count: 0 }
    const top = currentClusters.value.reduce((a, b) => b.tripCount > a.tripCount ? b : a)
    return { name: top.clusterType, count: top.tripCount }
  }
  if (!currentData.value.length) return { name: '-', count: 0 }
  const top = currentData.value.reduce((a, b) => b.tripCount > a.tripCount ? b : a)
  return { name: top.zoneName, count: top.tripCount }
})
const mapPoints = computed<HotspotMapPoint[]>(() => {
  if (activeTab.value === 'cluster') {
    return currentClusters.value
      .filter(item => item.centerLon && item.centerLat)
      .map(item => ({
        id: String(item.clusterId),
        name: item.clusterType,
        type: '自然热点',
        lon: item.centerLon,
        lat: item.centerLat,
        tripCount: item.tripCount,
      }))
  }

  return currentData.value
    .filter(item => item.lon != null && item.lat != null)
    .map(item => ({
      id: item.zoneId,
      name: item.zoneName,
      type: zoneTypeLabel(item.zoneType),
      lon: item.lon ?? 0,
      lat: item.lat ?? 0,
      tripCount: item.tripCount,
    }))
})

const chartHeight = computed(() => Math.max(340, visualRows.value.length * 22))

const hotspotRankOption = computed<EChartsOption>(() => ({
  color: ['#2563eb'],
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 96, right: 28, top: 12, bottom: 36 },
  xAxis: { type: 'value', name: '行程数', axisLabel: { fontSize: 11 } },
  yAxis: {
    type: 'category',
    inverse: true,
    data: visualRows.value.map(item => item.name),
    axisLabel: {
      fontSize: 11,
      width: 80,
      overflow: 'truncate',
    },
  },
  series: [
    {
      name: '行程数',
      type: 'bar',
      data: visualRows.value.map(item => item.tripCount),
      label: {
        show: true,
        position: 'right',
        fontSize: 11,
        formatter: (params: any) => formatNumber(Number(params.value)),
      },
    },
  ],
}))

async function loadHotspotMonitor() {
  monitorLoading.value = true
  try {
    const hour = timeMode.value === 'hour' ? selectedHour.value : undefined
    const date = timeMode.value === 'all' ? undefined : selectedDate.value
    const { items } = await getAdsHotspotMonitorDaily(timeMode.value, date, hour)
    hotspotMonitor.value = items
  }
  finally {
    monitorLoading.value = false
  }
}

async function loadHotspotZones() {
  zoneLoading.value = true
  try {
    const hour = timeMode.value === 'hour' ? selectedHour.value : undefined
    const result = await getPageHotspotZones(activeTab.value, selectedDate.value, hour, 200)
    hotspotZones.value = result.items
    totalZones.value = result.total
    await nextTick()
    refreshMap()
  }
  finally {
    zoneLoading.value = false
  }
}

function zoneTypeLabel(type: string) {
  return ({ district: '行政区', grid: '网格', poi: '重点场所', cluster: '自然热点' } as Record<string, string>)[type] ?? type
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
  hotspotLayer = L.layerGroup().addTo(map)
  window.setTimeout(() => {
    map.invalidateSize()
    refreshMap()
  }, 200)
}

function refreshMap() {
  const L = (window as any).L
  if (!L || !map || !hotspotLayer)
    return
  hotspotLayer.clearLayers()
  if (heatLayer) {
    map.removeLayer(heatLayer)
    heatLayer = null
  }
  if (!mapPoints.value.length) return

  const maxValue = Math.max(...mapPoints.value.map(item => item.tripCount), 1)

  // 用热力图表达密度，避免大圆叠加视觉杂乱
  if (typeof (L as any).heatLayer === 'function') {
    const heatData = mapPoints.value.map((item) => {
      const intensity = Math.max(0.2, Math.min(1, item.tripCount / maxValue))
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

  // 只为 Top 12 点位添加可点击 marker，便于查看详情
  const topPoints = [...mapPoints.value]
    .sort((a, b) => b.tripCount - a.tripCount)
    .slice(0, 12)
  topPoints.forEach((item) => {
    L.circleMarker([item.lat, item.lon], {
      radius: 4,
      color: '#ffffff',
      weight: 1,
      fillColor: '#1d4ed8',
      fillOpacity: 0.95,
    }).bindPopup(`
      <strong>${item.name}</strong><br/>
      类型：${item.type}<br/>
      行程量：${formatNumber(item.tripCount)}
    `).addTo(hotspotLayer)
  })

  const bounds = L.latLngBounds(mapPoints.value.map(item => [item.lat, item.lon]))
  map.fitBounds(bounds.pad(0.2), { maxZoom: 13 })
}

watch([activeTab, timeMode, selectedDate, selectedHour], loadHotspotZones)
watch([timeMode, selectedDate, selectedHour], loadHotspotMonitor)

onMounted(async () => {
  const ready = await waitForLeaflet()
  if (!ready) {
    initError.value = 'Leaflet 地图库加载失败，请检查网络连接'
    return
  }
  await nextTick()
  initMap()
})

onMounted(loadHotspotMonitor)
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
          区域出行统计
        </div>
        <h1 class="page-title">
          热点区域分析
        </h1>
        <p class="page-subtitle">
          按行政区、网格、重点场所和自然聚集区域查看行程数、上车数、下车数、平均距离和车辆覆盖。
        </p>
      </div>
      <el-space wrap>
        <el-segmented v-model="activeTab" :options="tabs" />
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

    <div v-loading="zoneLoading" class="content-grid grid-3">
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-chart-relationship />当前口径行程量
        </div>
        <div class="metric-value">
          {{ formatNumber(totalTrips) }}
        </div>
        <div class="metric-foot">
          {{ scopeText() }}
        </div>
      </div>
      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-location />热点对象数
        </div>
        <div class="metric-value">
          {{ totalZones }}
        </div>
        <div class="metric-foot">
          用于按区域查看出行集中度
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-flag />最高单点行程
        </div>
        <div class="metric-value">
          {{ formatNumber(maxTrips) }}
        </div>
        <div class="metric-foot">
          热点强度峰值
        </div>
      </div>
    </div>

    <div v-loading="monitorLoading" class="content-grid grid-3">
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-location-star />当前口径热点总数
        </div>
        <div class="metric-value">
          {{ formatNumber(monitorHotspotCount) }}
        </div>
        <div class="metric-foot">
          {{ scopeText() }}·{{ tabs.find(t => t.value === activeTab)?.label }}
        </div>
      </div>
      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-flow-data />热点关联行程
        </div>
        <div class="metric-value">
          {{ formatNumber(monitorTotalTrips) }}
        </div>
        <div class="metric-foot">
          {{ tabs.find(t => t.value === activeTab)?.label }}口径出行规模
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-star />最强热点
        </div>
        <div class="metric-value hotspot-name">
          {{ topHotspot.name }}
        </div>
        <div class="metric-foot">
          {{ formatNumber(topHotspot.count) }} 次行程
        </div>
      </div>
    </div>

    <section class="panel">
      <div class="panel-title">
        <h3>热点强度排序</h3>
        <span class="muted">按当前区域口径排序</span>
      </div>
      <BaseChart v-loading="zoneLoading" :option="hotspotRankOption" :height="chartHeight + 'px'" />
    </section>

    <section class="panel">
      <div class="panel-title">
        <h3>热点监测概览</h3>
        <span class="muted">按行政区、网格、重点场所汇总</span>
      </div>
      <el-table v-loading="monitorLoading" :data="hotspotMonitor" stripe>
        <el-table-column label="口径" width="120">
          <template #default="{ row }">
            {{ zoneTypeLabel(row.zone_type) }}
          </template>
        </el-table-column>
        <el-table-column label="热点数" width="120">
          <template #default="{ row }">
            {{ formatNumber(row.hotspot_count) }}
          </template>
        </el-table-column>
        <el-table-column label="行程数" width="140">
          <template #default="{ row }">
            {{ formatNumber(row.total_trip_count) }}
          </template>
        </el-table-column>
        <el-table-column label="上车" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.total_pickup_count) }}
          </template>
        </el-table-column>
        <el-table-column label="下车" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.total_dropoff_count) }}
          </template>
        </el-table-column>
        <el-table-column label="最高热点" min-width="180">
          <template #default="{ row }">
            {{ row.max_hotspot_zone_name || row.max_hotspot_zone_id || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="最高热点行程" width="150">
          <template #default="{ row }">
            {{ formatNumber(row.max_hotspot_trip_count ?? 0) }}
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="panel map-panel">
      <div class="map-toolbar">
        <div>
          <h3>热点空间分布</h3>
          <span>{{ scopeText() }}，点大小按行程量缩放。</span>
        </div>
        <el-button text type="primary" @click="$router.push('/hotspot-map')">
          进入地图专题
        </el-button>
      </div>
      <el-empty v-if="initError" :description="initError" />
      <div v-else class="map-frame">
        <div ref="mapContainer" class="map-container" />
      </div>
    </section>

    <section class="panel">
      <div class="panel-title">
        <h3>热点明细</h3>
        <span class="muted">上车、下车、均距、均时、车辆覆盖</span>
      </div>
      <el-table v-if="activeTab !== 'cluster'" v-loading="zoneLoading" :data="currentData" height="520" stripe>
        <el-table-column prop="zoneName" label="区域名称" min-width="160" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag effect="light">
              {{ zoneTypeLabel(row.zoneType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="行程数" sortable prop="tripCount" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.tripCount) }}
          </template>
        </el-table-column>
        <el-table-column label="上车" width="120">
          <template #default="{ row }">
            {{ formatNumber(row.pickupCount) }}
          </template>
        </el-table-column>
        <el-table-column label="下车" width="120">
          <template #default="{ row }">
            {{ formatNumber(row.dropoffCount) }}
          </template>
        </el-table-column>
        <el-table-column prop="avgTripDistance" label="均距(km)" width="120" />
        <el-table-column prop="avgDuration" label="均时(s)" width="120" />
        <el-table-column label="车辆数" width="120">
          <template #default="{ row }">
            {{ formatNumber(row.vehicleCount) }}
          </template>
        </el-table-column>
      </el-table>
      <el-table v-else v-loading="zoneLoading" :data="currentClusters" height="520" stripe>
        <el-table-column prop="clusterId" label="热点编号" width="100" />
        <el-table-column prop="clusterType" label="类型" min-width="150" />
        <el-table-column prop="centerLon" label="中心经度" width="120" />
        <el-table-column prop="centerLat" label="中心纬度" width="120" />
        <el-table-column label="行程数" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.tripCount) }}
          </template>
        </el-table-column>
        <el-table-column label="上车" width="120">
          <template #default="{ row }">
            {{ formatNumber(row.pickupCount) }}
          </template>
        </el-table-column>
        <el-table-column label="下车" width="120">
          <template #default="{ row }">
            {{ formatNumber(row.dropoffCount) }}
          </template>
        </el-table-column>
        <el-table-column prop="avgDuration" label="均时(s)" width="120" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.map-panel {
  min-height: 460px;
  padding: 0;
  overflow: hidden;
}

.map-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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
  height: 400px;
}

.map-container {
  width: 100%;
  height: 100%;
}

.hotspot-name {
  font-size: 24px;
}
</style>
