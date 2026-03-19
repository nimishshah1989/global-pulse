"""RRG repository -- scatter plot data with trailing tails.

Queries real rs_scores for trailing tail data. Returns empty list if
no real data exists — never generates mock/fake scores.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, RSScore
from repositories.instrument_repo import InstrumentRepository
from repositories.ranking_repo import (
    CANONICAL_COUNTRY_INDICES, CANONICAL_SECTORS, CANONICAL_GLOBAL_SECTORS,
    _resolve_action,
)

logger = logging.getLogger(__name__)


def _build_rrg_from_db(
    instrument: Instrument,
    scores: list[RSScore],
) -> dict[str, Any]:
    """Build RRG data point from real DB scores with trailing tail."""
    latest = scores[0]  # most recent
    rs_score = float(latest.adjusted_rs_score) if latest.adjusted_rs_score is not None else 50.0
    rs_momentum = float(latest.rs_momentum) if latest.rs_momentum is not None else 0.0
    raw_quadrant = latest.quadrant or "WATCH"
    action = _resolve_action(raw_quadrant, rs_score)

    # Volume character
    vol_ratio = float(latest.volume_ratio) if latest.volume_ratio is not None else 1.0
    if vol_ratio >= 1.3:
        volume_character = "ACCUMULATION"
    elif vol_ratio <= 0.7:
        volume_character = "DISTRIBUTION"
    else:
        volume_character = "NEUTRAL"

    # Build trail from historical scores (weekly samples)
    trail: list[dict[str, Any]] = []
    for s in scores:
        trail.append({
            "date": s.date,
            "rs_score": float(s.adjusted_rs_score) if s.adjusted_rs_score is not None else 50.0,
            "rs_momentum": float(s.rs_momentum) if s.rs_momentum is not None else 0.0,
        })

    trail.reverse()  # oldest first

    return {
        "id": instrument.id,
        "name": instrument.name,
        "rs_score": rs_score,
        "rs_momentum": rs_momentum,
        "action": action,
        "volume_character": volume_character,
        "trail": trail,
    }


class RRGRepository:
    """Repository for RRG scatter plot data with trailing tails."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._instrument_repo = InstrumentRepository(session)

    async def _get_rrg_by_filters(
        self,
        hierarchy_level: int | None = None,
        country: str | None = None,
        asset_types: tuple[str, ...] | None = None,
        sector: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get RRG data from DB by instrument filters. Returns empty list if no data."""
        if self._session is None:
            return []
        try:
            inst_stmt = select(Instrument).where(Instrument.is_active == True)
            if hierarchy_level is not None:
                inst_stmt = inst_stmt.where(Instrument.hierarchy_level == hierarchy_level)
            if country is not None:
                inst_stmt = inst_stmt.where(Instrument.country == country)
            if asset_types is not None:
                inst_stmt = inst_stmt.where(Instrument.asset_type.in_(asset_types))
            if sector is not None:
                inst_stmt = inst_stmt.where(Instrument.sector == sector)

            inst_result = await self._session.execute(inst_stmt)
            instruments = inst_result.scalars().all()
            if not instruments:
                return []

            max_date_result = await self._session.execute(
                select(func.max(RSScore.date))
            )
            max_date = max_date_result.scalar()
            if max_date is None:
                return []

            cutoff = max_date - timedelta(days=60)  # ~8 weeks

            results = []
            for inst in instruments:
                score_stmt = (
                    select(RSScore)
                    .where(RSScore.instrument_id == inst.id)
                    .where(RSScore.date >= cutoff)
                    .order_by(RSScore.date.desc())
                )
                score_result = await self._session.execute(score_stmt)
                scores = list(score_result.scalars().all())
                if not scores:
                    continue

                weekly_scores = scores[::5][:8]
                if not weekly_scores:
                    continue

                results.append(_build_rrg_from_db(inst, weekly_scores))

            return results

        except Exception as e:
            logger.debug("DB RRG query failed: %s", e)
            return []

    async def _get_rrg_by_ids(
        self, instrument_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Get RRG data for specific instrument IDs from DB."""
        if self._session is None:
            return []
        try:
            inst_stmt = (
                select(Instrument)
                .where(Instrument.is_active == True)
                .where(Instrument.id.in_(instrument_ids))
            )
            inst_result = await self._session.execute(inst_stmt)
            instruments = inst_result.scalars().all()
            if not instruments:
                return []

            max_date_result = await self._session.execute(
                select(func.max(RSScore.date))
            )
            max_date = max_date_result.scalar()
            if max_date is None:
                return []

            cutoff = max_date - timedelta(days=60)
            results = []
            for inst in instruments:
                score_stmt = (
                    select(RSScore)
                    .where(RSScore.instrument_id == inst.id)
                    .where(RSScore.date >= cutoff)
                    .order_by(RSScore.date.desc())
                )
                score_result = await self._session.execute(score_stmt)
                scores = list(score_result.scalars().all())
                if not scores:
                    continue
                weekly_scores = scores[::5][:8]
                if not weekly_scores:
                    continue
                results.append(_build_rrg_from_db(inst, weekly_scores))

            return results
        except Exception as e:
            logger.debug("DB RRG by IDs query failed: %s", e)
            return []

    async def get_country_rrg(self) -> list[dict[str, Any]]:
        """Return RRG data for canonical country indices."""
        return await self._get_rrg_by_ids(CANONICAL_COUNTRY_INDICES)

    async def get_sector_rrg(self, country_code: str) -> list[dict[str, Any]]:
        """Return RRG data for sectors within a country."""
        canonical_ids = CANONICAL_SECTORS.get(country_code)
        if canonical_ids is not None:
            return await self._get_rrg_by_ids(canonical_ids)

        return await self._get_rrg_by_filters(
            country=country_code,
            asset_types=("sector_etf", "sector_index"),
        )

    async def get_stock_rrg(
        self, country_code: str, sector: str,
    ) -> list[dict[str, Any]]:
        """Return RRG data for stocks in a country+sector."""
        return await self._get_rrg_by_filters(
            country=country_code, sector=sector,
            asset_types=("stock",),
        )
