"""Ranking repository v2 — RS score queries using the 3-indicator system.

Queries rs_scores table and maps to v2 format (action matrix instead of quadrants).
Includes real-time RS computation from prices table using v2 formula:
  RS Score = ((rs_line / rs_ma) - 1.0) * 1000 + 50, clipped [0, 100]
  Volume via OBV (On-Balance Volume) instead of SMA ratio.
"""
from __future__ import annotations

import datetime
import logging
from collections import defaultdict
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
    # HK, KR, CN, TW, AU, BR — use dynamic fallback to find sector ETFs
    # from the DB's sector classification (ETF→GICS mapping applied).
    "CA": [
        "XEG_CA", "XFN_CA", "XHC_CA", "XIN_CA", "XIT_CA",
        "XMA_CA", "XRE_CA", "XST_CA", "XUT_CA", "XIU_CA",
    ],
    # UK, DE, FR — use dynamic fallback (ETF→GICS mapping applied for UK).
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


# Sector group mapping: when user filters by a parent sector,
# include all sub-sectors that belong to it.
SECTOR_GROUP_MAP: dict[str, list[str]] = {
    "gold": ["gold", "gold_miners", "gold_miners_jr"],
    "silver": ["silver", "silver_miners"],
    "crude_oil": ["crude_oil", "oil_gas_exploration", "oil_services"],
    "natural_gas": ["natural_gas"],
    "commodities_broad": [
        "commodities_broad", "agriculture", "metals_broad",
        "platinum", "palladium", "copper_miners", "uranium",
        "lithium_battery", "rare_earth", "wheat", "corn",
        "soybeans", "coffee", "cocoa", "cotton", "sugar",
        "livestock", "timber", "carbon", "gasoline", "water",
        "shipping",
    ],
    "fixed_income": [
        "fixed_income", "aggregate_bond", "treasury_short",
        "treasury_mid", "treasury_long", "treasury_ultrashort",
        "treasury_strips", "tips", "floating_rate", "high_yield",
        "investment_grade", "municipal", "mortgage_backed",
        "em_bond", "intl_bond", "intl_treasury", "short_corp",
        "intermediate_corp", "long_corp", "corporate_bond",
        "convertible_bond", "preferred_stock", "target_date_bond",
        "fixed_income_other", "clo", "short_duration_bond",
        "long_duration_bond", "credit", "money_market", "bank_loans",
    ],
    "crypto": [
        "crypto", "bitcoin", "ethereum", "solana",
        "dogecoin", "xrp", "sui", "hbar", "chainlink", "blockchain",
    ],
    "energy": ["energy", "clean_energy", "solar", "wind_energy", "mlp_midstream"],
    "technology": ["technology", "semiconductors", "cybersecurity",
                   "cloud_computing", "artificial_intelligence",
                   "robotics_ai", "fintech", "internet", "data_centers",
                   "3d_printing", "space", "digital_media",
                   "it", "electrical_equipment"],  # India/Japan variants
    "healthcare": ["healthcare", "biotech", "pharma",
                   "medical_devices", "genomics"],
    "financials": ["financials", "banks", "regional_banks", "insurance",
                   "bank", "psu_bank", "financial_services",  # India variants
                   "other_finance", "securities"],  # Japan variants
    "industrials": ["industrials", "aerospace_defense", "homebuilders",
                    "airlines", "transportation", "infrastructure",
                    "construction", "machinery",  # Japan variants
                    "auto"],  # India variant
    "consumer_discretionary": ["consumer_discretionary", "retail",
                               "luxury", "gaming", "cannabis"],
    "consumer_staples": ["consumer_staples", "fmcg", "foods"],  # India/Japan
    "materials": ["materials", "iron_steel", "metal", "nonferrous_metals",
                  "chemicals", "resources"],  # India/Japan/AU variants
    "utilities": ["utilities"],
    "real_estate": ["real_estate", "realty"],  # India variant
    "communication_services": ["communication_services", "communication"],
}


# ---------------------------------------------------------------------------
# 3-Gate Action Engine (matches MarketPulse exactly)
# G1: Absolute return > 0? (is price going up?)
# G2: RS Score > 50? (v2: RS line above its MA — actually outperforming benchmark)
# G3: Momentum > 0? (is RS getting stronger?)
# ---------------------------------------------------------------------------

def _classify_quadrant(rs_score: float, momentum: float) -> str:
    """2x2 quadrant from RS score and momentum."""
    outperforming = rs_score > 50
    strengthening = momentum > 0
    if outperforming and strengthening:
        return "LEADING"
    if outperforming and not strengthening:
        return "WEAKENING"
    if not outperforming and strengthening:
        return "IMPROVING"
    return "LAGGING"


def _compute_volume_signal(volume_ratio: float, price_rising: bool) -> str:
    """Volume signal from 20d/100d volume ratio + price direction.

    Matches MarketPulse: ACCUMULATION, WEAK_RALLY, DISTRIBUTION, WEAK_DECLINE.
    """
    volume_rising = volume_ratio >= 1.0
    if price_rising and volume_rising:
        return "ACCUMULATION"
    if price_rising and not volume_rising:
        return "WEAK_RALLY"
    if not price_rising and volume_rising:
        return "DISTRIBUTION"
    return "WEAK_DECLINE"


def _derive_action_gate(
    absolute_return: float | None,
    rs_score: float,
    momentum: float,
    volume_signal: str,
    regime: str,
) -> tuple[str, str]:
    """3-gate action engine — exact MarketPulse logic.

    Returns (action, reason) tuple.
    """
    g1 = (absolute_return or 0) > 0
    g2 = rs_score > 50
    g3 = momentum > 0

    if g1 and g2 and g3:
        action = "BUY"
        reason = "Rising, outperforming, and strengthening"
    elif g1 and g2 and not g3:
        action = "HOLD"
        reason = "Outperforming but momentum fading"
    elif g1 and not g2 and g3:
        action = "WATCH_EMERGING"
        reason = "Rising and strengthening, but still lagging peers"
    elif g1 and not g2 and not g3:
        action = "AVOID"
        reason = "Rising but lagging with fading momentum"
    elif not g1 and g2 and g3:
        action = "WATCH_RELATIVE"
        reason = "Outperforming and strengthening despite price decline"
    elif not g1 and g2 and not g3:
        action = "SELL"
        reason = "Price falling with fading relative strength"
    elif not g1 and not g2 and g3:
        action = "WATCH_EARLY"
        reason = "Earliest reversal signal — momentum just turned positive"
    else:
        action = "SELL"
        reason = "Falling, underperforming, and weakening"

    # Volume override: BUY + DISTRIBUTION → downgrade to HOLD
    if action == "BUY" and volume_signal == "DISTRIBUTION":
        action = "HOLD"
        reason = "BUY downgraded — smart money distribution detected"

    # Regime override: BEAR → BUY downgraded to HOLD
    if action == "BUY" and regime in ("BEAR", "CORRECTION"):
        action = "HOLD"
        reason = f"BUY downgraded — market in {regime.lower()} regime"

    return action, reason


def _compute_market_regime(benchmark_price: float | None, benchmark_ma200: float | None) -> str:
    """Compute market regime from ACWI price vs 200-day MA."""
    if benchmark_price is None or benchmark_ma200 is None:
        return "BULL"
    ratio = benchmark_price / benchmark_ma200 if benchmark_ma200 > 0 else 1.0
    if ratio >= 1.0:
        return "BULL"
    if ratio >= 0.95:
        return "CAUTIOUS"
    if ratio >= 0.85:
        return "CORRECTION"
    return "BEAR"


def _rs_score_to_v2_dict(score: RSScore, inst: Instrument) -> dict[str, Any]:
    """Convert RSScore ORM model to v2 ranking dict.

    Computes quadrant, volume_signal, and preliminary action via 3-gate engine.
    Action is recalculated by _enrich_with_returns once actual returns are available.
    """
    rs_score = float(score.adjusted_rs_score) if score.adjusted_rs_score is not None else 50.0
    momentum = float(score.rs_momentum) if score.rs_momentum is not None else 0.0
    vol_ratio = float(score.volume_ratio) if score.volume_ratio is not None else 1.0

    # Quadrant from RS score + momentum
    quadrant = _classify_quadrant(rs_score, momentum)

    # Use RS trend as proxy for price direction (until actual returns are computed)
    price_rising = (score.rs_trend or "UNDERPERFORMING") == "OUTPERFORMING"

    # Volume signal: 4-category from volume ratio + price direction
    volume_signal = _compute_volume_signal(vol_ratio, price_rising)

    # Map old 2-category regime to 4-category (refined by _enrich_with_returns later)
    old_regime = score.regime or "RISK_ON"
    regime = "BULL" if old_regime == "RISK_ON" else "BEAR"

    # Preliminary action using rs_trend as proxy for absolute return
    # absolute_return > 0 ≈ price_rising for the initial pass
    preliminary_abs_return = 1.0 if price_rising else -1.0
    action, action_reason = _derive_action_gate(
        preliminary_abs_return, rs_score, momentum, volume_signal, regime,
    )

    return {
        "instrument_id": score.instrument_id,
        "name": inst.name,
        "country": inst.country,
        "sector": inst.sector,
        "asset_type": inst.asset_type,
        "rs_score": rs_score,
        "rs_momentum": momentum,
        "quadrant": quadrant,
        "action": action,
        "action_reason": action_reason,
        "volume_signal": volume_signal,
        "regime": regime,
        "absolute_return": None,
        "relative_return": None,
        "benchmark_id": inst.benchmark_id,
        # Ratio returns — populated by _enrich_with_returns
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


def _compute_rs_from_prices(
    asset_prices: list[tuple[datetime.date, float]],
    bench_prices: list[tuple[datetime.date, float]],
    ma_period: int = 63,
) -> tuple[float, float, float]:
    """Compute RS score, RS momentum, and RS line from price series.

    Uses v2 formula: RS Score = ((rs_line / rs_ma) - 1.0) * 1000 + 50, clipped [0, 100].
    RS line above its MA => score > 50 => actually outperforming (not just percentile).

    Returns (rs_score, rs_momentum, rs_line_latest).
    """
    # Build date-aligned RS line
    bench_map: dict[datetime.date, float] = {d: c for d, c in bench_prices}
    rs_values: list[tuple[datetime.date, float]] = []
    for d, close in asset_prices:
        if d in bench_map and bench_map[d] > 0:
            rs_values.append((d, close / bench_map[d] * 100))

    if len(rs_values) < ma_period:
        return 50.0, 0.0, 100.0

    # RS MA over ma_period
    recent_rs = [v for _, v in rs_values[-ma_period:]]
    rs_ma = sum(recent_rs) / len(recent_rs)
    rs_line = rs_values[-1][1]

    # RS Score (v2 formula)
    if rs_ma > 0:
        rs_score = ((rs_line / rs_ma) - 1.0) * 1000 + 50
        rs_score = max(0.0, min(100.0, round(rs_score, 2)))
    else:
        rs_score = 50.0

    # RS Momentum (20-day lookback of RS score)
    if len(rs_values) >= ma_period + 20:
        old_rs = [v for _, v in rs_values[-(ma_period + 20):-20]]
        old_ma = sum(old_rs[-ma_period:]) / ma_period if len(old_rs) >= ma_period else rs_ma
        if old_ma > 0:
            old_score = ((rs_values[-21][1] / old_ma) - 1.0) * 1000 + 50
            old_score = max(0.0, min(100.0, round(old_score, 2)))
        else:
            old_score = 50.0
        rs_momentum = round(rs_score - old_score, 2)
    else:
        rs_momentum = 0.0

    return rs_score, rs_momentum, rs_line


def _compute_obv_signal(
    price_list: list[tuple[datetime.date, float, int | None]],
) -> str:
    """Compute OBV-based volume character from price+volume series.

    Returns 'ACCUMULATION' if OBV > OBV 20-day MA, else 'DISTRIBUTION'.
    price_list: [(date, close, volume), ...] sorted by date ascending.
    """
    if len(price_list) < 21:
        return "ACCUMULATION"  # Not enough data, neutral default

    # Compute OBV series
    obv_series: list[int] = [0]
    for i in range(1, len(price_list)):
        vol = price_list[i][2] or 0
        prev_close = price_list[i - 1][1]
        curr_close = price_list[i][1]
        if curr_close > prev_close:
            obv_series.append(obv_series[-1] + vol)
        elif curr_close < prev_close:
            obv_series.append(obv_series[-1] - vol)
        else:
            obv_series.append(obv_series[-1])

    # OBV MA over last 20 values
    if len(obv_series) >= 20:
        obv_ma = sum(obv_series[-20:]) / 20
    else:
        obv_ma = sum(obv_series) / len(obv_series)

    obv_latest = obv_series[-1]
    return "ACCUMULATION" if obv_latest > obv_ma else "DISTRIBUTION"


class RankingRepository:
    """Repository for v2 RS score rankings, DB-backed."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._instrument_repo = InstrumentRepository(session)

    async def _enrich_with_returns(
        self,
        items: list[dict[str, Any]],
        benchmark_override: str | None = None,
        period: str = "3m",
    ) -> list[dict[str, Any]]:
        """Enrich ranking items with v2 RS scores computed from prices.

        Replaces DB percentile scores with real RS computation:
        - RS Score = ((rs_line / rs_ma) - 1.0) * 1000 + 50, clipped [0, 100]
        - OBV-based volume character instead of SMA ratio
        - Computes actual % returns for 1M, 3M, 6M, 12M and excess vs benchmark.
        """
        if not items or self._session is None:
            return items

        # Resolve MA period from the period parameter
        ma_period = _PERIOD_DAYS.get(period, 63)

        # Resolve benchmark override to actual prices table ID
        resolved_override = _BENCHMARK_ID_MAP.get(benchmark_override, benchmark_override) if benchmark_override else None

        # Collect all instrument IDs + their benchmarks
        inst_ids = [it["instrument_id"] for it in items]
        bench_ids: set[str] = set()
        for it in items:
            bid = resolved_override or _BENCHMARK_ID_MAP.get(it.get("benchmark_id", ""), it.get("benchmark_id"))
            if bid:
                bench_ids.add(bid)
        # Always include ACWI for regime calculation
        bench_ids.add("ACWI")
        all_ids = list(set(inst_ids) | bench_ids)

        # Fetch recent prices for all instruments (last ~400 calendar days)
        cutoff = datetime.date.today() - datetime.timedelta(days=400)
        try:
            stmt = (
                select(Price.instrument_id, Price.date, Price.close, Price.volume)
                .where(Price.instrument_id.in_(all_ids))
                .where(Price.date >= cutoff)
                .order_by(Price.instrument_id, Price.date)
            )
            result = await self._session.execute(stmt)
            rows = result.all()
        except Exception as e:
            logger.debug("Failed to fetch prices for returns: %s", e)
            return items

        # Build price lookups
        prices: dict[str, list[tuple[datetime.date, float]]] = defaultdict(list)
        prices_with_volume: dict[str, list[tuple[datetime.date, float, int | None]]] = defaultdict(list)
        for iid, dt, close, volume in rows:
            c = float(close)
            v = int(volume) if volume is not None else None
            prices[iid].append((dt, c))
            prices_with_volume[iid].append((dt, c, v))

        def _compute_return(price_list: list[tuple[datetime.date, float]], days: int) -> float | None:
            """Compute simple return over approximately N trading days."""
            if len(price_list) < 2:
                return None
            latest_close = price_list[-1][1]
            target_idx = max(0, len(price_list) - days - 1)
            if target_idx >= len(price_list) - 1:
                return None
            old_close = price_list[target_idx][1]
            if old_close == 0:
                return None
            return round((latest_close / old_close - 1) * 100, 2)

        # Compute market regime from ACWI price vs 200-day MA
        acwi_prices = prices.get("ACWI", [])
        regime = "BULL"
        if len(acwi_prices) >= 200:
            acwi_latest = acwi_prices[-1][1]
            acwi_ma200 = sum(p[1] for p in acwi_prices[-200:]) / 200
            regime = _compute_market_regime(acwi_latest, acwi_ma200)

        # Enrich each item
        for it in items:
            iid = it["instrument_id"]
            bid = resolved_override or _BENCHMARK_ID_MAP.get(it.get("benchmark_id", ""), it.get("benchmark_id"))
            asset_prices = prices.get(iid, [])
            bench_prices = prices.get(bid, []) if bid else []

            # --- V2 RS computation from prices ---
            if asset_prices and bench_prices:
                rs_score, rs_momentum, rs_line = _compute_rs_from_prices(
                    asset_prices, bench_prices, ma_period=ma_period,
                )
                it["rs_score"] = rs_score
                it["rs_momentum"] = rs_momentum
                it["quadrant"] = _classify_quadrant(rs_score, rs_momentum)

            # --- OBV-based volume signal ---
            asset_pv = prices_with_volume.get(iid, [])
            if asset_pv:
                it["volume_signal"] = _compute_obv_signal(asset_pv)

            # --- Standard return calculations ---
            for period_key, days in _PERIOD_DAYS.items():
                ret = _compute_return(asset_prices, days)
                it[f"return_{period_key}"] = ret

                # Excess return
                if bid and bid in prices:
                    bench_ret = _compute_return(prices[bid], days)
                    if ret is not None and bench_ret is not None:
                        it[f"excess_{period_key}"] = round(ret - bench_ret, 2)

            # Absolute and relative returns (3M as primary signal)
            abs_ret = it.get("return_3m") or it.get("return_1m")
            it["absolute_return"] = abs_ret
            it["relative_return"] = it.get("excess_3m") or it.get("excess_1m")

            # Apply computed regime
            it["regime"] = regime

            # Recalculate action with v2 RS score + OBV volume + regime
            action, reason = _derive_action_gate(
                abs_ret, it["rs_score"], it["rs_momentum"],
                it["volume_signal"], regime,
            )
            it["action"] = action
            it["action_reason"] = reason

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
                sector_slugs = SECTOR_GROUP_MAP.get(sector, [sector])
                conditions.append(Instrument.sector.in_(sector_slugs))

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
        period: str = "3m",
    ) -> list[dict[str, Any]]:
        """Return canonical country index rankings."""
        items = await self._get_rankings_by_ids(
            CANONICAL_COUNTRY_INDICES, as_of=as_of
        )
        return await self._enrich_with_returns(items, benchmark_override=benchmark, period=period)

    async def get_sector_rankings(
        self, country_code: str, as_of: datetime.date | None = None,
        benchmark: str | None = None,
        period: str = "3m",
    ) -> list[dict[str, Any]]:
        """Return sector rankings for a country.

        Strategy: first try canonical IDs, then fall back to dynamic query
        for any instrument in this country with a non-null GICS sector.
        """
        canonical_ids = CANONICAL_SECTORS.get(country_code)
        if canonical_ids is not None:
            items = await self._get_rankings_by_ids(canonical_ids, as_of=as_of)
            if items:
                return await self._enrich_with_returns(items, benchmark_override=benchmark, period=period)

        # Dynamic fallback: get best ETF per GICS sector in this country
        items = await self._get_rankings_filtered(
            country=country_code,
            asset_types=("sector_etf", "sector_index", "etf"),
        )
        # Deduplicate: keep the highest-RS ETF per sector
        seen_sectors: dict[str, dict[str, Any]] = {}
        for item in items:
            sector = item.get("sector")
            if not sector:
                continue
            if sector not in seen_sectors or item["rs_score"] > seen_sectors[sector]["rs_score"]:
                seen_sectors[sector] = item
        deduped = sorted(seen_sectors.values(), key=lambda x: x["rs_score"], reverse=True)
        return await self._enrich_with_returns(deduped or items, benchmark_override=benchmark, period=period)

    async def get_stock_rankings(
        self, country_code: str, sector: str,
        benchmark: str | None = None,
        period: str = "3m",
    ) -> list[dict[str, Any]]:
        """Return stock rankings for a country+sector."""
        items = await self._get_rankings_filtered(
            country=country_code,
            asset_types=("stock",),
            sector=sector,
        )
        return await self._enrich_with_returns(items, benchmark_override=benchmark, period=period)

    async def get_global_sector_rankings(
        self, benchmark: str | None = None,
        period: str = "3m",
    ) -> list[dict[str, Any]]:
        """Return global sector ETF rankings."""
        items = await self._get_rankings_by_ids(CANONICAL_GLOBAL_SECTORS)
        return await self._enrich_with_returns(items, benchmark_override=benchmark, period=period)

    async def get_all_etf_rankings(
        self, period: str = "3m",
    ) -> list[dict[str, Any]]:
        """Return all ETF rankings — the main output screen."""
        items = await self._get_rankings_filtered(
            asset_types=(
                "sector_etf", "sector_index", "country_etf", "global_sector_etf",
                "etf", "regional_etf", "commodity_etf", "bond_etf",
            ),
        )
        return await self._enrich_with_returns(items, period=period)

    async def get_top_etfs(
        self, action_filter: str | None = None,
        country_filter: str | None = None,
        sector_filter: str | None = None,
        limit: int = 50,
        period: str = "3m",
    ) -> list[dict[str, Any]]:
        """Return top ETFs with optional action/country/sector filters."""
        if self._session is None:
            return []
        try:
            conditions = [Instrument.is_active == True]
            conditions.append(
                Instrument.asset_type.in_((
                    "sector_etf", "sector_index", "country_etf", "global_sector_etf",
                    "etf", "regional_etf", "commodity_etf", "bond_etf",
                ))
            )
            if country_filter:
                conditions.append(Instrument.country == country_filter)
            if sector_filter:
                # Expand sector groups: "gold" → ["gold", "gold_miners", ...]
                sector_slugs = SECTOR_GROUP_MAP.get(sector_filter, [sector_filter])
                conditions.append(Instrument.sector.in_(sector_slugs))

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

            items = items[:limit]
            return await self._enrich_with_returns(items, period=period)
        except Exception as e:
            logger.debug("Top ETFs query failed: %s", e)
            return []
