"""Compute RS scores for all instruments and write to the rs_scores table.

Reads price data from SQLite, runs the RS engine (Stages 1-10), and
persists results. Runnable standalone: cd backend && python -m scripts.compute_rs_scores
"""

import asyncio
import json
import logging
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import polars as pl
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings  # noqa: E402
from db.models import Price, RSScore  # noqa: E402
from db.session import get_session_factory  # noqa: E402
from engine.rs_calculator import RSCalculator  # noqa: E402
from engine.volume_analyzer import VolumeAnalyzer  # noqa: E402
from engine.quadrant_classifier import classify_quadrant  # noqa: E402
from engine.liquidity_scorer import LiquidityScorer  # noqa: E402
from engine.regime_filter import calculate_regime  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MIN_PRICE_ROWS = 200
ACWI_ID = "ACWI"
DEFAULT_PCT = Decimal("50")


def _load_instrument_map() -> list[dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "instrument_map.json"
    with open(path) as f:
        return json.load(f)


async def _fetch_prices(session: AsyncSession, instrument_id: str) -> pl.DataFrame:
    """Fetch OHLCV prices as a Polars DataFrame with [date, close, volume]."""
    result = await session.execute(
        select(Price.date, Price.close, Price.volume)
        .where(Price.instrument_id == instrument_id)
        .order_by(Price.date)
    )
    rows = result.all()
    if not rows:
        return pl.DataFrame({"date": [], "close": [], "volume": []}).cast(
            {"date": pl.Date, "close": pl.Float64, "volume": pl.Int64}
        )
    return pl.DataFrame({
        "date": [r[0] for r in rows],
        "close": [float(r[1]) if r[1] is not None else None for r in rows],
        "volume": [int(r[2]) if r[2] is not None else 0 for r in rows],
    }).cast({"date": pl.Date, "close": pl.Float64, "volume": pl.Int64})


def _build_peer_groups(instruments: list[dict]) -> dict[str, list[str]]:
    """Level 1 country_index -> one group; Level 2 sectors -> grouped by country."""
    groups: dict[str, list[str]] = {}
    for inst in instruments:
        if inst.get("benchmark_id") is None:
            continue
        iid = inst["id"]
        if inst["hierarchy_level"] == 1 and inst["asset_type"] == "country_index":
            groups.setdefault("country_indices", []).append(iid)
        elif inst["hierarchy_level"] == 2:
            key = f"sector_{inst.get('country') or 'global'}"
            groups.setdefault(key, []).append(iid)
    return groups


def _peer_group_for(inst: dict, peer_groups: dict[str, list[str]]) -> list[str]:
    if inst["hierarchy_level"] == 1 and inst["asset_type"] == "country_index":
        return peer_groups.get("country_indices", [inst["id"]])
    if inst["hierarchy_level"] == 2:
        return peer_groups.get(f"sector_{inst.get('country') or 'global'}", [inst["id"]])
    return [inst["id"]]


def _dec4(val: float | None) -> float | None:
    if val is None:
        return None
    return float(Decimal(str(val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


async def compute_all(session: AsyncSession) -> int:
    """Run full RS computation pipeline. Returns count of scores written."""
    instruments = _load_instrument_map()

    logger.info("Fetching prices for %d instruments...", len(instruments))
    prices: dict[str, pl.DataFrame] = {}
    for inst in instruments:
        prices[inst["id"]] = await _fetch_prices(session, inst["id"])

    acwi_df = prices.get(ACWI_ID, pl.DataFrame())
    regime = calculate_regime(acwi_df) if acwi_df.height >= MIN_PRICE_ROWS else "RISK_ON"
    logger.info("Global regime: %s", regime)

    calc = RSCalculator()
    vol_a = VolumeAnalyzer()
    liq_s = LiquidityScorer()
    peer_groups = _build_peer_groups(instruments)

    # Pre-compute excess returns for instruments with enough data
    excess: dict[str, dict[str, Decimal]] = {}
    for inst in instruments:
        bid = inst.get("benchmark_id")
        if not bid or bid not in prices or prices[inst["id"]].height < MIN_PRICE_ROWS:
            continue
        excess[inst["id"]] = calc.calculate_excess_returns(prices[inst["id"]], prices[bid])

    today = date.today()
    records: list[RSScore] = []
    computable = [i for i in instruments if i.get("benchmark_id") and i["id"] in excess]
    logger.info("Computing RS scores for %d instruments...", len(computable))

    for inst in computable:
        iid, bid = inst["id"], inst["benchmark_id"]
        adf, bdf = prices[iid], prices[bid]

        # Stages 1-2: RS Line + Trend
        rs_trend_df = calc.calculate_rs_trend(calc.calculate_rs_line(adf, bdf))
        lt = rs_trend_df.filter(pl.col("rs_trend").is_not_null()).tail(1)
        rs_line_v = lt["rs_line"][0] if lt.height > 0 else None
        rs_ma_v = lt["rs_ma_150"][0] if lt.height > 0 else None
        rs_trend_v = lt["rs_trend"][0] if lt.height > 0 else None

        # Stage 3: Percentile ranks
        peers = _peer_group_for(inst, peer_groups)
        er = excess[iid]
        pct: dict[str, Decimal] = {}
        for tf in ("1M", "3M", "6M", "12M"):
            if tf not in er:
                pct[tf] = DEFAULT_PCT
                continue
            peer_ers = [excess[p][tf] for p in peers if p in excess and tf in excess[p]]
            pct[tf] = calc.calculate_percentile_rank(er[tf], peer_ers) if peer_ers else DEFAULT_PCT

        # Stage 4: Composite
        composite = calc.calculate_composite(
            pct.get("1M", DEFAULT_PCT), pct.get("3M", DEFAULT_PCT),
            pct.get("6M", DEFAULT_PCT), pct.get("12M", DEFAULT_PCT),
        )

        # Stage 5: Momentum (no historical composite yet, default 0)
        rs_momentum = Decimal("0")

        # Stage 6: Volume
        vol_ratio = vol_a.calculate_volume_ratio(adf.select(["date", "volume"]))
        vol_mult = vol_a.calculate_vol_multiplier(vol_ratio)

        # Stage 8: Liquidity tier
        if adf.height >= 20:
            t20 = adf.tail(20)
            adv = Decimal(str((t20["close"] * t20["volume"].cast(pl.Float64)).mean()))
        else:
            adv = Decimal("0")
        liq_tier = liq_s.calculate_liquidity_tier(adv)

        adjusted = vol_a.calculate_adjusted_rs_score(composite, vol_mult, liq_tier)
        quadrant = classify_quadrant(adjusted, rs_momentum)
        ext_warn = liq_s.check_extension_warning(
            pct.get("3M", Decimal("0")), pct.get("6M", Decimal("0")),
            pct.get("12M", Decimal("0")),
        )

        records.append(RSScore(
            instrument_id=iid, date=today,
            rs_line=_dec4(rs_line_v), rs_ma_150=_dec4(rs_ma_v), rs_trend=rs_trend_v,
            rs_pct_1m=float(pct["1M"]), rs_pct_3m=float(pct["3M"]),
            rs_pct_6m=float(pct["6M"]), rs_pct_12m=float(pct["12M"]),
            rs_composite=float(composite), rs_momentum=float(rs_momentum),
            volume_ratio=float(vol_ratio), vol_multiplier=float(vol_mult),
            adjusted_rs_score=float(adjusted), quadrant=quadrant,
            liquidity_tier=liq_tier, extension_warning=ext_warn, regime=regime,
        ))

    if records:
        await session.execute(delete(RSScore).where(RSScore.date == today))
        session.add_all(records)
        await session.commit()
        logger.info("Wrote %d RS score records for %s.", len(records), today.isoformat())
    else:
        logger.warning("No instruments had sufficient data for RS computation.")
    return len(records)


async def main() -> None:
    """Entry point for standalone execution."""
    _ = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        count = await compute_all(session)
    logger.info("Done. %d scores computed.", count)


if __name__ == "__main__":
    asyncio.run(main())
