from typing import Optional

from pydantic import BaseModel


class RoadFeature(BaseModel):
    """道路GeoJSON特征模型"""

    gid: int
    osm_id: int
    class_id: int
    length: float
    maxspeed_forward: Optional[int] = None
    maxspeed_backward: Optional[int] = None
    priority: float
    geom_json: dict


class MapDataResponse(BaseModel):
    """地图数据响应"""

    roads: list[RoadFeature]
