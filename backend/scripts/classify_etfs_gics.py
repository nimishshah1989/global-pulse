"""Classify all ETFs in the database into standardized GICS sectors.

Uses ETF name + ticker patterns to assign one of 11 GICS sectors.
Also enriches ETF names using yfinance where possible.

Usage:
    python backend/scripts/classify_etfs_gics.py --db-url DATABASE_URL
"""
from __future__ import annotations

import argparse
import logging
import re
import time

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 11 Standard GICS sectors + keyword patterns
# ---------------------------------------------------------------------------
GICS_SECTORS: dict[str, list[str]] = {
    "technology": [
        "tech", "software", "semiconductor", "cyber", "cloud", " ai ", "artificial intel",
        "robot", "automat", "innovat", "digital", "internet", "fintech", "blockchain",
        "computing", " data ", "5g ", "metaverse", "saas", "information tech",
        "disruptive", "nasdaq", "gaming", "esport", "video game",
    ],
    "financials": [
        "financ", "bank", "insur", "broker", "lend", "credit", "mortgage",
        "payment", "asset manage", "private equity", "capital market",
    ],
    "healthcare": [
        "health", "biotech", "pharma", "medic", "genomic", "drug", "therapeutic",
        "cannabis", "hospital", "clinical", "life science",
    ],
    "energy": [
        "energy", " oil ", "natural gas", "petrol", "solar", " wind ", "clean energy",
        "nuclear", "uranium", " mlp", "pipeline", "lng ", "crude",
        "renewable", "carbon",
    ],
    "industrials": [
        "industr", "aerospace", "defense", "defence", "transport", "logistic",
        "infrastr", "construct", "engineer", "manufactur", "machinery",
        "freight", "airline",
    ],
    "materials": [
        "material", "mining", " gold ", "silver", " metal", "steel", "copper",
        "lithium", "rare earth", "commodit", "palladium", "platinum",
        "timber", "lumber", "chemical", "aluminum", "aluminium", "nickel", "zinc",
    ],
    "consumer_discretionary": [
        "consumer disc", "retail", "luxury", "travel", "leisure", "hotel",
        "entertainment", " media ", "home build", "apparel", "fashion",
        " auto ", "electric vehicle", " ev ", "consumer cycl",
    ],
    "consumer_staples": [
        "consumer stap", " food", "beverage", "agri", "organic", "nutrition",
        "household", "grocery",
    ],
    "communication_services": [
        "communicat", "telecom", "stream", "social media", "network",
    ],
    "utilities": [
        "utilit", " water ", "electric power", "regulated utility",
        "global water",
    ],
    "real_estate": [
        "real estate", " reit", "property", "propert", "housing", "mortgage reit",
        "home equity",
    ],
}

# Known ticker → sector overrides for common ETFs
TICKER_SECTOR_OVERRIDES: dict[str, str] = {
    # US SPDR Sector ETFs
    "XLK_US": "technology", "XLF_US": "financials", "XLV_US": "healthcare",
    "XLE_US": "energy", "XLI_US": "industrials", "XLB_US": "materials",
    "XLY_US": "consumer_discretionary", "XLP_US": "consumer_staples",
    "XLC_US": "communication_services", "XLU_US": "utilities", "XLRE_US": "real_estate",
    # iShares Global Sectors
    "IXN_US": "technology", "IXG_US": "financials", "IXJ_US": "healthcare",
    "IXC_US": "energy", "EXI_US": "industrials", "MXI_US": "materials",
    "RXI_US": "consumer_discretionary", "KXI_US": "consumer_staples",
    "IXP_US": "communication_services", "JXI_US": "utilities",
    # Japan TOPIX sectors
    "1615_JP": "financials", "1613_JP": "technology", "1617_JP": "consumer_staples",
    "1619_JP": "industrials", "1621_JP": "healthcare", "1622_JP": "consumer_discretionary",
    "1623_JP": "materials", "1625_JP": "communication_services",
    "1629_JP": "industrials", "1630_JP": "materials", "1633_JP": "real_estate",
}

# Granular → GICS standardization map (for existing sector values in DB)
SECTOR_NORMALIZE: dict[str, str] = {
    "banks": "financials",
    "insurance": "financials",
    "securities": "financials",
    "other_finance": "financials",
    "regional_banks": "financials",
    "biotech": "healthcare",
    "pharma": "healthcare",
    "medical_devices": "healthcare",
    "genomics": "healthcare",
    "oil_gas_exploration": "energy",
    "oil_services": "energy",
    "clean_energy": "energy",
    "solar": "energy",
    "aerospace_defense": "industrials",
    "construction": "industrials",
    "machinery": "industrials",
    "transportation": "industrials",
    "transport_equipment": "consumer_discretionary",
    "iron_steel": "materials",
    "nonferrous_metals": "materials",
    "chemicals": "materials",
    "rare_earth": "materials",
    "lithium_battery": "materials",
    "gold": "materials",
    "crude_oil": "energy",
    "retail": "consumer_discretionary",
    "homebuilders": "consumer_discretionary",
    "airlines": "industrials",
    "gaming": "consumer_discretionary",
    "esports_gaming": "consumer_discretionary",
    "internet": "communication_services",
    "foods": "consumer_staples",
    "cannabis": "healthcare",
    "semiconductors": "technology",
    "cloud_computing": "technology",
    "cybersecurity": "technology",
    "artificial_intelligence": "technology",
    "autonomous_tech": "technology",
    "fintech": "technology",
    "blockchain": "technology",
    "robotics_ai": "technology",
    "innovation": "technology",
    "commerce": "consumer_discretionary",
    "precision_instruments": "technology",
    "services": "industrials",
    "electrical_equipment": "technology",
    "other_manufacturing": "industrials",
    "h_shares": None,  # not a sector
    "broad_market": None,
    "large_cap": None,
    "mid_cap": None,
    "small_cap": None,
    "small_growth": None,
    "small_value": None,
    "mid_growth": None,
    "mid_value": None,
    "growth": None,
    "value": None,
    "dividends": None,
    "equal_weight": None,
    "battery": "technology",
}


def classify_by_name(name: str) -> str | None:
    """Classify an instrument into a GICS sector by its name."""
    name_lower = " " + name.lower() + " "
    for sector, keywords in GICS_SECTORS.items():
        for kw in keywords:
            if kw in name_lower:
                return sector
    return None


def try_enrich_names_yfinance(cur, batch_size: int = 100) -> int:
    """Try to enrich ETF names using yfinance for unnamed instruments."""
    cur.execute(
        """SELECT id, ticker_stooq FROM instruments
           WHERE name = ticker_stooq OR name LIKE '%%_%%'
           ORDER BY id
           LIMIT %s""",
        (batch_size,),
    )
    rows = cur.fetchall()
    if not rows:
        return 0

    enriched = 0
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not available, skipping name enrichment")
        return 0

    for inst_id, ticker_stooq in rows:
        try:
            # Convert Stooq ticker to yfinance format
            yf_ticker = ticker_stooq
            if ticker_stooq and "." in ticker_stooq:
                parts = ticker_stooq.split(".")
                suffix = parts[-1].upper()
                base = ".".join(parts[:-1])
                if suffix == "UK":
                    yf_ticker = base + ".L"
                elif suffix == "JP":
                    yf_ticker = base + ".T"
                elif suffix == "HK":
                    yf_ticker = base.lstrip("0") + ".HK" if base.startswith("0") else base + ".HK"
                elif suffix == "US":
                    yf_ticker = base
            elif ticker_stooq and ticker_stooq.startswith("^"):
                yf_ticker = ticker_stooq  # indices keep ^ prefix

            info = yf.Ticker(yf_ticker).info
            long_name = info.get("longName") or info.get("shortName")
            if long_name:
                cur.execute("UPDATE instruments SET name = %s WHERE id = %s", (long_name, inst_id))
                enriched += 1
            time.sleep(0.2)  # Rate limit
        except Exception:
            continue

    return enriched


def main(db_url: str) -> None:
    """Classify all instruments in the database."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    # Step 1: Normalize existing sector values
    logger.info("Step 1: Normalizing existing granular sectors to GICS...")
    normalized = 0
    for granular, gics in SECTOR_NORMALIZE.items():
        if gics is None:
            continue
        cur.execute(
            "UPDATE instruments SET sector = %s WHERE sector = %s AND sector != %s",
            (gics, granular, gics),
        )
        count = cur.rowcount
        if count > 0:
            normalized += count
            logger.info("  %s → %s: %d instruments", granular, gics, count)
    conn.commit()
    logger.info("Normalized %d instruments with existing sectors.", normalized)

    # Step 2: Apply ticker-based overrides
    logger.info("Step 2: Applying ticker-based sector overrides...")
    overridden = 0
    for inst_id, sector in TICKER_SECTOR_OVERRIDES.items():
        cur.execute(
            "UPDATE instruments SET sector = %s WHERE id = %s",
            (sector, inst_id),
        )
        if cur.rowcount > 0:
            overridden += 1
    conn.commit()
    logger.info("Applied %d ticker overrides.", overridden)

    # Step 3: Try yfinance enrichment for unnamed ETFs (first batch)
    logger.info("Step 3: Enriching ETF names via yfinance (first 200)...")
    enriched = try_enrich_names_yfinance(cur, batch_size=200)
    conn.commit()
    logger.info("Enriched %d ETF names.", enriched)

    # Step 4: Classify unclassified ETFs by name
    logger.info("Step 4: Classifying ETFs by name keywords...")
    cur.execute(
        "SELECT id, name FROM instruments WHERE sector IS NULL AND asset_type IN ('etf', 'sector_etf', 'global_sector_etf')"
    )
    unclassified = cur.fetchall()
    classified = 0
    for inst_id, name in unclassified:
        sector = classify_by_name(name)
        if sector:
            cur.execute("UPDATE instruments SET sector = %s WHERE id = %s", (sector, inst_id))
            classified += 1
    conn.commit()
    logger.info("Classified %d ETFs by name.", classified)

    # Step 5: Summary
    logger.info("=== Classification Summary ===")
    cur.execute(
        """SELECT sector, country, COUNT(*)
           FROM instruments
           WHERE asset_type IN ('etf', 'sector_etf', 'global_sector_etf', 'country_index')
           AND sector IS NOT NULL
           GROUP BY sector, country
           ORDER BY sector, country"""
    )
    for row in cur.fetchall():
        logger.info("  %s | %s | %d", row[0], row[1] or "GLOBAL", row[2])

    cur.execute(
        """SELECT COUNT(*) FROM instruments
           WHERE asset_type IN ('etf', 'sector_etf', 'global_sector_etf')
           AND sector IS NULL"""
    )
    remaining = cur.fetchone()[0]
    logger.info("Unclassified ETFs remaining: %d", remaining)

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify ETFs into GICS sectors")
    parser.add_argument(
        "--db-url",
        default="postgresql://compass:compass_secure_2026@localhost:15433/momentum_compass",
    )
    args = parser.parse_args()
    main(args.db_url)
