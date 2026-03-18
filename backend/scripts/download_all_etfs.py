"""Download all ETF + index OHLCV data from Stooq and store in SQLite.

Downloads historical data for all instruments in the instrument_map.json that
have a ticker_stooq value. Uses the direct CSV endpoint with rate limiting.

Usage:
    cd backend
    python scripts/download_all_etfs.py [--missing-only] [--update-only] [--days N]

Modes:
    (default)      Download missing instruments + update all with latest data
    --missing-only Only download instruments that have zero price records
    --update-only  Only update existing instruments with latest data
    --days N       For updates, fetch last N days (default: 30)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend dir to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rate limiting — conservative to avoid blocks
REQUEST_DELAY = 1.5  # seconds between requests
MAX_RETRIES = 3
BACKOFF_BASE = 3.0
BATCH_PAUSE = 30  # pause every N requests
BATCH_SIZE = 50

DB_PATH = backend_dir / "momentum_compass.db"
MAP_PATH = backend_dir / "data" / "instrument_map.json"
STOOQ_BASE = "https://stooq.com/q/d/l/"
HISTORY_START = "20230101"  # 3+ years of history


def load_instrument_map() -> list[dict]:
    """Load the instrument map JSON."""
    with open(MAP_PATH) as f:
        return json.load(f)


def get_etf_and_index_instruments(instruments: list[dict]) -> list[dict]:
    """Filter to ETF-like and index instruments with Stooq tickers."""
    target_types = {
        "etf", "sector_etf", "country_etf", "global_sector_etf",
        "regional_etf", "bond_etf", "commodity_etf",
        "country_index", "sector_index", "benchmark",
    }
    return [
        i for i in instruments
        if i["asset_type"] in target_types and i.get("ticker_stooq")
    ]


def get_db_connection() -> sqlite3.Connection:
    """Get a SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def get_instruments_with_prices(conn: sqlite3.Connection) -> set[str]:
    """Get set of instrument IDs that already have price data."""
    cur = conn.execute("SELECT DISTINCT instrument_id FROM prices")
    return {row[0] for row in cur.fetchall()}


def get_latest_date_per_instrument(conn: sqlite3.Connection) -> dict[str, str]:
    """Get the latest price date for each instrument."""
    cur = conn.execute(
        "SELECT instrument_id, MAX(date) FROM prices GROUP BY instrument_id"
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def ensure_instrument_exists(conn: sqlite3.Connection, inst: dict) -> None:
    """Insert instrument into DB if it doesn't exist."""
    conn.execute(
        """INSERT OR IGNORE INTO instruments
           (id, name, ticker_stooq, ticker_yfinance, source, asset_type,
            country, sector, hierarchy_level, benchmark_id, currency,
            liquidity_tier, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            inst["id"],
            inst.get("name", inst["id"]),
            inst.get("ticker_stooq"),
            inst.get("ticker_yfinance"),
            inst.get("source", "stooq"),
            inst["asset_type"],
            inst.get("country"),
            inst.get("sector"),
            inst.get("hierarchy_level", 2),
            inst.get("benchmark_id"),
            inst.get("currency", "USD"),
            inst.get("liquidity_tier", 2),
            True,
        ),
    )


def insert_prices(
    conn: sqlite3.Connection, instrument_id: str, rows: list[tuple]
) -> int:
    """Insert price rows, skipping duplicates. Returns count inserted."""
    if not rows:
        return 0
    conn.executemany(
        """INSERT OR IGNORE INTO prices
           (instrument_id, date, open, high, low, close, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(instrument_id, *row) for row in rows],
    )
    return len(rows)


def parse_csv(text: str) -> list[tuple]:
    """Parse Stooq CSV text into list of (date, open, high, low, close, volume) tuples."""
    text = text.strip()
    if not text or "No data" in text or len(text) < 20:
        return []

    rows = []
    lines = text.split("\n")
    if len(lines) < 2:
        return []

    # Skip header
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            dt = parts[0].strip()
            open_ = float(parts[1]) if parts[1].strip() else None
            high = float(parts[2]) if parts[2].strip() else None
            low = float(parts[3]) if parts[3].strip() else None
            close = float(parts[4]) if parts[4].strip() else 0.0
            volume = int(float(parts[5])) if len(parts) > 5 and parts[5].strip() else None
            if close > 0:
                rows.append((dt, open_, high, low, close, volume))
        except (ValueError, IndexError):
            continue

    return rows


async def download_ticker(
    client: httpx.AsyncClient,
    ticker: str,
    start_date: str,
    end_date: str,
) -> str | None:
    """Download CSV data for a single ticker. Returns CSV text or None."""
    url = f"{STOOQ_BASE}?s={ticker.lower()}&d1={start_date}&d2={end_date}&i=d"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(url)

            if resp.status_code == 404:
                logger.warning("  %s: 404 not found", ticker)
                return None

            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                logger.warning("  %s: rate limited, waiting %.0fs (attempt %d)", ticker, wait, attempt)
                await asyncio.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.text

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE ** attempt)
                continue
            logger.error("  %s: HTTP error %s", ticker, e)
            return None

        except httpx.RequestError as e:
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                logger.warning("  %s: request error, retry in %.0fs: %s", ticker, wait, e)
                await asyncio.sleep(wait)
                continue
            logger.error("  %s: failed after %d retries: %s", ticker, MAX_RETRIES, e)
            return None

    return None


async def run_downloads(
    targets: list[dict],
    start_dates: dict[str, str],
    end_date: str,
) -> None:
    """Download price data for all target instruments."""
    conn = get_db_connection()
    total = len(targets)
    success = 0
    failed = 0
    skipped = 0
    total_rows = 0

    logger.info("Starting download of %d instruments", total)
    logger.info("End date: %s", end_date)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        follow_redirects=True,
    ) as client:
        for i, inst in enumerate(targets, 1):
            ticker = inst["ticker_stooq"]
            inst_id = inst["id"]
            start = start_dates.get(inst_id, HISTORY_START)

            # Progress
            pct = (i / total) * 100
            logger.info(
                "[%d/%d %.0f%%] %s (%s) from %s",
                i, total, pct, inst_id, ticker, start,
            )

            # Ensure instrument exists in DB
            ensure_instrument_exists(conn, inst)

            # Download
            csv_text = await download_ticker(client, ticker, start, end_date)

            if csv_text is None:
                failed += 1
                conn.commit()
                await asyncio.sleep(REQUEST_DELAY)
                continue

            # Parse and insert
            rows = parse_csv(csv_text)
            if not rows:
                skipped += 1
                logger.info("  %s: no data rows", ticker)
                conn.commit()
                await asyncio.sleep(REQUEST_DELAY)
                continue

            count = insert_prices(conn, inst_id, rows)
            total_rows += count
            success += 1
            logger.info("  %s: %d rows (new: %d)", ticker, len(rows), count)

            # Commit every 10 instruments
            if i % 10 == 0:
                conn.commit()

            # Rate limiting
            await asyncio.sleep(REQUEST_DELAY)

            # Batch pause to avoid detection
            if i % BATCH_SIZE == 0 and i < total:
                conn.commit()
                logger.info(
                    "--- Batch pause (%d/%d done, %d success, %d failed) ---",
                    i, total, success, failed,
                )
                await asyncio.sleep(BATCH_PAUSE)

    conn.commit()
    conn.close()

    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("  Total: %d | Success: %d | Failed: %d | Skipped: %d", total, success, failed, skipped)
    logger.info("  Total rows inserted: %d", total_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ETF/index data from Stooq")
    parser.add_argument("--missing-only", action="store_true", help="Only download instruments with no price data")
    parser.add_argument("--update-only", action="store_true", help="Only update existing instruments with latest data")
    parser.add_argument("--days", type=int, default=30, help="For updates, fetch last N days (default: 30)")
    parser.add_argument("--type", type=str, default=None, help="Filter by asset_type (e.g. 'sector_etf')")
    args = parser.parse_args()

    end_date = date.today().strftime("%Y%m%d")

    # Load instruments
    all_instruments = load_instrument_map()
    targets = get_etf_and_index_instruments(all_instruments)
    logger.info("Found %d ETF/index instruments with Stooq tickers", len(targets))

    # Filter by type if specified
    if args.type:
        targets = [t for t in targets if t["asset_type"] == args.type]
        logger.info("Filtered to %d instruments of type '%s'", len(targets), args.type)

    # Get existing data state
    conn = get_db_connection()
    has_prices = get_instruments_with_prices(conn)
    latest_dates = get_latest_date_per_instrument(conn)
    conn.close()

    # Determine start dates and filter targets
    start_dates: dict[str, str] = {}

    if args.missing_only:
        targets = [t for t in targets if t["id"] not in has_prices]
        logger.info("Missing-only mode: %d instruments need data", len(targets))
        # Full history for missing
        for t in targets:
            start_dates[t["id"]] = HISTORY_START

    elif args.update_only:
        targets = [t for t in targets if t["id"] in has_prices]
        logger.info("Update-only mode: %d instruments to update", len(targets))
        # Start from last known date
        for t in targets:
            last = latest_dates.get(t["id"])
            if last:
                # Start from 5 days before last known date (overlap for safety)
                last_dt = date.fromisoformat(last) - timedelta(days=5)
                start_dates[t["id"]] = last_dt.strftime("%Y%m%d")
            else:
                start_dates[t["id"]] = HISTORY_START

    else:
        # Default: missing get full history, existing get update
        for t in targets:
            if t["id"] not in has_prices:
                start_dates[t["id"]] = HISTORY_START
            else:
                last = latest_dates.get(t["id"])
                if last:
                    last_dt = date.fromisoformat(last) - timedelta(days=5)
                    start_dates[t["id"]] = last_dt.strftime("%Y%m%d")
                else:
                    start_dates[t["id"]] = HISTORY_START

        missing_count = sum(1 for t in targets if t["id"] not in has_prices)
        update_count = len(targets) - missing_count
        logger.info(
            "Default mode: %d missing + %d to update = %d total",
            missing_count, update_count, len(targets),
        )

    if not targets:
        logger.info("Nothing to download!")
        return

    # Sort: missing instruments first, then alphabetical
    targets.sort(key=lambda t: (t["id"] in has_prices, t["id"]))

    # Estimate time
    est_minutes = (len(targets) * REQUEST_DELAY + (len(targets) // BATCH_SIZE) * BATCH_PAUSE) / 60
    logger.info("Estimated time: %.0f minutes", est_minutes)

    asyncio.run(run_downloads(targets, start_dates, end_date))


if __name__ == "__main__":
    main()
