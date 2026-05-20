from datetime import date
from typing import Literal, Optional

from sqlalchemy import distinct, func
from sqlmodel import Session, select

from models.ads import (
    AdsHotspotClusterDaily,
    AdsHotspotClusterHourly,
    AdsHotspotDistrictDaily,
    AdsHotspotDistrictHourly,
    AdsHotspotGridDaily,
    AdsHotspotGridHourly,
    AdsHotspotPoiDaily,
    AdsHotspotPoiHourly,
    AdsNetworkStatusHourly,
    AdsRoadStatusHourly,
    AdsTripDistanceHourly,
)
from models.dw import DwDimPoi, DwFactNetworkDaily, DwFactNetworkHourly, DwFactTrip
from models.road import BfmapWay

TimeMode = Literal["all", "day", "hour"]


class DashboardPageService:
    """Dashboard page composite queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_platform_stats(self) -> dict:
        net_row = self.session.exec(
            select(
                func.sum(DwFactNetworkDaily.total_trips),
                func.sum(DwFactNetworkDaily.total_distance),
            )
        ).one()
        vehicle_count = self.session.execute(
            select(func.count(distinct(DwFactTrip.devid)))
        ).scalar_one()
        road_count = self.session.execute(
            select(func.count(BfmapWay.gid))
        ).scalar_one()
        poi_count = self.session.execute(
            select(func.count(DwDimPoi.poi_id))
        ).scalar_one()
        total_distance = net_row[1]
        return {
            "total_trips": net_row[0] or 0,
            "total_vehicles": vehicle_count or 0,
            "total_distance_km": (total_distance / 1000.0) if total_distance else None,
            "road_segments": road_count or 0,
            "total_pois": poi_count or 0,
        }

    def get_day_stats(
        self, time_mode: TimeMode, stat_date: Optional[date]
    ) -> Optional[dict]:
        """In 'all' mode aggregate across all dates; 'day'/'hour' use the given date."""
        if time_mode == "all":
            row = self.session.exec(
                select(
                    func.sum(DwFactNetworkDaily.total_trips),
                    func.sum(DwFactNetworkDaily.total_vehicles),
                    func.sum(DwFactNetworkDaily.total_distance),
                    func.avg(DwFactNetworkDaily.network_avg_speed),
                    func.sum(DwFactNetworkDaily.morning_rush_trips),
                    func.sum(DwFactNetworkDaily.evening_rush_trips),
                )
            ).one()
            if not row or row[0] is None:
                return None
            return {
                "trips": int(row[0] or 0),
                "vehicles": int(row[1] or 0),
                "distance_km": (row[2] / 1000.0) if row[2] else None,
                "avg_speed": float(row[3]) if row[3] is not None else None,
                "morning_rush_trips": int(row[4]) if row[4] is not None else None,
                "evening_rush_trips": int(row[5]) if row[5] is not None else None,
            }

        if stat_date is None:
            return None
        row = self.session.exec(
            select(DwFactNetworkDaily).where(DwFactNetworkDaily.stat_date == stat_date)
        ).first()
        if not row:
            return None
        return {
            "trips": row.total_trips,
            "vehicles": row.total_vehicles,
            "distance_km": (row.total_distance / 1000.0) if row.total_distance else None,
            "avg_speed": row.network_avg_speed,
            "morning_rush_trips": row.morning_rush_trips,
            "evening_rush_trips": row.evening_rush_trips,
        }

    def get_hour_stats(self, stat_date: date, hour: int) -> Optional[dict]:
        row = self.session.exec(
            select(DwFactNetworkHourly).where(
                DwFactNetworkHourly.stat_date == stat_date,
                DwFactNetworkHourly.hour_slice == hour,
            )
        ).first()
        if not row:
            return None
        return {
            "trips": row.total_trips,
            "vehicles": row.total_vehicles,
            "avg_speed": row.network_avg_speed,
        }

    def get_network_trend(
        self,
        time_mode: TimeMode,
        stat_date: Optional[date],
        hour: Optional[int] = None,
    ) -> list[dict]:
        """Return 24-hour trend; for 'all' mode averaged across all dates; for 'hour' only the selected hour has values."""
        filters = []
        if time_mode in ("day", "hour") and stat_date is not None:
            filters.append(AdsRoadStatusHourly.stat_date == stat_date)
        filters.append(AdsRoadStatusHourly.status.isnot(None))

        rows = self.session.exec(
            select(
                AdsRoadStatusHourly.hour_slice,
                AdsRoadStatusHourly.status,
                func.count(AdsRoadStatusHourly.road_id),
                func.avg(AdsRoadStatusHourly.current_speed),
            )
            .where(*filters)
            .group_by(AdsRoadStatusHourly.hour_slice, AdsRoadStatusHourly.status)
        ).all()
        by_hour: dict[int, dict] = {}
        for hour_slice, status, count, avg_speed in rows:
            item = by_hour.setdefault(
                hour_slice,
                {
                    "total": 0,
                    "smooth": 0,
                    "congested": 0,
                    "speed_sum": 0.0,
                    "speed_count": 0,
                },
            )
            count = int(count or 0)
            item["total"] += count
            if status == "畅通":
                item["smooth"] += count
            elif status in ("轻度拥堵", "中度拥堵", "严重拥堵"):
                item["congested"] += count
            if avg_speed is not None:
                item["speed_sum"] += float(avg_speed) * count
                item["speed_count"] += count

        net_filters = []
        if time_mode in ("day", "hour") and stat_date is not None:
            net_filters.append(AdsNetworkStatusHourly.stat_date == stat_date)
        net_rows_query = select(
            AdsNetworkStatusHourly.hour_slice,
            func.avg(AdsNetworkStatusHourly.network_avg_speed),
        ).group_by(AdsNetworkStatusHourly.hour_slice)
        if net_filters:
            net_rows_query = net_rows_query.where(*net_filters)
        network_rows = {
            int(h): float(s) if s is not None else None
            for h, s in self.session.exec(net_rows_query).all()
        }

        items = []
        for h in range(24):
            if time_mode == "hour" and hour is not None and h != hour:
                items.append(
                    {
                        "hour": h,
                        "avg_speed": None,
                        "smooth_pct": 0.0,
                        "congested_pct": 0.0,
                    }
                )
                continue
            item = by_hour.get(h)
            if not item or item["total"] <= 0:
                items.append(
                    {
                        "hour": h,
                        "avg_speed": network_rows.get(h),
                        "smooth_pct": 0.0,
                        "congested_pct": 0.0,
                    }
                )
                continue
            items.append(
                {
                    "hour": h,
                    "avg_speed": (
                        item["speed_sum"] / item["speed_count"]
                        if item["speed_count"]
                        else network_rows.get(h)
                    ),
                    "smooth_pct": item["smooth"] / item["total"] * 100,
                    "congested_pct": item["congested"] / item["total"] * 100,
                }
            )
        return items

    def get_distance_trend(
        self,
        time_mode: TimeMode,
        stat_date: Optional[date],
        hour: Optional[int] = None,
    ) -> list[dict]:
        if time_mode == "all":
            rows = self.session.exec(
                select(
                    AdsTripDistanceHourly.hour_slice,
                    func.sum(AdsTripDistanceHourly.short_trips),
                    func.sum(AdsTripDistanceHourly.medium_trips),
                    func.sum(AdsTripDistanceHourly.long_trips),
                )
                .group_by(AdsTripDistanceHourly.hour_slice)
                .order_by(AdsTripDistanceHourly.hour_slice)
            ).all()
            return [
                {
                    "hour": int(h),
                    "short_trips": int(s or 0),
                    "medium_trips": int(m or 0),
                    "long_trips": int(l or 0),
                }
                for h, s, m, l in rows
            ]

        if stat_date is None:
            return []

        rows = self.session.exec(
            select(AdsTripDistanceHourly)
            .where(AdsTripDistanceHourly.stat_date == stat_date)
            .order_by(AdsTripDistanceHourly.hour_slice)
        ).all()
        result = [
            {
                "hour": row.hour_slice,
                "short_trips": row.short_trips,
                "medium_trips": row.medium_trips,
                "long_trips": row.long_trips,
            }
            for row in rows
        ]
        if time_mode == "hour" and hour is not None:
            return [item for item in result if item["hour"] == hour]
        return result

    def get_top_roads(
        self,
        time_mode: TimeMode,
        stat_date: Optional[date],
        hour: Optional[int],
        top_n: int,
    ) -> list[dict]:
        """Aggregate top congested roads under the current time scope."""
        filters = [AdsRoadStatusHourly.congestion_idx.isnot(None)]
        if time_mode in ("day", "hour") and stat_date is not None:
            filters.append(AdsRoadStatusHourly.stat_date == stat_date)
        if time_mode == "hour" and hour is not None:
            filters.append(AdsRoadStatusHourly.hour_slice == hour)

        rows = self.session.exec(
            select(
                AdsRoadStatusHourly.road_id,
                func.max(AdsRoadStatusHourly.road_name).label("road_name"),
                func.avg(AdsRoadStatusHourly.congestion_idx).label("avg_congestion"),
                func.avg(AdsRoadStatusHourly.current_speed).label("avg_speed"),
            )
            .where(*filters)
            .group_by(AdsRoadStatusHourly.road_id)
            .order_by(func.avg(AdsRoadStatusHourly.congestion_idx).desc())
            .limit(top_n)
        ).all()

        results = []
        for idx, row in enumerate(rows, start=1):
            congestion_idx = float(row.avg_congestion) if row.avg_congestion is not None else None
            results.append(
                {
                    "rank": idx,
                    "road_id": row.road_id,
                    "road_name": row.road_name,
                    "congestion_idx": congestion_idx,
                    "avg_speed": float(row.avg_speed) if row.avg_speed is not None else None,
                    "status": self._congestion_to_status(congestion_idx),
                }
            )
        return results

    def get_top_hotspots(
        self,
        time_mode: TimeMode,
        stat_date: Optional[date],
        hour: Optional[int],
        top_n: int,
        zone_type: str = "poi",
    ) -> list[dict]:
        if zone_type == "cluster":
            return self._get_top_clusters(time_mode, stat_date, hour, top_n)

        zone_models = {
            "district": (AdsHotspotDistrictDaily, AdsHotspotDistrictHourly),
            "grid": (AdsHotspotGridDaily, AdsHotspotGridHourly),
            "poi": (AdsHotspotPoiDaily, AdsHotspotPoiHourly),
        }
        models = zone_models.get(zone_type)
        if not models:
            return []
        daily_model, hourly_model = models

        def _row_to_dict(zone_id, zone_name, trip_count, avg_trip_distance):
            return {
                "zone_id": str(zone_id),
                "zone_name": zone_name,
                "zone_type": zone_type,
                "trip_count": int(trip_count or 0),
                "avg_trip_distance": float(avg_trip_distance) if avg_trip_distance is not None else None,
            }

        if time_mode == "all":
            rows = self.session.exec(
                select(
                    daily_model.zone_id,
                    func.max(daily_model.zone_name).label("zone_name"),
                    func.sum(daily_model.trip_count).label("trip_count"),
                    func.avg(daily_model.avg_trip_distance).label("avg_trip_distance"),
                )
                .group_by(daily_model.zone_id)
                .order_by(func.sum(daily_model.trip_count).desc())
                .limit(top_n)
            ).all()
            return [_row_to_dict(r.zone_id, r.zone_name, r.trip_count, r.avg_trip_distance) for r in rows]

        if stat_date is None:
            return []

        if time_mode == "hour" and hour is not None:
            rows = self.session.exec(
                select(hourly_model)
                .where(
                    hourly_model.stat_date == stat_date,
                    hourly_model.hour_slice == hour,
                )
                .order_by(hourly_model.trip_count.desc())
                .limit(top_n)
            ).all()
            return [_row_to_dict(r.zone_id, r.zone_name, r.trip_count, r.avg_trip_distance) for r in rows]

        rows = self.session.exec(
            select(daily_model)
            .where(daily_model.stat_date == stat_date)
            .order_by(daily_model.trip_count.desc())
            .limit(top_n)
        ).all()
        return [_row_to_dict(r.zone_id, r.zone_name, r.trip_count, r.avg_trip_distance) for r in rows]

    def _get_top_clusters(
        self,
        time_mode: TimeMode,
        stat_date: Optional[date],
        hour: Optional[int],
        top_n: int,
    ) -> list[dict]:
        def _row_to_dict(cluster_id, cluster_type, trip_count):
            return {
                "zone_id": str(cluster_id),
                "zone_name": cluster_type or f"聚类 {cluster_id}",
                "zone_type": "cluster",
                "trip_count": int(trip_count or 0),
                "avg_trip_distance": None,
            }

        if time_mode == "all":
            rows = self.session.exec(
                select(
                    AdsHotspotClusterDaily.cluster_id,
                    func.max(AdsHotspotClusterDaily.cluster_type).label("cluster_type"),
                    func.sum(AdsHotspotClusterDaily.trip_count).label("trip_count"),
                )
                .group_by(AdsHotspotClusterDaily.cluster_id)
                .order_by(func.sum(AdsHotspotClusterDaily.trip_count).desc())
                .limit(top_n)
            ).all()
            return [_row_to_dict(r.cluster_id, r.cluster_type, r.trip_count) for r in rows]

        if stat_date is None:
            return []

        if time_mode == "hour" and hour is not None:
            rows = self.session.exec(
                select(AdsHotspotClusterHourly)
                .where(
                    AdsHotspotClusterHourly.stat_date == stat_date,
                    AdsHotspotClusterHourly.hour_slice == hour,
                )
                .order_by(AdsHotspotClusterHourly.trip_count.desc())
                .limit(top_n)
            ).all()
            return [_row_to_dict(r.cluster_id, r.cluster_type, r.trip_count) for r in rows]

        rows = self.session.exec(
            select(AdsHotspotClusterDaily)
            .where(AdsHotspotClusterDaily.stat_date == stat_date)
            .order_by(AdsHotspotClusterDaily.trip_count.desc())
            .limit(top_n)
        ).all()
        return [_row_to_dict(r.cluster_id, r.cluster_type, r.trip_count) for r in rows]

    @staticmethod
    def _congestion_to_status(congestion_idx: Optional[float]) -> Optional[str]:
        if congestion_idx is None:
            return None
        if congestion_idx > 10 / 3:
            return "严重拥堵"
        if congestion_idx > 2.5:
            return "中度拥堵"
        if congestion_idx > 2.0:
            return "轻度拥堵"
        if congestion_idx > 10 / 7:
            return "基本畅通"
        return "畅通"
