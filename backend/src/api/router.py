from fastapi import APIRouter

from api.data.ads import router as data_ads_router
from api.data.network import router as data_network_router
from api.data.nodes import router as data_nodes_router
from api.data.od import router as data_od_router
from api.data.poi import router as data_poi_router
from api.data.roads import router as data_roads_router
from api.data.tdm import router as data_tdm_router
from api.data.trips import router as data_trips_router
from api.heartbeat import router as heartbeat_router
from api.map_data import router as map_data_router
from api.metadata import router as metadata_router
from api.pages.congestion import router as page_congestion_router
from api.pages.dashboard import router as page_dashboard_router
from api.pages.hotspot import router as page_hotspot_router
from api.pages.road_status import router as page_road_status_router
from api.pages.trajectory import router as page_trajectory_router
from api.pages.trip_features import router as page_trip_features_router
from api.roads import router as roads_router
from api.version import router as version_router

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Data Platform Backend API is running."}


router.include_router(heartbeat_router)
router.include_router(version_router)
router.include_router(metadata_router)
router.include_router(data_ads_router)
router.include_router(data_network_router)
router.include_router(data_roads_router)
router.include_router(data_nodes_router)
router.include_router(data_trips_router)
router.include_router(data_od_router)
router.include_router(data_poi_router)
router.include_router(data_tdm_router)
router.include_router(roads_router)
router.include_router(map_data_router)
router.include_router(page_dashboard_router)
router.include_router(page_road_status_router)
router.include_router(page_congestion_router)
router.include_router(page_hotspot_router)
router.include_router(page_trip_features_router)
router.include_router(page_trajectory_router)