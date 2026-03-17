"""Load instrument map and CSV price data into the database.

Reads instruments from instrument_map.json, creates DB records, then loads
OHLCV data from CSV files in data/fetched/ into the prices table.

Usage: cd backend && python -m scripts.load_data_to_db
"""

import asyncio
import csv
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend/ is on sys.path for config import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings
from db.models import Base, Instrument, Price

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INSTRUMENT_MAP_PATH = DATA_DIR / "instrument_map.json"
FETCHED_DIR = DATA_DIR / "fetched"
PRICE_BATCH_SIZE = 500

# CSV columns we care about (case-insensitive matching)
OHLCV_COLUMNS = {"date", "open", "high", "low", "close", "volume"}


def _to_decimal(value: str) -> Decimal | None:
    """Convert a string to Decimal, returning None for empty/invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return None


def _to_volume(value: str) -> int | None:
    """Convert a string to integer volume, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return int(Decimal(value.strip()))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: str) -> date | None:
    """Parse a date string in YYYY-MM-DD format."""
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _load_instrument_map() -> list[dict]:
    """Load and return the instrument map JSON."""
    import json

    with open(INSTRUMENT_MAP_PATH, "r") as f:
        return json.load(f)


def _detect_columns(header: list[str]) -> dict[str, int] | None:
    """Map normalized column names to their indices. Returns None if invalid."""
    normalized = [col.strip().lower().replace(" ", "_") for col in header]
    col_map: dict[str, int] = {}
    for target in OHLCV_COLUMNS:
        for idx, col in enumerate(normalized):
            if col == target or (target == "close" and col == "adj_close"):
                col_map[target] = idx
                break
    if "date" not in col_map or "close" not in col_map:
        return None
    return col_map


def _read_csv_prices(csv_path: Path, instrument_id: str) -> list[dict]:
    """Read a CSV file and return a list of price row dicts."""
    rows: list[dict] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)
        if first_row is None:
            return rows

        # Detect if first row is a header
        col_map = _detect_columns(first_row)
        if col_map is None:
            # First row might be data, not header — assume standard order
            col_map = {"date": 0, "open": 1, "high": 2, "low": 3, "close": 4}
            if len(first_row) > 5:
                col_map["volume"] = 5
            # Process first_row as data
            row_data = _parse_row(first_row, col_map, instrument_id)
            if row_data:
                rows.append(row_data)

        for row in reader:
            if len(row) < 2:
                continue
            row_data = _parse_row(row, col_map, instrument_id)
            if row_data:
                rows.append(row_data)
    return rows


def _parse_row(
    row: list[str], col_map: dict[str, int], instrument_id: str
) -> dict | None:
    """Parse a single CSV row into a price dict."""
    try:
        parsed_date = _parse_date(row[col_map["date"]])
        if parsed_date is None:
            return None
        close_val = _to_decimal(row[col_map["close"]])
        if close_val is None:
            return None
        return {
            "instrument_id": instrument_id,
            "date": parsed_date,
            "open": _to_decimal(row[col_map["open"]]) if "open" in col_map else None,
            "high": _to_decimal(row[col_map["high"]]) if "high" in col_map else None,
            "low": _to_decimal(row[col_map["low"]]) if "low" in col_map else None,
            "close": close_val,
            "volume": _to_volume(row[col_map["volume"]])
            if "volume" in col_map
            else None,
        }
    except (IndexError, KeyError):
        return None


async def _load_instruments(
    session: AsyncSession, instruments: list[dict]
) -> tuple[int, int]:
    """Insert instruments into DB, skipping duplicates. Returns (loaded, skipped)."""
    existing = set()
    result = await session.execute(select(Instrument.id))
    for row in result.scalars():
        existing.add(row)

    loaded = 0
    skipped = 0
    for inst in instruments:
        if inst["id"] in existing:
            skipped += 1
            continue
        db_inst = Instrument(
            id=inst["id"],
            name=inst["name"],
            ticker_stooq=inst.get("ticker_stooq"),
            ticker_yfinance=inst.get("ticker_yfinance"),
            source=inst["source"],
            asset_type=inst["asset_type"],
            country=inst.get("country"),
            sector=inst.get("sector"),
            hierarchy_level=inst["hierarchy_level"],
            benchmark_id=inst.get("benchmark_id"),
            currency=inst.get("currency", "USD"),
            liquidity_tier=inst.get("liquidity_tier", 2),
            is_active=True,
        )
        session.add(db_inst)
        loaded += 1
    await session.commit()
    return loaded, skipped


async def _load_prices(
    session: AsyncSession, instrument_id: str, price_rows: list[dict]
) -> tuple[int, int]:
    """Batch-insert price rows, skipping duplicates. Returns (loaded, skipped)."""
    if not price_rows:
        return 0, 0

    # Get existing dates for this instrument
    result = await session.execute(
        select(Price.date).where(Price.instrument_id == instrument_id)
    )
    existing_dates = {row[0] for row in result.fetchall()}

    new_rows = [r for r in price_rows if r["date"] not in existing_dates]
    skipped = len(price_rows) - len(new_rows)

    for i in range(0, len(new_rows), PRICE_BATCH_SIZE):
        batch = new_rows[i : i + PRICE_BATCH_SIZE]
        session.add_all([Price(**row) for row in batch])
        await session.flush()
    await session.commit()
    return len(new_rows), skipped


async def main() -> None:
    """Main entry point: create tables, load instruments, load prices."""
    settings = get_settings()
    url = settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_async_engine(url, echo=False, connect_args=connect_args)

    # 1. Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 2. Load instruments
    instruments = _load_instrument_map()
    # Sort so benchmarks (no benchmark_id) load first to satisfy FK constraints
    instruments.sort(key=lambda x: (x.get("benchmark_id") is not None, x["id"]))

    async with factory() as session:
        inst_loaded, inst_skipped = await _load_instruments(session, instruments)
    print(f"Instruments: {inst_loaded} loaded, {inst_skipped} skipped (existing).")

    # 3. Load price CSVs
    total_prices_loaded = 0
    total_prices_skipped = 0
    matched = 0
    no_csv = []

    async with factory() as session:
        for inst in instruments:
            csv_path = FETCHED_DIR / f"{inst['id']}.csv"
            if not csv_path.exists():
                no_csv.append(inst["id"])
                continue
            matched += 1
            price_rows = _read_csv_prices(csv_path, inst["id"])
            loaded, skipped = await _load_prices(session, inst["id"], price_rows)
            total_prices_loaded += loaded
            total_prices_skipped += skipped
            if loaded > 0:
                print(f"  {inst['id']}: {loaded} prices loaded, {skipped} skipped")

    # 4. Summary
    print("\n=== LOAD SUMMARY ===")
    print(f"Instruments:  {inst_loaded} new, {inst_skipped} existing")
    print(f"CSVs matched: {matched}/{len(instruments)}")
    print(f"Prices:       {total_prices_loaded} loaded, {total_prices_skipped} skipped")
    if no_csv:
        print(f"No CSV found: {', '.join(no_csv)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
