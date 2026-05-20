<script setup lang="ts">
import { getPageRoadStatus } from '../api/pages'
import type { RoadStatusPageResponse } from '../api/pages'
import { availableDates, formatNumber, statusType } from '../data/traffic'

defineOptions({
  name: 'RoadStatusPage',
})

const selectedDate = ref('2015-01-05')
const selectedHour = ref(8)
const selectedStatus = ref('全部')
const selectedDistrict = ref('全部')
const loading = ref(false)
const roadStatus = ref<RoadStatusPageResponse | null>(null)

const statuses = ['全部', '严重拥堵', '中度拥堵', '轻度拥堵', '基本畅通', '畅通']

const requestStatus = computed(() =>
  selectedStatus.value === '全部' ? undefined : selectedStatus.value,
)

const districts = computed(() => [
  '全部',
  ...Array.from(
    new Set(
      roadStatus.value?.items
        .map(item => item.district_name)
        .filter(Boolean) as string[],
    ),
  ),
])

const filteredRoads = computed(() =>
  (roadStatus.value?.items ?? []).filter((item) => {
    const districtMatched =
      selectedDistrict.value === '全部' || item.district_name === selectedDistrict.value

    return districtMatched
  }),
)

const statusCounts = computed(() => {
  const total = roadStatus.value?.summary.total_roads ?? 0
  const items = roadStatus.value?.items ?? []

  return {
    total,
    severe: roadStatus.value?.summary.severe_congested_roads ?? 0,
    congested: Math.max(
      0,
      (roadStatus.value?.summary.congested_roads ?? 0)
        - (roadStatus.value?.summary.severe_congested_roads ?? 0),
    ),
    basicSmooth: items.filter(item => item.status === '基本畅通').length,
    smooth: items.filter(item => item.status === '畅通').length,
  }
})

const maxFlow = computed(() =>
  Math.max(...(roadStatus.value?.items ?? []).map(item => item.current_flow ?? 0), 1),
)

const congestionPct = computed(() =>
  normalizePct(roadStatus.value?.summary.congestion_pct ?? 0),
)

function normalizePct(value: number) {
  return value > 0 && value <= 1 ? value * 100 : value
}

async function loadRoadStatus() {
  loading.value = true

  try {
    roadStatus.value = await getPageRoadStatus(
      selectedDate.value,
      selectedHour.value,
      100,
      requestStatus.value,
    )
  }
  finally {
    loading.value = false
  }
}

watch([selectedDate, selectedHour, selectedStatus], () => {
  selectedDistrict.value = '全部'
  loadRoadStatus()
})

onMounted(loadRoadStatus)
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <div class="page-kicker">
          道路运行状态
        </div>

        <h1 class="page-title">
          路况监测
        </h1>

        <p class="page-subtitle">
          面向调度和值守人员按日期、小时、行政区和拥堵状态定位问题路段，辅助快速处置和复盘。
        </p>
      </div>

      <div class="query-form">
        <div class="query-row">
          <label>日期</label>
          <el-select v-model="selectedDate" style="width: 140px">
            <el-option
              v-for="date in availableDates"
              :key="date"
              :label="date"
              :value="date"
            />
          </el-select>
        </div>

        <div class="query-row">
          <label>小时</label>
          <el-select v-model="selectedHour" style="width: 140px">
            <el-option
              v-for="hour in 24"
              :key="hour - 1"
              :label="`${hour - 1}:00`"
              :value="hour - 1"
            />
          </el-select>
        </div>
      </div>
    </div>

    <div v-loading="loading" class="content-grid grid-4">
      <div class="metric-card tone-blue">
        <div class="metric-top">
          <span i-carbon-road />
          监测样本路段
        </div>

        <div class="metric-value">
          {{ statusCounts.total }}
        </div>

        <div class="metric-foot">
          当前展示核心路段清单
        </div>
      </div>

      <div class="metric-card tone-orange">
        <div class="metric-top">
          <span i-carbon-warning />
          拥堵道路
        </div>

        <div class="metric-value danger">
          {{ statusCounts.severe + statusCounts.congested }}
        </div>

        <div class="metric-foot">
          含严重拥堵 {{ statusCounts.severe }} 条
        </div>
      </div>

      <div class="metric-card tone-green">
        <div class="metric-top">
          <span i-carbon-meter />
          全网均速
        </div>

        <div class="metric-value">
          {{ (roadStatus?.summary.avg_speed ?? 0).toFixed(1) }} km/h
        </div>

        <div class="metric-foot">
          {{ selectedHour }}:00 运行状态
        </div>
      </div>

      <div class="metric-card tone-purple">
        <div class="metric-top">
          <span i-carbon-chart-line />
          拥堵率
        </div>

        <div class="metric-value warning">
          {{ congestionPct.toFixed(1) }}%
        </div>

        <div class="metric-foot">
          拥堵道路 {{ formatNumber(roadStatus?.summary.congested_roads ?? 0) }} 条
        </div>
      </div>
    </div>

    <section class="panel">
      <div class="panel-title">
        <h3>道路状态筛选</h3>

        <el-space wrap>
          <el-segmented v-model="selectedStatus" :options="statuses" />

          <el-select v-model="selectedDistrict" style="width: 140px">
            <el-option
              v-for="district in districts"
              :key="district"
              :label="district"
              :value="district"
            />
          </el-select>
        </el-space>
      </div>

      <el-table v-loading="loading" :data="filteredRoads" height="560" stripe>
        <el-table-column prop="road_id" label="路段编号" width="96" />

        <el-table-column label="路段" min-width="170">
          <template #default="{ row }">
            <strong>{{ row.road_name || `道路 ${row.road_id}` }}</strong>

            <div class="muted text-xs">
              {{ row.district_name || '-' }} · {{ row.road_class || '-' }}
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="当前速度"
          width="130"
          sortable
          prop="current_speed"
        >
          <template #default="{ row }">
            <span class="speed-value">
              {{ (row.current_speed ?? 0).toFixed(1) }} km/h
            </span>
          </template>
        </el-table-column>

        <el-table-column label="流量强度" min-width="180">
          <template #default="{ row }">
            <div class="flow-cell">
              <el-progress
                :percentage="Math.round((row.current_flow ?? 0) / maxFlow * 100)"
                :show-text="false"
                :stroke-width="8"
              />

              <span>{{ formatNumber(row.current_flow ?? 0) }} 辆/h</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          prop="congestion_idx"
          label="拥堵指数"
          sortable
          width="128"
        />

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status || '')" effect="light">
              {{ row.status || '-' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.query-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.query-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.query-row label {
  width: 40px;
  text-align: right;
  color: #606266;
  font-size: 14px;
  line-height: 32px;
}

.query-form :deep(.el-form-item__content) {
  height: 32px;
  line-height: 32px;
  display: inline-flex;
  align-items: center;
}

.danger {
  color: #ef4444;
}

.warning {
  color: #f59e0b;
}

.speed-value {
  font-weight: 720;
}

.flow-cell {
  display: grid;
  grid-template-columns: 1fr 78px;
  align-items: center;
  gap: 10px;
}
</style>