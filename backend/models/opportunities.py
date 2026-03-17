"""Pydantic v2 models for opportunity signal API responses."""

import datetime
import enum
import uuid

from pydantic import BaseModel, ConfigDict


class SignalType(str, enum.Enum):
    """Valid signal types for opportunity detection."""

    QUADRANT_ENTRY_LEADING = "quadrant_entry_leading"
    QUADRANT_ENTRY_IMPROVING = "quadrant_entry_improving"
    VOLUME_BREAKOUT = "volume_breakout"
    MULTI_LEVEL_ALIGNMENT = "multi_level_alignment"
    BEARISH_DIVERGENCE = "bearish_divergence"
    BULLISH_DIVERGENCE = "bullish_divergence"
    REGIME_CHANGE = "regime_change"
    EXTENSION_ALERT = "extension_alert"


class OpportunityResponse(BaseModel):
    """Single opportunity signal."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instrument_id: str
    date: datetime.date
    signal_type: str
    conviction_score: float | None = None
    description: str | None = None
    metadata: dict | None = None
    created_at: datetime.datetime


class MultiLevelAlignmentResponse(BaseModel):
    """Multi-level alignment signal showing the full country > sector > stock chain."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    date: datetime.date
    conviction_score: float | None = None
    description: str | None = None

    # The alignment chain
    country_id: str
    country_name: str
    country_quadrant: str

    sector_id: str
    sector_name: str
    sector_quadrant: str

    stock_id: str
    stock_name: str
    stock_quadrant: str
