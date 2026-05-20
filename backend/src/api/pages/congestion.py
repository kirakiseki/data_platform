from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.data.roads import GeoJSONFeature
from services.pages.congestion import CongestionPageService

router = APIRouter(prefix="/page", tags=["page"])


class CongestionRoadsGeojsonResponse(BaseModel):
    """GeoJSON FeatureCollection with keyset pagination cursor."""

    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]
    next_cursor: Optional[int] = None


class CongestionRoadRankingItem(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    status: Optional[str] = None
    congestion_idx: Optional[float] = None
    avg_speed: Optional[float] = None
    trip_count: Optional[int] = None


class CongestionRoadRankingResponse(BaseModel):
    items: list[CongestionRoadRankingItem]


@router.get(
    "/congestion/roads/geojson",
    response_model=ResponseBase[CongestionRoadsGeojsonResponse],
)
def get_congestion_roads_geojson(
    stat_date: date = Query(
        ..., alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期"
    ),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    status: Optional[Literal["畅通", "基本畅通", "轻度拥堵", "中度拥堵", "严重拥堵"]] = Query(
        None, description="路况状态过滤（不填时仅返回三级拥堵及以上）"
    ),
    all_roads: bool = Query(False, description="是否返回所有有拥堵指数的道路（忽略status过滤）"),
    limit: int = Query(2000, ge=1, le=5000, description="单次返回最大路段数"),
    center_lng: Optional[float] = Query(None, description="视图中心经度（无 bbox 时按距离排序）"),
    center_lat: Optional[float] = Query(None, description="视图中心纬度（无 bbox 时按距离排序）"),
    min_lng: Optional[float] = Query(None, description="视图 bbox 最小经度"),
    min_lat: Optional[float] = Query(None, description="视图 bbox 最小纬度"),
    max_lng: Optional[float] = Query(None, description="视图 bbox 最大经度"),
    max_lat: Optional[float] = Query(None, description="视图 bbox 最大纬度"),
    cursor: Optional[int] = Query(None, description="keyset 分页游标 (上页最后一个 road_id)"),
    simplify_tolerance: Optional[float] = Query(
        None, ge=0, le=0.05, description="几何简化容差（度），通常由前端根据 zoom 推导"
    ),
    session=Depends(get_session),
):
    try:
        bbox = None
        if None not in (min_lng, min_lat, max_lng, max_lat):
            bbox = (min_lng, min_lat, max_lng, max_lat)
        svc = CongestionPageService(session)
        result = svc.get_roads_geojson(
            stat_date,
            hour,
            status,
            limit,
            all_roads,
            center_lng,
            center_lat,
            bbox,
            cursor,
            simplify_tolerance,
        )
        return ResponseBase(
            data=CongestionRoadsGeojsonResponse(
                features=[GeoJSONFeature(**f) for f in result["features"]],
                next_cursor=result["next_cursor"],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get(
    "/congestion/roads/ranking",
    response_model=ResponseBase[CongestionRoadRankingResponse],
)
def get_congestion_roads_ranking(
    stat_date: date = Query(
        ..., alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期"
    ),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    sort_by: Literal["congestion", "flow"] = Query(
        "congestion", description="排序口径：congestion=拥堵指数，flow=道路流量"
    ),
    limit: int = Query(20, ge=1, le=100, description="返回路段数"),
    session=Depends(get_session),
):
    try:
        svc = CongestionPageService(session)
        items = svc.get_roads_ranking(stat_date, hour, sort_by, limit)
        return ResponseBase(
            data=CongestionRoadRankingResponse(
                items=[CongestionRoadRankingItem(**item) for item in items]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
