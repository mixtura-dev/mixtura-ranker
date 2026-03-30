"""
Общие модели и типы данных.
"""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

from .responses import ErrorResponse

T = TypeVar("T", covariant=True)


class ResponseMessage(BaseModel, Generic[T]):
    status: int = Field(..., description="HTTP-подобный код статуса (200 = успех)")
    message: T | ErrorResponse = Field(..., description="Полезная нагрузка")
