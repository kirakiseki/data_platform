from datetime import date
from typing import Literal, Optional

from sqlmodel import Session, func, select

from models.dw import DwFactNetworkDaily, DwFactNetworkHourly


class NetworkDataService:
    """Atomic network metric queries."""

    def __init__(self, session: Session):
        self.session = session

    def list_daily(self) -> list[dict]:
        query = select(DwFactNetworkDaily).order_by(DwFactNetworkDaily.stat_date)
        rows = self.session.exec(query).all()
        return [
            {
                "stat_date": row.stat_date,
                "hour": None,
                "grain": "day",
                "total_trips": row.total_trips,
                "total_vehicles": row.total_vehicles,
                "total_distance_km": self._meters_to_km(row.total_distance),
                "network_avg_speed": row.network_avg_speed,
                "network_avg_duration": row.network_avg_duration,
                "morning_rush_trips": row.morning_rush_trips,
                "evening_rush_trips": row.evening_rush_trips,
                "night_trips": row.night_trips,
            }
            for row in rows
        ]

    def list_hourly(self, stat_date: date) -> list[dict]:
        query = (
            select(DwFactNetworkHourly)
            .where(DwFactNetworkHourly.stat_date == stat_date)
            .order_by(DwFactNetworkHourly.hour_slice)
        )
        rows = self.session.exec(query).all()
        return [self._hourly_row_to_metric(row) for row in rows]

    def get_summary(
        self,
        time_mode: Literal["all", "day", "hour"],
        stat_date: Optional[date] = None,
        hour: Optional[int] = None,
    ) -> Optional[dict]:
        if time_mode == "all":
            row = self.session.exec(
                select(
                    func.sum(DwFactNetworkDaily.total_trips),
                    func.sum(DwFactNetworkDaily.total_vehicles),
                    func.sum(DwFactNetworkDaily.total_distance),
                    func.avg(DwFactNetworkDaily.network_avg_speed),
                    func.avg(DwFactNetworkDaily.network_avg_duration),
                    func.sum(DwFactNetworkDaily.morning_rush_trips),
                    func.sum(DwFactNetworkDaily.evening_rush_trips),
                    func.sum(DwFactNetworkDaily.night_trips),
                )
            ).one()
            return {
                "stat_date": None,
                "hour": None,
                "grain": "all",
                "total_trips": row[0] or 0,
                "total_vehicles": row[1] or 0,
                "total_distance_km": self._meters_to_km(row[2]),
                "network_avg_speed": row[3],
                "network_avg_duration": row[4],
                "morning_rush_trips": row[5],
                "evening_rush_trips": row[6],
                "night_trips": row[7],
            }

        if time_mode == "day":
            row = self.session.exec(
                select(DwFactNetworkDaily).where(DwFactNetworkDaily.stat_date == stat_date)
            ).first()
            if not row:
                return None
            return {
                "stat_date": row.stat_date,
                "hour": None,
                "grain": "day",
                "total_trips": row.total_trips,
                "total_vehicles": row.total_vehicles,
                "total_distance_km": self._meters_to_km(row.total_distance),
                "network_avg_speed": row.network_avg_speed,
                "network_avg_duration": row.network_avg_duration,
                "morning_rush_trips": row.morning_rush_trips,
                "evening_rush_trips": row.evening_rush_trips,
                "night_trips": row.night_trips,
            }

        row = self.session.exec(
            select(DwFactNetworkHourly).where(
                DwFactNetworkHourly.stat_date == stat_date,
                DwFactNetworkHourly.hour_slice == hour,
            )
        ).first()
        if not row:
            return None
        return self._hourly_row_to_metric(row)

    @staticmethod
    def _meters_to_km(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return value / 1000.0

    def _hourly_row_to_metric(self, row: DwFactNetworkHourly) -> dict:
        return {
            "stat_date": row.stat_date,
            "hour": row.hour_slice,
            "grain": "hour",
            "total_trips": row.total_trips,
            "total_vehicles": row.total_vehicles,
            "total_distance_km": self._meters_to_km(row.total_distance),
            "network_avg_speed": row.network_avg_speed,
            "network_avg_duration": None,
            "morning_rush_trips": None,
            "evening_rush_trips": None,
            "night_trips": None,
        }
