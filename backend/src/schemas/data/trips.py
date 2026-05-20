from datetime import date
from typing import Any, Optional

from pydantic import BaseModel

from schemas.data.common import PageResponse


class TripMetric(BaseModel):
    trip_id: int
    devid: str
    trip_date: date
    trip_seq: Optional[int] = None
    start_lon: Optional[float] = None
    start_lat: Optional[float] = None
    end_lon: Optional[float] = None
    end_lat: Optional[float] = None
    start_node_id: Optional[int] = None
    end_node_id: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[int] = None
    route_length: Optional[int] = None
    total_distance_m: Optional[float] = None
    avg_speed: Optional[float] = None
    is_rush_hour: bool
    is_long_trip: bool


class TripDetailMetric(TripMetric):
    route_line: Optional[dict[str, Any]] = None


class TripListResponse(PageResponse):
    items: list[TripMetric]


class TripDetailResponse(BaseModel):
    data: TripDetailMetric


class GpsPointMetric(BaseModel):
    id: int
    point_seq: int
    lon: float
    lat: float
    tms: float
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    acceleration: Optional[float] = None
    road_id: Optional[int] = None


class GpsPointListResponse(BaseModel):
    trip_id: int
    items: list[GpsPointMetric]