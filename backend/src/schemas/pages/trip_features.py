from typing import Optional

from pydantic import BaseModel


class TripOdItem(BaseModel):
    rank: int
    origin_name: Optional[str] = None
    origin_lon: Optional[float] = None
    origin_lat: Optional[float] = None
    dest_name: Optional[str] = None
    dest_lon: Optional[float] = None
    dest_lat: Optional[float] = None
    trip_count: int
    avg_distance: Optional[float] = None
    avg_duration: Optional[float] = None
    flow_direction: Optional[str] = None


class TripOdPageResponse(BaseModel):
    items: list[TripOdItem]
