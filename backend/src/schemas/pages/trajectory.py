from datetime import date
from typing import Any, Optional

from pydantic import BaseModel


class TrajectoryDailyStatsItem(BaseModel):
    stat_date: date
    trips: int
    total_vehicles: int
    total_gps_points: Optional[int] = None
    total_matched_roads: Optional[int] = None
    avg_speed: Optional[float] = None


class TrajectoryDailyStatsResponse(BaseModel):
    items: list[TrajectoryDailyStatsItem]


class TrajectorySampleItem(BaseModel):
    trip_id: int
    devid: str
    trip_date: date
    start_hour: Optional[int] = None
    total_distance_m: Optional[float] = None
    duration_s: Optional[int] = None
    route_line: Optional[dict[str, Any]] = None
    route_source: Optional[str] = None


class TrajectorySampleListResponse(BaseModel):
    items: list[TrajectorySampleItem]
