from datetime import date, datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlmodel import Field, SQLModel


class AdsNetworkStatusHourly(SQLModel, table=True):
    """ADS 全网路况小时表"""

    __tablename__ = "ads_network_status_hourly"

    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
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
    updated_at: Optional[datetime] = None


class AdsCongestionHourly(SQLModel, table=True):
    """ADS 拥堵小时汇总表"""

    __tablename__ = "ads_congestion_hourly"

    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    light_congested_roads: int
    moderate_congested_roads: int
    severe_congested_roads: int
    avg_congestion: Optional[float] = None
    total_delay_min: Optional[float] = None
    updated_at: Optional[datetime] = None


class AdsTopCongestedRoadsHourly(SQLModel, table=True):
    """ADS 小时拥堵道路排行表"""

    __tablename__ = "ads_top_congested_roads_hourly"

    rank_id: int = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    road_id: int
    road_name: Optional[str] = None
    congestion_idx: Optional[float] = None
    avg_speed: Optional[float] = None
    trip_count: Optional[int] = None
    duration_loss: Optional[float] = None
    updated_at: Optional[datetime] = None


class AdsTripDistanceHourly(SQLModel, table=True):
    """ADS 出行距离小时表"""

    __tablename__ = "ads_trip_distance_hourly"

    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    short_trips: int
    medium_trips: int
    long_trips: int
    avg_distance: Optional[float] = None
    total_distance: Optional[float] = None
    sample_count: Optional[int] = None
    updated_at: Optional[datetime] = None


class AdsTripDistanceDaily(SQLModel, table=True):
    """ADS 出行距离日表"""

    __tablename__ = "ads_trip_distance_daily"

    stat_date: date = Field(primary_key=True)
    short_trips: int
    medium_trips: int
    long_trips: int
    avg_distance: Optional[float] = None
    total_distance: Optional[float] = None
    sample_count: Optional[int] = None
    updated_at: Optional[datetime] = None


class AdsTripSpeedHourly(SQLModel, table=True):
    """ADS 出行速度小时表"""

    __tablename__ = "ads_trip_speed_hourly"

    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    avg_speed: Optional[float] = None
    speed_p50: Optional[float] = None
    speed_p85: Optional[float] = None
    speed_p95: Optional[float] = None
    overspeed_ratio: Optional[float] = None
    sample_count: Optional[int] = None
    updated_at: Optional[datetime] = None


class AdsTripSpeedDaily(SQLModel, table=True):
    """ADS 出行速度日表"""

    __tablename__ = "ads_trip_speed_daily"

    stat_date: date = Field(primary_key=True)
    avg_speed: Optional[float] = None
    speed_p50: Optional[float] = None
    speed_p85: Optional[float] = None
    speed_p95: Optional[float] = None
    overspeed_ratio: Optional[float] = None
    sample_count: Optional[int] = None
    updated_at: Optional[datetime] = None


class AdsTripTimeslotDaily(SQLModel, table=True):
    """ADS 出行时段日表"""

    __tablename__ = "ads_trip_timeslot_daily"

    stat_date: date = Field(primary_key=True)
    morning_rush: int
    daytime: int
    evening_rush: int
    night: int
    weekday_trips: Optional[int] = None
    holiday_trips: Optional[int] = None
    sample_count: Optional[int] = None
    updated_at: Optional[datetime] = None


class AdsHotspotMonitorDaily(SQLModel, table=True):
    """ADS 热点监测日表"""

    __tablename__ = "ads_hotspot_monitor_daily"

    stat_date: date = Field(primary_key=True)
    zone_type: str = Field(primary_key=True)
    hotspot_count: int
    total_trip_count: int
    total_pickup_count: int
    total_dropoff_count: int
    max_hotspot_zone_id: Optional[str] = None
    max_hotspot_zone_name: Optional[str] = None
    max_hotspot_trip_count: Optional[int] = None
    updated_at: Optional[datetime] = None


class AdsHotspotMonitorHourly(SQLModel, table=True):
    """ADS 热点监测小时表"""

    __tablename__ = "ads_hotspot_monitor_hourly"

    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    zone_type: str = Field(primary_key=True)
    hotspot_count: int
    total_trip_count: int
    total_pickup_count: int
    total_dropoff_count: int
    max_hotspot_zone_id: Optional[str] = None
    max_hotspot_zone_name: Optional[str] = None
    max_hotspot_trip_count: Optional[int] = None
    updated_at: Optional[datetime] = None


class AdsRoadStatusHourly(SQLModel, table=True):
    """ADS 道路小时路况表"""

    __tablename__ = "ads_road_status_hourly"

    road_id: int = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    road_name: Optional[str] = None
    road_class: Optional[str] = None
    current_speed: Optional[float] = None
    current_flow: Optional[int] = None
    congestion_idx: Optional[float] = None
    status: Optional[str] = None
    geom: Optional[str] = Field(default=None, sa_type=Geometry("LineString", srid=4326))
    updated_at: Optional[datetime] = None


class AdsHotspotGridHourly(SQLModel, table=True):
    """ADS 网格热点小时表"""

    __tablename__ = "ads_hotspot_grid_hourly"

    zone_id: str = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    zone_name: Optional[str] = None
    zone_type: str = "grid"
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    vehicle_count: int
    updated_at: Optional[datetime] = None


class AdsHotspotGridDaily(SQLModel, table=True):
    """ADS 网格热点日表"""

    __tablename__ = "ads_hotspot_grid_daily"

    zone_id: str = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    zone_name: Optional[str] = None
    zone_type: str = "grid"
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    vehicle_count: int
    updated_at: Optional[datetime] = None


class AdsHotspotPoiHourly(SQLModel, table=True):
    """ADS POI热点小时表"""

    __tablename__ = "ads_hotspot_poi_hourly"

    zone_id: str = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    zone_name: Optional[str] = None
    zone_type: str = "poi"
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    vehicle_count: int
    updated_at: Optional[datetime] = None


class AdsHotspotPoiDaily(SQLModel, table=True):
    """ADS POI热点日表"""

    __tablename__ = "ads_hotspot_poi_daily"

    zone_id: str = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    zone_name: Optional[str] = None
    zone_type: str = "poi"
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    vehicle_count: int
    updated_at: Optional[datetime] = None


class AdsHotspotClusterHourly(SQLModel, table=True):
    """ADS 聚类热点小时表"""

    __tablename__ = "ads_hotspot_cluster_hourly"

    cluster_id: int = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    center_lon: Optional[float] = None
    center_lat: Optional[float] = None
    center_geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_duration: Optional[float] = None
    cluster_type: Optional[str] = None
    updated_at: Optional[datetime] = None


class AdsHotspotClusterDaily(SQLModel, table=True):
    """ADS 聚类热点日表"""

    __tablename__ = "ads_hotspot_cluster_daily"

    cluster_id: int = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    center_lon: Optional[float] = None
    center_lat: Optional[float] = None
    center_geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_duration: Optional[float] = None
    cluster_type: Optional[str] = None
    updated_at: Optional[datetime] = None


class AdsHotspotDistrictHourly(SQLModel, table=True):
    """ADS 行政区热点小时表"""

    __tablename__ = "ads_hotspot_district_hourly"

    zone_id: str = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    zone_name: Optional[str] = None
    zone_type: str = "district"
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    vehicle_count: int
    updated_at: Optional[datetime] = None


class AdsHotspotDistrictDaily(SQLModel, table=True):
    """ADS 行政区热点日表"""

    __tablename__ = "ads_hotspot_district_daily"

    zone_id: str = Field(primary_key=True)
    stat_date: date = Field(primary_key=True)
    zone_name: Optional[str] = None
    zone_type: str = "district"
    trip_count: int
    pickup_count: int
    dropoff_count: int
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    vehicle_count: int
    updated_at: Optional[datetime] = None