from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.pages.hotspot import HotspotZoneItem, HotspotZoneListResponse
from services.pages.hotspot import HotspotPageService

router = APIRouter(prefix="/page", tags=["page"])


@router.get("/hotspot/zones", response_model=ResponseBase[HotspotZoneListResponse])
def get_hotspot_zones(
    zone_type: Literal["district", "grid", "poi", "cluster"] = Query(
        ..., description="区域类型"
    ),
    stat_date: date = Query(
        ..., alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期"
    ),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时（不填返回日级）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    try:
        svc = HotspotPageService(session)
        total, items = svc.get_zones(zone_type, stat_date, hour, page, page_size)
        return ResponseBase(
            data=HotspotZoneListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[HotspotZoneItem(**item) for item in items],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
