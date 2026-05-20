import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.data.poi import PoiFlowDailyListResponse, PoiFlowDailyMetric, PoiFlowHourlyListResponse, PoiFlowHourlyMetric
from services.data.poi import PoiDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/poi", tags=["data-poi"])


@router.get("/flow/hourly", response_model=ResponseBase[PoiFlowHourlyListResponse])
def list_poi_flow_hourly(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时，不填返回全天 24 条"),
    poi_id: Optional[int] = Query(None, description="POI ID"),
    session=Depends(get_session),
):
    """List POI hourly flow metrics."""
    try:
        service = PoiDataService(session)
        items = service.list_flow_hourly(stat_date=stat_date, hour=hour, poi_id=poi_id)
        return ResponseBase(
            data=PoiFlowHourlyListResponse(
                total=len(items),
                page=1,
                page_size=len(items),
                items=[PoiFlowHourlyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询 POI 小时流量失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/flow/daily", response_model=ResponseBase[PoiFlowDailyListResponse])
def list_poi_flow_daily(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期",
    ),
    poi_id: Optional[int] = Query(None, description="POI ID"),
    session=Depends(get_session),
):
    """List POI daily flow metrics."""
    try:
        service = PoiDataService(session)
        items = service.list_flow_daily(stat_date=stat_date, poi_id=poi_id)
        return ResponseBase(
            data=PoiFlowDailyListResponse(
                total=len(items),
                page=1,
                page_size=len(items),
                items=[PoiFlowDailyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询 POI 日流量失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")