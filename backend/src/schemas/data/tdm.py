from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from schemas.data.common import PageResponse


class TdmRoadTagMetric(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    road_type: Optional[str] = None
    speed_limit: Optional[int] = None
    avg_daily_flow: Optional[int] = None
    avg_rush_flow: Optional[int] = None
    avg_night_flow: Optional[int] = None
    avg_daily_speed: Optional[float] = None
    tags_updated_at: Optional[datetime] = None


class TdmRoadTagListResponse(PageResponse):
    items: list[TdmRoadTagMetric]


class TdmNodeTagMetric(BaseModel):
    node_id: int
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    avg_in_flow: Optional[int] = None
    avg_out_flow: Optional[int] = None
    in_out_ratio: Optional[float] = None
    tags_updated_at: Optional[datetime] = None


class TdmNodeTagListResponse(PageResponse):
    items: list[TdmNodeTagMetric]


class TdmVehicleTagMetric(BaseModel):
    devid: str
    total_trips: int
    total_distance: Optional[float] = None
    total_duration: Optional[int] = None
    avg_daily_trips: Optional[float] = None
    avg_daily_distance: Optional[float] = None
    avg_daily_hours: Optional[float] = None
    avg_trip_distance: Optional[float] = None
    avg_trip_duration: Optional[float] = None
    rush_hour_trips: int
    rush_hour_ratio: Optional[float] = None
    night_trips: int
    night_ratio: Optional[float] = None
    short_trip_count: int
    medium_trip_count: int
    long_trip_count: int
    long_trip_ratio: Optional[float] = None
    tags_updated_at: Optional[datetime] = None


class TdmVehicleTagResponse(TdmVehicleTagMetric):
    main_hour_start: Optional[int] = None
    main_hour_end: Optional[int] = None


class TdmVehicleTagListResponse(PageResponse):
    items: list[TdmVehicleTagMetric]


class TdmTimeSlotMetric(BaseModel):
    slot_id: int
    slot_name: str
    slot_type: str
    start_hour: int
    end_hour: int
    weekdays: Optional[str] = None
    traffic_pattern: Optional[str] = None


class DistrictMetric(BaseModel):
    district_code: str
    district_name: str
    district_level: Optional[str] = None
    parent_code: Optional[str] = None