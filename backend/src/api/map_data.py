import logging

from fastapi import APIRouter, Depends

from api.response import ResponseBase
from db.session import get_session
from schemas.data.map_data import MapDataResponse, RoadFeature
from services.map_data import MapDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/data", response_model=ResponseBase[MapDataResponse])
def get_map_data(
    session=Depends(get_session),
):
    """获取bfmap_ways道路地图数据"""
    try:
        service = MapDataService(session)
        roads = service.get_roads()

        return ResponseBase(
            data=MapDataResponse(
                roads=[
                    RoadFeature(
                        gid=r["gid"],
                        osm_id=r["osm_id"],
                        class_id=r["class_id"],
                        length=r["length"],
                        maxspeed_forward=r["maxspeed_forward"],
                        maxspeed_backward=r["maxspeed_backward"],
                        priority=r["priority"],
                        geom_json=r["geom_json"],
                    )
                    for r in roads
                ]
            )
        )
    except Exception as e:
        logger.exception("获取地图数据失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
