"""Pydantic v2 models for RS v2 API responses.

RS v2 uses 3 indicators (Price Trend, Momentum, OBV) and an 8-action matrix.
"""
from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict


class RankingItemV2(BaseModel):
    """Single item in a v2 ranking list."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    name: str
    country: str | None = None
    sector: str | None = None
    asset_type: str | None = None
    # Indicator 1: Price Trend
    rs_line: float | None = None
    rs_ma: float | None = None
    price_trend: str | None = None
    # Indicator 2: Momentum
    rs_momentum_pct: float | None = None
    momentum_trend: str | None = None
    # Indicator 3: OBV
    volume_character: str | None = None
    # Action
    action: str = "WATCH"
    # Score for sorting (0-100)
    rs_score: float = 50.0
    # Regime
    regime: str = "RISK_ON"

    # Legacy compatibility fields (map new to old for smooth transition)
    @property
    def adjusted_rs_score(self) -> float:
        return self.rs_score

    @property
    def quadrant(self) -> str:
        return self.action

    @property
    def rs_momentum(self) -> float:
        return self.rs_momentum_pct or 0.0


# Keep old model name as alias for import compatibility
RankingItem = RankingItemV2


class RSScoreResponse(BaseModel):
    """Full RS score record for an instrument on a given date."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    date: datetime.date
    rs_line: float | None = None
    rs_ma: float | None = None
    price_trend: str | None = None
    rs_momentum_pct: float | None = None
    momentum_trend: str | None = None
    volume_character: str | None = None
    action: str = "WATCH"
    rs_score: float = 50.0
    regime: str = "RISK_ON"


class RRGTrailPoint(BaseModel):
    """Single point in an RRG trail (historical position)."""

    date: datetime.date
    rs_score: float
    rs_momentum: float


class RRGDataPoint(BaseModel):
    """Single instrument plotted on the RRG scatter chart."""

    id: str
    name: str
    rs_score: float
    rs_momentum: float
    action: str | None = None
    volume_character: str | None = None
    trail: list[RRGTrailPoint] = []


class RRGResponse(BaseModel):
    """RRG scatter data for a set of instruments."""

    items: list[RRGDataPoint]
