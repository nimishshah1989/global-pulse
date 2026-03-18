"""Seed the database with REAL fetched data only — no sample/synthetic data.

Phase 1: Only Level 1-2 instruments (indices + ETFs), no stocks.
Loads OHLCV from data/fetched/ CSVs, computes RS scores, generates signals.

Usage: python -m scripts.seed_real_data
"""

import asyncio
import json
import logging
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

import polars as pl
from sqlalchemy import text

from config import get_settings
from db.models import Base
from db.session import get_engine, get_session_factory
from engine.rs_calculator import RSCalculator
from engine.volume_analyzer import VolumeAnalyzer
from engine.quadrant_classifier import classify_quadrant
from engine.liquidity_scorer import LiquidityScorer
from engine.regime_filter import calculate_regime
from engine.opportunity_scanner import OpportunityScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INSTRUMENT_MAP_PATH = _backend_root / "data" / "instrument_map.json"
FETCHED_DIR = _backend_root / "data" / "fetched"


def load_csv_to_polars(csv_path: Path) -> pl.DataFrame | None:
    """Load a fetched CSV into a Polars DataFrame with normalized columns."""
    try:
        df = pl.read_csv(csv_path, try_parse_dates=True)
    except Exception as e:
        logger.debug("Failed to read %s: %s", csv_path.name, e)
        return None

    # Normalize column names to lowercase
    col_map = {c: c.lower().strip() for c in df.columns}
    df = df.rename(col_map)

    # Must have date and close
    if "date" not in df.columns or "close" not in df.columns:
        return None

    # Ensure date column is Date type
    if df["date"].dtype == pl.Utf8:
        try:
            df = df.with_columns(pl.col("date").str.to_date())
        except Exception:
            return None

    # Ensure numeric columns
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        if col in df.columns:
            if df[col].dtype == pl.Utf8:
                df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))
            elif df[col].dtype not in (pl.Float64, pl.Float32, pl.Int64, pl.Int32):
                try:
                    df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))
                except Exception:
                    pass

    # Sort by date, drop nulls in close
    df = df.sort("date").drop_nulls(subset=["close"])

    if df.height < 20:
        return None

    return df


async def main() -> None:
    """Seed database with real fetched data for Level 1-2 instruments."""
    logger.info("=== Seeding database with REAL data (Level 1-2 only) ===")

    # Load instrument map — Level 1-2 only
    with open(INSTRUMENT_MAP_PATH) as f:
        all_instruments = json.load(f)

    instruments = [i for i in all_instruments if i.get("hierarchy_level", 0) in (1, 2)]
    logger.info("Level 1-2 instruments: %d (out of %d total)", len(instruments), len(all_instruments))

    # Find which have fetched CSVs
    available_csvs = {p.stem: p for p in FETCHED_DIR.glob("*.csv")} if FETCHED_DIR.exists() else {}
    logger.info("Available CSV files: %d", len(available_csvs))

    # Load data
    price_data: dict[str, pl.DataFrame] = {}
    for inst in instruments:
        iid = inst["id"]
        if iid in available_csvs:
            df = load_csv_to_polars(available_csvs[iid])
            if df is not None:
                price_data[iid] = df

    logger.info("Loaded real price data for %d instruments", len(price_data))

    # Filter instruments to only those with data
    instruments_with_data = [i for i in instruments if i["id"] in price_data]
    logger.info("Instruments with sufficient data: %d", len(instruments_with_data))

    if not instruments_with_data:
        logger.error("No instruments with data found. Run fetch first.")
        return

    # Step 1: Create tables
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created/verified.")

    # Step 2: Seed instruments (all Level 1-2, even without data)
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("DELETE FROM opportunities"))
        await session.execute(text("DELETE FROM rs_scores"))
        await session.execute(text("DELETE FROM prices"))
        await session.execute(text("DELETE FROM basket_positions"))
        await session.execute(text("DELETE FROM basket_nav"))
        await session.execute(text("DELETE FROM baskets"))
        await session.execute(text("DELETE FROM constituents"))
        await session.execute(text("DELETE FROM instruments"))
        await session.commit()

        for inst in instruments:
            await session.execute(
                text("""
                    INSERT INTO instruments
                    (id, name, ticker_stooq, ticker_yfinance, source, asset_type,
                     country, sector, hierarchy_level, benchmark_id, currency,
                     liquidity_tier, is_active)
                    VALUES (:id, :name, :ticker_stooq, :ticker_yfinance, :source,
                            :asset_type, :country, :sector, :hierarchy_level, NULL,
                            :currency, :liquidity_tier, :is_active)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name, source = EXCLUDED.source,
                        asset_type = EXCLUDED.asset_type
                """),
                {
                    "id": inst["id"],
                    "name": inst["name"],
                    "ticker_stooq": inst.get("ticker_stooq"),
                    "ticker_yfinance": inst.get("ticker_yfinance"),
                    "source": inst["source"],
                    "asset_type": inst["asset_type"],
                    "country": inst.get("country"),
                    "sector": inst.get("sector"),
                    "hierarchy_level": inst["hierarchy_level"],
                    "currency": inst.get("currency", "USD"),
                    "liquidity_tier": inst.get("liquidity_tier", 2),
                    "is_active": True,
                },
            )
        await session.commit()

        # Set benchmark_id references
        valid_ids = {i["id"] for i in instruments}
        for inst in instruments:
            bench = inst.get("benchmark_id")
            if bench and bench in valid_ids:
                await session.execute(
                    text("UPDATE instruments SET benchmark_id = :bench WHERE id = :id"),
                    {"bench": bench, "id": inst["id"]},
                )
        await session.commit()
        logger.info("Seeded %d instruments.", len(instruments))

    # Step 3: Seed REAL prices
    async with factory() as session:
        total_rows = 0
        for inst in instruments_with_data:
            iid = inst["id"]
            df = price_data[iid]
            rows = df.to_dicts()
            for row in rows:
                await session.execute(
                    text("""
                        INSERT INTO prices
                        (instrument_id, date, open, high, low, close, volume)
                        VALUES (:iid, :date, :open, :high, :low, :close, :volume)
                        ON CONFLICT (instrument_id, date) DO UPDATE SET
                            open = EXCLUDED.open, high = EXCLUDED.high,
                            low = EXCLUDED.low, close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """),
                    {
                        "iid": iid,
                        "date": row["date"],
                        "open": float(row["open"]) if row.get("open") is not None else None,
                        "high": float(row["high"]) if row.get("high") is not None else None,
                        "low": float(row["low"]) if row.get("low") is not None else None,
                        "close": float(row["close"]),
                        "volume": int(row["volume"]) if row.get("volume") is not None else None,
                    },
                )
            total_rows += len(rows)

            if total_rows % 10000 == 0:
                await session.commit()
                logger.info("  ... inserted %d price rows", total_rows)

        await session.commit()
        logger.info("Seeded %d real price rows for %d instruments.", total_rows, len(instruments_with_data))

    # Step 4: Compute RS scores
    logger.info("Computing RS scores on real data...")
    calculator = RSCalculator()
    volume_analyzer = VolumeAnalyzer()
    liquidity_scorer = LiquidityScorer()

    # Peer groups
    by_level_country: dict[tuple[int, str | None], list[dict]] = {}
    for inst in instruments_with_data:
        key = (inst["hierarchy_level"], inst.get("country"))
        by_level_country.setdefault(key, []).append(inst)

    # Regime
    regime = "RISK_ON"
    acwi_id = "ACWI"
    if acwi_id in price_data:
        acwi_df = price_data[acwi_id].select(["date", "close"]).cast({"close": pl.Float64})
        regime = calculate_regime(acwi_df)
    logger.info("Global regime: %s", regime)

    all_scores: list[dict] = []
    for inst in instruments_with_data:
        iid = inst["id"]
        asset_df = price_data[iid]

        bench_id = inst.get("benchmark_id")
        if not bench_id or bench_id not in price_data:
            bench_id = iid
        bench_df = price_data[bench_id]

        asset_prices = asset_df.select(["date", "close"]).cast({"close": pl.Float64})
        bench_prices = bench_df.select(["date", "close"]).cast({"close": pl.Float64})

        key = (inst["hierarchy_level"], inst.get("country"))
        peers = by_level_country.get(key, [inst])
        peer_data: dict[str, pl.DataFrame] = {}
        for peer in peers:
            pid = peer["id"]
            if pid in price_data:
                peer_data[pid] = price_data[pid].select(["date", "close"]).cast({"close": pl.Float64})

        try:
            rs_result = calculator.compute_rs_scores(iid, asset_prices, bench_prices, peer_data)
        except Exception as e:
            logger.debug("RS calc failed for %s: %s", iid, e)
            continue

        rs_trend_df = rs_result["rs_trend_df"]
        latest_rs_line = latest_rs_ma = latest_trend = None
        if rs_trend_df.height > 0:
            last_row = rs_trend_df.tail(1)
            latest_rs_line = last_row["rs_line"][0]
            latest_rs_ma = last_row["rs_ma_150"][0] if last_row["rs_ma_150"][0] is not None else None
            latest_trend = last_row["rs_trend"][0]

        pcts = rs_result["percentile_ranks"]
        pct_1m = pcts.get("1M", Decimal("50"))
        pct_3m = pcts.get("3M", Decimal("50"))
        pct_6m = pcts.get("6M", Decimal("50"))
        pct_12m = pcts.get("12M", Decimal("50"))
        composite = rs_result["rs_composite"]

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
            recent_20 = asset_df.tail(20)
            try:
                close_vals = recent_20["close"].cast(pl.Float64)
                vol_vals = recent_20["volume"].cast(pl.Float64)
                avg_daily_val = (close_vals * vol_vals).mean()
                if avg_daily_val is not None:
                    liq_tier = liquidity_scorer.calculate_liquidity_tier(Decimal(str(avg_daily_val)))
            except Exception:
                pass

        adjusted_rs = volume_analyzer.calculate_adjusted_rs_score(composite, vol_multiplier, liq_tier)

        rs_momentum = Decimal("0")
        excess = rs_result["excess_returns"]
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

    # Insert RS scores
    async with factory() as session:
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
        logger.info("Seeded %d RS scores.", len(all_scores))

    # Step 5: Generate opportunities
    logger.info("Generating opportunity signals...")
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
            import uuid
            from datetime import datetime, timezone

            for sig in signals:
                metadata_val = sig.get("metadata", {})
                clean_meta = {}
                for k, v in metadata_val.items():
                    clean_meta[k] = str(v) if isinstance(v, Decimal) else v

                await session.execute(
                    text("""
                        INSERT INTO opportunities
                        (id, instrument_id, date, signal_type, conviction_score,
                         description, metadata, created_at)
                        VALUES (:id, :instrument_id, :date, :signal_type,
                                :conviction_score, :description, :metadata, :created_at)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "instrument_id": sig["instrument_id"],
                        "date": all_scores[0]["date"] if all_scores else date(2026, 3, 18),
                        "signal_type": sig["signal_type"],
                        "conviction_score": float(sig["conviction_score"]),
                        "description": sig["description"],
                        "metadata": json.dumps(clean_meta),
                        "created_at": datetime.now(tz=timezone.utc).isoformat(),
                    },
                )
            await session.commit()
            logger.info("Seeded %d opportunity signals.", len(signals))
    else:
        logger.info("No opportunity signals generated.")

    # Verify
    logger.info("=== Verification ===")
    async with engine.connect() as conn:
        for table in ["instruments", "prices", "rs_scores", "opportunities"]:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            logger.info("  %s: %d rows", table, count)

    logger.info("=== Real data seed complete ===")


if __name__ == "__main__":
    asyncio.run(main())
