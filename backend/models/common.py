"""Common response envelope models for the Momentum Compass API.

Every API response is wrapped in ApiResponse with data + meta fields.
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    """Metadata included in every API response."""

    timestamp: datetime
    count: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    All endpoints return data wrapped in this format:
    {"data": ..., "meta": {"timestamp": ..., "count": ...}}
    """

    data: T
    meta: Meta
