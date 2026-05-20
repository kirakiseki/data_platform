from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.pages.dashboard import (
    DashboardPageResponse,
    DayStats,
    DistanceTrendItem,
    HourStats,
    NetworkTrendItem,
    PlatformStats,
    TopHotspotItem,
    TopRoadItem,
)
from services.pages.dashboard import DashboardPageService

router = APIRouter(prefix="/page", tags=["page"])


@router.get("/dashboard", response_model=ResponseBase[DashboardPageResponse])
def get_dashboard(
    time_mode: Literal["all", "day", "hour"] = Query(
        "day", description="统计口径：all=全部聚合，day=按天，hour=按小时"
    ),
    stat_date: Optional[date] = Query(
        None, alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期（day/hour 必填）"
    ),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时（hour 模式必填）"),
    top_n: int = Query(5, ge=1, le=50, description="Top-N 数量"),
    hotspot_zone_type: Literal["district", "grid", "poi", "cluster"] = Query(
        "poi", description="高频区域统计口径：行政区/网格/重点场所/聚类"
    ),
    session=Depends(get_session),
):
    try:
        if time_mode in ("day", "hour") and stat_date is None:
            return ResponseBase(code=400, message="day/hour 模式下需要提供 date")
        if time_mode == "hour" and hour is None:
            return ResponseBase(code=400, message="hour 模式下需要提供 hour")

        svc = DashboardPageService(session)

        platform_stats_data = svc.get_platform_stats()
        day_stats_data = svc.get_day_stats(time_mode, stat_date)
        hour_stats_data = (
            svc.get_hour_stats(stat_date, hour)
            if time_mode == "hour" and stat_date is not None and hour is not None
            else None
        )
        network_trend_data = svc.get_network_trend(time_mode, stat_date, hour)
        distance_trend_data = svc.get_distance_trend(time_mode, stat_date, hour)
        top_roads_data = svc.get_top_roads(time_mode, stat_date, hour, top_n)
        top_hotspots_data = svc.get_top_hotspots(
            time_mode, stat_date, hour, top_n, hotspot_zone_type
        )

        return ResponseBase(
            data=DashboardPageResponse(
                platform_stats=PlatformStats(**platform_stats_data),
                day_stats=DayStats(**day_stats_data) if day_stats_data else None,
                hour_stats=HourStats(**hour_stats_data) if hour_stats_data else None,
                network_trend=[NetworkTrendItem(**item) for item in network_trend_data],
                distance_trend=[DistanceTrendItem(**item) for item in distance_trend_data],
                top_roads=[TopRoadItem(**item) for item in top_roads_data],
                top_hotspots=[TopHotspotItem(**item) for item in top_hotspots_data],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
