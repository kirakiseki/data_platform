from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.pages.road_status import (
    RoadStatusPageItem,
    RoadStatusPageResponse,
    RoadStatusPageSummary,
)
from services.pages.road_status import RoadStatusPageService

router = APIRouter(prefix="/page", tags=["page"])


@router.get("/road-status", response_model=ResponseBase[RoadStatusPageResponse])
def get_road_status_page(
    stat_date: date = Query(
        ..., alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期"
    ),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    district_code: Optional[str] = Query(None, description="行政区代码过滤"),
    status: Optional[Literal["畅通", "基本畅通", "轻度拥堵", "中度拥堵", "严重拥堵"]] = Query(
        None, description="路况状态过滤"
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    try:
        svc = RoadStatusPageService(session)
        summary_data = svc.get_summary(stat_date, hour)
        total, items_data = svc.get_items(
            stat_date=stat_date,
            hour=hour,
            district_code=district_code,
            status=status,
            page=page,
            page_size=page_size,
        )

        if summary_data is None:
            summary_data = {
                "total_roads": 0,
                "congested_roads": 0,
                "severe_congested_roads": 0,
                "avg_speed": None,
                "congestion_pct": None,
            }

        return ResponseBase(
            data=RoadStatusPageResponse(
                summary=RoadStatusPageSummary(**summary_data),
                total=total,
                page=page,
                page_size=page_size,
                items=[RoadStatusPageItem(**item) for item in items_data],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
