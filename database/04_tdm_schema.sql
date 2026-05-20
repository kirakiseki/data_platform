-- ============================================================
-- 04_tdm_schema.sql
-- TDM 层（主题数据层）表结构
-- 依赖：03_dw_schema.sql（road_id/node_id 均来自 DW 维度）
-- ============================================================

-- 道路画像标签表
CREATE TABLE IF NOT EXISTS tdm_tag_road (
    road_id         BIGINT PRIMARY KEY,
    road_name       VARCHAR(255),
    road_type       VARCHAR(20),
    speed_limit     INTEGER,
    avg_daily_flow  INTEGER,        -- 日均流量，单位辆/日
    avg_rush_flow   INTEGER,        -- 高峰时段（7-9,17-19）平均流量，辆/小时
    avg_night_flow  INTEGER,        -- 夜间平均流量，辆/小时
    avg_daily_speed DOUBLE PRECISION,  -- 日均速度，km/h
    tags_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tdm_tag_road_road_type      ON tdm_tag_road(road_type);
CREATE INDEX IF NOT EXISTS idx_tdm_tag_road_avg_daily_flow ON tdm_tag_road(avg_daily_flow);
CREATE INDEX IF NOT EXISTS idx_tdm_tag_road_avg_daily_speed ON tdm_tag_road(avg_daily_speed);

COMMENT ON TABLE tdm_tag_road IS 'TDM层道路画像标签表，来源：dw_dim_road + dw_fact_road_flow_*，共22304条';

-- 节点画像标签表
CREATE TABLE IF NOT EXISTS tdm_tag_node (
    node_id         BIGINT PRIMARY KEY,
    node_name       VARCHAR(255),
    node_type       VARCHAR(20),
    avg_in_flow     INTEGER,        -- 日均驶入流量，辆/日
    avg_out_flow    INTEGER,        -- 日均驶出流量，辆/日
    in_out_ratio    DOUBLE PRECISION,  -- 进出比 = avg_in_flow / avg_out_flow
    tags_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tdm_tag_node_node_type    ON tdm_tag_node(node_type);
CREATE INDEX IF NOT EXISTS idx_tdm_tag_node_avg_in_flow  ON tdm_tag_node(avg_in_flow);
CREATE INDEX IF NOT EXISTS idx_tdm_tag_node_avg_out_flow ON tdm_tag_node(avg_out_flow);

COMMENT ON TABLE tdm_tag_node IS 'TDM层节点画像标签表，来源：dw_dim_node + dw_fact_node_daily，共226042条';

-- 行政区基础标签表
CREATE TABLE IF NOT EXISTS tdm_tag_district (
    district_code   VARCHAR(20) PRIMARY KEY,
    district_name   VARCHAR(50),
    district_level  VARCHAR(20),
    tags_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tdm_tag_district_name ON tdm_tag_district(district_name);

COMMENT ON TABLE tdm_tag_district IS 'TDM层行政区基础标签表，来源：dw_dim_district，共5条';

-- 时段标签表
CREATE TABLE IF NOT EXISTS tdm_tag_time_slot (
    slot_id         SERIAL PRIMARY KEY,
    slot_name       VARCHAR(20) NOT NULL,
    slot_type       VARCHAR(20) NOT NULL,   -- rush / normal / night
    start_hour      INTEGER NOT NULL CHECK (start_hour BETWEEN 0 AND 23),
    end_hour        INTEGER NOT NULL CHECK (end_hour BETWEEN 0 AND 23),
    weekdays        VARCHAR(20),            -- 全部 / 工作日
    traffic_pattern VARCHAR(20),            -- 高流量 / 中等 / 平稳 / 低流量
    created_at      TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE tdm_tag_time_slot IS 'TDM层时段标签表，7个时段定义（早高峰/上午/午间/下午/晚高峰/晚间/夜间）';
COMMENT ON COLUMN tdm_tag_time_slot.end_hour IS '夜间时段 end_hour=7 表示跨天，即22:00到次日07:00';

-- 车辆运营画像标签表
CREATE TABLE IF NOT EXISTS tdm_tag_vehicle (
    devid               VARCHAR(50) PRIMARY KEY,
    total_trips         INTEGER DEFAULT 0,
    total_distance      DOUBLE PRECISION DEFAULT 0,  -- 累计总里程，单位米
    total_duration      BIGINT DEFAULT 0,             -- 累计总时长，单位秒
    avg_daily_trips     DOUBLE PRECISION,
    avg_daily_distance  DOUBLE PRECISION,             -- 日均里程，单位米
    avg_daily_hours     DOUBLE PRECISION,             -- 日均运营时长，单位小时
    avg_trip_distance   DOUBLE PRECISION,             -- 平均行程距离，单位米
    avg_trip_duration   DOUBLE PRECISION,             -- 平均行程时长，单位分钟
    rush_hour_trips     INTEGER DEFAULT 0,            -- 高峰时段（7-9,17-19）行程数
    rush_hour_ratio     DOUBLE PRECISION,             -- 高峰出车比例
    night_trips         INTEGER DEFAULT 0,            -- 夜间（19-7）行程数
    night_ratio         DOUBLE PRECISION,
    short_trip_count    INTEGER DEFAULT 0,            -- 短途：< 3km
    medium_trip_count   INTEGER DEFAULT 0,            -- 中途：3-10km
    long_trip_count     INTEGER DEFAULT 0,            -- 长途：>= 10km
    long_trip_ratio     DOUBLE PRECISION,
    main_hour_start     INTEGER,                      -- 主要运营开始小时（保留，暂为NULL）
    main_hour_end       INTEGER,
    tags_updated_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tdm_tag_vehicle_total_trips    ON tdm_tag_vehicle(total_trips);
CREATE INDEX IF NOT EXISTS idx_tdm_tag_vehicle_rush_hour_ratio ON tdm_tag_vehicle(rush_hour_ratio);
CREATE INDEX IF NOT EXISTS idx_tdm_tag_vehicle_night_ratio    ON tdm_tag_vehicle(night_ratio);
CREATE INDEX IF NOT EXISTS idx_tdm_tag_vehicle_long_trip_ratio ON tdm_tag_vehicle(long_trip_ratio);

COMMENT ON TABLE tdm_tag_vehicle IS 'TDM层车辆运营画像标签表，来源：dw_fact_trip，共12470条';
