"""Export Stooq bulk data to CSV files for server-side import.

Reads ETF and index files from Desktop, generates two CSVs:
1. instruments.csv — instrument registry
2. prices.csv — OHLCV data

These can be SCP'd to the server and imported with COPY.

Usage:
    python backend/scripts/export_stooq_to_csv.py
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DESKTOP_DATA = Path(os.path.expanduser("~/Desktop/global-pulse/data"))
OUTPUT_DIR = Path(os.path.expanduser("~/Desktop/global-pulse"))

INGEST_PATHS = [
    (DESKTOP_DATA / "hong kong" / "daily" / "hk" / "hkex etfs", "hk", "etf", "HK"),
    (DESKTOP_DATA / "japan" / "daily" / "jp" / "tse etfs", "jp", "etf", "JP"),
    (DESKTOP_DATA / "japan" / "daily" / "jp" / "tse indices", "jp", "country_index", "JP"),
    (DESKTOP_DATA / "world" / "daily" / "world" / "indices", "world", "country_index", None),
    (DESKTOP_DATA / "united kingdom" / "daily" / "uk" / "lse etfs", "uk", "etf", "UK"),
]

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
    "^moex": "RU", "^moex10": "RU", "^rts": "RU",
    "^snx": "EU", "^sdxp": "EU", "^tdxp": "EU",
    "^cry": "US", "^djc": "US", "^djt": "US", "^dju": "US",
    "^mrv": "RU", "^rtstr": "RU", "^mcftr": "RU", "^nomuc": "DE",
}


def parse_ticker(filename: str) -> str:
    return filename.replace(".txt", "").replace(".csv", "").upper()


def make_id(ticker: str) -> str:
    return ticker.replace("^", "").replace(".", "_")


def parse_file(filepath: Path) -> list[tuple]:
    rows = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) < 8:
                    continue
                try:
                    ds = row[2].strip()
                    if len(ds) != 8:
                        continue
                    d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
                    if d.year < 2000:
                        continue
                    c = float(row[7]) if row[7].strip() else None
                    if not c or c == 0:
                        continue
                    o = float(row[4]) if row[4].strip() else None
                    h = float(row[5]) if row[5].strip() else None
                    lo = float(row[6]) if row[6].strip() else None
                    vol = int(float(row[8].strip())) if len(row) > 8 and row[8].strip() else 0
                    rows.append((d, o, h, lo, c, vol))
                except (ValueError, IndexError):
                    continue
    except Exception as e:
        logger.warning("Failed: %s: %s", filepath, e)
    return rows


def main() -> None:
    inst_file = OUTPUT_DIR / "instruments_export.csv"
    price_file = OUTPUT_DIR / "prices_export.csv"

    total_instr = 0
    total_prices = 0

    with open(inst_file, "w", newline="") as fi, open(price_file, "w", newline="") as fp:
        iw = csv.writer(fi)
        iw.writerow(["id", "name", "ticker_stooq", "source", "asset_type", "country",
                      "hierarchy_level", "currency", "liquidity_tier", "is_active"])
        pw = csv.writer(fp)
        pw.writerow(["instrument_id", "date", "open", "high", "low", "close", "volume"])

        for base_path, region, asset_type, default_country in INGEST_PATHS:
            files = list(base_path.rglob("*.txt")) if base_path.exists() else []
            logger.info("Processing %d files from %s", len(files), base_path)

            for filepath in files:
                ticker = parse_ticker(filepath.name)
                iid = make_id(ticker)

                country = default_country
                if region == "world":
                    lookup = "^" + ticker.lower() if not ticker.startswith("^") else ticker.lower()
                    country = WORLD_INDEX_COUNTRY.get(lookup, None)
                    if not ticker.startswith("^"):
                        ticker = "^" + ticker

                hierarchy = 1 if asset_type == "country_index" else 2
                currency = {"HK": "HKD", "JP": "JPY", "UK": "GBP"}.get(default_country or "", "USD")

                rows = parse_file(filepath)
                if not rows:
                    continue

                iw.writerow([iid, ticker, ticker, "stooq", asset_type, country,
                             hierarchy, currency, 2, "t"])
                total_instr += 1

                for d, o, h, lo, c, vol in rows:
                    pw.writerow([iid, d.isoformat(), o, h, lo, c, vol])
                    total_prices += 1

    logger.info("Exported %d instruments to %s", total_instr, inst_file)
    logger.info("Exported %d price rows to %s", total_prices, price_file)
    logger.info("File sizes: instruments=%s, prices=%s",
                f"{inst_file.stat().st_size / 1024 / 1024:.1f}MB",
                f"{price_file.stat().st_size / 1024 / 1024:.1f}MB")


if __name__ == "__main__":
    main()
