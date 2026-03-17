"""Pydantic v2 models for basket API requests and responses."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class BasketCreate(BaseModel):
    """Request body for creating a new basket."""

    name: str
    description: str | None = None
    benchmark_id: str | None = None
    weighting_method: str = "equal"


class BasketPositionCreate(BaseModel):
    """Request body for adding a position to a basket."""

    instrument_id: str
    weight: float


class BasketPositionResponse(BaseModel):
    """Response for a single basket position."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    basket_id: uuid.UUID
    instrument_id: str
    weight: float
    added_at: datetime.datetime
    removed_at: datetime.datetime | None = None
    status: str = "active"


class BasketResponse(BaseModel):
    """Full basket detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    benchmark_id: str | None = None
    created_at: datetime.datetime
    status: str = "active"
    weighting_method: str = "equal"
    positions: list[BasketPositionResponse] = []


class BasketNAVResponse(BaseModel):
    """Single NAV data point for a basket."""

    model_config = ConfigDict(from_attributes=True)

    basket_id: uuid.UUID
    date: datetime.date
    nav: float
    benchmark_nav: float | None = None
    rs_line: float | None = None


class BasketPerformanceResponse(BaseModel):
    """Performance metrics for a basket."""

    model_config = ConfigDict(from_attributes=True)

    basket_id: uuid.UUID
    cumulative_return: float
    cagr: float | None = None
    max_drawdown: float
    sharpe_ratio: float | None = None
    pct_weeks_outperforming: float | None = None
