from datetime import date

from pydantic import BaseModel

MIN_STAT_DATE = date(2015, 1, 3)
MAX_STAT_DATE = date(2015, 1, 8)


class PageResponse(BaseModel):
    """Common pagination fields."""

    total: int
    page: int
    page_size: int
