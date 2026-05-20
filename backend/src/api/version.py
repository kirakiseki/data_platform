import logging

from fastapi import APIRouter
from pydantic import BaseModel

from api.response import ResponseBase
from db.session import get_db_version

logger = logging.getLogger(__name__)

router = APIRouter()


class VersionResponse(BaseModel):
    database: str


@router.get("/version", response_model=ResponseBase[VersionResponse])
async def get_version():
    db_version = await get_db_version()

    return ResponseBase[VersionResponse](
        data=VersionResponse(
            database=db_version,
        ),
    )
