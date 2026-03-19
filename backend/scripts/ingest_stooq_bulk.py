"""Ingest Stooq bulk CSV/TXT files into production PostgreSQL.

Reads ETF and index files from the Desktop download folders.
Skips all stocks, bonds, futures, options, crypto, currencies.
Streams directly to the production database.

Usage:
    python backend/scripts/ingest_stooq_bulk.py [--db-url DATABASE_URL]
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stooq data paths on Desktop
# ---------------------------------------------------------------------------
DESKTOP_DATA = Path(os.path.expanduser("~/Desktop/global-pulse/data"))

# Paths to ingest (ETFs + indices ONLY)
INGEST_PATHS = [
    # (path, region, asset_type, country)
    (DESKTOP_DATA / "hong kong" / "daily" / "hk" / "hkex etfs", "hk", "etf", "HK"),
    (DESKTOP_DATA / "japan" / "daily" / "jp" / "tse etfs", "jp", "etf", "JP"),
    (DESKTOP_DATA / "japan" / "daily" / "jp" / "tse indices", "jp", "country_index", "JP"),
    (DESKTOP_DATA / "world" / "daily" / "world" / "indices", "world", "country_index", None),
    # UK ETFs are in subdirectories 1, 2, 3
    (DESKTOP_DATA / "united kingdom" / "daily" / "uk" / "lse etfs", "uk", "etf", "UK"),
]

# GICS sector keywords for ETF classification
GICS_SECTOR_MAP: dict[str, list[str]] = {
    "technology": [
        "tech", "software", "semiconductor", "cyber", "cloud", "ai ", "artificial",
        "robot", "automat", "innovat", "digital", "internet", "fintech", "blockchain",
        "computing", "data", "5g", "metaverse", "saas",
    ],
    "financials": [
        "financ", "bank", "insur", "broker", "lending", "credit", "mortgage",
        "payment", "asset management",
    ],
    "healthcare": [
        "health", "biotech", "pharma", "medic", "genomic", "drug", "therapeutic",
        "cannabis", "hospital",
    ],
    "energy": [
        "energy", "oil", "gas", "petrol", "solar", "wind", "clean energy",
        "nuclear", "uranium", "mlp", "pipeline",
    ],
    "industrials": [
        "industr", "aerospace", "defense", "defence", "transport", "logistic",
        "infrastr", "construct", "engineer", "manufactur", "machinery",
    ],
    "materials": [
        "material", "mining", "gold", "silver", "metal", "steel", "copper",
        "lithium", "rare earth", "commodity", "commodit", "palladium", "platinum",
        "timber", "lumber", "chemical",
    ],
    "consumer_discretionary": [
        "consumer disc", "retail", "luxury", "travel", "leisure", "hotel",
        "gaming", "entertainment", "media", "home build", "apparel", "fashion",
        "auto", "electric vehicle", "ev ",
    ],
    "consumer_staples": [
        "consumer stap", "food", "beverage", "agri", "organic", "nutrition",
        "household",
    ],
    "communication_services": [
        "communicat", "telecom", "streaming", "social media",
    ],
    "utilities": [
        "utilit", "water", "electric power", "regulated",
    ],
    "real_estate": [
        "real estate", "reit", "property", "propert", "housing", "mortgage reit",
    ],
}

# World index ticker → country mapping
WORLD_INDEX_COUNTRY: dict[str, str] = {
    "^spx": "US", "^dji": "US", "^ndq": "US", "^ndx": "US",
    "^ftm": "UK", "^ukx": "UK",
    "^dax": "DE", "^cdax": "DE", "^mdax": "DE",
    "^cac": "FR",
    "^nkx": "JP",
    "^hsi": "HK",
    "^kospi": "KR",
    "^twse": "TW",
    "^aex": "NL", "^bel20": "BE", "^fmib": "IT", "^ibex": "ES",
    "^hex": "FI", "^omxs": "SE", "^omxc25": "DK", "^oseax": "NO",
    "^smi": "CH", "^ath": "GR", "^psi20": "PT", "^px": "CZ",
    "^bux": "HU", "^bet": "RO", "^sax": "SK", "^omxr": "LV",
    "^omxt": "EE", "^omxv": "LT", "^sofix": "BG",
    "^bvp": "BR", "^ipc": "MX", "^ipsa": "CL",
    "^tsx": "CA",
    "^nz50": "NZ",
    "^set": "TH", "^klci": "MY", "^sti": "SG", "^psei": "PH",
    "^jci": "ID",
    "^xu100": "TR", "^tasi": "SA",
    "^shc": "CN", "^shbs": "CN",
    "^top40": "ZA",
    "^moex": "RU", "^moex10": "RU", "^mcftr": "RU", "^rts": "RU", "^rtstr": "RU",
    "^mrv": "RU",
    "^snx": "EU", "^sdxp": "EU", "^tdxp": "EU", "^nomuc": "DE",
    "^cry": "US",  # crypto index
    "^djc": "US", "^djt": "US", "^dju": "US",
}


def classify_sector(name: str) -> str | None:
    """Classify an ETF into a GICS sector based on its name."""
    name_lower = name.lower()
    for sector, keywords in GICS_SECTOR_MAP.items():
        for kw in keywords:
            if kw in name_lower:
                return sector
    return None


def parse_ticker_from_filename(filename: str) -> str:
    """Extract ticker from Stooq filename. E.g., '2800.hk.txt' → '2800.HK'"""
    name = filename.replace(".txt", "").replace(".csv", "")
    return name.upper()


def make_instrument_id(ticker: str) -> str:
    """Create a normalized instrument ID from a Stooq ticker.

    Examples:
        2800.HK → 2800_HK
        ^SPX → SPX
        XLK.US → XLK_US
    """
    clean = ticker.replace("^", "").replace(".", "_")
    return clean


def parse_stooq_file(filepath: Path) -> list[dict]:
    """Parse a single Stooq TXT/CSV file into OHLCV rows."""
    rows = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return []
            # Stooq format: <TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>
            for row in reader:
                if len(row) < 8:
                    continue
                try:
                    date_str = row[2].strip()
                    if len(date_str) != 8:
                        continue
                    d = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                    # Skip very old data (before 2000)
                    if d.year < 2000:
                        continue
                    o = Decimal(row[4]) if row[4].strip() else None
                    h = Decimal(row[5]) if row[5].strip() else None
                    lo = Decimal(row[6]) if row[6].strip() else None
                    c = Decimal(row[7]) if row[7].strip() else None
                    if c is None or c == 0:
                        continue
                    vol_str = row[8].strip() if len(row) > 8 else "0"
                    vol = int(float(vol_str)) if vol_str else 0
                    rows.append({
                        "date": d,
                        "open": float(o) if o else None,
                        "high": float(h) if h else None,
                        "low": float(lo) if lo else None,
                        "close": float(c),
                        "volume": vol,
                    })
                except (ValueError, IndexError, ArithmeticError):
                    continue
    except Exception as e:
        logger.warning("Failed to parse %s: %s", filepath, e)
    return rows


def find_all_files(base_path: Path) -> list[Path]:
    """Recursively find all .txt files under a path."""
    files = []
    if not base_path.exists():
        logger.warning("Path not found: %s", base_path)
        return files
    for item in base_path.rglob("*.txt"):
        if item.is_file():
            files.append(item)
    return files


def ingest_to_db(db_url: str) -> None:
    """Main ingestion function — parse all files and insert into PostgreSQL."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    # First, remove existing stocks from DB to reduce size
    logger.info("Removing stock instruments from database...")
    cur.execute("DELETE FROM prices WHERE instrument_id IN (SELECT id FROM instruments WHERE asset_type = 'stock')")
    cur.execute("DELETE FROM rs_scores WHERE instrument_id IN (SELECT id FROM instruments WHERE asset_type = 'stock')")
    cur.execute("DELETE FROM instruments WHERE asset_type = 'stock'")
    conn.commit()
    logger.info("Stocks removed.")

    total_instruments = 0
    total_prices = 0

    for base_path, region, asset_type, default_country in INGEST_PATHS:
        files = find_all_files(base_path)
        logger.info("Found %d files in %s (%s)", len(files), base_path, region)

        batch_instruments = []
        batch_prices = []

        for filepath in files:
            ticker = parse_ticker_from_filename(filepath.name)
            instrument_id = make_instrument_id(ticker)

            # Determine country
            country = default_country
            if region == "world":
                country = WORLD_INDEX_COUNTRY.get(ticker.lower().replace("_", "^").replace("^", "^"), None)
                # Try with ^ prefix
                ticker_lookup = "^" + ticker.lower() if not ticker.startswith("^") else ticker.lower()
                country = WORLD_INDEX_COUNTRY.get(ticker_lookup, country)
                # For world indices, restore ^ in ticker
                if not ticker.startswith("^"):
                    ticker = "^" + ticker

            # Determine hierarchy level
            hierarchy = 1 if asset_type == "country_index" else 2

            # Parse ETF name from ticker (best effort)
            name = ticker

            # Parse OHLCV data
            rows = parse_stooq_file(filepath)
            if not rows:
                continue

            # Classify sector (for ETFs)
            sector = None  # Will be classified in Phase 3

            # Determine currency
            currency = "USD"
            if default_country == "HK":
                currency = "HKD"
            elif default_country == "JP":
                currency = "JPY"
            elif default_country == "UK":
                currency = "GBP"

            batch_instruments.append({
                "id": instrument_id,
                "name": name,
                "ticker_stooq": ticker,
                "ticker_yfinance": None,
                "source": "stooq",
                "asset_type": asset_type,
                "country": country,
                "sector": sector,
                "hierarchy_level": hierarchy,
                "benchmark_id": None,
                "currency": currency,
                "liquidity_tier": 2,
                "is_active": True,
            })

            for row in rows:
                batch_prices.append((
                    instrument_id,
                    row["date"],
                    row["open"],
                    row["high"],
                    row["low"],
                    row["close"],
                    row["volume"],
                ))

        # Batch insert instruments
        if batch_instruments:
            for inst in batch_instruments:
                cur.execute(
                    """INSERT INTO instruments (id, name, ticker_stooq, ticker_yfinance, source,
                       asset_type, country, sector, hierarchy_level, benchmark_id, currency,
                       liquidity_tier, is_active)
                       VALUES (%(id)s, %(name)s, %(ticker_stooq)s, %(ticker_yfinance)s, %(source)s,
                               %(asset_type)s, %(country)s, %(sector)s, %(hierarchy_level)s,
                               %(benchmark_id)s, %(currency)s, %(liquidity_tier)s, %(is_active)s)
                       ON CONFLICT (id) DO UPDATE SET
                           name = EXCLUDED.name,
                           country = COALESCE(EXCLUDED.country, instruments.country),
                           asset_type = EXCLUDED.asset_type,
                           hierarchy_level = EXCLUDED.hierarchy_level,
                           currency = EXCLUDED.currency
                    """,
                    inst,
                )
            conn.commit()
            total_instruments += len(batch_instruments)
            logger.info("Inserted %d instruments from %s", len(batch_instruments), region)

        # Batch insert prices
        if batch_prices:
            # Insert in chunks of 10000
            for i in range(0, len(batch_prices), 10000):
                chunk = batch_prices[i:i+10000]
                execute_values(
                    cur,
                    """INSERT INTO prices (instrument_id, date, open, high, low, close, volume)
                       VALUES %s
                       ON CONFLICT (instrument_id, date) DO UPDATE SET
                           close = EXCLUDED.close,
                           volume = EXCLUDED.volume
                    """,
                    chunk,
                )
                conn.commit()
            total_prices += len(batch_prices)
            logger.info("Inserted %d price rows from %s", len(batch_prices), region)

    # Summary
    logger.info("=== Ingestion Complete ===")
    logger.info("Total instruments: %d", total_instruments)
    logger.info("Total price rows: %d", total_prices)

    # Verify counts
    cur.execute("SELECT asset_type, country, COUNT(*) FROM instruments GROUP BY asset_type, country ORDER BY COUNT(*) DESC LIMIT 30")
    logger.info("=== Instrument breakdown ===")
    for row in cur.fetchall():
        logger.info("  %s | %s | %d", row[0], row[1], row[2])

    cur.execute("SELECT COUNT(*) FROM prices")
    logger.info("Total prices in DB: %d", cur.fetchone()[0])

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Stooq bulk data")
    parser.add_argument(
        "--db-url",
        default="postgresql://compass:compass123@localhost:5433/momentum_compass",
        help="PostgreSQL connection URL",
    )
    args = parser.parse_args()
    ingest_to_db(args.db_url)
