"""Pydantic v2 models for RS v2 API responses.

RS v2 uses 3-gate action engine matching MarketPulse exactly:
G1 (absolute return), G2 (RS score vs 50), G3 (momentum direction).
"""
from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict


class RankingItemV2(BaseModel):
    """Single item in a v2 ranking list — matches frontend RankingItem type."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    name: str
    country: str | None = None
    sector: str | None = None
    asset_type: str | None = None
    # RS data
    rs_score: float = 50.0
    rs_momentum: float | None = None
    # Quadrant (LEADING / WEAKENING / IMPROVING / LAGGING)
    quadrant: str | None = None
    # 3-gate action (BUY / HOLD / WATCH_EMERGING / WATCH_RELATIVE / WATCH_EARLY / AVOID / SELL)
    action: str = "HOLD"
    action_reason: str | None = None
    # Volume signal (ACCUMULATION / WEAK_RALLY / DISTRIBUTION / WEAK_DECLINE)
    volume_signal: str | None = None
    # Market regime (BULL / CAUTIOUS / CORRECTION / BEAR)
    regime: str = "BULL"
    # Absolute and relative returns (actual %)
    absolute_return: float | None = None
    relative_return: float | None = None
    # Period returns
    return_1m: float | None = None
    return_3m: float | None = None
    return_6m: float | None = None
    return_12m: float | None = None
    # Excess returns vs benchmark
    excess_1m: float | None = None
    excess_3m: float | None = None
    excess_6m: float | None = None
    excess_12m: float | None = None
    # Benchmark used
    benchmark_id: str | None = None


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
