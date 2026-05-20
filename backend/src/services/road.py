import logging
from typing import Optional

from sqlalchemy import literal_column
from sqlmodel import Session, func, select

from models.road import BfmapWay

logger = logging.getLogger(__name__)


class RoadService:
    """道路数据服务层"""

    def __init__(self, session: Session):
        self.session = session

    def list_roads(
        self,
        page: int = 1,
        page_size: int = 20,
        class_id: Optional[int] = None,
    ) -> tuple[int, list[BfmapWay]]:
        """查询道路列表（分页）"""
        # 计数查询
        count_query = select(func.count(BfmapWay.gid))
        if class_id is not None:
            count_query = count_query.where(BfmapWay.class_id == class_id)
        total = self.session.exec(count_query).one()

        # 数据查询
        offset = (page - 1) * page_size
        query = select(BfmapWay).order_by(BfmapWay.gid).offset(offset).limit(page_size)
        if class_id is not None:
            query = query.where(BfmapWay.class_id == class_id)

        items = self.session.exec(query).all()
        return total, items

    def get_road_by_gid(self, gid: int) -> Optional[BfmapWay]:
        """根据 gid 查询单条道路"""
        return self.session.get(BfmapWay, gid)

    def get_road_geojson_by_gid(self, gid: int) -> Optional[dict]:
        """根据 gid 查询道路的 GeoJSON 格式"""

        query = select(
            BfmapWay.gid,
            BfmapWay.osm_id,
            BfmapWay.class_id,
            BfmapWay.source,
            BfmapWay.target,
            BfmapWay.length,
            BfmapWay.reverse,
            BfmapWay.maxspeed_forward,
            BfmapWay.maxspeed_backward,
            BfmapWay.priority,
            func.ST_AsGeoJSON(BfmapWay.geom).label("geom_json"),
        ).where(BfmapWay.gid == gid)

        result = self.session.exec(query).first()

        if not result:
            return None

        return {
            "gid": result.gid,
            "osm_id": result.osm_id,
            "class_id": result.class_id,
            "source": result.source,
            "target": result.target,
            "length": result.length,
            "reverse": result.reverse,
            "maxspeed_forward": result.maxspeed_forward,
            "maxspeed_backward": result.maxspeed_backward,
            "priority": result.priority,
            "geom_json": result.geom_json,
        }

    def get_roads_by_bbox(
        self,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[BfmapWay]]:
        """根据 bounding box 查询道路"""

        # 创建 envelope
        envelope = func.ST_MakeEnvelope(
            literal_column(f"{min_lng}"),
            literal_column(f"{min_lat}"),
            literal_column(f"{max_lng}"),
            literal_column(f"{max_lat}"),
            4326,
        )

        # 计数
        count_query = select(func.count(BfmapWay.gid)).where(
            func.ST_Intersects(BfmapWay.geom, envelope)
        )
        total = self.session.exec(count_query).one()

        # 数据查询
        offset = (page - 1) * page_size
        query = (
            select(BfmapWay)
            .where(func.ST_Intersects(BfmapWay.geom, envelope))
            .order_by(BfmapWay.gid)
            .offset(offset)
            .limit(page_size)
        )

        items = self.session.exec(query).all()
        return total, items

    def get_all_roads_geojson(self) -> list[dict]:
        """获取所有道路的 GeoJSON 数据"""
        query = select(
            BfmapWay.gid,
            BfmapWay.osm_id,
            BfmapWay.class_id,
            BfmapWay.source,
            BfmapWay.target,
            BfmapWay.length,
            BfmapWay.reverse,
            BfmapWay.maxspeed_forward,
            BfmapWay.maxspeed_backward,
            BfmapWay.priority,
            func.ST_AsGeoJSON(BfmapWay.geom).label("geom_json"),
        )

        results = self.session.exec(query).all()

        return [
            {
                "gid": r.gid,
                "osm_id": r.osm_id,
                "class_id": r.class_id,
                "source": r.source,
                "target": r.target,
                "length": r.length,
                "reverse": r.reverse,
                "maxspeed_forward": r.maxspeed_forward,
                "maxspeed_backward": r.maxspeed_backward,
                "priority": r.priority,
                "geom_json": r.geom_json,
            }
            for r in results
        ]

    def get_roads_by_bbox_geojson(
        self,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        limit: int = 1000,
        class_id: Optional[int] = None,
        cursor: Optional[int] = None,
        simplify_tolerance: Optional[float] = None,
    ) -> dict:
        """根据 bounding box 获取道路 GeoJSON，使用 gid keyset 分页。"""
        envelope = func.ST_MakeEnvelope(
            literal_column(f"{min_lng}"),
            literal_column(f"{min_lat}"),
            literal_column(f"{max_lng}"),
            literal_column(f"{max_lat}"),
            4326,
        )

        geom_expr = BfmapWay.geom
        if simplify_tolerance is not None and simplify_tolerance > 0:
            geom_expr = func.ST_SimplifyPreserveTopology(
                BfmapWay.geom, literal_column(f"{simplify_tolerance}")
            )

        filters = [func.ST_Intersects(BfmapWay.geom, envelope)]
        if class_id is not None:
            filters.append(BfmapWay.class_id == class_id)
        if cursor is not None:
            filters.append(BfmapWay.gid > cursor)

        query = (
            select(
                BfmapWay.gid,
                BfmapWay.osm_id,
                BfmapWay.class_id,
                BfmapWay.length,
                BfmapWay.maxspeed_forward,
                BfmapWay.maxspeed_backward,
                BfmapWay.priority,
                func.ST_AsGeoJSON(geom_expr).label("geom_json"),
            )
            .where(*filters)
            .order_by(BfmapWay.gid)
            .limit(limit)
        )

        results = self.session.exec(query).all()

        items = [
            {
                "gid": r.gid,
                "osm_id": r.osm_id,
                "class_id": r.class_id,
                "length": r.length,
                "maxspeed_forward": r.maxspeed_forward,
                "maxspeed_backward": r.maxspeed_backward,
                "priority": r.priority,
                "geom_json": r.geom_json,
            }
            for r in results
        ]
        next_cursor = items[-1]["gid"] if len(items) >= limit else None
        return {"items": items, "next_cursor": next_cursor}
