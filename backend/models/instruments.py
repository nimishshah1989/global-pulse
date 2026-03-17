"""Pydantic v2 models for instrument API requests and responses."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InstrumentBase(BaseModel):
    """Base instrument fields shared across create/update/response."""

    name: str
    ticker_stooq: str | None = None
    ticker_yfinance: str | None = None
    source: str
    asset_type: str
    country: str | None = None
    sector: str | None = None
    hierarchy_level: int
    benchmark_id: str | None = None
    currency: str = "USD"
    liquidity_tier: int | None = 2
    is_active: bool = True
    metadata: dict | None = None


class InstrumentResponse(InstrumentBase):
    """Full instrument response with ID."""

    model_config = ConfigDict(from_attributes=True)

    id: str


class InstrumentListResponse(BaseModel):
    """List of instruments returned by listing endpoints."""

    model_config = ConfigDict(from_attributes=True)

    items: list[InstrumentResponse]
    total: int
