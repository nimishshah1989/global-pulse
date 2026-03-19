"""Ranking repository v2 — RS score queries using the 3-indicator system.

Queries rs_scores table and maps to v2 format (action matrix instead of quadrants).
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, RSScore
from repositories.instrument_repo import InstrumentRepository

logger = logging.getLogger(__name__)

# Canonical sector instrument IDs per country
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
        "HSTECH_HK", "HSFI_HK", "HSPI_HK", "HSUI_HK",
        "2800_HK", "3067_HK", "3033_HK",
        # China/HK sector ETFs (US-listed, track Greater China sectors)
        "CHIQ_US", "KURE_US", "CHII_US", "CHIE_US",
        "CHIM_US", "KWEB_US", "CHIS_US", "CHIR_US",
    ],
    "BR": [
        "EWZ_US", "BOVA11_BR", "FIND11_BR", "MATB11_BR", "UTIL11_BR",
        "TECB11_BR", "ENGI11_BR", "IFNC11_BR", "CSMO11_BR", "SAUD11_BR",
    ],
}

CANONICAL_GLOBAL_SECTORS: list[str] = [
    "IXN_US", "IXG_US", "IXJ_US", "IXC_US", "EXI_US",
    "RXI_US", "KXI_US", "JXI_US", "MXI_US", "IXP_US",
]

CANONICAL_COUNTRY_INDICES: list[str] = [
    "SPX", "FTM", "DAX", "CAC", "NKX", "HSI",
    "CSI300", "KS11", "NSEI", "TWII", "AXJO",
    "BVSP", "GSPTSE", "NDQ",
]


_QUADRANT_TO_ACTION: dict[str, str] = {
    "LEADING": "BUY",
    "IMPROVING": "ACCUMULATE",
    "WEAKENING": "REDUCE",
    "LAGGING": "SELL",
}


def _resolve_action(quadrant: str, rs_score: float) -> str:
    """Derive action from quadrant AND RS score to avoid contradictions.

    Quadrant alone can produce misleading signals (e.g. IMPROVING + RS 38
    → ACCUMULATE, which looks bullish). Override with score-aware logic.
    """
    base = _QUADRANT_TO_ACTION.get(quadrant, quadrant)

    # Very weak RS — never show bullish action regardless of quadrant
    if rs_score < 30:
        if base in ("BUY", "ACCUMULATE"):
            return "AVOID"
        return base
    if rs_score < 40:
        if base == "BUY":
            return "WATCH"
        if base == "ACCUMULATE":
            return "WATCH"
        return base
    if rs_score < 50:
        if base == "BUY":
            return "ACCUMULATE"
        return base

    # Very strong RS — never show bearish action regardless of quadrant
    if rs_score >= 70:
        if base in ("SELL", "AVOID"):
            return "REDUCE"
        return base

    return base


def _rs_score_to_v2_dict(score: RSScore, inst: Instrument) -> dict[str, Any]:
    """Convert RSScore ORM model to v2 ranking dict."""
    adjusted = float(score.adjusted_rs_score) if score.adjusted_rs_score is not None else 50.0
    momentum = float(score.rs_momentum) if score.rs_momentum is not None else 0.0
    raw_quadrant = score.quadrant or "WATCH"
    action = _resolve_action(raw_quadrant, adjusted)
    rs_line = float(score.rs_line) if score.rs_line is not None else None
    rs_ma = float(score.rs_ma_150) if score.rs_ma_150 is not None else None
    raw_trend = score.rs_trend or "UNDERPERFORMING"

    # Override trend when score contradicts it — avoid misleading signals
    # A weak score (<40) should not show OUTPERFORMING; a strong score (>60) should not
    # show UNDERPERFORMING, because the trend label alone creates false confidence/fear.
    if adjusted < 40 and raw_trend == "OUTPERFORMING":
        price_trend = "RECOVERING"  # Technically above MA but still weak overall
    elif adjusted > 60 and raw_trend == "UNDERPERFORMING":
        price_trend = "CONSOLIDATING"  # Technically below MA but still strong overall
    else:
        price_trend = raw_trend

    # Volume character from volume_ratio (SMA20/SMA100 of volume)
    # Use meaningful thresholds, not just above/below 1.0
    vol_ratio = float(score.volume_ratio) if score.volume_ratio is not None else 1.0
    if vol_ratio >= 1.3:
        volume_character = "ACCUMULATION"  # Meaningful volume increase
    elif vol_ratio <= 0.7:
        volume_character = "DISTRIBUTION"  # Meaningful volume decrease
    else:
        volume_character = "NEUTRAL"  # Normal range — don't read into it

    # Momentum trend from sign
    momentum_trend = "ACCELERATING" if momentum > 0 else "DECELERATING"

    return {
        "instrument_id": score.instrument_id,
        "name": inst.name,
        "country": inst.country,
        "sector": inst.sector,
        "asset_type": inst.asset_type,
        "rs_line": rs_line,
        "rs_ma": rs_ma,
        "price_trend": price_trend,
        "rs_momentum_pct": momentum,
        "momentum_trend": momentum_trend,
        "volume_character": volume_character,
        "action": action,
        "rs_score": adjusted,
        "regime": score.regime or "RISK_ON",
    }


class RankingRepository:
    """Repository for v2 RS score rankings, DB-backed."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._instrument_repo = InstrumentRepository(session)

    async def _get_rankings_by_ids(
        self, instrument_ids: list[str],
        as_of: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Get rankings for a set of instrument IDs from DB."""
        if self._session is None:
            return []
        try:
            sub_q = (
                select(
                    RSScore.instrument_id,
                    func.max(RSScore.date).label("max_date"),
                )
                .where(RSScore.instrument_id.in_(instrument_ids))
            )
            if as_of is not None:
                sub_q = sub_q.where(RSScore.date <= as_of)
            latest = sub_q.group_by(RSScore.instrument_id).subquery()

            stmt = (
                select(Instrument, RSScore)
                .join(RSScore, RSScore.instrument_id == Instrument.id)
                .join(
                    latest,
                    (RSScore.instrument_id == latest.c.instrument_id)
                    & (RSScore.date == latest.c.max_date),
                )
                .where(Instrument.id.in_(instrument_ids))
                .order_by(RSScore.adjusted_rs_score.desc())
            )
            result = await self._session.execute(stmt)
            rows = result.all()
            if not rows:
                return []
            return [_rs_score_to_v2_dict(score, inst) for inst, score in rows]
        except Exception as e:
            logger.debug("DB ranking query failed: %s", e)
            return []

    async def _get_rankings_filtered(
        self,
        country: str | None = None,
        asset_types: tuple[str, ...] | None = None,
        sector: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get rankings with instrument filters."""
        if self._session is None:
            return []
        try:
            conditions = [Instrument.is_active == True]
            if country is not None:
                conditions.append(Instrument.country == country)
            if asset_types is not None:
                conditions.append(Instrument.asset_type.in_(asset_types))
            if sector is not None:
                conditions.append(Instrument.sector == sector)

            latest_sub = (
                select(
                    RSScore.instrument_id,
                    func.max(RSScore.date).label("max_date"),
                )
                .join(Instrument, Instrument.id == RSScore.instrument_id)
                .where(*conditions)
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
                .where(*conditions)
                .order_by(RSScore.adjusted_rs_score.desc())
            )
            result = await self._session.execute(stmt)
            rows = result.all()
            return [_rs_score_to_v2_dict(score, inst) for inst, score in rows]
        except Exception as e:
            logger.debug("DB filtered ranking query failed: %s", e)
            return []

    async def get_country_rankings(
        self, as_of: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Return canonical country index rankings."""
        return await self._get_rankings_by_ids(
            CANONICAL_COUNTRY_INDICES, as_of=as_of
        )

    async def get_sector_rankings(
        self, country_code: str, as_of: datetime.date | None = None,
    ) -> list[dict[str, Any]]:
        """Return sector rankings for a country."""
        canonical_ids = CANONICAL_SECTORS.get(country_code)
        if canonical_ids is not None:
            return await self._get_rankings_by_ids(canonical_ids, as_of=as_of)

        return await self._get_rankings_filtered(
            country=country_code,
            asset_types=("sector_etf", "sector_index"),
        )

    async def get_stock_rankings(
        self, country_code: str, sector: str,
    ) -> list[dict[str, Any]]:
        """Return stock rankings for a country+sector."""
        return await self._get_rankings_filtered(
            country=country_code,
            asset_types=("stock",),
            sector=sector,
        )

    async def get_global_sector_rankings(self) -> list[dict[str, Any]]:
        """Return global sector ETF rankings."""
        return await self._get_rankings_by_ids(CANONICAL_GLOBAL_SECTORS)

    async def get_all_etf_rankings(self) -> list[dict[str, Any]]:
        """Return all ETF rankings — the main output screen."""
        return await self._get_rankings_filtered(
            asset_types=(
                "sector_etf", "country_etf", "global_sector_etf",
                "etf", "regional_etf",
            ),
        )

    async def get_top_etfs(
        self, action_filter: str | None = None,
        country_filter: str | None = None,
        sector_filter: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return top ETFs with optional action/country/sector filters."""
        if self._session is None:
            return []
        try:
            conditions = [Instrument.is_active == True]
            conditions.append(
                Instrument.asset_type.in_((
                    "sector_etf", "country_etf", "global_sector_etf",
                    "etf", "regional_etf",
                ))
            )
            if country_filter:
                conditions.append(Instrument.country == country_filter)
            if sector_filter:
                conditions.append(Instrument.sector == sector_filter)

            latest_sub = (
                select(
                    RSScore.instrument_id,
                    func.max(RSScore.date).label("max_date"),
                )
                .join(Instrument, Instrument.id == RSScore.instrument_id)
                .where(*conditions)
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
                .where(*conditions)
            )

            # Fetch more rows when filtering by action since the filter is post-query
            fetch_limit = limit * 3 if action_filter else limit
            stmt = stmt.order_by(RSScore.adjusted_rs_score.desc()).limit(fetch_limit)

            result = await self._session.execute(stmt)
            rows = result.all()
            items = [_rs_score_to_v2_dict(score, inst) for inst, score in rows]

            # Action is computed from quadrant + score, so filter post-conversion
            if action_filter:
                items = [i for i in items if i["action"] == action_filter]

            return items[:limit]
        except Exception as e:
            logger.debug("Top ETFs query failed: %s", e)
            return []
