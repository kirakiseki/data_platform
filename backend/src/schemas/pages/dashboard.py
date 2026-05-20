from typing import Any, Optional

from pydantic import BaseModel


class PlatformStats(BaseModel):
    total_trips: int
    total_vehicles: int
    total_distance_km: Optional[float] = None
    road_segments: int
    total_pois: int = 0


class DayStats(BaseModel):
    trips: int
    vehicles: int
    distance_km: Optional[float] = None
    avg_speed: Optional[float] = None
    morning_rush_trips: Optional[int] = None
    evening_rush_trips: Optional[int] = None


class HourStats(BaseModel):
    trips: int
    vehicles: int
    avg_speed: Optional[float] = None


class NetworkTrendItem(BaseModel):
    hour: int
    avg_speed: Optional[float] = None
    smooth_pct: Optional[float] = None
    congested_pct: Optional[float] = None


class DistanceTrendItem(BaseModel):
    hour: int
    short_trips: int
    medium_trips: int
    long_trips: int


class TopRoadItem(BaseModel):
    rank: int
    road_id: int
    road_name: Optional[str] = None
    congestion_idx: Optional[float] = None
    avg_speed: Optional[float] = None
    status: Optional[str] = None


class TopHotspotItem(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    zone_type: str
    trip_count: int
    avg_trip_distance: Optional[float] = None


class DashboardPageResponse(BaseModel):
    platform_stats: PlatformStats
    day_stats: Optional[DayStats] = None
    hour_stats: Optional[HourStats] = None
    network_trend: list[NetworkTrendItem]
    distance_trend: list[DistanceTrendItem]
    top_roads: list[TopRoadItem]
    top_hotspots: list[TopHotspotItem]
