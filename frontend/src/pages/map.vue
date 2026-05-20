<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { ElMessage } from 'element-plus'
import { getRoadsByBbox, getRoadStats } from '../api/map'
import type { RoadFeature, RoadStats } from '../api/map'
import { formatNumber, roadClassDistribution, roadClassMeta } from '../data/traffic'

defineOptions({
  name: 'MapPage',
})

const MAP_PAGE_SIZE = 2000
const MAP_MAX_PAGES = 20

const mapContainer = ref<HTMLDivElement>()
const loading = ref(false)
const initError = ref('')
const selectedClass = ref('all')
const roadFeatures = ref<RoadFeature[]>([])
const mapTruncated = ref(false)
const roadStats = ref<RoadStats>({
  total_roads: 22304,
  by_class: Object.fromEntries(roadClassDistribution.map(item => [String(item.classId), item.count])),
})

let map: any = null
let layerGroup: any = null
let moveTimer: ReturnType<typeof setTimeout> | undefined
let abortController: AbortController | null = null

const classOptions = [
  { label: '全部道路', value: 'all' },
  ...roadClassDistribution.map(item => ({ label: item.name, value: String(item.classId) })),
]

const totalRoads = computed(() => roadStats.value.total_roads)
const visibleCount = computed(() => roadFeatures.value.length)
const trunkRoadCount = computed(() => roadStats.value.by_class['114'] ?? 0)
const residentialRoadCount = computed(() => roadStats.value.by_class['108'] ?? 0)

const classChartOption = computed<EChartsOption>(() => {
  const items = roadClassDistribution
    .map(item => ({ ...item, current: roadStats.value.by_class[String(item.classId)] ?? item.count }))
  return {
    color: ['#2563eb'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 92, right: 32, top: 24, bottom: 32 },
    xAxis: { type: 'value', name: '道路数' },
    yAxis: {
      type: 'category',
      inverse: true,
      data: items.map(item => item.name),
    },
    series: [
      {
        name: '道路数',
        type: 'bar',
        data: items.map(item => item.current),
        label: { show: true, position: 'right' },
      },
    ],
  }
})

const classTableData = computed(() => {
  const total = totalRoads.value || 1
  return roadClassDistribution.map((item) => {
    const count = roadStats.value.by_class[String(item.classId)] ?? item.count
    return {
      classId: item.classId,
      name: item.name,
      color: roadColor(item.classId),
      count,
      pct: count / total * 100,
    }
  }).sort((a, b) => b.count - a.count)
})

function roadColor(classId: number) {
  return roadClassMeta[String(classId)]?.color ?? '#409eff'
}

function roadLabel(classId: number) {
  return roadClassMeta[String(classId)]?.label ?? `class ${classId}`
}

function waitForLeaflet(maxRetries = 25): Promise<boolean> {
  return new Promise((resolve) => {
    let retries = 0
    const check = () => {
      if ((window as any).L) return resolve(true)
      retries += 1
      if (retries >= maxRetries) return resolve(false)
      window.setTimeout(check, 120)
    }
    check()
  })
}

async function loadStats() {
  try {
    roadStats.value = await getRoadStats()
  } catch (error) {
    console.warn('Use local road stats fallback:', error)
  }
}

// zoom 18 → 0; zoom 12 → ~0.0003 度 (~30m)
function simplifyToleranceFromZoom(zoom: number): number {
  if (zoom >= 17) return 0
  const pixelDeg = 360 / (256 * 2 ** zoom)
  return Number((pixelDeg * 1.5).toFixed(6))
}

function initMap() {
  if (!mapContainer.value) return
  const L = (window as any).L
  if (!L) {
    initError.value = 'Leaflet 地图库加载失败'
    return
  }

  map = L.map(mapContainer.value, { zoomControl: false }).setView([45.75, 126.63], 12)
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map)

  layerGroup = L.layerGroup().addTo(map)

  window.setTimeout(() => {
    map.invalidateSize()
    loadRoadsForViewport()
  }, 200)

  map.on('moveend zoomend', () => {
    if (moveTimer) window.clearTimeout(moveTimer)
    moveTimer = window.setTimeout(loadRoadsForViewport, 350)
  })
}

function clearMapLayer() {
  if (layerGroup) layerGroup.clearLayers()
  roadFeatures.value = []
}

function appendFeatures(features: RoadFeature[]) {
  const L = (window as any).L
  if (!L || !map || !layerGroup || !features.length) return
  L.geoJSON(
    { type: 'FeatureCollection', features },
    {
      style: (feature: any) => ({
        color: roadColor(feature.properties.class_id),
        weight: feature.properties.class_id === 106 ? 3 : 2,
        opacity: 0.82,
      }),
      onEachFeature: (feature: any, layer: any) => {
        layer.bindPopup(`
          <strong>道路 ${feature.properties.gid}</strong><br/>
          类型：${roadLabel(feature.properties.class_id)}<br/>
          长度：${Number(feature.properties.length || 0).toFixed(0)} m<br/>
          限速：${feature.properties.maxspeed_forward || '-'} km/h
        `)
      },
    },
  ).addTo(layerGroup)
}

async function loadRoadsForViewport() {
  if (!map) return
  const bounds = map.getBounds()
  if (!bounds || !bounds.isValid()) return
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()

  if (abortController) {
    abortController.abort()
  }
  const controller = new AbortController()
  abortController = controller

  const tolerance = simplifyToleranceFromZoom(map.getZoom())
  const classId = selectedClass.value === 'all' ? undefined : Number(selectedClass.value)

  loading.value = true
  mapTruncated.value = false
  clearMapLayer()

  try {
    let cursor: number | undefined
    let pageIndex = 0
    while (pageIndex < MAP_MAX_PAGES) {
      const resp = await getRoadsByBbox(
        sw.lng, sw.lat, ne.lng, ne.lat, MAP_PAGE_SIZE,
        { classId, cursor, simplifyTolerance: tolerance, signal: controller.signal },
      )
      if (controller.signal.aborted) return
      const features = resp.features ?? []
      appendFeatures(features)
      roadFeatures.value = [...roadFeatures.value, ...features]
      pageIndex += 1
      if (resp.next_cursor === null || resp.next_cursor === undefined) {
        return
      }
      cursor = resp.next_cursor
    }
    mapTruncated.value = true
  }
  catch (error: any) {
    if (error?.name === 'CanceledError' || error?.code === 'ERR_CANCELED' || controller.signal.aborted) {
      return
    }
    console.error('Failed to load roads:', error)
    ElMessage.warning('道路数据暂不可用，已保留地图底图')
  }
  finally {
    if (abortController === controller) {
      abortController = null
      loading.value = false
    }
  }
}

watch(selectedClass, loadRoadsForViewport)

onMounted(async () => {
  await loadStats()
  const ready = await waitForLeaflet()
  if (!ready) {
    initError.value = 'Leaflet 地图库加载失败，请检查网络连接'
    return
  }
  await nextTick()
  initMap()
})

onUnmounted(() => {
  if (moveTimer) window.clearTimeout(moveTimer)
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="page-shell map-page">
    <div class="page-header">
      <div>
        <div class="page-kicker">城市道路空间视图</div>
        <h1 class="page-title">路网地图</h1>
        <p class="page-subtitle">
          按当前地图范围分页加载哈尔滨道路网络，并按道路等级着色展示。同时呈现道路类型构成统计。
        </p>
      </div>
      <el-space wrap>
        <el-select v-model="selectedClass" style="width: 190px">
          <el-option v-for="option in classOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="loadRoadsForViewport">刷新地图范围</el-button>
      </el-space>
    </div>

    <div class="content-grid grid-4">
      <div class="metric-card tone-blue">
        <div class="metric-top"><span i-carbon-road />道路总数</div>
        <div class="metric-value">{{ formatNumber(totalRoads) }}</div>
        <div class="metric-foot">哈尔滨重点道路网络</div>
      </div>
      <div class="metric-card tone-green">
        <div class="metric-top"><span i-carbon-map />当前视口</div>
        <div class="metric-value">{{ formatNumber(visibleCount) }}</div>
        <div class="metric-foot">
          随地图范围动态分页加载<span v-if="mapTruncated">（超过 {{ MAP_MAX_PAGES * MAP_PAGE_SIZE }} 上限，可放大）</span>
        </div>
      </div>
      <div class="metric-card tone-orange">
        <div class="metric-top"><span i-carbon-direction-straight-right />主干路</div>
        <div class="metric-value">{{ formatNumber(trunkRoadCount) }}</div>
        <div class="metric-foot">城市主要通行道路</div>
      </div>
      <div class="metric-card tone-purple">
        <div class="metric-top"><span i-carbon-home />居住区道路</div>
        <div class="metric-value">{{ formatNumber(residentialRoadCount) }}</div>
        <div class="metric-foot">居住区和支路网络</div>
      </div>
    </div>

    <section class="map-shell panel">
      <div class="map-toolbar">
        <div>
          <h3>哈尔滨路网视图</h3>
          <span>
            拖动或缩放后自动按当前视口分页加载道路。颜色按道路等级标注，已加载 {{ visibleCount }} 条。
          </span>
        </div>
        <div class="legend">
          <span v-for="item in roadClassDistribution" :key="item.classId">
            <i :style="{ background: roadColor(item.classId) }" />
            {{ item.name }}
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
        <h3>道路类型分布</h3>
        <span class="muted">全部道路网络</span>
      </div>
      <BaseChart :option="classChartOption" height="320px" />
      <el-table :data="classTableData" stripe>
        <el-table-column label="道路类型" min-width="150">
          <template #default="{ row }">
            <span class="legend-dot" :style="{ background: row.color }" />
            {{ row.name }}
          </template>
        </el-table-column>
        <el-table-column label="道路数" width="160">
          <template #default="{ row }">{{ formatNumber(row.count) }}</template>
        </el-table-column>
        <el-table-column label="占比" width="120">
          <template #default="{ row }">{{ row.pct.toFixed(1) }}%</template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.map-page {
  min-height: calc(100vh - 128px);
}

.map-shell {
  min-height: 620px;
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

.legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px 14px;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend i {
  display: inline-block;
  width: 18px;
  height: 4px;
  border-radius: 999px;
}

.legend-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  margin-right: 8px;
  vertical-align: middle;
}

.map-frame {
  height: 560px;
}

.map-container {
  width: 100%;
  height: 100%;
}

@media (max-width: 760px) {
  .map-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .legend {
    justify-content: flex-start;
  }
}
</style>
