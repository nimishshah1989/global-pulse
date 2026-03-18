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

MIN_PRICE_ROWS = 100
ACWI_ID = "ACWI"
DEFAULT_PCT = Decimal("50")
EMPTY_PRICES = pl.DataFrame({"date": [], "close": [], "volume": []}).cast(
    {"date": pl.Date, "close": pl.Float64, "volume": pl.Int64}
)


async def _fetch_prices(session: AsyncSession, iid: str) -> pl.DataFrame:
    """Fetch OHLCV prices as a Polars DataFrame with [date, close, volume]."""
    rows = (await session.execute(
        select(Price.date, Price.close, Price.volume)
        .where(Price.instrument_id == iid).order_by(Price.date)
    )).all()
    if not rows:
        return EMPTY_PRICES.clone()
    return pl.DataFrame({
        "date": [r[0] for r in rows],
        "close": [float(r[1]) if r[1] is not None else None for r in rows],
        "volume": [int(r[2]) if r[2] is not None else 0 for r in rows],
    }).cast({"date": pl.Date, "close": pl.Float64, "volume": pl.Int64})


async def _fetch_prev_composites(session: AsyncSession, iid: str) -> pl.DataFrame:
    """Fetch recent historical rs_composite values for momentum calc."""
    rows = (await session.execute(
        select(RSScore.date, RSScore.rs_composite)
        .where(RSScore.instrument_id == iid, RSScore.rs_composite.is_not(None))
        .order_by(RSScore.date.desc()).limit(25)
    )).all()
    if not rows:
        return pl.DataFrame({"date": [], "rs_composite": []}).cast(
            {"date": pl.Date, "rs_composite": pl.Float64}
        )
    return pl.DataFrame({
        "date": [r[0] for r in rows],
        "rs_composite": [float(r[1]) for r in rows],
    }).cast({"date": pl.Date, "rs_composite": pl.Float64}).sort("date")


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
            groups.setdefault(f"sector_{inst.get('country') or 'global'}", []).append(iid)
        elif inst["hierarchy_level"] == 3:
            sector = inst.get("sector") or "unknown"
            country = inst.get("country") or "unknown"
            groups.setdefault(f"stock_{country}_{sector}", []).append(iid)
    return groups


def _peer_key(inst: dict) -> str:
    """Return the peer group key for an instrument."""
    if inst["hierarchy_level"] == 1 and inst["asset_type"] == "country_index":
        return "country_indices"
    if inst["hierarchy_level"] == 2:
        return f"sector_{inst.get('country') or 'global'}"
    if inst["hierarchy_level"] == 3:
        sector = inst.get("sector") or "unknown"
        country = inst.get("country") or "unknown"
        return f"stock_{country}_{sector}"
    return f"_solo_{inst['id']}"


def _dec(val: float | None, places: str = "0.0001") -> Decimal | None:
    if val is None:
        return None
    return Decimal(str(val)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


async def compute_all(session: AsyncSession) -> int:
    """Run full RS computation pipeline. Returns count of scores written."""
    inst_map_path = Path(__file__).resolve().parent.parent / "data" / "instrument_map.json"
    with open(inst_map_path) as f:
        all_instruments: list[dict] = json.load(f)

    # Only process instruments that exist in the DB (not all 9800+ from the map)
    from sqlalchemy import text
    db_ids_result = (await session.execute(text("SELECT id FROM instruments"))).all()
    db_ids = {r[0] for r in db_ids_result}
    instruments = [i for i in all_instruments if i["id"] in db_ids]
    logger.info("Instruments in DB: %d (out of %d in map)", len(instruments), len(all_instruments))

    # Only fetch prices for instruments that actually have price data
    price_ids_result = (await session.execute(
        text("SELECT instrument_id, COUNT(*) as cnt FROM prices GROUP BY instrument_id HAVING COUNT(*) >= :min"),
        {"min": MIN_PRICE_ROWS},
    )).all()
    ids_with_prices = {r[0] for r in price_ids_result}
    logger.info("Instruments with %d+ price rows: %d", MIN_PRICE_ROWS, len(ids_with_prices))

    # Also fetch benchmark prices
    bench_ids = {i.get("benchmark_id") for i in instruments if i.get("benchmark_id")}
    fetch_ids = (ids_with_prices | bench_ids) & db_ids
    # Add ACWI even if not in db_ids
    fetch_ids.add(ACWI_ID)

    logger.info("Fetching prices for %d instruments...", len(fetch_ids))
    prices: dict[str, pl.DataFrame] = {}
    for iid in fetch_ids:
        prices[iid] = await _fetch_prices(session, iid)

    # Stage 9: Global regime
    acwi_df = prices.get(ACWI_ID, pl.DataFrame())
    regime = calculate_regime(acwi_df) if acwi_df.height >= MIN_PRICE_ROWS else "RISK_ON"
    logger.info("Global regime: %s", regime)

    calc, vol_a, liq_s = RSCalculator(), VolumeAnalyzer(), LiquidityScorer()
    peer_groups = _build_peer_groups(instruments)

    # Pre-compute excess returns for instruments with enough data
    excess: dict[str, dict[str, Decimal]] = {}
    for inst in instruments:
        iid = inst["id"]
        bid = inst.get("benchmark_id")
        if bid and bid in prices and iid in prices and prices[iid].height >= MIN_PRICE_ROWS:
            excess[iid] = calc.calculate_excess_returns(prices[iid], prices[bid])

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
        rs_line_v = _dec(lt["rs_line"][0]) if lt.height else None
        rs_ma_v = _dec(lt["rs_ma_150"][0]) if lt.height else None
        rs_trend_v = lt["rs_trend"][0] if lt.height else None

        # Stage 3: Percentile ranks within peer group
        peers = peer_groups.get(_peer_key(inst), [iid])
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

        # Stage 5: RS Momentum from historical composites
        prev = await _fetch_prev_composites(session, iid)
        today_row = pl.DataFrame({"date": [today], "rs_composite": [float(composite)]}).cast(
            {"date": pl.Date, "rs_composite": pl.Float64}
        )
        comp_series = pl.concat([prev, today_row]).unique("date").sort("date")
        mom_df = calc.calculate_momentum(comp_series, lookback=20)
        mom_latest = mom_df.filter(pl.col("rs_momentum").is_not_null()).tail(1)
        rs_momentum = Decimal(str(mom_latest["rs_momentum"][0])) if mom_latest.height else Decimal("0")

        # Stage 6: Volume
        vol_ratio = vol_a.calculate_volume_ratio(adf.select(["date", "volume"]))
        vol_mult = vol_a.calculate_vol_multiplier(vol_ratio)

        # Stage 8: Liquidity tier
        adv = Decimal("0")
        if adf.height >= 20:
            t20 = adf.tail(20)
            adv = Decimal(str((t20["close"] * t20["volume"].cast(pl.Float64)).mean()))
        liq_tier = liq_s.calculate_liquidity_tier(adv)

        # Adjusted score + quadrant + extension
        adjusted = vol_a.calculate_adjusted_rs_score(composite, vol_mult, liq_tier)
        quadrant = classify_quadrant(adjusted, rs_momentum)
        ext_warn = liq_s.check_extension_warning(
            pct.get("3M", Decimal("0")), pct.get("6M", Decimal("0")), pct.get("12M", Decimal("0")),
        )

        records.append(RSScore(
            instrument_id=iid, date=today,
            rs_line=rs_line_v, rs_ma_150=rs_ma_v, rs_trend=rs_trend_v,
            rs_pct_1m=pct["1M"], rs_pct_3m=pct["3M"],
            rs_pct_6m=pct["6M"], rs_pct_12m=pct["12M"],
            rs_composite=composite, rs_momentum=rs_momentum,
            volume_ratio=vol_ratio, vol_multiplier=vol_mult,
            adjusted_rs_score=adjusted, quadrant=quadrant,
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
