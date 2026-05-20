from datetime import date
from typing import Optional

from sqlalchemy import String, cast, func
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
)
from models.dw import DwDimDistrict, DwDimGrid, DwDimPoi


class HotspotPageService:
    """Hotspot zones page composite queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_zones(
        self,
        zone_type: str,
        stat_date: date,
        hour: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        if zone_type == "district":
            return self._get_district_zones(stat_date, hour, page, page_size)
        if zone_type == "grid":
            return self._get_grid_zones(stat_date, hour, page, page_size)
        if zone_type == "poi":
            return self._get_poi_zones(stat_date, hour, page, page_size)
        if zone_type == "cluster":
            return self._get_cluster_zones(stat_date, hour, page, page_size)
        return 0, []

    def _get_district_zones(
        self, stat_date: date, hour: Optional[int], page: int, page_size: int
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size
        if hour is not None:
            Model = AdsHotspotDistrictHourly
            filters = [Model.stat_date == stat_date, Model.hour_slice == hour]
        else:
            Model = AdsHotspotDistrictDaily
            filters = [Model.stat_date == stat_date]

        total = self.session.execute(select(func.count(Model.zone_id)).where(*filters)).scalar_one()

        cx = func.ST_X(func.ST_Centroid(DwDimDistrict.geom)).label("center_lon")
        cy = func.ST_Y(func.ST_Centroid(DwDimDistrict.geom)).label("center_lat")

        rows = self.session.exec(
            select(
                Model.zone_id,
                Model.zone_name,
                Model.trip_count,
                Model.pickup_count,
                Model.dropoff_count,
                Model.vehicle_count,
                Model.avg_trip_distance,
                Model.avg_duration,
                cx,
                cy,
            )
            .outerjoin(DwDimDistrict, DwDimDistrict.district_code == Model.zone_id)
            .where(*filters)
            .order_by(Model.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        ).all()

        return total, [
            {
                "zone_id": r.zone_id,
                "zone_name": r.zone_name,
                "zone_type": "district",
                "center_lon": r.center_lon,
                "center_lat": r.center_lat,
                "trip_count": r.trip_count,
                "pickup_count": r.pickup_count,
                "dropoff_count": r.dropoff_count,
                "vehicle_count": r.vehicle_count,
                "avg_trip_distance": r.avg_trip_distance,
                "avg_duration": r.avg_duration,
            }
            for r in rows
        ]

    def _get_grid_zones(
        self, stat_date: date, hour: Optional[int], page: int, page_size: int
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size
        if hour is not None:
            Model = AdsHotspotGridHourly
            filters = [Model.stat_date == stat_date, Model.hour_slice == hour]
        else:
            Model = AdsHotspotGridDaily
            filters = [Model.stat_date == stat_date]

        total = self.session.execute(select(func.count(Model.zone_id)).where(*filters)).scalar_one()

        cx = func.ST_X(DwDimGrid.center_geom).label("center_lon")
        cy = func.ST_Y(DwDimGrid.center_geom).label("center_lat")

        rows = self.session.exec(
            select(
                Model.zone_id,
                Model.zone_name,
                Model.trip_count,
                Model.pickup_count,
                Model.dropoff_count,
                Model.vehicle_count,
                Model.avg_trip_distance,
                Model.avg_duration,
                cx,
                cy,
            )
            .outerjoin(DwDimGrid, DwDimGrid.grid_id == Model.zone_id)
            .where(*filters)
            .order_by(Model.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        ).all()

        return total, [
            {
                "zone_id": r.zone_id,
                "zone_name": r.zone_name,
                "zone_type": "grid",
                "center_lon": r.center_lon,
                "center_lat": r.center_lat,
                "trip_count": r.trip_count,
                "pickup_count": r.pickup_count,
                "dropoff_count": r.dropoff_count,
                "vehicle_count": r.vehicle_count,
                "avg_trip_distance": r.avg_trip_distance,
                "avg_duration": r.avg_duration,
            }
            for r in rows
        ]

    def _get_poi_zones(
        self, stat_date: date, hour: Optional[int], page: int, page_size: int
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size
        if hour is not None:
            Model = AdsHotspotPoiHourly
            filters = [Model.stat_date == stat_date, Model.hour_slice == hour]
        else:
            Model = AdsHotspotPoiDaily
            filters = [Model.stat_date == stat_date]

        total = self.session.execute(select(func.count(Model.zone_id)).where(*filters)).scalar_one()

        rows = self.session.exec(
            select(
                Model.zone_id,
                Model.zone_name,
                Model.trip_count,
                Model.pickup_count,
                Model.dropoff_count,
                Model.vehicle_count,
                Model.avg_trip_distance,
                Model.avg_duration,
                DwDimPoi.longitude.label("center_lon"),
                DwDimPoi.latitude.label("center_lat"),
            )
            .outerjoin(DwDimPoi, cast(DwDimPoi.poi_id, String) == Model.zone_id)
            .where(*filters)
            .order_by(Model.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        ).all()

        return total, [
            {
                "zone_id": r.zone_id,
                "zone_name": r.zone_name,
                "zone_type": "poi",
                "center_lon": r.center_lon,
                "center_lat": r.center_lat,
                "trip_count": r.trip_count,
                "pickup_count": r.pickup_count,
                "dropoff_count": r.dropoff_count,
                "vehicle_count": r.vehicle_count,
                "avg_trip_distance": r.avg_trip_distance,
                "avg_duration": r.avg_duration,
            }
            for r in rows
        ]

    def _get_cluster_zones(
        self, stat_date: date, hour: Optional[int], page: int, page_size: int
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size
        if hour is not None:
            Model = AdsHotspotClusterHourly
            filters = [Model.stat_date == stat_date, Model.hour_slice == hour]
        else:
            Model = AdsHotspotClusterDaily
            filters = [Model.stat_date == stat_date]

        total = self.session.execute(select(func.count(Model.cluster_id)).where(*filters)).scalar_one()

        # ADS 表中 cluster_type 当前固定写成 'od'，没有语义。
        # 用聚类中心点 ST_Within 行政区 geom，回填 "聚类 #N（XX区）" 这样的标签。
        district_name_sq = (
            select(DwDimDistrict.district_name)
            .where(
                func.ST_Within(
                    func.ST_SetSRID(
                        func.ST_Point(Model.center_lon, Model.center_lat), 4326
                    ),
                    DwDimDistrict.geom,
                )
            )
            .limit(1)
            .correlate(Model)
            .scalar_subquery()
        )

        rows = self.session.exec(
            select(
                Model.cluster_id,
                Model.cluster_type,
                Model.center_lon,
                Model.center_lat,
                Model.trip_count,
                Model.pickup_count,
                Model.dropoff_count,
                Model.avg_duration,
                district_name_sq.label("district_name"),
            )
            .where(*filters)
            .order_by(Model.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        ).all()

        return total, [
            {
                "zone_id": str(r.cluster_id),
                "zone_name": (
                    f"聚类 #{r.cluster_id}（{r.district_name}）"
                    if r.district_name
                    else f"聚类 #{r.cluster_id}"
                ),
                "zone_type": "cluster",
                "center_lon": r.center_lon,
                "center_lat": r.center_lat,
                "trip_count": r.trip_count,
                "pickup_count": r.pickup_count,
                "dropoff_count": r.dropoff_count,
                "vehicle_count": None,
                "avg_trip_distance": None,
                "avg_duration": r.avg_duration,
            }
            for r in rows
        ]
