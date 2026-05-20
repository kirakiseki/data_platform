# 哈尔滨交通管理数据中台

华东师范大学 2026 年春季学期《数据中台》课程大作业（SWEN6211102023）

---

## 目录

- [项目概述](#项目概述)
- [目标受众](#目标受众)
- [数据来源](#数据来源)
- [数据中台概念设计](#数据中台概念设计)
- [数据库表结构设计](#数据库表结构设计)
- [后端设计](#后端设计)
- [前端设计](#前端设计)
- [API 设计](#api-设计)
- [实现亮点](#实现亮点)
- [技术栈](#技术栈)
- [参考文献](#参考文献)

---

## 项目概述

本项目以哈尔滨出租车 GPS 轨迹数据为基础，构建一套完整的**交通管理数据中台**，实现从原始轨迹数据到可视化应用的全链路数据处理。

核心能力：

- 原始 GPS 轨迹 → 地图匹配 → 结构化路网数据的汇聚整合
- ODS → DW → TDM → ADS 四层数据体系的提纯加工
- RESTful API 服务，提供原子数据查询与聚合分析接口
- 交通路况、出行热点、轨迹分析等多维度可视化看板

---

## 目标受众

### 交通管理部门

面向负责城市道路运行监控与拥堵治理的交通执法和管理机构：

- **实时路况监控**：以小时粒度查看哈尔滨主干道及支路的路况等级（依据 GB/T 33171 五级评定：畅通 / 基本畅通 / 轻度拥堵 / 中度拥堵 / 严重拥堵），快速定位拥堵瓶颈路段
- **拥堵态势研判**：通过 Top-N 拥堵路段排行与全网拥堵概况掌握全市道路负荷分布，结合早晚高峰（7-8 时、17-18 时）趋势分析优化信号灯配时方案
- **应急响应支撑**：利用行政区热度分布识别跨区拥堵传导规律，在恶劣天气、大型活动等突发情境下，基于历史同期 OD 数据为应急疏导路线制定提供量化依据

### 城市规划人员

面向负责城市空间布局、道路网络规划及公共交通优化的政府规划部门：

- **出行流量分析**：通过 500m × 500m 网格 OD 矩阵分析全市出行流量分布，识别居住-就业核心走廊，为新路规划和快速路选线提供空间量化依据
- **热点区域评估**：利用 DBSCAN 空间聚类热点定位出租车接送客高密度区域，评估商圈、交通枢纽（火车站、机场、客运站）的实际客流辐射范围与服务能力
- **用地功能支撑**：结合通勤 / 非通勤流向分类（早高峰出发 / 晚高峰返程 / 跨区长途 / 本地短程）分析道路实际承担功能，为土地利用规划调整与公共交通线网优化提供参考

---

## 数据来源

- **来源**：哈尔滨出租车 GPS 轨迹数据集（公开学术数据）
- **时间范围**：2015-01-03 至 2015-01-08（共 6 天）
- **规模**：约 120 万条行程，约 5000 万个 GPS 轨迹点
- **地图底图**：OpenStreetMap 哈尔滨区域道路网络数据（22,304 条有向路段）
- **预处理**：使用 barefoot 对原始 GPS 轨迹进行地图匹配，输出 JLD2 格式匹配结果，再通过 `parse/jld2_to_db.py` 导入数据库

---

## 数据中台概念设计

### 四层架构

```
原始数据 (JLD2/OSM)
        │
        ▼
┌───────────────┐
│   ODS 层      │  贴源层：原样保存地图匹配后的轨迹数据，最小化转换
│               │  ods_trips · ods_trip_gps · ods_trip_roads
│               │  ods_trip_routes · ods_time · ods_poi
└───────┬───────┘
        │ ELT（07_elt_dw.sql）
        ▼
┌───────────────┐
│   DW 层       │  统一数仓层：维度建模、路段流量/节点流量/OD 矩阵聚合
│               │  维度表（道路/节点/行政区/时间/POI/网格）+
│               │  事实表（行程/路段流量/节点流量/OD网格/POI流量等）
└───────┬───────┘
        │ ELT（08_elt_tdm.sql）
        ▼
┌───────────────┐
│   TDM 层      │  标签数据层：面向对象的画像标签体系
│               │  道路画像 · 节点画像 · 车辆运营画像
│               │  行政区标签 · 时段标签
└───────┬───────┘
        │ ELT（09_elt_ads.sql）
        ▼
┌───────────────┐
│   ADS 层      │  应用数据层：面向前端直接消费的预计算聚合结果
│               │  路况/拥堵/出行特征/热点分析/轨迹统计
└───────────────┘
        │
        ▼
  FastAPI 后端 → Vue 3 前端
```

### 分层职责

| 层 | 职责 | 幂等策略 |
|----|------|----------|
| ODS | 原样保存地图匹配后的轨迹数据，附加时间/POI 维度 | `jld2_to_db.py` 全量重导 |
| DW | 从 ODS 提取维度与事实，计算路段流量、节点流量、OD 矩阵 | `INSERT … ON CONFLICT DO UPDATE` |
| TDM | 按实体（道路/节点/车辆）聚合运营画像标签 | `INSERT … ON CONFLICT DO UPDATE` |
| ADS | 按应用场景预计算拥堵指数、热点排名、行程特征分布 | `TRUNCATE + INSERT` 或 `ON CONFLICT DO UPDATE` |

### ELT 而非 ETL

本项目遵循课程所强调的 **ELT（Extract → Load → Transform）** 理念，而非传统的 ETL（先在管道中转换再写入）：

> **原始数据先完整入库（Load），再在数据库内部逐层转换（Transform）**，保留完整的数据追溯链路。

这一选择的优势在于：

- 原始数据语义完整保存于 ODS 层，任何时候可从源头重新计算，数据血缘清晰
- 各层转换逻辑以纯 SQL 表达，无需额外中间件，计算全部在数据库侧完成
- 幂等脚本可重复执行，便于数据错误修复和指标定义迭代
- 当有新到的流式数据（如实时 GPS 上报）需要增量接入时，只需追加写入 ODS 层，下游各层的转换逻辑无需修改，天然支持增量更新

### 数据规模快照

| 层次 | 表数量 | 代表性数据量 |
|------|--------|-------------|
| ODS | 6 | ods_trips 1,194,166 · ods_trip_gps 50,729,499 · ods_trip_roads 47,169,161 |
| DW 维度 | 7 | dw_dim_road 22,304 · dw_dim_node 226,042 · dw_dim_grid 2,437 |
| DW 事实 | 13 | dw_fact_trip 1,194,166 · dw_fact_road_flow_hourly 1,340,791 · dw_fact_od_grid_hourly 1,082,783 |
| TDM | 5 | tdm_tag_vehicle 12,470 · tdm_tag_road 22,304 · tdm_tag_node 226,042 |
| ADS | 19 | ads_road_status_hourly 1,340,791 · ads_hotspot_grid_hourly 156,314 · ads_hotspot_cluster_hourly 3,128 |

---

## 数据库表结构设计

### ODS 层（贴源层）

| 表名 | 行数 | 说明 |
|------|------|------|
| `ods_trips` | 1,194,166 | 行程主表：设备 ID、日期、起终点坐标、时间戳 |
| `ods_trip_gps` | 50,729,499 | GPS 轨迹点：经纬度、时间戳、PostGIS Point |
| `ods_trip_roads` | 47,169,161 | 路段匹配记录：行程 ID、路段 ID、匹配时刻 |
| `ods_trip_routes` | 1,194,166 | 路径信息：路段序列、完整 LineString 几何、总距离 |
| `ods_time` | 144 | 时间维度（日期+小时，覆盖 6 天 × 24 小时） |
| `ods_poi` | 316 | 哈尔滨市区兴趣点（火车站/机场/商圈/医院等 10 类） |

> `start_time` 存储为 Unix 时间戳数值，实际含义为 CST 本地时间；查询时需用 `to_timestamp(x) AT TIME ZONE 'Asia/Shanghai'`

### DW 层（统一数仓层）

**维度表**

| 表名 | 行数 | 说明 |
|------|------|------|
| `dw_dim_road` | 22,304 | 有向路段维度（来源：bfmap_ways + OSM ways） |
| `dw_dim_road_class` | 16 | 道路类型维度（对应 bfmap_ways.class_id） |
| `dw_dim_node` | 226,042 | 道路节点维度（来源：OSM nodes） |
| `dw_dim_district` | 5 | 行政区维度（哈尔滨 5 区，含 MultiPolygon 边界） |
| `dw_dim_time` | 144 | 时间维度（日期 + 小时，来源：ods_time） |
| `dw_dim_poi` | 244 | POI 维度（来源：ods_poi，经去重过滤） |
| `dw_dim_grid` | 2,437 | 500m × 500m 网格维度（由 ADS 热点数据反推） |

**事实表**

| 表名 | 行数 | 说明 |
|------|------|------|
| `dw_fact_trip` | 1,194,166 | 行程事实：起终点、距离、时长、平均速度 |
| `dw_fact_gps_point` | 50,729,499 | GPS 轨迹点事实（与 ods_trip_gps 对应） |
| `dw_fact_road_flow_hourly` | 1,340,791 | 路段小时流量：行程数、平均速度、车辆数 |
| `dw_fact_road_flow_daily` | 99,809 | 路段日流量：行程数、平均速度 |
| `dw_fact_road_travel_time` | 832,674 | 路段行程时间：各行程在每条路段的通行时长 |
| `dw_fact_node_hourly` | 1,147,996 | 节点小时流量：驶入/驶出车辆数 |
| `dw_fact_node_daily` | 76,080 | 节点日流量：驶入/驶出车辆数 |
| `dw_fact_od_grid_hourly` | 1,082,783 | 小时粒度 OD 网格矩阵 |
| `dw_fact_od_grid_daily` | 718,780 | 日粒度 OD 网格矩阵 |
| `dw_fact_od_cluster_hourly` | 442,958 | 小时粒度 DBSCAN 聚类热点 |
| `dw_fact_od_cluster_daily` | 12,819 | 日粒度 DBSCAN 聚类热点 |
| `dw_fact_od_poi_hourly` | 195,719 | 小时粒度 POI OD 流量（起终点 POI 对） |
| `dw_fact_od_poi_daily` | 80,721 | 日粒度 POI OD 流量 |
| `dw_fact_poi_hourly` | 25,868 | POI 小时接送客量 |
| `dw_fact_poi_daily` | 1,450 | POI 日接送客量 |
| `dw_fact_network_hourly` | 120 | 路网小时汇总指标（活跃路段数、总流量、平均速度） |
| `dw_fact_network_daily` | 6 | 路网日汇总指标 |

### TDM 层（标签数据层）

| 表名 | 行数 | 说明 |
|------|------|------|
| `tdm_tag_road` | 22,304 | 道路画像：日均流量、高峰/夜间流量、日均速度 |
| `tdm_tag_node` | 226,042 | 节点画像：日均驶入/驶出量、进出比 |
| `tdm_tag_vehicle` | 12,470 | 车辆运营画像：总行程、里程、高峰/夜间比例、行程距离分档 |
| `tdm_tag_district` | 5 | 行政区基础标签 |
| `tdm_tag_time_slot` | 7 | 时段标签（早高峰/上午/午间/下午/晚高峰/晚间/夜间） |

**车辆画像核心指标**：高峰时段（7、8、17、18 时）行程数及比例、夜间（19-6 时）行程数及比例、短/中/长途（<3km / 3-10km / ≥10km）行程分布

### ADS 层（应用数据层）

| 表名 | 行数 | 说明 |
|------|------|------|
| `ads_road_status_hourly` | 1,340,791 | 路段小时路况：拥堵指数（CI）、5 级路况状态 |
| `ads_network_status_hourly` | 120 | 路网整体小时状态：各级路况路段数量统计 |
| `ads_top_congested_roads_hourly` | 6,000 | Top-N 拥堵路段排行（按拥堵指数/流量） |
| `ads_congestion_hourly` | 120 | 小时粒度全网拥堵概况 |
| `ads_trip_distance_hourly` | 120 | 小时行程距离分布（按短/中/长档） |
| `ads_trip_distance_daily` | 6 | 日行程距离分布 |
| `ads_trip_timeslot_daily` | 6 | 按时段统计出行量 |
| `ads_trip_speed_hourly` | 120 | 小时行程速度分位数统计 |
| `ads_trip_speed_daily` | 6 | 日行程速度分位数统计 |
| `ads_hotspot_grid_hourly` | 156,314 | 小时 500m 网格热度（出发/到达次数） |
| `ads_hotspot_grid_daily` | 12,638 | 日 500m 网格热度 |
| `ads_hotspot_poi_hourly` | 25,868 | 小时 POI 周边热度（接送客量） |
| `ads_hotspot_poi_daily` | 1,450 | 日 POI 周边热度 |
| `ads_hotspot_cluster_hourly` | 3,128 | 小时 DBSCAN 聚类热点区域 |
| `ads_hotspot_cluster_daily` | 1,376 | 日 DBSCAN 聚类热点区域 |
| `ads_hotspot_district_hourly` | 600 | 小时行政区热度 |
| `ads_hotspot_district_daily` | 30 | 日行政区热度 |
| `ads_hotspot_monitor_hourly` | 358 | 小时全局热点监控汇总 |
| `ads_hotspot_monitor_daily` | 18 | 日全局热点监控汇总 |

---

## 后端设计

后端采用分层架构（Router → Service → Model），统一使用 `ResponseBase[T]` 封装所有响应。

```
src/
├── main.py               # FastAPI 应用入口、CORS、路由注册
├── config.toml           # 数据库连接等配置
├── api/                  # 路由层（仅参数解析、响应封装）
│   ├── data/             # 原子数据 API（各层直接查询）
│   ├── pages/            # 组合 API（面向前端页面的聚合接口）
│   ├── roads.py          # bfmap_ways 路段原始数据
│   ├── map_data.py       # 地图渲染底图
│   ├── metadata.py       # 元数据（日期范围、道路等级）
│   ├── heartbeat.py      # 健康检查
│   └── version.py        # 版本信息
├── services/             # 业务逻辑层（SQL 查询、数据组装）
├── schemas/              # Pydantic 请求/响应模型
├── models/               # SQLModel ORM 模型
├── db/                   # 数据库会话管理
└── core/                 # 配置读取、日志、全局状态
```

---

## 前端设计

前端基于 Vue 3 + Vite，采用文件系统路由，共实现以下页面：

| 页面路由 | 功能说明 |
|----------|----------|
| `/` | 系统首页 |
| `/dashboard` | 运行概览（全网流量、出行量、均速与拥堵率概况） |
| `/road-status` | 路况监测列表（日期/小时筛选，道路均速、5 级路况） |
| `/network-status` | 全网路况汇总（24 小时道路畅通、缓行、拥堵占比，以及全网平均速度折线图） |
| `/map` | 路网地图（哈尔滨道路网络，按道路类型着色展示，同时呈现道路类型构成统计） |
| `/congestion` | 拥堵排行（按道路拥堵指数或道路流量排序，按拥堵级别着色，查看高峰时段的重点路段） |
| `/hotspot` | 热点区域分析（按行政区、网格、重点场所和自然聚集区域查看行程数、上车数、下车数、平均距离、车辆覆盖和热点空间分布图） |
| `/trip-features` | 出行特征（查看出租车行程的距离分布、时段分布、速度分布和主要出行方向，包含重点出行方向地图和小时级行程距离结构） |
| `/trajectory-map` | 轨迹分布（随机采样行程在地图上展示，查看轨迹点、道路匹配记录，并在地图上展示典型行程路径） |
| `/hotspot-map` | 重点区域地图可视化（在地图上查看重点场所、网格区域和自然热点的上车、下车与行程集中情况，包含热点分布地图） |

---

## API 设计

### 设计理念：原子 API 与组合 API 分层

数据中台的核心价值之一是将**数据能力服务化**，让数据可以被不同的消费者以不同方式复用，而不是为每个应用单独维护一套数据逻辑。本项目的 API 层体现了这一理念，分为两种类型：

**原子数据 API（`/data/*`）** 对应数据中台"数据资产服务化"的基础层。每个接口职责单一，直接映射一张 DW/TDM/ADS 表的查询能力，无业务逻辑聚合。其优势在于：

- **高复用性**：同一个路段流量接口，既可以被路况地图调用，也可以被统计报表、第三方系统直接消费，数据能力不被绑定在特定场景
- **低耦合**：接口语义稳定，下游应用可自由组合，数据层的变化不会传导到多个业务逻辑层
- **可追溯**：原子接口对应的数据来源清晰，便于追踪指标的数据血缘

**组合 API（`/page/*`）** 对应数据中台"面向应用场景的数据服务"理念，类似 ADS 层的设计思路——针对具体的应用场景进行预聚合，将多个原子查询的结果在服务端组装后一次返回。其优势在于：

- **降低前端复杂度**：仪表盘、地图等页面往往需要 5～10 个维度的数据，单次请求返回完整页面所需数据，避免前端协调多个并发请求
- **性能优化**：服务端聚合可以利用数据库连接池和缓存，比客户端多次串行请求有更低的总延迟
- **关注点分离**：原子 API 由数据层驱动（"有什么数据"），组合 API 由业务层驱动（"这个页面需要什么"），两者职责边界清晰

这一分层设计与数据中台"高内聚、松耦合"的服务化原则一致：原子 API 保障数据能力的**可复用**，组合 API 保障具体应用的**快速响应**。

---

所有接口统一响应格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 原子数据 API（`/data/*`）

直接暴露各数据层的查询能力，供数据分析和第三方集成使用。

#### 路网底图

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/roads` | 路段列表（分页，支持 class_id 过滤） |
| GET | `/roads/{gid}` | 单条路段详情 |
| GET | `/roads/geojson/all` | 全量路段 GeoJSON |
| GET | `/roads/geojson/{gid}` | 单条路段 GeoJSON |
| GET | `/roads/bbox/` | 按 bbox 查询路段列表 |
| GET | `/roads/bbox/geojson` | 按 bbox 查询路段 GeoJSON（keyset 分页、几何简化） |
| GET | `/roads/stats` | 路段统计（总数、按类型分布） |
| GET | `/map/data` | 地图底图数据（全量 bfmap_ways） |

#### 元数据

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/metadata/date-range` | 可用日期范围（2015-01-03 ～ 2015-01-08） |
| GET | `/metadata/road-classes` | 道路类型元数据列表 |

#### DW 层原子查询

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 路段 | GET | `/data/roads/status` | 路段路况查询（日期+小时） |
| | GET | `/data/roads/flow/daily` | 路段日流量 |
| | GET | `/data/roads/travel-time` | 路段行程时间 |
| | GET | `/data/roads/geojson` | 路段 GeoJSON |
| 节点 | GET | `/data/nodes` | 节点列表（分页） |
| | GET | `/data/nodes/{node_id}` | 节点详情 |
| 行程 | GET | `/data/trips` | 行程列表（分页） |
| | GET | `/data/trips/{trip_id}` | 行程详情 |
| | GET | `/data/trips/gps-points` | 行程 GPS 轨迹点 |
| OD | GET | `/data/od/grid/daily` | 日粒度 OD 网格 |
| | GET | `/data/od/grid/hourly` | 小时粒度 OD 网格 |
| | GET | `/data/od/cluster/daily` | 日粒度 OD 聚类热点 |
| | GET | `/data/od/cluster/hourly` | 小时粒度 OD 聚类热点 |
| POI | GET | `/data/poi/flow/daily` | POI 日流量 |
| | GET | `/data/poi/flow/hourly` | POI 小时流量 |
| 路网 | GET | `/data/network/daily` | 路网日汇总指标 |
| | GET | `/data/network/hourly` | 路网小时汇总指标 |
| | GET | `/data/network/summary` | 路网全局统计摘要 |

#### TDM 层标签查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/data/tdm/roads` | 道路画像标签 |
| GET | `/data/tdm/nodes` | 节点画像标签 |
| GET | `/data/tdm/vehicles` | 车辆运营画像列表 |
| GET | `/data/tdm/vehicles/{devid}` | 单辆车辆运营画像详情 |
| GET | `/data/tdm/time-slots` | 时段标签列表 |

#### ADS 层聚合查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/data/ads/roads/status/hourly` | 路段小时路况（含 GeoJSON 几何） |
| GET | `/data/ads/network-status/hourly` | 路网整体小时状态分布 |
| GET | `/data/ads/congestion/hourly` | 小时拥堵概况 |
| GET | `/data/ads/top-congested-roads` | Top-N 拥堵路段 |
| GET | `/data/ads/trips/distance/hourly` | 小时行程距离分布 |
| GET | `/data/ads/trips/distance/daily` | 日行程距离分布 |
| GET | `/data/ads/trips/speed/hourly` | 小时行程速度分位数 |
| GET | `/data/ads/trips/speed/daily` | 日行程速度分位数 |
| GET | `/data/ads/trips/timeslot/daily` | 日时段出行量分布 |
| GET | `/data/ads/hotspots/grid/hourly` | 小时 500m 网格热度 |
| GET | `/data/ads/hotspots/grid/daily` | 日 500m 网格热度 |
| GET | `/data/ads/hotspots/poi/hourly` | 小时 POI 热度 |
| GET | `/data/ads/hotspots/poi/daily` | 日 POI 热度 |
| GET | `/data/ads/hotspots/cluster/hourly` | 小时 DBSCAN 聚类热点 |
| GET | `/data/ads/hotspots/cluster/daily` | 日 DBSCAN 聚类热点 |
| GET | `/data/ads/hotspots/district/hourly` | 小时行政区热度 |
| GET | `/data/ads/hotspots/district/daily` | 日行政区热度 |
| GET | `/data/ads/hotspots/monitor/daily` | 热点全局监控摘要 |

### 组合 API（`/page/*`）

面向前端页面，在单次请求中聚合多个数据源，减少请求往返。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/page/dashboard` | 总览看板（全网流量、速度、出行量汇总） |
| GET | `/page/road-status` | 路况页面数据（路段状态列表 + 统计） |
| GET | `/page/congestion/roads/geojson` | 拥堵地图 GeoJSON（bbox 筛选、状态过滤、几何简化、keyset 分页） |
| GET | `/page/congestion/roads/ranking` | 拥堵路段排行榜（按拥堵指数或流量排序） |
| GET | `/page/hotspot/zones` | 热点区域综合数据（DBSCAN + 网格 + POI） |
| GET | `/page/trip-features/od` | 出行 OD 特征（距离/时段/速度分布组合） |
| GET | `/page/trajectory/daily-stats` | 轨迹每日统计（行程数、GPS 点数、路段数） |
| GET | `/page/trajectory/samples` | 轨迹采样（随机抽取 N 条行程的完整路径） |

### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/heartbeat` | 服务健康检查 |
| GET | `/version` | 服务版本信息 |

---

## 实现亮点

### 1. 基于 GB/T 33171 的五级路况评级

路况评级遵循国家标准 GB/T 33171《城市道路交通运行状态分级》，采用**速度绩效指数（SPI）**而非简单阈值：

```
自由流速度 = P95(avg_speed) — 仅取 vehicle_count > 3 的小时样本，排除低样本干扰
拥堵指数 CI  = freeflow_speed / current_speed
SPI          = 100 / CI

畅通     SPI > 70
基本畅通  SPI > 50
轻度拥堵  SPI > 40
中度拥堵  SPI > 30
严重拥堵  SPI ≤ 30
```

自由流速度使用 P95 分位数而非最大值，有效规避异常数据的干扰；仅对车辆数 > 3 的样本计算，避免单辆车高速或低速造成偏差。

### 2. PostGIS 原生 DBSCAN 热点聚类

热点区域识别在数据库内部通过 `ST_ClusterDBSCAN` 函数完成，无需将数据导出到外部计算框架：

```sql
ST_ClusterDBSCAN(
    ST_SetSRID(ST_MakePoint(lon, lat), 4326),
    eps      => 0.0003,   -- ≈33m 地理距离
    minpoints := 100      -- 日粒度；小时粒度取 30
) OVER ()
```

以行程起点（接客）和终点（送客）的坐标为事件点，分别在日粒度和小时粒度上运行聚类，输出热点区域中心、半径和 OD 流量。

### 3. 500m 网格 OD 矩阵

将哈尔滨市区划分为 EPSG:3857 投影下的 500m × 500m 正方形网格，网格编号采用 `列_行` 字符串：

```sql
col  = FLOOR(ST_X(ST_Transform(point, 3857)) / 500)
row  = FLOOR(ST_Y(ST_Transform(point, 3857)) / 500)
zone = col || '_' || row
```

OD 矩阵记录每对起终网格之间的行程流量，支持小时和日两种粒度，是热力图底层数据来源。

### 4. POI 空间关联（300m 缓冲区）

POI 热度通过 PostGIS 地理类型（`geography` cast）+ `ST_DWithin` 实现高精度 300m 半径空间关联：

```sql
ST_DWithin(
    ST_SetSRID(ST_MakePoint(trip.start_lon, trip.start_lat), 4326)::geography,
    poi.geom::geography,
    300   -- 单位米，geography 类型下精确计算
)
```

LATERAL JOIN 写法使每个 POI 独立匹配最近行程，避免笛卡尔积膨胀。

### 5. 拥堵地图 keyset 分页 + 几何简化

地图端拥堵路段数量达 134 万条，直接全量返回不现实。后端实现：

- **keyset 分页**：以 `road_id` 为游标，避免 OFFSET 带来的深分页性能问题
- **bbox 空间过滤**：只返回当前视口内的路段，随地图移动动态加载
- **几何简化**：接受前端按缩放级别（zoom）推导的 `simplify_tolerance` 参数，在数据库侧用 `ST_Simplify` 减少坐标点数，降低传输体积

### 6. OD 流向语义分类

`dw_fact_od_cluster_*` 表对每条行程赋予语义流向标签，区分通勤与非通勤：

| flow_direction | 判断条件 |
|----------------|----------|
| commute_outbound | 距离 < 3700m 且出发小时在 7-8（早高峰出发） |
| commute_inbound | 距离 < 3700m 且出发小时在 17-18（晚高峰返程） |
| transit | 距离 ≥ 8900m（跨区长途） |
| local | 其余所有情况 |

### 7. 时区处理约定

数据集中 `start_time` 以 Unix 时间戳格式存储，但其数值含义为 **CST（UTC+8）本地时间值**，而非 UTC：

```sql
-- 正确写法
EXTRACT(HOUR FROM to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai')

-- 等效写法（因数值已是 CST 本地时）
EXTRACT(HOUR FROM to_timestamp(start_time + 28800) AT TIME ZONE 'Asia/Shanghai')
```

全库统一此约定，避免早晚高峰时段计算偏移 8 小时。

### 8. 数据链路完全可重现

所有 ELT 脚本均为幂等设计，可在不修改原始 ODS 数据的前提下，从 `07_elt_dw.sql` 起重新执行全部计算，数据库状态收敛到一致结果：

- DW/TDM：`INSERT … ON CONFLICT (pk) DO UPDATE SET … = EXCLUDED.…`
- ADS 路况：`TRUNCATE + INSERT`（无业务主键，全量重建更简洁）
- ADS 热点：`INSERT … ON CONFLICT DO UPDATE`

---

## 技术栈

### 数据库

| 组件 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 17 | 主数据库 |
| PostGIS | 3.5 | 空间扩展（Geometry/Geography 类型、GiST 索引、`ST_ClusterDBSCAN`、`ST_DWithin`、`ST_Transform`） |

### 后端

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | ≥ 3.10 | 运行环境 |
| uv | latest | 依赖管理 |
| FastAPI | ≥ 0.118 | Web 框架 |
| Uvicorn | ≥ 0.37 | ASGI 服务器 |
| SQLModel | ≥ 0.0.27 | ORM（基于 SQLAlchemy + Pydantic） |
| GeoAlchemy2 | ≥ 0.19 | PostGIS 空间类型 ORM 支持 |
| psycopg2-binary | ≥ 2.9 | PostgreSQL 驱动 |
| Pydantic-settings | ≥ 2.11 | 配置管理 |

### 前端

| 组件 | 版本 | 说明 |
|------|------|------|
| Node.js | ≥ 18 | 运行环境 |
| pnpm | latest | 包管理器 |
| Vue 3 | ≥ 3.4 | 前端框架（Composition API） |
| Vite | 5.2 | 构建工具 |
| Vue Router | ≥ 4.3 | 客户端路由 |
| UnoCSS | ≥ 0.58 | 原子化 CSS |
| Element Plus | ≥ 2.14 | UI 组件库 |
| ECharts | ≥ 6.0 | 图表库 |
| Leaflet | 通过 CDN | 交互地图 |
| Axios | ≥ 1.15 | HTTP 客户端 |
| TypeScript | ≥ 5.3 | 类型系统 |
| unplugin-vue-router | ≥ 0.19 | 文件系统路由 |

---

## 参考文献

1. **中华人民共和国国家标准 GB/T 33171-2016**《城市道路交通运行状态分级》— 路况 5 级评定标准（畅通/基本畅通/轻度拥堵/中度拥堵/严重拥堵）及速度绩效指数（SPI）算法

2. **DeepGTT** — Yuan, H. et al. *Learning Travel Time Distributions with Deep Generative Model*. WWW 2019.
   深度生成模型，用于行程时间分布估计；本项目使用其数据集与地图匹配结果。
   代码：[github.com/boathit/deepgtt](https://github.com/boathit/deepgtt)

3. **barefoot（BMW Car IT）** — 通用在线地图匹配框架，基于隐马尔可夫模型（HMM）实现 GPS 轨迹到路网路段的匹配。
   代码：[github.com/bmwcarit/barefoot](https://github.com/bmwcarit/barefoot)

4. **barefoot（hujilin1229）** — barefoot 的扩展实现，用于本项目 JLD2 格式轨迹数据的地图匹配处理。
   代码：[github.com/hujilin1229/barefoot](https://github.com/hujilin1229/barefoot)

5. **Data_Platform（hongfangao）** — 本课程配套大作业参考实现，地图匹配脚本与 JLD2 格式数据导入逻辑参考自此仓库。
   代码：[github.com/hongfangao/Data_Platform](https://github.com/hongfangao/Data_Platform)

6. **PostGIS Documentation** — 空间函数参考（`ST_ClusterDBSCAN`、`ST_DWithin`、`ST_Transform`、`ST_Simplify`）。
   文档：[postgis.net/docs](https://postgis.net/docs/)

7. **OpenStreetMap** — 哈尔滨区域道路网络底图数据。
   [openstreetmap.org](https://www.openstreetmap.org)

8. **FastAPI Documentation** — [fastapi.tiangolo.com](https://fastapi.tiangolo.com)

9. **Vue 3 Documentation** — [vuejs.org](https://vuejs.org)
