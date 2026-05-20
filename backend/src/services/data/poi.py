from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlmodel import Session

from models.dw import DwFactPoiDaily, DwFactPoiHourly


class PoiDataService:
    """Atomic POI data queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_flow_hourly(
        self,
        stat_date: date,
        hour: Optional[int] = None,
        poi_id: Optional[int] = None,
    ) -> list[dict]:
        filters = [DwFactPoiHourly.stat_date == stat_date]
        if hour is not None:
            filters.append(DwFactPoiHourly.hour_slice == hour)
        if poi_id is not None:
            filters.append(DwFactPoiHourly.poi_id == poi_id)

        query = (
            select(
                DwFactPoiHourly.poi_id,
                DwFactPoiHourly.stat_date,
                DwFactPoiHourly.hour_slice.label("hour"),
                DwFactPoiHourly.trip_count,
                DwFactPoiHourly.pickup_count,
                DwFactPoiHourly.dropoff_count,
            )
            .where(*filters)
            .order_by(DwFactPoiHourly.hour_slice, DwFactPoiHourly.poi_id)
        )
        rows = self.session.exec(query).all()
        return [dict(row._mapping) for row in rows]

    def list_flow_daily(
        self,
        stat_date: date,
        poi_id: Optional[int] = None,
    ) -> list[dict]:
        filters = [DwFactPoiDaily.stat_date == stat_date]
        if poi_id is not None:
            filters.append(DwFactPoiDaily.poi_id == poi_id)

        query = (
            select(
                DwFactPoiDaily.poi_id,
                DwFactPoiDaily.stat_date,
                DwFactPoiDaily.trip_count,
                DwFactPoiDaily.pickup_count,
                DwFactPoiDaily.dropoff_count,
            )
            .where(*filters)
            .order_by(DwFactPoiDaily.poi_id)
        )
        rows = self.session.exec(query).all()
        return [dict(row._mapping) for row in rows]