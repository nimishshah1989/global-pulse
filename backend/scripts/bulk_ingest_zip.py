"""Bulk ingest Stooq ZIP data — standalone script, no SQLAlchemy needed.

Reads a Stooq bulk download ZIP, discovers instruments, and loads all
OHLCV price data directly into SQLite using the stdlib sqlite3 module.
Works on Python 3.9+ with ZERO external dependencies.

Usage:
    cd backend
    python3 -m scripts.bulk_ingest_zip --zip ../data/stooq_bulk/d_us_txt.zip --region us
    python3 -m scripts.bulk_ingest_zip --zip ../data/stooq_bulk/d_us_txt.zip --region us --no-stocks
"""

import argparse
import csv
import io
import logging
import os
import sqlite3
import sys
import zipfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

# Default DB path: backend/momentum_compass.db
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _BACKEND_ROOT / "momentum_compass.db"

# ── Region config ──────────────────────────────────────────────────────

STOOQ_REGIONS = {
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
            "index": ["data/daily/uk/lse indices/"],
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

# ── Helpers ────────────────────────────────────────────────────────────


def _to_float(value):
    """Convert string to float, returning None for empty/invalid."""
    if not value or value.strip() == "":
        return None
    try:
        return float(Decimal(value.strip()))
    except (InvalidOperation, ValueError):
        return None


def _to_int(value):
    """Convert string to int volume."""
    if not value or value.strip() == "":
        return None
    try:
        return int(float(value.strip()))
    except (ValueError, OverflowError):
        return None


def _parse_date(value):
    """Parse date in YYYYMMDD or YYYY-MM-DD format. Returns ISO string."""
    value = value.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _classify_folder_type(file_path, region_config):
    """Determine folder type (stock/etf/index) from file path."""
    path_lower = file_path.lower()
    for folder_type, prefixes in region_config["paths"].items():
        for prefix in prefixes:
            if path_lower.startswith(prefix.lower()):
                return folder_type
    return None


def _parse_data_file(file_bytes, instrument_id):
    """Parse a Stooq CSV/TXT file into price row tuples.

    Handles both formats:
        <TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>
        Date,Open,High,Low,Close,Volume
    """
    rows = []
    try:
        text = file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return rows

    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None:
        return rows

    # Normalize: strip whitespace and angle brackets, lowercase
    normalized = [col.strip().strip("<>").lower() for col in header]

    # Map column names to indices
    col_map = {}
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
            close_val = _to_float(row[col_map["close"]])
            if close_val is None:
                continue
            rows.append((
                instrument_id,
                parsed_date,
                _to_float(row[col_map["open"]]) if "open" in col_map else None,
                _to_float(row[col_map["high"]]) if "high" in col_map else None,
                _to_float(row[col_map["low"]]) if "low" in col_map else None,
                close_val,
                _to_int(row[col_map["volume"]]) if "volume" in col_map else None,
            ))
        except (IndexError, KeyError):
            continue

    return rows


# ── Database setup ─────────────────────────────────────────────────────

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS instruments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ticker_stooq TEXT,
    ticker_yfinance TEXT,
    source TEXT NOT NULL DEFAULT 'stooq',
    asset_type TEXT NOT NULL,
    country TEXT,
    sector TEXT,
    hierarchy_level INTEGER NOT NULL,
    benchmark_id TEXT,
    currency TEXT NOT NULL DEFAULT 'USD',
    liquidity_tier INTEGER DEFAULT 2,
    is_active INTEGER DEFAULT 1,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS prices (
    instrument_id TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume INTEGER,
    PRIMARY KEY (instrument_id, date)
);

CREATE TABLE IF NOT EXISTS rs_scores (
    instrument_id TEXT NOT NULL,
    date TEXT NOT NULL,
    rs_line REAL,
    rs_ma_150 REAL,
    rs_trend TEXT,
    rs_pct_1m REAL,
    rs_pct_3m REAL,
    rs_pct_6m REAL,
    rs_pct_12m REAL,
    rs_composite REAL,
    rs_momentum REAL,
    volume_ratio REAL,
    vol_multiplier REAL,
    adjusted_rs_score REAL,
    quadrant TEXT,
    liquidity_tier INTEGER,
    extension_warning INTEGER DEFAULT 0,
    regime TEXT DEFAULT 'RISK_ON',
    PRIMARY KEY (instrument_id, date)
);
"""


def setup_db(db_path):
    """Create tables and return connection."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(CREATE_TABLES_SQL)
    conn.commit()
    return conn


# ── ETF Classification (from etf_classifier.py knowledge base) ────────
# Maps ticker_base (without .US suffix) → {country, sector, asset_type, benchmark_id, tier}

KNOWN_ETFS = {
    # COUNTRY ETFs
    "SPY": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "QQQ": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "NDQ", "tier": 1},
    "DIA": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "IVV": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "VOO": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "VTI": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "IWM": {"country": "US", "sector": "small_cap", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWF": {"country": "US", "sector": "growth", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWD": {"country": "US", "sector": "value", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "MDY": {"country": "US", "sector": "mid_cap", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "RSP": {"country": "US", "sector": "equal_weight", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "SCHD": {"country": "US", "sector": "dividends", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    # iShares MSCI single-country
    "EWU": {"country": "UK", "sector": None, "asset_type": "country_etf", "benchmark_id": "FTM", "tier": 1},
    "EWG": {"country": "DE", "sector": None, "asset_type": "country_etf", "benchmark_id": "DAX", "tier": 1},
    "EWQ": {"country": "FR", "sector": None, "asset_type": "country_etf", "benchmark_id": "CAC", "tier": 1},
    "EWJ": {"country": "JP", "sector": None, "asset_type": "country_etf", "benchmark_id": "NKX", "tier": 1},
    "EWH": {"country": "HK", "sector": None, "asset_type": "country_etf", "benchmark_id": "HSI", "tier": 1},
    "FXI": {"country": "CN", "sector": None, "asset_type": "country_etf", "benchmark_id": "CSI300", "tier": 1},
    "MCHI": {"country": "CN", "sector": None, "asset_type": "country_etf", "benchmark_id": "CSI300", "tier": 1},
    "EWY": {"country": "KR", "sector": None, "asset_type": "country_etf", "benchmark_id": "KS11", "tier": 1},
    "INDA": {"country": "IN", "sector": None, "asset_type": "country_etf", "benchmark_id": "NSEI", "tier": 1},
    "EWT": {"country": "TW", "sector": None, "asset_type": "country_etf", "benchmark_id": "TWII", "tier": 1},
    "EWA": {"country": "AU", "sector": None, "asset_type": "country_etf", "benchmark_id": "AXJO", "tier": 1},
    "EWZ": {"country": "BR", "sector": None, "asset_type": "country_etf", "benchmark_id": "BVSP", "tier": 1},
    "EWC": {"country": "CA", "sector": None, "asset_type": "country_etf", "benchmark_id": "GSPTSE", "tier": 1},
    "EWS": {"country": "SG", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWW": {"country": "MX", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWP": {"country": "ES", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWI": {"country": "IT", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWN": {"country": "NL", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWD": {"country": "SE", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWL": {"country": "CH", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "THD": {"country": "TH", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "KSA": {"country": "SA", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "DXJ": {"country": "JP", "sector": None, "asset_type": "country_etf", "benchmark_id": "NKX", "tier": 1},
    "EPI": {"country": "IN", "sector": None, "asset_type": "country_etf", "benchmark_id": "NSEI", "tier": 1},
    "INDY": {"country": "IN", "sector": None, "asset_type": "country_etf", "benchmark_id": "NSEI", "tier": 1},
    # Regional
    "ACWI": {"country": None, "sector": None, "asset_type": "benchmark", "benchmark_id": None, "tier": 1},
    "EEM": {"country": None, "sector": None, "asset_type": "benchmark", "benchmark_id": None, "tier": 1},
    "VEA": {"country": None, "sector": None, "asset_type": "benchmark", "benchmark_id": None, "tier": 1},
    "VWO": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "EFA": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "VT": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "VXUS": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "EZU": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "VGK": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    # US SECTOR (SPDR)
    "XLK": {"country": "US", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLF": {"country": "US", "sector": "financials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLV": {"country": "US", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLY": {"country": "US", "sector": "consumer_discretionary", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLP": {"country": "US", "sector": "consumer_staples", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLE": {"country": "US", "sector": "energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLI": {"country": "US", "sector": "industrials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLB": {"country": "US", "sector": "materials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLRE": {"country": "US", "sector": "real_estate", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLU": {"country": "US", "sector": "utilities", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XLC": {"country": "US", "sector": "communication_services", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    # US SECTOR (Vanguard)
    "VGT": {"country": "US", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VFH": {"country": "US", "sector": "financials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VHT": {"country": "US", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VDE": {"country": "US", "sector": "energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VIS": {"country": "US", "sector": "industrials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VCR": {"country": "US", "sector": "consumer_discretionary", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VDC": {"country": "US", "sector": "consumer_staples", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VAW": {"country": "US", "sector": "materials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VNQ": {"country": "US", "sector": "real_estate", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VPU": {"country": "US", "sector": "utilities", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "VOX": {"country": "US", "sector": "communication_services", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    # US SECTOR (iShares)
    "IYW": {"country": "US", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYF": {"country": "US", "sector": "financials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYH": {"country": "US", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYE": {"country": "US", "sector": "energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYJ": {"country": "US", "sector": "industrials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYC": {"country": "US", "sector": "consumer_discretionary", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYK": {"country": "US", "sector": "consumer_staples", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IDU": {"country": "US", "sector": "utilities", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYR": {"country": "US", "sector": "real_estate", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    # US SECTOR (Fidelity)
    "FTEC": {"country": "US", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FENY": {"country": "US", "sector": "energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FHLC": {"country": "US", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FDIS": {"country": "US", "sector": "consumer_discretionary", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FSTA": {"country": "US", "sector": "consumer_staples", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FIDU": {"country": "US", "sector": "industrials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FMAT": {"country": "US", "sector": "materials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FUTY": {"country": "US", "sector": "utilities", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FCOM": {"country": "US", "sector": "communication_services", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FREL": {"country": "US", "sector": "real_estate", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    # GLOBAL SECTOR (iShares)
    "IXN": {"country": None, "sector": "technology", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "IXG": {"country": None, "sector": "financials", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "IXJ": {"country": None, "sector": "healthcare", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "IXC": {"country": None, "sector": "energy", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "EXI": {"country": None, "sector": "industrials", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "RXI": {"country": None, "sector": "consumer_discretionary", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "KXI": {"country": None, "sector": "consumer_staples", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "JXI": {"country": None, "sector": "utilities", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "MXI": {"country": None, "sector": "materials", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "IXP": {"country": None, "sector": "communication_services", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    # THEMATIC
    "SOXX": {"country": "US", "sector": "semiconductors", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "SMH": {"country": "US", "sector": "semiconductors", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IBB": {"country": "US", "sector": "biotech", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XBI": {"country": "US", "sector": "biotech", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XHB": {"country": "US", "sector": "homebuilders", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XOP": {"country": "US", "sector": "oil_gas_exploration", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "KRE": {"country": "US", "sector": "regional_banks", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "KBE": {"country": "US", "sector": "banks", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XRT": {"country": "US", "sector": "retail", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ITA": {"country": "US", "sector": "aerospace_defense", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "HACK": {"country": "US", "sector": "cybersecurity", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ARKK": {"country": "US", "sector": "innovation", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "JETS": {"country": "US", "sector": "airlines", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "KWEB": {"country": "CN", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 1},
    "ICLN": {"country": None, "sector": "clean_energy", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "TAN": {"country": None, "sector": "solar", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "LIT": {"country": None, "sector": "lithium_battery", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    # COMMODITY
    "GLD": {"country": None, "sector": "gold", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "IAU": {"country": None, "sector": "gold", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "SLV": {"country": None, "sector": "silver", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "GDX": {"country": None, "sector": "gold_miners", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "USO": {"country": None, "sector": "crude_oil", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "DBC": {"country": None, "sector": "commodities_broad", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "URA": {"country": None, "sector": "uranium", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},
    "BITO": {"country": None, "sector": "crypto", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "IBIT": {"country": None, "sector": "crypto", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    # BOND
    "AGG": {"country": "US", "sector": "aggregate_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "BND": {"country": "US", "sector": "aggregate_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "TLT": {"country": "US", "sector": "treasury_long", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "IEF": {"country": "US", "sector": "treasury_mid", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "SHY": {"country": "US", "sector": "treasury_short", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "LQD": {"country": "US", "sector": "investment_grade", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "HYG": {"country": "US", "sector": "high_yield", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "EMB": {"country": None, "sector": "em_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
}


def _enrich_etfs(conn):
    """Update ETF instruments with sector/country/asset_type from KNOWN_ETFS."""
    enriched = 0
    for ticker_base, info in KNOWN_ETFS.items():
        # Instrument IDs are TICKER_SUFFIX format (e.g. XLK_US)
        for suffix in ("US", "UK", "JP", "HK", "DE"):
            inst_id = "{}_{}".format(ticker_base, suffix)
            result = conn.execute(
                "SELECT id FROM instruments WHERE id = ?", (inst_id,)
            ).fetchone()
            if result:
                conn.execute(
                    "UPDATE instruments SET "
                    "sector = ?, asset_type = ?, benchmark_id = ?, "
                    "liquidity_tier = ?, country = COALESCE(?, country) "
                    "WHERE id = ?",
                    (info.get("sector"), info["asset_type"],
                     info.get("benchmark_id"), info.get("tier", 2),
                     info.get("country"), inst_id),
                )
                enriched += 1
                break
    conn.commit()
    logger.info("Enriched %d ETFs with sector/country/asset_type", enriched)


# ── Main pipeline ──────────────────────────────────────────────────────

def bulk_ingest_zip(zip_path, region, include_stocks=True, db_path=None):
    """Process a Stooq bulk ZIP: discover instruments + load all prices."""

    if region not in STOOQ_REGIONS:
        logger.error("Unknown region: %s. Available: %s",
                      region, list(STOOQ_REGIONS.keys()))
        return

    config = STOOQ_REGIONS[region]
    suffix = config["suffix"]
    country = config["country"]
    currency = config["currency"]

    if db_path is None:
        db_path = _DEFAULT_DB

    stats = {
        "instruments_new": 0,
        "instruments_existing": 0,
        "prices_loaded": 0,
        "files_processed": 0,
        "files_failed": 0,
        "files_total": 0,
    }

    # Set up database
    conn = setup_db(db_path)
    logger.info("Database: %s", db_path)

    # Open ZIP
    logger.info("Opening ZIP: %s (%.1f MB)",
                zip_path, zip_path.stat().st_size / 1024 / 1024)

    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        logger.error("Invalid ZIP file: %s", zip_path)
        return

    # Find all data files (.txt or .csv)
    all_files = [f for f in zf.namelist()
                 if f.lower().endswith(".csv") or f.lower().endswith(".txt")]
    stats["files_total"] = len(all_files)
    logger.info("Found %d data files in ZIP", len(all_files))

    # Show sample paths for debugging
    if all_files:
        logger.info("Sample file paths:")
        for p in all_files[:10]:
            logger.info("  %s", p)

        # Show detected directories
        dirs = set()
        for f in all_files:
            parts = f.lower().split("/")
            if len(parts) >= 4:
                dirs.add("/".join(parts[:4]) + "/")
        logger.info("Detected directories:")
        for d in sorted(dirs):
            logger.info("  %s", d)

    # Get existing instrument IDs
    existing_ids = set(
        row[0] for row in conn.execute("SELECT id FROM instruments").fetchall()
    )

    # Process each file
    cursor = conn.cursor()

    for file_path in all_files:
        folder_type = _classify_folder_type(file_path, config)
        if folder_type is None:
            continue
        if folder_type == "stock" and not include_stocks:
            continue

        ticker_base = Path(file_path).stem.upper()

        # Build IDs
        if suffix:
            instrument_id = "{}_{}".format(ticker_base, suffix)
        else:
            instrument_id = ticker_base

        if folder_type == "index":
            stooq_ticker = "^{}".format(ticker_base)
        elif suffix:
            stooq_ticker = "{}.{}".format(ticker_base, suffix)
        else:
            stooq_ticker = ticker_base

        # Determine asset type
        type_map = {"stock": ("stock", 3), "etf": ("etf", 2), "index": ("country_index", 1)}
        asset_type, hierarchy_level = type_map.get(folder_type, ("unknown", 2))

        # Register instrument if new
        if instrument_id not in existing_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO instruments "
                "(id, name, ticker_stooq, source, asset_type, country, "
                "hierarchy_level, currency, liquidity_tier, is_active) "
                "VALUES (?, ?, ?, 'stooq', ?, ?, ?, ?, 2, 1)",
                (instrument_id, ticker_base, stooq_ticker, asset_type,
                 country, hierarchy_level, currency),
            )
            existing_ids.add(instrument_id)
            stats["instruments_new"] += 1
        else:
            stats["instruments_existing"] += 1

        # Parse and load price data
        try:
            file_bytes = zf.read(file_path)
            price_rows = _parse_data_file(file_bytes, instrument_id)

            if price_rows:
                cursor.executemany(
                    "INSERT OR IGNORE INTO prices "
                    "(instrument_id, date, open, high, low, close, volume) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    price_rows,
                )
                stats["prices_loaded"] += len(price_rows)
                stats["files_processed"] += 1

        except Exception as exc:
            stats["files_failed"] += 1
            if stats["files_failed"] <= 10:
                logger.warning("Failed %s: %s", file_path, exc)

        # Commit every 200 instruments
        total_done = stats["files_processed"] + stats["files_failed"]
        if total_done > 0 and total_done % 200 == 0:
            conn.commit()
            logger.info(
                "Progress: %d files processed, %d instruments, %d price rows",
                stats["files_processed"],
                stats["instruments_new"],
                stats["prices_loaded"],
            )

    conn.commit()
    zf.close()

    # Phase 4: Enrich ETFs with sector/country/asset_type from KNOWN_ETFS
    _enrich_etfs(conn)

    # Final stats
    row_count = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    inst_count = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    conn.close()

    logger.info("=" * 60)
    logger.info("BULK INGEST COMPLETE — Region: %s", region.upper())
    logger.info("  Instruments: %d new, %d existing, %d total in DB",
                stats["instruments_new"], stats["instruments_existing"], inst_count)
    logger.info("  Files:       %d total, %d processed, %d failed",
                stats["files_total"], stats["files_processed"], stats["files_failed"])
    logger.info("  Prices:      %d rows loaded, %d total in DB",
                stats["prices_loaded"], row_count)
    logger.info("  Database:    %s", db_path)
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Bulk ingest Stooq ZIP data into SQLite database",
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
    parser.add_argument(
        "--db", type=Path, default=None,
        help="Path to SQLite database (default: backend/momentum_compass.db)",
    )

    args = parser.parse_args()

    if not args.zip.exists():
        logger.error("ZIP file not found: %s", args.zip)
        sys.exit(1)

    bulk_ingest_zip(
        zip_path=args.zip,
        region=args.region,
        include_stocks=not args.no_stocks,
        db_path=args.db,
    )


if __name__ == "__main__":
    main()
