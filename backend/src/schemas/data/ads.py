from datetime import date
from typing import Any, Optional

from pydantic import BaseModel

from schemas.data.common import PageResponse


class AdsNetworkStatusHourlyMetric(BaseModel):
    stat_date: date
    hour: int
    total_roads: int
    smooth_roads: int
    basically_smooth_roads: int
    light_congested_roads: int
    moderate_congested_roads: int
    severe_congested_roads: int
    smooth_pct: float
    basically_smooth_pct: float
    light_congested_pct: float
    moderate_congested_pct: float
    severe_congested_pct: float
    network_avg_speed: Optional[float] = None


class AdsCongestionHourlyMetric(BaseModel):
    stat_date: date
    hour: int
    light_congested_roads: int
    moderate_congested_roads: int
    severe_congested_roads: int
    avg_congestion: Optional[float] = None
    total_delay_min: Optional[float] = None


class AdsTopCongestedRoadMetric(BaseModel):
    rank_id: int
    stat_date: date
    hour: int
    road_id: int
    road_name: Optional[str] = None
    congestion_idx: Optional[float] = None
    avg_speed: Optional[float] = None
    trip_count: Optional[int] = None
    duration_loss: Optional[float] = None


class AdsTripDistanceHourlyMetric(BaseModel):
    stat_date: date
    hour: int
    short_trips: int
    medium_trips: int
    long_trips: int
    avg_distance: Optional[float] = None
    total_distance: Optional[float] = None
    sample_count: Optional[int] = None


class AdsTripDistanceDailyMetric(BaseModel):
    stat_date: date
    short_trips: int
    medium_trips: int
    long_trips: int
    avg_distance: Optional[float] = None
    total_distance: Optional[float] = None
    sample_count: Optional[int] = None


class AdsTripSpeedHourlyMetric(BaseModel):
    stat_date: date
    hour: int
    avg_speed: Optional[float] = None
    speed_p50: Optional[float] = None
    speed_p85: Optional[float] = None
    speed_p95: Optional[float] = None
    overspeed_ratio: Optional[float] = None
    sample_count: Optional[int] = None


class AdsTripSpeedDailyMetric(BaseModel):
    stat_date: date
    avg_speed: Optional[float] = None
    speed_p50: Optional[float] = None
    speed_p85: Optional[float] = None
    speed_p95: Optional[float] = None
    sample_count: Optional[int] = None


class AdsTripTimeslotDailyMetric(BaseModel):
    stat_date: date
    morning_rush: int
    daytime: int
    evening_rush: int
    night: int
    weekday_trips: Optional[int] = None
    holiday_trips: Optional[int] = None
    sample_count: Optional[int] = None


class AdsHotspotMonitorDailyMetric(BaseModel):
    stat_date: date
    zone_type: str
    hotspot_count: int
    total_trip_count: int
    total_pickup_count: int
    total_dropoff_count: int
    max_hotspot_zone_id: Optional[str] = None
    max_hotspot_zone_name: Optional[str] = None
    max_hotspot_trip_count: Optional[int] = None


class AdsRoadStatusHourlyMetric(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    road_class: Optional[str] = None
    stat_date: date
    hour: int
    current_speed: Optional[float] = None
    current_flow: Optional[int] = None
    congestion_idx: Optional[float] = None
    status: Optional[str] = None


class AdsRoadStatusHourlyListResponse(PageResponse):
    items: list[AdsRoadStatusHourlyMetric]


class AdsHotspotDistrictHourlyMetric(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    stat_date: date
    hour: int
    trip_count: int
    pickup_count: int
    dropoff_count: int
    vehicle_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class AdsHotspotDistrictDailyMetric(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    stat_date: date
    trip_count: int
    pickup_count: int
    dropoff_count: int
    vehicle_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class AdsHotspotGridHourlyMetric(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    stat_date: date
    hour: int
    trip_count: int
    pickup_count: int
    dropoff_count: int
    vehicle_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class AdsHotspotGridHourlyListResponse(PageResponse):
    items: list[AdsHotspotGridHourlyMetric]


class AdsHotspotGridDailyMetric(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    stat_date: date
    trip_count: int
    pickup_count: int
    dropoff_count: int
    vehicle_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class AdsHotspotGridDailyListResponse(PageResponse):
    items: list[AdsHotspotGridDailyMetric]


class AdsHotspotClusterHourlyMetric(BaseModel):
    cluster_id: int
    stat_date: date
    hour: int
    center_lon: Optional[float] = None
    center_lat: Optional[float] = None
    cluster_type: Optional[str] = None
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_duration: Optional[float] = None


class AdsHotspotClusterHourlyListResponse(PageResponse):
    items: list[AdsHotspotClusterHourlyMetric]


class AdsHotspotClusterDailyMetric(BaseModel):
    cluster_id: int
    stat_date: date
    center_lon: Optional[float] = None
    center_lat: Optional[float] = None
    cluster_type: Optional[str] = None
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_duration: Optional[float] = None


class AdsHotspotClusterDailyListResponse(PageResponse):
    items: list[AdsHotspotClusterDailyMetric]


class AdsHotspotPoiHourlyMetric(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    stat_date: date
    hour: int
    trip_count: int
    pickup_count: int
    dropoff_count: int
    vehicle_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class AdsHotspotPoiHourlyListResponse(PageResponse):
    items: list[AdsHotspotPoiHourlyMetric]


class AdsHotspotPoiDailyMetric(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    stat_date: date
    trip_count: int
    pickup_count: int
    dropoff_count: int
    vehicle_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class AdsHotspotPoiDailyListResponse(PageResponse):
    items: list[AdsHotspotPoiDailyMetric]


class AdsNetworkStatusHourlyResponse(BaseModel):
    items: list[AdsNetworkStatusHourlyMetric]


class AdsCongestionHourlyResponse(BaseModel):
    items: list[AdsCongestionHourlyMetric]


class AdsTopCongestedRoadsResponse(BaseModel):
    items: list[AdsTopCongestedRoadMetric]


class AdsTripDistanceHourlyResponse(BaseModel):
    items: list[AdsTripDistanceHourlyMetric]


class AdsTripDistanceDailyResponse(BaseModel):
    items: list[AdsTripDistanceDailyMetric]


class AdsTripSpeedHourlyResponse(BaseModel):
    items: list[AdsTripSpeedHourlyMetric]


class AdsTripSpeedDailyResponse(BaseModel):
    items: list[AdsTripSpeedDailyMetric]


class AdsTripTimeslotDailyResponse(BaseModel):
    items: list[AdsTripTimeslotDailyMetric]


class AdsHotspotMonitorDailyResponse(BaseModel):
    items: list[AdsHotspotMonitorDailyMetric]


class AdsHotspotDistrictHourlyResponse(BaseModel):
    items: list[AdsHotspotDistrictHourlyMetric]


class AdsHotspotDistrictDailyResponse(BaseModel):
    items: list[AdsHotspotDistrictDailyMetric]