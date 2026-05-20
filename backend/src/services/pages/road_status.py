from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models.ads import AdsRoadStatusHourly
from models.dw import DwDimDistrict, DwDimRoad


class RoadStatusPageService:
    """Road status page composite queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_summary(self, stat_date: date, hour: int) -> Optional[dict]:
        rows = self.session.exec(
            select(
                AdsRoadStatusHourly.status,
                func.count(AdsRoadStatusHourly.road_id),
                func.avg(AdsRoadStatusHourly.current_speed),
            )
            .where(
                AdsRoadStatusHourly.stat_date == stat_date,
                AdsRoadStatusHourly.hour_slice == hour,
                AdsRoadStatusHourly.status.isnot(None),
            )
            .group_by(AdsRoadStatusHourly.status)
        ).all()
        if not rows:
            return None

        counts = {"畅通": 0, "基本畅通": 0, "轻度拥堵": 0, "中度拥堵": 0, "严重拥堵": 0}
        speed_sum = 0.0
        speed_count = 0
        for status, count, avg_speed in rows:
            count = int(count or 0)
            if status in counts:
                counts[status] += count
            if avg_speed is not None:
                speed_sum += float(avg_speed) * count
                speed_count += count

        total = sum(counts.values())
        congested = counts["轻度拥堵"] + counts["中度拥堵"] + counts["严重拥堵"]
        return {
            "total_roads": total,
            "congested_roads": congested,
            "severe_congested_roads": counts["严重拥堵"],
            "avg_speed": (speed_sum / speed_count) if speed_count else None,
            "congestion_pct": (congested / total * 100) if total else 0.0,
        }

    def get_items(
        self,
        stat_date: date,
        hour: int,
        district_code: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        offset = (page - 1) * page_size

        filters = [
            AdsRoadStatusHourly.stat_date == stat_date,
            AdsRoadStatusHourly.hour_slice == hour,
        ]
        if status is not None:
            filters.append(AdsRoadStatusHourly.status == status)
        if district_code is not None:
            filters.append(DwDimRoad.district_code == district_code)

        base_query = (
            select(
                AdsRoadStatusHourly.road_id,
                AdsRoadStatusHourly.road_name,
                AdsRoadStatusHourly.road_class,
                AdsRoadStatusHourly.current_speed,
                AdsRoadStatusHourly.current_flow,
                AdsRoadStatusHourly.congestion_idx,
                AdsRoadStatusHourly.status,
                DwDimRoad.district_code,
                DwDimDistrict.district_name,
            )
            .outerjoin(DwDimRoad, DwDimRoad.road_id == AdsRoadStatusHourly.road_id)
            .outerjoin(DwDimDistrict, DwDimDistrict.district_code == DwDimRoad.district_code)
            .where(*filters)
        )

        count_query = select(func.count()).select_from(base_query.subquery())
        total = self.session.execute(count_query).scalar_one()

        rows = self.session.exec(
            base_query
            .order_by(AdsRoadStatusHourly.congestion_idx.desc().nullslast())
            .offset(offset)
            .limit(page_size)
        ).all()

        return total, [dict(row._mapping) for row in rows]
