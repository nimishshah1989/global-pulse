"""Enrich unclassified ETFs using yfinance metadata.

Uses yfinance's `category` field to map ETFs to country/sector/type.
Processes in batches with rate limiting.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── yfinance category → our classification mapping ──────────────────────
# Categories from Morningstar via yfinance
CATEGORY_MAP: dict[str, dict] = {
    # US Equity
    "Large Blend": {"country": "US", "asset_type": "etf"},
    "Large Growth": {"country": "US", "asset_type": "etf"},
    "Large Value": {"country": "US", "asset_type": "etf"},
    "Mid-Cap Blend": {"country": "US", "asset_type": "etf"},
    "Mid-Cap Growth": {"country": "US", "asset_type": "etf"},
    "Mid-Cap Value": {"country": "US", "asset_type": "etf"},
    "Small Blend": {"country": "US", "asset_type": "etf"},
    "Small Growth": {"country": "US", "asset_type": "etf"},
    "Small Value": {"country": "US", "asset_type": "etf"},
    # Foreign Equity
    "Foreign Large Blend": {"region": "INTL", "asset_type": "regional_etf"},
    "Foreign Large Growth": {"region": "INTL", "asset_type": "regional_etf"},
    "Foreign Large Value": {"region": "INTL", "asset_type": "regional_etf"},
    "Foreign Small/Mid Blend": {"region": "INTL", "asset_type": "regional_etf"},
    "Foreign Small/Mid Growth": {"region": "INTL", "asset_type": "regional_etf"},
    "Foreign Small/Mid Value": {"region": "INTL", "asset_type": "regional_etf"},
    # Diversified EM
    "Diversified Emerging Mkts": {"region": "EM", "asset_type": "regional_etf"},
    "Diversified Emerging Markets": {"region": "EM", "asset_type": "regional_etf"},
    # Regional
    "Europe Stock": {"region": "EU", "asset_type": "regional_etf"},
    "Pacific/Asia ex-Japan Stk": {"region": "APAC", "asset_type": "regional_etf"},
    "Japan Stock": {"country": "JP", "asset_type": "country_etf"},
    "China Region": {"country": "CN", "asset_type": "country_etf"},
    "India Equity": {"country": "IN", "asset_type": "country_etf"},
    "Latin America Stock": {"region": "LATAM", "asset_type": "regional_etf"},
    # Sector - US
    "Technology": {"country": "US", "sector": "technology", "asset_type": "sector_etf"},
    "Health": {"country": "US", "sector": "healthcare", "asset_type": "sector_etf"},
    "Financial": {"country": "US", "sector": "financials", "asset_type": "sector_etf"},
    "Communications": {"country": "US", "sector": "communication_services", "asset_type": "sector_etf"},
    "Consumer Cyclical": {"country": "US", "sector": "consumer_discretionary", "asset_type": "sector_etf"},
    "Consumer Defensive": {"country": "US", "sector": "consumer_staples", "asset_type": "sector_etf"},
    "Energy": {"country": "US", "sector": "energy", "asset_type": "sector_etf"},
    "Industrials": {"country": "US", "sector": "industrials", "asset_type": "sector_etf"},
    "Basic Materials": {"country": "US", "sector": "materials", "asset_type": "sector_etf"},
    "Real Estate": {"country": "US", "sector": "real_estate", "asset_type": "sector_etf"},
    "Utilities": {"country": "US", "sector": "utilities", "asset_type": "sector_etf"},
    "Natural Resources": {"country": "US", "sector": "materials", "asset_type": "sector_etf"},
    # Sector - Global
    "Global Real Estate": {"region": "GLOBAL", "sector": "real_estate", "asset_type": "global_sector_etf"},
    # Fixed Income
    "Long-Term Bond": {"asset_type": "bond_etf"},
    "Intermediate-Term Bond": {"asset_type": "bond_etf"},
    "Short-Term Bond": {"asset_type": "bond_etf"},
    "Ultrashort Bond": {"asset_type": "bond_etf"},
    "Long Government": {"asset_type": "bond_etf"},
    "Intermediate Government": {"asset_type": "bond_etf"},
    "Short Government": {"asset_type": "bond_etf"},
    "Corporate Bond": {"asset_type": "bond_etf"},
    "Intermediate Core Bond": {"asset_type": "bond_etf"},
    "Intermediate Core-Plus Bond": {"asset_type": "bond_etf"},
    "High Yield Bond": {"asset_type": "bond_etf"},
    "Multisector Bond": {"asset_type": "bond_etf"},
    "World Bond": {"asset_type": "bond_etf"},
    "Emerging Markets Bond": {"asset_type": "bond_etf"},
    "Muni National Interm": {"asset_type": "bond_etf"},
    "Muni National Short": {"asset_type": "bond_etf"},
    "Muni National Long": {"asset_type": "bond_etf"},
    "Muni California Long": {"asset_type": "bond_etf"},
    "Muni California Intermediate": {"asset_type": "bond_etf"},
    "Muni New York Long": {"asset_type": "bond_etf"},
    "Muni New York Intermediate": {"asset_type": "bond_etf"},
    "Muni Single State Long": {"asset_type": "bond_etf"},
    "Muni Single State Interm": {"asset_type": "bond_etf"},
    "Muni Single State Short": {"asset_type": "bond_etf"},
    "Inflation-Protected Bond": {"asset_type": "bond_etf"},
    "Bank Loan": {"asset_type": "bond_etf"},
    "Nontraditional Bond": {"asset_type": "bond_etf"},
    "Preferred Stock": {"asset_type": "bond_etf"},
    "Target-Date Retirement": {"asset_type": "bond_etf"},
    "Target Maturity": {"asset_type": "bond_etf"},
    # Alternatives
    "Commodities Broad Basket": {"asset_type": "commodity_etf"},
    "Commodities Focused": {"asset_type": "commodity_etf"},
    "Equity Precious Metals": {"asset_type": "commodity_etf"},
    # Options/Income
    "Derivative Income": {"country": "US", "asset_type": "etf"},
    "Options Trading": {"country": "US", "asset_type": "etf"},
    # Multi-Asset
    "Allocation--15% to 30% Equity": {"asset_type": "etf"},
    "Allocation--30% to 50% Equity": {"asset_type": "etf"},
    "Allocation--50% to 70% Equity": {"asset_type": "etf"},
    "Allocation--70% to 85% Equity": {"asset_type": "etf"},
    "Allocation--85%+ Equity": {"asset_type": "etf"},
    "World Allocation": {"region": "GLOBAL", "asset_type": "regional_etf"},
    "Tactical Allocation": {"asset_type": "etf"},
    # Trading
    "Trading--Leveraged Equity": {"country": "US", "asset_type": "etf", "is_leveraged": True},
    "Trading--Inverse Equity": {"country": "US", "asset_type": "etf", "is_inverse": True},
    "Trading--Leveraged/Inverse": {"country": "US", "asset_type": "etf", "is_leveraged": True},
    "Trading--Leveraged Commodities": {"asset_type": "commodity_etf", "is_leveraged": True},
    "Trading--Miscellaneous": {"asset_type": "etf"},
    # Digital Assets
    "Digital Assets": {"asset_type": "crypto"},
}


def enrich_unclassified(
    instrument_map_path: Path,
    batch_size: int = 20,
    delay: float = 0.5,
) -> int:
    """Enrich unclassified ETFs in instrument_map.json using yfinance.

    Args:
        instrument_map_path: Path to instrument_map.json.
        batch_size: Process this many ETFs before saving progress.
        delay: Seconds between yfinance requests.

    Returns:
        Number of ETFs enriched.
    """
    import yfinance as yf

    with open(instrument_map_path) as f:
        instruments = json.load(f)

    # Find ETFs that need enrichment (no country, no sector, type is generic 'etf')
    needs_enrichment = []
    for i, inst in enumerate(instruments):
        if (
            inst.get("asset_type") == "etf"
            and not inst.get("country")
            and not inst.get("sector")
            and not inst.get("region")
            and inst.get("ticker_yfinance")
        ):
            needs_enrichment.append((i, inst))

    logger.info("Found %d ETFs needing enrichment", len(needs_enrichment))

    enriched = 0
    errors = 0
    cache_path = instrument_map_path.parent / "yf_category_cache.json"

    # Load cache
    cache: dict[str, str | None] = {}
    if cache_path.exists():
        with open(cache_path) as f:
            cache = json.load(f)

    for batch_start in range(0, len(needs_enrichment), batch_size):
        batch = needs_enrichment[batch_start:batch_start + batch_size]

        for idx, inst in batch:
            ticker = inst["ticker_yfinance"]

            if ticker in cache:
                category = cache[ticker]
            else:
                try:
                    info = yf.Ticker(ticker).info
                    category = info.get("category")
                    cache[ticker] = category
                    time.sleep(delay)
                except Exception as e:
                    logger.debug("yfinance error for %s: %s", ticker, e)
                    cache[ticker] = None
                    errors += 1
                    continue

            if not category:
                continue

            # Map category to our classification
            mapping = None
            for cat_key, cat_map in CATEGORY_MAP.items():
                if category.lower() == cat_key.lower():
                    mapping = cat_map
                    break

            # Fuzzy match if exact didn't work
            if not mapping:
                cat_lower = category.lower()
                for cat_key, cat_map in CATEGORY_MAP.items():
                    if cat_key.lower() in cat_lower or cat_lower in cat_key.lower():
                        mapping = cat_map
                        break

            if mapping:
                if "country" in mapping:
                    instruments[idx]["country"] = mapping["country"]
                if "region" in mapping:
                    instruments[idx]["region"] = mapping["region"]
                if "sector" in mapping:
                    instruments[idx]["sector"] = mapping["sector"]
                if "asset_type" in mapping:
                    instruments[idx]["asset_type"] = mapping["asset_type"]
                if mapping.get("is_leveraged"):
                    instruments[idx]["is_leveraged"] = True
                if mapping.get("is_inverse"):
                    instruments[idx]["is_inverse"] = True

                # Set benchmark
                country = instruments[idx].get("country")
                if country == "US":
                    instruments[idx]["benchmark_id"] = "SPX"
                elif country:
                    from data.etf_classifier import COUNTRY_BENCHMARKS
                    instruments[idx]["benchmark_id"] = COUNTRY_BENCHMARKS.get(
                        country, "ACWI"
                    )
                else:
                    instruments[idx]["benchmark_id"] = "ACWI"

                enriched += 1
            else:
                logger.debug(
                    "Unknown category for %s: %s", ticker, category
                )

        # Save progress periodically
        if (batch_start + batch_size) % (batch_size * 5) == 0:
            with open(instrument_map_path, "w") as f:
                json.dump(instruments, f, indent=2)
            with open(cache_path, "w") as f:
                json.dump(cache, f, indent=2)
            logger.info(
                "Progress: %d/%d processed, %d enriched, %d errors",
                min(batch_start + batch_size, len(needs_enrichment)),
                len(needs_enrichment),
                enriched,
                errors,
            )

    # Final save
    with open(instrument_map_path, "w") as f:
        json.dump(instruments, f, indent=2)
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)

    logger.info("=" * 60)
    logger.info("Enrichment complete: %d enriched, %d errors out of %d",
                enriched, errors, len(needs_enrichment))
    logger.info("=" * 60)

    # Show updated stats
    by_type: dict[str, int] = {}
    by_country: dict[str, int] = {}
    still_unclassified = 0
    for inst in instruments:
        t = inst.get("asset_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        c = inst.get("country") or inst.get("region") or "unassigned"
        by_country[c] = by_country.get(c, 0) + 1
        if t == "etf" and not inst.get("country") and not inst.get("sector"):
            still_unclassified += 1

    logger.info("Updated breakdown by type:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        logger.info("  %-25s %6d", t, c)
    logger.info("Updated breakdown by country (top 15):")
    for cc, c in sorted(by_country.items(), key=lambda x: -x[1])[:15]:
        logger.info("  %-10s %6d", cc, c)
    logger.info("Still unclassified: %d", still_unclassified)

    return enriched


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Enrich ETFs with yfinance metadata"
    )
    parser.add_argument(
        "--map", type=Path,
        default=_backend_root / "data" / "instrument_map.json",
        help="Path to instrument_map.json",
    )
    parser.add_argument(
        "--batch-size", type=int, default=20,
    )
    parser.add_argument(
        "--delay", type=float, default=0.4,
    )

    args = parser.parse_args()
    enrich_unclassified(args.map, args.batch_size, args.delay)
