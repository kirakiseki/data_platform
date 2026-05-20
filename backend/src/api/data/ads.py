from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from api.response import ResponseBase
from db.session import get_session
from schemas.data.ads import (
    AdsCongestionHourlyMetric,
    AdsCongestionHourlyResponse,
    AdsHotspotClusterDailyListResponse,
    AdsHotspotClusterDailyMetric,
    AdsHotspotClusterHourlyListResponse,
    AdsHotspotClusterHourlyMetric,
    AdsHotspotDistrictDailyMetric,
    AdsHotspotDistrictDailyResponse,
    AdsHotspotDistrictHourlyResponse,
    AdsHotspotDistrictHourlyMetric,
    AdsHotspotGridDailyListResponse,
    AdsHotspotGridDailyMetric,
    AdsHotspotGridHourlyListResponse,
    AdsHotspotGridHourlyMetric,
    AdsHotspotMonitorDailyMetric,
    AdsHotspotMonitorDailyResponse,
    AdsHotspotPoiDailyListResponse,
    AdsHotspotPoiDailyMetric,
    AdsHotspotPoiHourlyListResponse,
    AdsHotspotPoiHourlyMetric,
    AdsNetworkStatusHourlyMetric,
    AdsNetworkStatusHourlyResponse,
    AdsRoadStatusHourlyListResponse,
    AdsRoadStatusHourlyMetric,
    AdsTopCongestedRoadMetric,
    AdsTopCongestedRoadsResponse,
    AdsTripDistanceDailyMetric,
    AdsTripDistanceDailyResponse,
    AdsTripDistanceHourlyMetric,
    AdsTripDistanceHourlyResponse,
    AdsTripSpeedDailyMetric,
    AdsTripSpeedDailyResponse,
    AdsTripSpeedHourlyMetric,
    AdsTripSpeedHourlyResponse,
    AdsTripTimeslotDailyMetric,
    AdsTripTimeslotDailyResponse,
)
from schemas.data.common import MAX_STAT_DATE, MIN_STAT_DATE
from services.data.ads import AdsDataService

router = APIRouter(prefix="/data/ads", tags=["data-ads"])


def date_query():
    return Query(
        ...,
        alias="date",
        ge=MIN_STAT_DATE,
        le=MAX_STAT_DATE,
        description="统计日期，范围 2015-01-03 到 2015-01-08",
    )


@router.get("/network-status/hourly", response_model=ResponseBase[AdsNetworkStatusHourlyResponse])
def list_network_status_hourly(stat_date: date = date_query(), session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsNetworkStatusHourlyResponse(
                items=[
                    AdsNetworkStatusHourlyMetric(**item)
                    for item in service.list_network_status_hourly(stat_date)
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/congestion/hourly", response_model=ResponseBase[AdsCongestionHourlyResponse])
def list_congestion_hourly(stat_date: date = date_query(), session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsCongestionHourlyResponse(
                items=[
                    AdsCongestionHourlyMetric(**item)
                    for item in service.list_congestion_hourly(stat_date)
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/top-congested-roads", response_model=ResponseBase[AdsTopCongestedRoadsResponse])
def list_top_congested_roads(
    stat_date: date = date_query(),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsTopCongestedRoadsResponse(
                items=[
                    AdsTopCongestedRoadMetric(**item)
                    for item in service.list_top_congested_roads(stat_date, hour, limit)
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/trips/distance/hourly", response_model=ResponseBase[AdsTripDistanceHourlyResponse])
def list_trip_distance_hourly(stat_date: date = date_query(), session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsTripDistanceHourlyResponse(
                items=[
                    AdsTripDistanceHourlyMetric(**item)
                    for item in service.list_trip_distance_hourly(stat_date)
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/trips/distance/daily", response_model=ResponseBase[AdsTripDistanceDailyResponse])
def list_trip_distance_daily(session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsTripDistanceDailyResponse(
                items=[AdsTripDistanceDailyMetric(**item) for item in service.list_trip_distance_daily()]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/trips/speed/hourly", response_model=ResponseBase[AdsTripSpeedHourlyResponse])
def list_trip_speed_hourly(stat_date: date = date_query(), session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsTripSpeedHourlyResponse(
                items=[
                    AdsTripSpeedHourlyMetric(**item)
                    for item in service.list_trip_speed_hourly(stat_date)
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/trips/speed/daily", response_model=ResponseBase[AdsTripSpeedDailyResponse])
def list_trip_speed_daily(session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsTripSpeedDailyResponse(
                items=[AdsTripSpeedDailyMetric(**item) for item in service.list_trip_speed_daily()]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/trips/timeslot/daily", response_model=ResponseBase[AdsTripTimeslotDailyResponse])
def list_trip_timeslot_daily(session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsTripTimeslotDailyResponse(
                items=[AdsTripTimeslotDailyMetric(**item) for item in service.list_trip_timeslot_daily()]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/monitor/daily", response_model=ResponseBase[AdsHotspotMonitorDailyResponse])
def list_hotspot_monitor_daily(
    stat_date: Optional[date] = Query(None, alias="date", ge=MIN_STAT_DATE, le=MAX_STAT_DATE, description="统计日期"),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时"),
    time_mode: Literal["all", "day", "hour"] = Query("day", description="时间口径"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsHotspotMonitorDailyResponse(
                items=[
                    AdsHotspotMonitorDailyMetric(**item)
                    for item in service.list_hotspot_monitor(
                        time_mode=time_mode, stat_date=stat_date, hour=hour
                    )
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/roads/status/hourly", response_model=ResponseBase[AdsRoadStatusHourlyListResponse])
def list_road_status_hourly(
    stat_date: date = date_query(),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    status: Optional[Literal["畅通", "缓行", "拥堵", "严重拥堵"]] = Query(None, description="路况状态"),
    road_id: Optional[int] = Query(None, description="道路 ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        total, items = service.list_road_status_hourly(
            stat_date=stat_date,
            hour=hour,
            status=status,
            road_id=road_id,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=AdsRoadStatusHourlyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[AdsRoadStatusHourlyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/district/hourly", response_model=ResponseBase[AdsHotspotDistrictHourlyResponse])
def list_hotspot_district_hourly(
    stat_date: date = date_query(),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时，不填返回全天"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsHotspotDistrictHourlyResponse(
                items=[
                    AdsHotspotDistrictHourlyMetric(**item)
                    for item in service.list_hotspot_district_hourly(stat_date, hour)
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/district/daily", response_model=ResponseBase[AdsHotspotDistrictDailyResponse])
def list_hotspot_district_daily(stat_date: date = date_query(), session=Depends(get_session)):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsHotspotDistrictDailyResponse(
                items=[
                    AdsHotspotDistrictDailyMetric(**item)
                    for item in service.list_hotspot_district_daily(stat_date)
                ]
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/grid/hourly", response_model=ResponseBase[AdsHotspotGridHourlyListResponse])
def list_hotspot_grid_hourly(
    stat_date: date = date_query(),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    min_trip_count: Optional[int] = Query(None, ge=1, description="最小行程数"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        total, items = service.list_hotspot_grid_hourly(
            stat_date=stat_date,
            hour=hour,
            min_trip_count=min_trip_count,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=AdsHotspotGridHourlyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[AdsHotspotGridHourlyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/grid/daily", response_model=ResponseBase[AdsHotspotGridDailyListResponse])
def list_hotspot_grid_daily(
    stat_date: date = date_query(),
    min_trip_count: Optional[int] = Query(None, ge=1, description="最小行程数"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        total, items = service.list_hotspot_grid_daily(
            stat_date=stat_date,
            min_trip_count=min_trip_count,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=AdsHotspotGridDailyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[AdsHotspotGridDailyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/cluster/hourly", response_model=ResponseBase[AdsHotspotClusterHourlyListResponse])
def list_hotspot_cluster_hourly(
    stat_date: date = date_query(),
    hour: int = Query(..., ge=0, le=23, description="小时"),
    cluster_type: Optional[str] = Query(None, description="聚类类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        total, items = service.list_hotspot_cluster_hourly(
            stat_date=stat_date,
            hour=hour,
            cluster_type=cluster_type,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=AdsHotspotClusterHourlyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[AdsHotspotClusterHourlyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/cluster/daily", response_model=ResponseBase[AdsHotspotClusterDailyListResponse])
def list_hotspot_cluster_daily(
    stat_date: date = date_query(),
    cluster_type: Optional[str] = Query(None, description="聚类类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        total, items = service.list_hotspot_cluster_daily(
            stat_date=stat_date,
            cluster_type=cluster_type,
            page=page,
            page_size=page_size,
        )
        return ResponseBase(
            data=AdsHotspotClusterDailyListResponse(
                total=total,
                page=page,
                page_size=page_size,
                items=[AdsHotspotClusterDailyMetric(**item) for item in items],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/poi/hourly", response_model=ResponseBase[AdsHotspotPoiHourlyListResponse])
def list_hotspot_poi_hourly(
    stat_date: date = date_query(),
    hour: Optional[int] = Query(None, ge=0, le=23, description="小时，不填返回全天"),
    zone_id: Optional[str] = Query(None, description="POI ID"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsHotspotPoiHourlyListResponse(
                total=0,
                page=1,
                page_size=0,
                items=[
                    AdsHotspotPoiHourlyMetric(**item)
                    for item in service.list_hotspot_poi_hourly(stat_date, hour, zone_id)
                ],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")


@router.get("/hotspots/poi/daily", response_model=ResponseBase[AdsHotspotPoiDailyListResponse])
def list_hotspot_poi_daily(
    stat_date: date = date_query(),
    zone_id: Optional[str] = Query(None, description="POI ID"),
    session=Depends(get_session),
):
    try:
        service = AdsDataService(session)
        return ResponseBase(
            data=AdsHotspotPoiDailyListResponse(
                total=0,
                page=1,
                page_size=0,
                items=[AdsHotspotPoiDailyMetric(**item) for item in service.list_hotspot_poi_daily(stat_date, zone_id)],
            )
        )
    except Exception as e:
        return ResponseBase(code=500, message=f"查询失败: {str(e)}")