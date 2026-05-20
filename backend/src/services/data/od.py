from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models.dw import (
    DwFactOdClusterDaily,
    DwFactOdClusterHourly,
    DwFactOdGridDaily,
    DwFactOdGridHourly,
)


class OdDataService:
    """Atomic OD matrix queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_grid_hourly(
        self,
        stat_date: date,
        hour: int,
        origin_grid_id: Optional[str] = None,
        dest_grid_id: Optional[str] = None,
        min_trip_count: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [
            DwFactOdGridHourly.stat_date == stat_date,
            DwFactOdGridHourly.hour_slice == hour,
        ]
        if origin_grid_id is not None:
            filters.append(DwFactOdGridHourly.origin_grid_id == origin_grid_id)
        if dest_grid_id is not None:
            filters.append(DwFactOdGridHourly.dest_grid_id == dest_grid_id)
        if min_trip_count is not None:
            filters.append(DwFactOdGridHourly.trip_count >= min_trip_count)

        count_query = select(func.count(DwFactOdGridHourly.od_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwFactOdGridHourly.od_id,
                DwFactOdGridHourly.origin_grid_id,
                DwFactOdGridHourly.dest_grid_id,
                DwFactOdGridHourly.stat_date,
                DwFactOdGridHourly.hour_slice.label("hour"),
                DwFactOdGridHourly.trip_count,
                DwFactOdGridHourly.vehicle_count,
                DwFactOdGridHourly.avg_distance,
                DwFactOdGridHourly.avg_duration,
            )
            .where(*filters)
            .order_by(DwFactOdGridHourly.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_grid_daily(
        self,
        stat_date: date,
        origin_grid_id: Optional[str] = None,
        dest_grid_id: Optional[str] = None,
        min_trip_count: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [DwFactOdGridDaily.stat_date == stat_date]
        if origin_grid_id is not None:
            filters.append(DwFactOdGridDaily.origin_grid_id == origin_grid_id)
        if dest_grid_id is not None:
            filters.append(DwFactOdGridDaily.dest_grid_id == dest_grid_id)
        if min_trip_count is not None:
            filters.append(DwFactOdGridDaily.trip_count >= min_trip_count)

        count_query = select(func.count(DwFactOdGridDaily.od_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwFactOdGridDaily.od_id,
                DwFactOdGridDaily.origin_grid_id,
                DwFactOdGridDaily.dest_grid_id,
                DwFactOdGridDaily.stat_date,
                DwFactOdGridDaily.trip_count,
                DwFactOdGridDaily.vehicle_count,
                DwFactOdGridDaily.avg_distance,
                DwFactOdGridDaily.avg_duration,
            )
            .where(*filters)
            .order_by(DwFactOdGridDaily.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_cluster_hourly(
        self,
        stat_date: date,
        hour: int,
        flow_direction: Optional[str] = None,
        distance_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [
            DwFactOdClusterHourly.stat_date == stat_date,
            DwFactOdClusterHourly.hour_slice == hour,
        ]
        if flow_direction is not None:
            filters.append(DwFactOdClusterHourly.flow_direction == flow_direction)
        if distance_type is not None:
            filters.append(DwFactOdClusterHourly.distance_type == distance_type)

        count_query = select(func.count(DwFactOdClusterHourly.fact_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwFactOdClusterHourly.fact_id,
                DwFactOdClusterHourly.stat_date,
                DwFactOdClusterHourly.hour_slice.label("hour"),
                DwFactOdClusterHourly.origin_center_lon,
                DwFactOdClusterHourly.origin_center_lat,
                DwFactOdClusterHourly.dest_center_lon,
                DwFactOdClusterHourly.dest_center_lat,
                DwFactOdClusterHourly.distance_type,
                DwFactOdClusterHourly.flow_direction,
                DwFactOdClusterHourly.trip_count,
                DwFactOdClusterHourly.vehicle_count,
                DwFactOdClusterHourly.avg_distance,
                DwFactOdClusterHourly.avg_duration,
            )
            .where(*filters)
            .order_by(DwFactOdClusterHourly.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_cluster_daily(
        self,
        stat_date: date,
        flow_direction: Optional[str] = None,
        distance_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [DwFactOdClusterDaily.stat_date == stat_date]
        if flow_direction is not None:
            filters.append(DwFactOdClusterDaily.flow_direction == flow_direction)
        if distance_type is not None:
            filters.append(DwFactOdClusterDaily.distance_type == distance_type)

        count_query = select(func.count(DwFactOdClusterDaily.fact_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwFactOdClusterDaily.fact_id,
                DwFactOdClusterDaily.stat_date,
                DwFactOdClusterDaily.origin_center_lon,
                DwFactOdClusterDaily.origin_center_lat,
                DwFactOdClusterDaily.dest_center_lon,
                DwFactOdClusterDaily.dest_center_lat,
                DwFactOdClusterDaily.distance_type,
                DwFactOdClusterDaily.flow_direction,
                DwFactOdClusterDaily.trip_count,
                DwFactOdClusterDaily.vehicle_count,
                DwFactOdClusterDaily.avg_distance,
                DwFactOdClusterDaily.avg_duration,
            )
            .where(*filters)
            .order_by(DwFactOdClusterDaily.trip_count.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]