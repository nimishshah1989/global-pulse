"""Enrich all ETFs in the database with real metadata from yfinance.

For each ETF in the instruments table, fetches:
- Full name (longName)
- Category (e.g. "Large Blend", "Technology", "Japan Stock")
- Sector exposure
- Country exposure
- Asset class (equity, bond, commodity)

Then classifies into our schema: asset_type, sector, country, benchmark_id, hierarchy_level.

Usage:
    cd backend
    pip3 install yfinance
    python3 -m scripts.enrich_etfs_from_yfinance

    # Dry run (show what would change, don't write):
    python3 -m scripts.enrich_etfs_from_yfinance --dry-run

    # Only process first N:
    python3 -m scripts.enrich_etfs_from_yfinance --limit 50
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sqlite3
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _BACKEND_ROOT / "momentum_compass.db"

# ── Category → Sector mapping ─────────────────────────────────────────
# yfinance ETF categories mapped to our GICS sector slugs

CATEGORY_TO_SECTOR = {
    # Technology
    "technology": "technology",
    "communications": "communication_services",
    "china technology": "technology",
    # Financials
    "financial": "financials",
    "financials": "financials",
    # Healthcare
    "health": "healthcare",
    "healthcare": "healthcare",
    "biotech": "biotech",
    # Energy
    "energy": "energy",
    "oil": "energy",
    "natural resources": "energy",
    "mlp": "energy",
    # Industrials
    "industrial": "industrials",
    "industrials": "industrials",
    "infrastructure": "industrials",
    "transportation": "industrials",
    "aerospace": "aerospace_defense",
    # Consumer
    "consumer cyclical": "consumer_discretionary",
    "consumer defensive": "consumer_staples",
    "consumer discretionary": "consumer_discretionary",
    "consumer staples": "consumer_staples",
    "retail": "retail",
    # Materials
    "basic materials": "materials",
    "materials": "materials",
    "metals": "materials",
    "mining": "materials",
    "gold": "gold",
    "silver": "silver",
    "precious metals": "gold_miners",
    # Utilities
    "utilities": "utilities",
    # Real Estate
    "real estate": "real_estate",
    # Semiconductors
    "semiconductor": "semiconductors",
    "semiconductors": "semiconductors",
    # Bonds
    "long government": "treasury_long",
    "intermediate government": "treasury_mid",
    "short government": "treasury_short",
    "ultrashort bond": "treasury_short",
    "long-term bond": "treasury_long",
    "intermediate-term bond": "aggregate_bond",
    "short-term bond": "treasury_short",
    "corporate bond": "investment_grade",
    "high yield bond": "high_yield",
    "inflation-protected bond": "tips",
    "muni": "municipal",
    "municipal": "municipal",
    "mortgage": "mortgage_backed",
    "emerging markets bond": "em_bond",
    "world bond": "intl_bond",
    "total bond market": "aggregate_bond",
    # Commodities
    "commodities": "commodities_broad",
    "commodity": "commodities_broad",
    "agriculture": "agriculture",
    # Clean energy / thematic
    "clean energy": "clean_energy",
    "solar": "solar",
    "alternative energy": "clean_energy",
    "water": "utilities",
    "cannabis": "cannabis",
    "cloud computing": "cloud_computing",
    "cybersecurity": "cybersecurity",
    "robotics": "robotics_ai",
    "artificial intelligence": "artificial_intelligence",
    "blockchain": "blockchain",
    "digital": "technology",
    "gaming": "gaming",
    "esports": "esports_gaming",
    # Crypto
    "digital assets": "crypto",
    "cryptocurrency": "crypto",
    "bitcoin": "crypto",
    "ethereum": "crypto",
}

# yfinance category keywords → country mapping
CATEGORY_TO_COUNTRY = {
    "japan": "JP",
    "china": "CN",
    "india": "IN",
    "korea": "KR",
    "taiwan": "TW",
    "australia": "AU",
    "brazil": "BR",
    "canada": "CA",
    "germany": "DE",
    "france": "FR",
    "united kingdom": "UK",
    "uk": "UK",
    "hong kong": "HK",
    "mexico": "MX",
    "italy": "IT",
    "spain": "ES",
    "switzerland": "CH",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "singapore": "SG",
    "thailand": "TH",
    "indonesia": "ID",
    "philippines": "PH",
    "malaysia": "MY",
    "south africa": "ZA",
    "israel": "IL",
    "saudi": "SA",
    "turkey": "TR",
    "chile": "CL",
    "colombia": "CO",
    "peru": "PE",
    "argentina": "AR",
    "vietnam": "VN",
    "new zealand": "NZ",
    "poland": "PL",
    "netherlands": "NL",
    "belgium": "BE",
    "austria": "AT",
    "finland": "FI",
    "ireland": "IE",
    "greece": "GR",
    "russia": "RU",
    "egypt": "EG",
    "qatar": "QA",
    "uae": "AE",
    "nigeria": "NG",
    "pakistan": "PK",
}

# Benchmark mapping
COUNTRY_BENCHMARKS = {
    "US": "SPX", "UK": "FTM", "DE": "DAX", "FR": "CAC",
    "JP": "NKX", "HK": "HSI", "CN": "CSI300", "KR": "KS11",
    "IN": "NSEI", "TW": "TWII", "AU": "AXJO", "BR": "BVSP",
    "CA": "GSPTSE",
}


def _classify_from_yfinance(info: dict, ticker_base: str) -> dict:
    """Classify an ETF from its yfinance info dict.

    Returns dict with: name, sector, country, asset_type, benchmark_id,
    hierarchy_level, liquidity_tier, asset_class.
    """
    result = {
        "name": None,
        "sector": None,
        "country": None,
        "asset_type": "etf",
        "benchmark_id": None,
        "hierarchy_level": 2,
        "liquidity_tier": 2,
        "asset_class": "equity",
    }

    # Extract name
    result["name"] = info.get("longName") or info.get("shortName") or ticker_base

    # Get category (most useful field for classification)
    category = (info.get("category") or "").lower()
    quote_type = (info.get("quoteType") or "").lower()

    # Determine asset class from category
    is_bond = any(kw in category for kw in [
        "bond", "treasury", "government", "corporate", "municipal",
        "fixed income", "tips", "inflation", "mortgage", "credit",
        "ultrashort", "floating rate", "bank loan",
    ])
    is_commodity = any(kw in category for kw in [
        "commodit", "gold", "silver", "oil", "energy commodity",
        "precious metal", "agriculture", "natural gas",
    ])
    is_crypto = any(kw in category for kw in [
        "digital asset", "crypto", "bitcoin", "ethereum",
    ])

    if is_bond:
        result["asset_class"] = "fixed_income"
        result["asset_type"] = "bond_etf"
        result["hierarchy_level"] = 2
        result["benchmark_id"] = None
    elif is_commodity:
        result["asset_class"] = "commodity"
        result["asset_type"] = "commodity_etf"
        result["benchmark_id"] = None
    elif is_crypto:
        result["asset_class"] = "crypto"
        result["asset_type"] = "commodity_etf"
        result["benchmark_id"] = None

    # Determine sector from category
    for keyword, sector_slug in CATEGORY_TO_SECTOR.items():
        if keyword in category:
            result["sector"] = sector_slug
            if result["asset_type"] == "etf":
                result["asset_type"] = "sector_etf"
            break

    # Determine country from category
    for keyword, country_code in CATEGORY_TO_COUNTRY.items():
        if keyword in category:
            result["country"] = country_code
            if result["asset_type"] == "etf" and result["sector"] is None:
                result["asset_type"] = "country_etf"
                result["hierarchy_level"] = 1
            break

    # Check for regional/global patterns
    is_global = any(kw in category for kw in [
        "world", "global", "international", "foreign",
        "diversified emerging", "emerging markets",
        "pacific", "europe", "asia", "latin america",
    ])
    if is_global and result["country"] is None:
        if result["sector"]:
            result["asset_type"] = "global_sector_etf"
        else:
            result["asset_type"] = "regional_etf"
        result["benchmark_id"] = "ACWI"

    # US-focused
    if result["country"] is None and not is_global:
        us_keywords = [
            "large blend", "large growth", "large value",
            "mid-cap", "small blend", "small growth", "small value",
            "s&p 500", "total stock", "nasdaq", "dow jones",
            "russell", "u.s.", "domestic",
        ]
        if any(kw in category for kw in us_keywords):
            result["country"] = "US"

    # Set benchmark based on country
    if result["country"] and result["benchmark_id"] is None:
        result["benchmark_id"] = COUNTRY_BENCHMARKS.get(
            result["country"], "ACWI"
        )

    # If still unclassified equity ETF with a country
    if result["asset_type"] == "etf" and result["country"]:
        if result["sector"]:
            result["asset_type"] = "sector_etf"
        else:
            result["asset_type"] = "country_etf"

    return result


def enrich_etfs(db_path=None, dry_run=False, limit=None):
    """Fetch yfinance metadata for all ETFs and update the database."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed. Run: pip3 install yfinance")
        sys.exit(1)

    if db_path is None:
        db_path = _DEFAULT_DB

    conn = sqlite3.connect(str(db_path))

    # Get all ETF instruments
    query = "SELECT id, name, ticker_stooq FROM instruments WHERE asset_type IN ('etf', 'etf_unclassified')"
    if limit:
        query += " LIMIT {}".format(limit)

    etfs = conn.execute(query).fetchall()
    logger.info("Found %d ETFs to enrich", len(etfs))

    stats = {"enriched": 0, "failed": 0, "skipped": 0, "already_classified": 0}
    enrichment_log = []

    for i, (inst_id, name, ticker_stooq) in enumerate(etfs):
        # Convert Stooq ticker to yfinance format
        if ticker_stooq and ticker_stooq.endswith(".US"):
            yf_ticker = ticker_stooq[:-3]  # strip .US
        elif ticker_stooq and ticker_stooq.startswith("^"):
            yf_ticker = ticker_stooq
        else:
            yf_ticker = inst_id.replace("_US", "").replace("_", ".")
            if not yf_ticker:
                stats["skipped"] += 1
                continue

        try:
            ticker_obj = yf.Ticker(yf_ticker)
            info = ticker_obj.info

            if not info or info.get("quoteType") is None:
                stats["failed"] += 1
                continue

            classification = _classify_from_yfinance(info, yf_ticker)

            if dry_run:
                if classification["sector"] or classification["country"]:
                    enrichment_log.append({
                        "id": inst_id,
                        "yf_ticker": yf_ticker,
                        "name": classification["name"],
                        "category": info.get("category", ""),
                        "sector": classification["sector"],
                        "country": classification["country"],
                        "asset_type": classification["asset_type"],
                    })
            else:
                conn.execute(
                    "UPDATE instruments SET "
                    "name = ?, sector = COALESCE(?, sector), "
                    "country = COALESCE(?, country), "
                    "asset_type = ?, benchmark_id = COALESCE(?, benchmark_id), "
                    "hierarchy_level = ?, liquidity_tier = ? "
                    "WHERE id = ?",
                    (
                        classification["name"],
                        classification["sector"],
                        classification["country"],
                        classification["asset_type"],
                        classification["benchmark_id"],
                        classification["hierarchy_level"],
                        classification["liquidity_tier"],
                        inst_id,
                    ),
                )
            stats["enriched"] += 1

        except Exception as exc:
            stats["failed"] += 1
            if stats["failed"] <= 5:
                logger.warning("Failed %s (%s): %s", inst_id, yf_ticker, exc)

        # Rate limit: ~2 requests/second
        time.sleep(0.5)

        # Progress
        if (i + 1) % 50 == 0:
            conn.commit()
            logger.info(
                "Progress: %d/%d (enriched=%d, failed=%d)",
                i + 1, len(etfs), stats["enriched"], stats["failed"],
            )

    conn.commit()

    if dry_run and enrichment_log:
        logger.info("\n=== DRY RUN RESULTS ===")
        for entry in enrichment_log[:30]:
            logger.info(
                "  %-12s %-40s sector=%-25s country=%-4s type=%s",
                entry["id"], entry["name"][:40],
                entry["sector"] or "-",
                entry["country"] or "-",
                entry["asset_type"],
            )
        if len(enrichment_log) > 30:
            logger.info("  ... and %d more", len(enrichment_log) - 30)

    # Show classification stats
    if not dry_run:
        type_counts = conn.execute(
            "SELECT asset_type, COUNT(*) FROM instruments "
            "GROUP BY asset_type ORDER BY COUNT(*) DESC"
        ).fetchall()
        sector_counts = conn.execute(
            "SELECT sector, COUNT(*) FROM instruments "
            "WHERE sector IS NOT NULL "
            "GROUP BY sector ORDER BY COUNT(*) DESC LIMIT 20"
        ).fetchall()

        logger.info("\n=== INSTRUMENT TYPES ===")
        for atype, count in type_counts:
            logger.info("  %-25s %d", atype, count)

        logger.info("\n=== TOP SECTORS ===")
        for sector, count in sector_counts:
            logger.info("  %-25s %d", sector, count)

    conn.close()

    logger.info("=" * 60)
    logger.info("ENRICHMENT COMPLETE")
    logger.info("  Enriched: %d", stats["enriched"])
    logger.info("  Failed:   %d", stats["failed"])
    logger.info("  Skipped:  %d", stats["skipped"])
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Enrich ETFs with real metadata from yfinance",
    )
    parser.add_argument(
        "--db", type=Path, default=None,
        help="Path to SQLite database (default: backend/momentum_compass.db)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without writing to DB",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only process first N ETFs (for testing)",
    )
    args = parser.parse_args()

    enrich_etfs(db_path=args.db, dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
