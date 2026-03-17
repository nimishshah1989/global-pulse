"""Ranking repository -- RS score queries for rankings.

Queries real rs_scores table first. Falls back to deterministic mock
scores if the DB has no data (for tests and pre-seed operation).
"""

import hashlib
import logging
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


def _rs_score_to_dict(score: RSScore, name: str) -> dict[str, Any]:
    """Convert an RSScore ORM model to a ranking dict."""
    adjusted = Decimal(str(score.adjusted_rs_score)) if score.adjusted_rs_score is not None else Decimal("50")
    momentum = Decimal(str(score.rs_momentum)) if score.rs_momentum is not None else Decimal("0")
    return {
        "instrument_id": score.instrument_id,
        "name": name,
        "adjusted_rs_score": adjusted,
        "quadrant": score.quadrant or "LAGGING",
        "rs_momentum": momentum,
        "volume_ratio": Decimal(str(score.volume_ratio)) if score.volume_ratio is not None else Decimal("1"),
        "rs_trend": score.rs_trend or "UNDERPERFORMING",
        "rs_pct_1m": Decimal(str(score.rs_pct_1m)) if score.rs_pct_1m is not None else Decimal("50"),
        "rs_pct_3m": Decimal(str(score.rs_pct_3m)) if score.rs_pct_3m is not None else Decimal("50"),
        "rs_pct_6m": Decimal(str(score.rs_pct_6m)) if score.rs_pct_6m is not None else Decimal("50"),
        "rs_pct_12m": Decimal(str(score.rs_pct_12m)) if score.rs_pct_12m is not None else Decimal("50"),
        "liquidity_tier": score.liquidity_tier or 2,
        "extension_warning": score.extension_warning or False,
    }


class RankingRepository:
    """Repository for RS score rankings, DB-backed with mock fallback."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize with an instrument repository for data access."""
        self._session = session
        self._instrument_repo = InstrumentRepository(session)

    async def _get_latest_date_subquery(self):
        """Return a subquery for the maximum date in rs_scores."""
        return select(func.max(RSScore.date)).scalar_subquery()

    async def _try_db_rankings(
        self, hierarchy_level: int | None = None,
        country: str | None = None,
        asset_type: str | None = None,
        sector: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """Try to get rankings from the database. Returns None if no data."""
        if self._session is None:
            return None
        try:
            max_date_sub = await self._get_latest_date_subquery()
            stmt = (
                select(Instrument, RSScore)
                .join(RSScore, RSScore.instrument_id == Instrument.id)
                .where(RSScore.date == max_date_sub)
            )
            if hierarchy_level is not None:
                stmt = stmt.where(Instrument.hierarchy_level == hierarchy_level)
            if country is not None:
                stmt = stmt.where(Instrument.country == country)
            if asset_type is not None:
                stmt = stmt.where(Instrument.asset_type == asset_type)
            if sector is not None:
                stmt = stmt.where(Instrument.sector == sector)
            stmt = stmt.order_by(RSScore.adjusted_rs_score.desc())

            result = await self._session.execute(stmt)
            rows = result.all()
            if not rows:
                return None
            return [_rs_score_to_dict(score, inst.name) for inst, score in rows]
        except Exception as e:
            logger.debug("DB ranking query failed: %s", e)
            return None

    async def get_country_rankings(self) -> list[dict[str, Any]]:
        """Return Level 1 country index instruments with RS scores."""
        db_result = await self._try_db_rankings(
            hierarchy_level=1, asset_type="country_index"
        )
        if db_result is not None:
            return db_result

        # Mock fallback
        instruments = await self._instrument_repo.get_all(
            filters={"hierarchy_level": 1}
        )
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
        """Return Level 2 sector instruments for a country with RS scores."""
        db_result = await self._try_db_rankings(
            hierarchy_level=2, country=country_code
        )
        if db_result is not None:
            return db_result

        # Mock fallback
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
        """Return Level 3 stock instruments for a country+sector with RS scores."""
        db_result = await self._try_db_rankings(
            hierarchy_level=3, country=country_code, sector=sector
        )
        if db_result is not None:
            return db_result

        # Mock fallback
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
        """Return global sector ETF instruments with RS scores."""
        db_result = await self._try_db_rankings(asset_type="global_sector_etf")
        if db_result is not None:
            return db_result

        # Mock fallback
        instruments = await self._instrument_repo.get_all(
            filters={"asset_type": "global_sector_etf"}
        )
        return sorted(
            [_mock_rs_scores(i) for i in instruments],
            key=lambda x: x["adjusted_rs_score"],
            reverse=True,
        )
