"""Pydantic v2 models for price data API responses."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceResponse(BaseModel):
    """Single OHLCV price record."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    date: datetime.date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal
    volume: int | None = None


class PriceHistoryResponse(BaseModel):
    """Historical price data for an instrument."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    prices: list[PriceResponse]
