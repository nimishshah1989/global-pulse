"""Ranking repository -- RS score queries for rankings.

Queries real rs_scores table first. Falls back to deterministic mock
scores if the DB has no data (for tests and pre-seed operation).

Supports `as_of` date parameter for temporal/historical views.
In mock mode, dates shift the deterministic seed so scores change
realistically over time.
"""

import datetime
import hashlib
import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, RSScore
from repositories.instrument_repo import InstrumentRepository

# ---------------------------------------------------------------
# Canonical sector instrument IDs per country (from CLAUDE.md spec)
# Only these instruments appear in sector rankings and the matrix.
# ---------------------------------------------------------------
CANONICAL_SECTORS: dict[str, list[str]] = {
    "US": [
        "XLK_US", "XLF_US", "XLV_US", "XLY_US", "XLP_US",
        "XLE_US", "XLI_US", "XLB_US", "XLRE_US", "XLU_US", "XLC_US",
    ],
    "IN": [
        "CNXIT_IN", "NSEBANK_IN", "CNXFIN_IN", "CNXPHARMA_IN",
        "CNXAUTO_IN", "CNXFMCG_IN", "CNXMETAL_IN", "CNXREALTY_IN",
        "CNXENERGY_IN", "CNXINFRA_IN", "CNXPSUBANK_IN",
    ],
    "JP": [
        "1615_JP", "1613_JP", "1617_JP", "1618_JP", "1619_JP",
        "1620_JP", "1621_JP", "1622_JP", "1623_JP", "1624_JP",
        "1625_JP", "1626_JP", "1627_JP", "1628_JP", "1629_JP",
        "1633_JP",
    ],
    "HK": [
        # HS sub-indices
        "HSTECH_HK", "HSFI_HK", "HSPI_HK", "HSUI_HK",
        # HKEX sector ETFs as fallback
        "2800_HK", "3067_HK", "3033_HK",
    ],
}

CANONICAL_GLOBAL_SECTORS: list[str] = [
    "IXN_US", "IXG_US", "IXJ_US", "IXC_US", "EXI_US",
    "RXI_US", "KXI_US", "JXI_US", "MXI_US", "IXP_US",
]

# One primary index per country (from CLAUDE.md Level 1 spec)
CANONICAL_COUNTRY_INDICES: list[str] = [
    "SPX",      # US — S&P 500
    "FTM",      # UK — FTSE 100
    "DAX",      # Germany — DAX 40
    "CAC",      # France — CAC 40
    "NKX",      # Japan — Nikkei 225
    "HSI",      # Hong Kong — Hang Seng
    "CSI300",   # China — CSI 300
    "KS11",     # South Korea — KOSPI
    "NSEI",     # India — NIFTY 50
    "TWII",     # Taiwan — TWSE
    "AXJO",     # Australia — ASX 200
    "BVSP",     # Brazil — IBOVESPA
    "GSPTSE",   # Canada — TSX
    "NDQ",      # US — NASDAQ 100 (secondary, useful for traders)
]

logger = logging.getLogger(__name__)


def _seed_float(instrument_id: str, salt: str = "", date_str: str = "") -> float:
    """Return a deterministic float in [0, 1) based on instrument ID, salt, and date."""
    digest = hashlib.md5((instrument_id + salt + date_str).encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _determine_quadrant(score: float, momentum: float) -> str:
    """Assign RRG quadrant based on score and momentum thresholds."""
    if score > 50 and momentum > 0:
        return "LEADING"
    if score > 50 and momentum <= 0:
        return "WEAKENING"
    if score <= 50 and momentum <= 0:
        return "LAGGING"
    return "IMPROVING"


def _mock_rs_scores(
    instrument: dict[str, Any],
    as_of: datetime.date | None = None,
) -> dict[str, Any]:
    """Generate realistic mock RS scores for an instrument.

    When `as_of` is provided, scores shift deterministically by date
    so the temporal UI shows different rankings over time.
    """
    iid = instrument["id"]
    date_str = as_of.isoformat() if as_of else ""

    # Adjusted RS score: 20-90 range
    raw = _seed_float(iid, "score", date_str)
    adjusted_rs_score = round(20 + raw * 70, 2)

    # RS momentum: -30 to +30
    mom_raw = _seed_float(iid, "momentum", date_str)
    rs_momentum = round(-30 + mom_raw * 60, 2)

    quadrant = _determine_quadrant(adjusted_rs_score, rs_momentum)

    # Volume ratio: 0.5 to 2.0
    vol_raw = _seed_float(iid, "volume", date_str)
    volume_ratio = round(0.5 + vol_raw * 1.5, 3)

    # RS trend
    rs_trend = "OUTPERFORMING" if adjusted_rs_score > 50 else "UNDERPERFORMING"

    # Percentile fields: 0-100
    rs_pct_1m = round(_seed_float(iid, "1m", date_str) * 100, 2)
    rs_pct_3m = round(_seed_float(iid, "3m", date_str) * 100, 2)
    rs_pct_6m = round(_seed_float(iid, "6m", date_str) * 100, 2)
    rs_pct_12m = round(_seed_float(iid, "12m", date_str) * 100, 2)

    # Extension warning
    extension_warning = (
        rs_pct_3m > 95 and rs_pct_6m > 95 and rs_pct_12m > 90
    )

    liquidity_tier = instrument.get("liquidity_tier", 2)

    return {
        "instrument_id": iid,
        "name": instrument["name"],
        "country": instrument.get("country"),
        "sector": instrument.get("sector"),
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


def _rs_score_to_dict(score: RSScore, inst: Instrument) -> dict[str, Any]:
    """Convert an RSScore ORM model to a ranking dict."""
    adjusted = float(score.adjusted_rs_score) if score.adjusted_rs_score is not None else 50.0
    momentum = float(score.rs_momentum) if score.rs_momentum is not None else 0.0
    return {
        "instrument_id": score.instrument_id,
        "name": inst.name,
        "country": inst.country,
        "sector": inst.sector,
        "adjusted_rs_score": adjusted,
        "quadrant": score.quadrant or "LAGGING",
        "rs_momentum": momentum,
        "volume_ratio": float(score.volume_ratio) if score.volume_ratio is not None else 1.0,
        "rs_trend": score.rs_trend or "UNDERPERFORMING",
        "rs_pct_1m": float(score.rs_pct_1m) if score.rs_pct_1m is not None else 50.0,
        "rs_pct_3m": float(score.rs_pct_3m) if score.rs_pct_3m is not None else 50.0,
        "rs_pct_6m": float(score.rs_pct_6m) if score.rs_pct_6m is not None else 50.0,
        "rs_pct_12m": float(score.rs_pct_12m) if score.rs_pct_12m is not None else 50.0,
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
        asset_types: tuple[str, ...] | None = None,
        sector: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """Try to get rankings from the database. Returns None if no data.

        Uses each instrument's latest RS score date, not the global max,
        so instruments computed on different dates are all included.
        """
        if self._session is None:
            return None
        try:
            # Build instrument filter conditions
            inst_conditions = [Instrument.is_active == True]
            if hierarchy_level is not None:
                inst_conditions.append(Instrument.hierarchy_level == hierarchy_level)
            if country is not None:
                inst_conditions.append(Instrument.country == country)
            if asset_type is not None:
                inst_conditions.append(Instrument.asset_type == asset_type)
            if asset_types is not None:
                inst_conditions.append(Instrument.asset_type.in_(asset_types))
            if sector is not None:
                inst_conditions.append(Instrument.sector == sector)

            # Subquery: latest RS date per matching instrument
            latest_sub = (
                select(
                    RSScore.instrument_id,
                    func.max(RSScore.date).label("max_date"),
                )
                .join(Instrument, Instrument.id == RSScore.instrument_id)
                .where(*inst_conditions)
                .group_by(RSScore.instrument_id)
                .subquery()
            )

            stmt = (
                select(Instrument, RSScore)
                .join(RSScore, RSScore.instrument_id == Instrument.id)
                .join(
                    latest_sub,
                    (RSScore.instrument_id == latest_sub.c.instrument_id)
                    & (RSScore.date == latest_sub.c.max_date),
                )
                .where(*inst_conditions)
                .order_by(RSScore.adjusted_rs_score.desc())
            )

            result = await self._session.execute(stmt)
            rows = result.all()
            if not rows:
                return None
            return [_rs_score_to_dict(score, inst) for inst, score in rows]
        except Exception as e:
            logger.debug("DB ranking query failed: %s", e)
            return None

    async def _try_db_rankings_by_ids(
        self, instrument_ids: list[str],
        as_of: datetime.date | None = None,
    ) -> list[dict[str, Any]] | None:
        """Get rankings for a specific set of instrument IDs from the DB.

        When `as_of` is provided, finds the latest score on or before that date.
        Otherwise uses each instrument's latest RS score date.
        """
        if self._session is None:
            return None
        try:
            # Subquery: latest date per instrument (on or before as_of if given)
            sub_q = (
                select(
                    RSScore.instrument_id,
                    func.max(RSScore.date).label("max_date"),
                )
                .where(RSScore.instrument_id.in_(instrument_ids))
            )
            if as_of is not None:
                sub_q = sub_q.where(RSScore.date <= as_of)
            latest_per_inst = sub_q.group_by(RSScore.instrument_id).subquery()

            stmt = (
                select(Instrument, RSScore)
                .join(RSScore, RSScore.instrument_id == Instrument.id)
                .join(
                    latest_per_inst,
                    (RSScore.instrument_id == latest_per_inst.c.instrument_id)
                    & (RSScore.date == latest_per_inst.c.max_date),
                )
                .where(Instrument.id.in_(instrument_ids))
                .order_by(RSScore.adjusted_rs_score.desc())
            )
            result = await self._session.execute(stmt)
            rows = result.all()
            if not rows:
                return None
            return [_rs_score_to_dict(score, inst) for inst, score in rows]
        except Exception as e:
            logger.debug("DB ranking by IDs query failed: %s", e)
            return None

    async def get_country_rankings(
        self, as_of: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Return Level 1 canonical country index instruments with RS scores.

        Uses the 14 primary country indices from the CLAUDE.md spec.
        If `as_of` is provided, return scores for that historical date.
        """
        db_result = await self._try_db_rankings_by_ids(
            CANONICAL_COUNTRY_INDICES, as_of=as_of
        )
        if db_result is not None:
            return db_result

        # Mock fallback using canonical IDs
        all_instruments = await self._instrument_repo.get_all()
        country_indices = [
            i for i in all_instruments
            if i["id"] in CANONICAL_COUNTRY_INDICES
        ]
        return sorted(
            [_mock_rs_scores(i, as_of=as_of) for i in country_indices],
            key=lambda x: x["adjusted_rs_score"],
            reverse=True,
        )

    async def get_sector_rankings(
        self, country_code: str, as_of: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Return Level 2 sector instruments for a country with RS scores.

        Uses canonical sector lists when available (US, IN, JP, HK) to
        return only the primary sector ETFs/indices, not thematic/specialty ETFs.
        Falls back to all sector_etf/sector_index types for other countries.
        """
        canonical_ids = CANONICAL_SECTORS.get(country_code)

        if canonical_ids is not None:
            # Use canonical whitelist
            db_result = await self._try_db_rankings_by_ids(
                canonical_ids, as_of=as_of
            )
            if db_result is not None:
                return db_result

            # Mock fallback for canonical IDs
            all_instruments = await self._instrument_repo.get_all()
            instruments = [i for i in all_instruments if i["id"] in canonical_ids]
            return sorted(
                [_mock_rs_scores(i, as_of=as_of) for i in instruments],
                key=lambda x: x["adjusted_rs_score"],
                reverse=True,
            )

        # Non-canonical countries: use asset_type filter
        db_result = await self._try_db_rankings(
            hierarchy_level=2, country=country_code,
            asset_types=("sector_etf", "sector_index"),
        )
        if db_result is not None:
            return db_result

        instruments = await self._instrument_repo.get_by_country(country_code)
        sectors = [
            i for i in instruments
            if i.get("hierarchy_level") == 2
            and i.get("asset_type") in ("sector_etf", "sector_index")
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
        """Return canonical global sector ETF rankings (iShares 10 sectors)."""
        db_result = await self._try_db_rankings_by_ids(CANONICAL_GLOBAL_SECTORS)
        if db_result is not None:
            return db_result

        # Mock fallback — use canonical list only
        all_instruments = await self._instrument_repo.get_all()
        instruments = [
            i for i in all_instruments
            if i["id"] in CANONICAL_GLOBAL_SECTORS
        ]
        return sorted(
            [_mock_rs_scores(i) for i in instruments],
            key=lambda x: x["adjusted_rs_score"],
            reverse=True,
        )
