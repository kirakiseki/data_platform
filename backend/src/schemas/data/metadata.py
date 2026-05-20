from datetime import date
from typing import Optional

from pydantic import BaseModel


class DateRangeResponse(BaseModel):
    """Available business date range."""

    start_date: date
    end_date: date
    available_dates: list[date]


class RoadClassResponse(BaseModel):
    """Road class metadata and congestion thresholds."""

    class_id: int
    class_name: str
    road_level: str
    default_speed: int
    congestion_threshold_smooth: Optional[float] = None
    congestion_threshold_slow: Optional[float] = None
    congestion_threshold_congested: Optional[float] = None
    description: Optional[str] = None
