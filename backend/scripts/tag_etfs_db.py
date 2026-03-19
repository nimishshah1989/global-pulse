#!/usr/bin/env python3
"""Tag untagged ETFs in the SQLite database with sector metadata.

Reads instruments table, classifies untagged ETFs using:
1. etf_classifier.py (KNOWN_ETFS exact match + name heuristic)
2. tag_etfs.py regex rules (deeper name analysis)
Updates sector column directly in the database.

Does NOT modify any RS scores, benchmarks, or action logic.
"""
from __future__ import annotations

import sqlite3
import sys
from collections import Counter
from pathlib import Path

# Add backend to path so we can import the classifiers
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from data.etf_classifier import ETFClassifier
from scripts.tag_etfs import classify_name as classify_name_regex

DB_PATH = BACKEND_DIR / "momentum_compass.db"

# Standard sector groupings for the filter dropdown
# Sub-sectors roll up to parent for display but keep their specific tag in DB
SECTOR_DISPLAY_GROUPS: dict[str, str] = {
    # Gold group
    "gold": "gold",
    "gold_miners": "gold",
    "gold_miners_jr": "gold",
    # Silver group
    "silver": "silver",
    "silver_miners": "silver",
    # Oil group
    "crude_oil": "crude_oil",
    "oil_gas_exploration": "crude_oil",
    "oil_services": "crude_oil",
    "natural_gas": "natural_gas",
    # Energy group (non-oil)
    "energy": "energy",
    "clean_energy": "energy",
    "solar": "energy",
    "wind_energy": "energy",
    "mlp_midstream": "energy",
    # Commodity broad
    "commodities_broad": "commodities_broad",
    "agriculture": "commodities_broad",
    "metals_broad": "commodities_broad",
    "platinum": "commodities_broad",
    "palladium": "commodities_broad",
    "copper_miners": "commodities_broad",
    "uranium": "commodities_broad",
    "lithium_battery": "commodities_broad",
    "rare_earth": "commodities_broad",
    "wheat": "commodities_broad",
    "corn": "commodities_broad",
    "soybeans": "commodities_broad",
    "coffee": "commodities_broad",
    "cocoa": "commodities_broad",
    "cotton": "commodities_broad",
    "sugar": "commodities_broad",
    "livestock": "commodities_broad",
    "timber": "commodities_broad",
    "carbon": "commodities_broad",
    "gasoline": "commodities_broad",
    "water": "commodities_broad",
    # Fixed income group
    "fixed_income": "fixed_income",
    "aggregate_bond": "fixed_income",
    "treasury_short": "fixed_income",
    "treasury_mid": "fixed_income",
    "treasury_long": "fixed_income",
    "treasury_ultrashort": "fixed_income",
    "treasury_strips": "fixed_income",
    "tips": "fixed_income",
    "floating_rate": "fixed_income",
    "high_yield": "fixed_income",
    "investment_grade": "fixed_income",
    "municipal": "fixed_income",
    "mortgage_backed": "fixed_income",
    "em_bond": "fixed_income",
    "intl_bond": "fixed_income",
    "intl_treasury": "fixed_income",
    "short_corp": "fixed_income",
    "intermediate_corp": "fixed_income",
    "long_corp": "fixed_income",
    "corporate_bond": "fixed_income",
    "convertible_bond": "fixed_income",
    "preferred_stock": "fixed_income",
    "target_date_bond": "fixed_income",
    "fixed_income_other": "fixed_income",
    "clo": "fixed_income",
    "short_duration_bond": "fixed_income",
    "long_duration_bond": "fixed_income",
    "credit": "fixed_income",
    "money_market": "fixed_income",
    "bank_loans": "fixed_income",
    # Crypto
    "crypto": "crypto",
    "bitcoin": "crypto",
    "ethereum": "crypto",
    "solana": "crypto",
    "dogecoin": "crypto",
    "xrp": "crypto",
    "sui": "crypto",
    "hbar": "crypto",
    "chainlink": "crypto",
    "blockchain": "crypto",
}


def main() -> None:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    # Fetch all instruments with NULL sector
    rows = db.execute("""
        SELECT id, name, ticker_stooq, asset_type, country
        FROM instruments
        WHERE sector IS NULL
    """).fetchall()

    print(f"Found {len(rows)} instruments with NULL sector")

    classifier = ETFClassifier()
    tagged = 0
    still_untagged = 0
    sector_counts: Counter[str] = Counter()
    updates: list[tuple[str, str]] = []  # (sector, instrument_id)

    for row in rows:
        iid = row["id"]
        name = row["name"] or ""
        ticker = row["ticker_stooq"] or ""
        asset_type = row["asset_type"] or ""

        sector: str | None = None

        # Method 1: ETF classifier (exact match + name heuristic)
        if ticker:
            classification = classifier.classify(ticker, name)
            if classification.sector:
                sector = classification.sector

        # Method 2: Regex-based name classification (deeper patterns)
        if not sector and name:
            sector = classify_name_regex(name)

        # Method 3: Asset-type based fallback
        if not sector:
            if asset_type == "bond_etf":
                sector = "fixed_income"
            elif asset_type == "commodity_etf":
                sector = "commodities_broad"
            elif asset_type in ("country_etf", "regional_etf"):
                sector = "broad_market"
            elif asset_type == "etf":
                sector = "broad_market"

        if sector:
            updates.append((sector, iid))
            sector_counts[sector] += 1
            tagged += 1
        else:
            still_untagged += 1
            if still_untagged <= 20:
                print(f"  UNTAGGED: {iid:25s} | {name[:60]:60s} | {asset_type}")

    # Apply all updates in a single transaction
    print(f"\nApplying {len(updates)} sector updates...")
    db.executemany("UPDATE instruments SET sector = ? WHERE id = ?", updates)
    db.commit()

    print(f"\n=== RESULTS ===")
    print(f"Tagged:         {tagged}")
    print(f"Still untagged: {still_untagged}")

    print(f"\nSector assignment breakdown:")
    for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1]):
        display_group = SECTOR_DISPLAY_GROUPS.get(sector, sector)
        print(f"  {sector:35s} → {display_group:20s} ({count})")

    # Verify: count sectors in DB after update
    print(f"\n=== POST-UPDATE SECTOR DISTRIBUTION ===")
    result = db.execute("""
        SELECT sector, COUNT(*) as cnt
        FROM instruments
        WHERE sector IS NOT NULL
        GROUP BY sector
        ORDER BY cnt DESC
        LIMIT 40
    """).fetchall()
    for s, c in result:
        print(f"  {s:35s} {c:5d}")

    remaining_null = db.execute(
        "SELECT COUNT(*) FROM instruments WHERE sector IS NULL"
    ).fetchone()[0]
    print(f"\nRemaining NULL sector: {remaining_null}")

    db.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
