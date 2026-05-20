from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models.dw import DwDimDistrict
from models.tdm import TdmTagNode, TdmTagRoad, TdmTagTimeSlot, TdmTagVehicle


class TdmDataService:
    """TDM tag data queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_road_tags(
        self,
        road_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = []
        if road_type is not None:
            filters.append(TdmTagRoad.road_type == road_type)

        count_query = select(func.count(TdmTagRoad.road_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                TdmTagRoad.road_id,
                TdmTagRoad.road_name,
                TdmTagRoad.road_type,
                TdmTagRoad.speed_limit,
                TdmTagRoad.avg_daily_flow,
                TdmTagRoad.avg_rush_flow,
                TdmTagRoad.avg_night_flow,
                TdmTagRoad.avg_daily_speed,
                TdmTagRoad.tags_updated_at,
            )
            .where(*filters)
            .order_by(TdmTagRoad.avg_daily_flow.desc().nullslast())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_node_tags(
        self,
        node_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = []
        if node_type is not None:
            filters.append(TdmTagNode.node_type == node_type)

        count_query = select(func.count(TdmTagNode.node_id)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(
                TdmTagNode.node_id,
                TdmTagNode.node_name,
                TdmTagNode.node_type,
                TdmTagNode.avg_in_flow,
                TdmTagNode.avg_out_flow,
                TdmTagNode.in_out_ratio,
                TdmTagNode.tags_updated_at,
            )
            .where(*filters)
            .order_by(TdmTagNode.avg_in_flow.desc().nullslast())
            .offset(offset)
            .limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [dict(row._mapping) for row in rows]

    def list_vehicle_tags(
        self,
        devid: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = []
        if devid is not None:
            filters.append(TdmTagVehicle.devid == devid)

        count_query = select(func.count(TdmTagVehicle.devid)).where(*filters)
        total = self.session.execute(count_query).scalar_one()

        query = (
            select(TdmTagVehicle).where(*filters).offset(offset).limit(page_size)
        )
        rows = self.session.exec(query).all()
        return total, [
            {
                "devid": row.devid,
                "total_trips": row.total_trips,
                "total_distance": row.total_distance,
                "total_duration": row.total_duration,
                "avg_daily_trips": row.avg_daily_trips,
                "avg_daily_distance": row.avg_daily_distance,
                "avg_daily_hours": row.avg_daily_hours,
                "avg_trip_distance": row.avg_trip_distance,
                "avg_trip_duration": row.avg_trip_duration,
                "rush_hour_trips": row.rush_hour_trips,
                "rush_hour_ratio": row.rush_hour_ratio,
                "night_trips": row.night_trips,
                "night_ratio": row.night_ratio,
                "short_trip_count": row.short_trip_count,
                "medium_trip_count": row.medium_trip_count,
                "long_trip_count": row.long_trip_count,
                "long_trip_ratio": row.long_trip_ratio,
                "tags_updated_at": row.tags_updated_at,
            }
            for row in rows
        ]

    def get_vehicle_tag(self, devid: str) -> Optional[dict]:
        row = self.session.exec(
            select(TdmTagVehicle).where(TdmTagVehicle.devid == devid)
        ).first()
        if not row:
            return None
        return {
            "devid": row.devid,
            "total_trips": row.total_trips,
            "total_distance": row.total_distance,
            "total_duration": row.total_duration,
            "avg_daily_trips": row.avg_daily_trips,
            "avg_daily_distance": row.avg_daily_distance,
            "avg_daily_hours": row.avg_daily_hours,
            "avg_trip_distance": row.avg_trip_distance,
            "avg_trip_duration": row.avg_trip_duration,
            "rush_hour_trips": row.rush_hour_trips,
            "rush_hour_ratio": row.rush_hour_ratio,
            "night_trips": row.night_trips,
            "night_ratio": row.night_ratio,
            "short_trip_count": row.short_trip_count,
            "medium_trip_count": row.medium_trip_count,
            "long_trip_count": row.long_trip_count,
            "long_trip_ratio": row.long_trip_ratio,
            "main_hour_start": row.main_hour_start,
            "main_hour_end": row.main_hour_end,
            "tags_updated_at": row.tags_updated_at,
        }

    def list_time_slots(self) -> list[dict]:
        rows = self.session.exec(
            select(TdmTagTimeSlot).order_by(TdmTagTimeSlot.slot_id)
        ).all()
        return [
            {
                "slot_id": row.slot_id,
                "slot_name": row.slot_name,
                "slot_type": row.slot_type,
                "start_hour": row.start_hour,
                "end_hour": row.end_hour,
                "weekdays": row.weekdays,
                "traffic_pattern": row.traffic_pattern,
            }
            for row in rows
        ]

    def list_districts(self) -> list[dict]:
        rows = self.session.exec(
            select(DwDimDistrict).order_by(DwDimDistrict.district_code)
        ).all()
        return [
            {
                "district_code": row.district_code,
                "district_name": row.district_name,
                "district_level": row.district_level,
                "parent_code": row.parent_code,
            }
            for row in rows
        ]