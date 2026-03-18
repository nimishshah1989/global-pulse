"""Opportunity repository — DB-backed with mock fallback.

Reads opportunity signals from the opportunities table. Falls back to
deterministic mock data if the DB has no data.
"""

import datetime
import json
import logging
import uuid
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Opportunity

logger = logging.getLogger(__name__)


def _parse_metadata(raw: Any) -> dict[str, Any]:
    """Parse metadata from DB — may be JSON string or dict."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _opportunity_to_dict(opp: Opportunity) -> dict[str, Any]:
    """Convert an Opportunity ORM model to a response dict."""
    meta = _parse_metadata(opp.metadata_)
    return {
        "id": uuid.UUID(opp.id) if isinstance(opp.id, str) else opp.id,
        "instrument_id": opp.instrument_id,
        "instrument_name": meta.get("instrument_name", opp.instrument_id),
        "date": opp.date,
        "signal_type": opp.signal_type,
        "conviction_score": float(opp.conviction_score) if opp.conviction_score is not None else None,
        "description": opp.description,
        "metadata": meta,
        "created_at": opp.created_at or datetime.datetime.now(tz=datetime.timezone.utc),
    }


def _make_mock_opportunity(
    instrument_id: str,
    instrument_name: str,
    signal_type: str,
    conviction_score: float,
    description: str,
    metadata: dict[str, Any] | None = None,
    days_ago: int = 0,
) -> dict[str, Any]:
    """Build a single mock opportunity dict."""
    today = datetime.date(2026, 3, 17)
    signal_date = today - datetime.timedelta(days=days_ago)
    return {
        "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"{instrument_id}-{signal_type}-{days_ago}"),
        "instrument_id": instrument_id,
        "instrument_name": instrument_name,
        "date": signal_date,
        "signal_type": signal_type,
        "conviction_score": conviction_score,
        "description": description,
        "metadata": metadata or {},
        "created_at": datetime.datetime(
            signal_date.year, signal_date.month, signal_date.day,
            2, 0, 0, tzinfo=datetime.timezone.utc,
        ),
    }


def _build_mock_opportunities() -> list[dict[str, Any]]:
    """Create a pre-populated set of realistic mock opportunities."""
    return [
        _make_mock_opportunity(
            "EWJ_US", "iShares MSCI Japan", "quadrant_entry_leading", 78.50,
            "EWJ_US entered LEADING quadrant (from IMPROVING)",
            {"previous_quadrant": "IMPROVING", "current_quadrant": "LEADING",
             "country": "JP"},
        ),
        _make_mock_opportunity(
            "XLK_US", "Technology Select Sector SPDR", "quadrant_entry_leading", 82.15,
            "XLK_US entered LEADING quadrant (from WEAKENING)",
            {"previous_quadrant": "WEAKENING", "current_quadrant": "LEADING",
             "country": "US", "sector": "technology"},
            days_ago=1,
        ),
        _make_mock_opportunity(
            "INDA_US", "iShares MSCI India", "volume_breakout", 74.25,
            "INDA_US RS turning positive with volume 1.8x average",
            {"rs_momentum": "5.20", "volume_ratio": "1.800", "country": "IN"},
        ),
        _make_mock_opportunity(
            "TATASTEEL_IN", "Tata Steel", "multi_level_alignment", 72.40,
            "India LEADING globally -> NIFTY Metal LEADING in India -> "
            "Tata Steel LEADING in NIFTY Metal",
            {
                "country": "India", "country_quadrant": "LEADING",
                "sector": "NIFTY Metal", "sector_quadrant": "LEADING",
                "stock": "Tata Steel", "stock_quadrant": "LEADING",
                "country_id": "NIFTY50_IN", "country_name": "India",
                "sector_id": "NIFTYMETAL_IN", "sector_name": "NIFTY Metal",
                "stock_id": "TATASTEEL_IN", "stock_name": "Tata Steel",
            },
        ),
        _make_mock_opportunity(
            "NVDA_US", "NVIDIA Corp", "multi_level_alignment", 91.00,
            "US LEADING globally -> Technology LEADING in US -> "
            "NVIDIA LEADING in Technology",
            {
                "country": "United States", "country_quadrant": "LEADING",
                "sector": "Technology", "sector_quadrant": "LEADING",
                "stock": "NVIDIA Corp", "stock_quadrant": "LEADING",
                "country_id": "SPX", "country_name": "United States",
                "sector_id": "XLK_US", "sector_name": "Technology",
                "stock_id": "NVDA_US", "stock_name": "NVIDIA Corp",
            },
        ),
        _make_mock_opportunity(
            "ACWI", "MSCI ACWI", "regime_change", 95.00,
            "Global regime changed to RISK_OFF — ACWI crossed below 200-day MA",
            {"previous_regime": "RISK_ON", "current_regime": "RISK_OFF"},
            days_ago=5,
        ),
        _make_mock_opportunity(
            "XLK_US", "Technology Select Sector SPDR", "extension_alert", 88.50,
            "XLK_US extended — RS in top 5% across all timeframes",
            {"rs_pct_3m": "97.20", "rs_pct_6m": "96.80", "rs_pct_12m": "93.10",
             "country": "US", "sector": "technology"},
        ),
    ]


class OpportunityRepository:
    """Repository for opportunity signals, DB-backed with mock fallback."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize with an optional DB session."""
        self._session = session
        self._mock_opportunities: list[dict[str, Any]] | None = None

    def _get_mock(self) -> list[dict[str, Any]]:
        """Lazy-load mock opportunities."""
        if self._mock_opportunities is None:
            self._mock_opportunities = _build_mock_opportunities()
        return self._mock_opportunities

    async def get_latest(
        self,
        limit: int = 50,
        signal_type: str | None = None,
        min_conviction: float | None = None,
        hierarchy_level: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve latest opportunity signals with optional filters."""
        # Try DB first
        if self._session is not None:
            try:
                stmt = select(Opportunity).order_by(
                    desc(Opportunity.date),
                    desc(Opportunity.conviction_score),
                )
                if signal_type is not None:
                    stmt = stmt.where(Opportunity.signal_type == signal_type)
                if min_conviction is not None:
                    stmt = stmt.where(Opportunity.conviction_score >= min_conviction)
                stmt = stmt.limit(limit)

                result = await self._session.execute(stmt)
                rows = result.scalars().all()
                if rows:
                    return [_opportunity_to_dict(r) for r in rows]
            except Exception as e:
                logger.debug("DB opportunity query failed: %s", e)

        # Mock fallback
        results = list(self._get_mock())
        if signal_type is not None:
            results = [o for o in results if o["signal_type"] == signal_type]
        if min_conviction is not None:
            results = [o for o in results if (o["conviction_score"] or 0) >= min_conviction]
        results.sort(key=lambda o: (o["date"], o["conviction_score"] or 0), reverse=True)
        return results[:limit]

    async def get_multi_level_alignments(
        self, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Retrieve only multi-level alignment signals."""
        if self._session is not None:
            try:
                stmt = (
                    select(Opportunity)
                    .where(Opportunity.signal_type == "multi_level_alignment")
                    .order_by(desc(Opportunity.conviction_score))
                    .limit(limit)
                )
                result = await self._session.execute(stmt)
                rows = result.scalars().all()
                if rows:
                    return [_opportunity_to_dict(r) for r in rows]
            except Exception as e:
                logger.debug("DB multi-level query failed: %s", e)

        # Mock fallback
        results = [
            o for o in self._get_mock()
            if o["signal_type"] == "multi_level_alignment"
        ]
        results.sort(key=lambda o: o["conviction_score"] or 0, reverse=True)
        return results[:limit]
