from typing import Generic, Optional, TypeVar

from pydantic.generics import GenericModel

T = TypeVar("T")


# Public response model
class ResponseBase(GenericModel, Generic[T]):
    code: int = 0  # 0 indicates success, non-zero indicates error
    message: str = "success"  # "success" for success, error message for failure
    data: Optional[T] = None  # The actual response data, can be None
