import logging

from fastapi import APIRouter, Depends

from api.response import ResponseBase
from db.session import get_session
from schemas.data.metadata import DateRangeResponse, RoadClassResponse
from services.data.metadata import MetadataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/date-range", response_model=ResponseBase[DateRangeResponse])
def get_date_range(session=Depends(get_session)):
    """Get available business dates."""
    try:
        service = MetadataService(session)
        dates = service.get_available_dates()
        if not dates:
            return ResponseBase(code=404, message="暂无可用日期")
        return ResponseBase(
            data=DateRangeResponse(
                start_date=dates[0],
                end_date=dates[-1],
                available_dates=dates,
            )
        )
    except Exception as e:
        logger.exception("获取日期范围失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/road-classes", response_model=ResponseBase[list[RoadClassResponse]])
def list_road_classes(session=Depends(get_session)):
    """List road class metadata."""
    try:
        service = MetadataService(session)
        return ResponseBase(
            data=[RoadClassResponse(**item) for item in service.list_road_classes()]
        )
    except Exception as e:
        logger.exception("获取道路等级元数据失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")
