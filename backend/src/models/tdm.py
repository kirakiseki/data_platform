from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class TdmTagDistrict(SQLModel, table=True):
    """行政区标签表"""

    __tablename__ = "tdm_tag_district"

    district_code: str = Field(primary_key=True)
    district_name: str
    district_level: Optional[str] = None
    tags_updated_at: Optional[datetime] = None


class TdmTagRoad(SQLModel, table=True):
    """道路画像标签表"""

    __tablename__ = "tdm_tag_road"

    road_id: int = Field(primary_key=True)
    road_name: Optional[str] = None
    road_type: Optional[str] = None
    speed_limit: Optional[int] = None
    avg_daily_flow: Optional[int] = None
    avg_rush_flow: Optional[int] = None
    avg_night_flow: Optional[int] = None
    avg_daily_speed: Optional[float] = None
    tags_updated_at: Optional[datetime] = None


class TdmTagNode(SQLModel, table=True):
    """节点画像标签表"""

    __tablename__ = "tdm_tag_node"

    node_id: int = Field(primary_key=True)
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    avg_in_flow: Optional[int] = None
    avg_out_flow: Optional[int] = None
    in_out_ratio: Optional[float] = None
    tags_updated_at: Optional[datetime] = None


class TdmTagTimeSlot(SQLModel, table=True):
    """时段标签表"""

    __tablename__ = "tdm_tag_time_slot"

    slot_id: int = Field(primary_key=True)
    slot_name: str
    slot_type: str
    start_hour: int
    end_hour: int
    weekdays: Optional[str] = None
    traffic_pattern: Optional[str] = None
    created_at: Optional[datetime] = None


class TdmTagVehicle(SQLModel, table=True):
    """车辆运营画像标签表"""

    __tablename__ = "tdm_tag_vehicle"

    devid: str = Field(primary_key=True)
    total_trips: int = 0
    total_distance: float = 0
    total_duration: int = 0
    avg_daily_trips: Optional[float] = None
    avg_daily_distance: Optional[float] = None
    avg_daily_hours: Optional[float] = None
    avg_trip_distance: Optional[float] = None
    avg_trip_duration: Optional[float] = None
    rush_hour_trips: int = 0
    rush_hour_ratio: Optional[float] = None
    night_trips: int = 0
    night_ratio: Optional[float] = None
    short_trip_count: int = 0
    medium_trip_count: int = 0
    long_trip_count: int = 0
    long_trip_ratio: Optional[float] = None
    main_hour_start: Optional[int] = None
    main_hour_end: Optional[int] = None
    tags_updated_at: Optional[datetime] = None