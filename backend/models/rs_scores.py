"""Pydantic v2 models for RS score, ranking, and RRG API responses.

Note: RS scores use float (not Decimal) for JSON serialization.
These are display scores (0-100), not currency values.
Decimal precision is maintained in the engine and database layers.
"""

import datetime

from pydantic import BaseModel, ConfigDict


class RSScoreResponse(BaseModel):
    """Full RS score record for an instrument on a given date."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    date: datetime.date
    rs_line: float | None = None
    rs_ma_150: float | None = None
    rs_trend: str | None = None
    rs_pct_1m: float | None = None
    rs_pct_3m: float | None = None
    rs_pct_6m: float | None = None
    rs_pct_12m: float | None = None
    rs_composite: float | None = None
    rs_momentum: float | None = None
    volume_ratio: float | None = None
    vol_multiplier: float | None = None
    adjusted_rs_score: float | None = None
    quadrant: str | None = None
    liquidity_tier: int | None = None
    extension_warning: bool = False
    regime: str = "RISK_ON"


class RankingItem(BaseModel):
    """Single item in a ranking list."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    name: str
    adjusted_rs_score: float | None = None
    quadrant: str | None = None
    rs_momentum: float | None = None
    volume_ratio: float | None = None
    rs_trend: str | None = None
    rs_pct_1m: float | None = None
    rs_pct_3m: float | None = None
    rs_pct_6m: float | None = None
    rs_pct_12m: float | None = None
    liquidity_tier: int | None = None
    extension_warning: bool = False


class RankingResponse(BaseModel):
    """Ranked list of instruments by RS score."""

    items: list[RankingItem]


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
    quadrant: str | None = None
    trail: list[RRGTrailPoint] = []


class RRGResponse(BaseModel):
    """RRG scatter data for a set of instruments."""

    items: list[RRGDataPoint]
