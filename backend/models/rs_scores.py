"""Pydantic v2 models for RS score, ranking, and RRG API responses."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RSScoreResponse(BaseModel):
    """Full RS score record for an instrument on a given date."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    date: datetime.date
    rs_line: Decimal | None = None
    rs_ma_150: Decimal | None = None
    rs_trend: str | None = None
    rs_pct_1m: Decimal | None = None
    rs_pct_3m: Decimal | None = None
    rs_pct_6m: Decimal | None = None
    rs_pct_12m: Decimal | None = None
    rs_composite: Decimal | None = None
    rs_momentum: Decimal | None = None
    volume_ratio: Decimal | None = None
    vol_multiplier: Decimal | None = None
    adjusted_rs_score: Decimal | None = None
    quadrant: str | None = None
    liquidity_tier: int | None = None
    extension_warning: bool = False
    regime: str = "RISK_ON"


class RankingItem(BaseModel):
    """Single item in a ranking list."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    name: str
    adjusted_rs_score: Decimal | None = None
    quadrant: str | None = None
    rs_momentum: Decimal | None = None
    volume_ratio: Decimal | None = None
    rs_trend: str | None = None
    rs_pct_1m: Decimal | None = None
    rs_pct_3m: Decimal | None = None
    rs_pct_6m: Decimal | None = None
    rs_pct_12m: Decimal | None = None
    liquidity_tier: int | None = None
    extension_warning: bool = False


class RankingResponse(BaseModel):
    """Ranked list of instruments by RS score."""

    items: list[RankingItem]


class RRGTrailPoint(BaseModel):
    """Single point in an RRG trail (historical position)."""

    date: datetime.date
    rs_score: Decimal
    rs_momentum: Decimal


class RRGDataPoint(BaseModel):
    """Single instrument plotted on the RRG scatter chart."""

    id: str
    name: str
    rs_score: Decimal
    rs_momentum: Decimal
    quadrant: str | None = None
    trail: list[RRGTrailPoint] = []


class RRGResponse(BaseModel):
    """RRG scatter data for a set of instruments."""

    items: list[RRGDataPoint]
