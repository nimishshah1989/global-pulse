"""Seed the database with instruments from instrument_map.json and generate sample data.

This script:
1. Creates all tables
2. Reads instrument_map.json
3. Inserts all instruments into the instruments table
4. Generates 180 days of sample OHLCV data
5. Inserts prices into the prices table
6. Runs the RS engine to compute rs_scores
7. Generates opportunities from the scanner

Usage: python scripts/seed_db.py
"""

import asyncio
import json
import logging
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Ensure backend root is on sys.path
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

import polars as pl
from sqlalchemy import text

from config import get_settings
from db.models import Base, Instrument, Price, RSScore, Opportunity
from db.session import get_engine, get_session_factory
from data.seed_sample import generate_sample_data
from engine.rs_calculator import RSCalculator
from engine.volume_analyzer import VolumeAnalyzer
from engine.quadrant_classifier import classify_quadrant
from engine.liquidity_scorer import LiquidityScorer
from engine.regime_filter import calculate_regime
from engine.opportunity_scanner import OpportunityScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INSTRUMENT_MAP_PATH = _backend_root / "data" / "instrument_map.json"


async def create_tables() -> None:
    """Create all tables from ORM models."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created.")


async def seed_instruments(instruments_data: list[dict]) -> None:
    """Insert instruments into the database."""
    factory = get_session_factory()
    async with factory() as session:
        # Clear existing instruments (cascade will clear related tables)
        await session.execute(text("DELETE FROM opportunities"))
        await session.execute(text("DELETE FROM rs_scores"))
        await session.execute(text("DELETE FROM prices"))
        await session.execute(text("DELETE FROM basket_positions"))
        await session.execute(text("DELETE FROM basket_nav"))
        await session.execute(text("DELETE FROM baskets"))
        await session.execute(text("DELETE FROM constituents"))
        await session.execute(text("DELETE FROM instruments"))
        await session.commit()

        # Insert instruments -- handle benchmark_id ordering
        # First pass: insert all without benchmark_id
        for inst_data in instruments_data:
            inst = Instrument(
                id=inst_data["id"],
                name=inst_data["name"],
                ticker_stooq=inst_data.get("ticker_stooq"),
                ticker_yfinance=inst_data.get("ticker_yfinance"),
                source=inst_data["source"],
                asset_type=inst_data["asset_type"],
                country=inst_data.get("country"),
                sector=inst_data.get("sector"),
                hierarchy_level=inst_data["hierarchy_level"],
                benchmark_id=None,  # set later
                currency=inst_data.get("currency", "USD"),
                liquidity_tier=inst_data.get("liquidity_tier", 2),
                is_active=inst_data.get("is_active", True),
                metadata_=inst_data.get("metadata"),
            )
            session.add(inst)

        await session.commit()

        # Second pass: set benchmark_id references
        valid_ids = {i["id"] for i in instruments_data}
        for inst_data in instruments_data:
            bench_id = inst_data.get("benchmark_id")
            if bench_id and bench_id in valid_ids:
                await session.execute(
                    text("UPDATE instruments SET benchmark_id = :bench WHERE id = :id"),
                    {"bench": bench_id, "id": inst_data["id"]},
                )
        await session.commit()

        logger.info("Seeded %d instruments.", len(instruments_data))


async def seed_prices(
    instruments_data: list[dict], sample_data: dict[str, pl.DataFrame]
) -> None:
    """Insert sample OHLCV data into the prices table."""
    factory = get_session_factory()
    async with factory() as session:
        total = 0
        for inst_data in instruments_data:
            iid = inst_data["id"]
            if iid not in sample_data:
                continue
            df = sample_data[iid]
            rows = df.to_dicts()
            for row in rows:
                await session.execute(
                    text("""
                        INSERT INTO prices
                        (instrument_id, date, open, high, low, close, volume)
                        VALUES (:instrument_id, :date, :open, :high, :low, :close, :volume)
                        ON CONFLICT (instrument_id, date) DO UPDATE SET
                            open = EXCLUDED.open, high = EXCLUDED.high,
                            low = EXCLUDED.low, close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """),
                    {
                        "instrument_id": iid,
                        "date": row["date"],
                        "open": float(row["open"]) if row["open"] is not None else None,
                        "high": float(row["high"]) if row["high"] is not None else None,
                        "low": float(row["low"]) if row["low"] is not None else None,
                        "close": float(row["close"]),
                        "volume": row["volume"],
                    },
                )
            total += len(rows)

            if total % 5000 == 0:
                await session.commit()
                logger.info("  ... inserted %d price rows so far", total)

        await session.commit()
        logger.info("Seeded %d total price rows.", total)


async def compute_and_seed_rs_scores(
    instruments_data: list[dict], sample_data: dict[str, pl.DataFrame]
) -> None:
    """Compute RS scores using the engine modules and insert into rs_scores."""
    calculator = RSCalculator()
    volume_analyzer = VolumeAnalyzer()
    liquidity_scorer = LiquidityScorer()

    # Group instruments by hierarchy level and country for peer groups
    by_level_country: dict[tuple[int, str | None], list[dict]] = {}
    for inst in instruments_data:
        key = (inst["hierarchy_level"], inst.get("country"))
        by_level_country.setdefault(key, []).append(inst)

    # Find the ACWI benchmark for regime calculation
    acwi_id = None
    for inst in instruments_data:
        if inst["id"] == "ACWI":
            acwi_id = inst["id"]
            break

    # Calculate regime
    regime = "RISK_ON"
    if acwi_id and acwi_id in sample_data:
        acwi_df = sample_data[acwi_id].select(["date", "close"]).cast(
            {"close": pl.Float64}
        )
        regime = calculate_regime(acwi_df)
    logger.info("Global regime: %s", regime)

    # Compute RS scores for each instrument
    all_scores: list[dict] = []
    factory = get_session_factory()

    for inst in instruments_data:
        iid = inst["id"]
        if iid not in sample_data:
            continue

        asset_df = sample_data[iid]

        # Find benchmark
        bench_id = inst.get("benchmark_id")
        if not bench_id or bench_id not in sample_data:
            # Use self as benchmark (score will be 50)
            bench_id = iid
        bench_df = sample_data[bench_id]

        # Cast to Float64 for calculations
        asset_prices = asset_df.select(["date", "close"]).cast({"close": pl.Float64})
        bench_prices = bench_df.select(["date", "close"]).cast({"close": pl.Float64})

        # Build peer group (same hierarchy level + country)
        key = (inst["hierarchy_level"], inst.get("country"))
        peers = by_level_country.get(key, [inst])
        peer_data: dict[str, pl.DataFrame] = {}
        for peer in peers:
            pid = peer["id"]
            if pid in sample_data:
                peer_data[pid] = sample_data[pid].select(["date", "close"]).cast(
                    {"close": pl.Float64}
                )

        # Stage 1-5
        rs_result = calculator.compute_rs_scores(
            iid, asset_prices, bench_prices, peer_data
        )

        # Get latest RS trend data
        rs_trend_df = rs_result["rs_trend_df"]
        latest_rs_line = None
        latest_rs_ma = None
        latest_trend = None
        if rs_trend_df.height > 0:
            last_row = rs_trend_df.tail(1)
            latest_rs_line = last_row["rs_line"][0]
            latest_rs_ma = last_row["rs_ma_150"][0] if last_row["rs_ma_150"][0] is not None else None
            latest_trend = last_row["rs_trend"][0]

        # Percentile ranks
        pcts = rs_result["percentile_ranks"]
        pct_1m = pcts.get("1M", Decimal("50"))
        pct_3m = pcts.get("3M", Decimal("50"))
        pct_6m = pcts.get("6M", Decimal("50"))
        pct_12m = pcts.get("12M", Decimal("50"))

        composite = rs_result["rs_composite"]

        # Stage 6: Volume
        vol_df = asset_df.select(["date", "volume"]).cast({"volume": pl.Float64})
        volume_ratio = volume_analyzer.calculate_volume_ratio(vol_df)
        vol_multiplier = volume_analyzer.calculate_vol_multiplier(volume_ratio)

        # Liquidity tier
        liq_tier = inst.get("liquidity_tier", 2)
        if asset_df.height >= 20:
            # Calculate avg daily value
            recent_20 = asset_df.tail(20)
            close_vals = recent_20["close"].cast(pl.Float64)
            vol_vals = recent_20["volume"].cast(pl.Float64)
            avg_daily_val = (close_vals * vol_vals).mean()
            if avg_daily_val is not None:
                liq_tier = liquidity_scorer.calculate_liquidity_tier(
                    Decimal(str(avg_daily_val))
                )

        # Adjusted RS score
        adjusted_rs = volume_analyzer.calculate_adjusted_rs_score(
            composite, vol_multiplier, liq_tier
        )

        # Stage 5: Momentum (simple: difference from 20 days ago)
        # Since we only have the final composite, approximate momentum
        rs_momentum = Decimal("0")
        # Use excess return as proxy for momentum direction
        excess = rs_result["excess_returns"]
        if "1M" in excess:
            er_1m = excess["1M"]
            rs_momentum = (er_1m * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            rs_momentum = max(Decimal("-50"), min(Decimal("50"), rs_momentum))

        # Stage 7: Quadrant
        quadrant = classify_quadrant(adjusted_rs, rs_momentum)

        # Stage 10: Extension warning
        extension = liquidity_scorer.check_extension_warning(pct_3m, pct_6m, pct_12m)

        # Get trading dates from sample data
        dates = asset_df["date"].to_list()
        latest_date = dates[-1] if dates else date(2026, 3, 17)

        score_dict = {
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
            # extra fields for opportunity scanner
            "name": inst["name"],
            "country": inst.get("country"),
            "sector": inst.get("sector"),
            "hierarchy_level": inst["hierarchy_level"],
            "asset_type": inst.get("asset_type"),
        }
        all_scores.append(score_dict)

    # Insert RS scores into DB
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
                        rs_trend = EXCLUDED.rs_trend, rs_pct_1m = EXCLUDED.rs_pct_1m,
                        rs_pct_3m = EXCLUDED.rs_pct_3m, rs_pct_6m = EXCLUDED.rs_pct_6m,
                        rs_pct_12m = EXCLUDED.rs_pct_12m, rs_composite = EXCLUDED.rs_composite,
                        rs_momentum = EXCLUDED.rs_momentum, volume_ratio = EXCLUDED.volume_ratio,
                        vol_multiplier = EXCLUDED.vol_multiplier,
                        adjusted_rs_score = EXCLUDED.adjusted_rs_score,
                        quadrant = EXCLUDED.quadrant, liquidity_tier = EXCLUDED.liquidity_tier,
                        extension_warning = EXCLUDED.extension_warning, regime = EXCLUDED.regime
                """),
                {
                    "instrument_id": sc["instrument_id"],
                    "date": sc["date"],
                    "rs_line": sc["rs_line"],
                    "rs_ma_150": sc["rs_ma_150"],
                    "rs_trend": sc["rs_trend"],
                    "rs_pct_1m": sc["rs_pct_1m"],
                    "rs_pct_3m": sc["rs_pct_3m"],
                    "rs_pct_6m": sc["rs_pct_6m"],
                    "rs_pct_12m": sc["rs_pct_12m"],
                    "rs_composite": sc["rs_composite"],
                    "rs_momentum": sc["rs_momentum"],
                    "volume_ratio": sc["volume_ratio"],
                    "vol_multiplier": sc["vol_multiplier"],
                    "adjusted_rs_score": sc["adjusted_rs_score"],
                    "quadrant": sc["quadrant"],
                    "liquidity_tier": sc["liquidity_tier"],
                    "extension_warning": sc["extension_warning"],
                    "regime": sc["regime"],
                },
            )
        await session.commit()
        logger.info("Seeded %d RS score rows.", len(all_scores))

    return all_scores


async def seed_opportunities(all_scores: list[dict]) -> None:
    """Generate and insert opportunity signals."""
    scanner = OpportunityScanner()

    country_scores = [s for s in all_scores if s.get("hierarchy_level") == 1]
    sector_scores = [s for s in all_scores if s.get("hierarchy_level") == 2]
    stock_scores = [s for s in all_scores if s.get("hierarchy_level") == 3]

    # For quadrant entries, create mock "previous" scores with shifted quadrants
    previous_scores = []
    for s in all_scores:
        prev = dict(s)
        # Shift some quadrants to generate signals
        if prev["quadrant"] == "LEADING":
            prev["quadrant"] = "IMPROVING"
        elif prev["quadrant"] == "IMPROVING":
            prev["quadrant"] = "LAGGING"
        previous_scores.append(prev)

    signals = []
    signals.extend(scanner.scan_quadrant_entries(all_scores, previous_scores))
    signals.extend(scanner.scan_volume_breakouts(all_scores))
    signals.extend(
        scanner.scan_multi_level_alignments(country_scores, sector_scores, stock_scores)
    )
    signals.extend(scanner.scan_extension_alerts(all_scores))

    if not signals:
        logger.info("No opportunity signals generated.")
        return

    factory = get_session_factory()
    async with factory() as session:
        import uuid
        from datetime import datetime, timezone

        for sig in signals:
            sig_id = str(uuid.uuid4())
            sig_date = all_scores[0]["date"] if all_scores else date(2026, 3, 17)
            metadata_val = sig.get("metadata", {})
            # Convert Decimal values in metadata to strings
            clean_meta = {}
            for k, v in metadata_val.items():
                if isinstance(v, Decimal):
                    clean_meta[k] = str(v)
                else:
                    clean_meta[k] = v

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
                    "id": sig_id,
                    "instrument_id": sig["instrument_id"],
                    "date": sig_date,
                    "signal_type": sig["signal_type"],
                    "conviction_score": float(sig["conviction_score"]),
                    "description": sig["description"],
                    "metadata": json.dumps(clean_meta),
                    "created_at": datetime.now(tz=timezone.utc).isoformat(),
                },
            )
        await session.commit()
        logger.info("Seeded %d opportunity signals.", len(signals))


async def verify_data() -> None:
    """Print row counts to verify seeding."""
    engine = get_engine()
    async with engine.connect() as conn:
        for table in ["instruments", "prices", "rs_scores", "opportunities"]:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            logger.info("  %s: %d rows", table, count)


async def main() -> None:
    """Run the full seed pipeline."""
    logger.info("=== Starting database seed ===")

    # Load instrument map
    with open(INSTRUMENT_MAP_PATH, "r", encoding="utf-8") as f:
        instruments_data = json.load(f)
    logger.info("Loaded %d instruments from instrument_map.json", len(instruments_data))

    # Step 1: Create tables
    await create_tables()

    # Step 2: Seed instruments
    await seed_instruments(instruments_data)

    # Step 3: Generate sample data
    logger.info("Generating 180 days of sample OHLCV data...")
    sample_data = generate_sample_data(instruments_data, days=180, seed=42)
    logger.info("Generated data for %d instruments.", len(sample_data))

    # Step 4: Seed prices
    await seed_prices(instruments_data, sample_data)

    # Step 5: Compute and seed RS scores
    logger.info("Computing RS scores...")
    all_scores = await compute_and_seed_rs_scores(instruments_data, sample_data)

    # Step 6: Generate and seed opportunities
    logger.info("Generating opportunity signals...")
    await seed_opportunities(all_scores)

    # Verify
    logger.info("=== Verification ===")
    await verify_data()

    logger.info("=== Seed complete ===")


if __name__ == "__main__":
    asyncio.run(main())
