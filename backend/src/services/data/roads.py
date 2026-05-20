from datetime import date
from typing import Literal, Optional

from sqlalchemy import case, desc, func
from sqlmodel import Session, select

from models.dw import DwDimRoad, DwDimRoadClass, DwFactRoadFlowDaily, DwFactRoadFlowHourly, DwFactRoadTravelTime
from models.tdm import TdmTagDistrict


class RoadDataService:
    """Atomic road data queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_status(
        self,
        stat_date: date,
        hour: int,
        page: int = 1,
        page_size: int = 20,
        district_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size
        speed_base = func.coalesce(
            func.nullif(DwDimRoad.speed_limit, 0),
            DwDimRoadClass.default_speed,
        )
        congestion_index = self._congestion_index_expr(speed_base)
        status_expr = self._status_expr(speed_base)

        filters = [
            DwFactRoadFlowHourly.stat_date == stat_date,
            DwFactRoadFlowHourly.hour_slice == hour,
        ]
        if district_code is not None:
            filters.append(DwDimRoad.district_code == district_code)
        if status is not None:
            filters.append(status_expr == status)

        count_query = (
            select(func.count(DwFactRoadFlowHourly.fact_id))
            .join(DwDimRoad, DwDimRoad.road_id == DwFactRoadFlowHourly.road_id)
            .join(DwDimRoadClass, DwDimRoadClass.class_name == DwDimRoad.road_type, isouter=True)
            .where(*filters)
        )
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwDimRoad.road_id,
                DwDimRoad.road_name,
                DwDimRoad.road_type,
                DwDimRoadClass.road_level,
                DwDimRoad.speed_limit,
                DwDimRoad.length_m,
                DwDimRoad.district_code,
                TdmTagDistrict.district_name,
                DwFactRoadFlowHourly.stat_date,
                DwFactRoadFlowHourly.hour_slice.label("hour"),
                DwFactRoadFlowHourly.trip_count,
                DwFactRoadFlowHourly.vehicle_count,
                (DwFactRoadFlowHourly.total_distance / 1000.0).label("total_distance_km"),
                DwFactRoadFlowHourly.avg_speed,
                congestion_index.label("congestion_index"),
                status_expr.label("status"),
            )
            .join(DwDimRoad, DwDimRoad.road_id == DwFactRoadFlowHourly.road_id)
            .join(DwDimRoadClass, DwDimRoadClass.class_name == DwDimRoad.road_type, isouter=True)
            .join(
                TdmTagDistrict,
                TdmTagDistrict.district_code == DwDimRoad.district_code,
                isouter=True,
            )
            .where(*filters)
            .order_by(desc(congestion_index).nulls_last(), desc(DwFactRoadFlowHourly.trip_count))
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_road_flow_daily(
        self,
        stat_date: date,
        road_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [DwFactRoadFlowDaily.stat_date == stat_date]
        if road_id is not None:
            filters.append(DwFactRoadFlowDaily.road_id == road_id)

        count_query = select(func.count(DwFactRoadFlowDaily.fact_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwFactRoadFlowDaily.road_id,
                func.coalesce(DwDimRoad.road_name, "").label("road_name"),
                func.coalesce(DwDimRoad.road_type, "").label("road_type"),
                DwFactRoadFlowDaily.stat_date,
                DwFactRoadFlowDaily.trip_count,
                DwFactRoadFlowDaily.vehicle_count,
                (DwFactRoadFlowDaily.total_distance / 1000.0).label("total_distance_km"),
                DwFactRoadFlowDaily.avg_speed,
            )
            .join(DwDimRoad, DwDimRoad.road_id == DwFactRoadFlowDaily.road_id, isouter=True)
            .where(*filters)
            .order_by(DwFactRoadFlowDaily.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_road_travel_time(
        self,
        stat_date: date,
        road_id: Optional[int] = None,
        hour: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [DwFactRoadTravelTime.stat_date == stat_date]
        if road_id is not None:
            filters.append(DwFactRoadTravelTime.road_id == road_id)
        if hour is not None:
            filters.append(DwFactRoadTravelTime.hour_slice == hour)
        else:
            filters.append(DwFactRoadTravelTime.hour_slice.is_(None))

        count_query = select(func.count(DwFactRoadTravelTime.fact_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwFactRoadTravelTime.road_id,
                func.coalesce(DwDimRoad.road_name, "").label("road_name"),
                DwFactRoadTravelTime.stat_date,
                DwFactRoadTravelTime.hour_slice.label("hour"),
                DwFactRoadTravelTime.sample_count,
                DwFactRoadTravelTime.min_travel_time,
                DwFactRoadTravelTime.max_travel_time,
                DwFactRoadTravelTime.avg_travel_time,
                DwFactRoadTravelTime.p50_travel_time,
                DwFactRoadTravelTime.p90_travel_time,
                DwFactRoadTravelTime.p95_travel_time,
            )
            .join(DwDimRoad, DwDimRoad.road_id == DwFactRoadTravelTime.road_id, isouter=True)
            .where(*filters)
            .order_by(DwFactRoadTravelTime.sample_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    @staticmethod
    def _congestion_index_expr(speed_base):
        return case(
            (
                (DwFactRoadFlowHourly.avg_speed.is_(None)) | (DwFactRoadFlowHourly.avg_speed <= 0),
                None,
            ),
            else_=speed_base / DwFactRoadFlowHourly.avg_speed,
        )

    @staticmethod
    def _status_expr(speed_base):
        congestion_index = RoadDataService._congestion_index_expr(speed_base)
        return case(
            (
                (DwFactRoadFlowHourly.avg_speed.is_(None)) | (DwFactRoadFlowHourly.avg_speed <= 0),
                "未知",
            ),
            # GB/T 33171 5-level classification via CI = Vf/Vkj
            # SPI ≤ 30%  → CI > 1/0.3  = 3.333
            # SPI 30-40% → CI > 1/0.4  = 2.5
            # SPI 40-50% → CI > 1/0.5  = 2.0
            # SPI 50-70% → CI > 1/0.7  ≈ 1.429
            # SPI > 70%  → CI < 1.429
            (congestion_index > 10.0 / 3.0, "严重拥堵"),
            (congestion_index > 2.5,        "中度拥堵"),
            (congestion_index > 2.0,        "轻度拥堵"),
            (congestion_index > 10.0 / 7.0, "基本畅通"),
            else_="畅通",
        )