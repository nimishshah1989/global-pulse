"""Bulk ingest Stooq ZIP data — discovers instruments + loads ALL price data.

Single-command pipeline for processing a Stooq bulk download ZIP:
1. Reads the ZIP file (no network needed)
2. Discovers all instruments (stocks, ETFs, indices)
3. Registers instruments in the database
4. Loads ALL OHLCV price data from every CSV in the ZIP

Usage:
    cd backend
    python -m scripts.bulk_ingest_zip --zip ../data/stooq_bulk/d_us_txt.zip --region us

    # Skip stocks, only ETFs + indices:
    python -m scripts.bulk_ingest_zip --zip ../data/stooq_bulk/d_us_txt.zip --region us --no-stocks

    # Multiple ZIPs:
    python -m scripts.bulk_ingest_zip --bulk-dir ../data/stooq_bulk
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import logging
import sys
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Ensure backend/ is on sys.path
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import get_settings
from db.models import Base, Instrument, Price

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Region config (matches stooq_bulk_processor.py) ────────────────────

STOOQ_REGIONS: dict[str, dict] = {
    "us": {
        "paths": {
            "stock": [
                "data/daily/us/nasdaq stocks/",
                "data/daily/us/nyse stocks/",
                "data/daily/us/nysemkt stocks/",
            ],
            "etf": [
                "data/daily/us/nasdaq etfs/",
                "data/daily/us/nyse etfs/",
                "data/daily/us/nysemkt etfs/",
            ],
            "index": [
                "data/daily/us/nyse indices/",
                "data/daily/us/nasdaq indices/",
            ],
        },
        "suffix": "US",
        "country": "US",
        "currency": "USD",
    },
    "uk": {
        "paths": {
            "stock": [
                "data/daily/uk/lse stocks/",
                "data/daily/uk/lse intl stocks/",
            ],
            "etf": [
                "data/daily/uk/lse etfs/",
                "data/daily/uk/lse intl etfs/",
            ],
            "index": [
                "data/daily/uk/lse indices/",
            ],
        },
        "suffix": "UK",
        "country": "UK",
        "currency": "GBP",
    },
    "jp": {
        "paths": {
            "stock": ["data/daily/jp/tse stocks/"],
            "etf": ["data/daily/jp/tse etfs/"],
            "index": ["data/daily/jp/tse indices/"],
        },
        "suffix": "JP",
        "country": "JP",
        "currency": "JPY",
    },
    "hk": {
        "paths": {
            "stock": ["data/daily/hk/hkex stocks/"],
            "etf": ["data/daily/hk/hkex etfs/"],
            "index": ["data/daily/hk/hkex indices/"],
        },
        "suffix": "HK",
        "country": "HK",
        "currency": "HKD",
    },
    "de": {
        "paths": {
            "stock": [
                "data/daily/de/xetra stocks/",
                "data/daily/de/frankfurt stocks/",
            ],
            "etf": [
                "data/daily/de/xetra etfs/",
                "data/daily/de/frankfurt etfs/",
            ],
            "index": ["data/daily/de/xetra indices/"],
        },
        "suffix": "DE",
        "country": "DE",
        "currency": "EUR",
    },
}

PRICE_BATCH_SIZE = 1000


# ── Helpers ────────────────────────────────────────────────────────────

def _to_decimal(value: str) -> Decimal | None:
    """Convert string to Decimal, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return None


def _to_volume(value: str) -> int | None:
    """Convert string to integer volume."""
    if not value or value.strip() == "":
        return None
    try:
        return int(Decimal(value.strip()))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: str) -> date | None:
    """Parse date in YYYYMMDD or YYYY-MM-DD format."""
    value = value.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _classify_folder_type(csv_path: str, region_config: dict) -> str | None:
    """Determine the folder type (stock/etf/index) from the CSV path."""
    path_lower = csv_path.lower()
    for folder_type, prefixes in region_config["paths"].items():
        for prefix in prefixes:
            if path_lower.startswith(prefix.lower()):
                return folder_type
    return None


def _build_instrument_id(ticker_base: str, suffix: str) -> str:
    """Build canonical instrument ID from ticker base and suffix."""
    if suffix:
        return f"{ticker_base}_{suffix}"
    return ticker_base


def _build_stooq_ticker(
    ticker_base: str, suffix: str, folder_type: str
) -> str:
    """Build Stooq ticker string."""
    if folder_type == "index":
        return f"^{ticker_base}"
    if suffix:
        return f"{ticker_base}.{suffix}"
    return ticker_base


def _determine_asset_type(folder_type: str) -> tuple[str, int]:
    """Return (asset_type, hierarchy_level) based on folder type."""
    mapping = {
        "stock": ("stock", 3),
        "etf": ("etf", 2),
        "index": ("country_index", 1),
    }
    return mapping.get(folder_type, ("unknown", 2))


def _parse_csv_bytes(csv_bytes: bytes, instrument_id: str) -> list[dict]:
    """Parse a Stooq CSV/TXT file into price row dicts.

    Stooq bulk files use headers like:
        <TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>
    or standard:
        Date,Open,High,Low,Close,Volume
    """
    rows: list[dict] = []
    try:
        text = csv_bytes.decode("utf-8", errors="replace")
    except Exception:
        return rows

    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return rows

    # Normalize headers: strip whitespace, angle brackets, lowercase
    normalized = [col.strip().strip("<>").lower() for col in header]
    col_map: dict[str, int] = {}

    # Map Stooq bracket-style AND standard headers
    aliases = {
        "date": ("date",),
        "open": ("open",),
        "high": ("high",),
        "low": ("low",),
        "close": ("close",),
        "volume": ("volume", "vol"),
    }

    for target, names in aliases.items():
        for idx, col in enumerate(normalized):
            if col in names:
                col_map[target] = idx
                break

    if "date" not in col_map or "close" not in col_map:
        return rows

    for row in reader:
        if len(row) < 2:
            continue
        try:
            parsed_date = _parse_date(row[col_map["date"]])
            if parsed_date is None:
                continue
            close_val = _to_decimal(row[col_map["close"]])
            if close_val is None:
                continue
            rows.append({
                "instrument_id": instrument_id,
                "date": parsed_date,
                "open": _to_decimal(row[col_map["open"]]) if "open" in col_map else None,
                "high": _to_decimal(row[col_map["high"]]) if "high" in col_map else None,
                "low": _to_decimal(row[col_map["low"]]) if "low" in col_map else None,
                "close": close_val,
                "volume": _to_volume(row[col_map["volume"]]) if "volume" in col_map else None,
            })
        except (IndexError, KeyError):
            continue

    return rows


# ── Main pipeline ──────────────────────────────────────────────────────

async def bulk_ingest_zip(
    zip_path: Path,
    region: str,
    include_stocks: bool = True,
) -> dict:
    """Process a single Stooq bulk ZIP: discover instruments + load prices.

    Args:
        zip_path: Path to the Stooq ZIP file (e.g. d_us_txt.zip).
        region: Region key (us, uk, jp, hk, de).
        include_stocks: If False, skip individual stocks (ETFs + indices only).

    Returns:
        Stats dict with counts.
    """
    if region not in STOOQ_REGIONS:
        logger.error("Unknown region: %s. Available: %s",
                      region, list(STOOQ_REGIONS.keys()))
        return {"error": f"Unknown region: {region}"}

    config = STOOQ_REGIONS[region]
    suffix = config["suffix"]
    country = config["country"]
    currency = config["currency"]

    stats = {
        "instruments_discovered": 0,
        "instruments_loaded": 0,
        "instruments_skipped": 0,
        "prices_loaded": 0,
        "prices_skipped": 0,
        "csv_files_total": 0,
        "csv_files_processed": 0,
        "csv_files_failed": 0,
    }

    # Set up database
    settings = get_settings()
    url = settings.effective_database_url
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    engine = create_async_engine(url, echo=False, connect_args=connect_args)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Open ZIP
    logger.info("Opening ZIP: %s", zip_path)
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        logger.error("Invalid ZIP file: %s", zip_path)
        return {"error": "Invalid ZIP file"}

    all_csv_files = [f for f in zf.namelist()
                     if f.lower().endswith(".csv") or f.lower().endswith(".txt")]
    stats["csv_files_total"] = len(all_csv_files)
    logger.info("Found %d data files in ZIP", len(all_csv_files))

    # Show sample paths for debugging folder structure
    if all_csv_files:
        sample = all_csv_files[:10]
        logger.info("Sample file paths in ZIP:")
        for p in sample:
            logger.info("  %s", p)

        # Show unique top-level directories
        dirs = set()
        for f in all_csv_files:
            parts = f.lower().split("/")
            if len(parts) >= 4:
                dirs.add("/".join(parts[:4]) + "/")
        logger.info("Detected directories:")
        for d in sorted(dirs):
            logger.info("  %s", d)

    # Phase 1: Discover instruments from folder structure
    instruments: list[dict] = []
    csv_to_instrument: dict[str, str] = {}  # csv_path -> instrument_id

    for csv_path in all_csv_files:
        folder_type = _classify_folder_type(csv_path, config)
        if folder_type is None:
            continue
        if folder_type == "stock" and not include_stocks:
            continue

        # Strip .txt or .csv extension to get ticker
        ticker_base = Path(csv_path).stem.upper()
        instrument_id = _build_instrument_id(ticker_base, suffix)
        stooq_ticker = _build_stooq_ticker(ticker_base, suffix, folder_type)
        asset_type, hierarchy_level = _determine_asset_type(folder_type)

        instruments.append({
            "id": instrument_id,
            "name": ticker_base,
            "ticker_stooq": stooq_ticker,
            "ticker_yfinance": None,
            "source": "stooq",
            "asset_type": asset_type,
            "country": country,
            "sector": None,
            "hierarchy_level": hierarchy_level,
            "benchmark_id": None,  # set later
            "currency": currency,
            "liquidity_tier": 2,
        })
        csv_to_instrument[csv_path] = instrument_id

    # Deduplicate by ID
    seen: dict[str, dict] = {}
    for inst in instruments:
        if inst["id"] not in seen:
            seen[inst["id"]] = inst
    instruments = list(seen.values())
    stats["instruments_discovered"] = len(instruments)

    logger.info("Discovered %d unique instruments", len(instruments))

    # Phase 2: Register instruments in DB
    async with factory() as session:
        existing_result = await session.execute(select(Instrument.id))
        existing_ids = {row[0] for row in existing_result.fetchall()}

        new_instruments = [i for i in instruments if i["id"] not in existing_ids]
        for inst in new_instruments:
            session.add(Instrument(
                id=inst["id"],
                name=inst["name"],
                ticker_stooq=inst.get("ticker_stooq"),
                ticker_yfinance=inst.get("ticker_yfinance"),
                source=inst["source"],
                asset_type=inst["asset_type"],
                country=inst.get("country"),
                sector=inst.get("sector"),
                hierarchy_level=inst["hierarchy_level"],
                benchmark_id=None,
                currency=inst.get("currency", "USD"),
                liquidity_tier=inst.get("liquidity_tier", 2),
                is_active=True,
            ))
        await session.commit()
        stats["instruments_loaded"] = len(new_instruments)
        stats["instruments_skipped"] = len(instruments) - len(new_instruments)
        all_valid_ids = existing_ids | {i["id"] for i in new_instruments}

    logger.info(
        "Instruments: %d new, %d existing",
        stats["instruments_loaded"],
        stats["instruments_skipped"],
    )

    # Phase 3: Load ALL price data from CSV files
    logger.info("Starting price data ingestion...")

    async with factory() as session:
        processed = 0
        for csv_path, instrument_id in csv_to_instrument.items():
            if instrument_id not in all_valid_ids:
                continue

            try:
                csv_bytes = zf.read(csv_path)
                price_rows = _parse_csv_bytes(csv_bytes, instrument_id)

                if not price_rows:
                    continue

                # Batch insert using raw SQL for speed
                for i in range(0, len(price_rows), PRICE_BATCH_SIZE):
                    batch = price_rows[i:i + PRICE_BATCH_SIZE]
                    for row in batch:
                        session.add(Price(
                            instrument_id=row["instrument_id"],
                            date=row["date"],
                            open=float(row["open"]) if row["open"] is not None else None,
                            high=float(row["high"]) if row["high"] is not None else None,
                            low=float(row["low"]) if row["low"] is not None else None,
                            close=float(row["close"]),
                            volume=row["volume"],
                        ))
                    await session.flush()

                stats["prices_loaded"] += len(price_rows)
                stats["csv_files_processed"] += 1
                processed += 1

                # Commit every 200 instruments for memory management
                if processed % 200 == 0:
                    await session.commit()
                    logger.info(
                        "Progress: %d/%d instruments processed, %d price rows loaded",
                        processed,
                        len(csv_to_instrument),
                        stats["prices_loaded"],
                    )

            except Exception as exc:
                stats["csv_files_failed"] += 1
                if stats["csv_files_failed"] <= 10:
                    logger.warning("Failed %s: %s", csv_path, exc)

        await session.commit()

    zf.close()
    await engine.dispose()

    # Summary
    logger.info("=" * 60)
    logger.info("BULK INGEST COMPLETE — Region: %s", region.upper())
    logger.info("  Instruments: %d discovered, %d new, %d existing",
                stats["instruments_discovered"],
                stats["instruments_loaded"],
                stats["instruments_skipped"])
    logger.info("  CSV files:   %d total, %d processed, %d failed",
                stats["csv_files_total"],
                stats["csv_files_processed"],
                stats["csv_files_failed"])
    logger.info("  Price rows:  %d loaded", stats["prices_loaded"])
    logger.info("=" * 60)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk ingest Stooq ZIP data into database",
    )
    parser.add_argument(
        "--zip", type=Path, required=True,
        help="Path to Stooq ZIP file (e.g. ../data/stooq_bulk/d_us_txt.zip)",
    )
    parser.add_argument(
        "--region", type=str, required=True,
        choices=list(STOOQ_REGIONS.keys()),
        help="Region key matching the ZIP file",
    )
    parser.add_argument(
        "--no-stocks", action="store_true",
        help="Skip individual stocks (only ETFs + indices)",
    )

    args = parser.parse_args()

    if not args.zip.exists():
        logger.error("ZIP file not found: %s", args.zip)
        sys.exit(1)

    asyncio.run(bulk_ingest_zip(
        zip_path=args.zip,
        region=args.region,
        include_stocks=not args.no_stocks,
    ))


if __name__ == "__main__":
    main()
