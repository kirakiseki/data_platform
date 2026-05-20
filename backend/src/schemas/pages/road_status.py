from typing import Optional

from pydantic import BaseModel


class RoadStatusPageSummary(BaseModel):
    total_roads: int
    congested_roads: int
    severe_congested_roads: int
    avg_speed: Optional[float] = None
    congestion_pct: Optional[float] = None


class RoadStatusPageItem(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    road_class: Optional[str] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    current_speed: Optional[float] = None
    current_flow: Optional[int] = None
    congestion_idx: Optional[float] = None
    status: Optional[str] = None


class RoadStatusPageResponse(BaseModel):
    summary: RoadStatusPageSummary
    total: int
    page: int
    page_size: int
    items: list[RoadStatusPageItem]
