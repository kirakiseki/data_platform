<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import type { AdsCongestionHourlyMetric } from '../api/ads'
import { getAdsCongestionHourly } from '../api/ads'
import { getPageCongestionRoadsGeojson, getPageCongestionRoadsRanking } from '../api/pages'
import type { CongestionRoadRankingItem } from '../api/pages'
import { availableDates, formatNumber } from '../data/traffic'

defineOptions({
  name: 'CongestionPage',
})

const MAP_PAGE_SIZE = 2000
const MAP_MAX_PAGES = 20
const RANKING_LIMIT = 20

const selectedScope = ref<'拥堵指数' | '道路流量'>('拥堵指数')
const selectedDate = ref(availableDates[2])
const selectedHour = ref(8)
const loading = ref(false)
const mapLoading = ref(false)
const congestionHourly = ref<AdsCongestionHourlyMetric[]>([])
const rankedRoads = ref<RankedRoad[]>([])
const mapContainer = ref<HTMLDivElement>()
const initError = ref('')

let map: any = null
let congestionLayer: any = null
let mapMoveTimer: number | undefined
let mapAbortController: AbortController | null = null
const mapRoadCount = ref(0)
const mapTruncated = ref(false)

interface RankedRoad {
  rank: number
  road_id: number
  road_name: string
  congestion_idx: number
  avg_speed: number
  trip_count: number
  status: string
}

const scopeOptions = [
  { label: '拥堵指数', value: '拥堵指数' },
  { label: '道路流量', value: '道路流量' },
]

function roadColor(status: string) {
  if (status === '严重拥堵')
    return '#FF0000'
  if (status === '中度拥堵')
    return '#FF9900'
  if (status === '轻度拥堵')
    return '#FFFF00'
  if (status === '基本畅通')
    return '#99CC00'
  return '#008000'
}

function statusByCongestion(value: number) {
  // CI = Vf/Vkj — thresholds from GB/T 33171 Table 2
  if (value > 10 / 3)
    return '严重拥堵'
  if (value > 2.5)
    return '中度拥堵'
  if (value > 2.0)
    return '轻度拥堵'
  if (value > 10 / 7)
    return '基本畅通'
  return '畅通'
}

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === '严重拥堵' || status === '中度拥堵')
    return 'danger'
  if (status === '轻度拥堵')
    return 'warning'
  if (status === '畅通' || status === '基本畅通')
    return 'success'
  return 'info'
}

function toRankedRoad(item: CongestionRoadRankingItem, index: number): RankedRoad {
  const congestionIdx = item.congestion_idx ?? 0
  // 后端在 trip_count<=3 时把 status / congestion_idx 都置 NULL，前端不再用
  // statusByCongestion 兜底（兜底会用 OSM 路牌限速时代的旧阈值，
  // 错把稀疏样本贴上"严重拥堵"标签）。直接显示后端给的 status，
  // null/空 时显示"无数据"。
  return {
    rank: index + 1,
    road_id: item.road_id,
    road_name: item.road_name || `道路 ${item.road_id}`,
    congestion_idx: congestionIdx,
    avg_speed: item.avg_speed ?? 0,
    trip_count: item.trip_count ?? 0,
    status: item.status || '无数据',
  }
}

function getMapBbox(): { minLng: number, minLat: number, maxLng: number, maxLat: number } | undefined {
  if (!map)
    return undefined
  const bounds = map.getBounds()
  if (!bounds || !bounds.isValid())
    return undefined
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  return { minLng: sw.lng, minLat: sw.lat, maxLng: ne.lng, maxLat: ne.lat }
}

// 按 zoom 估算地理简化容差（度）：~ 一个屏幕像素对应的经纬度跨度
// zoom 18 → 0；zoom 12 → ~0.0003 度（≈30m）；zoom 9 → ~0.003 度
function simplifyToleranceFromZoom(zoom: number): number {
  if (zoom >= 17)
    return 0
  const pixelDeg = 360 / (256 * 2 ** zoom)
  return Number((pixelDeg * 1.5).toFixed(6))
}

async function loadHourlyTrend() {
  const hourly = await getAdsCongestionHourly(selectedDate.value)
  congestionHourly.value = hourly.items
}

async function loadRanking() {
  const sortBy = selectedScope.value === '道路流量' ? 'flow' : 'congestion'
  const resp = await getPageCongestionRoadsRanking(
    selectedDate.value,
    selectedHour.value,
    sortBy,
    RANKING_LIMIT,
  )
  rankedRoads.value = resp.items.map((item, index) => toRankedRoad(item, index))
}

async function loadMapRoads() {
  if (!map)
    return
  const bbox = getMapBbox()
  if (!bbox)
    return

  // 取消上一轮还没跑完的分页请求
  if (mapAbortController) {
    mapAbortController.abort()
  }
  const controller = new AbortController()
  mapAbortController = controller

  const tolerance = simplifyToleranceFromZoom(map.getZoom())
  mapLoading.value = true
  mapTruncated.value = false
  clearMapLayer()
  mapRoadCount.value = 0

  try {
    let cursor: number | undefined
    let pageIndex = 0
    while (pageIndex < MAP_MAX_PAGES) {
      const resp = await getPageCongestionRoadsGeojson(
        selectedDate.value,
        selectedHour.value,
        MAP_PAGE_SIZE,
        {
          allRoads: true,
          bbox,
          cursor,
          simplifyTolerance: tolerance,
          signal: controller.signal,
        },
      )
      if (controller.signal.aborted)
        return
      appendMapFeatures(resp.features)
      mapRoadCount.value += resp.features.length
      pageIndex += 1
      if (resp.next_cursor === null || resp.next_cursor === undefined) {
        return
      }
      cursor = resp.next_cursor
    }
    mapTruncated.value = true
  }
  catch (err: any) {
    // 取消请求不算错误
    if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED' || controller.signal.aborted)
      return
    throw err
  }
  finally {
    if (mapAbortController === controller) {
      mapAbortController = null
      mapLoading.value = false
    }
  }
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadHourlyTrend(), loadRanking(), loadMapRoads()])
  }
  finally {
    loading.value = false
  }
}

const topRankingOption = computed<EChartsOption>(() => {
  const isFlow = selectedScope.value === '道路流量'
  const top = rankedRoads.value.slice(0, 8)
  return {
    color: [isFlow ? '#2563eb' : '#ef4444'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 0, data: [selectedScope.value] },
    grid: { left: 80, right: 48, top: 28, bottom: 48 },
    xAxis: {
      type: 'value',
      name: isFlow ? '行程数' : '指数',
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: top.map(item => item.road_name),
    },
    series: [
      {
        name: selectedScope.value,
        type: 'bar',
        data: top.map(item => (isFlow ? item.trip_count : item.congestion_idx)),
      },
    ],
  }
})

const hourCongestionOption = computed<EChartsOption>(() => ({
  color: ['#ef4444'],
  tooltip: { trigger: 'axis' },
  grid: { left: 42, right: 20, top: 24, bottom: 32 },
  xAxis: { type: 'category', data: congestionHourly.value.map(item => `${item.hour}:00`) },
  yAxis: { type: 'value', name: '指数' },
  series: [
    { name: '平均拥堵指数', type: 'line', smooth: true, areaStyle: { opacity: 0.12 }, data: congestionHourly.value.map(item => item.avg_congestion ?? 0) },
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

  map = L.map(mapContainer.value, { zoomControl: false }).setView([45.745, 126.635], 12)
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map)
  congestionLayer = L.layerGroup().addTo(map)

  map.on('moveend', () => {
    if (mapMoveTimer)
      window.clearTimeout(mapMoveTimer)
    mapMoveTimer = window.setTimeout(() => {
      loadMapRoads()
    }, 350)
  })

  window.setTimeout(() => {
    map.invalidateSize()
    loadMapRoads()
  }, 200)
}

function clearMapLayer() {
  if (congestionLayer)
    congestionLayer.clearLayers()
}

function appendMapFeatures(features: any[]) {
  const L = (window as any).L
  if (!L || !map || !congestionLayer || !features.length)
    return
  L.geoJSON(
    { type: 'FeatureCollection', features },
    {
      style: (feature: any) => ({
        color: roadColor(feature.properties.status || statusByCongestion(feature.properties.congestion_idx ?? 0)),
        weight: 2,
        opacity: 0.86,
      }),
      onEachFeature: (feature: any, layer: any) => {
        const props = feature.properties
        layer.bindPopup(`
          <strong>${props.road_name || `道路 ${props.road_id}`}</strong><br/>
          状态：${props.status || '-'}<br/>
          均速：${(props.avg_speed ?? 0).toFixed(1)} km/h<br/>
          拥堵指数：${(props.congestion_idx ?? 0).toFixed(2)}
        `)
      },
    },
  ).addTo(congestionLayer)
}

onMounted(async () => {
  const ready = await waitForLeaflet()
  if (!ready) {
    initError.value = 'Leaflet 地图库加载失败，请检查网络连接'
    return
  }
  await nextTick()
  initMap()
  // 表格、柱状图、时段曲线（不依赖地图）独立加载
  loading.value = true
  try {
    await Promise.all([loadHourlyTrend(), loadRanking()])
  }
  finally {
    loading.value = false
  }
})

watch([selectedDate, selectedHour], () => loadAll())
watch(selectedScope, () => loadRanking())

onUnmounted(() => {
  if (mapMoveTimer)
    window.clearTimeout(mapMoveTimer)
  if (mapAbortController) {
    mapAbortController.abort()
    mapAbortController = null
  }
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
          拥堵路段统计
        </div>
        <h1 class="page-title">
          拥堵排行
        </h1>
        <p class="page-subtitle">
          按道路拥堵指数或道路流量排序，查看高峰时段的重点路段。
        </p>
      </div>
      <el-space wrap>
        <el-segmented v-model="selectedScope" :options="scopeOptions" />
        <el-select v-model="selectedDate" style="width: 140px">
          <el-option v-for="date in availableDates" :key="date" :label="date" :value="date" />
        </el-select>
        <el-select v-model="selectedHour" style="width: 110px">
          <el-option v-for="hour in 24" :key="hour - 1" :label="`${hour - 1}:00`" :value="hour - 1" />
        </el-select>
      </el-space>
    </div>

    <div v-loading="loading" class="content-grid grid-3">
      <section class="panel">
        <div class="panel-title">
          <h3>拥堵时段分布</h3>
          <span class="muted">全天平均拥堵指数变化</span>
        </div>
        <BaseChart :option="hourCongestionOption" height="280px" />
      </section>

      <section class="panel span-2">
        <div class="panel-title">
          <h3>{{ selectedScope }}排行</h3>
          <span class="muted">全网 Top 8</span>
        </div>
        <BaseChart :option="topRankingOption" height="280px" />
      </section>
    </div>

    <section class="panel map-panel">
      <div class="map-toolbar">
        <div>
          <h3>拥堵路段地图</h3>
          <span>
            {{ selectedDate }} {{ selectedHour }}:00，渲染当前视图范围内所有该时段有数据的道路；
            已加载 {{ mapRoadCount }} 条<span v-if="mapTruncated">（超过分页上限 {{ MAP_MAX_PAGES * MAP_PAGE_SIZE }}，可放大视图查看完整数据）</span>。
          </span>
        </div>
      </div>
      <el-empty v-if="initError" :description="initError" />
      <div v-else v-loading="mapLoading" class="map-frame">
        <div ref="mapContainer" class="map-container" />
      </div>
    </section>

    <section class="panel">
      <div class="panel-title">
        <h3>拥堵路段排行</h3>
        <span class="muted">{{ selectedDate }} {{ selectedHour }}:00 全网 Top {{ rankedRoads.length }}</span>
      </div>
      <el-table v-loading="loading" :data="rankedRoads" height="560" stripe>
        <el-table-column prop="rank" label="排名" width="80" />
        <el-table-column label="路段" min-width="170">
          <template #default="{ row }">
            <strong>{{ row.road_name }}</strong>
            <div class="muted text-xs">
              道路编号 {{ row.road_id }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="congestion_idx" label="拥堵指数" sortable width="128">
          <template #default="{ row }">
            {{ row.congestion_idx.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="avg_speed" label="均速" sortable width="120">
          <template #default="{ row }">
            {{ row.avg_speed.toFixed(1) }} km/h
          </template>
        </el-table-column>
        <el-table-column label="通过行程" sortable prop="trip_count" width="130">
          <template #default="{ row }">
            {{ formatNumber(row.trip_count) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.span-2 {
  grid-column: span 2;
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
  height: 400px;
}

.map-container {
  width: 100%;
  height: 100%;
}

@media (max-width: 1180px) {
  .span-2 {
    grid-column: span 1;
  }
}
</style>
