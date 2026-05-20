from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.pages.trajectory import (
    TrajectorySampleItem,
    TrajectorySampleListResponse,
    TrajectoryDailyStatsItem,
    TrajectoryDailyStatsResponse,
)
from services.pages.trajectory import TrajectoryPageService

router = APIRouter(prefix="/page", tags=["page"])


@router.get(
    "/trajectory/daily-stats", response_model=ResponseBase[TrajectoryDailyStatsResponse]
)
def get_trajectory_daily_stats(session=Depends(get_session)):
    try:
        svc = TrajectoryPageService(session)
        items = svc.get_daily_stats()
        return ResponseBase(
            data=TrajectoryDailyStatsResponse(
                items=[TrajectoryDailyStatsItem(**item) for item in items]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get(
    "/trajectory/samples", response_model=ResponseBase[TrajectorySampleListResponse]
)
def get_trajectory_samples(
    stat_date: Optional[date] = Query(
        None, alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期（可选）"
    ),
    hour: Optional[int] = Query(None, ge=0, le=23, description="行程起始小时（可选）"),
    sample_size: int = Query(5, ge=1, le=20, description="采样行程数"),
    route_source: Literal["matched", "raw"] = Query(
        "matched",
        description="路径来源：matched=地图匹配后路段拼接（默认，严格沿道路），raw=原始 GPS 点聚合",
    ),
    session=Depends(get_session),
):
    try:
        svc = TrajectoryPageService(session)
        items = svc.get_samples(stat_date, hour, sample_size, route_source)
        return ResponseBase(
            data=TrajectorySampleListResponse(
                items=[TrajectorySampleItem(**item) for item in items]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
