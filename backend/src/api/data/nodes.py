import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.roads import NodeDetailMetric, NodeDetailResponse, NodeListResponse, NodeMetric
from services.data.nodes import NodeDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data/nodes", tags=["data-nodes"])


@router.get("", response_model=ResponseBase[NodeListResponse])
def list_nodes(
    district_code: Optional[str] = Query(None, description="行政区代码"),
    node_type: Optional[str] = Query(None, description="节点类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    """List nodes with pagination."""
    try:
        service = NodeDataService(session)
        total, items = service.list_nodes(
            district_code=district_code,
            node_type=node_type,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=NodeListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[NodeMetric(**item) for item in items],
            )
        )
    except Exception as e:
        logger.exception("查询节点列表失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/{node_id}", response_model=ResponseBase[NodeDetailResponse])
def get_node(node_id: int, session=Depends(get_session)):
    """Get single node detail with TDM tags."""
    try:
        service = NodeDataService(session)
        item = service.get_node(node_id)
        if not item:
            return ResponseBase(code=404, message="节点不存在")
        return ResponseBase(data=NodeDetailResponse(data=NodeDetailMetric(**item)))
    except Exception as e:
        logger.exception("查询节点详情失败")
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")