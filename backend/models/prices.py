"""Pydantic v2 models for price data API responses."""

import datetime



from pydantic import BaseModel, ConfigDict


class PriceResponse(BaseModel):
    """Single OHLCV price record."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    date: datetime.date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: int | None = None


class PriceHistoryResponse(BaseModel):
    """Historical price data for an instrument."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    prices: list[PriceResponse]
