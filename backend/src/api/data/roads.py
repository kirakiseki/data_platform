import json
import logging
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.data.roads import (
    RoadFlowDailyListResponse,
    RoadFlowDailyMetric,
    RoadGeoJSONResponse,
    RoadStatusListResponse,
    RoadStatusMetric,
    RoadTravelTimeListResponse,
    RoadTravelTimeMetric,
)
from services.data.roads import RoadDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/roads", tags=["data-roads"])


@router.get("/status", response_model=ResponseBase[RoadStatusListResponse])
def list_road_status(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    district_code: Optional[str] = Query(None, description="行政区代码"),
    status: Optional[Literal["畅通", "基本畅通", "轻度拥堵", "中度拥堵", "严重拥堵", "未知"]] = Query(
        None,
        description="路况状态",
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    """List road status metrics for one date-hour slice."""
    try:
        service = RoadDataService(session)
        from schemas.data.roads import RoadStatusListResponse, RoadStatusMetric
        total, items = service.list_status(
            stat_date=stat_date,
            hour=hour,
            page=page,
            page_size=page_size,
            district_code=district_code,
            status=status,
        )
        return ResponseBase(
            data=RoadStatusListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[RoadStatusMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询道路状态指标失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/flow/daily", response_model=ResponseBase[RoadFlowDailyListResponse])
def list_road_flow_daily(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    road_id: Optional[int] = Query(None, description="道路 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    """List daily road flow metrics."""
    try:
        service = RoadDataService(session)
        total, items = service.list_road_flow_daily(
            stat_date=stat_date,
            road_id=road_id,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=RoadFlowDailyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[RoadFlowDailyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询道路日流量失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/travel-time", response_model=ResponseBase[RoadTravelTimeListResponse])
def list_road_travel_time(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    road_id: Optional[int] = Query(None, description="道路 ID"),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时，不填则返回全天聚合"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    """List road travel time distribution."""
    try:
        service = RoadDataService(session)
        total, items = service.list_road_travel_time(
            stat_date=stat_date,
            road_id=road_id,
            hour=hour,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=RoadTravelTimeListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[RoadTravelTimeMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询道路通行时间失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/geojson", response_model=ResponseBase[RoadGeoJSONResponse])
def list_road_geojson(
    min_lng: Optional[float] = Query(None, description="最小经度"),
    min_lat: Optional[float] = Query(None, description="最小纬度"),
    max_lng: Optional[float] = Query(None, description="最大经度"),
    max_lat: Optional[float] = Query(None, description="最大纬度"),
    road_type: Optional[str] = Query(None, description="道路类型"),
    district_code: Optional[str] = Query(None, description="行政区代码"),
    limit: int = Query(1000, ge=1, le=5000, description="最大返回数量"),
    session=Depends(get_session),
):
    """List road GeoJSON from dw_dim_road."""
    try:
        from models.dw import DwDimRoad
        from sqlalchemy import func, select

        filters = []
        if all(v is not None for v in [min_lng, min_lat, max_lng, max_lat]):
            filters.append(DwDimRoad.geom.ST_Intersects(
                func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
            ))
        if road_type is not None:
            filters.append(DwDimRoad.road_type == road_type)
        if district_code is not None:
            filters.append(DwDimRoad.district_code == district_code)

        count_query = select(func.count(DwDimRoad.road_id)).where(*filters)
        total = session.execute(count_query).scalar_one()

        query = (
            select(
                DwDimRoad.road_id,
                DwDimRoad.road_name,
                DwDimRoad.road_type,
                DwDimRoad.speed_limit,
                DwDimRoad.length_m,
                DwDimRoad.district_code,
                func.ST_AsGeoJSON(DwDimRoad.geom).label("geom_json"),
            )
            .where(*filters)
            .limit(limit)
        )
        rows = session.exec(query).all()

        features = []
        for row in rows:
            geom = json.loads(row.geom_json) if row.geom_json else None
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "road_id": row.road_id,
                    "road_name": row.road_name,
                    "road_type": row.road_type,
                    "speed_limit": row.speed_limit,
                    "length_m": row.length_m,
                    "district_code": row.district_code,
                },
            })

        return ResponseBase(data=RoadGeoJSONResponse(total=total, features=features))
    except Exception as e:
        logger.exception("查询道路 GeoJSON 失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")