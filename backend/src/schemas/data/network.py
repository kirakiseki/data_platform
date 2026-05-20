from datetime import date
from typing import Optional

from pydantic import BaseModel


class NetworkMetric(BaseModel):
    """Network metric for a specific time grain."""

    stat_date: Optional[date] = None
    hour: Optional[int] = None
    grain: str
    total_trips: int
    total_vehicles: int
    total_distance_km: Optional[float] = None
    network_avg_speed: Optional[float] = None
    network_avg_duration: Optional[float] = None
    morning_rush_trips: Optional[int] = None
    evening_rush_trips: Optional[int] = None
    night_trips: Optional[int] = None


class NetworkHourlyResponse(BaseModel):
    """Hourly network metrics for one date."""

    date: date
    items: list[NetworkMetric]


class NetworkDailyResponse(BaseModel):
    """Daily network metrics."""

    items: list[NetworkMetric]
