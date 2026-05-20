-- ============================================================
-- 05_ads_schema.sql
-- ADS 层（应用数据层）表结构
-- 依赖：03_dw_schema.sql、01_extensions_types.sql
-- 所有业务时间均使用 Asia/Shanghai
-- 路况状态按 GB/T 33171 五级体系：畅通/基本畅通/轻度拥堵/中度拥堵/严重拥堵
-- ============================================================

-- ============================================================
-- 路况与拥堵
-- ============================================================

-- 道路小时级路况表（核心业务表）
-- 拥堵指数 CI = 自由流速度 / 实测速度 (SPI = current_speed/freeflow_speed*100)
-- GB/T 33171 阈值：SPI>70→畅通, >50→基本畅通, >40→轻度拥堵, >30→中度拥堵, ≤30→严重拥堵
CREATE TABLE IF NOT EXISTS ads_road_status_hourly (
    road_id       BIGINT NOT NULL,
    stat_date     DATE NOT NULL,
    hour_slice    INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    road_name     VARCHAR(255),
    road_class    VARCHAR(50),
    current_speed DOUBLE PRECISION,      -- 当前速度，km/h
    current_flow  INTEGER,               -- 当前流量，辆/小时
    congestion_idx DOUBLE PRECISION,     -- 拥堵指数 CI = freeflow/current_speed；NULL 表示样本不足
    status        VARCHAR(10),
    geom          GEOMETRY(LineString, 4326),
    updated_at    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (road_id, stat_date, hour_slice),
    CONSTRAINT chk_ads_road_status_hourly_status
        CHECK (status IS NULL OR status IN ('畅通', '基本畅通', '轻度拥堵', '中度拥堵', '严重拥堵'))
);

CREATE INDEX IF NOT EXISTS idx_ads_road_status_hourly_stat_hour ON ads_road_status_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_ads_road_status_hourly_road_id   ON ads_road_status_hourly(road_id);
CREATE INDEX IF NOT EXISTS idx_ads_road_status_hourly_status    ON ads_road_status_hourly(status);
CREATE INDEX IF NOT EXISTS idx_ads_road_status_hourly_geom      ON ads_road_status_hourly USING GIST(geom);

COMMENT ON TABLE ads_road_status_hourly IS 'ADS道路小时级路况，GB/T 33171 五级；自由流速度用P95估计（vehicle_count>3）';
COMMENT ON COLUMN ads_road_status_hourly.congestion_idx IS 'CI = freeflow_speed/current_speed；vehicle_count≤3时置NULL';

-- 全网小时级路况汇总表
CREATE TABLE IF NOT EXISTS ads_network_status_hourly (
    stat_date               DATE NOT NULL,
    hour_slice              INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    total_roads             INTEGER,
    smooth_roads            INTEGER,
    basically_smooth_roads  INTEGER,
    light_congested_roads   INTEGER,
    moderate_congested_roads INTEGER,
    severe_congested_roads  INTEGER,
    smooth_pct              DOUBLE PRECISION,
    basically_smooth_pct    DOUBLE PRECISION,
    light_congested_pct     DOUBLE PRECISION,
    moderate_congested_pct  DOUBLE PRECISION,
    severe_congested_pct    DOUBLE PRECISION,
    network_avg_speed       DOUBLE PRECISION,
    updated_at              TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_ads_network_status_hourly_stat_hour ON ads_network_status_hourly(stat_date, hour_slice);

COMMENT ON TABLE ads_network_status_hourly IS 'ADS全网小时级路况汇总，五级分布占比；从ads_road_status_hourly聚合';

-- TOP 拥堵路段小时排行
CREATE TABLE IF NOT EXISTS ads_top_congested_roads_hourly (
    rank_id       INTEGER NOT NULL,
    stat_date     DATE NOT NULL,
    hour_slice    INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    road_id       BIGINT,
    road_name     VARCHAR(255),
    congestion_idx DOUBLE PRECISION,
    avg_speed     DOUBLE PRECISION,  -- km/h
    trip_count    INTEGER,
    duration_loss DOUBLE PRECISION,  -- 延误损失，分钟
    updated_at    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (rank_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_ads_top_congested_roads_hourly_stat_hour    ON ads_top_congested_roads_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_ads_top_congested_roads_hourly_road_id      ON ads_top_congested_roads_hourly(road_id);
CREATE INDEX IF NOT EXISTS idx_ads_top_congested_roads_hourly_congestion_idx ON ads_top_congested_roads_hourly(congestion_idx);

COMMENT ON TABLE ads_top_congested_roads_hourly IS 'ADS小时级TOP50拥堵路段排行，按congestion_idx DESC排序';

-- 拥堵分布小时统计
CREATE TABLE IF NOT EXISTS ads_congestion_hourly (
    stat_date              DATE NOT NULL,
    hour_slice             INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    light_congested_roads  INTEGER,
    moderate_congested_roads INTEGER,
    severe_congested_roads INTEGER,
    avg_congestion         DOUBLE PRECISION,
    total_delay_min        DOUBLE PRECISION,  -- 全网总延误，分钟
    updated_at             TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_ads_congestion_hourly_stat_hour ON ads_congestion_hourly(stat_date, hour_slice);

-- ============================================================
-- 出行特征
-- ============================================================

-- 出行距离小时分布
CREATE TABLE IF NOT EXISTS ads_trip_distance_hourly (
    stat_date     DATE NOT NULL,
    hour_slice    INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    short_trips   INTEGER DEFAULT 0,    -- < 3km
    medium_trips  INTEGER DEFAULT 0,    -- 3-10km
    long_trips    INTEGER DEFAULT 0,    -- >= 10km
    avg_distance  DOUBLE PRECISION,     -- 平均距离，米
    total_distance DOUBLE PRECISION,    -- 总距离，米
    sample_count  INTEGER DEFAULT 0,
    updated_at    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_ads_trip_distance_hourly_stat_hour ON ads_trip_distance_hourly(stat_date, hour_slice);

-- 出行距离日分布
CREATE TABLE IF NOT EXISTS ads_trip_distance_daily (
    stat_date     DATE PRIMARY KEY,
    short_trips   INTEGER DEFAULT 0,
    medium_trips  INTEGER DEFAULT 0,
    long_trips    INTEGER DEFAULT 0,
    avg_distance  DOUBLE PRECISION,
    total_distance DOUBLE PRECISION,
    sample_count  INTEGER DEFAULT 0,
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- 出行时段日分布
CREATE TABLE IF NOT EXISTS ads_trip_timeslot_daily (
    stat_date      DATE PRIMARY KEY,
    morning_rush   INTEGER DEFAULT 0,   -- 早高峰（7-9）
    daytime        INTEGER DEFAULT 0,   -- 日间（9-17）
    evening_rush   INTEGER DEFAULT 0,   -- 晚高峰（17-19）
    night          INTEGER DEFAULT 0,   -- 夜间（19-7）
    weekday_trips  INTEGER DEFAULT 0,
    holiday_trips  INTEGER DEFAULT 0,
    sample_count   INTEGER DEFAULT 0,
    updated_at     TIMESTAMP DEFAULT NOW()
);

-- 出行速度小时分布
CREATE TABLE IF NOT EXISTS ads_trip_speed_hourly (
    stat_date      DATE NOT NULL,
    hour_slice     INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    avg_speed      DOUBLE PRECISION,
    speed_p50      DOUBLE PRECISION,
    speed_p85      DOUBLE PRECISION,
    speed_p95      DOUBLE PRECISION,
    overspeed_ratio DOUBLE PRECISION,   -- 超速比例，0~1
    sample_count   INTEGER DEFAULT 0,
    updated_at     TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stat_date, hour_slice),
    CONSTRAINT chk_ads_trip_speed_hourly_overspeed_ratio
        CHECK (overspeed_ratio IS NULL OR (overspeed_ratio >= 0 AND overspeed_ratio <= 1))
);

CREATE INDEX IF NOT EXISTS idx_ads_trip_speed_hourly_stat_hour ON ads_trip_speed_hourly(stat_date, hour_slice);

-- 出行速度日分布
CREATE TABLE IF NOT EXISTS ads_trip_speed_daily (
    stat_date      DATE PRIMARY KEY,
    avg_speed      DOUBLE PRECISION,
    speed_p50      DOUBLE PRECISION,
    speed_p85      DOUBLE PRECISION,
    speed_p95      DOUBLE PRECISION,
    overspeed_ratio DOUBLE PRECISION,
    sample_count   INTEGER DEFAULT 0,
    updated_at     TIMESTAMP DEFAULT NOW(),
    CONSTRAINT chk_ads_trip_speed_daily_overspeed_ratio
        CHECK (overspeed_ratio IS NULL OR (overspeed_ratio >= 0 AND overspeed_ratio <= 1))
);

-- ============================================================
-- 热点分析
-- ============================================================

-- 网格热点小时表
CREATE TABLE IF NOT EXISTS ads_hotspot_grid_hourly (
    zone_id           VARCHAR(50) NOT NULL,
    stat_date         DATE NOT NULL,
    hour_slice        INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    zone_name         VARCHAR(100),
    zone_type         VARCHAR(20) DEFAULT 'grid',
    trip_count        INTEGER DEFAULT 0,
    pickup_count      INTEGER DEFAULT 0,
    dropoff_count     INTEGER DEFAULT 0,
    avg_trip_distance DOUBLE PRECISION,  -- 米
    avg_duration      DOUBLE PRECISION,  -- 秒
    vehicle_count     INTEGER DEFAULT 0,
    updated_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zone_id, stat_date, hour_slice),
    CONSTRAINT chk_ads_hotspot_grid_hourly_zone_type CHECK (zone_type = 'grid')
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_grid_hourly_stat_hour ON ads_hotspot_grid_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_grid_hourly_zone_id   ON ads_hotspot_grid_hourly(zone_id);

-- 网格热点日表
CREATE TABLE IF NOT EXISTS ads_hotspot_grid_daily (
    zone_id           VARCHAR(50) NOT NULL,
    stat_date         DATE NOT NULL,
    zone_name         VARCHAR(100),
    zone_type         VARCHAR(20) DEFAULT 'grid',
    trip_count        INTEGER DEFAULT 0,
    pickup_count      INTEGER DEFAULT 0,
    dropoff_count     INTEGER DEFAULT 0,
    avg_trip_distance DOUBLE PRECISION,
    avg_duration      DOUBLE PRECISION,
    vehicle_count     INTEGER DEFAULT 0,
    updated_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zone_id, stat_date),
    CONSTRAINT chk_ads_hotspot_grid_daily_zone_type CHECK (zone_type = 'grid')
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_grid_daily_stat_date ON ads_hotspot_grid_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_grid_daily_zone_id   ON ads_hotspot_grid_daily(zone_id);

-- POI 热点小时表
CREATE TABLE IF NOT EXISTS ads_hotspot_poi_hourly (
    zone_id           VARCHAR(50) NOT NULL,
    stat_date         DATE NOT NULL,
    hour_slice        INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    zone_name         VARCHAR(100),
    zone_type         VARCHAR(20) DEFAULT 'poi',
    trip_count        INTEGER DEFAULT 0,
    pickup_count      INTEGER DEFAULT 0,
    dropoff_count     INTEGER DEFAULT 0,
    avg_trip_distance DOUBLE PRECISION,
    avg_duration      DOUBLE PRECISION,
    vehicle_count     INTEGER DEFAULT 0,
    updated_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zone_id, stat_date, hour_slice),
    CONSTRAINT chk_ads_hotspot_poi_hourly_zone_type CHECK (zone_type = 'poi')
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_poi_hourly_stat_hour ON ads_hotspot_poi_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_poi_hourly_zone_id   ON ads_hotspot_poi_hourly(zone_id);

-- POI 热点日表
CREATE TABLE IF NOT EXISTS ads_hotspot_poi_daily (
    zone_id           VARCHAR(50) NOT NULL,
    stat_date         DATE NOT NULL,
    zone_name         VARCHAR(100),
    zone_type         VARCHAR(20) DEFAULT 'poi',
    trip_count        INTEGER DEFAULT 0,
    pickup_count      INTEGER DEFAULT 0,
    dropoff_count     INTEGER DEFAULT 0,
    avg_trip_distance DOUBLE PRECISION,
    avg_duration      DOUBLE PRECISION,
    vehicle_count     INTEGER DEFAULT 0,
    updated_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zone_id, stat_date),
    CONSTRAINT chk_ads_hotspot_poi_daily_zone_type CHECK (zone_type = 'poi')
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_poi_daily_stat_date ON ads_hotspot_poi_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_poi_daily_zone_id   ON ads_hotspot_poi_daily(zone_id);

-- 聚类热点小时表（DBSCAN eps=33m, minpoints=30）
CREATE TABLE IF NOT EXISTS ads_hotspot_cluster_hourly (
    cluster_id    INTEGER NOT NULL,
    stat_date     DATE NOT NULL,
    hour_slice    INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    center_lon    DOUBLE PRECISION,
    center_lat    DOUBLE PRECISION,
    center_geom   GEOMETRY(Point, 4326),
    trip_count    INTEGER DEFAULT 0,
    pickup_count  INTEGER DEFAULT 0,
    dropoff_count INTEGER DEFAULT 0,
    avg_duration  DOUBLE PRECISION,  -- 秒
    cluster_type  VARCHAR(20),
    updated_at    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (cluster_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_cluster_hourly_stat_hour  ON ads_hotspot_cluster_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_cluster_hourly_center_geom ON ads_hotspot_cluster_hourly USING GIST(center_geom);

COMMENT ON TABLE ads_hotspot_cluster_hourly IS 'ADS小时聚类热点，DBSCAN eps=0.0003(≈33m), minpoints=30';

-- 聚类热点日表（DBSCAN eps=33m, minpoints=100）
CREATE TABLE IF NOT EXISTS ads_hotspot_cluster_daily (
    cluster_id    INTEGER NOT NULL,
    stat_date     DATE NOT NULL,
    center_lon    DOUBLE PRECISION,
    center_lat    DOUBLE PRECISION,
    center_geom   GEOMETRY(Point, 4326),
    trip_count    INTEGER DEFAULT 0,
    pickup_count  INTEGER DEFAULT 0,
    dropoff_count INTEGER DEFAULT 0,
    avg_duration  DOUBLE PRECISION,
    cluster_type  VARCHAR(20),
    updated_at    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (cluster_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_cluster_daily_stat_date   ON ads_hotspot_cluster_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_cluster_daily_center_geom ON ads_hotspot_cluster_daily USING GIST(center_geom);

COMMENT ON TABLE ads_hotspot_cluster_daily IS 'ADS日聚类热点，DBSCAN eps=0.0003(≈33m), minpoints=100；cluster_id按trip_count降序编号';

-- 行政区热点小时表
CREATE TABLE IF NOT EXISTS ads_hotspot_district_hourly (
    zone_id           VARCHAR(20) NOT NULL,
    stat_date         DATE NOT NULL,
    hour_slice        INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    zone_name         VARCHAR(100),
    zone_type         VARCHAR(20) DEFAULT 'district',
    trip_count        INTEGER DEFAULT 0,
    pickup_count      INTEGER DEFAULT 0,
    dropoff_count     INTEGER DEFAULT 0,
    avg_trip_distance DOUBLE PRECISION,
    avg_duration      DOUBLE PRECISION,
    vehicle_count     INTEGER DEFAULT 0,
    updated_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zone_id, stat_date, hour_slice)
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_district_hourly_date ON ads_hotspot_district_hourly(stat_date, hour_slice);

COMMENT ON TABLE ads_hotspot_district_hourly IS 'ADS行政区热点（小时），需要dw_dim_district.geom有效（ST_Within空间关联）';

-- 行政区热点日表
CREATE TABLE IF NOT EXISTS ads_hotspot_district_daily (
    zone_id           VARCHAR(20) NOT NULL,
    stat_date         DATE NOT NULL,
    zone_name         VARCHAR(100),
    zone_type         VARCHAR(20) DEFAULT 'district',
    trip_count        INTEGER DEFAULT 0,
    pickup_count      INTEGER DEFAULT 0,
    dropoff_count     INTEGER DEFAULT 0,
    avg_trip_distance DOUBLE PRECISION,
    avg_duration      DOUBLE PRECISION,
    vehicle_count     INTEGER DEFAULT 0,
    updated_at        TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (zone_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_district_daily_date ON ads_hotspot_district_daily(stat_date);

-- 热点监控小时汇总
CREATE TABLE IF NOT EXISTS ads_hotspot_monitor_hourly (
    stat_date              DATE NOT NULL,
    hour_slice             INTEGER NOT NULL CHECK (hour_slice BETWEEN 0 AND 23),
    zone_type              VARCHAR(20) NOT NULL,
    hotspot_count          INTEGER DEFAULT 0,
    total_trip_count       INTEGER DEFAULT 0,
    total_pickup_count     INTEGER DEFAULT 0,
    total_dropoff_count    INTEGER DEFAULT 0,
    max_hotspot_zone_id    VARCHAR(50),
    max_hotspot_zone_name  VARCHAR(100),
    max_hotspot_trip_count INTEGER,
    updated_at             TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stat_date, hour_slice, zone_type),
    CONSTRAINT chk_ads_hotspot_monitor_hourly_zone_type
        CHECK (zone_type IN ('grid', 'poi', 'cluster'))
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_monitor_hourly_stat_hour ON ads_hotspot_monitor_hourly(stat_date, hour_slice);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_monitor_hourly_zone_type ON ads_hotspot_monitor_hourly(zone_type);

-- 热点监控日汇总
CREATE TABLE IF NOT EXISTS ads_hotspot_monitor_daily (
    stat_date              DATE NOT NULL,
    zone_type              VARCHAR(20) NOT NULL,
    hotspot_count          INTEGER DEFAULT 0,
    total_trip_count       INTEGER DEFAULT 0,
    total_pickup_count     INTEGER DEFAULT 0,
    total_dropoff_count    INTEGER DEFAULT 0,
    max_hotspot_zone_id    VARCHAR(50),
    max_hotspot_zone_name  VARCHAR(100),
    max_hotspot_trip_count INTEGER,
    updated_at             TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (stat_date, zone_type),
    CONSTRAINT chk_ads_hotspot_monitor_daily_zone_type
        CHECK (zone_type IN ('grid', 'poi', 'cluster'))
);

CREATE INDEX IF NOT EXISTS idx_ads_hotspot_monitor_daily_stat_date ON ads_hotspot_monitor_daily(stat_date);
CREATE INDEX IF NOT EXISTS idx_ads_hotspot_monitor_daily_zone_type ON ads_hotspot_monitor_daily(zone_type);
