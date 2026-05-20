-- ============================================================
-- 09_elt_ads.sql
-- ADS 层应用数据装载
-- 依赖：07_elt_dw.sql（DW 层已完整装载）
-- 执行顺序：
--   1. ads_road_status_hourly（P95 自由流速度 + GB/T 33171 五级路况）
--   2. ads_network_status_hourly（网络级聚合）
--   3. ads_top_congested_roads_hourly（LATERAL Top 50）
--   4. ads_congestion_hourly（拥堵汇总）
--   5. ads_trip_distance_hourly / daily（行程距离分档）
--   6. ads_trip_timeslot_daily（行程时段分布）
--   7. ads_trip_speed_hourly / daily（行程速度分位数）
--   8. ads_hotspot_grid_hourly / daily（500m 网格热点）
--   9. ads_hotspot_poi_hourly / daily（POI 热点）
--  10. ads_hotspot_cluster_daily（DBSCAN 聚类，eps=0.0003≈33m，minpoints=100）
--  11. ads_hotspot_cluster_hourly（DBSCAN 聚类，eps=0.0003≈33m，minpoints=30）
--  12. ads_hotspot_district_hourly / daily（行政区热点，ST_Within 空间关联）
--  13. ads_hotspot_monitor_hourly / daily（热点监控汇总）
--  14. dw_dim_grid（网格维度，从 ads_hotspot_grid_daily 提取）
-- 幂等策略：TRUNCATE + INSERT（路况/聚类表）或 INSERT ... ON CONFLICT DO UPDATE
-- ============================================================

-- ============================================================
-- 1. ads_road_status_hourly
--    路况来源：dw_fact_road_flow_hourly（avg_speed = current_speed）
--    自由流速度：同一路段所有 vehicle_count>3 的小时观测，取 P95
--    GB/T 33171 五级路况：
--      SPI = current_speed / freeflow_speed * 100
--      畅通      SPI > 70
--      基本畅通  50 < SPI ≤ 70
--      轻度拥堵  40 < SPI ≤ 50
--      中度拥堵  30 < SPI ≤ 40
--      严重拥堵  SPI ≤ 30
--    vehicle_count ≤ 3 的时段不计算路况（status/congestion_idx 为 NULL）
-- ============================================================

TRUNCATE ads_road_status_hourly;

INSERT INTO ads_road_status_hourly (
    road_id, stat_date, hour_slice,
    road_name, road_class,
    current_speed, current_flow,
    geom, updated_at
)
SELECT
    f.road_id,
    f.stat_date,
    f.hour_slice,
    r.road_name,
    r.road_type       AS road_class,
    f.avg_speed       AS current_speed,
    f.vehicle_count   AS current_flow,
    w.geom            AS geom,
    NOW()
FROM dw_fact_road_flow_hourly f
JOIN dw_dim_road r ON r.road_id = f.road_id
LEFT JOIN bfmap_ways w ON w.gid = f.road_id;

-- P95 自由流速度临时表（vehicle_count > 3 的小时观测）
DROP TABLE IF EXISTS _tmp_road_freeflow;
CREATE TEMP TABLE _tmp_road_freeflow AS
SELECT
    road_id,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY avg_speed) AS freeflow_speed,
    COUNT(*)                                                  AS sample_hours
FROM dw_fact_road_flow_hourly
WHERE avg_speed > 0 AND vehicle_count > 3
GROUP BY road_id;

CREATE INDEX ON _tmp_road_freeflow (road_id);

-- 计算并写入 congestion_idx / status
WITH joined AS (
    SELECT
        a.road_id, a.stat_date, a.hour_slice, a.current_speed,
        rf.freeflow_speed,
        COALESCE(f.vehicle_count, 0) AS vehicle_count
    FROM ads_road_status_hourly a
    LEFT JOIN _tmp_road_freeflow rf ON rf.road_id = a.road_id
    LEFT JOIN dw_fact_road_flow_hourly f
      ON f.road_id = a.road_id AND f.stat_date = a.stat_date AND f.hour_slice = a.hour_slice
),
calc AS (
    SELECT
        road_id, stat_date, hour_slice,
        vehicle_count,
        CASE WHEN freeflow_speed > 0 AND current_speed > 0
             THEN freeflow_speed / current_speed
             ELSE NULL END AS new_congestion_idx,
        CASE WHEN freeflow_speed > 0 AND current_speed > 0
             THEN LEAST(100.0, current_speed / freeflow_speed * 100.0)
             ELSE NULL END AS spi
    FROM joined
)
UPDATE ads_road_status_hourly a
SET
    congestion_idx = CASE
        WHEN c.vehicle_count <= 3 OR c.spi IS NULL THEN NULL
        ELSE c.new_congestion_idx
    END,
    status = CASE
        WHEN c.vehicle_count <= 3 OR c.spi IS NULL THEN NULL
        WHEN c.spi > 70 THEN '畅通'
        WHEN c.spi > 50 THEN '基本畅通'
        WHEN c.spi > 40 THEN '轻度拥堵'
        WHEN c.spi > 30 THEN '中度拥堵'
        ELSE                  '严重拥堵'
    END,
    updated_at = NOW()
FROM calc c
WHERE a.road_id    = c.road_id
  AND a.stat_date  = c.stat_date
  AND a.hour_slice = c.hour_slice;

-- ============================================================
-- 2. ads_network_status_hourly（从 ads_road_status_hourly 聚合五级路况）
-- ============================================================

TRUNCATE ads_network_status_hourly;

INSERT INTO ads_network_status_hourly (
    stat_date, hour_slice,
    total_roads,
    smooth_roads, basically_smooth_roads,
    light_congested_roads, moderate_congested_roads, severe_congested_roads,
    smooth_pct, basically_smooth_pct,
    light_congested_pct, moderate_congested_pct, severe_congested_pct,
    network_avg_speed, updated_at
)
SELECT
    r.stat_date, r.hour_slice,
    COUNT(*) FILTER (WHERE r.status IS NOT NULL)::integer          AS total_roads,
    COUNT(*) FILTER (WHERE r.status = '畅通')::integer             AS smooth_roads,
    COUNT(*) FILTER (WHERE r.status = '基本畅通')::integer         AS basically_smooth_roads,
    COUNT(*) FILTER (WHERE r.status = '轻度拥堵')::integer         AS light_congested_roads,
    COUNT(*) FILTER (WHERE r.status = '中度拥堵')::integer         AS moderate_congested_roads,
    COUNT(*) FILTER (WHERE r.status = '严重拥堵')::integer         AS severe_congested_roads,
    COUNT(*) FILTER (WHERE r.status = '畅通')::double precision
        / NULLIF(COUNT(*) FILTER (WHERE r.status IS NOT NULL), 0)  AS smooth_pct,
    COUNT(*) FILTER (WHERE r.status = '基本畅通')::double precision
        / NULLIF(COUNT(*) FILTER (WHERE r.status IS NOT NULL), 0)  AS basically_smooth_pct,
    COUNT(*) FILTER (WHERE r.status = '轻度拥堵')::double precision
        / NULLIF(COUNT(*) FILTER (WHERE r.status IS NOT NULL), 0)  AS light_congested_pct,
    COUNT(*) FILTER (WHERE r.status = '中度拥堵')::double precision
        / NULLIF(COUNT(*) FILTER (WHERE r.status IS NOT NULL), 0)  AS moderate_congested_pct,
    COUNT(*) FILTER (WHERE r.status = '严重拥堵')::double precision
        / NULLIF(COUNT(*) FILTER (WHERE r.status IS NOT NULL), 0)  AS severe_congested_pct,
    AVG(r.current_speed) FILTER (WHERE r.current_speed > 0)        AS network_avg_speed,
    NOW()
FROM ads_road_status_hourly r
GROUP BY r.stat_date, r.hour_slice;

-- ============================================================
-- 3. ads_top_congested_roads_hourly（每时段拥堵前 50 路段）
--    duration_loss = (total_distance/current_speed - total_distance/freeflow_speed) / 60
-- ============================================================

TRUNCATE ads_top_congested_roads_hourly;

-- 临时表：路段总行驶距离（用于计算延误）
DROP TABLE IF EXISTS _tmp_road_distance;
CREATE TEMP TABLE _tmp_road_distance AS
SELECT road_id, stat_date, hour_slice, total_distance
FROM dw_fact_road_flow_hourly
WHERE total_distance > 0;

CREATE INDEX ON _tmp_road_distance (road_id, stat_date, hour_slice);

-- 局部索引加速 LATERAL 排序
CREATE INDEX IF NOT EXISTS idx_ads_road_status_congestion_top
    ON ads_road_status_hourly (stat_date, hour_slice, congestion_idx DESC NULLS LAST)
    WHERE status IS NOT NULL AND congestion_idx IS NOT NULL;

WITH periods AS (
    SELECT DISTINCT stat_date, hour_slice
    FROM ads_road_status_hourly
    WHERE status IS NOT NULL AND congestion_idx IS NOT NULL
)
INSERT INTO ads_top_congested_roads_hourly (
    rank_id, stat_date, hour_slice, road_id, road_name,
    congestion_idx, avg_speed, trip_count, duration_loss, updated_at
)
SELECT
    ROW_NUMBER() OVER (
        PARTITION BY p.stat_date, p.hour_slice
        ORDER BY top.congestion_idx DESC NULLS LAST, top.current_flow DESC, top.road_id
    )::integer AS rank_id,
    p.stat_date, p.hour_slice,
    top.road_id, top.road_name,
    top.congestion_idx,
    top.current_speed    AS avg_speed,
    top.current_flow     AS trip_count,
    CASE
        WHEN d.total_distance > 0 AND top.current_speed > 0 AND rf.freeflow_speed > 0
        THEN GREATEST(0.0,
                (d.total_distance / (top.current_speed  * 1000.0 / 3600.0)
               - d.total_distance / (rf.freeflow_speed  * 1000.0 / 3600.0)) / 60.0)
        ELSE NULL
    END AS duration_loss,
    NOW()
FROM periods p
CROSS JOIN LATERAL (
    SELECT r.road_id, r.road_name, r.congestion_idx, r.current_speed, r.current_flow
    FROM ads_road_status_hourly r
    WHERE r.stat_date  = p.stat_date
      AND r.hour_slice = p.hour_slice
      AND r.status IS NOT NULL
      AND r.congestion_idx IS NOT NULL
    ORDER BY r.congestion_idx DESC NULLS LAST, r.current_flow DESC, r.road_id
    LIMIT 50
) top
LEFT JOIN _tmp_road_distance d
    ON d.road_id = top.road_id AND d.stat_date = p.stat_date AND d.hour_slice = p.hour_slice
LEFT JOIN _tmp_road_freeflow rf ON rf.road_id = top.road_id;

-- ============================================================
-- 4. ads_congestion_hourly（三级拥堵汇总 + 总延误分钟）
-- ============================================================

TRUNCATE ads_congestion_hourly;

WITH road_delay AS (
    SELECT r.stat_date, r.hour_slice, r.status, r.congestion_idx,
        CASE WHEN d.total_distance > 0 AND r.current_speed > 0 AND rf.freeflow_speed > 0
             THEN GREATEST(0.0,
                  (d.total_distance / (r.current_speed * 1000.0 / 3600.0)
                   - d.total_distance / (rf.freeflow_speed * 1000.0 / 3600.0)) / 60.0)
             ELSE NULL END AS delay_min
    FROM ads_road_status_hourly r
    LEFT JOIN _tmp_road_distance d
      ON d.road_id = r.road_id AND d.stat_date = r.stat_date AND d.hour_slice = r.hour_slice
    LEFT JOIN _tmp_road_freeflow rf ON rf.road_id = r.road_id
)
INSERT INTO ads_congestion_hourly (
    stat_date, hour_slice,
    light_congested_roads, moderate_congested_roads, severe_congested_roads,
    avg_congestion, total_delay_min, updated_at
)
SELECT
    stat_date, hour_slice,
    COUNT(*) FILTER (WHERE status = '轻度拥堵')::integer     AS light_congested_roads,
    COUNT(*) FILTER (WHERE status = '中度拥堵')::integer     AS moderate_congested_roads,
    COUNT(*) FILTER (WHERE status = '严重拥堵')::integer     AS severe_congested_roads,
    AVG(congestion_idx) FILTER (WHERE status IS NOT NULL)    AS avg_congestion,
    SUM(delay_min)                                            AS total_delay_min,
    NOW()
FROM road_delay
GROUP BY stat_date, hour_slice;

-- ============================================================
-- 5. ads_trip_distance_hourly / daily（行程距离分档统计）
--    分档：<3000m 短途 / 3000-10000m 中途 / >=10000m 长途
--    hour_slice = EXTRACT(HOUR FROM start_time AT TIME ZONE 'Asia/Shanghai')
-- ============================================================

WITH trip_base AS (
    SELECT
        (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai')::date AS stat_date,
        EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice,
        total_distance
    FROM dw_fact_trip
    WHERE start_time IS NOT NULL
      AND total_distance IS NOT NULL
      AND total_distance > 0
),
hourly_source AS (
    SELECT
        stat_date,
        hour_slice,
        COUNT(*) FILTER (WHERE total_distance < 3000)::integer                          AS short_trips,
        COUNT(*) FILTER (WHERE total_distance >= 3000 AND total_distance < 10000)::integer AS medium_trips,
        COUNT(*) FILTER (WHERE total_distance >= 10000)::integer                         AS long_trips,
        AVG(total_distance)                                                              AS avg_distance,
        SUM(total_distance)                                                              AS total_distance,
        COUNT(*)::integer                                                                AS sample_count
    FROM trip_base
    GROUP BY stat_date, hour_slice
)
INSERT INTO ads_trip_distance_hourly (
    stat_date, hour_slice,
    short_trips, medium_trips, long_trips,
    avg_distance, total_distance, sample_count, updated_at
)
SELECT
    stat_date, hour_slice,
    short_trips, medium_trips, long_trips,
    avg_distance, total_distance, sample_count, NOW()
FROM hourly_source
ON CONFLICT (stat_date, hour_slice) DO UPDATE
SET short_trips   = EXCLUDED.short_trips,
    medium_trips  = EXCLUDED.medium_trips,
    long_trips    = EXCLUDED.long_trips,
    avg_distance  = EXCLUDED.avg_distance,
    total_distance = EXCLUDED.total_distance,
    sample_count  = EXCLUDED.sample_count,
    updated_at    = EXCLUDED.updated_at;

WITH daily_source AS (
    SELECT
        stat_date,
        SUM(short_trips)::integer                                           AS short_trips,
        SUM(medium_trips)::integer                                          AS medium_trips,
        SUM(long_trips)::integer                                            AS long_trips,
        SUM(total_distance) / NULLIF(SUM(sample_count), 0)                 AS avg_distance,
        SUM(total_distance)                                                  AS total_distance,
        SUM(sample_count)::integer                                          AS sample_count
    FROM ads_trip_distance_hourly
    GROUP BY stat_date
)
INSERT INTO ads_trip_distance_daily (
    stat_date,
    short_trips, medium_trips, long_trips,
    avg_distance, total_distance, sample_count, updated_at
)
SELECT
    stat_date,
    short_trips, medium_trips, long_trips,
    avg_distance, total_distance, sample_count, NOW()
FROM daily_source
ON CONFLICT (stat_date) DO UPDATE
SET short_trips   = EXCLUDED.short_trips,
    medium_trips  = EXCLUDED.medium_trips,
    long_trips    = EXCLUDED.long_trips,
    avg_distance  = EXCLUDED.avg_distance,
    total_distance = EXCLUDED.total_distance,
    sample_count  = EXCLUDED.sample_count,
    updated_at    = EXCLUDED.updated_at;

-- ============================================================
-- 6. ads_trip_timeslot_daily（行程时段分布）
--    早高峰：7-8 / 日间：9-16 / 晚高峰：17-18 / 夜间：19-23,0-6
-- ============================================================

WITH trip_base AS (
    SELECT
        (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai')::date AS stat_date,
        EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice
    FROM dw_fact_trip
    WHERE start_time IS NOT NULL
),
timeslot_source AS (
    SELECT
        b.stat_date,
        COUNT(*) FILTER (WHERE b.hour_slice IN (7, 8))::integer                               AS morning_rush,
        COUNT(*) FILTER (WHERE b.hour_slice BETWEEN 9 AND 16)::integer                        AS daytime,
        COUNT(*) FILTER (WHERE b.hour_slice IN (17, 18))::integer                             AS evening_rush,
        COUNT(*) FILTER (WHERE b.hour_slice IN (19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6))::integer AS night,
        COUNT(*) FILTER (WHERE COALESCE(t.is_weekday,
            (EXTRACT(ISODOW FROM b.stat_date)::int BETWEEN 1 AND 5)))::integer                AS weekday_trips,
        COUNT(*) FILTER (WHERE COALESCE(t.is_holiday, FALSE))::integer                        AS holiday_trips,
        COUNT(*)::integer                                                                      AS sample_count
    FROM trip_base b
    LEFT JOIN dw_dim_time t
      ON t.date_id = b.stat_date AND t.hour = b.hour_slice
    GROUP BY b.stat_date
)
INSERT INTO ads_trip_timeslot_daily (
    stat_date,
    morning_rush, daytime, evening_rush, night,
    weekday_trips, holiday_trips, sample_count, updated_at
)
SELECT
    stat_date,
    morning_rush, daytime, evening_rush, night,
    weekday_trips, holiday_trips, sample_count, NOW()
FROM timeslot_source
ON CONFLICT (stat_date) DO UPDATE
SET morning_rush  = EXCLUDED.morning_rush,
    daytime       = EXCLUDED.daytime,
    evening_rush  = EXCLUDED.evening_rush,
    night         = EXCLUDED.night,
    weekday_trips = EXCLUDED.weekday_trips,
    holiday_trips = EXCLUDED.holiday_trips,
    sample_count  = EXCLUDED.sample_count,
    updated_at    = EXCLUDED.updated_at;

-- ============================================================
-- 7. ads_trip_speed_hourly / daily（行程速度分位数）
--    速度来源：dw_fact_trip.avg_speed（单位 km/h）
--    计算：P50 / P85 / P95（行程级别）
-- ============================================================

WITH trip_speed_base AS (
    SELECT
        (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai')::date AS stat_date,
        EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice,
        avg_speed
    FROM dw_fact_trip
    WHERE start_time IS NOT NULL
      AND avg_speed IS NOT NULL
      AND avg_speed > 0
),
hourly_source AS (
    SELECT
        stat_date,
        hour_slice,
        AVG(avg_speed)                                                     AS avg_speed,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_speed)            AS speed_p50,
        PERCENTILE_CONT(0.85) WITHIN GROUP (ORDER BY avg_speed)            AS speed_p85,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY avg_speed)            AS speed_p95,
        NULL::double precision                                             AS overspeed_ratio,
        COUNT(*)::integer                                                  AS sample_count
    FROM trip_speed_base
    GROUP BY stat_date, hour_slice
)
INSERT INTO ads_trip_speed_hourly (
    stat_date, hour_slice,
    avg_speed, speed_p50, speed_p85, speed_p95,
    overspeed_ratio, sample_count, updated_at
)
SELECT
    stat_date, hour_slice,
    avg_speed, speed_p50, speed_p85, speed_p95,
    overspeed_ratio, sample_count, NOW()
FROM hourly_source
ON CONFLICT (stat_date, hour_slice) DO UPDATE
SET avg_speed      = EXCLUDED.avg_speed,
    speed_p50      = EXCLUDED.speed_p50,
    speed_p85      = EXCLUDED.speed_p85,
    speed_p95      = EXCLUDED.speed_p95,
    overspeed_ratio = EXCLUDED.overspeed_ratio,
    sample_count   = EXCLUDED.sample_count,
    updated_at     = EXCLUDED.updated_at;

WITH trip_speed_base AS (
    SELECT
        (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai')::date AS stat_date,
        avg_speed
    FROM dw_fact_trip
    WHERE start_time IS NOT NULL
      AND avg_speed IS NOT NULL
      AND avg_speed > 0
),
daily_source AS (
    SELECT
        stat_date,
        AVG(avg_speed)                                                     AS avg_speed,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_speed)            AS speed_p50,
        PERCENTILE_CONT(0.85) WITHIN GROUP (ORDER BY avg_speed)            AS speed_p85,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY avg_speed)            AS speed_p95,
        NULL::double precision                                             AS overspeed_ratio,
        COUNT(*)::integer                                                  AS sample_count
    FROM trip_speed_base
    GROUP BY stat_date
)
INSERT INTO ads_trip_speed_daily (
    stat_date,
    avg_speed, speed_p50, speed_p85, speed_p95,
    overspeed_ratio, sample_count, updated_at
)
SELECT
    stat_date,
    avg_speed, speed_p50, speed_p85, speed_p95,
    overspeed_ratio, sample_count, NOW()
FROM daily_source
ON CONFLICT (stat_date) DO UPDATE
SET avg_speed      = EXCLUDED.avg_speed,
    speed_p50      = EXCLUDED.speed_p50,
    speed_p85      = EXCLUDED.speed_p85,
    speed_p95      = EXCLUDED.speed_p95,
    overspeed_ratio = EXCLUDED.overspeed_ratio,
    sample_count   = EXCLUDED.sample_count,
    updated_at     = EXCLUDED.updated_at;

-- ============================================================
-- 8. ads_hotspot_grid_hourly / daily（500m 网格热点）
--    数据来源：dw_fact_od_grid_hourly / dw_fact_od_grid_daily
--    - 起点网格 → pickup_count；终点网格 → dropoff_count；
--      同一网格起终点 → 合并计数
--    - trip_count = pickup + dropoff（同格起终点不重复）
-- ============================================================

WITH zone_events AS (
    SELECT origin_grid_id AS zone_id, stat_date, hour_slice,
           trip_count AS zone_trip_count, trip_count AS pickup_count,
           CASE WHEN origin_grid_id = dest_grid_id THEN trip_count ELSE 0 END AS dropoff_count,
           avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_grid_hourly
    UNION ALL
    SELECT dest_grid_id, stat_date, hour_slice,
           trip_count, 0, trip_count,
           avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_grid_hourly
    WHERE dest_grid_id <> origin_grid_id
),
grid_source AS (
    SELECT
        zone_id,
        stat_date,
        hour_slice,
        zone_id AS zone_name,
        'grid'::varchar(20) AS zone_type,
        SUM(zone_trip_count)::integer AS trip_count,
        SUM(pickup_count)::integer    AS pickup_count,
        SUM(dropoff_count)::integer   AS dropoff_count,
        SUM(avg_distance * zone_trip_count) / NULLIF(SUM(zone_trip_count), 0) AS avg_trip_distance,
        SUM(avg_duration * zone_trip_count) / NULLIF(SUM(zone_trip_count), 0) AS avg_duration,
        SUM(vehicle_count)::integer   AS vehicle_count
    FROM zone_events
    GROUP BY zone_id, stat_date, hour_slice
)
INSERT INTO ads_hotspot_grid_hourly (
    zone_id, stat_date, hour_slice,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, updated_at
)
SELECT
    zone_id, stat_date, hour_slice,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, NOW()
FROM grid_source
ON CONFLICT (zone_id, stat_date, hour_slice) DO UPDATE
SET zone_name         = EXCLUDED.zone_name,
    zone_type         = EXCLUDED.zone_type,
    trip_count        = EXCLUDED.trip_count,
    pickup_count      = EXCLUDED.pickup_count,
    dropoff_count     = EXCLUDED.dropoff_count,
    avg_trip_distance = EXCLUDED.avg_trip_distance,
    avg_duration      = EXCLUDED.avg_duration,
    vehicle_count     = EXCLUDED.vehicle_count,
    updated_at        = EXCLUDED.updated_at;

WITH zone_events AS (
    SELECT origin_grid_id AS zone_id, stat_date,
           trip_count AS zone_trip_count, trip_count AS pickup_count,
           CASE WHEN origin_grid_id = dest_grid_id THEN trip_count ELSE 0 END AS dropoff_count,
           avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_grid_daily
    UNION ALL
    SELECT dest_grid_id, stat_date,
           trip_count, 0, trip_count,
           avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_grid_daily
    WHERE dest_grid_id <> origin_grid_id
),
grid_source AS (
    SELECT
        zone_id,
        stat_date,
        zone_id AS zone_name,
        'grid'::varchar(20) AS zone_type,
        SUM(zone_trip_count)::integer AS trip_count,
        SUM(pickup_count)::integer    AS pickup_count,
        SUM(dropoff_count)::integer   AS dropoff_count,
        SUM(avg_distance * zone_trip_count) / NULLIF(SUM(zone_trip_count), 0) AS avg_trip_distance,
        SUM(avg_duration * zone_trip_count) / NULLIF(SUM(zone_trip_count), 0) AS avg_duration,
        SUM(vehicle_count)::integer   AS vehicle_count
    FROM zone_events
    GROUP BY zone_id, stat_date
)
INSERT INTO ads_hotspot_grid_daily (
    zone_id, stat_date,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, updated_at
)
SELECT
    zone_id, stat_date,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, NOW()
FROM grid_source
ON CONFLICT (zone_id, stat_date) DO UPDATE
SET zone_name         = EXCLUDED.zone_name,
    zone_type         = EXCLUDED.zone_type,
    trip_count        = EXCLUDED.trip_count,
    pickup_count      = EXCLUDED.pickup_count,
    dropoff_count     = EXCLUDED.dropoff_count,
    avg_trip_distance = EXCLUDED.avg_trip_distance,
    avg_duration      = EXCLUDED.avg_duration,
    vehicle_count     = EXCLUDED.vehicle_count,
    updated_at        = EXCLUDED.updated_at;

-- ============================================================
-- 9. ads_hotspot_poi_hourly / daily（POI 热点）
--    数据来源：dw_fact_poi_hourly / dw_fact_poi_daily
--              + dw_fact_od_poi_hourly / dw_fact_od_poi_daily（OD 加权距离/时长）
--    trip_count / pickup_count / dropoff_count 来自 dw_fact_poi_*
--    avg_trip_distance / avg_duration 来自 dw_fact_od_poi_*（OD 加权均值）
-- ============================================================

WITH poi_od_events AS (
    SELECT origin_poi_id AS poi_id, stat_date, hour_slice, trip_count, avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_poi_hourly
    UNION ALL
    SELECT dest_poi_id, stat_date, hour_slice, trip_count, avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_poi_hourly
    WHERE dest_poi_id <> origin_poi_id
),
poi_od_agg AS (
    SELECT poi_id, stat_date, hour_slice,
        SUM(avg_distance * trip_count) / NULLIF(SUM(trip_count), 0) AS avg_trip_distance,
        SUM(avg_duration * trip_count) / NULLIF(SUM(trip_count), 0) AS avg_duration,
        SUM(vehicle_count)::integer AS vehicle_count
    FROM poi_od_events
    GROUP BY poi_id, stat_date, hour_slice
),
poi_keys AS (
    SELECT poi_id, stat_date, hour_slice FROM dw_fact_poi_hourly
    UNION
    SELECT poi_id, stat_date, hour_slice FROM poi_od_agg
),
poi_source AS (
    SELECT
        k.poi_id::text AS zone_id,
        k.stat_date,
        k.hour_slice,
        p.poi_name AS zone_name,
        'poi'::varchar(20) AS zone_type,
        COALESCE(h.trip_count, 0)::integer    AS trip_count,
        COALESCE(h.pickup_count, 0)::integer  AS pickup_count,
        COALESCE(h.dropoff_count, 0)::integer AS dropoff_count,
        o.avg_trip_distance,
        o.avg_duration,
        COALESCE(o.vehicle_count, 0)::integer AS vehicle_count
    FROM poi_keys k
    LEFT JOIN dw_fact_poi_hourly h
      ON h.poi_id = k.poi_id AND h.stat_date = k.stat_date AND h.hour_slice = k.hour_slice
    LEFT JOIN poi_od_agg o
      ON o.poi_id = k.poi_id AND o.stat_date = k.stat_date AND o.hour_slice = k.hour_slice
    LEFT JOIN dw_dim_poi p ON p.poi_id = k.poi_id
)
INSERT INTO ads_hotspot_poi_hourly (
    zone_id, stat_date, hour_slice,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, updated_at
)
SELECT
    zone_id, stat_date, hour_slice,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, NOW()
FROM poi_source
ON CONFLICT (zone_id, stat_date, hour_slice) DO UPDATE
SET zone_name         = EXCLUDED.zone_name,
    zone_type         = EXCLUDED.zone_type,
    trip_count        = EXCLUDED.trip_count,
    pickup_count      = EXCLUDED.pickup_count,
    dropoff_count     = EXCLUDED.dropoff_count,
    avg_trip_distance = EXCLUDED.avg_trip_distance,
    avg_duration      = EXCLUDED.avg_duration,
    vehicle_count     = EXCLUDED.vehicle_count,
    updated_at        = EXCLUDED.updated_at;

WITH poi_od_events AS (
    SELECT origin_poi_id AS poi_id, stat_date, trip_count, avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_poi_daily
    UNION ALL
    SELECT dest_poi_id, stat_date, trip_count, avg_distance, avg_duration, vehicle_count
    FROM dw_fact_od_poi_daily
    WHERE dest_poi_id <> origin_poi_id
),
poi_od_agg AS (
    SELECT poi_id, stat_date,
        SUM(avg_distance * trip_count) / NULLIF(SUM(trip_count), 0) AS avg_trip_distance,
        SUM(avg_duration * trip_count) / NULLIF(SUM(trip_count), 0) AS avg_duration,
        SUM(vehicle_count)::integer AS vehicle_count
    FROM poi_od_events
    GROUP BY poi_id, stat_date
),
poi_keys AS (
    SELECT poi_id, stat_date FROM dw_fact_poi_daily
    UNION
    SELECT poi_id, stat_date FROM poi_od_agg
),
poi_source AS (
    SELECT
        k.poi_id::text AS zone_id,
        k.stat_date,
        p.poi_name AS zone_name,
        'poi'::varchar(20) AS zone_type,
        COALESCE(h.trip_count, 0)::integer    AS trip_count,
        COALESCE(h.pickup_count, 0)::integer  AS pickup_count,
        COALESCE(h.dropoff_count, 0)::integer AS dropoff_count,
        o.avg_trip_distance,
        o.avg_duration,
        COALESCE(o.vehicle_count, 0)::integer AS vehicle_count
    FROM poi_keys k
    LEFT JOIN dw_fact_poi_daily h ON h.poi_id = k.poi_id AND h.stat_date = k.stat_date
    LEFT JOIN poi_od_agg o ON o.poi_id = k.poi_id AND o.stat_date = k.stat_date
    LEFT JOIN dw_dim_poi p ON p.poi_id = k.poi_id
)
INSERT INTO ads_hotspot_poi_daily (
    zone_id, stat_date,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, updated_at
)
SELECT
    zone_id, stat_date,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, NOW()
FROM poi_source
ON CONFLICT (zone_id, stat_date) DO UPDATE
SET zone_name         = EXCLUDED.zone_name,
    zone_type         = EXCLUDED.zone_type,
    trip_count        = EXCLUDED.trip_count,
    pickup_count      = EXCLUDED.pickup_count,
    dropoff_count     = EXCLUDED.dropoff_count,
    avg_trip_distance = EXCLUDED.avg_trip_distance,
    avg_duration      = EXCLUDED.avg_duration,
    vehicle_count     = EXCLUDED.vehicle_count,
    updated_at        = EXCLUDED.updated_at;

-- ============================================================
-- 10. ads_hotspot_cluster_daily（DBSCAN 日级聚类）
--     算法：ST_ClusterDBSCAN，eps=0.0003（≈33m），minpoints=100
--     事件集：每天所有行程的起点 + 终点合并为 OD 事件
--     cluster_id 按 trip_count DESC 排序（同天内排名）
--     noise（cid IS NULL）丢弃
-- ============================================================

TRUNCATE ads_hotspot_cluster_daily;

DO $$
DECLARE
    v_date  DATE;
    v_count INTEGER;
    v_total INTEGER := 0;
BEGIN
    FOR v_date IN
        SELECT DISTINCT trip_date FROM dw_fact_trip ORDER BY trip_date
    LOOP
        RAISE NOTICE '[%] 处理日期: %', clock_timestamp(), v_date;

        WITH events AS (
            SELECT trip_id, start_lon AS lon, start_lat AS lat,
                   1 AS is_pickup, 0 AS is_dropoff, duration
            FROM dw_fact_trip
            WHERE trip_date = v_date
              AND start_lon IS NOT NULL AND start_lat IS NOT NULL
            UNION ALL
            SELECT trip_id, end_lon, end_lat,
                   0, 1, duration
            FROM dw_fact_trip
            WHERE trip_date = v_date
              AND end_lon IS NOT NULL AND end_lat IS NOT NULL
        ),
        clustered AS (
            SELECT lon, lat, is_pickup, is_dropoff, duration,
                ST_ClusterDBSCAN(
                    ST_SetSRID(ST_MakePoint(lon, lat), 4326),
                    eps       => 0.0003,
                    minpoints := 100
                ) OVER () AS cid
            FROM events
        ),
        per_cluster AS (
            SELECT cid,
                AVG(lon)                       AS center_lon,
                AVG(lat)                       AS center_lat,
                SUM(is_pickup)::integer        AS pickup_count,
                SUM(is_dropoff)::integer       AS dropoff_count,
                (SUM(is_pickup) + SUM(is_dropoff))::integer AS trip_count,
                AVG(duration)                  AS avg_duration
            FROM clustered
            WHERE cid IS NOT NULL
            GROUP BY cid
        ),
        ranked AS (
            SELECT
                ROW_NUMBER() OVER (ORDER BY trip_count DESC, center_lon, center_lat)::integer AS cluster_id,
                center_lon, center_lat,
                ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326) AS center_geom,
                pickup_count, dropoff_count, trip_count, avg_duration,
                'od'::varchar(20) AS cluster_type
            FROM per_cluster
        )
        INSERT INTO ads_hotspot_cluster_daily (
            cluster_id, stat_date, center_lon, center_lat, center_geom,
            trip_count, pickup_count, dropoff_count, avg_duration, cluster_type, updated_at
        )
        SELECT cluster_id, v_date, center_lon, center_lat, center_geom,
               trip_count, pickup_count, dropoff_count, avg_duration, cluster_type, NOW()
        FROM ranked;

        GET DIAGNOSTICS v_count = ROW_COUNT;
        v_total := v_total + v_count;
        RAISE NOTICE '[%] 日期 %: 聚类 % 条', clock_timestamp(), v_date, v_count;
    END LOOP;
    RAISE NOTICE '[%] 全部完成，累计 % 条', clock_timestamp(), v_total;
END $$;

-- ============================================================
-- 11. ads_hotspot_cluster_hourly（DBSCAN 小时级聚类）
--     算法：ST_ClusterDBSCAN，eps=0.0003（≈33m），minpoints=30
--     minpoints 降低到 30，因小时级数据量约为日级的 1/24
--     hour_slice = EXTRACT(HOUR FROM start/end_time AT TIME ZONE 'Asia/Shanghai')
-- ============================================================

TRUNCATE ads_hotspot_cluster_hourly;

DO $$
DECLARE
    v_date  DATE;
    v_hour  INTEGER;
    v_count INTEGER;
    v_total INTEGER := 0;
BEGIN
    FOR v_date IN SELECT DISTINCT trip_date FROM dw_fact_trip ORDER BY trip_date LOOP
        FOR v_hour IN 0..23 LOOP
            WITH events AS (
                SELECT start_lon AS lon, start_lat AS lat, 1 AS is_pickup, 0 AS is_dropoff, duration
                FROM dw_fact_trip
                WHERE trip_date = v_date
                  AND start_lon IS NOT NULL
                  AND EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int = v_hour
                UNION ALL
                SELECT end_lon, end_lat, 0, 1, duration
                FROM dw_fact_trip
                WHERE trip_date = v_date
                  AND end_lon IS NOT NULL
                  AND EXTRACT(HOUR FROM (to_timestamp(end_time) AT TIME ZONE 'Asia/Shanghai'))::int = v_hour
            ),
            clustered AS (
                SELECT lon, lat, is_pickup, is_dropoff, duration,
                    ST_ClusterDBSCAN(
                        ST_SetSRID(ST_MakePoint(lon, lat), 4326),
                        eps       => 0.0003,
                        minpoints := 30
                    ) OVER () AS cid
                FROM events
            ),
            per_cluster AS (
                SELECT cid,
                    AVG(lon) AS center_lon, AVG(lat) AS center_lat,
                    SUM(is_pickup)::integer AS pickup_count,
                    SUM(is_dropoff)::integer AS dropoff_count,
                    (SUM(is_pickup) + SUM(is_dropoff))::integer AS trip_count,
                    AVG(duration) AS avg_duration
                FROM clustered WHERE cid IS NOT NULL
                GROUP BY cid
            ),
            ranked AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY trip_count DESC, center_lon, center_lat)::integer AS cluster_id,
                    center_lon, center_lat,
                    ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326) AS center_geom,
                    pickup_count, dropoff_count, trip_count, avg_duration,
                    'od'::varchar(20) AS cluster_type
                FROM per_cluster
            )
            INSERT INTO ads_hotspot_cluster_hourly (
                cluster_id, stat_date, hour_slice, center_lon, center_lat, center_geom,
                trip_count, pickup_count, dropoff_count, avg_duration, cluster_type, updated_at
            )
            SELECT cluster_id, v_date, v_hour, center_lon, center_lat, center_geom,
                   trip_count, pickup_count, dropoff_count, avg_duration, cluster_type, NOW()
            FROM ranked;

            GET DIAGNOSTICS v_count = ROW_COUNT;
            v_total := v_total + v_count;
        END LOOP;
        RAISE NOTICE '[%] 日期 % 完成', clock_timestamp(), v_date;
    END LOOP;
    RAISE NOTICE '[%] 小时聚类累计 % 条', clock_timestamp(), v_total;
END $$;

-- ============================================================
-- 12. ads_hotspot_district_hourly / daily（行政区热点）
--     空间关联：ST_Within(ST_MakePoint(lon,lat), district.geom)
--     trip_count = pickup + dropoff（同区起终点时 trip 不重复）
-- ============================================================

WITH trip_district AS (
    SELECT
        t.trip_id,
        t.devid,
        t.trip_date AS stat_date,
        EXTRACT(HOUR FROM (to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice,
        t.total_distance,
        t.duration,
        sd.district_code AS start_district_code,
        sd.district_name AS start_district_name,
        ed.district_code AS end_district_code,
        ed.district_name AS end_district_name
    FROM dw_fact_trip t
    LEFT JOIN dw_dim_district sd
        ON ST_Within(ST_SetSRID(ST_MakePoint(t.start_lon, t.start_lat), 4326), sd.geom)
    LEFT JOIN dw_dim_district ed
        ON ST_Within(ST_SetSRID(ST_MakePoint(t.end_lon, t.end_lat), 4326), ed.geom)
    WHERE t.start_lon IS NOT NULL AND t.start_lat IS NOT NULL
      AND t.end_lon   IS NOT NULL AND t.end_lat   IS NOT NULL
      AND t.total_distance IS NOT NULL
),
district_events AS (
    SELECT start_district_code AS zone_id, start_district_name AS zone_name,
           stat_date, hour_slice, devid, total_distance, duration,
           1 AS is_pickup,
           CASE WHEN start_district_code = end_district_code THEN 1 ELSE 0 END AS is_dropoff,
           1 AS trip_cnt
    FROM trip_district
    WHERE start_district_code IS NOT NULL
    UNION ALL
    SELECT end_district_code, end_district_name,
           stat_date, hour_slice, devid, total_distance, duration,
           0, 1, 1
    FROM trip_district
    WHERE end_district_code IS NOT NULL
      AND (start_district_code IS NULL OR start_district_code <> end_district_code)
),
agg AS (
    SELECT zone_id, zone_name, stat_date, hour_slice,
        'district'::varchar(20)                                         AS zone_type,
        SUM(trip_cnt)::int                                              AS trip_count,
        SUM(is_pickup)::int                                             AS pickup_count,
        SUM(is_dropoff)::int                                            AS dropoff_count,
        SUM(total_distance * trip_cnt) / NULLIF(SUM(trip_cnt), 0)      AS avg_trip_distance,
        SUM(duration::numeric * trip_cnt) / NULLIF(SUM(trip_cnt), 0)   AS avg_duration,
        COUNT(DISTINCT devid)::int                                      AS vehicle_count
    FROM district_events
    GROUP BY zone_id, zone_name, stat_date, hour_slice
)
INSERT INTO ads_hotspot_district_hourly (
    zone_id, stat_date, hour_slice,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, updated_at
)
SELECT zone_id, stat_date, hour_slice,
       zone_name, zone_type,
       trip_count, pickup_count, dropoff_count,
       avg_trip_distance, avg_duration, vehicle_count, NOW()
FROM agg
ON CONFLICT (zone_id, stat_date, hour_slice) DO UPDATE
SET zone_name         = EXCLUDED.zone_name,
    zone_type         = EXCLUDED.zone_type,
    trip_count        = EXCLUDED.trip_count,
    pickup_count      = EXCLUDED.pickup_count,
    dropoff_count     = EXCLUDED.dropoff_count,
    avg_trip_distance = EXCLUDED.avg_trip_distance,
    avg_duration      = EXCLUDED.avg_duration,
    vehicle_count     = EXCLUDED.vehicle_count,
    updated_at        = EXCLUDED.updated_at;

WITH trip_district AS (
    SELECT
        t.trip_id,
        t.devid,
        t.trip_date AS stat_date,
        t.total_distance,
        t.duration,
        sd.district_code AS start_district_code,
        sd.district_name AS start_district_name,
        ed.district_code AS end_district_code,
        ed.district_name AS end_district_name
    FROM dw_fact_trip t
    LEFT JOIN dw_dim_district sd
        ON ST_Within(ST_SetSRID(ST_MakePoint(t.start_lon, t.start_lat), 4326), sd.geom)
    LEFT JOIN dw_dim_district ed
        ON ST_Within(ST_SetSRID(ST_MakePoint(t.end_lon, t.end_lat), 4326), ed.geom)
    WHERE t.start_lon IS NOT NULL AND t.start_lat IS NOT NULL
      AND t.end_lon   IS NOT NULL AND t.end_lat   IS NOT NULL
      AND t.total_distance IS NOT NULL
),
district_events AS (
    SELECT start_district_code AS zone_id, start_district_name AS zone_name,
           stat_date, devid, total_distance, duration,
           1 AS is_pickup,
           CASE WHEN start_district_code = end_district_code THEN 1 ELSE 0 END AS is_dropoff,
           1 AS trip_cnt
    FROM trip_district
    WHERE start_district_code IS NOT NULL
    UNION ALL
    SELECT end_district_code, end_district_name,
           stat_date, devid, total_distance, duration,
           0, 1, 1
    FROM trip_district
    WHERE end_district_code IS NOT NULL
      AND (start_district_code IS NULL OR start_district_code <> end_district_code)
),
agg AS (
    SELECT zone_id, zone_name, stat_date,
        'district'::varchar(20)                                         AS zone_type,
        SUM(trip_cnt)::int                                              AS trip_count,
        SUM(is_pickup)::int                                             AS pickup_count,
        SUM(is_dropoff)::int                                            AS dropoff_count,
        SUM(total_distance * trip_cnt) / NULLIF(SUM(trip_cnt), 0)      AS avg_trip_distance,
        SUM(duration::numeric * trip_cnt) / NULLIF(SUM(trip_cnt), 0)   AS avg_duration,
        COUNT(DISTINCT devid)::int                                      AS vehicle_count
    FROM district_events
    GROUP BY zone_id, zone_name, stat_date
)
INSERT INTO ads_hotspot_district_daily (
    zone_id, stat_date,
    zone_name, zone_type,
    trip_count, pickup_count, dropoff_count,
    avg_trip_distance, avg_duration, vehicle_count, updated_at
)
SELECT zone_id, stat_date,
       zone_name, zone_type,
       trip_count, pickup_count, dropoff_count,
       avg_trip_distance, avg_duration, vehicle_count, NOW()
FROM agg
ON CONFLICT (zone_id, stat_date) DO UPDATE
SET zone_name         = EXCLUDED.zone_name,
    zone_type         = EXCLUDED.zone_type,
    trip_count        = EXCLUDED.trip_count,
    pickup_count      = EXCLUDED.pickup_count,
    dropoff_count     = EXCLUDED.dropoff_count,
    avg_trip_distance = EXCLUDED.avg_trip_distance,
    avg_duration      = EXCLUDED.avg_duration,
    vehicle_count     = EXCLUDED.vehicle_count,
    updated_at        = EXCLUDED.updated_at;

-- ============================================================
-- 13. ads_hotspot_monitor_hourly / daily（热点监控汇总）
--     聚合三类热点源（grid / poi / cluster）的汇总统计，
--     并标记各类型最高流量的区域
-- ============================================================

WITH hotspot_union AS (
    SELECT stat_date, hour_slice, 'grid'::varchar(20) AS zone_type,
           zone_id, zone_name, trip_count, pickup_count, dropoff_count
    FROM ads_hotspot_grid_hourly
    UNION ALL
    SELECT stat_date, hour_slice, 'poi'::varchar(20),
           zone_id, zone_name, trip_count, pickup_count, dropoff_count
    FROM ads_hotspot_poi_hourly
    UNION ALL
    SELECT stat_date, hour_slice, 'cluster'::varchar(20),
           cluster_id::text, NULL::varchar(100), trip_count, pickup_count, dropoff_count
    FROM ads_hotspot_cluster_hourly
),
monitor_source AS (
    SELECT stat_date, hour_slice, zone_type,
        COUNT(*)::integer                                                  AS hotspot_count,
        SUM(trip_count)::integer                                           AS total_trip_count,
        SUM(pickup_count)::integer                                         AS total_pickup_count,
        SUM(dropoff_count)::integer                                        AS total_dropoff_count,
        (ARRAY_AGG(zone_id    ORDER BY trip_count DESC NULLS LAST, zone_id))[1] AS max_hotspot_zone_id,
        (ARRAY_AGG(zone_name  ORDER BY trip_count DESC NULLS LAST, zone_id))[1] AS max_hotspot_zone_name,
        (ARRAY_AGG(trip_count ORDER BY trip_count DESC NULLS LAST, zone_id))[1] AS max_hotspot_trip_count
    FROM hotspot_union
    GROUP BY stat_date, hour_slice, zone_type
)
INSERT INTO ads_hotspot_monitor_hourly (
    stat_date, hour_slice, zone_type, hotspot_count,
    total_trip_count, total_pickup_count, total_dropoff_count,
    max_hotspot_zone_id, max_hotspot_zone_name, max_hotspot_trip_count, updated_at
)
SELECT stat_date, hour_slice, zone_type, hotspot_count,
       total_trip_count, total_pickup_count, total_dropoff_count,
       max_hotspot_zone_id, max_hotspot_zone_name, max_hotspot_trip_count, NOW()
FROM monitor_source
ON CONFLICT (stat_date, hour_slice, zone_type) DO UPDATE
SET hotspot_count           = EXCLUDED.hotspot_count,
    total_trip_count        = EXCLUDED.total_trip_count,
    total_pickup_count      = EXCLUDED.total_pickup_count,
    total_dropoff_count     = EXCLUDED.total_dropoff_count,
    max_hotspot_zone_id     = EXCLUDED.max_hotspot_zone_id,
    max_hotspot_zone_name   = EXCLUDED.max_hotspot_zone_name,
    max_hotspot_trip_count  = EXCLUDED.max_hotspot_trip_count,
    updated_at              = EXCLUDED.updated_at;

WITH hotspot_union AS (
    SELECT stat_date, 'grid'::varchar(20) AS zone_type,
           zone_id, zone_name, trip_count, pickup_count, dropoff_count
    FROM ads_hotspot_grid_daily
    UNION ALL
    SELECT stat_date, 'poi'::varchar(20),
           zone_id, zone_name, trip_count, pickup_count, dropoff_count
    FROM ads_hotspot_poi_daily
    UNION ALL
    SELECT stat_date, 'cluster'::varchar(20),
           cluster_id::text, NULL::varchar(100), trip_count, pickup_count, dropoff_count
    FROM ads_hotspot_cluster_daily
),
monitor_source AS (
    SELECT stat_date, zone_type,
        COUNT(*)::integer                                                  AS hotspot_count,
        SUM(trip_count)::integer                                           AS total_trip_count,
        SUM(pickup_count)::integer                                         AS total_pickup_count,
        SUM(dropoff_count)::integer                                        AS total_dropoff_count,
        (ARRAY_AGG(zone_id    ORDER BY trip_count DESC NULLS LAST, zone_id))[1] AS max_hotspot_zone_id,
        (ARRAY_AGG(zone_name  ORDER BY trip_count DESC NULLS LAST, zone_id))[1] AS max_hotspot_zone_name,
        (ARRAY_AGG(trip_count ORDER BY trip_count DESC NULLS LAST, zone_id))[1] AS max_hotspot_trip_count
    FROM hotspot_union
    GROUP BY stat_date, zone_type
)
INSERT INTO ads_hotspot_monitor_daily (
    stat_date, zone_type, hotspot_count,
    total_trip_count, total_pickup_count, total_dropoff_count,
    max_hotspot_zone_id, max_hotspot_zone_name, max_hotspot_trip_count, updated_at
)
SELECT stat_date, zone_type, hotspot_count,
       total_trip_count, total_pickup_count, total_dropoff_count,
       max_hotspot_zone_id, max_hotspot_zone_name, max_hotspot_trip_count, NOW()
FROM monitor_source
ON CONFLICT (stat_date, zone_type) DO UPDATE
SET hotspot_count           = EXCLUDED.hotspot_count,
    total_trip_count        = EXCLUDED.total_trip_count,
    total_pickup_count      = EXCLUDED.total_pickup_count,
    total_dropoff_count     = EXCLUDED.total_dropoff_count,
    max_hotspot_zone_id     = EXCLUDED.max_hotspot_zone_id,
    max_hotspot_zone_name   = EXCLUDED.max_hotspot_zone_name,
    max_hotspot_trip_count  = EXCLUDED.max_hotspot_trip_count,
    updated_at              = EXCLUDED.updated_at;

-- ============================================================
-- 14. dw_dim_grid（网格维度表）
--     从 ads_hotspot_grid_daily 提取全部出现过的 zone_id，
--     解析坐标后填充几何中心点。
--     前置条件：ads_hotspot_grid_daily 已在步骤 8 中装载完毕。
--     grid_id 格式："col_row"（EPSG:3857 投影坐标除以 500 取整）
--     中心点经纬度通过逆投影从网格坐标还原：
--       x_center = (col + 0.5) * 500，y_center = (row + 0.5) * 500
--       geom = ST_Transform(ST_SetSRID(ST_MakePoint(x_center,y_center),3857),4326)
-- ============================================================

INSERT INTO dw_dim_grid (
    grid_id,
    col,
    row,
    center_lon,
    center_lat,
    geom,
    created_at
)
SELECT DISTINCT ON (zone_id)
    zone_id AS grid_id,
    split_part(zone_id, '_', 1)::bigint AS col,
    split_part(zone_id, '_', 2)::bigint AS row,
    ST_X(ST_Transform(
        ST_SetSRID(ST_MakePoint(
            (split_part(zone_id, '_', 1)::double precision + 0.5) * 500,
            (split_part(zone_id, '_', 2)::double precision + 0.5) * 500
        ), 3857), 4326))                AS center_lon,
    ST_Y(ST_Transform(
        ST_SetSRID(ST_MakePoint(
            (split_part(zone_id, '_', 1)::double precision + 0.5) * 500,
            (split_part(zone_id, '_', 2)::double precision + 0.5) * 500
        ), 3857), 4326))                AS center_lat,
    ST_Transform(
        ST_SetSRID(ST_MakePoint(
            (split_part(zone_id, '_', 1)::double precision + 0.5) * 500,
            (split_part(zone_id, '_', 2)::double precision + 0.5) * 500
        ), 3857), 4326)                 AS geom,
    NOW()
FROM ads_hotspot_grid_daily
ON CONFLICT (grid_id) DO NOTHING;
