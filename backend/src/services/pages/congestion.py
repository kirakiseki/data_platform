import json
from datetime import date
from typing import Literal, Optional

from sqlalchemy import func, literal_column
from sqlmodel import Session, select

from models.ads import AdsRoadStatusHourly


class CongestionPageService:
    """Congestion GeoJSON page queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_roads_geojson(
        self,
        stat_date: date,
        hour: int,
        status: Optional[str] = None,
        limit: int = 200,
        all_roads: bool = False,
        center_lng: Optional[float] = None,
        center_lat: Optional[float] = None,
        bbox: Optional[tuple[float, float, float, float]] = None,
        cursor: Optional[int] = None,
        simplify_tolerance: Optional[float] = None,
    ) -> dict:
        """Return a page of features.

        - When ``bbox`` is given pagination is keyset by ``road_id`` (stable, no offset cost).
        - When ``simplify_tolerance > 0`` geometry is simplified server-side to cut payload size.
        - The returned ``next_cursor`` is None when the result set is exhausted.
        """
        filters = [
            AdsRoadStatusHourly.stat_date == stat_date,
            AdsRoadStatusHourly.hour_slice == hour,
            AdsRoadStatusHourly.geom.isnot(None),
            # 全网图也只显示有有效状态的路段（vehicle_count > 3 的样本）。
            # 否则地图上 status=NULL 的稀疏路段仍会通过 current_flow>0 这条 OR
            # 漏进来，且前端用 statusByCongestion 兜底着色，与排行口径不一致。
            AdsRoadStatusHourly.status.isnot(None),
        ]
        if not all_roads:
            if status is not None:
                filters.append(AdsRoadStatusHourly.status == status)
            else:
                filters.append(AdsRoadStatusHourly.status.in_(["轻度拥堵", "中度拥堵", "严重拥堵"]))

        if bbox is not None:
            min_lng, min_lat, max_lng, max_lat = bbox
            envelope = func.ST_MakeEnvelope(
                literal_column(str(min_lng)),
                literal_column(str(min_lat)),
                literal_column(str(max_lng)),
                literal_column(str(max_lat)),
                4326,
            )
            filters.append(func.ST_Intersects(AdsRoadStatusHourly.geom, envelope))

        if cursor is not None:
            filters.append(AdsRoadStatusHourly.road_id > cursor)

        if simplify_tolerance and simplify_tolerance > 0:
            geom_expr = func.ST_AsGeoJSON(
                func.ST_SimplifyPreserveTopology(
                    AdsRoadStatusHourly.geom,
                    literal_column(str(simplify_tolerance)),
                )
            ).label("geom_json")
        else:
            geom_expr = func.ST_AsGeoJSON(AdsRoadStatusHourly.geom).label("geom_json")

        select_cols = [
            AdsRoadStatusHourly.road_id,
            AdsRoadStatusHourly.road_name,
            AdsRoadStatusHourly.status,
            AdsRoadStatusHourly.congestion_idx,
            AdsRoadStatusHourly.current_speed,
            AdsRoadStatusHourly.current_flow,
            geom_expr,
        ]

        query = select(*select_cols).where(*filters)

        # 用 road_id 做 keyset 排序保证分页稳定；bbox + 索引下扫描代价可控。
        if cursor is not None or bbox is not None:
            query = query.order_by(AdsRoadStatusHourly.road_id.asc())
        elif center_lng is not None and center_lat is not None:
            center_geom = func.ST_SetSRID(
                func.ST_MakePoint(literal_column(str(center_lng)), literal_column(str(center_lat))),
                4326,
            )
            query = query.order_by(func.ST_Distance(AdsRoadStatusHourly.geom, center_geom).asc())
        else:
            query = query.order_by(AdsRoadStatusHourly.congestion_idx.desc().nullslast())

        rows = self.session.exec(query.limit(limit)).all()

        features = []
        last_road_id: Optional[int] = None
        for row in rows:
            if not row.geom_json:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(row.geom_json),
                    "properties": {
                        "road_id": row.road_id,
                        "road_name": row.road_name,
                        "status": row.status,
                        "congestion_idx": row.congestion_idx,
                        "avg_speed": row.current_speed,
                        "trip_count": row.current_flow,
                    },
                }
            )
            last_road_id = row.road_id

        # 只有 keyset 模式下才返回 next_cursor；其它排序方式分页结果不稳定。
        next_cursor = None
        if (cursor is not None or bbox is not None) and len(rows) >= limit and last_road_id is not None:
            next_cursor = last_road_id

        return {"features": features, "next_cursor": next_cursor}

    def get_roads_ranking(
        self,
        stat_date: date,
        hour: int,
        sort_by: Literal["congestion", "flow"] = "congestion",
        limit: int = 20,
    ) -> list[dict]:
        """全网范围内按拥堵指数或道路流量排序，返回 TopN（无几何）。"""
        filters = [
            AdsRoadStatusHourly.stat_date == stat_date,
            AdsRoadStatusHourly.hour_slice == hour,
            # 拥堵排行只看有效状态行；trip_count<=3 的稀疏样本 status 为 NULL，
            # 此处必须显式过滤，否则会泄漏到排行里被前端兜底成 "严重拥堵"。
            AdsRoadStatusHourly.status.isnot(None),
        ]
        if sort_by == "flow":
            filters.append(AdsRoadStatusHourly.current_flow.isnot(None))
            filters.append(AdsRoadStatusHourly.current_flow > 0)
            order_col = AdsRoadStatusHourly.current_flow.desc().nullslast()
        else:
            filters.append(AdsRoadStatusHourly.congestion_idx.isnot(None))
            order_col = AdsRoadStatusHourly.congestion_idx.desc().nullslast()

        rows = self.session.exec(
            select(
                AdsRoadStatusHourly.road_id,
                AdsRoadStatusHourly.road_name,
                AdsRoadStatusHourly.status,
                AdsRoadStatusHourly.congestion_idx,
                AdsRoadStatusHourly.current_speed,
                AdsRoadStatusHourly.current_flow,
            )
            .where(*filters)
            .order_by(order_col)
            .limit(limit)
        ).all()

        return [
            {
                "road_id": row.road_id,
                "road_name": row.road_name,
                "status": row.status,
                "congestion_idx": row.congestion_idx,
                "avg_speed": row.current_speed,
                "trip_count": row.current_flow,
            }
            for row in rows
        ]
