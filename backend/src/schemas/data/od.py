from datetime import date
from typing import Optional

from pydantic import BaseModel

from schemas.data.common import PageResponse


class OdGridHourlyMetric(BaseModel):
    od_id: int
    origin_grid_id: str
    dest_grid_id: str
    stat_date: date
    hour: int
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class OdGridHourlyListResponse(PageResponse):
    items: list[OdGridHourlyMetric]


class OdGridDailyMetric(BaseModel):
    od_id: int
    origin_grid_id: str
    dest_grid_id: str
    stat_date: date
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class OdGridDailyListResponse(PageResponse):
    items: list[OdGridDailyMetric]


class OdClusterHourlyMetric(BaseModel):
    fact_id: int
    stat_date: date
    hour: int
    origin_center_lon: Optional[float] = None
    origin_center_lat: Optional[float] = None
    dest_center_lon: Optional[float] = None
    dest_center_lat: Optional[float] = None
    distance_type: Optional[str] = None
    flow_direction: Optional[str] = None
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class OdClusterHourlyListResponse(PageResponse):
    items: list[OdClusterHourlyMetric]


class OdClusterDailyMetric(BaseModel):
    fact_id: int
    stat_date: date
    origin_center_lon: Optional[float] = None
    origin_center_lat: Optional[float] = None
    dest_center_lon: Optional[float] = None
    dest_center_lat: Optional[float] = None
    distance_type: Optional[str] = None
    flow_direction: Optional[str] = None
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class OdClusterDailyListResponse(PageResponse):
    items: list[OdClusterDailyMetric]