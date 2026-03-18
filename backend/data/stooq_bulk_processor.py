"""Stooq Bulk Processor — discovers and ingests ALL instruments from Stooq bulk downloads.

Stooq provides complete historical databases for all regions via stooq.com/db/h/.
This processor downloads and processes EVERYTHING:
- ALL stocks (~25,000+ across US, UK, JP, HK, DE, PL, HU)
- ALL ETFs (~8,000+ including US-listed global ETFs)
- ALL indices (65+ global indices)
- ALL bonds, currencies, commodities
- Polish and Hungarian markets

Architecture:
1. Download bulk ZIP per region (or read from local disk)
2. Walk the ZIP structure to discover every instrument
3. Classify each instrument using ETFClassifier (for ETFs/indices)
4. Assign asset_type based on Stooq's folder structure
5. Generate instrument_map entries OR directly ingest OHLCV data

Usage:
    python -m data.stooq_bulk_processor --regions all --output instrument_map.json
    python -m data.stooq_bulk_processor --bulk-dir /data/stooq_bulk --discover
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import zipfile
from pathlib import Path

import httpx

from data.etf_classifier import (
    COUNTRY_BENCHMARKS,
    COUNTRY_CURRENCY,
    ETFClassifier,
    KNOWN_ETFS,
    build_instrument_entry,
)

logger = logging.getLogger(__name__)

# ── ALL Stooq bulk download regions ─────────────────────────────────────
# Structure: region → {url, instrument_type_paths, suffix}
# The path patterns map Stooq's ZIP folder structure to instrument types.

STOOQ_REGIONS: dict[str, dict] = {
    "us": {
        "url": "https://stooq.com/db/h/d_us_txt.zip",
        "paths": {
            # asset_type → list of path prefixes in the ZIP
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
        "url": "https://stooq.com/db/h/d_uk_txt.zip",
        "paths": {
            "stock": [
                "data/daily/uk/lse stocks/",
                "data/daily/uk/lse intl stocks/",
            ],
            "etf": [
                "data/daily/uk/lse etfs/",
                "data/daily/uk/lse intl etfs/",
            ],
            "index": [
                "data/daily/uk/lse indices/",
            ],
        },
        "suffix": "UK",
        "country": "UK",
        "currency": "GBP",
    },
    "jp": {
        "url": "https://stooq.com/db/h/d_jp_txt.zip",
        "paths": {
            "stock": [
                "data/daily/jp/tse stocks/",
            ],
            "etf": [
                "data/daily/jp/tse etfs/",
            ],
            "index": [
                "data/daily/jp/tse indices/",
            ],
        },
        "suffix": "JP",
        "country": "JP",
        "currency": "JPY",
    },
    "hk": {
        "url": "https://stooq.com/db/h/d_hk_txt.zip",
        "paths": {
            "stock": [
                "data/daily/hk/hkex stocks/",
            ],
            "etf": [
                "data/daily/hk/hkex etfs/",
            ],
            "index": [
                "data/daily/hk/hkex indices/",
            ],
        },
        "suffix": "HK",
        "country": "HK",
        "currency": "HKD",
    },
    "de": {
        "url": "https://stooq.com/db/h/d_de_txt.zip",
        "paths": {
            "stock": [
                "data/daily/de/xetra stocks/",
                "data/daily/de/frankfurt stocks/",
            ],
            "etf": [
                "data/daily/de/xetra etfs/",
                "data/daily/de/frankfurt etfs/",
            ],
            "index": [
                "data/daily/de/xetra indices/",
            ],
        },
        "suffix": "DE",
        "country": "DE",
        "currency": "EUR",
    },
    "hu": {
        "url": "https://stooq.com/db/h/d_hu_txt.zip",
        "paths": {
            "stock": [
                "data/daily/hu/bse stocks/",
                "data/daily/hu/budapest stocks/",
            ],
            "etf": [
                "data/daily/hu/bse etfs/",
                "data/daily/hu/budapest etfs/",
            ],
            "index": [
                "data/daily/hu/bse indices/",
                "data/daily/hu/budapest indices/",
            ],
        },
        "suffix": "HU",
        "country": "HU",
        "currency": "HUF",
    },
    "pl": {
        "url": "https://stooq.com/db/h/d_pl_txt.zip",
        "paths": {
            "stock": [
                "data/daily/pl/wse stocks/",
                "data/daily/pl/warsaw stocks/",
            ],
            "etf": [
                "data/daily/pl/wse etfs/",
                "data/daily/pl/warsaw etfs/",
            ],
            "index": [
                "data/daily/pl/wse indices/",
                "data/daily/pl/warsaw indices/",
            ],
        },
        "suffix": "PL",
        "country": "PL",
        "currency": "PLN",
    },
    "world": {
        "url": "https://stooq.com/db/h/d_world_txt.zip",
        "paths": {
            "index": [
                "data/daily/world/",
            ],
            "commodity": [
                "data/daily/world/commodities/",
            ],
            "currency": [
                "data/daily/world/currencies/",
            ],
            "bond": [
                "data/daily/world/bonds/",
            ],
            "macro": [
                "data/daily/world/macro/",
            ],
            "crypto": [
                "data/daily/world/crypto/",
            ],
        },
        "suffix": "",
        "country": None,
        "currency": "USD",
    },
}

# Asset type mapping from Stooq folder type to our schema
FOLDER_TYPE_TO_ASSET: dict[str, dict] = {
    "stock": {
        "asset_type": "stock",
        "hierarchy_level": 3,
    },
    "etf": {
        "asset_type": "etf",  # will be refined by classifier
        "hierarchy_level": 2,
    },
    "index": {
        "asset_type": "country_index",
        "hierarchy_level": 1,
    },
    "commodity": {
        "asset_type": "commodity",
        "hierarchy_level": 1,
    },
    "currency": {
        "asset_type": "currency_pair",
        "hierarchy_level": 1,
    },
    "bond": {
        "asset_type": "bond",
        "hierarchy_level": 1,
    },
    "macro": {
        "asset_type": "macro_indicator",
        "hierarchy_level": 1,
    },
    "crypto": {
        "asset_type": "crypto",
        "hierarchy_level": 1,
    },
}


class StooqBulkProcessor:
    """Processes Stooq bulk downloads to discover ALL instruments.

    This is the primary data ingestion path. It processes complete regional
    databases from Stooq and generates instrument_map entries for every
    instrument found.
    """

    def __init__(self) -> None:
        self.classifier = ETFClassifier()

    async def process_region(
        self,
        region: str,
        zip_path: Path | None = None,
        include_stocks: bool = True,
    ) -> list[dict]:
        """Process a Stooq bulk ZIP and extract all instruments.

        Args:
            region: Region key (us, uk, jp, hk, de, pl, hu, world).
            zip_path: Local path to ZIP file. If None, downloads from Stooq.
            include_stocks: If True, include individual stocks (adds ~25K instruments).

        Returns:
            List of instrument_map entries for every instrument found.
        """
        if region not in STOOQ_REGIONS:
            logger.error("Unknown region: %s. Available: %s",
                         region, list(STOOQ_REGIONS.keys()))
            return []

        config = STOOQ_REGIONS[region]
        entries: list[dict] = []

        # Get ZIP contents
        if zip_path and zip_path.exists():
            logger.info("Reading %s bulk data from: %s", region, zip_path)
            zip_bytes = zip_path.read_bytes()
        else:
            logger.info("Downloading %s bulk data from Stooq...", region)
            zip_bytes = await self._download_zip(config["url"])
            if not zip_bytes:
                return []

        # Parse ZIP
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except zipfile.BadZipFile:
            logger.error("Invalid ZIP for region %s", region)
            return []

        all_csv_files = [f for f in zf.namelist() if f.lower().endswith(".csv")]
        logger.info(
            "Region %s: %d total CSV files in ZIP", region, len(all_csv_files)
        )

        suffix = config["suffix"]
        region_country = config["country"]
        region_currency = config["currency"]

        # Process by folder type
        for folder_type, path_prefixes in config["paths"].items():
            # Skip stocks if not requested (saves processing time)
            if folder_type == "stock" and not include_stocks:
                logger.info("Skipping %s stocks (include_stocks=False)", region)
                continue

            matched_files = self._match_files(all_csv_files, path_prefixes)
            logger.info(
                "  %s/%s: %d instruments", region, folder_type, len(matched_files)
            )

            type_info = FOLDER_TYPE_TO_ASSET.get(folder_type, {})

            for csv_path in matched_files:
                ticker_base = Path(csv_path).stem.upper()

                # Build Stooq ticker
                if folder_type == "index":
                    stooq_ticker = f"^{ticker_base}"
                elif suffix:
                    stooq_ticker = f"{ticker_base}.{suffix}"
                else:
                    stooq_ticker = ticker_base

                # Build instrument entry
                entry = self._build_entry(
                    stooq_ticker=stooq_ticker,
                    ticker_base=ticker_base,
                    folder_type=folder_type,
                    type_info=type_info,
                    region_country=region_country,
                    region_currency=region_currency,
                )
                entry["_stooq_path"] = csv_path
                entry["_region"] = region
                entries.append(entry)

        zf.close()

        # Deduplicate by ID
        seen: dict[str, dict] = {}
        for e in entries:
            eid = e["id"]
            if eid not in seen:
                seen[eid] = e
        entries = list(seen.values())

        logger.info("Region %s: %d unique instruments", region, len(entries))
        return entries

    def _build_entry(
        self,
        stooq_ticker: str,
        ticker_base: str,
        folder_type: str,
        type_info: dict,
        region_country: str | None,
        region_currency: str,
    ) -> dict:
        """Build an instrument_map entry for a discovered instrument."""

        # For ETFs, use the classifier for intelligent mapping
        if folder_type == "etf":
            classification = self.classifier.classify(stooq_ticker)
            entry = build_instrument_entry(
                stooq_ticker, f"ETF: {ticker_base}",
                classification, source="stooq",
            )
            return entry

        # For indices, use classifier
        if folder_type == "index":
            classification = self.classifier.classify_index(stooq_ticker)
            entry = build_instrument_entry(
                stooq_ticker,
                classification.country or ticker_base,
                classification,
                source="stooq",
            )
            return entry

        # For stocks, commodities, bonds, currencies, etc.
        instrument_id = stooq_ticker.lstrip("^").replace(".", "_").replace(" ", "_")
        asset_type = type_info.get("asset_type", folder_type)
        hierarchy_level = type_info.get("hierarchy_level", 2)

        # Determine benchmark for stocks
        benchmark_id = None
        if folder_type == "stock" and region_country:
            benchmark_id = COUNTRY_BENCHMARKS.get(region_country, "ACWI")

        return {
            "id": instrument_id,
            "name": ticker_base,  # placeholder; enriched later
            "ticker_stooq": stooq_ticker,
            "ticker_yfinance": None,
            "source": "stooq",
            "asset_type": asset_type,
            "country": region_country,
            "sector": None,
            "hierarchy_level": hierarchy_level,
            "benchmark_id": benchmark_id,
            "currency": region_currency,
            "liquidity_tier": 2,
        }

    async def process_all_regions(
        self,
        regions: list[str] | None = None,
        bulk_dir: Path | None = None,
        include_stocks: bool = True,
    ) -> list[dict]:
        """Process all Stooq regions and return combined instrument list.

        Args:
            regions: Region keys to process. None = all regions.
            bulk_dir: Directory with pre-downloaded ZIPs.
            include_stocks: Whether to include individual stocks.

        Returns:
            Combined deduplicated list of all instruments.
        """
        if regions is None:
            regions = list(STOOQ_REGIONS.keys())

        all_entries: list[dict] = []
        for region in regions:
            zip_path = self._find_zip(bulk_dir, region) if bulk_dir else None
            entries = await self.process_region(
                region, zip_path, include_stocks=include_stocks
            )
            all_entries.extend(entries)

        # Global dedup
        seen: dict[str, dict] = {}
        for e in all_entries:
            eid = e["id"]
            if eid not in seen:
                seen[eid] = e
        result = list(seen.values())

        # Stats
        by_type: dict[str, int] = {}
        by_region: dict[str, int] = {}
        for e in result:
            t = e.get("asset_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            r = e.get("_region", "unknown")
            by_region[r] = by_region.get(r, 0) + 1

        logger.info("=" * 60)
        logger.info("TOTAL: %d instruments across %d regions", len(result), len(regions))
        logger.info("By region:")
        for r, c in sorted(by_region.items()):
            logger.info("  %-10s %6d", r, c)
        logger.info("By type:")
        for t, c in sorted(by_type.items()):
            logger.info("  %-25s %6d", t, c)
        logger.info("=" * 60)

        return result

    def merge_with_yfinance(
        self,
        stooq_entries: list[dict],
        yfinance_entries: list[dict],
    ) -> list[dict]:
        """Merge Stooq-discovered instruments with yfinance gap-fill instruments.

        Stooq entries are primary. yfinance entries fill gaps for markets
        Stooq doesn't cover (India, Korea, China A-shares, etc.).

        Args:
            stooq_entries: All entries from Stooq bulk processing.
            yfinance_entries: Gap-fill entries (India, Korea, etc.).

        Returns:
            Merged list with no duplicates.
        """
        seen_ids = {e["id"] for e in stooq_entries}
        merged = list(stooq_entries)

        for entry in yfinance_entries:
            if entry["id"] not in seen_ids:
                merged.append(entry)
                seen_ids.add(entry["id"])

        return merged

    def generate_instrument_map(
        self,
        entries: list[dict],
        output_path: Path,
    ) -> None:
        """Write instrument entries to instrument_map.json.

        Cleans internal fields and sorts for readability.
        """
        clean = []
        for entry in entries:
            e = {k: v for k, v in entry.items() if not k.startswith("_")}
            clean.append(e)

        # Sort order: benchmarks → indices → ETFs → stocks → other
        type_order = {
            "benchmark": 0, "country_index": 1, "country_etf": 2,
            "regional_etf": 3, "global_sector_etf": 4, "sector_index": 5,
            "sector_etf": 6, "etf": 7, "etf_unclassified": 8,
            "stock": 9, "bond_etf": 10, "bond": 11,
            "commodity_etf": 12, "commodity": 13,
            "currency_pair": 14, "crypto": 15, "macro_indicator": 16,
        }

        def sort_key(e: dict) -> tuple:
            return (
                type_order.get(e.get("asset_type", ""), 99),
                e.get("hierarchy_level", 99),
                e.get("country") or "ZZZ",
                e.get("id", ""),
            )

        clean.sort(key=sort_key)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2, ensure_ascii=False)

        logger.info("Wrote %d instruments to %s", len(clean), output_path)

    @staticmethod
    def _match_files(all_files: list[str], prefixes: list[str]) -> list[str]:
        """Filter files matching any of the given path prefixes."""
        result = []
        for f in all_files:
            f_lower = f.lower()
            for prefix in prefixes:
                # Flexible matching: handle slight variations in Stooq folder names
                if f_lower.startswith(prefix.lower()) and f_lower.endswith(".csv"):
                    result.append(f)
                    break
        return result

    @staticmethod
    def _find_zip(bulk_dir: Path, region: str) -> Path | None:
        """Find a bulk ZIP file for a region in the local directory."""
        patterns = [
            f"d_{region}_txt.zip",
            f"{region}_d.zip",
            f"d_{region}.zip",
            f"{region}.zip",
        ]
        for pat in patterns:
            path = bulk_dir / pat
            if path.exists():
                return path
        return None

    @staticmethod
    async def _download_zip(url: str) -> bytes | None:
        """Download a bulk ZIP file from Stooq with retries."""
        for attempt in range(1, 5):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(600.0),  # 10 min for large ZIPs
                    headers={"User-Agent": "MomentumCompass/1.0"},
                ) as client:
                    logger.info("Downloading %s (attempt %d)...", url, attempt)
                    response = await client.get(url, follow_redirects=True)
                    response.raise_for_status()
                    size_mb = len(response.content) / (1024 * 1024)
                    logger.info("Downloaded %.1f MB from %s", size_mb, url)
                    return response.content
            except httpx.HTTPError as exc:
                wait = 2 ** attempt
                logger.warning(
                    "Download failed (attempt %d): %s. Retrying in %ds...",
                    attempt, exc, wait,
                )
                await asyncio.sleep(wait)
        logger.error("Failed to download %s after 4 attempts", url)
        return None


async def discover_full_universe(
    bulk_dir: Path | None = None,
    output_path: Path | None = None,
    include_stocks: bool = True,
    regions: list[str] | None = None,
) -> list[dict]:
    """Discover the complete Stooq instrument universe.

    This is the main entry point for populating the instrument universe
    from Stooq bulk data.

    Args:
        bulk_dir: Directory with pre-downloaded Stooq ZIP files.
        output_path: Where to write instrument_map.json.
        include_stocks: Whether to include individual stocks (~25K).
        regions: Specific regions to process. None = all.

    Returns:
        Complete list of instrument entries.
    """
    processor = StooqBulkProcessor()
    entries = await processor.process_all_regions(
        regions=regions,
        bulk_dir=bulk_dir,
        include_stocks=include_stocks,
    )

    if output_path:
        processor.generate_instrument_map(entries, output_path)

    return entries


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Discover ALL instruments from Stooq bulk downloads"
    )
    parser.add_argument(
        "--bulk-dir", type=Path, default=None,
        help="Directory with downloaded Stooq ZIP files",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).parent / "instrument_map.json",
        help="Output path for instrument_map.json",
    )
    parser.add_argument(
        "--regions", type=str, default=None,
        help="Comma-separated regions (default: all). Options: us,uk,jp,hk,de,pl,hu,world",
    )
    parser.add_argument(
        "--no-stocks", action="store_true",
        help="Skip individual stocks (only ETFs, indices, etc.)",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    region_list = args.regions.split(",") if args.regions else None

    asyncio.run(
        discover_full_universe(
            bulk_dir=args.bulk_dir,
            output_path=args.output,
            include_stocks=not args.no_stocks,
            regions=region_list,
        )
    )
