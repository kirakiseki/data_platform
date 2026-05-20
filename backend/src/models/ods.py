from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class OdsTrip(SQLModel, table=True):
    """ODS 行程主表"""

    __tablename__ = "ods_trips"

    trip_id: int = Field(primary_key=True)
    devid: str = Field(index=True)
    trip_date: date = Field(index=True)
    trip_seq: Optional[int] = None
    start_lon: Optional[float] = None
    start_lat: Optional[float] = None
    end_lon: Optional[float] = None
    end_lat: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[int] = None
    n_points: Optional[int] = None
    n_roads: Optional[int] = None
