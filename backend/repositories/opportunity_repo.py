"""Opportunity repository — DB-backed, no mock fallback.

Reads opportunity signals from the opportunities table. Returns empty
list if no real data exists.
"""
from __future__ import annotations

import datetime
import json
import logging
import uuid
from typing import Any

from sqlalchemy import select, desc
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


class OpportunityRepository:
    """Repository for opportunity signals — real data only."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def get_latest(
        self,
        limit: int = 50,
        signal_type: str | None = None,
        min_conviction: float | None = None,
        hierarchy_level: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve latest opportunity signals with optional filters."""
        if self._session is None:
            return []
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
            return [_opportunity_to_dict(r) for r in rows]
        except Exception as e:
            logger.debug("DB opportunity query failed: %s", e)
            return []

    async def get_multi_level_alignments(
        self, limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve only multi-level alignment signals."""
        if self._session is None:
            return []
        try:
            stmt = (
                select(Opportunity)
                .where(Opportunity.signal_type == "multi_level_alignment")
                .order_by(desc(Opportunity.conviction_score))
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            rows = result.scalars().all()
            return [_opportunity_to_dict(r) for r in rows]
        except Exception as e:
            logger.debug("DB multi-level query failed: %s", e)
            return []
