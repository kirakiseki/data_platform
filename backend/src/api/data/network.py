from datetime import date
import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.data.network import NetworkDailyResponse, NetworkHourlyResponse, NetworkMetric
from services.data.network import NetworkDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/network", tags=["data-network"])


@router.get("/daily", response_model=ResponseBase[NetworkDailyResponse])
def list_network_daily(session=Depends(get_session)):
    """List daily network metrics."""
    try:
        service = NetworkDataService(session)
        return ResponseBase(
            data=NetworkDailyResponse(
                items=[NetworkMetric(**item) for item in service.list_daily()]
            )
        )
    except Exception as e:
        logger.exception("查询全网日指标失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hourly", response_model=ResponseBase[NetworkHourlyResponse])
def list_network_hourly(
    stat_date: date = Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期，范围 2015-01-03 到 2015-01-08",
    ),
    session=Depends(get_session),
):
    """List hourly network metrics for one date."""
    try:
        service = NetworkDataService(session)
        return ResponseBase(
            data=NetworkHourlyResponse(
                date=stat_date,
                items=[NetworkMetric(**item) for item in service.list_hourly(stat_date)],
            )
        )
    except Exception as e:
        logger.exception("查询全网小时指标失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/summary", response_model=ResponseBase[NetworkMetric])
def get_network_summary(
    time_mode: Literal["all", "day", "hour"] = Query(..., description="统计范围"),
    stat_date: Optional[date] = Query(
        None,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期，day/hour 模式必填",
    ),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时，hour 模式必填"),
    session=Depends(get_session),
):
    """Get one network summary metric by time mode."""
    if time_mode in {"day", "hour"} and stat_date is None:
        return ResponseBase(code=400, message="day/hour 模式必须提供 date")
    if time_mode == "hour" and hour is None:
        return ResponseBase(code=400, message="hour 模式必须提供 hour")

    try:
        service = NetworkDataService(session)
        item = service.get_summary(time_mode, stat_date, hour)
        if not item:
            return ResponseBase(code=404, message="指标不存在")
        return ResponseBase(data=NetworkMetric(**item))
    except Exception as e:
        logger.exception("查询全网汇总指标失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
