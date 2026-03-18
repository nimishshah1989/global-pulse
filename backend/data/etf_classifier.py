"""ETF Classifier — maps any ETF/index ticker to country, sector, asset class.

This is the intelligence layer that understands what an ETF represents.
Given a Stooq ticker, it determines:
- country exposure (which country/region does this ETF track?)
- sector (which GICS sector, if any?)
- asset_class (equity, fixed_income, commodity, currency, multi_asset)
- asset_type for instrument_map (country_etf, sector_etf, global_sector_etf, etc.)
- hierarchy_level (1=country/benchmark, 2=sector)
- benchmark_id (what should this be measured against?)
- liquidity_tier (1=high, 2=medium, 3=low)

Classification priority:
1. Exact ticker match in KNOWN_ETFS (hand-curated, highest confidence)
2. ETF family pattern match (iShares MSCI country pattern, SPDR sector, etc.)
3. Name-based heuristic (keyword matching on ETF name)
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ETFClassification:
    """Result of classifying an ETF."""

    country: str | None  # ISO 2-letter or None for global
    sector: str | None  # GICS sector slug or None
    asset_class: str  # equity, fixed_income, commodity, currency, multi_asset
    asset_type: str  # country_etf, sector_etf, global_sector_etf, etc.
    hierarchy_level: int  # 1 or 2
    benchmark_id: str | None  # what to measure against
    liquidity_tier: int  # 1, 2, or 3
    confidence: str  # "exact", "pattern", "heuristic", "unknown"


# ── Country code → primary index benchmark mapping ──────────────────────
COUNTRY_BENCHMARKS: dict[str, str] = {
    "US": "SPX",
    "UK": "FTM",
    "DE": "DAX",
    "FR": "CAC",
    "JP": "NKX",
    "HK": "HSI",
    "CN": "CSI300",
    "KR": "KS11",
    "IN": "NSEI",
    "TW": "TWII",
    "AU": "AXJO",
    "BR": "BVSP",
    "CA": "GSPTSE",
    # Extended countries (not in our 14 core, but ETFs exist)
    "SG": "ACWI",
    "MX": "ACWI",
    "ES": "ACWI",
    "IT": "ACWI",
    "NL": "ACWI",
    "SE": "ACWI",
    "BE": "ACWI",
    "AT": "ACWI",
    "CH": "ACWI",
    "MY": "ACWI",
    "ID": "ACWI",
    "PH": "ACWI",
    "TH": "ACWI",
    "CL": "ACWI",
    "TR": "ACWI",
    "DK": "ACWI",
    "NZ": "ACWI",
    "SA": "ACWI",
    "QA": "ACWI",
    "AE": "ACWI",
    "IL": "ACWI",
    "FI": "ACWI",
    "NO": "ACWI",
    "IE": "ACWI",
    "CO": "ACWI",
    "PE": "ACWI",
    "AR": "ACWI",
    "VN": "ACWI",
    "NG": "ACWI",
    "GR": "ACWI",
    "PL": "ACWI",
    "ZA": "ACWI",
    "CZ": "ACWI",
    "RO": "ACWI",
    "PK": "ACWI",
    "EG": "ACWI",
    "HU": "ACWI",
}

# ── Currency mapping for countries ──────────────────────────────────────
COUNTRY_CURRENCY: dict[str, str] = {
    "US": "USD", "UK": "GBP", "DE": "EUR", "FR": "EUR", "JP": "JPY",
    "HK": "HKD", "CN": "CNY", "KR": "KRW", "IN": "INR", "TW": "TWD",
    "AU": "AUD", "BR": "BRL", "CA": "CAD", "SG": "SGD", "MX": "MXN",
    "ES": "EUR", "IT": "EUR", "NL": "EUR", "SE": "SEK", "BE": "EUR",
    "AT": "EUR", "CH": "CHF", "MY": "MYR", "ID": "IDR", "PH": "PHP",
    "TH": "THB", "CL": "CLP", "TR": "TRY", "DK": "DKK", "NZ": "NZD",
    "SA": "SAR", "QA": "QAR", "AE": "AED", "IL": "ILS", "FI": "EUR",
    "NO": "NOK", "IE": "EUR", "CO": "COP", "PE": "PEN", "AR": "ARS",
    "VN": "VND", "NG": "NGN", "GR": "EUR", "PL": "PLN", "ZA": "ZAR",
    "CZ": "CZK", "RO": "RON", "PK": "PKR", "EG": "EGP",
    "HU": "HUF",
}

# ── Sector keyword patterns ────────────────────────────────────────────
# Maps keywords found in ETF names to sector slugs
_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "technology": [
        "technology", "tech", " it ", "information tech", "software",
        "internet", "cloud", "cyber", "digital",
    ],
    "financials": [
        "financial", "financials", "finance", "banking", "banks",
        "insurance", "fintech",
    ],
    "healthcare": [
        "healthcare", "health care", "medical", "biotech", "pharma",
        "genomic",
    ],
    "energy": [
        "energy", "oil", "gas", "petroleum", "natural gas", "clean energy",
        "solar", "wind energy", "renewable",
    ],
    "industrials": [
        "industrial", "industrials", "aerospace", "defense", "transport",
        "infrastructure",
    ],
    "consumer_discretionary": [
        "consumer discretionary", "consumer disc", "consumer cyclical",
        "retail", "luxury", "homebuilder", "gaming",
    ],
    "consumer_staples": [
        "consumer staples", "food", "beverage", "household",
    ],
    "materials": [
        "materials", "mining", "metals", "steel", "gold miner",
        "silver miner", "rare earth", "lithium", "copper",
    ],
    "utilities": [
        "utilities", "utility", "electric", "water",
    ],
    "real_estate": [
        "real estate", "reit", "property", "mortgage",
    ],
    "communication_services": [
        "communication", "telecom", "media", "entertainment",
    ],
    "semiconductors": [
        "semiconductor", "chip",
    ],
}

# ── KNOWN ETFS: Hand-curated exact matches (highest confidence) ─────────
# Format: ticker_without_suffix → classification dict
# These are US-listed (.US suffix on Stooq) unless noted otherwise
KNOWN_ETFS: dict[str, dict] = {
    # ── COUNTRY ETFs (iShares MSCI series) ──
    "SPY": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "QQQ": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "NDQ", "tier": 1},
    "DIA": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "IVV": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "VOO": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "VTI": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "IWM": {"country": "US", "sector": "small_cap", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWB": {"country": "US", "sector": "large_cap", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWF": {"country": "US", "sector": "growth", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWD": {"country": "US", "sector": "value", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWO": {"country": "US", "sector": "small_growth", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWN": {"country": "US", "sector": "small_value", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWS": {"country": "US", "sector": "mid_value", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IWP": {"country": "US", "sector": "mid_growth", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "MDY": {"country": "US", "sector": "mid_cap", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "SLY": {"country": "US", "sector": "small_cap", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "RSP": {"country": "US", "sector": "equal_weight", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "SCHB": {"country": "US", "sector": None, "asset_type": "country_etf", "benchmark_id": "SPX", "tier": 1},
    "SCHA": {"country": "US", "sector": "small_cap", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "SCHD": {"country": "US", "sector": "dividends", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},

    # ── iShares MSCI single-country ETFs ──
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
    # Extended countries
    "EWS": {"country": "SG", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWW": {"country": "MX", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWP": {"country": "ES", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWI": {"country": "IT", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWN": {"country": "NL", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWD": {"country": "SE", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWK": {"country": "BE", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWO": {"country": "AT", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWL": {"country": "CH", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EWM": {"country": "MY", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "EIDO": {"country": "ID", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EPHE": {"country": "PH", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "THD": {"country": "TH", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "ECH": {"country": "CL", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "TUR": {"country": "TR", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EDEN": {"country": "DK", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "ENZL": {"country": "NZ", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "KSA": {"country": "SA", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 1},
    "QAT": {"country": "QA", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "UAE": {"country": "AE", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EIS": {"country": "IL", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EFNL": {"country": "FI", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "NORW": {"country": "NO", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EIRL": {"country": "IE", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "GXG": {"country": "CO", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EPU": {"country": "PE", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "ARGT": {"country": "AR", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "VNM": {"country": "VN", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "NGE": {"country": "NG", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "GREK": {"country": "GR", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EPOL": {"country": "PL", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "EZA": {"country": "ZA", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    # Franklin FTSE single-country
    "FLAU": {"country": "AU", "sector": None, "asset_type": "country_etf", "benchmark_id": "AXJO", "tier": 2},
    "FLBR": {"country": "BR", "sector": None, "asset_type": "country_etf", "benchmark_id": "BVSP", "tier": 2},
    "FLCA": {"country": "CA", "sector": None, "asset_type": "country_etf", "benchmark_id": "GSPTSE", "tier": 2},
    "FLCH": {"country": "CN", "sector": None, "asset_type": "country_etf", "benchmark_id": "CSI300", "tier": 2},
    "FLFR": {"country": "FR", "sector": None, "asset_type": "country_etf", "benchmark_id": "CAC", "tier": 2},
    "FLGB": {"country": "UK", "sector": None, "asset_type": "country_etf", "benchmark_id": "FTM", "tier": 2},
    "FLGR": {"country": "DE", "sector": None, "asset_type": "country_etf", "benchmark_id": "DAX", "tier": 2},
    "FLHK": {"country": "HK", "sector": None, "asset_type": "country_etf", "benchmark_id": "HSI", "tier": 2},
    "FLIN": {"country": "IN", "sector": None, "asset_type": "country_etf", "benchmark_id": "NSEI", "tier": 2},
    "FLJP": {"country": "JP", "sector": None, "asset_type": "country_etf", "benchmark_id": "NKX", "tier": 2},
    "FLKR": {"country": "KR", "sector": None, "asset_type": "country_etf", "benchmark_id": "KS11", "tier": 2},
    "FLMX": {"country": "MX", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "FLSA": {"country": "SA", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "FLSG": {"country": "SG", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "FLSW": {"country": "CH", "sector": None, "asset_type": "country_etf", "benchmark_id": "ACWI", "tier": 2},
    "FLTW": {"country": "TW", "sector": None, "asset_type": "country_etf", "benchmark_id": "TWII", "tier": 2},
    # WisdomTree country
    "DXJ": {"country": "JP", "sector": None, "asset_type": "country_etf", "benchmark_id": "NKX", "tier": 1},
    "DFJ": {"country": "JP", "sector": "small_cap", "asset_type": "sector_etf", "benchmark_id": "NKX", "tier": 2},
    "HEDJ": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "DFE": {"country": None, "sector": "small_cap", "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "EPI": {"country": "IN", "sector": None, "asset_type": "country_etf", "benchmark_id": "NSEI", "tier": 1},
    "CXSE": {"country": "CN", "sector": None, "asset_type": "country_etf", "benchmark_id": "CSI300", "tier": 2},
    "PIN": {"country": "IN", "sector": None, "asset_type": "country_etf", "benchmark_id": "NSEI", "tier": 2},
    "INDY": {"country": "IN", "sector": None, "asset_type": "country_etf", "benchmark_id": "NSEI", "tier": 1},
    "SMIN": {"country": "IN", "sector": "small_cap", "asset_type": "sector_etf", "benchmark_id": "NSEI", "tier": 2},

    # ── REGIONAL ETFs ──
    "EEM": {"country": None, "sector": None, "asset_type": "benchmark", "benchmark_id": None, "tier": 1},
    "VWO": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "IEMG": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "EFA": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "VEA": {"country": None, "sector": None, "asset_type": "benchmark", "benchmark_id": None, "tier": 1},
    "ACWI": {"country": None, "sector": None, "asset_type": "benchmark", "benchmark_id": None, "tier": 1},
    "VT": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "VXUS": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "SCHF": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "SCHE": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "AAXJ": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "AIA": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "EPP": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "EZU": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "FEZ": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "VGK": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "ILF": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "EEMA": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "EMQQ": {"country": None, "sector": "technology", "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "AFK": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "FM": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "FRDM": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 2},
    "IEUR": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "IPAC": {"country": None, "sector": None, "asset_type": "regional_etf", "benchmark_id": "ACWI", "tier": 1},
    "IUSV": {"country": "US", "sector": "value", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IUSG": {"country": "US", "sector": "growth", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},

    # ── US SECTOR ETFs (SPDR) ──
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

    # ── US SECTOR ETFs (Vanguard) ──
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

    # ── US SECTOR ETFs (iShares) ──
    "IYW": {"country": "US", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYF": {"country": "US", "sector": "financials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYH": {"country": "US", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYE": {"country": "US", "sector": "energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYJ": {"country": "US", "sector": "industrials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYC": {"country": "US", "sector": "consumer_discretionary", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYK": {"country": "US", "sector": "consumer_staples", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IDU": {"country": "US", "sector": "utilities", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYM": {"country": "US", "sector": "materials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYR": {"country": "US", "sector": "real_estate", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IYZ": {"country": "US", "sector": "communication_services", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},

    # ── US SECTOR ETFs (Fidelity) ──
    "FREL": {"country": "US", "sector": "real_estate", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FENY": {"country": "US", "sector": "energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FHLC": {"country": "US", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FDIS": {"country": "US", "sector": "consumer_discretionary", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FSTA": {"country": "US", "sector": "consumer_staples", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FIDU": {"country": "US", "sector": "industrials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FMAT": {"country": "US", "sector": "materials", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FUTY": {"country": "US", "sector": "utilities", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FCOM": {"country": "US", "sector": "communication_services", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "FTEC": {"country": "US", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},

    # ── GLOBAL SECTOR ETFs (iShares) ──
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

    # ── THEMATIC / SUB-SECTOR ETFs ──
    "SOXX": {"country": "US", "sector": "semiconductors", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "SMH": {"country": "US", "sector": "semiconductors", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XSD": {"country": "US", "sector": "semiconductors", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IBB": {"country": "US", "sector": "biotech", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XBI": {"country": "US", "sector": "biotech", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "IHI": {"country": "US", "sector": "medical_devices", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XHB": {"country": "US", "sector": "homebuilders", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ITB": {"country": "US", "sector": "homebuilders", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XOP": {"country": "US", "sector": "oil_gas_exploration", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "OIH": {"country": "US", "sector": "oil_services", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "KRE": {"country": "US", "sector": "regional_banks", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "KBE": {"country": "US", "sector": "banks", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "KIE": {"country": "US", "sector": "insurance", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "XRT": {"country": "US", "sector": "retail", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ITA": {"country": "US", "sector": "aerospace_defense", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "PPA": {"country": "US", "sector": "aerospace_defense", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "XAR": {"country": "US", "sector": "aerospace_defense", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "HACK": {"country": "US", "sector": "cybersecurity", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "CIBR": {"country": "US", "sector": "cybersecurity", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "WCLD": {"country": "US", "sector": "cloud_computing", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "SKYY": {"country": "US", "sector": "cloud_computing", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "AIQ": {"country": "US", "sector": "artificial_intelligence", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "BOTZ": {"country": None, "sector": "robotics_ai", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 2},
    "ROBO": {"country": None, "sector": "robotics_ai", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 2},
    "ARKK": {"country": "US", "sector": "innovation", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ARKG": {"country": "US", "sector": "genomics", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ARKW": {"country": "US", "sector": "internet", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ARKF": {"country": "US", "sector": "fintech", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "ARKQ": {"country": "US", "sector": "autonomous_tech", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "TAN": {"country": None, "sector": "solar", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "ICLN": {"country": None, "sector": "clean_energy", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "QCLN": {"country": "US", "sector": "clean_energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "PBW": {"country": "US", "sector": "clean_energy", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "LIT": {"country": None, "sector": "lithium_battery", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 1},
    "REMX": {"country": None, "sector": "rare_earth", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 2},
    "BLOK": {"country": None, "sector": "blockchain", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 2},
    "BITO": {"country": None, "sector": "crypto", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "IBIT": {"country": None, "sector": "crypto", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "MJ": {"country": "US", "sector": "cannabis", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 2},
    "JETS": {"country": "US", "sector": "airlines", "asset_type": "sector_etf", "benchmark_id": "SPX", "tier": 1},
    "GAMR": {"country": None, "sector": "gaming", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 2},
    "ESPO": {"country": None, "sector": "esports_gaming", "asset_type": "global_sector_etf", "benchmark_id": "ACWI", "tier": 2},

    # ── CHINA SECTOR ETFs (US-listed) ──
    "KWEB": {"country": "CN", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 1},
    "CHIQ": {"country": "CN", "sector": "consumer_discretionary", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CQQQ": {"country": "CN", "sector": "technology", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "KURE": {"country": "CN", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "KGRN": {"country": "CN", "sector": "clean_energy", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CHIS": {"country": "CN", "sector": "consumer_staples", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CHIH": {"country": "CN", "sector": "healthcare", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CHII": {"country": "CN", "sector": "industrials", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CHIF": {"country": "CN", "sector": "financials", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CHIE": {"country": "CN", "sector": "energy", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CHIM": {"country": "CN", "sector": "materials", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},
    "CHIR": {"country": "CN", "sector": "real_estate", "asset_type": "sector_etf", "benchmark_id": "CSI300", "tier": 2},

    # ── COMMODITY ETFs ──
    "GLD": {"country": None, "sector": "gold", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "IAU": {"country": None, "sector": "gold", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "SLV": {"country": None, "sector": "silver", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "GDX": {"country": None, "sector": "gold_miners", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "GDXJ": {"country": None, "sector": "gold_miners_jr", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "USO": {"country": None, "sector": "crude_oil", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "UNG": {"country": None, "sector": "natural_gas", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "DBA": {"country": None, "sector": "agriculture", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "DBC": {"country": None, "sector": "commodities_broad", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "PDBC": {"country": None, "sector": "commodities_broad", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 1},
    "PPLT": {"country": None, "sector": "platinum", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},
    "PALL": {"country": None, "sector": "palladium", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},
    "COPX": {"country": None, "sector": "copper_miners", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},
    "SIL": {"country": None, "sector": "silver_miners", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},
    "URA": {"country": None, "sector": "uranium", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},
    "WEAT": {"country": None, "sector": "wheat", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},
    "CORN": {"country": None, "sector": "corn", "asset_type": "commodity_etf", "benchmark_id": None, "tier": 2},

    # ── BOND / FIXED INCOME ETFs ──
    "AGG": {"country": "US", "sector": "aggregate_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "BND": {"country": "US", "sector": "aggregate_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "TLT": {"country": "US", "sector": "treasury_long", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "IEF": {"country": "US", "sector": "treasury_mid", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "SHY": {"country": "US", "sector": "treasury_short", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "TIPS": {"country": "US", "sector": "tips", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "TIP": {"country": "US", "sector": "tips", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "LQD": {"country": "US", "sector": "investment_grade", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "HYG": {"country": "US", "sector": "high_yield", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "JNK": {"country": "US", "sector": "high_yield", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "MBB": {"country": "US", "sector": "mortgage_backed", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "VCSH": {"country": "US", "sector": "short_corp", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "VCIT": {"country": "US", "sector": "intermediate_corp", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "VGSH": {"country": "US", "sector": "treasury_short", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "VGIT": {"country": "US", "sector": "treasury_mid", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "VGLT": {"country": "US", "sector": "treasury_long", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "EMB": {"country": None, "sector": "em_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "PCY": {"country": None, "sector": "em_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "BWX": {"country": None, "sector": "intl_treasury", "asset_type": "bond_etf", "benchmark_id": None, "tier": 2},
    "BNDX": {"country": None, "sector": "intl_bond", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "IGOV": {"country": None, "sector": "intl_treasury", "asset_type": "bond_etf", "benchmark_id": None, "tier": 2},
    "IAGG": {"country": None, "sector": "intl_aggregate", "asset_type": "bond_etf", "benchmark_id": None, "tier": 2},
    "MUB": {"country": "US", "sector": "municipal", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "HYD": {"country": "US", "sector": "high_yield_muni", "asset_type": "bond_etf", "benchmark_id": None, "tier": 2},
    "SPTL": {"country": "US", "sector": "treasury_long", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "SPTI": {"country": "US", "sector": "treasury_mid", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "SPTS": {"country": "US", "sector": "treasury_short", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "FLOT": {"country": "US", "sector": "floating_rate", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "BKLN": {"country": "US", "sector": "bank_loans", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "SRLN": {"country": "US", "sector": "bank_loans", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "TMF": {"country": "US", "sector": "treasury_long_3x", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
    "TBT": {"country": "US", "sector": "treasury_short_2x", "asset_type": "bond_etf", "benchmark_id": None, "tier": 1},
}

# ── Stooq index tickers (with ^ prefix) ────────────────────────────────
KNOWN_INDICES: dict[str, dict] = {
    # US
    "^SPX": {"country": "US", "name": "S&P 500", "tier": 1},
    "^DJI": {"country": "US", "name": "Dow Jones Industrial Average", "tier": 1},
    "^NDQ": {"country": "US", "name": "NASDAQ 100", "tier": 1},
    "^RUT": {"country": "US", "name": "Russell 2000", "tier": 1},
    "^NYA": {"country": "US", "name": "NYSE Composite", "tier": 1},
    "^XAX": {"country": "US", "name": "NYSE AMEX Composite", "tier": 2},
    "^SP400": {"country": "US", "name": "S&P MidCap 400", "tier": 1},
    "^SP600": {"country": "US", "name": "S&P SmallCap 600", "tier": 1},
    "^VIX": {"country": "US", "name": "CBOE Volatility Index", "tier": 1},
    "^SOX": {"country": "US", "name": "PHLX Semiconductor", "tier": 1},
    "^DJT": {"country": "US", "name": "Dow Jones Transportation", "tier": 1},
    "^DJU": {"country": "US", "name": "Dow Jones Utilities", "tier": 1},
    "^BKX": {"country": "US", "name": "KBW Bank Index", "tier": 1},
    "^XOI": {"country": "US", "name": "NYSE Oil Index", "tier": 1},
    "^HUI": {"country": "US", "name": "NYSE Gold BUGS", "tier": 1},
    # UK
    "^FTM": {"country": "UK", "name": "FTSE 100", "tier": 1},
    "^FTMC": {"country": "UK", "name": "FTSE 250", "tier": 1},
    "^FTSC": {"country": "UK", "name": "FTSE SmallCap", "tier": 2},
    "^FTAS": {"country": "UK", "name": "FTSE All-Share", "tier": 1},
    "^FTAI": {"country": "UK", "name": "FTSE AIM All-Share", "tier": 2},
    # Germany
    "^DAX": {"country": "DE", "name": "DAX 40", "tier": 1},
    "^MDAX": {"country": "DE", "name": "MDAX", "tier": 1},
    "^SDAX": {"country": "DE", "name": "SDAX", "tier": 2},
    "^TDXP": {"country": "DE", "name": "TecDAX", "tier": 1},
    # France
    "^CAC": {"country": "FR", "name": "CAC 40", "tier": 1},
    "^SBF120": {"country": "FR", "name": "SBF 120", "tier": 1},
    # Japan
    "^NKX": {"country": "JP", "name": "Nikkei 225", "tier": 1},
    "^TOPX": {"country": "JP", "name": "TOPIX", "tier": 1},
    "^JASQ": {"country": "JP", "name": "JASDAQ", "tier": 2},
    "^MOTH": {"country": "JP", "name": "Mothers Index", "tier": 2},
    # Hong Kong
    "^HSI": {"country": "HK", "name": "Hang Seng Index", "tier": 1},
    "^HSCE": {"country": "HK", "name": "Hang Seng China Enterprises", "tier": 1},
    # Europe
    "^SX5E": {"country": None, "name": "Euro STOXX 50", "tier": 1},
    "^STOXX": {"country": None, "name": "STOXX Europe 600", "tier": 1},
    # Other
    "^AEX": {"country": "NL", "name": "AEX Index", "tier": 1},
    "^BFX": {"country": "BE", "name": "BEL 20", "tier": 1},
    "^IBEX": {"country": "ES", "name": "IBEX 35", "tier": 1},
    "^FMIB": {"country": "IT", "name": "FTSE MIB", "tier": 1},
    "^SMI": {"country": "CH", "name": "Swiss Market Index", "tier": 1},
    "^ATX": {"country": "AT", "name": "ATX", "tier": 1},
    "^OMX": {"country": "SE", "name": "OMX Stockholm 30", "tier": 1},
    "^OBX": {"country": "NO", "name": "OBX Total Return", "tier": 1},
    "^OMXH": {"country": "FI", "name": "OMX Helsinki 25", "tier": 1},
    "^OMXC": {"country": "DK", "name": "OMX Copenhagen 20", "tier": 1},
    "^ISEQ": {"country": "IE", "name": "ISEQ Overall", "tier": 2},
    "^PSI20": {"country": None, "name": "PSI 20 (Portugal)", "tier": 2},
    "^WIG20": {"country": "PL", "name": "WIG 20", "tier": 1},
    "^ATH": {"country": "GR", "name": "Athens General", "tier": 2},
    "^TA35": {"country": "IL", "name": "TA-35", "tier": 1},
    "^TASI": {"country": "SA", "name": "Tadawul All Share", "tier": 1},
    "^GNRI": {"country": "QA", "name": "QE General", "tier": 2},
    "^ADI": {"country": "AE", "name": "ADX General", "tier": 2},
    "^EGX30": {"country": "EG", "name": "EGX 30", "tier": 2},
    "^JSE": {"country": "ZA", "name": "JSE All-Share", "tier": 1},
    "^KLCI": {"country": "MY", "name": "KLCI", "tier": 1},
    "^STI": {"country": "SG", "name": "Straits Times", "tier": 1},
    "^SET": {"country": "TH", "name": "SET Index", "tier": 1},
    "^JKSE": {"country": "ID", "name": "Jakarta Composite", "tier": 1},
    "^PSEI": {"country": "PH", "name": "PSEi Composite", "tier": 1},
    "^NZX50": {"country": "NZ", "name": "NZX 50", "tier": 1},
    "^MXX": {"country": "MX", "name": "IPC Mexico", "tier": 1},
    "^BSESN": {"country": "IN", "name": "BSE Sensex", "tier": 1},
    "^COLCAP": {"country": "CO", "name": "COLCAP", "tier": 2},
    "^IPSA": {"country": "CL", "name": "IPSA", "tier": 2},
    "^MERV": {"country": "AR", "name": "MERVAL", "tier": 2},
    "^BIST100": {"country": "TR", "name": "BIST 100", "tier": 1},
    "^XU100": {"country": "TR", "name": "BIST 100", "tier": 1},
    "^PX": {"country": "CZ", "name": "PX Index", "tier": 2},
    "^BET": {"country": "RO", "name": "BET Index", "tier": 2},
    "^KSE100": {"country": "PK", "name": "KSE 100", "tier": 2},
    "^VNI": {"country": "VN", "name": "VN-Index", "tier": 1},
    # Hungary
    "^BUX": {"country": "HU", "name": "Budapest Stock Exchange Index", "tier": 1},
    # Poland (extended)
    "^WIG": {"country": "PL", "name": "WIG", "tier": 1},
    "^MWIG40": {"country": "PL", "name": "mWIG40", "tier": 2},
    "^SWIG80": {"country": "PL", "name": "sWIG80", "tier": 2},
}


class ETFClassifier:
    """Classifies ETF/index tickers into country, sector, and asset class."""

    def classify(
        self,
        ticker: str,
        name: str = "",
    ) -> ETFClassification:
        """Classify an ETF or index ticker.

        Args:
            ticker: Stooq ticker (e.g., "XLK.US", "^SPX", "EWJ.US").
            name: Optional ETF name for heuristic matching.

        Returns:
            ETFClassification with all resolved fields.
        """
        # Normalize: strip whitespace
        ticker = ticker.strip()

        # Check if it's an index (^ prefix)
        if ticker.startswith("^"):
            return self._classify_index(ticker)

        # Strip country suffix (.US, .UK, .JP, .HK)
        base_ticker, suffix = self._split_ticker(ticker)

        # 1. Exact match in KNOWN_ETFS
        if base_ticker in KNOWN_ETFS:
            return self._from_known(base_ticker, suffix)

        # 2. Name-based heuristic
        if name:
            result = self._classify_by_name(base_ticker, suffix, name)
            if result is not None:
                return result

        # 3. Unknown — still ingest it, mark as unclassified equity
        return ETFClassification(
            country=self._country_from_suffix(suffix),
            sector=None,
            asset_class="equity",
            asset_type="etf_unclassified",
            hierarchy_level=2,
            benchmark_id=COUNTRY_BENCHMARKS.get(
                self._country_from_suffix(suffix) or "", "ACWI"
            ),
            liquidity_tier=2,
            confidence="unknown",
        )

    def classify_index(self, ticker: str) -> ETFClassification:
        """Classify a Stooq index ticker."""
        return self._classify_index(ticker)

    def _classify_index(self, ticker: str) -> ETFClassification:
        """Internal: classify index by ^ prefix."""
        if ticker in KNOWN_INDICES:
            info = KNOWN_INDICES[ticker]
            country = info.get("country")
            return ETFClassification(
                country=country,
                sector=None,
                asset_class="equity",
                asset_type="country_index",
                hierarchy_level=1,
                benchmark_id="ACWI" if country else None,
                liquidity_tier=info.get("tier", 1),
                confidence="exact",
            )
        # Unknown index — still ingest
        return ETFClassification(
            country=None,
            sector=None,
            asset_class="equity",
            asset_type="country_index",
            hierarchy_level=1,
            benchmark_id="ACWI",
            liquidity_tier=2,
            confidence="unknown",
        )

    def _from_known(self, base_ticker: str, suffix: str) -> ETFClassification:
        """Build classification from KNOWN_ETFS entry."""
        info = KNOWN_ETFS[base_ticker]
        asset_type = info["asset_type"]

        # Determine asset class from asset_type
        if asset_type in ("bond_etf",):
            asset_class = "fixed_income"
        elif asset_type in ("commodity_etf",):
            asset_class = "commodity"
        else:
            asset_class = "equity"

        # Hierarchy level
        if asset_type in ("country_etf", "benchmark", "regional_etf"):
            hierarchy_level = 1
        else:
            hierarchy_level = 2

        return ETFClassification(
            country=info.get("country"),
            sector=info.get("sector"),
            asset_class=asset_class,
            asset_type=asset_type,
            hierarchy_level=hierarchy_level,
            benchmark_id=info.get("benchmark_id"),
            liquidity_tier=info.get("tier", 2),
            confidence="exact",
        )

    def _classify_by_name(
        self, base_ticker: str, suffix: str, name: str
    ) -> ETFClassification | None:
        """Attempt classification via ETF name keywords."""
        name_lower = name.lower()

        # Check for country keywords in name
        country = self._detect_country_from_name(name_lower)

        # Check for sector keywords
        sector = self._detect_sector_from_name(name_lower)

        # Check for bond keywords
        bond_keywords = [
            "bond", "treasury", "fixed income", "aggregate", "yield",
            "investment grade", "municipal", "mortgage", "floating rate",
            "loan", "credit", "debt",
        ]
        is_bond = any(kw in name_lower for kw in bond_keywords)

        # Check for commodity keywords
        commodity_keywords = [
            "gold", "silver", "oil", "commodity", "natural gas", "agriculture",
            "platinum", "palladium", "copper", "mining", "miner", "uranium",
            "wheat", "corn",
        ]
        is_commodity = any(kw in name_lower for kw in commodity_keywords)

        if is_bond:
            return ETFClassification(
                country=country,
                sector=sector or "bond",
                asset_class="fixed_income",
                asset_type="bond_etf",
                hierarchy_level=2,
                benchmark_id=None,
                liquidity_tier=2,
                confidence="heuristic",
            )

        if is_commodity:
            return ETFClassification(
                country=None,
                sector=sector or "commodity",
                asset_class="commodity",
                asset_type="commodity_etf",
                hierarchy_level=2,
                benchmark_id=None,
                liquidity_tier=2,
                confidence="heuristic",
            )

        if sector:
            # If we found a sector, it's a sector ETF
            benchmark = COUNTRY_BENCHMARKS.get(country, "ACWI") if country else "ACWI"
            asset_type = "sector_etf" if country else "global_sector_etf"
            return ETFClassification(
                country=country,
                sector=sector,
                asset_class="equity",
                asset_type=asset_type,
                hierarchy_level=2,
                benchmark_id=benchmark,
                liquidity_tier=2,
                confidence="heuristic",
            )

        if country:
            # Country but no sector → country ETF
            benchmark = COUNTRY_BENCHMARKS.get(country, "ACWI")
            return ETFClassification(
                country=country,
                sector=None,
                asset_class="equity",
                asset_type="country_etf",
                hierarchy_level=1,
                benchmark_id=benchmark,
                liquidity_tier=2,
                confidence="heuristic",
            )

        return None

    def _detect_country_from_name(self, name_lower: str) -> str | None:
        """Detect country from ETF name."""
        country_keywords: dict[str, list[str]] = {
            "US": ["united states", "u.s.", "s&p 500", "nasdaq", "dow jones", "russell"],
            "UK": ["united kingdom", "ftse", "british"],
            "DE": ["germany", "german", "dax"],
            "FR": ["france", "french", "cac"],
            "JP": ["japan", "japanese", "nikkei", "topix"],
            "HK": ["hong kong", "hang seng"],
            "CN": ["china", "chinese", "csi", "shanghai", "shenzhen"],
            "KR": ["korea", "korean", "kospi"],
            "IN": ["india", "indian", "nifty", "sensex"],
            "TW": ["taiwan", "taiwanese", "twse"],
            "AU": ["australia", "australian", "asx"],
            "BR": ["brazil", "brazilian", "ibovespa", "bovespa"],
            "CA": ["canada", "canadian", "tsx"],
            "SG": ["singapore"],
            "MX": ["mexico", "mexican"],
            "ES": ["spain", "spanish", "ibex"],
            "IT": ["italy", "italian"],
            "NL": ["netherlands", "dutch"],
            "SE": ["sweden", "swedish"],
            "CH": ["switzerland", "swiss"],
            "MY": ["malaysia", "malaysian"],
            "ID": ["indonesia", "indonesian"],
            "TH": ["thailand", "thai"],
            "PH": ["philippines", "philippine"],
            "CL": ["chile", "chilean"],
            "TR": ["turkey", "turkish"],
            "DK": ["denmark", "danish"],
            "NZ": ["new zealand"],
            "SA": ["saudi"],
            "IL": ["israel", "israeli"],
            "FI": ["finland", "finnish"],
            "NO": ["norway", "norwegian"],
            "IE": ["ireland", "irish"],
            "ZA": ["south africa"],
            "PL": ["poland", "polish"],
            "GR": ["greece", "greek"],
            "VN": ["vietnam", "vietnamese"],
            "AR": ["argentina", "argentine"],
            "CO": ["colombia", "colombian"],
            "PE": ["peru", "peruvian"],
            "EG": ["egypt", "egyptian"],
            "PK": ["pakistan"],
        }
        for code, keywords in country_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return code
        return None

    def _detect_sector_from_name(self, name_lower: str) -> str | None:
        """Detect sector from ETF name keywords."""
        for sector, keywords in _SECTOR_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return sector
        return None

    @staticmethod
    def _split_ticker(ticker: str) -> tuple[str, str]:
        """Split 'XLK.US' into ('XLK', 'US')."""
        if "." in ticker:
            parts = ticker.rsplit(".", 1)
            return parts[0], parts[1]
        return ticker, ""

    @staticmethod
    def _country_from_suffix(suffix: str) -> str | None:
        """Map Stooq suffix to country code."""
        suffix_map = {
            "US": "US",
            "UK": "UK",
            "JP": "JP",
            "HK": "HK",
            "DE": "DE",
            "FR": "FR",
        }
        return suffix_map.get(suffix.upper())


def build_instrument_entry(
    ticker: str,
    name: str,
    classification: ETFClassification,
    source: str = "stooq",
) -> dict:
    """Build an instrument_map.json entry from a classification.

    Args:
        ticker: Stooq ticker (e.g., "XLK.US", "^SPX").
        name: Human-readable name.
        classification: The ETF classification result.
        source: Data source ("stooq" or "yfinance").

    Returns:
        Dictionary matching instrument_map.json schema.
    """
    # Generate ID from ticker
    instrument_id = _ticker_to_id(ticker)

    # Determine currency
    if classification.country:
        currency = COUNTRY_CURRENCY.get(classification.country, "USD")
    else:
        currency = "USD"  # US-listed ETFs trade in USD

    # For US-listed ETFs tracking foreign markets, use USD
    if source == "stooq" and ticker.endswith(".US"):
        currency = "USD"

    return {
        "id": instrument_id,
        "name": name,
        "ticker_stooq": ticker if source == "stooq" else None,
        "ticker_yfinance": ticker if source == "yfinance" else None,
        "source": source,
        "asset_type": classification.asset_type,
        "country": classification.country,
        "sector": classification.sector,
        "hierarchy_level": classification.hierarchy_level,
        "benchmark_id": classification.benchmark_id,
        "currency": currency,
        "liquidity_tier": classification.liquidity_tier,
    }


def _ticker_to_id(ticker: str) -> str:
    """Convert a Stooq ticker to a canonical instrument ID.

    Examples:
        "XLK.US" → "XLK_US"
        "^SPX" → "SPX"
        "1615.JP" → "1615_JP"
        "EWJ.US" → "EWJ_US"
    """
    if ticker.startswith("^"):
        return ticker[1:]
    return ticker.replace(".", "_").replace(" ", "_")
