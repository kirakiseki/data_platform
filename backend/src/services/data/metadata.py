from sqlmodel import Session, select

from models.dw import DwDimRoadClass, DwDimTime


class MetadataService:
    """Metadata and business glossary queries."""

    def __init__(self, session: Session):
        self.session = session

    def get_available_dates(self) -> list:
        query = select(DwDimTime.date_id).distinct().order_by(DwDimTime.date_id)
        return list(self.session.exec(query).all())

    def list_road_classes(self) -> list[dict]:
        query = select(DwDimRoadClass).order_by(DwDimRoadClass.class_id)
        rows = self.session.exec(query).all()
        return [
            {
                "class_id": row.class_id,
                "class_name": row.class_name,
                "road_level": row.road_level,
                "default_speed": row.default_speed,
                "congestion_threshold_smooth": row.congestion_threshold_smooth,
                "congestion_threshold_slow": row.congestion_threshold_slow,
                "congestion_threshold_congested": row.congestion_threshold_congested,
                "description": row.description,
            }
            for row in rows
        ]
