from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models.ads import (
    AdsCongestionHourly,
    AdsHotspotClusterDaily,
    AdsHotspotClusterHourly,
    AdsHotspotDistrictDaily,
    AdsHotspotDistrictHourly,
    AdsHotspotGridDaily,
    AdsHotspotGridHourly,
    AdsHotspotMonitorDaily,
    AdsHotspotMonitorHourly,
    AdsHotspotPoiDaily,
    AdsHotspotPoiHourly,
    AdsNetworkStatusHourly,
    AdsRoadStatusHourly,
    AdsTopCongestedRoadsHourly,
    AdsTripDistanceDaily,
    AdsTripDistanceHourly,
    AdsTripSpeedDaily,
    AdsTripSpeedHourly,
    AdsTripTimeslotDaily,
)
from models.dw import DwDimDistrict, DwDimPoi


class AdsDataService:
    """ADS application metric queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_network_status_hourly(self, stat_date: date) -> list[dict]:
        rows = self.session.exec(
            select(AdsNetworkStatusHourly)
            .where(AdsNetworkStatusHourly.stat_date == stat_date)
            .order_by(AdsNetworkStatusHourly.hour_slice)
        ).all()

        distributions = self._road_status_distributions(stat_date)
        return [
            {
                "stat_date": row.stat_date,
                "hour": row.hour_slice,
                **self._merge_network_status_row(row, distributions.get(row.hour_slice)),
            }
            for row in rows
        ]

    def _road_status_distributions(self, stat_date: date) -> dict[int, dict]:
        rows = self.session.exec(
            select(
                AdsRoadStatusHourly.hour_slice,
                AdsRoadStatusHourly.status,
                func.count(AdsRoadStatusHourly.road_id),
                func.avg(AdsRoadStatusHourly.current_speed),
            )
            .where(
                AdsRoadStatusHourly.stat_date == stat_date,
                AdsRoadStatusHourly.status.isnot(None),
            )
            .group_by(AdsRoadStatusHourly.hour_slice, AdsRoadStatusHourly.status)
        ).all()

        distributions: dict[int, dict] = {}
        for hour, status, count, avg_speed in rows:
            item = distributions.setdefault(
                hour,
                {
                    "total_roads": 0,
                    "smooth_roads": 0,
                    "basically_smooth_roads": 0,
                    "light_congested_roads": 0,
                    "moderate_congested_roads": 0,
                    "severe_congested_roads": 0,
                    "speed_sum": 0.0,
                    "speed_count": 0,
                },
            )
            count = int(count or 0)
            item["total_roads"] += count
            if avg_speed is not None:
                item["speed_sum"] += float(avg_speed) * count
                item["speed_count"] += count
            if status == "畅通":
                item["smooth_roads"] += count
            elif status == "基本畅通":
                item["basically_smooth_roads"] += count
            elif status == "轻度拥堵":
                item["light_congested_roads"] += count
            elif status == "中度拥堵":
                item["moderate_congested_roads"] += count
            elif status == "严重拥堵":
                item["severe_congested_roads"] += count
        return distributions

    @staticmethod
    def _merge_network_status_row(row: AdsNetworkStatusHourly, dist: Optional[dict]) -> dict:
        if not dist or dist["total_roads"] <= 0:
            return {
                "total_roads": 0,
                "smooth_roads": 0,
                "basically_smooth_roads": 0,
                "light_congested_roads": 0,
                "moderate_congested_roads": 0,
                "severe_congested_roads": 0,
                "smooth_pct": 0.0,
                "basically_smooth_pct": 0.0,
                "light_congested_pct": 0.0,
                "moderate_congested_pct": 0.0,
                "severe_congested_pct": 0.0,
                "network_avg_speed": row.network_avg_speed,
            }

        total = dist["total_roads"]
        avg_speed = (
            dist["speed_sum"] / dist["speed_count"]
            if dist["speed_count"]
            else row.network_avg_speed
        )
        return {
            "total_roads": total,
            "smooth_roads": dist["smooth_roads"],
            "basically_smooth_roads": dist["basically_smooth_roads"],
            "light_congested_roads": dist["light_congested_roads"],
            "moderate_congested_roads": dist["moderate_congested_roads"],
            "severe_congested_roads": dist["severe_congested_roads"],
            "smooth_pct": dist["smooth_roads"] / total * 100,
            "basically_smooth_pct": dist["basically_smooth_roads"] / total * 100,
            "light_congested_pct": dist["light_congested_roads"] / total * 100,
            "moderate_congested_pct": dist["moderate_congested_roads"] / total * 100,
            "severe_congested_pct": dist["severe_congested_roads"] / total * 100,
            "network_avg_speed": avg_speed,
        }

    def list_congestion_hourly(self, stat_date: date) -> list[dict]:
        rows = self.session.exec(
            select(AdsCongestionHourly)
            .where(AdsCongestionHourly.stat_date == stat_date)
            .order_by(AdsCongestionHourly.hour_slice)
        ).all()
        return [
            {
                "stat_date": row.stat_date,
                "hour": row.hour_slice,
                "light_congested_roads": row.light_congested_roads,
                "moderate_congested_roads": row.moderate_congested_roads,
                "severe_congested_roads": row.severe_congested_roads,
                "avg_congestion": row.avg_congestion,
                "total_delay_min": row.total_delay_min,
            }
            for row in rows
        ]

    def list_top_congested_roads(
        self,
        stat_date: date,
        hour: int,
        limit: int = 10,
    ) -> list[dict]:
        rows = self.session.exec(
            select(AdsTopCongestedRoadsHourly)
            .where(
                AdsTopCongestedRoadsHourly.stat_date == stat_date,
                AdsTopCongestedRoadsHourly.hour_slice == hour,
            )
            .order_by(AdsTopCongestedRoadsHourly.rank_id)
            .limit(limit)
        ).all()
        return [
            {
                "rank_id": row.rank_id,
                "stat_date": row.stat_date,
                "hour": row.hour_slice,
                "road_id": row.road_id,
                "road_name": row.road_name,
                "congestion_idx": row.congestion_idx,
                "avg_speed": row.avg_speed,
                "trip_count": row.trip_count,
                "duration_loss": row.duration_loss,
            }
            for row in rows
        ]

    def list_trip_distance_hourly(self, stat_date: date) -> list[dict]:
        rows = self.session.exec(
            select(AdsTripDistanceHourly)
            .where(AdsTripDistanceHourly.stat_date == stat_date)
            .order_by(AdsTripDistanceHourly.hour_slice)
        ).all()
        return [
            {
                "stat_date": row.stat_date,
                "hour": row.hour_slice,
                "short_trips": row.short_trips,
                "medium_trips": row.medium_trips,
                "long_trips": row.long_trips,
                "avg_distance": row.avg_distance,
                "total_distance": row.total_distance,
                "sample_count": row.sample_count,
            }
            for row in rows
        ]

    def list_trip_distance_daily(self) -> list[dict]:
        rows = self.session.exec(
            select(AdsTripDistanceDaily).order_by(AdsTripDistanceDaily.stat_date)
        ).all()
        return [
            {
                "stat_date": row.stat_date,
                "short_trips": row.short_trips,
                "medium_trips": row.medium_trips,
                "long_trips": row.long_trips,
                "avg_distance": row.avg_distance,
                "total_distance": row.total_distance,
                "sample_count": row.sample_count,
            }
            for row in rows
        ]

    def list_trip_speed_hourly(self, stat_date: date) -> list[dict]:
        rows = self.session.exec(
            select(AdsTripSpeedHourly)
            .where(AdsTripSpeedHourly.stat_date == stat_date)
            .order_by(AdsTripSpeedHourly.hour_slice)
        ).all()
        return [
            {
                "stat_date": row.stat_date,
                "hour": row.hour_slice,
                "avg_speed": row.avg_speed,
                "speed_p50": row.speed_p50,
                "speed_p85": row.speed_p85,
                "speed_p95": row.speed_p95,
                "overspeed_ratio": row.overspeed_ratio,
                "sample_count": row.sample_count,
            }
            for row in rows
        ]

    def list_trip_speed_daily(self) -> list[dict]:
        rows = self.session.exec(
            select(AdsTripSpeedDaily).order_by(AdsTripSpeedDaily.stat_date)
        ).all()
        return [
            {
                "stat_date": row.stat_date,
                "avg_speed": row.avg_speed,
                "speed_p50": row.speed_p50,
                "speed_p85": row.speed_p85,
                "speed_p95": row.speed_p95,
                "sample_count": row.sample_count,
            }
            for row in rows
        ]

    def list_trip_timeslot_daily(self) -> list[dict]:
        rows = self.session.exec(
            select(AdsTripTimeslotDaily).order_by(AdsTripTimeslotDaily.stat_date)
        ).all()
        return [
            {
                "stat_date": row.stat_date,
                "morning_rush": row.morning_rush,
                "daytime": row.daytime,
                "evening_rush": row.evening_rush,
                "night": row.night,
                "weekday_trips": row.weekday_trips,
                "holiday_trips": row.holiday_trips,
                "sample_count": row.sample_count,
            }
            for row in rows
        ]

    def list_hotspot_monitor_daily(self, stat_date: date) -> list[dict]:
        return self.list_hotspot_monitor(time_mode="day", stat_date=stat_date, hour=None)

    def list_hotspot_monitor(
        self,
        time_mode: str = "day",
        stat_date: Optional[date] = None,
        hour: Optional[int] = None,
    ) -> list[dict]:
        """按时间口径聚合热点监测：
        - 'all'：跨全部日期，按 zone_type 汇总；max_hotspot 用各 zone 的全期 trip_count 排序取首。
        - 'day'：filter by stat_date（原行为）。
        - 'hour'：filter by stat_date+hour，取自 ads_hotspot_monitor_hourly。
        """
        if time_mode == "hour":
            if stat_date is None or hour is None:
                return []
            rows = self.session.exec(
                select(AdsHotspotMonitorHourly)
                .where(
                    AdsHotspotMonitorHourly.stat_date == stat_date,
                    AdsHotspotMonitorHourly.hour_slice == hour,
                )
                .order_by(AdsHotspotMonitorHourly.zone_type)
            ).all()
            base_rows = [
                {
                    "stat_date": r.stat_date,
                    "zone_type": r.zone_type,
                    "hotspot_count": r.hotspot_count,
                    "total_trip_count": r.total_trip_count,
                    "total_pickup_count": r.total_pickup_count,
                    "total_dropoff_count": r.total_dropoff_count,
                    "max_hotspot_zone_id": r.max_hotspot_zone_id,
                    "max_hotspot_zone_name": r.max_hotspot_zone_name,
                    "max_hotspot_trip_count": r.max_hotspot_trip_count,
                }
                for r in rows
            ]
        elif time_mode == "all":
            # 跨日聚合 ads_hotspot_monitor_daily：对每个 zone_type 取 SUM 指标，并按各日
            # 内 max_hotspot_zone 出现次数 + 行程量加权挑选总冠军（取 daily 中
            # max_hotspot_trip_count 最大的那条作为代表）
            agg_rows = self.session.execute(
                select(
                    AdsHotspotMonitorDaily.zone_type,
                    func.sum(AdsHotspotMonitorDaily.hotspot_count).label("hotspot_count"),
                    func.sum(AdsHotspotMonitorDaily.total_trip_count).label("total_trip_count"),
                    func.sum(AdsHotspotMonitorDaily.total_pickup_count).label("total_pickup_count"),
                    func.sum(AdsHotspotMonitorDaily.total_dropoff_count).label("total_dropoff_count"),
                ).group_by(AdsHotspotMonitorDaily.zone_type)
            ).all()

            # 对每个 zone_type 选取全期冠军：daily 表中 max_hotspot_trip_count 最大的那一天
            base_rows = []
            for r in agg_rows:
                top = self.session.execute(
                    select(
                        AdsHotspotMonitorDaily.stat_date,
                        AdsHotspotMonitorDaily.max_hotspot_zone_id,
                        AdsHotspotMonitorDaily.max_hotspot_zone_name,
                        AdsHotspotMonitorDaily.max_hotspot_trip_count,
                    )
                    .where(AdsHotspotMonitorDaily.zone_type == r.zone_type)
                    .order_by(AdsHotspotMonitorDaily.max_hotspot_trip_count.desc().nullslast())
                    .limit(1)
                ).first()
                base_rows.append(
                    {
                        "stat_date": top.stat_date if top else None,
                        "zone_type": r.zone_type,
                        "hotspot_count": int(r.hotspot_count or 0),
                        "total_trip_count": int(r.total_trip_count or 0),
                        "total_pickup_count": int(r.total_pickup_count or 0),
                        "total_dropoff_count": int(r.total_dropoff_count or 0),
                        "max_hotspot_zone_id": top.max_hotspot_zone_id if top else None,
                        "max_hotspot_zone_name": top.max_hotspot_zone_name if top else None,
                        "max_hotspot_trip_count": top.max_hotspot_trip_count if top else None,
                    }
                )
        else:
            if stat_date is None:
                return []
            rows = self.session.exec(
                select(AdsHotspotMonitorDaily)
                .where(AdsHotspotMonitorDaily.stat_date == stat_date)
                .order_by(AdsHotspotMonitorDaily.zone_type)
            ).all()
            base_rows = [
                {
                    "stat_date": r.stat_date,
                    "zone_type": r.zone_type,
                    "hotspot_count": r.hotspot_count,
                    "total_trip_count": r.total_trip_count,
                    "total_pickup_count": r.total_pickup_count,
                    "total_dropoff_count": r.total_dropoff_count,
                    "max_hotspot_zone_id": r.max_hotspot_zone_id,
                    "max_hotspot_zone_name": r.max_hotspot_zone_name,
                    "max_hotspot_trip_count": r.max_hotspot_trip_count,
                }
                for r in rows
            ]

        # 缺失 zone_name 时按 zone_type + id 回填语义化名称
        for row in base_rows:
            if (not row["max_hotspot_zone_name"]) and row["max_hotspot_zone_id"]:
                row["max_hotspot_zone_name"] = self._resolve_zone_name(
                    row["zone_type"], row["max_hotspot_zone_id"]
                )
        return base_rows

    def _resolve_zone_name(self, zone_type: str, zone_id: str) -> Optional[str]:
        if zone_type == "cluster":
            district = self._lookup_cluster_district(zone_id)
            if district:
                return f"聚类 #{zone_id}（{district}）"
            return f"聚类 #{zone_id}"
        if zone_type == "grid":
            return f"网格 {zone_id}"
        if zone_type == "poi":
            try:
                poi_id = int(zone_id)
            except (TypeError, ValueError):
                return None
            name = self.session.execute(
                select(DwDimPoi.poi_name).where(DwDimPoi.poi_id == poi_id)
            ).scalar()
            return name
        if zone_type == "district":
            name = self.session.execute(
                select(DwDimDistrict.district_name).where(
                    DwDimDistrict.district_code == zone_id
                )
            ).scalar()
            return name
        return None

    def _lookup_cluster_district(self, cluster_id: str) -> Optional[str]:
        try:
            cid = int(cluster_id)
        except (TypeError, ValueError):
            return None
        # 用 cluster center 与行政区 geom 求 ST_Within
        row = self.session.execute(
            select(AdsHotspotClusterDaily.center_lon, AdsHotspotClusterDaily.center_lat)
            .where(AdsHotspotClusterDaily.cluster_id == cid)
            .limit(1)
        ).first()
        if not row or row[0] is None or row[1] is None:
            return None
        lon, lat = row
        district = self.session.execute(
            select(DwDimDistrict.district_name)
            .where(
                func.ST_Within(
                    func.ST_SetSRID(func.ST_Point(lon, lat), 4326),
                    DwDimDistrict.geom,
                )
            )
            .limit(1)
        ).scalar()
        return district

    def list_road_status_hourly(
        self,
        stat_date: date,
        hour: int,
        status: Optional[str] = None,
        road_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [
            AdsRoadStatusHourly.stat_date == stat_date,
            AdsRoadStatusHourly.hour_slice == hour,
        ]
        if status is not None:
            filters.append(AdsRoadStatusHourly.status == status)
        if road_id is not None:
            filters.append(AdsRoadStatusHourly.road_id == road_id)

        count_query = select(func.count(AdsRoadStatusHourly.road_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                AdsRoadStatusHourly.road_id,
                AdsRoadStatusHourly.road_name,
                AdsRoadStatusHourly.road_class,
                AdsRoadStatusHourly.stat_date,
                AdsRoadStatusHourly.hour_slice.label("hour"),
                AdsRoadStatusHourly.current_speed,
                AdsRoadStatusHourly.current_flow,
                AdsRoadStatusHourly.congestion_idx,
                AdsRoadStatusHourly.status,
            )
            .where(*filters)
            .order_by(AdsRoadStatusHourly.congestion_idx.desc().nullslast())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_hotspot_district_hourly(
        self,
        stat_date: date,
        hour: Optional[int] = None,
    ) -> list[dict]:
        filters = [AdsHotspotDistrictHourly.stat_date == stat_date]
        if hour is not None:
            filters.append(AdsHotspotDistrictHourly.hour_slice == hour)

        query = (
            select(
                AdsHotspotDistrictHourly.zone_id,
                AdsHotspotDistrictHourly.zone_name,
                AdsHotspotDistrictHourly.stat_date,
                AdsHotspotDistrictHourly.hour_slice.label("hour"),
                AdsHotspotDistrictHourly.trip_count,
                AdsHotspotDistrictHourly.pickup_count,
                AdsHotspotDistrictHourly.dropoff_count,
                AdsHotspotDistrictHourly.vehicle_count,
                AdsHotspotDistrictHourly.avg_trip_distance,
                AdsHotspotDistrictHourly.avg_duration,
            )
            .where(*filters)
            .order_by(AdsHotspotDistrictHourly.hour_slice, AdsHotspotDistrictHourly.trip_count.desc())
        )
        rows = self.session.exec(query).all()
        return [dict(row._mapping) for row in rows]

    def list_hotspot_district_daily(self, stat_date: date) -> list[dict]:
        rows = self.session.exec(
            select(AdsHotspotDistrictDaily)
            .where(AdsHotspotDistrictDaily.stat_date == stat_date)
            .order_by(AdsHotspotDistrictDaily.trip_count.desc())
        ).all()
        return [
            {
                "zone_id": row.zone_id,
                "zone_name": row.zone_name,
                "stat_date": row.stat_date,
                "trip_count": row.trip_count,
                "pickup_count": row.pickup_count,
                "dropoff_count": row.dropoff_count,
                "vehicle_count": row.vehicle_count,
                "avg_trip_distance": row.avg_trip_distance,
                "avg_duration": row.avg_duration,
            }
            for row in rows
        ]

    def list_hotspot_grid_hourly(
        self,
        stat_date: date,
        hour: int,
        min_trip_count: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [
            AdsHotspotGridHourly.stat_date == stat_date,
            AdsHotspotGridHourly.hour_slice == hour,
        ]
        if min_trip_count is not None:
            filters.append(AdsHotspotGridHourly.trip_count >= min_trip_count)

        count_query = select(func.count(AdsHotspotGridHourly.zone_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                AdsHotspotGridHourly.zone_id,
                AdsHotspotGridHourly.zone_name,
                AdsHotspotGridHourly.stat_date,
                AdsHotspotGridHourly.hour_slice.label("hour"),
                AdsHotspotGridHourly.trip_count,
                AdsHotspotGridHourly.pickup_count,
                AdsHotspotGridHourly.dropoff_count,
                AdsHotspotGridHourly.vehicle_count,
                AdsHotspotGridHourly.avg_trip_distance,
                AdsHotspotGridHourly.avg_duration,
            )
            .where(*filters)
            .order_by(AdsHotspotGridHourly.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_hotspot_grid_daily(
        self,
        stat_date: date,
        min_trip_count: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [AdsHotspotGridDaily.stat_date == stat_date]
        if min_trip_count is not None:
            filters.append(AdsHotspotGridDaily.trip_count >= min_trip_count)

        count_query = select(func.count(AdsHotspotGridDaily.zone_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                AdsHotspotGridDaily.zone_id,
                AdsHotspotGridDaily.zone_name,
                AdsHotspotGridDaily.stat_date,
                AdsHotspotGridDaily.trip_count,
                AdsHotspotGridDaily.pickup_count,
                AdsHotspotGridDaily.dropoff_count,
                AdsHotspotGridDaily.vehicle_count,
                AdsHotspotGridDaily.avg_trip_distance,
                AdsHotspotGridDaily.avg_duration,
            )
            .where(*filters)
            .order_by(AdsHotspotGridDaily.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_hotspot_cluster_hourly(
        self,
        stat_date: date,
        hour: int,
        cluster_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [
            AdsHotspotClusterHourly.stat_date == stat_date,
            AdsHotspotClusterHourly.hour_slice == hour,
        ]
        if cluster_type is not None:
            filters.append(AdsHotspotClusterHourly.cluster_type == cluster_type)

        count_query = select(func.count(AdsHotspotClusterHourly.cluster_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                AdsHotspotClusterHourly.cluster_id,
                AdsHotspotClusterHourly.stat_date,
                AdsHotspotClusterHourly.hour_slice.label("hour"),
                AdsHotspotClusterHourly.center_lon,
                AdsHotspotClusterHourly.center_lat,
                AdsHotspotClusterHourly.cluster_type,
                AdsHotspotClusterHourly.trip_count,
                AdsHotspotClusterHourly.pickup_count,
                AdsHotspotClusterHourly.dropoff_count,
                AdsHotspotClusterHourly.avg_duration,
            )
            .where(*filters)
            .order_by(AdsHotspotClusterHourly.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_hotspot_cluster_daily(
        self,
        stat_date: date,
        cluster_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [AdsHotspotClusterDaily.stat_date == stat_date]
        if cluster_type is not None:
            filters.append(AdsHotspotClusterDaily.cluster_type == cluster_type)

        count_query = select(func.count(AdsHotspotClusterDaily.cluster_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                AdsHotspotClusterDaily.cluster_id,
                AdsHotspotClusterDaily.stat_date,
                AdsHotspotClusterDaily.center_lon,
                AdsHotspotClusterDaily.center_lat,
                AdsHotspotClusterDaily.cluster_type,
                AdsHotspotClusterDaily.trip_count,
                AdsHotspotClusterDaily.pickup_count,
                AdsHotspotClusterDaily.dropoff_count,
                AdsHotspotClusterDaily.avg_duration,
            )
            .where(*filters)
            .order_by(AdsHotspotClusterDaily.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_hotspot_poi_hourly(
        self,
        stat_date: date,
        hour: Optional[int] = None,
        zone_id: Optional[str] = None,
    ) -> list[dict]:
        filters = [AdsHotspotPoiHourly.stat_date == stat_date]
        if hour is not None:
            filters.append(AdsHotspotPoiHourly.hour_slice == hour)
        if zone_id is not None:
            filters.append(AdsHotspotPoiHourly.zone_id == zone_id)

        query = (
            select(
                AdsHotspotPoiHourly.zone_id,
                AdsHotspotPoiHourly.zone_name,
                AdsHotspotPoiHourly.stat_date,
                AdsHotspotPoiHourly.hour_slice.label("hour"),
                AdsHotspotPoiHourly.trip_count,
                AdsHotspotPoiHourly.pickup_count,
                AdsHotspotPoiHourly.dropoff_count,
                AdsHotspotPoiHourly.vehicle_count,
                AdsHotspotPoiHourly.avg_trip_distance,
                AdsHotspotPoiHourly.avg_duration,
            )
            .where(*filters)
            .order_by(AdsHotspotPoiHourly.hour_slice, AdsHotspotPoiHourly.trip_count.desc())
        )
        rows = self.session.exec(query).all()
        return [dict(row._mapping) for row in rows]

    def list_hotspot_poi_daily(
        self,
        stat_date: date,
        zone_id: Optional[str] = None,
    ) -> list[dict]:
        filters = [AdsHotspotPoiDaily.stat_date == stat_date]
        if zone_id is not None:
            filters.append(AdsHotspotPoiDaily.zone_id == zone_id)

        query = (
            select(
                AdsHotspotPoiDaily.zone_id,
                AdsHotspotPoiDaily.zone_name,
                AdsHotspotPoiDaily.stat_date,
                AdsHotspotPoiDaily.trip_count,
                AdsHotspotPoiDaily.pickup_count,
                AdsHotspotPoiDaily.dropoff_count,
                AdsHotspotPoiDaily.vehicle_count,
                AdsHotspotPoiDaily.avg_trip_distance,
                AdsHotspotPoiDaily.avg_duration,
            )
            .where(*filters)
            .order_by(AdsHotspotPoiDaily.trip_count.desc())
        )
        rows = self.session.exec(query).all()
        return [dict(row._mapping) for row in rows]
