"""Pydantic v2 models for basket API requests and responses."""

import datetime
import uuid
from decimal import Decimal

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
    weight: Decimal


class BasketPositionResponse(BaseModel):
    """Response for a single basket position."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    basket_id: uuid.UUID
    instrument_id: str
    weight: Decimal
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
    nav: Decimal
    benchmark_nav: Decimal | None = None
    rs_line: Decimal | None = None


class BasketPerformanceResponse(BaseModel):
    """Performance metrics for a basket."""

    model_config = ConfigDict(from_attributes=True)

    basket_id: uuid.UUID
    cumulative_return: Decimal
    cagr: Decimal | None = None
    max_drawdown: Decimal
    sharpe_ratio: Decimal | None = None
    pct_weeks_outperforming: Decimal | None = None
