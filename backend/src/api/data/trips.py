import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.data.trips import GpsPointListResponse, GpsPointMetric, TripDetailMetric, TripDetailResponse, TripListResponse, TripMetric
from services.data.trips import TripDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/trips", tags=["data-trips"])


@router.get("", response_model=ResponseBase[TripListResponse])
def list_trips(
    stat_date: Optional[date] = Query(
        None,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    devid: Optional[str] = Query(None, description="车辆设备 ID"),
    is_rush_hour: Optional[bool] = Query(None, description="仅高峰时段行程"),
    is_long_trip: Optional[bool] = Query(None, description="仅长途行程（> 10km）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    """List trip details with pagination."""
    try:
        service = TripDataService(session)
        total, items = service.list_trips(
            stat_date=stat_date,
            devid=devid,
            is_rush_hour=is_rush_hour,
            is_long_trip=is_long_trip,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=TripListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[TripMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询行程列表失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/gps-points", response_model=ResponseBase[GpsPointListResponse])
def list_gps_points(trip_id: int = Query(..., description="行程 ID"), session=Depends(get_session)):
    """List GPS points for a trip."""
    try:
        service = TripDataService(session)
        items = service.list_gps_points(trip_id)
        if not items:
            return ResponseBase(code=404, message="无 GPS 点数据")
        return ResponseBase(
            data=GpsPointListResponse(
                trip_id=trip_id,
                items=[GpsPointMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询 GPS 点失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/{trip_id}", response_model=ResponseBase[TripDetailResponse])
def get_trip(trip_id: int, session=Depends(get_session)):
    """Get single trip detail with route line."""
    try:
        service = TripDataService(session)
        item = service.get_trip(trip_id)
        if not item:
            return ResponseBase(code=404, message="行程不存在")
        return ResponseBase(data=TripDetailResponse(data=TripDetailMetric(**item)))
    except Exception as e:
        logger.exception("查询行程详情失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")