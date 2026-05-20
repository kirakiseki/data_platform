from typing import Optional

from pydantic import BaseModel


class HotspotZoneItem(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    zone_type: str
    center_lon: Optional[float] = None
    center_lat: Optional[float] = None
    trip_count: int
    pickup_count: int
    dropoff_count: int
    vehicle_count: Optional[int] = None
    avg_trip_distance: Optional[float] = None
    avg_duration: Optional[float] = None


class HotspotZoneListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[HotspotZoneItem]
