from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from schemas.pages.trip_features import TripOdItem, TripOdPageResponse
from services.pages.trip_features import TripFeaturesPageService

router = APIRouter(prefix="/page", tags=["page"])


@router.get("/trip-features/od", response_model=ResponseBase[TripOdPageResponse])
def get_trip_od(
    stat_date: date = Query(
        ..., alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期"
    ),
    top_n: int = Query(10, ge=1, le=50, description="返回 Top-N OD 对"),
    flow_direction: Optional[
        Literal["commute_outbound", "commute_inbound", "local", "transit"]
    ] = Query(None, description="流向类型过滤"),
    session=Depends(get_session),
):
    try:
        svc = TripFeaturesPageService(session)
        items = svc.get_od_pairs(stat_date, top_n, flow_direction)
        return ResponseBase(
            data=TripOdPageResponse(items=[TripOdItem(**item) for item in items])
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
