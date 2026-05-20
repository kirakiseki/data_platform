import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.tdm import (
    DistrictMetric,
    TdmNodeTagListResponse,
    TdmNodeTagMetric,
    TdmRoadTagListResponse,
    TdmRoadTagMetric,
    TdmTimeSlotMetric,
    TdmVehicleTagListResponse,
    TdmVehicleTagMetric,
    TdmVehicleTagResponse,
)
from services.data.tdm import TdmDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/tdm", tags=["data-tdm"])


@router.get("/roads", response_model=ResponseBase[TdmRoadTagListResponse])
def list_tdm_roads(
    road_type: Optional[str] = Query(None, description="道路类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    """List road tag metrics."""
    try:
        service = TdmDataService(session)
        total, items = service.list_road_tags(road_type=road_type, page=page, page_size=page_size)
        return ResponseBase(
            data=TdmRoadTagListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[TdmRoadTagMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询道路标签失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/nodes", response_model=ResponseBase[TdmNodeTagListResponse])
def list_tdm_nodes(
    node_type: Optional[str] = Query(None, description="节点类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    """List node tag metrics."""
    try:
        service = TdmDataService(session)
        total, items = service.list_node_tags(node_type=node_type, page=page, page_size=page_size)
        return ResponseBase(
            data=TdmNodeTagListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[TdmNodeTagMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询节点标签失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/vehicles", response_model=ResponseBase[TdmVehicleTagListResponse])
def list_tdm_vehicles(
    devid: Optional[str] = Query(None, description="车辆设备 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    """List vehicle tag metrics."""
    try:
        service = TdmDataService(session)
        total, items = service.list_vehicle_tags(devid=devid, page=page, page_size=page_size)
        return ResponseBase(
            data=TdmVehicleTagListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[TdmVehicleTagMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询车辆标签失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/vehicles/{devid}", response_model=ResponseBase[TdmVehicleTagResponse])
def get_tdm_vehicle(devid: str, session=Depends(get_session)):
    """Get single vehicle tag detail."""
    try:
        service = TdmDataService(session)
        item = service.get_vehicle_tag(devid)
        if not item:
            return ResponseBase(code=404, message="车辆标签不存在")
        return ResponseBase(data=TdmVehicleTagResponse(**item))
    except Exception as e:
        logger.exception("查询车辆标签详情失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/time-slots", response_model=ResponseBase[list[TdmTimeSlotMetric]])
def list_tdm_time_slots(session=Depends(get_session)):
    """List time slot definitions."""
    try:
        service = TdmDataService(session)
        return ResponseBase(data=[TdmTimeSlotMetric(**item) for item in service.list_time_slots()])
    except Exception as e:
        logger.exception("查询时段标签失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/districts", response_model=ResponseBase[list[DistrictMetric]])
def list_districts(session=Depends(get_session)):
    """List district metadata."""
    try:
        service = TdmDataService(session)
        return ResponseBase(data=[DistrictMetric(**item) for item in service.list_districts()])
    except Exception as e:
        logger.exception("查询行政区信息失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")