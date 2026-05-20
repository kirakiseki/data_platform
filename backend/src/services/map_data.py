import json
import logging

from sqlmodel import Session, func, select

from models.road import BfmapWay

logger = logging.getLogger(__name__)


class MapDataService:
    """地图数据服务层(bfmap_ways道路数据)"""

    def __init__(self, session: Session):
        self.session = session

    def get_roads(self) -> list[dict]:
        """从bfmap_ways表获取道路数据"""
        query = select(
            BfmapWay.gid,
            BfmapWay.osm_id,
            BfmapWay.class_id,
            BfmapWay.length,
            BfmapWay.maxspeed_forward,
            BfmapWay.maxspeed_backward,
            BfmapWay.priority,
            func.ST_AsGeoJSON(BfmapWay.geom).label("geom_json"),
        )

        try:
            results = self.session.exec(query).all()
            return [
                {
                    "gid": r.gid,
                    "osm_id": r.osm_id,
                    "class_id": r.class_id,
                    "length": r.length,
                    "maxspeed_forward": r.maxspeed_forward,
                    "maxspeed_backward": r.maxspeed_backward,
                    "priority": r.priority,
                    "geom_json": json.loads(r.geom_json) if r.geom_json else {},
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"查询道路数据失败: {e}")
            return []
