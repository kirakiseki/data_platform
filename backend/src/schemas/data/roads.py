from datetime import date
from typing import Any, Optional

from pydantic import BaseModel

from schemas.data.common import PageResponse


class BfmapWayBase(BaseModel):
    osm_id: int
    class_id: int
    length: float
    priority: float
    maxspeed_forward: Optional[int] = None
    maxspeed_backward: Optional[int] = None


class BfmapWayResponse(BfmapWayBase):
    gid: int
    source: int
    target: int
    reverse: float

    class Config:
        from_attributes = True


class BfmapWayListResponse(BaseModel):
    total: int
    items: list[BfmapWayResponse]


class BfmapWayGeoJSONResponse(BaseModel):
    type: str = "Feature"
    geometry: Any
    properties: dict


class RoadStatusMetric(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    road_type: Optional[str] = None
    road_level: Optional[str] = None
    speed_limit: Optional[int] = None
    length_m: Optional[float] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    stat_date: date
    hour: int
    trip_count: int
    vehicle_count: int
    total_distance_km: Optional[float] = None
    avg_speed: Optional[float] = None
    congestion_index: Optional[float] = None
    status: str


class RoadStatusListResponse(PageResponse):
    items: list[RoadStatusMetric]


class RoadFlowDailyMetric(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    road_type: Optional[str] = None
    stat_date: date
    trip_count: int
    vehicle_count: int
    total_distance_km: Optional[float] = None
    avg_speed: Optional[float] = None


class RoadFlowDailyListResponse(PageResponse):
    items: list[RoadFlowDailyMetric]


class RoadTravelTimeMetric(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    stat_date: date
    hour: Optional[int] = None
    sample_count: int
    min_travel_time: Optional[float] = None
    max_travel_time: Optional[float] = None
    avg_travel_time: Optional[float] = None
    p50_travel_time: Optional[float] = None
    p90_travel_time: Optional[float] = None
    p95_travel_time: Optional[float] = None


class RoadTravelTimeListResponse(PageResponse):
    items: list[RoadTravelTimeMetric]


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]


class RoadGeoJSONResponse(BaseModel):
    total: int
    features: list[GeoJSONFeature]


class NodeMetric(BaseModel):
    node_id: int
    osm_node_id: int
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district_code: Optional[str] = None


class NodeDetailMetric(NodeMetric):
    avg_in_flow: Optional[int] = None
    avg_out_flow: Optional[int] = None
    in_out_ratio: Optional[float] = None


class NodeListResponse(PageResponse):
    items: list[NodeMetric]


class NodeDetailResponse(BaseModel):
    data: NodeDetailMetric