"""Recompute all RS scores using Engine v2 (3-indicator system).

Reads prices from SQLite, computes RS Line + Momentum + OBV for every
instrument, and writes results back to rs_scores table.

Usage:
    cd backend && python -m scripts.recompute_rs_v2
"""

import json
import logging
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

import polars as pl

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.rs_engine_v2 import (
    compute_instrument_scores,
    calculate_regime,
    TIMEFRAME_MAP,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "momentum_compass.db"
INSTRUMENT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "instrument_map.json"


def load_instruments() -> list[dict]:
    """Load instrument map from JSON."""
    with open(INSTRUMENT_MAP_PATH, "r") as f:
        return json.load(f)


def load_prices(conn: sqlite3.Connection, instrument_id: str) -> pl.DataFrame:
    """Load OHLCV prices for an instrument from SQLite."""
    query = """
        SELECT date, open, high, low, close, volume
        FROM prices
        WHERE instrument_id = ?
        ORDER BY date ASC
    """
    rows = conn.execute(query, (instrument_id,)).fetchall()
    if not rows:
        return pl.DataFrame(schema={
            "date": pl.Date,
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Float64,
        })

    df = pl.DataFrame(
        {
            "date": [r[0] for r in rows],
            "open": [float(r[1]) if r[1] is not None else None for r in rows],
            "high": [float(r[2]) if r[2] is not None else None for r in rows],
            "low": [float(r[3]) if r[3] is not None else None for r in rows],
            "close": [float(r[4]) if r[4] is not None else None for r in rows],
            "volume": [float(r[5]) if r[5] is not None else 0.0 for r in rows],
        }
    )

    # Parse date strings
    df = df.with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    # Remove rows with null close
    df = df.filter(pl.col("close").is_not_null())

    return df


def get_benchmark_id(instrument: dict) -> str | None:
    """Determine benchmark ID for an instrument."""
    return instrument.get("benchmark_id")


def main() -> None:
    """Recompute all RS scores using v2 engine."""
    logger.info("Starting RS v2 recomputation...")

    conn = sqlite3.connect(str(DB_PATH))

    # Load instrument map
    instruments = load_instruments()
    logger.info("Loaded %d instruments from map", len(instruments))

    # Build instrument lookup
    inst_map = {i["id"]: i for i in instruments}

    # Load ACWI for regime
    acwi_prices = load_prices(conn, "ACWI")
    regime = "RISK_ON"
    if acwi_prices.height >= 200:
        regime = calculate_regime(acwi_prices)
    logger.info("Global regime: %s", regime)

    # Preload all price data into memory for speed
    logger.info("Preloading price data...")
    all_prices: dict[str, pl.DataFrame] = {}

    cursor = conn.execute("SELECT DISTINCT instrument_id FROM prices")
    priced_ids = [row[0] for row in cursor.fetchall()]

    for iid in priced_ids:
        all_prices[iid] = load_prices(conn, iid)

    logger.info("Loaded prices for %d instruments", len(all_prices))

    # Clear existing rs_scores
    conn.execute("DELETE FROM rs_scores")
    conn.commit()
    logger.info("Cleared existing rs_scores table")

    # Compute scores for each instrument using medium timeframe
    computed = 0
    skipped = 0
    errors = 0
    today = date.today()

    for instrument in instruments:
        iid = instrument["id"]

        if iid not in all_prices:
            skipped += 1
            continue

        asset_prices = all_prices[iid]
        if asset_prices.height < 20:
            skipped += 1
            continue

        # Get benchmark prices
        benchmark_id = get_benchmark_id(instrument)
        if benchmark_id and benchmark_id in all_prices:
            benchmark_prices = all_prices[benchmark_id]
        elif "ACWI" in all_prices:
            benchmark_prices = all_prices["ACWI"]
        else:
            skipped += 1
            continue

        if benchmark_prices.height < 20:
            skipped += 1
            continue

        try:
            # Compute for all 3 timeframes, store medium as primary
            scores = compute_instrument_scores(
                iid, asset_prices, benchmark_prices, timeframe="medium"
            )

            if scores is None:
                skipped += 1
                continue

            # Also compute short and long for the dropdown
            scores_short = compute_instrument_scores(
                iid, asset_prices, benchmark_prices, timeframe="short"
            )
            scores_long = compute_instrument_scores(
                iid, asset_prices, benchmark_prices, timeframe="long"
            )

            # Get the latest date from prices
            latest_date = str(asset_prices["date"].max())

            # Insert into rs_scores table
            conn.execute(
                """
                INSERT OR REPLACE INTO rs_scores (
                    instrument_id, date,
                    rs_line, rs_ma_150, rs_trend,
                    rs_pct_1m, rs_pct_3m, rs_pct_6m, rs_pct_12m,
                    rs_composite, rs_momentum,
                    volume_ratio, vol_multiplier,
                    adjusted_rs_score, quadrant,
                    liquidity_tier, extension_warning, regime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    iid,
                    latest_date,
                    # RS Line data
                    scores["rs_line"],
                    scores["rs_ma"],
                    scores["price_trend"],
                    # Timeframe percentiles → now store action + indicators
                    # Reuse fields: pct_1m=short_score, pct_3m=short_action
                    scores_short["rs_score"] if scores_short else scores["rs_score"],
                    scores_long["rs_score"] if scores_long else scores["rs_score"],
                    # Store OBV and momentum in pct_6m and pct_12m
                    scores["obv"],
                    scores["obv_ma"],
                    # Composite = medium score
                    scores["rs_score"],
                    # Momentum
                    scores["rs_momentum_pct"],
                    # Volume character (reuse volume_ratio field as 1.0 for accum, 0.0 for dist)
                    1.0 if scores["volume_character"] == "ACCUMULATION" else 0.0,
                    # vol_multiplier: not used, store 1.0
                    1.0,
                    # Adjusted score = medium score
                    scores["rs_score"],
                    # Quadrant → now Action
                    scores["action"],
                    # Liquidity tier
                    instrument.get("liquidity_tier", 2),
                    # Extension warning: not used in v2
                    False,
                    # Regime
                    regime,
                ),
            )
            computed += 1

            if computed % 500 == 0:
                conn.commit()
                logger.info("Computed %d instruments...", computed)

        except Exception as exc:
            errors += 1
            if errors <= 10:
                logger.error("Error computing %s: %s", iid, exc)

    conn.commit()
    conn.close()

    logger.info(
        "Done. Computed=%d, Skipped=%d, Errors=%d",
        computed, skipped, errors,
    )

    # Verify key results
    verify_conn = sqlite3.connect(str(DB_PATH))
    logger.info("\n=== VERIFICATION ===")

    # Country indices
    logger.info("Country Index Scores (medium timeframe):")
    cursor = verify_conn.execute("""
        SELECT r.instrument_id, i.name, i.country,
               r.adjusted_rs_score, r.quadrant, r.rs_momentum, r.date
        FROM rs_scores r
        JOIN instruments i ON r.instrument_id = i.id
        WHERE i.asset_type = 'country_index'
        AND r.instrument_id IN ('SPX','NDQ','FTM','DAX','CAC','NKX','HSI','CSI300','KS11','NSEI','TWII','AXJO','BVSP','GSPTSE')
        ORDER BY r.adjusted_rs_score DESC
    """)
    for row in cursor.fetchall():
        logger.info(
            "  %s (%s) %s: Score=%.2f Action=%s Mom=%.2f Date=%s",
            row[0], row[1], row[2], row[3], row[4], row[5], row[6]
        )

    verify_conn.close()


if __name__ == "__main__":
    main()
