-- ============================================================
-- 02_ods_schema.sql
-- ODS 层（原始数据层）表结构
-- 依赖：01_extensions_types.sql
-- 数据来源：
--   - ods_trips / ods_trip_gps / ods_trip_roads / ods_trip_routes：
--       由 parse/jld2_to_db.py 从 JLD2 轨迹文件导入
--   - ods_time：由静态 SQL 初始化（见 06_static_data.sql）
--   - ods_poi：由静态 SQL 初始化（见 06_static_data.sql）
-- ============================================================

-- ----------------------------------------------------------
-- 行程主表
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ods_trips (
    trip_id    BIGSERIAL PRIMARY KEY,
    devid      VARCHAR(50)  NOT NULL,
    trip_date  DATE         NOT NULL,
    trip_seq   INTEGER,
    start_lon  DOUBLE PRECISION NOT NULL,
    start_lat  DOUBLE PRECISION NOT NULL,
    end_lon    DOUBLE PRECISION NOT NULL,
    end_lat    DOUBLE PRECISION NOT NULL,
    start_time DOUBLE PRECISION NOT NULL,  -- Unix 时间戳（秒），存储为 CST 本地时间值
    end_time   DOUBLE PRECISION NOT NULL,
    duration   INTEGER,                     -- 行程时长，单位秒
    n_points   INTEGER DEFAULT 0,          -- GPS 点数量
    n_roads    INTEGER DEFAULT 0,          -- 匹配路段数量
    metadata   JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ods_trips_devid     ON ods_trips(devid);
CREATE INDEX IF NOT EXISTS idx_ods_trips_trip_date ON ods_trips(trip_date);

COMMENT ON TABLE ods_trips IS 'ODS层行程主表，来源：JLD2文件经jld2_to_db.py导入';
COMMENT ON COLUMN ods_trips.start_time IS 'Unix时间戳（秒），实际含义为CST本地时间数值，查询时用to_timestamp(x) AT TIME ZONE ''Asia/Shanghai''';

-- ----------------------------------------------------------
-- GPS 轨迹点表
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ods_trip_gps (
    id         BIGSERIAL PRIMARY KEY,
    trip_id    BIGINT NOT NULL,
    point_seq  INTEGER NOT NULL,
    lon        DOUBLE PRECISION NOT NULL,
    lat        DOUBLE PRECISION NOT NULL,
    tms        DOUBLE PRECISION NOT NULL,  -- Unix 时间戳（秒）
    geom       GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_ods_trip_gps_trip_id ON ods_trip_gps(trip_id);
CREATE INDEX IF NOT EXISTS idx_ods_trip_gps_tms     ON ods_trip_gps(tms);

COMMENT ON TABLE ods_trip_gps IS 'ODS层GPS轨迹点表，来源：JLD2文件经jld2_to_db.py导入';

-- ----------------------------------------------------------
-- 路段匹配表
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ods_trip_roads (
    id         BIGSERIAL PRIMARY KEY,
    trip_id    BIGINT NOT NULL,
    match_seq  INTEGER NOT NULL,
    road_id    INTEGER NOT NULL,
    match_time DOUBLE PRECISION NOT NULL,  -- 匹配时刻（Unix秒，CST本地值）
    frac       DOUBLE PRECISION            -- 路段内分数位置，0~1
);

CREATE INDEX IF NOT EXISTS idx_ods_trip_roads_trip_id ON ods_trip_roads(trip_id);
CREATE INDEX IF NOT EXISTS idx_ods_trip_roads_road_id ON ods_trip_roads(road_id);

COMMENT ON TABLE ods_trip_roads IS 'ODS层路段匹配表，来源：地图匹配结果';
COMMENT ON COLUMN ods_trip_roads.match_time IS 'CST本地时间数值；转为本地时间：to_timestamp(match_time + 28800) AT TIME ZONE ''Asia/Shanghai''';

-- ----------------------------------------------------------
-- 路径信息表
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ods_trip_routes (
    trip_id        BIGINT PRIMARY KEY,
    route          INTEGER[] NOT NULL,     -- 道路 ID 序列
    route_heading  TEXT[],                 -- 行驶方向序列
    route_geom     TEXT[],                 -- 路段几何序列（WKT）
    n_route        INTEGER,               -- 路段数量
    first_road     INTEGER,               -- 起始路段 ID（对应 dw_dim_road.road_id）
    last_road      INTEGER,               -- 终止路段 ID
    route_line     GEOMETRY(LineString, 4326),  -- 完整行程路径几何
    total_distance DOUBLE PRECISION       -- 行程总距离，单位米（由 route_line 计算）
);

CREATE INDEX IF NOT EXISTS idx_ods_trip_routes_first_road ON ods_trip_routes(first_road);
CREATE INDEX IF NOT EXISTS idx_ods_trip_routes_last_road  ON ods_trip_routes(last_road);

COMMENT ON TABLE ods_trip_routes IS 'ODS层路径信息表，来源：地图匹配结果';
COMMENT ON COLUMN ods_trip_routes.total_distance IS '单位米，由 ST_Length(route_line::geography) 计算';

-- ----------------------------------------------------------
-- 时间维度表（ODS层）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ods_time (
    date_id      DATE    NOT NULL,
    hour         INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    day          INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,   -- 1=Monday ... 7=Sunday (ISO)
    day_name     VARCHAR(20),
    is_weekday   BOOLEAN NOT NULL,
    is_holiday   BOOLEAN DEFAULT FALSE,
    holiday_name VARCHAR(50),
    is_rush_hour BOOLEAN NOT NULL,   -- TRUE if hour IN (7,8,17,18)
    time_period  VARCHAR(20) NOT NULL, -- 早高峰/上午/午间/下午/晚高峰/晚间/夜间
    created_at   TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date_id, hour)
);

COMMENT ON TABLE ods_time IS 'ODS层时间维度表，覆盖数据集日期范围 2015-01-03 至 2015-01-08';

-- ----------------------------------------------------------
-- POI 表（ODS层）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS ods_poi (
    poi_id       SERIAL PRIMARY KEY,
    poi_name     VARCHAR(100) NOT NULL,
    poi_type     poi_category NOT NULL,
    longitude    DOUBLE PRECISION NOT NULL,
    latitude     DOUBLE PRECISION NOT NULL,
    address      VARCHAR(200),
    district_code VARCHAR(20),
    geom         GEOMETRY(Point, 4326),
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ods_poi_poi_type     ON ods_poi(poi_type);
CREATE INDEX IF NOT EXISTS idx_ods_poi_district_code ON ods_poi(district_code);
CREATE INDEX IF NOT EXISTS idx_ods_poi_geom          ON ods_poi USING GIST(geom);

COMMENT ON TABLE ods_poi IS 'ODS层POI表，哈尔滨市区兴趣点，共316条';
