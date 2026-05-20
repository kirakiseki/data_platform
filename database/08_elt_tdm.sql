-- ============================================================
-- 08_elt_tdm.sql
-- TDM 层标签表数据装载
-- 依赖：07_elt_dw.sql（DW 层已完整装载）
-- 注意：tdm_tag_time_slot 已在 06_static_data.sql 中以静态 INSERT 方式装载，
--       本脚本不重复处理。
-- 幂等策略：INSERT ... ON CONFLICT DO UPDATE
-- ============================================================

-- ============================================================
-- 1. tdm_tag_district（行政区基础标签）
--    来源：dw_dim_district（5 条，静态数据，district_code 为 PK）
-- ============================================================

INSERT INTO tdm_tag_district (
    district_code,
    district_name,
    district_level,
    tags_updated_at
)
SELECT
    district_code,
    district_name,
    district_level,
    NOW() AS tags_updated_at
FROM dw_dim_district
ON CONFLICT (district_code) DO UPDATE
SET district_name  = EXCLUDED.district_name,
    district_level = EXCLUDED.district_level,
    tags_updated_at = EXCLUDED.tags_updated_at;

-- ============================================================
-- 2. tdm_tag_road（道路画像标签）
--    来源：dw_dim_road + dw_fact_road_flow_daily + dw_fact_road_flow_hourly
--    - avg_daily_flow / avg_daily_speed：取每条路段各天 trip_count / avg_speed 的平均值
--    - avg_rush_flow：高峰时段 (7,8,17,18) 小时级 trip_count 的平均值
--    - avg_night_flow：夜间时段 (19-23, 0-6) 小时级 trip_count 的平均值
-- ============================================================

INSERT INTO tdm_tag_road (
    road_id,
    road_name,
    road_type,
    speed_limit,
    avg_daily_flow,
    avg_rush_flow,
    avg_night_flow,
    avg_daily_speed,
    tags_updated_at
)
SELECT
    d.road_id,
    d.road_name,
    d.road_type,
    d.speed_limit,
    ROUND(day_flow.avg_daily_flow)::int    AS avg_daily_flow,
    ROUND(hour_flow.avg_rush_flow)::int    AS avg_rush_flow,
    ROUND(hour_flow.avg_night_flow)::int   AS avg_night_flow,
    day_flow.avg_daily_speed,
    NOW() AS tags_updated_at
FROM dw_dim_road d
LEFT JOIN (
    SELECT
        road_id,
        AVG(trip_count)::numeric           AS avg_daily_flow,
        AVG(avg_speed)::double precision   AS avg_daily_speed
    FROM dw_fact_road_flow_daily
    GROUP BY road_id
) day_flow ON day_flow.road_id = d.road_id
LEFT JOIN (
    SELECT
        road_id,
        AVG(trip_count) FILTER (WHERE hour_slice IN (7, 8, 17, 18))::numeric
            AS avg_rush_flow,
        AVG(trip_count) FILTER (WHERE hour_slice IN (19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6))::numeric
            AS avg_night_flow
    FROM dw_fact_road_flow_hourly
    GROUP BY road_id
) hour_flow ON hour_flow.road_id = d.road_id
ON CONFLICT (road_id) DO UPDATE
SET road_name       = EXCLUDED.road_name,
    road_type       = EXCLUDED.road_type,
    speed_limit     = EXCLUDED.speed_limit,
    avg_daily_flow  = EXCLUDED.avg_daily_flow,
    avg_rush_flow   = EXCLUDED.avg_rush_flow,
    avg_night_flow  = EXCLUDED.avg_night_flow,
    avg_daily_speed = EXCLUDED.avg_daily_speed,
    tags_updated_at = EXCLUDED.tags_updated_at;

-- ============================================================
-- 3. tdm_tag_node（节点画像标签）
--    来源：dw_dim_node + dw_fact_node_daily
--    - avg_in_flow  / avg_out_flow：各天驶入/驶出量的平均值（辆/日）
--    - in_out_ratio：avg_in_flow / avg_out_flow
-- ============================================================

INSERT INTO tdm_tag_node (
    node_id,
    node_name,
    node_type,
    avg_in_flow,
    avg_out_flow,
    in_out_ratio,
    tags_updated_at
)
SELECT
    d.node_id,
    d.node_name,
    d.node_type,
    ROUND(flow.avg_in_flow)::int                                 AS avg_in_flow,
    ROUND(flow.avg_out_flow)::int                                AS avg_out_flow,
    flow.avg_in_flow / NULLIF(flow.avg_out_flow, 0)             AS in_out_ratio,
    NOW() AS tags_updated_at
FROM dw_dim_node d
LEFT JOIN (
    SELECT
        node_id,
        AVG(in_vehicle_count)::numeric   AS avg_in_flow,
        AVG(out_vehicle_count)::numeric  AS avg_out_flow
    FROM dw_fact_node_daily
    GROUP BY node_id
) flow ON flow.node_id = d.node_id
ON CONFLICT (node_id) DO UPDATE
SET node_name       = EXCLUDED.node_name,
    node_type       = EXCLUDED.node_type,
    avg_in_flow     = EXCLUDED.avg_in_flow,
    avg_out_flow    = EXCLUDED.avg_out_flow,
    in_out_ratio    = EXCLUDED.in_out_ratio,
    tags_updated_at = EXCLUDED.tags_updated_at;

-- ============================================================
-- 4. tdm_tag_vehicle（车辆运营画像标签）
--    来源：dw_fact_trip（按 devid 聚合）
--    - start_hour 通过 to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai' 提取
--    - 行程距离分档：<3000m 短途 / 3000-10000m 中途 / >=10000m 长途
--    - 高峰时段：hour IN (7,8,17,18)；夜间：hour IN (19-23,0-6)
--    - avg_daily_* 按活跃天数（active_days = COUNT(DISTINCT trip_date)）归一化
-- ============================================================

WITH trip_base AS (
    SELECT
        trip_id,
        devid,
        trip_date,
        total_distance,
        duration,
        EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS start_hour
    FROM dw_fact_trip
    WHERE devid IS NOT NULL
),
vehicle_stats AS (
    SELECT
        devid,
        COUNT(*)                                                                        AS total_trips,
        SUM(total_distance)                                                             AS total_distance,
        SUM(duration)                                                                   AS total_duration,
        COUNT(DISTINCT trip_date)                                                       AS active_days,
        AVG(total_distance)                                                             AS avg_trip_distance,
        AVG(duration) / 60.0                                                            AS avg_trip_duration,
        COUNT(*) FILTER (WHERE start_hour IN (7, 8, 17, 18))                          AS rush_hour_trips,
        COUNT(*) FILTER (WHERE start_hour IN (19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6)) AS night_trips,
        COUNT(*) FILTER (WHERE total_distance < 3000)                                  AS short_trip_count,
        COUNT(*) FILTER (WHERE total_distance >= 3000 AND total_distance < 10000)      AS medium_trip_count,
        COUNT(*) FILTER (WHERE total_distance >= 10000)                                AS long_trip_count
    FROM trip_base
    GROUP BY devid
)
INSERT INTO tdm_tag_vehicle (
    devid,
    total_trips,
    total_distance,
    total_duration,
    avg_daily_trips,
    avg_daily_distance,
    avg_daily_hours,
    avg_trip_distance,
    avg_trip_duration,
    rush_hour_trips,
    rush_hour_ratio,
    night_trips,
    night_ratio,
    short_trip_count,
    medium_trip_count,
    long_trip_count,
    long_trip_ratio,
    main_hour_start,
    main_hour_end,
    tags_updated_at
)
SELECT
    s.devid,
    s.total_trips,
    s.total_distance,
    s.total_duration,
    s.total_trips    / NULLIF(s.active_days, 0)::double precision       AS avg_daily_trips,
    s.total_distance / NULLIF(s.active_days, 0)::double precision       AS avg_daily_distance,
    s.total_duration / NULLIF(s.active_days, 0)::double precision / 3600.0 AS avg_daily_hours,
    s.avg_trip_distance,
    s.avg_trip_duration,
    s.rush_hour_trips,
    s.rush_hour_trips / NULLIF(s.total_trips, 0)::double precision      AS rush_hour_ratio,
    s.night_trips,
    s.night_trips    / NULLIF(s.total_trips, 0)::double precision       AS night_ratio,
    s.short_trip_count,
    s.medium_trip_count,
    s.long_trip_count,
    s.long_trip_count / NULLIF(s.total_trips, 0)::double precision      AS long_trip_ratio,
    NULL::integer AS main_hour_start,
    NULL::integer AS main_hour_end,
    NOW() AS tags_updated_at
FROM vehicle_stats s
ON CONFLICT (devid) DO UPDATE
SET total_trips        = EXCLUDED.total_trips,
    total_distance     = EXCLUDED.total_distance,
    total_duration     = EXCLUDED.total_duration,
    avg_daily_trips    = EXCLUDED.avg_daily_trips,
    avg_daily_distance = EXCLUDED.avg_daily_distance,
    avg_daily_hours    = EXCLUDED.avg_daily_hours,
    avg_trip_distance  = EXCLUDED.avg_trip_distance,
    avg_trip_duration  = EXCLUDED.avg_trip_duration,
    rush_hour_trips    = EXCLUDED.rush_hour_trips,
    rush_hour_ratio    = EXCLUDED.rush_hour_ratio,
    night_trips        = EXCLUDED.night_trips,
    night_ratio        = EXCLUDED.night_ratio,
    short_trip_count   = EXCLUDED.short_trip_count,
    medium_trip_count  = EXCLUDED.medium_trip_count,
    long_trip_count    = EXCLUDED.long_trip_count,
    long_trip_ratio    = EXCLUDED.long_trip_ratio,
    main_hour_start    = EXCLUDED.main_hour_start,
    main_hour_end      = EXCLUDED.main_hour_end,
    tags_updated_at    = EXCLUDED.tags_updated_at;
