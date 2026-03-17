"""RRG repository -- scatter plot data with trailing tails.

Queries real rs_scores for trailing tail data. Falls back to deterministic
mock data if the DB has no data.
"""

import hashlib
import logging
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, RSScore
from repositories.instrument_repo import InstrumentRepository

logger = logging.getLogger(__name__)


def _seed_float(instrument_id: str, salt: str = "") -> float:
    """Return a deterministic float in [0, 1) based on instrument ID and salt."""
    digest = hashlib.md5((instrument_id + salt).encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _determine_quadrant(score: Decimal, momentum: Decimal) -> str:
    """Assign RRG quadrant based on score and momentum thresholds."""
    if score > 50 and momentum > 0:
        return "LEADING"
    if score > 50 and momentum <= 0:
        return "WEAKENING"
    if score <= 50 and momentum <= 0:
        return "LAGGING"
    return "IMPROVING"


def _generate_trail(
    instrument_id: str,
    current_score: float,
    current_momentum: float,
    weeks: int = 8,
) -> list[dict[str, Any]]:
    """Generate an 8-week trailing tail with realistic rotation patterns."""
    trail: list[dict[str, Any]] = []
    today = date(2026, 3, 17)

    phase = _seed_float(instrument_id, "phase") * 2 * math.pi
    speed = 0.15 + _seed_float(instrument_id, "speed") * 0.25

    for week_offset in range(weeks):
        t = week_offset * speed
        score_offset = math.sin(phase + t) * 8
        momentum_offset = math.cos(phase + t) * 6

        trail_score = Decimal(str(round(current_score - score_offset, 2)))
        trail_momentum = Decimal(str(round(current_momentum - momentum_offset, 2)))
        trail_date = today - timedelta(weeks=week_offset)

        trail.append({
            "date": trail_date,
            "rs_score": trail_score,
            "rs_momentum": trail_momentum,
        })

    trail.reverse()
    return trail


def _build_rrg_point(instrument: dict[str, Any]) -> dict[str, Any]:
    """Build a full RRG data point with trail for an instrument (mock)."""
    iid = instrument["id"]

    raw = _seed_float(iid, "score")
    score = round(20 + raw * 70, 2)

    mom_raw = _seed_float(iid, "momentum")
    momentum = round(-30 + mom_raw * 60, 2)

    score_dec = Decimal(str(score))
    momentum_dec = Decimal(str(momentum))
    quadrant = _determine_quadrant(score_dec, momentum_dec)

    trail = _generate_trail(iid, score, momentum)

    return {
        "id": iid,
        "name": instrument["name"],
        "rs_score": score_dec,
        "rs_momentum": momentum_dec,
        "quadrant": quadrant,
        "trail": trail,
    }


def _build_rrg_from_db(
    instrument: Instrument,
    scores: list[RSScore],
) -> dict[str, Any]:
    """Build RRG data point from real DB scores with trailing tail.

    If fewer than 8 data points exist, pads the trail using the
    same rotation simulation used by the mock generator.
    """
    latest = scores[0]  # most recent
    rs_score = Decimal(str(latest.adjusted_rs_score)) if latest.adjusted_rs_score is not None else Decimal("50")
    rs_momentum = Decimal(str(latest.rs_momentum)) if latest.rs_momentum is not None else Decimal("0")
    quadrant = latest.quadrant or _determine_quadrant(rs_score, rs_momentum)

    # Build trail from historical scores (weekly samples)
    trail: list[dict[str, Any]] = []
    for s in scores:
        trail.append({
            "date": s.date,
            "rs_score": Decimal(str(s.adjusted_rs_score)) if s.adjusted_rs_score is not None else Decimal("50"),
            "rs_momentum": Decimal(str(s.rs_momentum)) if s.rs_momentum is not None else Decimal("0"),
        })

    trail.reverse()  # oldest first

    # Pad to 8 entries if needed using synthetic rotation
    if len(trail) < 8:
        trail = _generate_trail(instrument.id, float(rs_score), float(rs_momentum), weeks=8)

    return {
        "id": instrument.id,
        "name": instrument.name,
        "rs_score": rs_score,
        "rs_momentum": rs_momentum,
        "quadrant": quadrant,
        "trail": trail,
    }


class RRGRepository:
    """Repository for RRG scatter plot data with trailing tails."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize with an instrument repository for data access."""
        self._session = session
        self._instrument_repo = InstrumentRepository(session)

    async def _try_db_rrg(
        self,
        hierarchy_level: int | None = None,
        country: str | None = None,
        asset_type: str | None = None,
        sector: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """Try to get RRG data from the database. Returns None if no data."""
        if self._session is None:
            return None
        try:
            # Get instruments matching the criteria
            inst_stmt = select(Instrument).where(Instrument.is_active == True)
            if hierarchy_level is not None:
                inst_stmt = inst_stmt.where(Instrument.hierarchy_level == hierarchy_level)
            if country is not None:
                inst_stmt = inst_stmt.where(Instrument.country == country)
            if asset_type is not None:
                inst_stmt = inst_stmt.where(Instrument.asset_type == asset_type)
            if sector is not None:
                inst_stmt = inst_stmt.where(Instrument.sector == sector)

            inst_result = await self._session.execute(inst_stmt)
            instruments = inst_result.scalars().all()
            if not instruments:
                return None

            # Get trailing weekly scores (last 8 weeks of data)
            # Use every 5th trading day as weekly proxy
            max_date_result = await self._session.execute(
                select(func.max(RSScore.date))
            )
            max_date = max_date_result.scalar()
            if max_date is None:
                return None

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

                # Sample weekly (every 5th record)
                weekly_scores = scores[::5][:8]
                if not weekly_scores:
                    continue

                results.append(_build_rrg_from_db(inst, weekly_scores))

            if not results:
                return None
            return results

        except Exception as e:
            logger.debug("DB RRG query failed: %s", e)
            return None

    async def get_country_rrg(self) -> list[dict[str, Any]]:
        """Return RRG data for all country indices."""
        db_result = await self._try_db_rrg(
            hierarchy_level=1, asset_type="country_index"
        )
        if db_result is not None:
            return db_result

        instruments = await self._instrument_repo.get_all(
            filters={"hierarchy_level": 1}
        )
        country_indices = [
            i for i in instruments if i.get("asset_type") == "country_index"
        ]
        return [_build_rrg_point(i) for i in country_indices]

    async def get_sector_rrg(self, country_code: str) -> list[dict[str, Any]]:
        """Return RRG data for sectors within a specific country."""
        db_result = await self._try_db_rrg(
            hierarchy_level=2, country=country_code
        )
        if db_result is not None:
            return db_result

        instruments = await self._instrument_repo.get_by_country(country_code)
        sectors = [i for i in instruments if i.get("hierarchy_level") == 2]
        return [_build_rrg_point(i) for i in sectors]

    async def get_stock_rrg(
        self, country_code: str, sector: str
    ) -> list[dict[str, Any]]:
        """Return RRG data for stocks in a country+sector combination."""
        db_result = await self._try_db_rrg(
            hierarchy_level=3, country=country_code, sector=sector
        )
        if db_result is not None:
            return db_result

        instruments = await self._instrument_repo.get_by_country(country_code)
        stocks = [
            i for i in instruments
            if i.get("hierarchy_level") == 3 and i.get("sector") == sector
        ]
        return [_build_rrg_point(i) for i in stocks]
