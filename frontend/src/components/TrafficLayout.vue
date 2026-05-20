<script setup lang="ts">
defineOptions({
  name: 'TrafficLayout',
})

const route = useRoute()
const router = useRouter()

const menuGroups = [
  {
    title: '监测指挥',
    items: [
      { name: '运行概览', icon: 'i-carbon-dashboard', path: '/dashboard' },
      { name: '路况监测', icon: 'i-carbon-traffic-incident', path: '/road-status' },
      { name: '全网路况', icon: 'i-carbon-road', path: '/network-status' },
      { name: '路网地图', icon: 'i-carbon-map', path: '/map' },
    ],
  },
  {
    title: '专题分析',
    items: [
      { name: '拥堵排行', icon: 'i-carbon-list-boxes', path: '/congestion' },
      { name: '热点区域', icon: 'i-carbon-location', path: '/hotspot' },
      { name: '出行特征', icon: 'i-carbon-analytics', path: '/trip-features' },
      { name: '轨迹分布', icon: 'i-carbon-direction-right-01', path: '/trajectory-map' },
      { name: '重点区域地图', icon: 'i-carbon-map', path: '/hotspot-map' },
    ],
  },
]

function go(path: string) {
  if (route.path !== path) router.push(path)
}
</script>

<template>
  <el-container class="traffic-layout">
    <el-aside class="layout-aside" width="260px">
      <div class="brand-block" @click="go('/dashboard')">
        <div class="brand-mark">
          <div i-carbon-road />
        </div>
        <div>
          <div class="brand-title">交通运行管理平台</div>
          <div class="brand-subtitle">哈尔滨出租车轨迹分析</div>
        </div>
      </div>

      <nav class="side-nav">
        <section v-for="group in menuGroups" :key="group.title" class="nav-group">
          <div class="nav-group-title">{{ group.title }}</div>
          <button
            v-for="item in group.items"
            :key="item.path"
            class="nav-item"
            :class="{ active: route.path === item.path || (route.path === '/' && item.path === '/dashboard') }"
            type="button"
            @click="go(item.path)"
          >
            <span :class="item.icon" />
            <span>{{ item.name }}</span>
          </button>
        </section>
      </nav>
    </el-aside>

    <el-container class="content-container">
      <el-main class="layout-main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.traffic-layout {
  min-height: 100vh;
  background: #f4f7fb;
}

.layout-aside {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  border-right: 1px solid #e4e7ec;
  background: #f8fafc;
  color: #182230;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 86px;
  padding: 18px;
  cursor: pointer;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background: #e8f1ff;
  color: #2563eb;
  font-size: 24px;
}

.brand-title {
  font-size: 17px;
  font-weight: 760;
}

.brand-subtitle {
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
}

.side-nav {
  padding: 0 12px 20px;
}

.nav-group {
  margin-top: 14px;
}

.nav-group-title {
  padding: 0 10px 8px;
  color: #667085;
  font-size: 12px;
  font-weight: 700;
}

.nav-item {
  display: flex;
  width: 100%;
  height: 42px;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #475467;
  cursor: pointer;
  font: inherit;
  padding: 0 12px;
  text-align: left;
}

.nav-item:hover {
  background: #eef4ff;
  color: #1d4ed8;
}

.nav-item > span:first-child {
  flex: 0 0 auto;
  color: #344054;
  font-size: 18px;
}

.nav-item:hover > span:first-child,
.nav-item.active > span:first-child {
  color: #1d4ed8;
}

.nav-item.active {
  background: #dbeafe;
  color: #1d4ed8;
  font-weight: 700;
}

.content-container {
  min-width: 0;
}

.layout-main {
  min-width: 0;
  padding: 24px 28px 36px;
}

@media (max-width: 900px) {
  .layout-aside {
    display: none;
  }

  .layout-main {
    padding: 18px;
  }
}
</style>
