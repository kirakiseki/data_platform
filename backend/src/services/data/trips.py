import json
from datetime import date
from typing import Any, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models.dw import DwFactGpsPoint, DwFactTrip


class TripDataService:
    """Atomic trip data queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_trips(
        self,
        stat_date: Optional[date] = None,
        devid: Optional[str] = None,
        is_rush_hour: Optional[bool] = None,
        is_long_trip: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = []
        if stat_date is not None:
            filters.append(DwFactTrip.trip_date == stat_date)
        if devid is not None:
            filters.append(DwFactTrip.devid == devid)
        if is_rush_hour is not None:
            filters.append(DwFactTrip.is_rush_hour == is_rush_hour)
        if is_long_trip is not None:
            filters.append(DwFactTrip.is_long_trip == is_long_trip)

        count_query = select(func.count(DwFactTrip.trip_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwFactTrip.trip_id,
                DwFactTrip.devid,
                DwFactTrip.trip_date,
                DwFactTrip.trip_seq,
                DwFactTrip.start_lon,
                DwFactTrip.start_lat,
                DwFactTrip.end_lon,
                DwFactTrip.end_lat,
                DwFactTrip.start_node_id,
                DwFactTrip.end_node_id,
                DwFactTrip.start_time,
                DwFactTrip.end_time,
                DwFactTrip.duration,
                DwFactTrip.route_length,
                DwFactTrip.total_distance.label("total_distance_m"),
                DwFactTrip.avg_speed,
                DwFactTrip.is_rush_hour,
                DwFactTrip.is_long_trip,
            )
            .where(*filters)
            .order_by(DwFactTrip.trip_date, DwFactTrip.trip_id)
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def get_trip(self, trip_id: int) -> Optional[dict[str, Any]]:
        row = self.session.exec(
            select(DwFactTrip).where(DwFactTrip.trip_id == trip_id)
        ).first()
        if not row:
            return None

        result = {
            "trip_id": row.trip_id,
            "devid": row.devid,
            "trip_date": row.trip_date,
            "trip_seq": row.trip_seq,
            "start_lon": row.start_lon,
            "start_lat": row.start_lat,
            "end_lon": row.end_lon,
            "end_lat": row.end_lat,
            "start_node_id": row.start_node_id,
            "end_node_id": row.end_node_id,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "duration": row.duration,
            "route_length": row.route_length,
            "total_distance_m": row.total_distance,
            "avg_speed": row.avg_speed,
            "is_rush_hour": row.is_rush_hour,
            "is_long_trip": row.is_long_trip,
        }

        if row.route_line is not None:
            geom_str = self.session.execute(
                select(func.ST_AsGeoJSON(DwFactTrip.route_line))
                .where(DwFactTrip.trip_id == trip_id)
            ).scalar_one_or_none()
            try:
                result["route_line"] = json.loads(geom_str) if geom_str else None
            except (ValueError, TypeError):
                result["route_line"] = None
        else:
            result["route_line"] = None

        return result

    def list_gps_points(self, trip_id: int) -> list[dict]:
        rows = self.session.exec(
            select(DwFactGpsPoint)
            .where(DwFactGpsPoint.trip_id == trip_id)
            .order_by(DwFactGpsPoint.point_seq)
        ).all()
        return [
            {
                "id": row.id,
                "point_seq": row.point_seq,
                "lon": row.lon,
                "lat": row.lat,
                "tms": row.tms,
                "speed_kmh": row.speed_kmh,
                "heading": row.heading,
                "acceleration": row.acceleration,
                "road_id": row.road_id,
            }
            for row in rows
        ]