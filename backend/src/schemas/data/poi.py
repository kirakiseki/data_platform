from datetime import date
from typing import Optional

from pydantic import BaseModel

from schemas.data.common import PageResponse


class PoiFlowHourlyMetric(BaseModel):
    poi_id: int
    stat_date: date
    hour: int
    trip_count: int
    pickup_count: int
    dropoff_count: int


class PoiFlowHourlyListResponse(PageResponse):
    items: list[PoiFlowHourlyMetric]


class PoiFlowDailyMetric(BaseModel):
    poi_id: int
    stat_date: date
    trip_count: int
    pickup_count: int
    dropoff_count: int


class PoiFlowDailyListResponse(PageResponse):
    items: list[PoiFlowDailyMetric]