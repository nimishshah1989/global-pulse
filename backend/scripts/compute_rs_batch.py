"""Batch RS score computation — optimized for large instrument universes.

Pre-computes peer group excess returns ONCE per group, then assigns
percentile ranks to each instrument. O(n) per group instead of O(n²).

Usage: python -m scripts.compute_rs_batch
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

import polars as pl
from sqlalchemy import text

from db.session import get_engine, get_session_factory
from engine.rs_calculator import (
    RSCalculator,
    TRADING_DAYS_1M, TRADING_DAYS_3M, TRADING_DAYS_6M, TRADING_DAYS_12M,
    WEIGHT_1M, WEIGHT_3M, WEIGHT_6M, WEIGHT_12M,
)
from engine.volume_analyzer import VolumeAnalyzer
from engine.quadrant_classifier import classify_quadrant
from engine.liquidity_scorer import LiquidityScorer
from engine.regime_filter import calculate_regime
from engine.opportunity_scanner import OpportunityScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INSTRUMENT_MAP_PATH = _backend_root / "data" / "instrument_map.json"
FETCHED_DIR = _backend_root / "data" / "fetched"


def load_csv(csv_path: Path) -> pl.DataFrame | None:
    """Load CSV into Polars with normalization."""
    try:
        df = pl.read_csv(csv_path, try_parse_dates=True)
    except Exception:
        return None
    col_map = {c: c.lower().strip() for c in df.columns}
    df = df.rename(col_map)
    if "date" not in df.columns or "close" not in df.columns:
        return None
    if df["date"].dtype == pl.Utf8:
        try:
            df = df.with_columns(pl.col("date").str.to_date())
        except Exception:
            return None
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns and df[col].dtype != pl.Float64:
            try:
                df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))
            except Exception:
                pass
    df = df.sort("date").drop_nulls(subset=["close"])
    return df if df.height >= 20 else None


def compute_excess_return(
    asset_prices: pl.DataFrame,
    bench_prices: pl.DataFrame,
    days: int,
) -> Decimal | None:
    """Compute excess return for one timeframe."""
    # Align dates
    merged = asset_prices.join(bench_prices, on="date", suffix="_bench")
    if merged.height < days:
        return None
    recent = merged.tail(days)
    if recent.height < days:
        return None
    a_start = recent["close"][0]
    a_end = recent["close"][-1]
    b_start = recent["close_bench"][0]
    b_end = recent["close_bench"][-1]
    if a_start == 0 or b_start == 0:
        return None
    a_ret = (a_end - a_start) / a_start
    b_ret = (b_end - b_start) / b_start
    return Decimal(str(round(a_ret - b_ret, 8)))


def percentile_rank(value: Decimal, population: list[Decimal]) -> Decimal:
    """Distribution-agnostic percentile rank."""
    if not population:
        return Decimal("50")
    n = len(population)
    below = sum(1 for v in population if v < value)
    equal = sum(1 for v in population if v == value)
    rank = (below + equal * Decimal("0.5")) / n * 100
    return rank.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def main() -> None:
    """Batch compute RS scores using optimized peer group approach."""
    logger.info("=== Batch RS Computation (Optimized) ===")

    # Load instruments (Level 1-2 only)
    with open(INSTRUMENT_MAP_PATH) as f:
        all_instruments = json.load(f)
    instruments = [i for i in all_instruments if i.get("hierarchy_level", 0) in (1, 2)]

    # Load price data
    available_csvs = {p.stem: p for p in FETCHED_DIR.glob("*.csv")}
    price_data: dict[str, pl.DataFrame] = {}
    for inst in instruments:
        iid = inst["id"]
        if iid in available_csvs:
            df = load_csv(available_csvs[iid])
            if df is not None:
                price_data[iid] = df

    instruments_with_data = [i for i in instruments if i["id"] in price_data]
    logger.info("Instruments with data: %d", len(instruments_with_data))

    # Regime
    regime = "RISK_ON"
    if "ACWI" in price_data:
        acwi_df = price_data["ACWI"].select(["date", "close"])
        regime = calculate_regime(acwi_df)
    logger.info("Regime: %s", regime)

    # Group by peer group key: (hierarchy_level, country)
    peer_groups: dict[tuple[int, str | None], list[dict]] = {}
    for inst in instruments_with_data:
        key = (inst["hierarchy_level"], inst.get("country"))
        peer_groups.setdefault(key, []).append(inst)

    logger.info("Peer groups: %d", len(peer_groups))

    calculator = RSCalculator()
    volume_analyzer = VolumeAnalyzer()
    liquidity_scorer = LiquidityScorer()
    all_scores: list[dict] = []

    timeframes = {
        "1M": TRADING_DAYS_1M,
        "3M": TRADING_DAYS_3M,
        "6M": TRADING_DAYS_6M,
        "12M": TRADING_DAYS_12M,
    }

    group_count = 0
    for (level, country), group_instruments in peer_groups.items():
        group_count += 1
        if group_count % 10 == 0:
            logger.info(
                "Processing peer group %d/%d (level=%d, country=%s, n=%d)",
                group_count, len(peer_groups), level, country, len(group_instruments),
            )

        # Step 1: Pre-compute ALL excess returns for this peer group
        # Key optimization: compute once, rank later
        group_excess: dict[str, dict[str, Decimal]] = {}  # iid -> {tf -> excess}

        for inst in group_instruments:
            iid = inst["id"]
            asset_df = price_data[iid].select(["date", "close"])

            bench_id = inst.get("benchmark_id")
            if not bench_id or bench_id not in price_data:
                bench_id = iid
            bench_df = price_data[bench_id].select(["date", "close"])

            excess: dict[str, Decimal] = {}
            for tf, days in timeframes.items():
                er = compute_excess_return(asset_df, bench_df, days)
                if er is not None:
                    excess[tf] = er
            group_excess[iid] = excess

        # Step 2: Build population lists per timeframe
        tf_populations: dict[str, list[Decimal]] = {tf: [] for tf in timeframes}
        for iid, excess in group_excess.items():
            for tf, val in excess.items():
                tf_populations[tf].append(val)

        # Step 3: Compute percentile ranks + composite for each instrument
        for inst in group_instruments:
            iid = inst["id"]
            excess = group_excess.get(iid, {})
            asset_df = price_data[iid]

            bench_id = inst.get("benchmark_id")
            if not bench_id or bench_id not in price_data:
                bench_id = iid
            bench_df = price_data[bench_id]

            # RS Line & Trend
            try:
                asset_prices = asset_df.select(["date", "close"])
                bench_prices = bench_df.select(["date", "close"])
                rs_line_df = calculator.calculate_rs_line(asset_prices, bench_prices)
                rs_trend_df = calculator.calculate_rs_trend(rs_line_df)
            except Exception:
                continue

            latest_rs_line = latest_rs_ma = latest_trend = None
            if rs_trend_df.height > 0:
                last_row = rs_trend_df.tail(1)
                latest_rs_line = last_row["rs_line"][0]
                latest_rs_ma = last_row["rs_ma_150"][0]
                latest_trend = last_row["rs_trend"][0]

            # Percentile ranks
            pcts = {}
            for tf in timeframes:
                if tf in excess:
                    pcts[tf] = percentile_rank(excess[tf], tf_populations[tf])
                else:
                    pcts[tf] = Decimal("50")

            pct_1m = pcts.get("1M", Decimal("50"))
            pct_3m = pcts.get("3M", Decimal("50"))
            pct_6m = pcts.get("6M", Decimal("50"))
            pct_12m = pcts.get("12M", Decimal("50"))

            composite = (
                pct_1m * WEIGHT_1M +
                pct_3m * WEIGHT_3M +
                pct_6m * WEIGHT_6M +
                pct_12m * WEIGHT_12M
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Volume
            if "volume" in asset_df.columns:
                vol_df = asset_df.select(["date", "volume"]).cast({"volume": pl.Float64})
                volume_ratio = volume_analyzer.calculate_volume_ratio(vol_df)
            else:
                volume_ratio = Decimal("1.0")
            vol_multiplier = volume_analyzer.calculate_vol_multiplier(volume_ratio)

            # Liquidity
            liq_tier = inst.get("liquidity_tier", 2)
            if asset_df.height >= 20 and "volume" in asset_df.columns:
                try:
                    recent_20 = asset_df.tail(20)
                    close_vals = recent_20["close"].cast(pl.Float64)
                    vol_vals = recent_20["volume"].cast(pl.Float64)
                    avg_daily_val = (close_vals * vol_vals).mean()
                    if avg_daily_val is not None:
                        liq_tier = liquidity_scorer.calculate_liquidity_tier(Decimal(str(avg_daily_val)))
                except Exception:
                    pass

            adjusted_rs = volume_analyzer.calculate_adjusted_rs_score(composite, vol_multiplier, liq_tier)

            # Momentum
            rs_momentum = Decimal("0")
            if "1M" in excess:
                rs_momentum = (excess["1M"] * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                rs_momentum = max(Decimal("-50"), min(Decimal("50"), rs_momentum))

            quadrant = classify_quadrant(adjusted_rs, rs_momentum)
            extension = liquidity_scorer.check_extension_warning(pct_3m, pct_6m, pct_12m)

            dates = asset_df["date"].to_list()
            latest_date = dates[-1] if dates else date(2026, 3, 18)

            all_scores.append({
                "instrument_id": iid,
                "date": latest_date,
                "rs_line": float(latest_rs_line) if latest_rs_line is not None else None,
                "rs_ma_150": float(latest_rs_ma) if latest_rs_ma is not None else None,
                "rs_trend": latest_trend,
                "rs_pct_1m": float(pct_1m),
                "rs_pct_3m": float(pct_3m),
                "rs_pct_6m": float(pct_6m),
                "rs_pct_12m": float(pct_12m),
                "rs_composite": float(composite),
                "rs_momentum": float(rs_momentum),
                "volume_ratio": float(volume_ratio),
                "vol_multiplier": float(vol_multiplier),
                "adjusted_rs_score": float(adjusted_rs),
                "quadrant": quadrant,
                "liquidity_tier": liq_tier,
                "extension_warning": extension,
                "regime": regime,
                "name": inst["name"],
                "country": inst.get("country"),
                "sector": inst.get("sector"),
                "hierarchy_level": inst["hierarchy_level"],
                "asset_type": inst.get("asset_type"),
            })

    logger.info("Computed RS scores for %d instruments.", len(all_scores))

    # Insert into DB
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("DELETE FROM rs_scores"))
        await session.commit()

        for sc in all_scores:
            await session.execute(
                text("""
                    INSERT INTO rs_scores
                    (instrument_id, date, rs_line, rs_ma_150, rs_trend,
                     rs_pct_1m, rs_pct_3m, rs_pct_6m, rs_pct_12m,
                     rs_composite, rs_momentum, volume_ratio, vol_multiplier,
                     adjusted_rs_score, quadrant, liquidity_tier,
                     extension_warning, regime)
                    VALUES (:instrument_id, :date, :rs_line, :rs_ma_150, :rs_trend,
                            :rs_pct_1m, :rs_pct_3m, :rs_pct_6m, :rs_pct_12m,
                            :rs_composite, :rs_momentum, :volume_ratio, :vol_multiplier,
                            :adjusted_rs_score, :quadrant, :liquidity_tier,
                            :extension_warning, :regime)
                    ON CONFLICT (instrument_id, date) DO UPDATE SET
                        rs_line = EXCLUDED.rs_line, rs_ma_150 = EXCLUDED.rs_ma_150,
                        rs_trend = EXCLUDED.rs_trend, rs_composite = EXCLUDED.rs_composite,
                        adjusted_rs_score = EXCLUDED.adjusted_rs_score,
                        quadrant = EXCLUDED.quadrant, regime = EXCLUDED.regime
                """),
                {k: sc[k] for k in [
                    "instrument_id", "date", "rs_line", "rs_ma_150", "rs_trend",
                    "rs_pct_1m", "rs_pct_3m", "rs_pct_6m", "rs_pct_12m",
                    "rs_composite", "rs_momentum", "volume_ratio", "vol_multiplier",
                    "adjusted_rs_score", "quadrant", "liquidity_tier",
                    "extension_warning", "regime",
                ]},
            )
        await session.commit()
        logger.info("Inserted %d RS scores into database.", len(all_scores))

    # Generate opportunities
    logger.info("Generating opportunities...")
    scanner = OpportunityScanner()
    country_scores = [s for s in all_scores if s.get("hierarchy_level") == 1]
    sector_scores = [s for s in all_scores if s.get("hierarchy_level") == 2]

    previous_scores = []
    for s in all_scores:
        prev = dict(s)
        if prev["quadrant"] == "LEADING":
            prev["quadrant"] = "IMPROVING"
        elif prev["quadrant"] == "IMPROVING":
            prev["quadrant"] = "LAGGING"
        previous_scores.append(prev)

    signals = []
    signals.extend(scanner.scan_quadrant_entries(all_scores, previous_scores))
    signals.extend(scanner.scan_volume_breakouts(all_scores))
    signals.extend(scanner.scan_multi_level_alignments(country_scores, sector_scores, []))
    signals.extend(scanner.scan_extension_alerts(all_scores))

    if signals:
        async with factory() as session:
            await session.execute(text("DELETE FROM opportunities"))
            await session.commit()
            for sig in signals:
                meta = sig.get("metadata", {})
                clean_meta = {k: str(v) if isinstance(v, Decimal) else v for k, v in meta.items()}
                await session.execute(
                    text("""
                        INSERT INTO opportunities
                        (id, instrument_id, date, signal_type, conviction_score,
                         description, metadata, created_at)
                        VALUES (:id, :iid, :date, :signal_type, :conviction,
                                :description, :metadata, :created_at)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "iid": sig["instrument_id"],
                        "date": all_scores[0]["date"] if all_scores else date(2026, 3, 18),
                        "signal_type": sig["signal_type"],
                        "conviction": float(sig["conviction_score"]),
                        "description": sig["description"],
                        "metadata": json.dumps(clean_meta),
                        "created_at": datetime.now(tz=timezone.utc).isoformat(),
                    },
                )
            await session.commit()
            logger.info("Inserted %d opportunities.", len(signals))

    # Verify
    engine = get_engine()
    async with engine.connect() as conn:
        for table in ["instruments", "prices", "rs_scores", "opportunities"]:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            logger.info("  %s: %d rows", table, result.scalar())

    # Show top RS scores
    logger.info("=== Top 15 RS Scores ===")
    top = sorted(all_scores, key=lambda s: s["adjusted_rs_score"], reverse=True)[:15]
    for s in top:
        logger.info(
            "  %-25s RS=%.1f Q=%-12s %s %s",
            s["name"][:25], s["adjusted_rs_score"], s["quadrant"],
            s.get("country", ""), s.get("sector", "") or "",
        )

    logger.info("=== Batch RS computation complete ===")


if __name__ == "__main__":
    asyncio.run(main())
