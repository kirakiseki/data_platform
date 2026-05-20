from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models.dw import DwDimNode
from models.tdm import TdmTagNode


class NodeDataService:
    """Atomic node data queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_nodes(
        self,
        district_code: Optional[str] = None,
        node_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = []
        if district_code is not None:
            filters.append(DwDimNode.district_code == district_code)
        if node_type is not None:
            filters.append(DwDimNode.node_type == node_type)

        count_query = select(func.count(DwDimNode.node_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                DwDimNode.node_id,
                DwDimNode.osm_node_id,
                DwDimNode.node_name,
                DwDimNode.node_type,
                DwDimNode.latitude,
                DwDimNode.longitude,
                DwDimNode.district_code,
            )
            .where(*filters)
            .order_by(DwDimNode.node_id)
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def get_node(self, node_id: int) -> Optional[dict]:
        row = self.session.exec(
            select(DwDimNode).where(DwDimNode.node_id == node_id)
        ).first()
        if not row:
            return None

        result = {
            "node_id": row.node_id,
            "osm_node_id": row.osm_node_id,
            "node_name": row.node_name,
            "node_type": row.node_type,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "district_code": row.district_code,
        }

        tag = self.session.exec(
            select(TdmTagNode).where(TdmTagNode.node_id == node_id)
        ).first()
        if tag:
            result["avg_in_flow"] = tag.avg_in_flow
            result["avg_out_flow"] = tag.avg_out_flow
            result["in_out_ratio"] = tag.in_out_ratio

        return result