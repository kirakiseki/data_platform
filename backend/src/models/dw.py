from datetime import date, datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlmodel import Field, SQLModel


class DwDimTime(SQLModel, table=True):
    """时间维度表"""

    __tablename__ = "dw_dim_time"

    date_id: date = Field(primary_key=True)
    hour: int = Field(primary_key=True)
    year: int
    quarter: int
    month: int
    day: int
    day_of_week: int
    day_name: Optional[str] = None
    is_weekday: bool
    is_holiday: bool
    holiday_name: Optional[str] = None
    is_rush_hour: bool
    time_period: Optional[str] = None
    created_at: Optional[datetime] = None


class DwDimRoad(SQLModel, table=True):
    """道路维度表"""

    __tablename__ = "dw_dim_road"

    road_id: int = Field(primary_key=True)
    osm_id: int
    road_name: Optional[str] = None
    road_type: Optional[str] = None
    speed_limit: Optional[int] = None
    length_m: Optional[float] = None
    source_node_id: Optional[int] = None
    target_node_id: Optional[int] = None
    district_code: Optional[str] = None
    geom: Optional[str] = Field(default=None, sa_type=Geometry("LINESTRING", srid=4326))
    created_at: Optional[datetime] = None


class DwDimRoadClass(SQLModel, table=True):
    """道路等级维度表"""

    __tablename__ = "dw_dim_road_class"

    class_id: int = Field(primary_key=True)
    class_name: str
    road_level: str
    default_speed: int
    congestion_threshold_smooth: Optional[float] = None
    congestion_threshold_slow: Optional[float] = None
    congestion_threshold_congested: Optional[float] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class DwDimNode(SQLModel, table=True):
    """节点维度表"""

    __tablename__ = "dw_dim_node"

    node_id: int = Field(primary_key=True)
    osm_node_id: int
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district_code: Optional[str] = None
    geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    created_at: Optional[datetime] = None


class DwDimDistrict(SQLModel, table=True):
    """行政区维度表"""

    __tablename__ = "dw_dim_district"

    district_id: int = Field(primary_key=True)
    district_code: str = Field(index=True)
    district_name: str
    district_level: Optional[str] = None
    parent_code: Optional[str] = None
    geom: Optional[str] = Field(default=None, sa_type=Geometry("MultiPolygon", srid=4326))
    created_at: Optional[datetime] = None


class DwDimPoi(SQLModel, table=True):
    """POI维度表"""

    __tablename__ = "dw_dim_poi"

    poi_id: int = Field(primary_key=True)
    poi_name: str
    poi_type: str
    district_code: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    created_at: Optional[datetime] = None


class DwDimGrid(SQLModel, table=True):
    """网格维度表"""

    __tablename__ = "dw_dim_grid"

    grid_id: str = Field(primary_key=True)
    col: int
    row: int
    center_lon: Optional[float] = None
    center_lat: Optional[float] = None
    center_geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    created_at: Optional[datetime] = None


class DwFactNetworkHourly(SQLModel, table=True):
    """全网小时事实表"""

    __tablename__ = "dw_fact_network_hourly"

    stat_date: date = Field(primary_key=True)
    hour_slice: int = Field(primary_key=True)
    total_trips: int
    total_vehicles: int
    total_distance: Optional[float] = None
    network_avg_speed: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactNetworkDaily(SQLModel, table=True):
    """全网日事实表"""

    __tablename__ = "dw_fact_network_daily"

    stat_date: date = Field(primary_key=True)
    total_trips: int
    total_vehicles: int
    total_distance: Optional[float] = None
    network_avg_speed: Optional[float] = None
    network_avg_duration: Optional[float] = None
    morning_rush_trips: Optional[int] = None
    evening_rush_trips: Optional[int] = None
    night_trips: Optional[int] = None
    created_at: Optional[datetime] = None


class DwFactRoadFlowHourly(SQLModel, table=True):
    """道路小时流量事实表"""

    __tablename__ = "dw_fact_road_flow_hourly"

    fact_id: int = Field(primary_key=True)
    road_id: int
    stat_date: date
    hour_slice: int
    trip_count: int
    vehicle_count: int
    total_distance: Optional[float] = None
    avg_speed: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactRoadFlowDaily(SQLModel, table=True):
    """道路日流量事实表"""

    __tablename__ = "dw_fact_road_flow_daily"

    fact_id: int = Field(primary_key=True)
    road_id: int
    stat_date: date
    trip_count: int
    vehicle_count: int
    avg_speed: Optional[float] = None
    total_distance: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactRoadTravelTime(SQLModel, table=True):
    """路段通行时间事实表"""

    __tablename__ = "dw_fact_road_travel_time"

    fact_id: int = Field(primary_key=True)
    road_id: int
    stat_date: date
    hour_slice: Optional[int] = None
    sample_count: int
    min_travel_time: Optional[float] = None
    max_travel_time: Optional[float] = None
    avg_travel_time: Optional[float] = None
    p50_travel_time: Optional[float] = None
    p90_travel_time: Optional[float] = None
    p95_travel_time: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactNodeHourly(SQLModel, table=True):
    """节点小时事实表"""

    __tablename__ = "dw_fact_node_hourly"

    fact_id: int = Field(primary_key=True)
    node_id: int
    stat_date: date
    hour_slice: int
    in_vehicle_count: int
    out_vehicle_count: int
    avg_speed: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactNodeDaily(SQLModel, table=True):
    """节点日事实表"""

    __tablename__ = "dw_fact_node_daily"

    fact_id: int = Field(primary_key=True)
    node_id: int
    stat_date: date
    in_vehicle_count: int
    out_vehicle_count: int
    avg_speed: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactPoiHourly(SQLModel, table=True):
    """POI小时事实表"""

    __tablename__ = "dw_fact_poi_hourly"

    fact_id: int = Field(primary_key=True)
    poi_id: int
    stat_date: date
    hour_slice: int
    trip_count: int
    pickup_count: int
    dropoff_count: int
    created_at: Optional[datetime] = None


class DwFactPoiDaily(SQLModel, table=True):
    """POI日事实表"""

    __tablename__ = "dw_fact_poi_daily"

    fact_id: int = Field(primary_key=True)
    poi_id: int
    stat_date: date
    trip_count: int
    pickup_count: int
    dropoff_count: int
    created_at: Optional[datetime] = None


class DwFactTrip(SQLModel, table=True):
    """行程明细事实表"""

    __tablename__ = "dw_fact_trip"

    trip_id: int = Field(primary_key=True)
    devid: str = Field(index=True)
    trip_date: date = Field(index=True)
    trip_seq: Optional[int] = None
    start_lon: Optional[float] = None
    start_lat: Optional[float] = None
    end_lon: Optional[float] = None
    end_lat: Optional[float] = None
    start_node_id: Optional[int] = Field(default=None, index=True)
    end_node_id: Optional[int] = Field(default=None, index=True)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[int] = None
    route_length: Optional[int] = None
    total_distance: Optional[float] = None
    avg_speed: Optional[float] = None
    is_rush_hour: bool = False
    is_long_trip: bool = False
    route_line: Optional[str] = Field(default=None, sa_type=Geometry("LineString", srid=4326))
    created_at: Optional[datetime] = None


class DwFactGpsPoint(SQLModel, table=True):
    """GPS点明细事实表"""

    __tablename__ = "dw_fact_gps_point"

    id: int = Field(primary_key=True)
    trip_id: int = Field(index=True)
    point_seq: int
    lon: float
    lat: float
    tms: float = Field(index=True)
    speed_kmh: Optional[float] = None
    heading: Optional[float] = None
    acceleration: Optional[float] = None
    road_id: Optional[int] = Field(default=None, index=True)
    geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    created_at: Optional[datetime] = None


class DwFactOdGridHourly(SQLModel, table=True):
    """网格OD小时事实表"""

    __tablename__ = "dw_fact_od_grid_hourly"

    od_id: int = Field(primary_key=True)
    origin_grid_id: str = Field(index=True)
    dest_grid_id: str = Field(index=True)
    stat_date: date
    hour_slice: int
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactOdGridDaily(SQLModel, table=True):
    """网格OD日事实表"""

    __tablename__ = "dw_fact_od_grid_daily"

    od_id: int = Field(primary_key=True)
    origin_grid_id: str = Field(index=True)
    dest_grid_id: str = Field(index=True)
    stat_date: date
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    created_at: Optional[datetime] = None


class DwFactOdClusterHourly(SQLModel, table=True):
    """聚类OD小时事实表"""

    __tablename__ = "dw_fact_od_cluster_hourly"

    fact_id: int = Field(primary_key=True)
    stat_date: date
    hour_slice: int
    origin_center_lon: Optional[float] = None
    origin_center_lat: Optional[float] = None
    origin_geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    dest_center_lon: Optional[float] = None
    dest_center_lat: Optional[float] = None
    dest_geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    distance_type: Optional[str] = None
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    flow_direction: Optional[str] = None
    created_at: Optional[datetime] = None


class DwFactOdClusterDaily(SQLModel, table=True):
    """聚类OD日事实表"""

    __tablename__ = "dw_fact_od_cluster_daily"

    fact_id: int = Field(primary_key=True)
    stat_date: date
    origin_center_lon: Optional[float] = None
    origin_center_lat: Optional[float] = None
    origin_geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    dest_center_lon: Optional[float] = None
    dest_center_lat: Optional[float] = None
    dest_geom: Optional[str] = Field(default=None, sa_type=Geometry("Point", srid=4326))
    distance_type: Optional[str] = None
    trip_count: int
    vehicle_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    flow_direction: Optional[str] = None
    created_at: Optional[datetime] = None
