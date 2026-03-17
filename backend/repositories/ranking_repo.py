"""Ranking repository -- RS score queries for rankings.

Generates deterministic mock RS scores until the real RS engine is connected.
Uses instrument ID as the hash seed so scores are stable across requests.
"""

import hashlib
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


def _mock_rs_scores(instrument: dict[str, Any]) -> dict[str, Any]:
    """Generate realistic mock RS scores for an instrument."""
    iid = instrument["id"]

    # Adjusted RS score: 20-90 range
    raw = _seed_float(iid, "score")
    adjusted_rs_score = Decimal(str(round(20 + raw * 70, 2)))

    # RS momentum: -30 to +30
    mom_raw = _seed_float(iid, "momentum")
    rs_momentum = Decimal(str(round(-30 + mom_raw * 60, 2)))

    quadrant = _determine_quadrant(adjusted_rs_score, rs_momentum)

    # Volume ratio: 0.5 to 2.0
    vol_raw = _seed_float(iid, "volume")
    volume_ratio = Decimal(str(round(0.5 + vol_raw * 1.5, 3)))

    # RS trend
    rs_trend = "OUTPERFORMING" if adjusted_rs_score > 50 else "UNDERPERFORMING"

    # Percentile fields: 0-100
    rs_pct_1m = Decimal(str(round(_seed_float(iid, "1m") * 100, 2)))
    rs_pct_3m = Decimal(str(round(_seed_float(iid, "3m") * 100, 2)))
    rs_pct_6m = Decimal(str(round(_seed_float(iid, "6m") * 100, 2)))
    rs_pct_12m = Decimal(str(round(_seed_float(iid, "12m") * 100, 2)))

    # Extension warning
    extension_warning = (
        rs_pct_3m > 95 and rs_pct_6m > 95 and rs_pct_12m > 90
    )

    liquidity_tier = instrument.get("liquidity_tier", 2)

    return {
        "instrument_id": iid,
        "name": instrument["name"],
        "adjusted_rs_score": adjusted_rs_score,
        "quadrant": quadrant,
        "rs_momentum": rs_momentum,
        "volume_ratio": volume_ratio,
        "rs_trend": rs_trend,
        "rs_pct_1m": rs_pct_1m,
        "rs_pct_3m": rs_pct_3m,
        "rs_pct_6m": rs_pct_6m,
        "rs_pct_12m": rs_pct_12m,
        "liquidity_tier": liquidity_tier,
        "extension_warning": extension_warning,
    }


class RankingRepository:
    """Repository for RS score rankings, backed by mock data."""

    def __init__(self, session: Any = None) -> None:
        """Initialize with an instrument repository for data access."""
        self._instrument_repo = InstrumentRepository(session)

    async def get_country_rankings(self) -> list[dict[str, Any]]:
        """Return Level 1 country index instruments with mock RS scores."""
        instruments = await self._instrument_repo.get_all(
            filters={"hierarchy_level": 1}
        )
        # Only country indices (not benchmarks or country ETFs)
        country_indices = [
            i for i in instruments
            if i.get("asset_type") == "country_index"
        ]
        return sorted(
            [_mock_rs_scores(i) for i in country_indices],
            key=lambda x: x["adjusted_rs_score"],
            reverse=True,
        )

    async def get_sector_rankings(self, country_code: str) -> list[dict[str, Any]]:
        """Return Level 2 sector instruments for a country with mock RS scores."""
        instruments = await self._instrument_repo.get_by_country(country_code)
        sectors = [
            i for i in instruments
            if i.get("hierarchy_level") == 2
        ]
        return sorted(
            [_mock_rs_scores(i) for i in sectors],
            key=lambda x: x["adjusted_rs_score"],
            reverse=True,
        )

    async def get_stock_rankings(
        self, country_code: str, sector: str
    ) -> list[dict[str, Any]]:
        """Return Level 3 stock instruments for a country+sector with mock RS scores.

        Since the instrument_map.json does not yet contain Level 3 stocks,
        this returns an empty list until stock data is seeded.
        """
        instruments = await self._instrument_repo.get_by_country(country_code)
        stocks = [
            i for i in instruments
            if i.get("hierarchy_level") == 3 and i.get("sector") == sector
        ]
        return sorted(
            [_mock_rs_scores(i) for i in stocks],
            key=lambda x: x["adjusted_rs_score"],
            reverse=True,
        )

    async def get_global_sector_rankings(self) -> list[dict[str, Any]]:
        """Return global sector ETF instruments with mock RS scores."""
        instruments = await self._instrument_repo.get_all(
            filters={"asset_type": "global_sector_etf"}
        )
        return sorted(
            [_mock_rs_scores(i) for i in instruments],
            key=lambda x: x["adjusted_rs_score"],
            reverse=True,
        )
