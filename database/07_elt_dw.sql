-- ============================================================
-- 07_elt_dw.sql
-- DW 层数据计算逻辑（ELT）
-- 前置条件：
--   1. 03_dw_schema.sql 已执行（表结构存在）
--   2. 06_static_data.sql 已执行（dw_dim_road_class、dw_dim_district 有数据）
--   3. ODS 层数据已通过 parse/jld2_to_db.py 导入
--   4. OSM 基础表存在（bfmap_ways、ways、nodes、relations）
-- 执行顺序严格按本文件中的章节顺序
-- 时区说明：
--   - ods_trips.start_time 存储的是 Unix 时间戳，但实际存储值等于
--     CST 本地时间对应的 Unix 数值（即比真实 UTC 少 8 小时的存储错位）。
--   - 转换公式：to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'
--   - ods_trip_roads.match_time 类似，本地时间转换：
--     to_timestamp(match_time + 28800) AT TIME ZONE 'Asia/Shanghai'
-- ============================================================

-- ============================================================
-- 1. ODS 层补充计算
-- ============================================================

-- 1a. 回补 ods_trip_routes.total_distance（路径几何长度，米）
BEGIN;
WITH calc AS (
    SELECT
        trip_id,
        ST_Length(route_line::geography) AS calc_distance_m
    FROM ods_trip_routes
    WHERE route_line IS NOT NULL
      AND ST_IsValid(route_line)
      AND ST_Length(route_line::geography) > 0
)
UPDATE ods_trip_routes r
SET total_distance = c.calc_distance_m
FROM calc c
WHERE r.trip_id = c.trip_id
  AND (r.total_distance IS NULL OR r.total_distance <= 0);
COMMIT;

-- ============================================================
-- 2. DW 维度表装载
-- ============================================================

-- 2a. 时间维度：ods_time → dw_dim_time
INSERT INTO dw_dim_time (
    date_id, hour, year, quarter, month, day, day_of_week,
    day_name, is_weekday, is_holiday, holiday_name, is_rush_hour, time_period
)
SELECT
    date_id, hour, year, quarter, month, day, day_of_week,
    day_name, is_weekday, COALESCE(is_holiday, FALSE), holiday_name, is_rush_hour, time_period
FROM ods_time
ON CONFLICT (date_id, hour) DO NOTHING;

-- 2b. POI 维度：ods_poi → dw_dim_poi（去重）
INSERT INTO dw_dim_poi (poi_name, poi_type, district_code, longitude, latitude, geom)
SELECT DISTINCT ON (poi_name, poi_type, longitude, latitude)
    poi_name, poi_type, district_code, longitude, latitude, geom
FROM ods_poi
ORDER BY poi_name, poi_type, longitude, latitude, created_at
ON CONFLICT DO NOTHING;

-- 2c. 道路类型维度：静态数据已由 06_static_data.sql 写入，此处跳过

-- 2d. 节点维度：OSM nodes → dw_dim_node
INSERT INTO dw_dim_node (osm_node_id, node_name, node_type, latitude, longitude, district_code, geom)
SELECT
    n.id AS osm_node_id,
    COALESCE(
        NULLIF(n.tags -> 'name:zh', ''),
        NULLIF(n.tags -> 'name', ''),
        NULLIF(n.tags -> 'official_name', ''),
        NULLIF(n.tags -> 'alt_name', '')
    ) AS node_name,
    CASE
        WHEN n.tags ? 'railway' THEN 'railway'
        WHEN n.tags ? 'amenity' THEN 'amenity'
        WHEN n.tags ? 'tourism' THEN 'tourism'
        WHEN n.tags ? 'shop'    THEN 'shop'
        WHEN n.tags ? 'place'   THEN 'place'
        ELSE 'node'
    END AS node_type,
    ST_Y(n.geom) AS latitude,
    ST_X(n.geom) AS longitude,
    NULL::varchar(20) AS district_code,
    n.geom
FROM nodes n
WHERE n.geom IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM dw_dim_node d WHERE d.osm_node_id = n.id);

-- 2e. 道路维度：bfmap_ways + ways → dw_dim_road
INSERT INTO dw_dim_road (osm_id, road_name, road_type, speed_limit, length_m, source_node_id, target_node_id, district_code, geom)
SELECT
    bw.osm_id,
    COALESCE(
        NULLIF(w.tags -> 'name:zh', ''),
        NULLIF(w.tags -> 'name', ''),
        NULLIF(w.tags -> 'official_name', '')
    ) AS road_name,
    w.tags -> 'highway' AS road_type,
    COALESCE(bw.maxspeed_forward, bw.maxspeed_backward, rc.default_speed) AS speed_limit,
    bw.length AS length_m,
    bw.source AS source_node_id,
    bw.target AS target_node_id,
    NULL::varchar(20) AS district_code,
    bw.geom
FROM bfmap_ways bw
LEFT JOIN ways w ON w.id = bw.osm_id
LEFT JOIN dw_dim_road_class rc ON rc.class_id = bw.class_id
WHERE bw.geom IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM dw_dim_road d
      WHERE d.osm_id = bw.osm_id
        AND d.source_node_id = bw.source
        AND d.target_node_id = bw.target
  );

-- 2f. 行政区维度：已由 06_static_data.sql 写入几何，此处跳过

-- ============================================================
-- 3. dw_fact_trip 装载
-- 来源：ods_trips + ods_trip_routes + dw_dim_road
-- ============================================================
INSERT INTO dw_fact_trip (
    trip_id, devid, trip_date, trip_seq,
    start_lon, start_lat, end_lon, end_lat,
    start_node_id, end_node_id,
    start_time, end_time, duration,
    route_length, total_distance, avg_speed,
    is_rush_hour, is_long_trip, route_line, created_at
)
SELECT
    t.trip_id,
    t.devid,
    t.trip_date,
    t.trip_seq,
    t.start_lon, t.start_lat,
    t.end_lon, t.end_lat,
    d_first.source_node_id AS start_node_id,
    d_last.target_node_id  AS end_node_id,
    t.start_time,
    t.end_time,
    t.duration,
    r.n_route AS route_length,
    r.total_distance,
    CASE
        WHEN t.duration > 0 AND r.total_distance IS NOT NULL
        THEN (r.total_distance / t.duration) * 3.6
        ELSE NULL
    END AS avg_speed,
    CASE
        WHEN EXTRACT(HOUR FROM (to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai'))::int IN (7, 8, 17, 18)
        THEN TRUE ELSE FALSE
    END AS is_rush_hour,
    CASE WHEN COALESCE(r.total_distance, 0) >= 10000 THEN TRUE ELSE FALSE END AS is_long_trip,
    r.route_line,
    NOW()
FROM ods_trips t
LEFT JOIN ods_trip_routes r ON r.trip_id = t.trip_id
LEFT JOIN dw_dim_road d_first ON d_first.road_id = r.first_road
LEFT JOIN dw_dim_road d_last  ON d_last.road_id  = r.last_road
ON CONFLICT (trip_id) DO NOTHING;

-- 3a. 回补 dw_fact_trip.total_distance（优先用 route_line 几何测量）
BEGIN;
WITH updated AS (
    UPDATE dw_fact_trip f
    SET
        total_distance = CASE
            WHEN f.total_distance IS NULL OR f.total_distance <= 0
            THEN ST_Length(r.route_line::geography)
            ELSE f.total_distance
        END,
        avg_speed = CASE
            WHEN (f.avg_speed IS NULL OR f.avg_speed <= 0) AND f.duration > 0
            THEN COALESCE(f.total_distance, ST_Length(r.route_line::geography)) / f.duration * 3.6
            ELSE f.avg_speed
        END,
        is_long_trip = CASE
            WHEN COALESCE(f.total_distance, ST_Length(r.route_line::geography)) >= 10000 THEN TRUE
            ELSE FALSE
        END
    FROM ods_trip_routes r
    WHERE r.trip_id = f.trip_id
      AND r.route_line IS NOT NULL
      AND ST_IsValid(r.route_line)
      AND ST_Length(r.route_line::geography) > 0
    RETURNING 1
)
SELECT COUNT(*) FROM updated;
COMMIT;

-- ============================================================
-- 4. dw_fact_gps_point 装载
-- 来源：ods_trip_gps，按日期分批，每批约 1000 万行
-- ============================================================
DO $$
DECLARE
    v_date DATE;
BEGIN
    FOR v_date IN
        SELECT DISTINCT trip_date FROM ods_trips ORDER BY trip_date
    LOOP
        INSERT INTO dw_fact_gps_point (
            id, trip_id, point_seq, lon, lat, tms,
            speed_kmh, heading, acceleration, road_id, geom, created_at
        )
        SELECT
            g.id, g.trip_id, g.point_seq,
            g.lon, g.lat, g.tms,
            NULL, NULL, NULL, NULL,
            ST_SetSRID(ST_MakePoint(g.lon, g.lat), 4326),
            NOW()
        FROM ods_trip_gps g
        JOIN ods_trips t ON t.trip_id = g.trip_id
        WHERE t.trip_date = v_date
        ON CONFLICT (id) DO NOTHING;
        RAISE NOTICE '日期 % GPS点装载完成', v_date;
    END LOOP;
END $$;

-- 4a. 回补 dw_fact_gps_point.speed_kmh 和 heading
--     速度 = 相邻点距离 / 时差 * 3.6（优先用 next 点，最后一点用 prev 点）
--     方位角 = ST_Azimuth（优先朝向 next 点）
--     注意：实际执行时建议按 trip_date 分块并行，以控制内存使用
DO $$
DECLARE
    v_date DATE;
BEGIN
    FOR v_date IN
        SELECT DISTINCT trip_date FROM ods_trips ORDER BY trip_date
    LOOP
        WITH base AS (
            SELECT
                p.id, p.trip_id, p.point_seq, p.tms, p.geom,
                LAG(p.tms)  OVER (PARTITION BY p.trip_id ORDER BY p.point_seq) AS prev_tms,
                LAG(p.geom) OVER (PARTITION BY p.trip_id ORDER BY p.point_seq) AS prev_geom,
                LEAD(p.tms)  OVER (PARTITION BY p.trip_id ORDER BY p.point_seq) AS next_tms,
                LEAD(p.geom) OVER (PARTITION BY p.trip_id ORDER BY p.point_seq) AS next_geom
            FROM dw_fact_gps_point p
            JOIN ods_trips t ON t.trip_id = p.trip_id
            WHERE t.trip_date = v_date
              AND p.speed_kmh IS NULL
        )
        UPDATE dw_fact_gps_point p
        SET
            speed_kmh = CASE
                WHEN b.next_tms IS NOT NULL AND b.next_tms > b.tms AND b.next_geom IS NOT NULL
                THEN ST_Distance(b.geom::geography, b.next_geom::geography) / (b.next_tms - b.tms) * 3.6
                WHEN b.prev_tms IS NOT NULL AND b.tms > b.prev_tms AND b.prev_geom IS NOT NULL
                THEN ST_Distance(b.prev_geom::geography, b.geom::geography) / (b.tms - b.prev_tms) * 3.6
                ELSE NULL
            END,
            heading = CASE
                WHEN b.next_geom IS NOT NULL AND NOT ST_Equals(b.geom, b.next_geom)
                THEN DEGREES(ST_Azimuth(b.geom, b.next_geom))
                WHEN b.prev_geom IS NOT NULL AND NOT ST_Equals(b.prev_geom, b.geom)
                THEN DEGREES(ST_Azimuth(b.prev_geom, b.geom))
                ELSE NULL
            END
        FROM base b
        WHERE p.id = b.id AND p.speed_kmh IS NULL;

        RAISE NOTICE '日期 % GPS运动回补完成', v_date;
    END LOOP;
END $$;

-- 4b. 回补 dw_fact_gps_point.road_id（来源：ods_trip_roads）
UPDATE dw_fact_gps_point p
SET road_id = r.road_id::bigint
FROM ods_trip_roads r
WHERE r.trip_id = p.trip_id
  AND r.match_seq = p.point_seq
  AND p.road_id IS NULL;

-- ============================================================
-- 5. dw_fact_road_flow_hourly / daily 装载
-- 来源：ods_trip_roads + ods_trips + dw_fact_trip
-- 距离均摊：total_distance / route_length（不按路段长度比例分摊）
-- 速度：按行程总距离加权平均
-- ============================================================
BEGIN;

WITH hourly_source AS (
    SELECT
        tr.road_id::bigint AS road_id,
        (CASE
            WHEN tr.match_time IS NOT NULL
            THEN to_timestamp(tr.match_time + 28800) AT TIME ZONE 'Asia/Shanghai'
            ELSE to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai'
         END)::date AS stat_date,
        EXTRACT(HOUR FROM (
            CASE
                WHEN tr.match_time IS NOT NULL
                THEN to_timestamp(tr.match_time + 28800) AT TIME ZONE 'Asia/Shanghai'
                ELSE to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai'
            END
        ))::int AS hour_slice,
        COUNT(DISTINCT tr.trip_id) AS trip_count,
        COUNT(DISTINCT t.devid) AS vehicle_count,
        SUM(ft.total_distance / NULLIF(ft.route_length, 0)) AS total_distance,
        CASE
            WHEN SUM(ft.total_distance) FILTER (WHERE ft.avg_speed IS NOT NULL AND ft.total_distance > 0) > 0
            THEN SUM(ft.avg_speed * ft.total_distance) FILTER (WHERE ft.avg_speed IS NOT NULL AND ft.total_distance > 0)
                 / NULLIF(SUM(ft.total_distance) FILTER (WHERE ft.avg_speed IS NOT NULL AND ft.total_distance > 0), 0)
            ELSE AVG(ft.avg_speed)
        END AS avg_speed
    FROM ods_trip_roads tr
    JOIN ods_trips t ON t.trip_id = tr.trip_id
    JOIN dw_fact_trip ft ON ft.trip_id = tr.trip_id
    GROUP BY
        tr.road_id::bigint,
        (CASE WHEN tr.match_time IS NOT NULL THEN to_timestamp(tr.match_time + 28800) AT TIME ZONE 'Asia/Shanghai' ELSE to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai' END)::date,
        EXTRACT(HOUR FROM (CASE WHEN tr.match_time IS NOT NULL THEN to_timestamp(tr.match_time + 28800) AT TIME ZONE 'Asia/Shanghai' ELSE to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai' END))::int
)
INSERT INTO dw_fact_road_flow_hourly (road_id, stat_date, hour_slice, trip_count, vehicle_count, total_distance, avg_speed, created_at)
SELECT road_id, stat_date, hour_slice, trip_count, vehicle_count, total_distance, avg_speed, NOW()
FROM hourly_source
ON CONFLICT (road_id, stat_date, hour_slice) DO UPDATE
SET trip_count = EXCLUDED.trip_count,
    vehicle_count = EXCLUDED.vehicle_count,
    total_distance = EXCLUDED.total_distance,
    avg_speed = EXCLUDED.avg_speed,
    created_at = EXCLUDED.created_at;

INSERT INTO dw_fact_road_flow_daily (road_id, stat_date, trip_count, vehicle_count, avg_speed, total_distance, created_at)
SELECT
    road_id, stat_date,
    SUM(trip_count), SUM(vehicle_count),
    SUM(avg_speed * COALESCE(total_distance, 0)) / NULLIF(SUM(COALESCE(total_distance, 0)) FILTER (WHERE avg_speed IS NOT NULL), 0),
    SUM(total_distance),
    NOW()
FROM dw_fact_road_flow_hourly
GROUP BY road_id, stat_date
ON CONFLICT (road_id, stat_date) DO UPDATE
SET trip_count = EXCLUDED.trip_count,
    vehicle_count = EXCLUDED.vehicle_count,
    avg_speed = EXCLUDED.avg_speed,
    total_distance = EXCLUDED.total_distance,
    created_at = EXCLUDED.created_at;

COMMIT;

-- ============================================================
-- 6. dw_fact_node_hourly / daily 装载
-- 来源：dw_dim_road（source/target node）+ dw_fact_road_flow_hourly
-- in_vehicle_count：车辆经过该节点作为路段 source（驶出节点）
-- out_vehicle_count：车辆经过该节点作为路段 target（驶入节点）
-- ============================================================
BEGIN;

WITH node_flow AS (
    SELECT
        f.stat_date,
        f.hour_slice,
        d.source_node_id AS node_id,
        f.vehicle_count AS out_vehicles,
        0 AS in_vehicles
    FROM dw_fact_road_flow_hourly f
    JOIN dw_dim_road d ON d.road_id = f.road_id
    WHERE d.source_node_id IS NOT NULL
    UNION ALL
    SELECT
        f.stat_date,
        f.hour_slice,
        d.target_node_id AS node_id,
        0 AS out_vehicles,
        f.vehicle_count AS in_vehicles
    FROM dw_fact_road_flow_hourly f
    JOIN dw_dim_road d ON d.road_id = f.road_id
    WHERE d.target_node_id IS NOT NULL
),
node_hourly_agg AS (
    SELECT
        node_id, stat_date, hour_slice,
        SUM(in_vehicles)  AS in_vehicle_count,
        SUM(out_vehicles) AS out_vehicle_count
    FROM node_flow
    GROUP BY node_id, stat_date, hour_slice
)
INSERT INTO dw_fact_node_hourly (node_id, stat_date, hour_slice, in_vehicle_count, out_vehicle_count, created_at)
SELECT node_id, stat_date, hour_slice, in_vehicle_count, out_vehicle_count, NOW()
FROM node_hourly_agg
ON CONFLICT (node_id, stat_date, hour_slice) DO UPDATE
SET in_vehicle_count  = EXCLUDED.in_vehicle_count,
    out_vehicle_count = EXCLUDED.out_vehicle_count,
    created_at        = EXCLUDED.created_at;

INSERT INTO dw_fact_node_daily (node_id, stat_date, in_vehicle_count, out_vehicle_count, created_at)
SELECT node_id, stat_date, SUM(in_vehicle_count), SUM(out_vehicle_count), NOW()
FROM dw_fact_node_hourly
GROUP BY node_id, stat_date
ON CONFLICT (node_id, stat_date) DO UPDATE
SET in_vehicle_count  = EXCLUDED.in_vehicle_count,
    out_vehicle_count = EXCLUDED.out_vehicle_count,
    created_at        = EXCLUDED.created_at;

COMMIT;

-- 6a. 回补 dw_fact_node_hourly / daily avg_speed
UPDATE dw_fact_node_hourly nh
SET avg_speed = sub.node_avg_speed
FROM (
    SELECT
        d.source_node_id AS node_id,
        f.stat_date, f.hour_slice,
        AVG(f.avg_speed) AS node_avg_speed
    FROM dw_fact_road_flow_hourly f
    JOIN dw_dim_road d ON d.road_id = f.road_id
    WHERE d.source_node_id IS NOT NULL AND f.avg_speed IS NOT NULL
    GROUP BY d.source_node_id, f.stat_date, f.hour_slice
) sub
WHERE nh.node_id = sub.node_id
  AND nh.stat_date = sub.stat_date
  AND nh.hour_slice = sub.hour_slice;

UPDATE dw_fact_node_daily nd
SET avg_speed = sub.node_avg_speed
FROM (
    SELECT node_id, stat_date, AVG(avg_speed) AS node_avg_speed
    FROM dw_fact_node_hourly
    WHERE avg_speed IS NOT NULL
    GROUP BY node_id, stat_date
) sub
WHERE nd.node_id = sub.node_id AND nd.stat_date = sub.stat_date;

-- ============================================================
-- 7. dw_fact_network_hourly / daily 装载
-- 来源：dw_fact_trip
-- 速度：按 total_distance 加权均值
-- ============================================================
BEGIN;

WITH trip_hour AS (
    SELECT
        trip_date AS stat_date,
        EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice,
        devid, total_distance, avg_speed, duration
    FROM dw_fact_trip
)
INSERT INTO dw_fact_network_hourly (stat_date, hour_slice, total_trips, total_vehicles, total_distance, network_avg_speed, created_at)
SELECT
    stat_date, hour_slice,
    COUNT(*) AS total_trips,
    COUNT(DISTINCT devid) AS total_vehicles,
    SUM(total_distance),
    CASE
        WHEN SUM(total_distance) FILTER (WHERE avg_speed IS NOT NULL AND total_distance > 0) > 0
        THEN SUM(avg_speed * total_distance) FILTER (WHERE avg_speed IS NOT NULL AND total_distance > 0)
             / SUM(total_distance) FILTER (WHERE avg_speed IS NOT NULL AND total_distance > 0)
        ELSE AVG(avg_speed)
    END AS network_avg_speed,
    NOW()
FROM trip_hour
GROUP BY stat_date, hour_slice
ON CONFLICT (stat_date, hour_slice) DO UPDATE
SET total_trips = EXCLUDED.total_trips,
    total_vehicles = EXCLUDED.total_vehicles,
    total_distance = EXCLUDED.total_distance,
    network_avg_speed = EXCLUDED.network_avg_speed,
    created_at = EXCLUDED.created_at;

INSERT INTO dw_fact_network_daily (
    stat_date, total_trips, total_vehicles, total_distance,
    network_avg_speed, network_avg_duration,
    morning_rush_trips, evening_rush_trips, night_trips, created_at
)
SELECT
    trip_date AS stat_date,
    COUNT(*) AS total_trips,
    COUNT(DISTINCT devid) AS total_vehicles,
    SUM(total_distance),
    CASE
        WHEN SUM(total_distance) FILTER (WHERE avg_speed IS NOT NULL AND total_distance > 0) > 0
        THEN SUM(avg_speed * total_distance) FILTER (WHERE avg_speed IS NOT NULL AND total_distance > 0)
             / SUM(total_distance) FILTER (WHERE avg_speed IS NOT NULL AND total_distance > 0)
        ELSE AVG(avg_speed)
    END AS network_avg_speed,
    AVG(duration) AS network_avg_duration,
    COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int IN (7, 8)) AS morning_rush_trips,
    COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int IN (17, 18)) AS evening_rush_trips,
    COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM (to_timestamp(start_time) AT TIME ZONE 'Asia/Shanghai'))::int IN (19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6)) AS night_trips,
    NOW()
FROM dw_fact_trip
GROUP BY trip_date
ON CONFLICT (stat_date) DO UPDATE
SET total_trips = EXCLUDED.total_trips,
    total_vehicles = EXCLUDED.total_vehicles,
    total_distance = EXCLUDED.total_distance,
    network_avg_speed = EXCLUDED.network_avg_speed,
    network_avg_duration = EXCLUDED.network_avg_duration,
    morning_rush_trips = EXCLUDED.morning_rush_trips,
    evening_rush_trips = EXCLUDED.evening_rush_trips,
    night_trips = EXCLUDED.night_trips,
    created_at = EXCLUDED.created_at;

COMMIT;

-- ============================================================
-- 8. dw_fact_road_travel_time 装载
-- 算法：gaps-and-islands 识别连续路段遍历，过滤 10~1800 秒
-- 来源：ods_trip_roads（按日期分批）
-- ============================================================
DO $$
DECLARE
    v_date DATE;
BEGIN
    FOR v_date IN
        SELECT DISTINCT trip_date FROM ods_trips ORDER BY trip_date
    LOOP
        WITH road_runs AS (
            SELECT
                r.trip_id, r.road_id, r.match_seq, r.match_time,
                r.match_seq - ROW_NUMBER() OVER (
                    PARTITION BY r.trip_id, r.road_id ORDER BY r.match_seq
                ) AS run_group
            FROM ods_trip_roads r
            JOIN ods_trips t ON r.trip_id = t.trip_id
            WHERE t.trip_date = v_date
        ),
        traversals AS (
            SELECT
                road_id,
                (to_timestamp(MIN(match_time) + 28800) AT TIME ZONE 'Asia/Shanghai')::date AS stat_date,
                EXTRACT(HOUR FROM (to_timestamp(MIN(match_time) + 28800) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice,
                MAX(match_time) - MIN(match_time) AS travel_time_s
            FROM road_runs
            GROUP BY trip_id, road_id, run_group
            HAVING COUNT(*) >= 2
               AND MAX(match_time) > MIN(match_time)
               AND MAX(match_time) - MIN(match_time) BETWEEN 10 AND 1800
        )
        INSERT INTO dw_fact_road_travel_time (
            road_id, stat_date, hour_slice,
            sample_count, min_travel_time, max_travel_time, avg_travel_time,
            p50_travel_time, p90_travel_time, p95_travel_time, created_at
        )
        SELECT
            road_id, stat_date, hour_slice,
            COUNT(*),
            MIN(travel_time_s), MAX(travel_time_s), AVG(travel_time_s),
            PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY travel_time_s),
            PERCENTILE_CONT(0.9)  WITHIN GROUP (ORDER BY travel_time_s),
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY travel_time_s),
            NOW()
        FROM traversals
        GROUP BY road_id, stat_date, hour_slice
        ON CONFLICT (road_id, stat_date, hour_slice) DO UPDATE
        SET sample_count    = EXCLUDED.sample_count,
            min_travel_time = EXCLUDED.min_travel_time,
            max_travel_time = EXCLUDED.max_travel_time,
            avg_travel_time = EXCLUDED.avg_travel_time,
            p50_travel_time = EXCLUDED.p50_travel_time,
            p90_travel_time = EXCLUDED.p90_travel_time,
            p95_travel_time = EXCLUDED.p95_travel_time,
            created_at      = EXCLUDED.created_at;

        RAISE NOTICE '日期 % 路段通行时间装载完成', v_date;
    END LOOP;
END $$;

-- ============================================================
-- 9. dw_fact_poi_hourly / daily 装载
-- 来源：dw_fact_trip（起终点坐标）+ dw_dim_poi（空间匹配300m）
-- ============================================================
BEGIN;

WITH trip_base AS (
    SELECT
        f.trip_id, f.devid, f.total_distance, f.duration,
        t.trip_date AS stat_date,
        EXTRACT(HOUR FROM (to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice,
        ST_SetSRID(ST_MakePoint(f.start_lon, f.start_lat), 4326) AS origin_geom,
        ST_SetSRID(ST_MakePoint(f.end_lon, f.end_lat), 4326) AS dest_geom
    FROM dw_fact_trip f
    JOIN ods_trips t ON t.trip_id = f.trip_id
    WHERE f.start_lon IS NOT NULL AND f.end_lon IS NOT NULL
),
poi_match AS (
    SELECT
        b.trip_id, b.stat_date, b.hour_slice, b.devid,
        op.poi_id AS origin_poi_id, dp.poi_id AS dest_poi_id
    FROM trip_base b
    LEFT JOIN LATERAL (
        SELECT p.poi_id FROM dw_dim_poi p
        WHERE ST_DWithin(p.geom::geography, b.origin_geom::geography, 300)
        ORDER BY p.geom <-> b.origin_geom LIMIT 1
    ) op ON TRUE
    LEFT JOIN LATERAL (
        SELECT p.poi_id FROM dw_dim_poi p
        WHERE ST_DWithin(p.geom::geography, b.dest_geom::geography, 300)
        ORDER BY p.geom <-> b.dest_geom LIMIT 1
    ) dp ON TRUE
)
INSERT INTO dw_fact_poi_hourly (poi_id, stat_date, hour_slice, trip_count, pickup_count, dropoff_count, created_at)
SELECT
    poi_id, stat_date, hour_slice,
    COUNT(DISTINCT trip_id),
    COUNT(*) FILTER (WHERE role = 'pickup'),
    COUNT(*) FILTER (WHERE role = 'dropoff'),
    NOW()
FROM (
    SELECT trip_id, stat_date, hour_slice, origin_poi_id AS poi_id, 'pickup' AS role
    FROM poi_match WHERE origin_poi_id IS NOT NULL
    UNION ALL
    SELECT trip_id, stat_date, hour_slice, dest_poi_id AS poi_id, 'dropoff' AS role
    FROM poi_match WHERE dest_poi_id IS NOT NULL
) s
GROUP BY poi_id, stat_date, hour_slice
ON CONFLICT (poi_id, stat_date, hour_slice) DO UPDATE
SET trip_count = EXCLUDED.trip_count,
    pickup_count = EXCLUDED.pickup_count,
    dropoff_count = EXCLUDED.dropoff_count,
    created_at = EXCLUDED.created_at;

INSERT INTO dw_fact_poi_daily (poi_id, stat_date, trip_count, pickup_count, dropoff_count, created_at)
SELECT poi_id, stat_date, SUM(trip_count), SUM(pickup_count), SUM(dropoff_count), NOW()
FROM dw_fact_poi_hourly
GROUP BY poi_id, stat_date
ON CONFLICT (poi_id, stat_date) DO UPDATE
SET trip_count = EXCLUDED.trip_count,
    pickup_count = EXCLUDED.pickup_count,
    dropoff_count = EXCLUDED.dropoff_count,
    created_at = EXCLUDED.created_at;

COMMIT;

-- ============================================================
-- 10. dw_fact_od_grid_hourly / daily 装载
-- 网格规则：500m EPSG:3857，grid_id = CONCAT(FLOOR(x/500), '_', FLOOR(y/500))
-- ============================================================
BEGIN;

WITH trip_grid AS (
    SELECT
        f.trip_id, f.devid,
        t.trip_date AS stat_date,
        EXTRACT(HOUR FROM (to_timestamp(t.start_time) AT TIME ZONE 'Asia/Shanghai'))::int AS hour_slice,
        f.total_distance, f.duration,
        CONCAT(
            FLOOR(ST_X(ST_Transform(ST_SetSRID(ST_MakePoint(f.start_lon, f.start_lat), 4326), 3857)) / 500)::bigint,
            '_',
            FLOOR(ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint(f.start_lon, f.start_lat), 4326), 3857)) / 500)::bigint
        ) AS origin_grid_id,
        CONCAT(
            FLOOR(ST_X(ST_Transform(ST_SetSRID(ST_MakePoint(f.end_lon, f.end_lat), 4326), 3857)) / 500)::bigint,
            '_',
            FLOOR(ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint(f.end_lon, f.end_lat), 4326), 3857)) / 500)::bigint
        ) AS dest_grid_id
    FROM dw_fact_trip f
    JOIN ods_trips t ON t.trip_id = f.trip_id
    WHERE f.start_lon IS NOT NULL AND f.end_lon IS NOT NULL
)
INSERT INTO dw_fact_od_grid_hourly (
    origin_grid_id, dest_grid_id, stat_date, hour_slice,
    trip_count, vehicle_count, avg_distance, avg_duration, created_at
)
SELECT
    origin_grid_id, dest_grid_id, stat_date, hour_slice,
    COUNT(*), COUNT(DISTINCT devid), AVG(total_distance), AVG(duration), NOW()
FROM trip_grid
GROUP BY origin_grid_id, dest_grid_id, stat_date, hour_slice
ON CONFLICT (origin_grid_id, dest_grid_id, stat_date, hour_slice) DO UPDATE
SET trip_count = EXCLUDED.trip_count,
    vehicle_count = EXCLUDED.vehicle_count,
    avg_distance = EXCLUDED.avg_distance,
    avg_duration = EXCLUDED.avg_duration,
    created_at = EXCLUDED.created_at;

INSERT INTO dw_fact_od_grid_daily (
    origin_grid_id, dest_grid_id, stat_date,
    trip_count, vehicle_count, avg_distance, avg_duration, created_at
)
SELECT
    origin_grid_id, dest_grid_id, stat_date,
    SUM(trip_count), SUM(vehicle_count), AVG(avg_distance), AVG(avg_duration), NOW()
FROM dw_fact_od_grid_hourly
GROUP BY origin_grid_id, dest_grid_id, stat_date
ON CONFLICT (origin_grid_id, dest_grid_id, stat_date) DO UPDATE
SET trip_count = EXCLUDED.trip_count,
    vehicle_count = EXCLUDED.vehicle_count,
    avg_distance = EXCLUDED.avg_distance,
    avg_duration = EXCLUDED.avg_duration,
    created_at = EXCLUDED.created_at;

COMMIT;

-- ============================================================
-- 11. dw_dim_grid 装载（从 dw_fact_od_grid_daily 的 zone_id 派生）
-- ============================================================
INSERT INTO dw_dim_grid (grid_id, col, row, center_lon, center_lat, center_geom)
SELECT DISTINCT
    zone_id,
    SPLIT_PART(zone_id, '_', 1)::INTEGER AS col,
    SPLIT_PART(zone_id, '_', 2)::INTEGER AS row,
    ST_X(center_geom)::DOUBLE PRECISION,
    ST_Y(center_geom)::DOUBLE PRECISION,
    center_geom
FROM (
    SELECT
        zone_id,
        ST_Transform(
            ST_SetSRID(
                ST_MakePoint(
                    (SPLIT_PART(zone_id, '_', 1)::BIGINT * 500 + 250)::DOUBLE PRECISION,
                    (SPLIT_PART(zone_id, '_', 2)::BIGINT * 500 + 250)::DOUBLE PRECISION
                ), 3857
            ), 4326
        ) AS center_geom
    FROM ads_hotspot_grid_daily
) grid_coords
ON CONFLICT (grid_id) DO UPDATE
SET col = EXCLUDED.col,
    row = EXCLUDED.row,
    center_lon = EXCLUDED.center_lon,
    center_lat = EXCLUDED.center_lat,
    center_geom = EXCLUDED.center_geom;
