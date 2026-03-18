"""Classify the full US ETF universe into country/sector/asset_type.

Uses yfinance metadata + name-based heuristics to determine:
- Country exposure (which country does this ETF track?)
- Sector exposure (which GICS sector?)
- Asset type (country_etf, sector_etf, bond_etf, commodity_etf, etc.)
- Listing country (always US for NYSE/NASDAQ-listed)

This script processes the raw ETF list from NASDAQ API and produces
classified entries ready for instrument_map.json.
"""

import json
import logging
import re
import sys
import time
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

from data.etf_classifier import ETFClassifier, ETFClassification, build_instrument_entry

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Name-based country patterns ─────────────────────────────────────────
# Maps keywords in ETF names to ISO country codes
COUNTRY_KEYWORDS: dict[str, str] = {
    "japan": "JP", "japanese": "JP", "nikkei": "JP", "topix": "JP",
    "china": "CN", "chinese": "CN", "csi 300": "CN", "ftse china": "CN",
    "hong kong": "HK", "hang seng": "HK",
    "india": "IN", "indian": "IN", "nifty": "IN",
    "korea": "KR", "korean": "KR", "kospi": "KR",
    "taiwan": "TW", "taiwanese": "TW",
    "australia": "AU", "australian": "AU", "asx": "AU",
    "brazil": "BR", "brazilian": "BR", "ibovespa": "BR",
    "canada": "CA", "canadian": "CA", "tsx": "CA",
    "germany": "DE", "german": "DE", "dax": "DE",
    "france": "FR", "french": "FR", "cac": "FR",
    "united kingdom": "UK", "u.k.": "UK", "ftse 100": "UK", "british": "UK",
    "mexico": "MX", "mexican": "MX",
    "singapore": "SG",
    "spain": "ES", "spanish": "ES", "ibex": "ES",
    "italy": "IT", "italian": "IT",
    "netherlands": "NL", "dutch": "NL",
    "sweden": "SE", "swedish": "SE",
    "switzerland": "CH", "swiss": "CH",
    "israel": "IL", "israeli": "IL",
    "south africa": "ZA",
    "indonesia": "ID", "indonesian": "ID",
    "malaysia": "MY", "malaysian": "MY",
    "philippines": "PH", "philippine": "PH",
    "thailand": "TH", "thai": "TH",
    "vietnam": "VN", "vietnamese": "VN",
    "chile": "CL", "chilean": "CL",
    "colombia": "CO", "colombian": "CO",
    "peru": "PE", "peruvian": "PE",
    "argentina": "AR", "argentine": "AR",
    "turkey": "TR", "turkish": "TR",
    "saudi": "SA", "saudi arabia": "SA",
    "qatar": "QA",
    "uae": "AE", "emirates": "AE",
    "nigeria": "NG", "nigerian": "NG",
    "egypt": "EG", "egyptian": "EG",
    "poland": "PL", "polish": "PL",
    "greece": "GR", "greek": "GR",
    "denmark": "DK", "danish": "DK",
    "norway": "NO", "norwegian": "NO",
    "finland": "FI", "finnish": "FI",
    "ireland": "IE", "irish": "IE",
    "new zealand": "NZ",
    "austria": "AT", "austrian": "AT",
    "belgium": "BE", "belgian": "BE",
    "czech": "CZ",
    "romania": "RO", "romanian": "RO",
    "pakistan": "PK", "pakistani": "PK",
    "hungary": "HU", "hungarian": "HU",
    "russia": "RU", "russian": "RU",
    "portugal": "PT", "portuguese": "PT",
    "europe": "EU", "european": "EU", "eurozone": "EU", "euro stoxx": "EU",
}

# Regional keywords (not single country)
REGION_KEYWORDS: dict[str, str] = {
    "emerging market": "EM",
    "frontier market": "FM",
    "developed market": "DM",
    "asia pacific": "APAC",
    "asia": "APAC",
    "latin america": "LATAM",
    "africa": "AF",
    "middle east": "ME",
    "global": "GLOBAL",
    "world": "GLOBAL",
    "international": "INTL",
    "ex-us": "INTL",
    "ex-u.s.": "INTL",
    "eafe": "INTL",
    "acwi": "GLOBAL",
    "all country": "GLOBAL",
    "bric": "EM",
}

# ── Sector keywords ─────────────────────────────────────────────────────
SECTOR_KEYWORDS: dict[str, str] = {
    "technology": "technology", "tech": "technology", "semiconductor": "technology",
    "software": "technology", "cloud": "technology", "cyber": "technology",
    "internet": "technology", "digital": "technology", "ai ": "technology",
    "artificial intelligence": "technology", "robotics": "technology",
    "fintech": "technology",
    "financial": "financials", "finance": "financials", "bank": "financials",
    "insurance": "financials",
    "healthcare": "healthcare", "health care": "healthcare", "biotech": "healthcare",
    "pharma": "healthcare", "genomic": "healthcare", "medical": "healthcare",
    "consumer discretionary": "consumer_discretionary", "retail": "consumer_discretionary",
    "consumer staple": "consumer_staples", "food": "consumer_staples",
    "energy": "energy", "oil": "energy", "natural gas": "energy",
    "clean energy": "energy", "solar": "energy", "renewable": "energy",
    "industrial": "industrials", "aerospace": "industrials", "defense": "industrials",
    "infrastructure": "industrials", "transport": "industrials",
    "material": "materials", "mining": "materials", "metal": "materials",
    "steel": "materials", "lithium": "materials", "timber": "materials",
    "real estate": "real_estate", "reit": "real_estate", "mortgage": "real_estate",
    "homebuilder": "real_estate",
    "utilities": "utilities", "utility": "utilities", "water": "utilities",
    "communication": "communication_services", "media": "communication_services",
    "telecom": "communication_services",
}

# ── Asset type keywords ──────────────────────────────────────────────────
BOND_KEYWORDS = [
    "bond", "treasury", "fixed income", "aggregate", "corporate",
    "high yield", "investment grade", "municipal", "muni",
    "tips", "inflation", "floating rate", "short-term", "long-term",
    "intermediate", "credit", "debt", "income",
]

COMMODITY_KEYWORDS = [
    "gold", "silver", "platinum", "palladium", "commodity",
    "oil", "natural gas", "agriculture", "wheat", "corn",
    "copper", "uranium", "metal", "mining",
]

CRYPTO_KEYWORDS = [
    "bitcoin", "ethereum", "crypto", "blockchain", "digital asset",
]

LEVERAGED_PATTERNS = [
    r"\b[23]x\b", r"\bultra\b", r"\bproshares\b.*\b(short|ultra)\b",
    r"\bdirexion\b", r"\bleveraged\b", r"\binverse\b",
    r"\bbear\b.*\b(etf|fund)\b", r"\bbull\b.*\b(etf|fund)\b",
]


def classify_by_name(symbol: str, name: str) -> dict:
    """Classify an ETF based on its name and symbol.

    Returns a dict with keys: country, sector, asset_type, region,
    is_leveraged, is_inverse, hierarchy_level, listing_country.
    """
    name_lower = name.lower()
    result = {
        "country": None,
        "sector": None,
        "asset_type": "etf",
        "region": None,
        "is_leveraged": False,
        "is_inverse": False,
        "hierarchy_level": 2,
        "listing_country": "US",
    }

    # Check leveraged/inverse
    for pattern in LEVERAGED_PATTERNS:
        if re.search(pattern, name_lower):
            result["is_leveraged"] = True
            break

    if any(kw in name_lower for kw in ["inverse", "short", "bear", "ultra short"]):
        if "short-term" not in name_lower and "short term" not in name_lower:
            result["is_inverse"] = True

    # Check crypto
    if any(kw in name_lower for kw in CRYPTO_KEYWORDS):
        result["asset_type"] = "crypto"
        return result

    # Check bonds
    if any(kw in name_lower for kw in BOND_KEYWORDS):
        result["asset_type"] = "bond_etf"
        # Check if country-specific bond
        for kw, cc in COUNTRY_KEYWORDS.items():
            if kw in name_lower:
                result["country"] = cc
                break
        return result

    # Check commodities
    if any(kw in name_lower for kw in COMMODITY_KEYWORDS):
        # But not if it's clearly a mining stock ETF
        if any(kw in name_lower for kw in ["miner", "mining companies"]):
            result["asset_type"] = "sector_etf"
            result["sector"] = "materials"
        else:
            result["asset_type"] = "commodity_etf"
        return result

    # Check country exposure
    for kw, cc in COUNTRY_KEYWORDS.items():
        if kw in name_lower:
            result["country"] = cc
            if cc == "EU":
                result["asset_type"] = "regional_etf"
                result["region"] = "EU"
            else:
                result["asset_type"] = "country_etf"
            break

    # Check regional
    if not result["country"]:
        for kw, region in REGION_KEYWORDS.items():
            if kw in name_lower:
                result["region"] = region
                result["asset_type"] = "regional_etf"
                break

    # Check sector
    for kw, sector in SECTOR_KEYWORDS.items():
        if kw in name_lower:
            result["sector"] = sector
            if result["country"]:
                result["asset_type"] = "sector_etf"
            elif result["region"]:
                result["asset_type"] = "global_sector_etf"
            else:
                result["asset_type"] = "sector_etf"
                # Default to US if sector ETF with no country
                if not result["country"] and not result["region"]:
                    result["country"] = "US"
            break

    # If still no classification, check for broad US equity patterns
    us_broad_patterns = [
        "s&p 500", "s&p500", "nasdaq", "dow jones", "russell",
        "total stock", "total market", "large cap", "mid cap",
        "small cap", "large-cap", "mid-cap", "small-cap",
        "value", "growth", "dividend", "equal weight",
        "momentum", "quality", "volatility", "fundamental",
    ]
    if result["asset_type"] == "etf":
        for pattern in us_broad_patterns:
            if pattern in name_lower:
                result["country"] = "US"
                result["asset_type"] = "etf"
                break

    return result


def classify_etf_universe(
    input_path: Path,
    output_path: Path,
    use_yfinance: bool = False,
    batch_size: int = 50,
) -> list[dict]:
    """Classify all ETFs in the raw universe file.

    Args:
        input_path: Path to us_etf_universe_raw.json.
        output_path: Path to write classified output.
        use_yfinance: If True, also fetch metadata from yfinance (slow).
        batch_size: How many yfinance lookups per batch.

    Returns:
        List of classified instrument entries.
    """
    with open(input_path) as f:
        raw_etfs = json.load(f)

    logger.info("Classifying %d ETFs...", len(raw_etfs))

    # First pass: name-based classification
    classifier = ETFClassifier()
    entries = []
    unclassified = []

    for etf in raw_etfs:
        symbol = etf["symbol"]
        name = etf["name"]

        # Try the existing classifier first (has hand-curated data)
        stooq_ticker = f"{symbol}.US"
        classification = classifier.classify(stooq_ticker, name)

        if classification.confidence in ("exact", "pattern"):
            entry = build_instrument_entry(
                stooq_ticker, name, classification, source="stooq"
            )
            # Always add listing_country for US-listed
            entry["listing_country"] = "US"
            entry["ticker_yfinance"] = symbol
            entries.append(entry)
        else:
            # Use our enhanced name-based classifier
            result = classify_by_name(symbol, name)

            entry = {
                "id": f"{symbol}_US",
                "name": name,
                "ticker_stooq": stooq_ticker,
                "ticker_yfinance": symbol,
                "source": "stooq",
                "asset_type": result["asset_type"],
                "country": result["country"],
                "sector": result["sector"],
                "hierarchy_level": result["hierarchy_level"],
                "benchmark_id": None,
                "currency": "USD",
                "liquidity_tier": 2,
                "listing_country": "US",
            }

            if result["region"]:
                entry["region"] = result["region"]
            if result["is_leveraged"]:
                entry["is_leveraged"] = True
            if result["is_inverse"]:
                entry["is_inverse"] = True

            # Set benchmark based on classification
            if result["country"] and result["country"] not in ("EU",):
                from data.etf_classifier import COUNTRY_BENCHMARKS
                entry["benchmark_id"] = COUNTRY_BENCHMARKS.get(
                    result["country"], "ACWI"
                )
            elif result["region"] or result["asset_type"] == "regional_etf":
                entry["benchmark_id"] = "ACWI"
            elif result["country"] == "US" and result["sector"]:
                entry["benchmark_id"] = "SPX"
            else:
                entry["benchmark_id"] = "ACWI"

            entries.append(entry)

            if result["asset_type"] == "etf" and not result["country"] and not result["sector"]:
                unclassified.append({"symbol": symbol, "name": name})

    # Stats
    by_type: dict[str, int] = {}
    by_country: dict[str, int] = {}
    for e in entries:
        t = e.get("asset_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        c = e.get("country") or e.get("region") or "unassigned"
        by_country[c] = by_country.get(c, 0) + 1

    logger.info("=" * 60)
    logger.info("Classification Results: %d ETFs", len(entries))
    logger.info("By asset type:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        logger.info("  %-25s %6d", t, c)
    logger.info("By country/region (top 20):")
    for cc, c in sorted(by_country.items(), key=lambda x: -x[1])[:20]:
        logger.info("  %-10s %6d", cc, c)
    logger.info("Unclassified: %d", len(unclassified))
    logger.info("=" * 60)

    # Write output
    with open(output_path, "w") as f:
        json.dump(entries, f, indent=2)
    logger.info("Wrote %d entries to %s", len(entries), output_path)

    # Write unclassified for review
    if unclassified:
        unclass_path = output_path.parent / "etf_unclassified.json"
        with open(unclass_path, "w") as f:
            json.dump(unclassified, f, indent=2)
        logger.info("Wrote %d unclassified to %s", len(unclassified), unclass_path)

    return entries


def merge_with_existing(
    classified_path: Path,
    existing_map_path: Path,
    output_path: Path,
) -> list[dict]:
    """Merge classified ETFs with existing instrument_map.json.

    Existing entries take priority (they may have hand-curated data).
    New entries are added with appropriate deduplication.
    """
    with open(classified_path) as f:
        new_entries = json.load(f)
    with open(existing_map_path) as f:
        existing = json.load(f)

    # Index existing by ID
    existing_ids = {e["id"]: e for e in existing}
    added = 0

    for entry in new_entries:
        eid = entry["id"]
        if eid not in existing_ids:
            existing_ids[eid] = entry
            added += 1

    merged = list(existing_ids.values())

    # Sort by type, hierarchy, country, id
    type_order = {
        "benchmark": 0, "country_index": 1, "country_etf": 2,
        "regional_etf": 3, "global_sector_etf": 4, "sector_index": 5,
        "sector_etf": 6, "etf": 7, "etf_unclassified": 8,
        "stock": 9, "bond_etf": 10, "bond": 11,
        "commodity_etf": 12, "commodity": 13,
        "currency_pair": 14, "crypto": 15, "macro_indicator": 16,
    }

    merged.sort(key=lambda e: (
        type_order.get(e.get("asset_type", ""), 99),
        e.get("hierarchy_level", 99),
        e.get("country") or "ZZZ",
        e.get("id", ""),
    ))

    with open(output_path, "w") as f:
        json.dump(merged, f, indent=2)

    logger.info(
        "Merged: %d existing + %d new = %d total → %s",
        len(existing), added, len(merged), output_path,
    )
    return merged


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Classify US ETF universe into country/sector/type"
    )
    parser.add_argument(
        "--input", type=Path,
        default=_backend_root / "data" / "us_etf_universe_raw.json",
        help="Raw ETF list from NASDAQ API",
    )
    parser.add_argument(
        "--output", type=Path,
        default=_backend_root / "data" / "us_etf_classified.json",
        help="Classified ETF output",
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Also merge with existing instrument_map.json",
    )
    parser.add_argument(
        "--use-yfinance", action="store_true",
        help="Fetch metadata from yfinance (slow, ~1 req/sec)",
    )

    args = parser.parse_args()

    entries = classify_etf_universe(
        input_path=args.input,
        output_path=args.output,
        use_yfinance=args.use_yfinance,
    )

    if args.merge:
        merge_with_existing(
            classified_path=args.output,
            existing_map_path=_backend_root / "data" / "instrument_map.json",
            output_path=_backend_root / "data" / "instrument_map.json",
        )
