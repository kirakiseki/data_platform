import json
from datetime import date
from typing import Optional

from sqlalchemy import func, text
from sqlmodel import Session, select

from models.dw import DwFactNetworkDaily, DwFactTrip
from models.ods import OdsTrip


class TrajectoryPageService:
    """Trajectory page queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_daily_stats(self) -> list[dict]:
        network_rows = self.session.exec(
            select(DwFactNetworkDaily).order_by(DwFactNetworkDaily.stat_date)
        ).all()

        ods_rows = self.session.exec(
            select(
                OdsTrip.trip_date,
                func.sum(OdsTrip.n_points).label("total_gps_points"),
                func.sum(OdsTrip.n_roads).label("total_matched_roads"),
            )
            .group_by(OdsTrip.trip_date)
            .order_by(OdsTrip.trip_date)
        ).all()

        ods_by_date = {row.trip_date: row for row in ods_rows}

        result = []
        for net in network_rows:
            ods = ods_by_date.get(net.stat_date)
            result.append(
                {
                    "stat_date": net.stat_date,
                    "trips": net.total_trips,
                    "total_vehicles": net.total_vehicles,
                    "total_gps_points": int(ods.total_gps_points) if ods and ods.total_gps_points else None,
                    "total_matched_roads": int(ods.total_matched_roads) if ods and ods.total_matched_roads else None,
                    "avg_speed": net.network_avg_speed,
                }
            )
        return result

    def get_samples(
        self,
        stat_date: Optional[date] = None,
        hour: Optional[int] = None,
        sample_size: int = 5,
        route_source: str = "matched",
    ) -> list[dict]:
        """采样行程路径。

        route_source:
            - "matched"：使用 ods_trip_routes.route_geom（地图匹配后的路段 WKT 列表），
              按顺序合并为 MultiLineString，严格沿道路。
            - "raw"：使用 dw_fact_trip.route_line（由触发器从 ods_trip_gps 原始点聚合），
              展示原始 GPS 轨迹。
        """
        if route_source == "matched":
            return self._get_matched_samples(stat_date, hour, sample_size)
        return self._get_raw_samples(stat_date, hour, sample_size)

    def _get_raw_samples(
        self,
        stat_date: Optional[date],
        hour: Optional[int],
        sample_size: int,
    ) -> list[dict]:
        # 先用轻字段池随机选 trip_id，再仅对采样集合算 ST_AsGeoJSON，避免对大表
        # 的全部 route_line 做 sort + 几何序列化。
        conditions = ["f.total_distance >= 3000", "f.route_line IS NOT NULL"]
        params: dict = {"pool_size": max(sample_size * 4, 40), "sample_size": sample_size}
        if stat_date is not None:
            conditions.append("f.trip_date = :stat_date")
            params["stat_date"] = stat_date
        if hour is not None and stat_date is not None:
            conditions.append("extract(hour from to_timestamp(f.start_time)) = :hour")
            params["hour"] = hour

        where_clause = " AND ".join(conditions)
        sql = text(
            f"""
            WITH pool AS (
                SELECT f.trip_id
                FROM dw_fact_trip f
                WHERE {where_clause}
                ORDER BY random()
                LIMIT :pool_size
            )
            SELECT
                f.trip_id,
                f.devid,
                f.trip_date,
                f.total_distance,
                f.duration,
                extract(hour from to_timestamp(f.start_time))::int AS start_hour,
                ST_AsGeoJSON(f.route_line) AS route_line_json
            FROM pool p
            JOIN dw_fact_trip f ON f.trip_id = p.trip_id
            LIMIT :sample_size
            """
        )
        rows = self.session.execute(sql, params).all()

        result = []
        for row in rows:
            route_line = None
            if row.route_line_json:
                try:
                    route_line = json.loads(row.route_line_json)
                except (ValueError, TypeError):
                    pass
            result.append(
                {
                    "trip_id": row.trip_id,
                    "devid": row.devid,
                    "trip_date": row.trip_date,
                    "start_hour": int(row.start_hour) if row.start_hour is not None else None,
                    "total_distance_m": row.total_distance,
                    "duration_s": row.duration,
                    "route_line": route_line,
                    "route_source": "raw",
                }
            )
        return result

    def _get_matched_samples(
        self,
        stat_date: Optional[date],
        hour: Optional[int],
        sample_size: int,
    ) -> list[dict]:
        """构造严格沿道路的轨迹：
        - 先在 dw_fact_trip 上按 trip_date / 起始小时 / 长度过滤后随机采样 trip_id（候选池）
        - 再把 ods_trip_routes.route 数组按顺序展开，JOIN bfmap_ways.geom，
          用 ST_Collect 拼成 MultiLineString，最后 ST_AsGeoJSON 输出
        这样所有 WKT 都是 PostGIS 原生几何，不会出 GeometryCollection 边角情况，
        采样池小、性能稳定。
        """
        conditions = ["f.total_distance >= 3000", "f.route_line IS NOT NULL"]
        params: dict = {"pool_size": max(sample_size * 4, 40), "sample_size": sample_size}
        if stat_date is not None:
            conditions.append("f.trip_date = :stat_date")
            params["stat_date"] = stat_date
        if hour is not None and stat_date is not None:
            conditions.append("extract(hour from to_timestamp(f.start_time)) = :hour")
            params["hour"] = hour

        where_clause = " AND ".join(conditions)
        sql = text(
            f"""
            WITH pool AS (
                SELECT f.trip_id, f.devid, f.trip_date, f.total_distance, f.duration,
                       f.start_time
                FROM dw_fact_trip f
                WHERE {where_clause}
                ORDER BY random()
                LIMIT :pool_size
            ),
            with_route AS (
                SELECT p.trip_id, p.devid, p.trip_date, p.total_distance, p.duration,
                       p.start_time,
                       r.route
                FROM pool p
                JOIN ods_trip_routes r ON r.trip_id = p.trip_id
                WHERE r.route IS NOT NULL AND array_length(r.route, 1) >= 2
                LIMIT :sample_size
            ),
            road_lines AS (
                SELECT w.trip_id, w.devid, w.trip_date, w.total_distance, w.duration,
                       w.start_time,
                       ST_Collect(b.geom ORDER BY u.ord) AS line_geom
                FROM with_route w
                CROSS JOIN LATERAL unnest(w.route) WITH ORDINALITY AS u(road_id, ord)
                JOIN bfmap_ways b ON b.gid = u.road_id
                GROUP BY w.trip_id, w.devid, w.trip_date, w.total_distance,
                         w.duration, w.start_time
            )
            SELECT
                trip_id,
                devid,
                trip_date,
                total_distance,
                duration,
                extract(hour from to_timestamp(start_time))::int AS start_hour,
                ST_AsGeoJSON(line_geom) AS route_line_json
            FROM road_lines
            """
        )
        rows = self.session.execute(sql, params).all()

        result = []
        for row in rows:
            route_line = None
            if row.route_line_json:
                try:
                    route_line = json.loads(row.route_line_json)
                except (ValueError, TypeError):
                    pass
            result.append(
                {
                    "trip_id": row.trip_id,
                    "devid": row.devid,
                    "trip_date": row.trip_date,
                    "start_hour": int(row.start_hour) if row.start_hour is not None else None,
                    "total_distance_m": row.total_distance,
                    "duration_s": row.duration,
                    "route_line": route_line,
                    "route_source": "matched",
                }
            )
        return result
