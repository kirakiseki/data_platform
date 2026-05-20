import logging

from fastapi import APIRouter
from pydantic import BaseModel

from api.response import ResponseBase
from db.session import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class HeartbeatResponse(BaseModel):
    health: bool
    database: dict


@router.get("/heartbeat", response_model=ResponseBase[HeartbeatResponse])
async def heartbeat():
    db_status, db_error = await check_database_connection()
    db_health = db_status if db_status else False

    return ResponseBase[HeartbeatResponse](
        data=HeartbeatResponse(
            health=db_health,
            database={"health": db_health, "error": db_error},
        ),
    )
