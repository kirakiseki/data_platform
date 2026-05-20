import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.data.od import (
    OdClusterDailyListResponse,
    OdClusterDailyMetric,
    OdClusterHourlyListResponse,
    OdClusterHourlyMetric,
    OdGridDailyListResponse,
    OdGridDailyMetric,
    OdGridHourlyListResponse,
    OdGridHourlyMetric,
)
from services.data.od import OdDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/od", tags=["data-od"])


@router.get("/grid/hourly", response_model=ResponseBase[OdGridHourlyListResponse])
def list_od_grid_hourly(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    origin_grid_id: Optional[str] = Query(None, description="起点网格 ID"),
    dest_grid_id: Optional[str] = Query(None, description="终点网格 ID"),
    min_trip_count: Optional[int] = Query(None, ge=1, description="最小行程数"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    """List grid OD hourly metrics."""
    try:
        service = OdDataService(session)
        total, items = service.list_grid_hourly(
            stat_date=stat_date,
            hour=hour,
            origin_grid_id=origin_grid_id,
            dest_grid_id=dest_grid_id,
            min_trip_count=min_trip_count,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=OdGridHourlyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[OdGridHourlyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询网格 OD 小时矩阵失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/grid/daily", response_model=ResponseBase[OdGridDailyListResponse])
def list_od_grid_daily(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    origin_grid_id: Optional[str] = Query(None, description="起点网格 ID"),
    dest_grid_id: Optional[str] = Query(None, description="终点网格 ID"),
    min_trip_count: Optional[int] = Query(None, ge=1, description="最小行程数"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    """List grid OD daily metrics."""
    try:
        service = OdDataService(session)
        total, items = service.list_grid_daily(
            stat_date=stat_date,
            origin_grid_id=origin_grid_id,
            dest_grid_id=dest_grid_id,
            min_trip_count=min_trip_count,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=OdGridDailyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[OdGridDailyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询网格 OD 日矩阵失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/cluster/hourly", response_model=ResponseBase[OdClusterHourlyListResponse])
def list_od_cluster_hourly(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    flow_direction: Optional[str] = Query(
        None,
        description="流向类型：commute_outbound、commute_inbound、local、transit",
    ),
    distance_type: Optional[str] = Query(None, description="距离类型：short、medium、long"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    """List cluster OD hourly metrics."""
    try:
        service = OdDataService(session)
        total, items = service.list_cluster_hourly(
            stat_date=stat_date,
            hour=hour,
            flow_direction=flow_direction,
            distance_type=distance_type,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=OdClusterHourlyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[OdClusterHourlyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询聚类 OD 小时矩阵失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/cluster/daily", response_model=ResponseBase[OdClusterDailyListResponse])
def list_od_cluster_daily(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    flow_direction: Optional[str] = Query(
        None,
        description="流向类型：commute_outbound、commute_inbound、local、transit",
    ),
    distance_type: Optional[str] = Query(None, description="距离类型：short、medium、long"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    """List cluster OD daily metrics."""
    try:
        service = OdDataService(session)
        total, items = service.list_cluster_daily(
            stat_date=stat_date,
            flow_direction=flow_direction,
            distance_type=distance_type,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=OdClusterDailyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[OdClusterDailyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询聚类 OD 日矩阵失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")