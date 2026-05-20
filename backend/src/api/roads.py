import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.response import ResponseBase
from db.session import get_session
from schemas.data.roads import (
    BfmapWayGeoJSONResponse,
    BfmapWayListResponse,
    BfmapWayResponse,
)
from services.road import RoadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/roads", tags=["roads"])


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection"""

    type: str = "FeatureCollection"
    features: list[dict]
    next_cursor: Optional[int] = None


class RoadStatsResponse(BaseModel):
    """道路统计数据"""

    total_roads: int
    by_class: dict[str, int]


@router.get("/geojson/all", response_model=ResponseBase[GeoJSONFeatureCollection])
def get_all_roads_geojson(
    session=Depends(get_session),
):
    """获取所有道路的 GeoJSON FeatureCollection"""
    try:
        service = RoadService(session)
        roads = service.get_all_roads_geojson()

        features = [
            {
                "type": "Feature",
                "geometry": json.loads(road["geom_json"]) if isinstance(road["geom_json"], str) else road["geom_json"],
                "properties": {
                    "gid": road["gid"],
                    "osm_id": road["osm_id"],
                    "class_id": road["class_id"],
                    "length": road["length"],
                    "maxspeed_forward": road["maxspeed_forward"],
                    "maxspeed_backward": road["maxspeed_backward"],
                    "priority": road["priority"],
                },
            }
            for road in roads
        ]

        return ResponseBase(data=GeoJSONFeatureCollection(features=features))
    except Exception as e:
        logger.exception("获取所有道路 GeoJSON 失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/stats", response_model=ResponseBase[RoadStatsResponse])
def get_road_stats(
    session=Depends(get_session),
):
    """获取道路统计数据"""
    try:
        from sqlmodel import func, select

        from models.road import BfmapWay

        total = session.exec(select(func.count(BfmapWay.gid))).one()

        by_class_query = select(BfmapWay.class_id, func.count(BfmapWay.gid)).group_by(
            BfmapWay.class_id
        )
        class_counts = session.exec(by_class_query).all()

        by_class = {str(class_id): count for class_id, count in class_counts}

        return ResponseBase(
            data=RoadStatsResponse(
                total_roads=total,
                by_class=by_class,
            )
        )
    except Exception as e:
        logger.exception("获取道路统计失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("", response_model=ResponseBase[BfmapWayListResponse])
def list_roads(
    session=Depends(get_session),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    class_id: Optional[int] = Query(None, description="道路类别过滤"),
):
    """查询道路列表（分页）"""
    try:
        service = RoadService(session)
        total, items = service.list_roads(page, page_size, class_id)

        return ResponseBase(
            data=BfmapWayListResponse(
                total=total,
                items=[
                    BfmapWayResponse(
                        gid=item.gid,
                        osm_id=item.osm_id,
                        class_id=item.class_id,
                        source=item.source,
                        target=item.target,
                        length=item.length,
                        reverse=item.reverse,
                        priority=item.priority,
                        maxspeed_forward=item.maxspeed_forward,
                        maxspeed_backward=item.maxspeed_backward,
                    )
                    for item in items
                ],
            )
        )
    except Exception as e:
        logger.exception("查询道路列表失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/{gid}", response_model=ResponseBase[BfmapWayResponse])
def get_road(
    gid: int,
    session=Depends(get_session),
):
    """根据 gid 查询单条道路"""
    try:
        service = RoadService(session)
        road = service.get_road_by_gid(gid)

        if not road:
            return ResponseBase(code=404, message="道路不存在")

        return ResponseBase(
            data=BfmapWayResponse(
                gid=road.gid,
                osm_id=road.osm_id,
                class_id=road.class_id,
                source=road.source,
                target=road.target,
                length=road.length,
                reverse=road.reverse,
                priority=road.priority,
                maxspeed_forward=road.maxspeed_forward,
                maxspeed_backward=road.maxspeed_backward,
            )
        )
    except Exception as e:
        logger.exception("查询道路详情失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/geojson/{gid}", response_model=ResponseBase[BfmapWayGeoJSONResponse])
def get_road_geojson(
    gid: int,
    session=Depends(get_session),
):
    """根据 gid 查询道路的 GeoJSON 格式"""
    try:
        service = RoadService(session)
        result = service.get_road_geojson_by_gid(gid)

        if not result:
            return ResponseBase(code=404, message="道路不存在")

        return ResponseBase(
            data=BfmapWayGeoJSONResponse(
                type="Feature",
                geometry=json.loads(result["geom_json"]) if isinstance(result["geom_json"], str) else result["geom_json"],
                properties={
                    "gid": result["gid"],
                    "osm_id": result["osm_id"],
                    "class_id": result["class_id"],
                    "source": result["source"],
                    "target": result["target"],
                    "length": result["length"],
                    "reverse": result["reverse"],
                    "maxspeed_forward": result["maxspeed_forward"],
                    "maxspeed_backward": result["maxspeed_backward"],
                    "priority": result["priority"],
                },
            )
        )
    except Exception as e:
        logger.exception("查询道路 GeoJSON 失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/bbox/geojson", response_model=ResponseBase[GeoJSONFeatureCollection])
def get_roads_by_bbox_geojson(
    min_lng: float = Query(..., description="最小经度"),
    min_lat: float = Query(..., description="最小纬度"),
    max_lng: float = Query(..., description="最大经度"),
    max_lat: float = Query(..., description="最大纬度"),
    limit: int = Query(2000, ge=1, le=5000, description="单次返回最大路段数"),
    class_id: Optional[int] = Query(None, description="道路类别过滤"),
    cursor: Optional[int] = Query(None, description="keyset 分页游标 (上页最后一个 gid)"),
    simplify_tolerance: Optional[float] = Query(
        None, ge=0, le=0.05, description="几何简化容差（度），通常按 zoom 推导"
    ),
    session=Depends(get_session),
):
    """根据 bounding box 查询道路 GeoJSON，支持 keyset 分页和按 class 过滤"""
    try:
        service = RoadService(session)
        result = service.get_roads_by_bbox_geojson(
            min_lng,
            min_lat,
            max_lng,
            max_lat,
            limit,
            class_id,
            cursor,
            simplify_tolerance,
        )

        features = [
            {
                "type": "Feature",
                "geometry": json.loads(road["geom_json"]) if isinstance(road["geom_json"], str) else road["geom_json"],
                "properties": {
                    "gid": road["gid"],
                    "osm_id": road["osm_id"],
                    "class_id": road["class_id"],
                    "length": road["length"],
                    "maxspeed_forward": road["maxspeed_forward"],
                    "maxspeed_backward": road["maxspeed_backward"],
                    "priority": road["priority"],
                },
            }
            for road in result["items"]
        ]

        return ResponseBase(
            data=GeoJSONFeatureCollection(
                features=features, next_cursor=result["next_cursor"]
            )
        )
    except Exception as e:
        logger.exception("按 bbox 查询道路 GeoJSON 失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/bbox/", response_model=ResponseBase[BfmapWayListResponse])
def get_roads_by_bbox(
    min_lng: float = Query(..., description="最小经度"),
    min_lat: float = Query(..., description="最小纬度"),
    max_lng: float = Query(..., description="最大经度"),
    max_lat: float = Query(..., description="最大纬度"),
    session=Depends(get_session),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """根据 bounding box 查询道路"""
    try:
        service = RoadService(session)
        total, items = service.get_roads_by_bbox(
            min_lng, min_lat, max_lng, max_lat, page, page_size
        )

        return ResponseBase(
            data=BfmapWayListResponse(
                total=total,
                items=[
                    BfmapWayResponse(
                        gid=r.gid,
                        osm_id=r.osm_id,
                        class_id=r.class_id,
                        source=r.source,
                        target=r.target,
                        length=r.length,
                        reverse=r.reverse,
                        priority=r.priority,
                        maxspeed_forward=r.maxspeed_forward,
                        maxspeed_backward=r.maxspeed_backward,
                    )
                    for r in items
                ],
            )
        )
    except Exception as e:
        logger.exception("按 bbox 查询道路失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
