-- ============================================================
-- 03_dw_schema.sql
-- DW 层（数据仓库层）表结构
-- 依赖：01_extensions_types.sql、OSM 基础表（bfmap_ways/ways/nodes/relations）
-- 包含：维度表（dw_dim_*）+ 事实表（dw_fact_*）
-- ============================================================

-- ============================================================
-- DW 维度表
-- ============================================================

-- 道路类型维度表
CREATE TABLE IF NOT EXISTS dw_dim_road_class (
    class_id                       INTEGER PRIMARY KEY,
    class_name                     VARCHAR(50),
    road_level                     VARCHAR(20),
    default_speed                  INTEGER,
    congestion_threshold_smooth    DOUBLE PRECISION DEFAULT 1.0,
    congestion_threshold_slow      DOUBLE PRECISION DEFAULT 1.3,
    congestion_threshold_congested DOUBLE PRECISION DEFAULT 1.8,
    description                    VARCHAR(100),
    created_at                     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dw_dim_road_class_name  ON dw_dim_road_class(class_name);
CREATE INDEX IF NOT EXISTS idx_dw_dim_road_class_level ON dw_dim_road_class(road_level);

COMMENT ON TABLE dw_dim_road_class IS 'DW层道路类型维度表，class_id 对应 bfmap_ways.class_id';

-- 道路维度表（来源：bfmap_ways + ways）
CREATE TABLE IF NOT EXISTS dw_dim_road (
    road_id        BIGSERIAL PRIMARY KEY,
    osm_id         BIGINT NOT NULL,
    road_name      VARCHAR(255),
    road_type      VARCHAR(20),
    speed_limit    INTEGER,
    length_m       DOUBLE PRECISION,
    source_node_id BIGINT,
    target_node_id BIGINT,
    district_code  VARCHAR(20),
    geom           GEOMETRY(LineString, 4326),
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dw_dim_road_osm_id       ON dw_dim_road(osm_id);
CREATE INDEX IF NOT EXISTS idx_dw_dim_road_district_code ON dw_dim_road(district_code);
CREATE INDEX IF NOT EXISTS idx_dw_dim_road_geom          ON dw_dim_road USING GIST(geom);

COMMENT ON TABLE dw_dim_road IS 'DW层道路维度表，来源：bfmap_ways JOIN ways，共22304条';
COMMENT ON COLUMN dw_dim_road.road_id IS '自增主键，在事实表中用作外键';
COMMENT ON COLUMN dw_dim_road.length_m IS '路段长度，单位米（bfmap_ways.length）';

-- 节点维度表（来源：OSM nodes）
CREATE TABLE IF NOT EXISTS dw_dim_node (
    node_id       BIGSERIAL PRIMARY KEY,
    osm_node_id   BIGINT NOT NULL,
    node_name     VARCHAR(255),
    node_type     VARCHAR(20),
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    district_code VARCHAR(20),
    geom          GEOMETRY(Point, 4326),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dw_dim_node_osm_node_id ON dw_dim_node(osm_node_id);
CREATE INDEX IF NOT EXISTS idx_dw_dim_node_district_code ON dw_dim_node(district_code);
CREATE INDEX IF NOT EXISTS idx_dw_dim_node_geom          ON dw_dim_node USING GIST(geom);

COMMENT ON TABLE dw_dim_node IS 'DW层节点维度表，来源：OSM nodes表，共226042条';

-- 行政区维度表
CREATE TABLE IF NOT EXISTS dw_dim_district (
    district_id    SERIAL PRIMARY KEY,
    district_code  VARCHAR(20) UNIQUE NOT NULL,
    district_name  VARCHAR(50) NOT NULL,
    district_level VARCHAR(20),
    parent_code    VARCHAR(20),
    geom           GEOMETRY(MultiPolygon, 4326),
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dw_dim_district_parent_code ON dw_dim_district(parent_code);
CREATE INDEX IF NOT EXISTS idx_dw_dim_district_geom         ON dw_dim_district USING GIST(geom);

COMMENT ON TABLE dw_dim_district IS 'DW层行政区维度表，哈尔滨5个区级行政区；geom来自OSM relations空间计算';

-- 时间维度表（来源：ods_time）
CREATE TABLE IF NOT EXISTS dw_dim_time (
    date_id      DATE    NOT NULL,
    hour         INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    day          INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,
    day_name     VARCHAR(10),
    is_weekday   BOOLEAN NOT NULL,
    is_holiday   BOOLEAN DEFAULT FALSE,
    holiday_name VARCHAR(50),
    is_rush_hour BOOLEAN NOT NULL,
    time_period  VARCHAR(20) NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date_id, hour)
);

CREATE INDEX IF NOT EXISTS idx_dw_dim_time_date_id ON dw_dim_time(date_id);
CREATE INDEX IF NOT EXISTS idx_dw_dim_time_hour    ON dw_dim_time(hour);
CREATE INDEX IF NOT EXISTS idx_dw_dim_time_period  ON dw_dim_time(time_period);

COMMENT ON TABLE dw_dim_time IS 'DW层时间维度表，按日期+小时，直接从ods_time同步';

-- POI 维度表（来源：ods_poi）
CREATE TABLE IF NOT EXISTS dw_dim_poi (
    poi_id        SERIAL PRIMARY KEY,
    poi_name      VARCHAR(100) NOT NULL,
    poi_type      poi_category NOT NULL,
    district_code VARCHAR(20),
    longitude     DOUBLE PRECISION,
    latitude      DOUBLE PRECISION,
    geom          GEOMETRY(Point, 4326),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dw_dim_poi_district_code ON dw_dim_poi(district_code);
CREATE INDEX IF NOT EXISTS idx_dw_dim_poi_poi_type      ON dw_dim_poi(poi_type);
CREATE INDEX IF NOT EXISTS idx_dw_dim_poi_geom          ON dw_dim_poi USING GIST(geom);

COMMENT ON TABLE dw_dim_poi IS 'DW层POI维度表，去重后来源于ods_poi，共244条';

-- 网格维度表（500m EPSG:3857 网格）
CREATE TABLE IF NOT EXISTS dw_dim_grid (
    grid_id     VARCHAR(50) PRIMARY KEY,   -- 格式："col_row"，如 "28198_11477"
    col         INTEGER NOT NULL,           -- col = FLOOR(mercator_x / 500)
    row         INTEGER NOT NULL,           -- row = FLOOR(mercator_y / 500)
    center_lon  DOUBLE PRECISION,
    center_lat  DOUBLE PRECISION,
    center_geom GEOMETRY(Point, 4326),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dw_dim_grid_col ON dw_dim_grid(col);
CREATE INDEX IF NOT EXISTS idx_dw_dim_grid_row ON dw_dim_grid(row);

COMMENT ON TABLE dw_dim_grid IS '网格维度表，500m EPSG:3857 网格中心点；grid_id由ads_hotspot_grid_daily的zone_id派生';
COMMENT ON COLUMN dw_dim_grid.grid_id IS '格式 col_row，col=FLOOR(mercator_x/500)，row=FLOOR(mercator_y/500)';

-- ============================================================
-- DW 事实表
-- ============================================================

-- 行程明细事实表
CREATE TABLE IF NOT EXISTS dw_fact_trip (
    trip_id        BIGINT PRIMARY KEY,
    devid          VARCHAR(50) NOT NULL,
    trip_date      DATE NOT NULL,
    trip_seq       INTEGER,
    start_lon      DOUBLE PRECISION,
    start_lat      DOUBLE PRECISION,
    end_lon        DOUBLE PRECISION,
    end_lat        DOUBLE PRECISION,
    start_node_id  BIGINT,              -- 起点路段的 source_node_id
    end_node_id    BIGINT,              -- 终点路段的 target_node_id
    start_time     DOUBLE PRECISION,
    end_time       DOUBLE PRECISION,
    duration       INTEGER,             -- 行程时长，单位秒
    route_length   INTEGER,             -- 路线包含的道路数量
    total_distance DOUBLE PRECISION,   -- 行程总距离，单位米
    avg_speed      DOUBLE PRECISION,   -- 平均速度，单位 km/h
    is_rush_hour   BOOLEAN DEFAULT FALSE,
    is_long_trip   BOOLEAN DEFAULT FALSE,  -- total_distance >= 10000m
    route_line     GEOMETRY(LineString, 4326),
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_trip_devid        ON dw_fact_trip(devid);
CREATE INDEX IF NOT EXISTS idx_dw_fact_trip_trip_date    ON dw_fact_trip(trip_date);
CREATE INDEX IF NOT EXISTS idx_dw_fact_trip_start_node_id ON dw_fact_trip(start_node_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_trip_end_node_id  ON dw_fact_trip(end_node_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_trip_route_line   ON dw_fact_trip USING GIST(route_line);

COMMENT ON TABLE dw_fact_trip IS 'DW层行程明细事实表，来源：ods_trips + ods_trip_routes + dw_dim_road';
COMMENT ON COLUMN dw_fact_trip.total_distance IS '单位米，由 ST_Length(route_line::geography) 计算';
COMMENT ON COLUMN dw_fact_trip.avg_speed IS '单位 km/h，由 total_distance/duration*3.6 计算';

-- GPS 点明细事实表
CREATE TABLE IF NOT EXISTS dw_fact_gps_point (
    id           BIGINT PRIMARY KEY,
    trip_id      BIGINT NOT NULL,
    point_seq    INTEGER NOT NULL,
    lon          DOUBLE PRECISION NOT NULL,
    lat          DOUBLE PRECISION NOT NULL,
    tms          DOUBLE PRECISION NOT NULL,
    speed_kmh    DOUBLE PRECISION,    -- 由相邻点距离/时差计算
    heading      DOUBLE PRECISION,    -- 方位角，度（0=北，顺时针）
    acceleration DOUBLE PRECISION,    -- 加速度，m/s²
    road_id      BIGINT,             -- 匹配路段 ID（来源：ods_trip_roads）
    geom         GEOMETRY(Point, 4326),
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_gps_point_trip_id ON dw_fact_gps_point(trip_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_gps_point_road_id ON dw_fact_gps_point(road_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_gps_point_tms     ON dw_fact_gps_point(tms);
CREATE INDEX IF NOT EXISTS idx_dw_fact_gps_point_geom    ON dw_fact_gps_point USING GIST(geom);

COMMENT ON TABLE dw_fact_gps_point IS 'DW层GPS点明细事实表，来源：ods_trip_gps';
COMMENT ON COLUMN dw_fact_gps_point.speed_kmh IS '由相邻GPS点距离/时差计算，优先用next点，last点用prev点';
COMMENT ON COLUMN dw_fact_gps_point.heading IS '由ST_Azimuth计算，优先朝向next点';

-- 路段小时流量事实表
CREATE TABLE IF NOT EXISTS dw_fact_road_flow_hourly (
    fact_id        BIGSERIAL PRIMARY KEY,
    road_id        BIGINT NOT NULL,
    stat_date      DATE NOT NULL,
    hour_slice     INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    trip_count     INTEGER DEFAULT 0,
    vehicle_count  INTEGER DEFAULT 0,
    total_distance DOUBLE PRECISION,   -- 经过该路段的车辆行程距离均摊值，单位米
    avg_speed      DOUBLE PRECISION,   -- 经过该路段的行程平均速度，km/h
    created_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (road_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_road_flow_hourly_stat_hour ON dw_fact_road_flow_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_dw_fact_road_flow_hourly_road_id   ON dw_fact_road_flow_hourly(road_id);

COMMENT ON TABLE dw_fact_road_flow_hourly IS 'DW层路段小时流量事实表，来源：ods_trip_roads + ods_trips + dw_fact_trip';
COMMENT ON COLUMN dw_fact_road_flow_hourly.hour_slice IS '时间按match_time(+28800) AT TIME ZONE Asia/Shanghai确定';

-- 路段日流量事实表
CREATE TABLE IF NOT EXISTS dw_fact_road_flow_daily (
    fact_id        BIGSERIAL PRIMARY KEY,
    road_id        BIGINT NOT NULL,
    stat_date      DATE NOT NULL,
    trip_count     INTEGER DEFAULT 0,
    vehicle_count  INTEGER DEFAULT 0,
    avg_speed      DOUBLE PRECISION,
    total_distance DOUBLE PRECISION,
    created_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (road_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_road_flow_daily_stat_date ON dw_fact_road_flow_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_dw_fact_road_flow_daily_road_id   ON dw_fact_road_flow_daily(road_id);

-- 节点小时事实表
CREATE TABLE IF NOT EXISTS dw_fact_node_hourly (
    fact_id          BIGSERIAL PRIMARY KEY,
    node_id          BIGINT NOT NULL,
    stat_date        DATE NOT NULL,
    hour_slice       INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    in_vehicle_count  INTEGER DEFAULT 0,
    out_vehicle_count INTEGER DEFAULT 0,
    avg_speed        DOUBLE PRECISION,
    created_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE (node_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_node_hourly_stat_hour ON dw_fact_node_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_dw_fact_node_hourly_node_id   ON dw_fact_node_hourly(node_id);

COMMENT ON TABLE dw_fact_node_hourly IS 'DW层节点小时事实表，in=经该节点驶入的车辆数，out=驶出';

-- 节点日事实表
CREATE TABLE IF NOT EXISTS dw_fact_node_daily (
    fact_id          BIGSERIAL PRIMARY KEY,
    node_id          BIGINT NOT NULL,
    stat_date        DATE NOT NULL,
    in_vehicle_count  INTEGER DEFAULT 0,
    out_vehicle_count INTEGER DEFAULT 0,
    avg_speed        DOUBLE PRECISION,
    created_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE (node_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_node_daily_stat_date ON dw_fact_node_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_dw_fact_node_daily_node_id   ON dw_fact_node_daily(node_id);

-- POI 小时事实表
CREATE TABLE IF NOT EXISTS dw_fact_poi_hourly (
    fact_id       BIGSERIAL PRIMARY KEY,
    poi_id        INTEGER NOT NULL,
    stat_date     DATE NOT NULL,
    hour_slice    INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    trip_count    INTEGER DEFAULT 0,
    pickup_count  INTEGER DEFAULT 0,
    dropoff_count INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (poi_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_poi_hourly_stat_hour ON dw_fact_poi_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_dw_fact_poi_hourly_poi_id    ON dw_fact_poi_hourly(poi_id);

COMMENT ON TABLE dw_fact_poi_hourly IS 'DW层POI小时事实表，匹配半径300m，via ST_DWithin';

-- POI 日事实表
CREATE TABLE IF NOT EXISTS dw_fact_poi_daily (
    fact_id       BIGSERIAL PRIMARY KEY,
    poi_id        INTEGER NOT NULL,
    stat_date     DATE NOT NULL,
    trip_count    INTEGER DEFAULT 0,
    pickup_count  INTEGER DEFAULT 0,
    dropoff_count INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (poi_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_poi_daily_stat_date ON dw_fact_poi_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_dw_fact_poi_daily_poi_id    ON dw_fact_poi_daily(poi_id);

-- 路段通行时间分布事实表
CREATE TABLE IF NOT EXISTS dw_fact_road_travel_time (
    fact_id         BIGSERIAL PRIMARY KEY,
    road_id         BIGINT NOT NULL,
    stat_date       DATE NOT NULL,
    hour_slice      INTEGER CHECK (hour_slice BETWEEN 0 AND 23),  -- NULL 表示全天
    sample_count    INTEGER DEFAULT 0,
    min_travel_time DOUBLE PRECISION,   -- 单位秒
    max_travel_time DOUBLE PRECISION,
    avg_travel_time DOUBLE PRECISION,
    p50_travel_time DOUBLE PRECISION,
    p90_travel_time DOUBLE PRECISION,
    p95_travel_time DOUBLE PRECISION,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (road_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_road_travel_time_stat_hour ON dw_fact_road_travel_time(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_dw_fact_road_travel_time_road_id   ON dw_fact_road_travel_time(road_id);

COMMENT ON TABLE dw_fact_road_travel_time IS 'DW层路段通行时间分布，用gaps-and-islands识别连续路段遍历；过滤10~1800秒';

-- 全网小时事实表
CREATE TABLE IF NOT EXISTS dw_fact_network_hourly (
    stat_date       DATE NOT NULL,
    hour_slice      INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    total_trips     INTEGER DEFAULT 0,
    total_vehicles  INTEGER DEFAULT 0,
    total_distance  DOUBLE PRECISION,
    network_avg_speed DOUBLE PRECISION,
    created_at      TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_network_hourly_stat_hour ON dw_fact_network_hourly(stat_date, hour_slice);

-- 全网日事实表
CREATE TABLE IF NOT EXISTS dw_fact_network_daily (
    stat_date           DATE PRIMARY KEY,
    total_trips         INTEGER DEFAULT 0,
    total_vehicles      INTEGER DEFAULT 0,
    total_distance      DOUBLE PRECISION,
    network_avg_speed   DOUBLE PRECISION,
    network_avg_duration DOUBLE PRECISION,
    morning_rush_trips  INTEGER DEFAULT 0,  -- hour IN (7,8)
    evening_rush_trips  INTEGER DEFAULT 0,  -- hour IN (17,18)
    night_trips         INTEGER DEFAULT 0,  -- hour IN (19..23,0..6)
    created_at          TIMESTAMP DEFAULT NOW()
);

-- 网格 OD 小时事实表
CREATE TABLE IF NOT EXISTS dw_fact_od_grid_hourly (
    od_id          BIGSERIAL PRIMARY KEY,
    origin_grid_id VARCHAR(50) NOT NULL,
    dest_grid_id   VARCHAR(50) NOT NULL,
    stat_date      DATE NOT NULL,
    hour_slice     INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    trip_count     INTEGER DEFAULT 0,
    vehicle_count  INTEGER DEFAULT 0,
    avg_distance   DOUBLE PRECISION,
    avg_duration   DOUBLE PRECISION,
    created_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (origin_grid_id, dest_grid_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_od_grid_hourly_stat_hour      ON dw_fact_od_grid_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_grid_hourly_origin_grid_id ON dw_fact_od_grid_hourly(origin_grid_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_grid_hourly_dest_grid_id   ON dw_fact_od_grid_hourly(dest_grid_id);

COMMENT ON TABLE dw_fact_od_grid_hourly IS 'DW层网格OD小时事实，网格规则：500m EPSG:3857 方格，grid_id=CONCAT(FLOOR(x/500),_,FLOOR(y/500))';

-- 网格 OD 日事实表
CREATE TABLE IF NOT EXISTS dw_fact_od_grid_daily (
    od_id          BIGSERIAL PRIMARY KEY,
    origin_grid_id VARCHAR(50) NOT NULL,
    dest_grid_id   VARCHAR(50) NOT NULL,
    stat_date      DATE NOT NULL,
    trip_count     INTEGER DEFAULT 0,
    vehicle_count  INTEGER DEFAULT 0,
    avg_distance   DOUBLE PRECISION,
    avg_duration   DOUBLE PRECISION,
    created_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (origin_grid_id, dest_grid_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_od_grid_daily_stat_date      ON dw_fact_od_grid_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_grid_daily_origin_grid_id ON dw_fact_od_grid_daily(origin_grid_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_grid_daily_dest_grid_id   ON dw_fact_od_grid_daily(dest_grid_id);

-- POI OD 小时事实表
CREATE TABLE IF NOT EXISTS dw_fact_od_poi_hourly (
    od_id          BIGSERIAL PRIMARY KEY,
    origin_poi_id  INTEGER NOT NULL,
    dest_poi_id    INTEGER NOT NULL,
    stat_date      DATE NOT NULL,
    hour_slice     INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    trip_count     INTEGER DEFAULT 0,
    vehicle_count  INTEGER DEFAULT 0,
    avg_distance   DOUBLE PRECISION,
    avg_duration   DOUBLE PRECISION,
    created_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (origin_poi_id, dest_poi_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_od_poi_hourly_stat_hour     ON dw_fact_od_poi_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_poi_hourly_origin_poi_id ON dw_fact_od_poi_hourly(origin_poi_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_poi_hourly_dest_poi_id   ON dw_fact_od_poi_hourly(dest_poi_id);

-- POI OD 日事实表
CREATE TABLE IF NOT EXISTS dw_fact_od_poi_daily (
    od_id          BIGSERIAL PRIMARY KEY,
    origin_poi_id  INTEGER NOT NULL,
    dest_poi_id    INTEGER NOT NULL,
    stat_date      DATE NOT NULL,
    trip_count     INTEGER DEFAULT 0,
    vehicle_count  INTEGER DEFAULT 0,
    avg_distance   DOUBLE PRECISION,
    avg_duration   DOUBLE PRECISION,
    created_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE (origin_poi_id, dest_poi_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_od_poi_daily_stat_date     ON dw_fact_od_poi_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_poi_daily_origin_poi_id ON dw_fact_od_poi_daily(origin_poi_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_poi_daily_dest_poi_id   ON dw_fact_od_poi_daily(dest_poi_id);

-- 聚类 OD 小时事实表
CREATE TABLE IF NOT EXISTS dw_fact_od_cluster_hourly (
    fact_id           BIGSERIAL PRIMARY KEY,
    stat_date         DATE NOT NULL,
    hour_slice        INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    origin_center_lon DOUBLE PRECISION,
    origin_center_lat DOUBLE PRECISION,
    origin_geom       GEOMETRY(Point, 4326),
    dest_center_lon   DOUBLE PRECISION,
    dest_center_lat   DOUBLE PRECISION,
    dest_geom         GEOMETRY(Point, 4326),
    distance_type     VARCHAR(10),
    trip_count        INTEGER DEFAULT 0,
    vehicle_count     INTEGER DEFAULT 0,
    avg_distance      DOUBLE PRECISION,
    avg_duration      DOUBLE PRECISION,
    flow_direction    VARCHAR(20),
    created_at        TIMESTAMP DEFAULT NOW(),
    CONSTRAINT chk_dw_fact_od_cluster_hourly_distance_type
        CHECK (distance_type IS NULL OR distance_type IN ('short', 'medium', 'long')),
    CONSTRAINT chk_dw_fact_od_cluster_hourly_flow_direction
        CHECK (flow_direction IS NULL OR flow_direction IN ('commute_inbound', 'commute_outbound', 'local', 'transit')),
    UNIQUE (origin_center_lat, origin_center_lon, dest_center_lat, dest_center_lon, distance_type, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_od_cluster_hourly_stat_hour   ON dw_fact_od_cluster_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_cluster_hourly_origin_geom ON dw_fact_od_cluster_hourly USING GIST(origin_geom);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_cluster_hourly_dest_geom   ON dw_fact_od_cluster_hourly USING GIST(dest_geom);

-- 聚类 OD 日事实表
CREATE TABLE IF NOT EXISTS dw_fact_od_cluster_daily (
    fact_id           BIGSERIAL PRIMARY KEY,
    stat_date         DATE NOT NULL,
    origin_center_lon DOUBLE PRECISION,
    origin_center_lat DOUBLE PRECISION,
    origin_geom       GEOMETRY(Point, 4326),
    dest_center_lon   DOUBLE PRECISION,
    dest_center_lat   DOUBLE PRECISION,
    dest_geom         GEOMETRY(Point, 4326),
    distance_type     VARCHAR(10),
    trip_count        INTEGER DEFAULT 0,
    vehicle_count     INTEGER DEFAULT 0,
    avg_distance      DOUBLE PRECISION,
    avg_duration      DOUBLE PRECISION,
    flow_direction    VARCHAR(20),
    created_at        TIMESTAMP DEFAULT NOW(),
    CONSTRAINT chk_dw_fact_od_cluster_daily_distance_type
        CHECK (distance_type IS NULL OR distance_type IN ('short', 'medium', 'long')),
    CONSTRAINT chk_dw_fact_od_cluster_daily_flow_direction
        CHECK (flow_direction IS NULL OR flow_direction IN ('commute_inbound', 'commute_outbound', 'local', 'transit')),
    UNIQUE (origin_center_lat, origin_center_lon, dest_center_lat, dest_center_lon, distance_type, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_od_cluster_daily_stat_date   ON dw_fact_od_cluster_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_cluster_daily_origin_geom ON dw_fact_od_cluster_daily USING GIST(origin_geom);
CREATE INDEX IF NOT EXISTS idx_dw_fact_od_cluster_daily_dest_geom   ON dw_fact_od_cluster_daily USING GIST(dest_geom);
