"""RRG repository -- scatter plot data with trailing tails.

Generates deterministic mock RRG data with 8-week trailing tails
that simulate realistic rotation patterns through the four quadrants.
"""

import hashlib
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from repositories.instrument_repo import InstrumentRepository


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
    """Generate an 8-week trailing tail with realistic rotation patterns.

    The trail moves backward from the current position, simulating
    clockwise rotation through the RRG quadrants.
    """
    trail: list[dict[str, Any]] = []
    today = date(2026, 3, 17)

    # Rotation speed and direction seeded by instrument
    phase = _seed_float(instrument_id, "phase") * 2 * math.pi
    speed = 0.15 + _seed_float(instrument_id, "speed") * 0.25

    for week_offset in range(weeks):
        # Work backward from current position
        t = week_offset * speed
        # Small perturbation around current position going backward
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

    # Reverse so oldest is first
    trail.reverse()
    return trail


def _build_rrg_point(instrument: dict[str, Any]) -> dict[str, Any]:
    """Build a full RRG data point with trail for an instrument."""
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


class RRGRepository:
    """Repository for RRG scatter plot data with trailing tails."""

    def __init__(self, session: Any = None) -> None:
        """Initialize with an instrument repository for data access."""
        self._instrument_repo = InstrumentRepository(session)

    async def get_country_rrg(self) -> list[dict[str, Any]]:
        """Return RRG data for all country indices."""
        instruments = await self._instrument_repo.get_all(
            filters={"hierarchy_level": 1}
        )
        country_indices = [
            i for i in instruments if i.get("asset_type") == "country_index"
        ]
        return [_build_rrg_point(i) for i in country_indices]

    async def get_sector_rrg(self, country_code: str) -> list[dict[str, Any]]:
        """Return RRG data for sectors within a specific country."""
        instruments = await self._instrument_repo.get_by_country(country_code)
        sectors = [i for i in instruments if i.get("hierarchy_level") == 2]
        return [_build_rrg_point(i) for i in sectors]

    async def get_stock_rrg(
        self, country_code: str, sector: str
    ) -> list[dict[str, Any]]:
        """Return RRG data for stocks in a country+sector combination."""
        instruments = await self._instrument_repo.get_by_country(country_code)
        stocks = [
            i for i in instruments
            if i.get("hierarchy_level") == 3 and i.get("sector") == sector
        ]
        return [_build_rrg_point(i) for i in stocks]
