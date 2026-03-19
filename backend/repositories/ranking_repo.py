"""Ranking repository v2 — RS score queries using the 3-indicator system.

Queries rs_scores table and maps to v2 format (action matrix instead of quadrants).
Includes ratio return computation from prices table.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instrument, Price, RSScore
from repositories.instrument_repo import InstrumentRepository

logger = logging.getLogger(__name__)

# Canonical sector instrument IDs per country
# ONLY instruments verified to exist in the DB with RS scores and price data.
# No phantom IDs — every ID here has been audited against the database.
CANONICAL_SECTORS: dict[str, list[str]] = {
    "US": [
        "XLK_US", "XLF_US", "XLV_US", "XLY_US", "XLP_US",
        "XLE_US", "XLI_US", "XLB_US", "XLRE_US", "XLU_US", "XLC_US",
    ],
    "IN": [
        "CNXIT_IN", "NSEBANK_IN", "CNXPHARMA_IN",
        "CNXAUTO_IN", "CNXFMCG_IN", "CNXMETAL_IN", "CNXREALTY_IN",
        "CNXENERGY_IN", "CNXINFRA_IN", "CNXPSUBANK_IN",
    ],
    "JP": [
        "1615_JP", "1617_JP", "1619_JP", "1621_JP", "1622_JP",
        "1623_JP", "1625_JP", "1629_JP", "1630_JP", "1633_JP",
    ],
    "HK": [
        "KTEC_US",  # KraneShares Hang Seng TECH (technology)
    ],
    "KR": [
        "KODEX_FIN_KR", "KODEX_HC_KR", "KODEX_IND_KR",
        "KODEX_SEM_KR", "TIGER_KR", "KODEX_BAT_KR",
        "KDEF_US",
    ],
    "CN": [
        "CHIQ_US", "CHIE_US", "CHIM_US", "CHIR_US",
        "CQQQ_US", "KWEB_US", "KURE_US", "KGRN_US",
    ],
    "TW": [
        "0050_TW", "0051_TW",
    ],
    "AU": [
        "MVB_AU", "OZR_AU", "VAS_AU",
    ],
    "BR": [
        "FIND11_BR", "MATB11_BR", "BOVA11_BR",
    ],
    "CA": [
        "XEG_CA", "XFN_CA", "XHC_CA", "XIN_CA", "XIT_CA",
        "XMA_CA", "XRE_CA", "XST_CA", "XUT_CA", "XIU_CA",
    ],
    # UK, DE, FR — no sector-level instruments with RS scores in the DB yet.
    # These countries need price data fetched and RS computed before they can appear.
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

    # Override trend when score contradicts it
    if adjusted < 40 and raw_trend == "OUTPERFORMING":
        price_trend = "RECOVERING"
    elif adjusted > 60 and raw_trend == "UNDERPERFORMING":
        price_trend = "CONSOLIDATING"
    else:
        price_trend = raw_trend

    # Volume character from volume_ratio
    vol_ratio = float(score.volume_ratio) if score.volume_ratio is not None else 1.0
    if vol_ratio >= 1.3:
        volume_character = "ACCUMULATION"
    elif vol_ratio <= 0.7:
        volume_character = "DISTRIBUTION"
    else:
        volume_character = "NEUTRAL"

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
        "benchmark_id": inst.benchmark_id,
        # Ratio returns — populated by enrich step (None until enriched)
        "return_1m": None,
        "return_3m": None,
        "return_6m": None,
        "return_12m": None,
        "excess_1m": None,
        "excess_3m": None,
        "excess_6m": None,
        "excess_12m": None,
    }


# Trading days per period (approximate)
_PERIOD_DAYS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}

# Map frontend benchmark values to actual instrument IDs in the prices table
_BENCHMARK_ID_MAP: dict[str, str] = {
    "ACWI": "ACWI",
    "SPX": "SPX",
    "NSEI": "NSEI",
    "GLD": "GLD_US",
    "SHY": "SHY_US",
    "EEM": "EEM_US",
    "VEA": "VEA_US",
}


class RankingRepository:
    """Repository for v2 RS score rankings, DB-backed."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._instrument_repo = InstrumentRepository(session)

    async def _enrich_with_returns(
        self,
        items: list[dict[str, Any]],
        benchmark_override: str | None = None,
    ) -> list[dict[str, Any]]:
        """Enrich ranking items with ratio returns from prices table.

        Computes actual % returns for 1M, 3M, 6M, 12M and excess vs benchmark.
        """
        if not items or self._session is None:
            return items

        # Resolve benchmark override to actual prices table ID
        resolved_override = _BENCHMARK_ID_MAP.get(benchmark_override, benchmark_override) if benchmark_override else None

        # Collect all instrument IDs + their benchmarks
        inst_ids = [it["instrument_id"] for it in items]
        bench_ids = set()
        for it in items:
            bid = resolved_override or _BENCHMARK_ID_MAP.get(it.get("benchmark_id", ""), it.get("benchmark_id"))
            if bid:
                bench_ids.add(bid)
        all_ids = list(set(inst_ids) | bench_ids)

        # Fetch recent prices for all instruments (last 260 trading days)
        cutoff = datetime.date.today() - datetime.timedelta(days=400)
        try:
            stmt = (
                select(Price.instrument_id, Price.date, Price.close)
                .where(Price.instrument_id.in_(all_ids))
                .where(Price.date >= cutoff)
                .order_by(Price.instrument_id, Price.date)
            )
            result = await self._session.execute(stmt)
            rows = result.all()
        except Exception as e:
            logger.debug("Failed to fetch prices for returns: %s", e)
            return items

        # Build price lookup: {instrument_id: [(date, close), ...]}
        from collections import defaultdict
        prices: dict[str, list[tuple[datetime.date, float]]] = defaultdict(list)
        for iid, dt, close in rows:
            prices[iid].append((dt, float(close)))

        def _compute_return(price_list: list[tuple[datetime.date, float]], days: int) -> float | None:
            """Compute simple return over approximately N trading days."""
            if len(price_list) < 2:
                return None
            latest_close = price_list[-1][1]
            # Find the price closest to N trading days ago
            target_idx = max(0, len(price_list) - days - 1)
            if target_idx >= len(price_list) - 1:
                return None
            old_close = price_list[target_idx][1]
            if old_close == 0:
                return None
            return round((latest_close / old_close - 1) * 100, 2)

        # Enrich each item
        for it in items:
            iid = it["instrument_id"]
            bid = resolved_override or _BENCHMARK_ID_MAP.get(it.get("benchmark_id", ""), it.get("benchmark_id"))
            asset_prices = prices.get(iid, [])

            for period_key, days in _PERIOD_DAYS.items():
                ret = _compute_return(asset_prices, days)
                it[f"return_{period_key}"] = ret

                # Excess return
                if bid and bid in prices:
                    bench_ret = _compute_return(prices[bid], days)
                    if ret is not None and bench_ret is not None:
                        it[f"excess_{period_key}"] = round(ret - bench_ret, 2)

            # Update benchmark_id to reflect what was actually used
            if resolved_override:
                it["benchmark_id"] = benchmark_override  # Show the user-friendly name

        return items

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
        benchmark: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return canonical country index rankings."""
        items = await self._get_rankings_by_ids(
            CANONICAL_COUNTRY_INDICES, as_of=as_of
        )
        return await self._enrich_with_returns(items, benchmark_override=benchmark)

    async def get_sector_rankings(
        self, country_code: str, as_of: datetime.date | None = None,
        benchmark: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return sector rankings for a country."""
        canonical_ids = CANONICAL_SECTORS.get(country_code)
        if canonical_ids is not None:
            items = await self._get_rankings_by_ids(canonical_ids, as_of=as_of)
        else:
            items = await self._get_rankings_filtered(
                country=country_code,
                asset_types=("sector_etf", "sector_index"),
            )
        return await self._enrich_with_returns(items, benchmark_override=benchmark)

    async def get_stock_rankings(
        self, country_code: str, sector: str,
        benchmark: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return stock rankings for a country+sector."""
        items = await self._get_rankings_filtered(
            country=country_code,
            asset_types=("stock",),
            sector=sector,
        )
        return await self._enrich_with_returns(items, benchmark_override=benchmark)

    async def get_global_sector_rankings(
        self, benchmark: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return global sector ETF rankings."""
        items = await self._get_rankings_by_ids(CANONICAL_GLOBAL_SECTORS)
        return await self._enrich_with_returns(items, benchmark_override=benchmark)

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
