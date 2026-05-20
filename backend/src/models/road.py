from typing import Optional

from geoalchemy2 import Geometry
from sqlmodel import Field, SQLModel


class BfmapWay(SQLModel, table=True):
    """图匹配后的道路表"""

    __tablename__ = "bfmap_ways"

    gid: Optional[int] = Field(default=None, primary_key=True)
    osm_id: int = Field(nullable=False)
    class_id: int = Field(nullable=False)
    source: int = Field(nullable=False)
    target: int = Field(nullable=False)
    length: float = Field(nullable=False)
    reverse: float = Field(nullable=False)
    maxspeed_forward: Optional[int] = Field(default=None)
    maxspeed_backward: Optional[int] = Field(default=None)
    priority: float = Field(nullable=False)
    geom: Optional[str] = Field(default=None, sa_type=Geometry("LINESTRING", srid=4326))
