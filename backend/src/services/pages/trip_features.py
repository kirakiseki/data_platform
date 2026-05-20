from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models.dw import DwDimDistrict, DwFactOdClusterDaily


class TripFeaturesPageService:
    """Trip features OD page queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_od_pairs(
        self,
        stat_date: date,
        top_n: int = 10,
        flow_direction: Optional[str] = None,
    ) -> list[dict]:
        filters = [
            DwFactOdClusterDaily.stat_date == stat_date,
            DwFactOdClusterDaily.origin_center_lon.isnot(None),
            DwFactOdClusterDaily.origin_center_lat.isnot(None),
            DwFactOdClusterDaily.dest_center_lon.isnot(None),
            DwFactOdClusterDaily.dest_center_lat.isnot(None),
        ]
        if flow_direction is not None:
            filters.append(DwFactOdClusterDaily.flow_direction == flow_direction)

        origin_name_sq = (
            select(DwDimDistrict.district_name)
            .where(
                func.ST_Within(
                    func.ST_SetSRID(
                        func.ST_Point(
                            DwFactOdClusterDaily.origin_center_lon,
                            DwFactOdClusterDaily.origin_center_lat,
                        ),
                        4326,
                    ),
                    DwDimDistrict.geom,
                )
            )
            .limit(1)
            .correlate(DwFactOdClusterDaily)
            .scalar_subquery()
        )

        dest_name_sq = (
            select(DwDimDistrict.district_name)
            .where(
                func.ST_Within(
                    func.ST_SetSRID(
                        func.ST_Point(
                            DwFactOdClusterDaily.dest_center_lon,
                            DwFactOdClusterDaily.dest_center_lat,
                        ),
                        4326,
                    ),
                    DwDimDistrict.geom,
                )
            )
            .limit(1)
            .correlate(DwFactOdClusterDaily)
            .scalar_subquery()
        )

        rows = self.session.exec(
            select(
                DwFactOdClusterDaily.fact_id,
                DwFactOdClusterDaily.origin_center_lon,
                DwFactOdClusterDaily.origin_center_lat,
                DwFactOdClusterDaily.dest_center_lon,
                DwFactOdClusterDaily.dest_center_lat,
                DwFactOdClusterDaily.trip_count,
                DwFactOdClusterDaily.avg_distance,
                DwFactOdClusterDaily.avg_duration,
                DwFactOdClusterDaily.flow_direction,
                origin_name_sq.label("origin_name"),
                dest_name_sq.label("dest_name"),
            )
            .where(*filters)
            .order_by(DwFactOdClusterDaily.trip_count.desc())
            .limit(top_n)
        ).all()

        return [
            {
                "rank": idx + 1,
                "origin_name": row.origin_name,
                "origin_lon": row.origin_center_lon,
                "origin_lat": row.origin_center_lat,
                "dest_name": row.dest_name,
                "dest_lon": row.dest_center_lon,
                "dest_lat": row.dest_center_lat,
                "trip_count": row.trip_count,
                "avg_distance": (row.avg_distance / 1000.0) if row.avg_distance else None,
                "avg_duration": (row.avg_duration / 60.0) if row.avg_duration else None,
                "flow_direction": row.flow_direction,
            }
            for idx, row in enumerate(rows)
        ]
