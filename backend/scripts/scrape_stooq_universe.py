"""Scrape the complete Stooq instrument universe from their browse pages.

Since bulk ZIP downloads require authentication, this script discovers
ALL instruments by scraping Stooq's paginated browse pages (/t/?i=XXX).
It then uses the individual CSV endpoint to fetch price data.

Stooq browse page IDs:
- 510: Main Indices (66)
- 515: NYSE Stocks (paginated, ~3500)
- 516: NASDAQ Stocks (paginated, ~4300)
- 517: NYSE MKT Stocks (paginated, ~308)
- 519: Japan Stocks (paginated, ~3957)
- 521: German Stocks
- 522: Hungarian Stocks
- 523: Polish Stocks
- 524: Indices Asia
- 525: Indices Europe
- 526: Indices America
- 549: S&P US Indices
- 551: US Global and Sector ETFs
- 552: US Country ETFs
- 557: All Commodities
- 560: DAX Stocks
- 602: US Commodity ETFs
- 609: US ETFs (all, paginated ~3500)
- 610: UK Stocks (paginated)
- 611: UK100 Stocks
- 612: UK ETFs (paginated ~4200)
- 613: JP ETFs (paginated ~475)
- 614: HK Stocks (paginated)
- 615: HK ETFs (paginated ~195)
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.etf_classifier import ETFClassifier, build_instrument_entry

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Pages to scrape: (page_id, label, max_pages)
# Stooq paginates with &p=N, showing ~100 instruments per page
SCRAPE_TARGETS: list[tuple[int, str, int]] = [
    # Indices
    (510, "Main Indices", 2),
    (524, "Indices Asia", 1),
    (525, "Indices Europe", 1),
    (526, "Indices America", 1),
    (527, "Indices Futures", 1),
    (528, "WSE Indices", 1),
    (549, "S&P US Indices", 1),
    # ETFs — these are the big ones
    (551, "US Global/Sector ETFs", 1),
    (552, "US Country ETFs", 1),
    (602, "US Commodity ETFs", 1),
    (609, "US ETFs ALL", 40),  # ~3500 ETFs, ~100/page
    (612, "UK ETFs ALL", 45),  # ~4200 ETFs
    (613, "JP ETFs ALL", 6),   # ~475 ETFs
    (615, "HK ETFs ALL", 3),   # ~195 ETFs
    (587, "UK Country ETFs USD", 1),
    (603, "UK Country ETFs GBP", 1),
    (604, "UK Commodity ETFs USD", 1),
    (605, "UK Commodity ETFs GBP", 1),
    (606, "PL ETFs", 1),
    (607, "UK Global/Sector ETFs USD", 1),
    # Stocks — the huge sets
    (515, "NYSE Stocks", 40),
    (516, "NASDAQ Stocks", 50),
    (517, "NYSE MKT Stocks", 4),
    (519, "Japan Stocks", 45),
    (521, "German Stocks", 10),
    (522, "Hungarian Stocks", 2),
    (523, "Polish Stocks", 10),
    (610, "UK Stocks", 60),
    (614, "HK Stocks", 35),
    # Commodities, Bonds, Currencies
    (557, "All Commodities", 5),
    (511, "All Currencies", 20),
    (534, "Cryptocurrencies", 2),
    (536, "10Y Bond Yields", 1),
    (541, "Govt Bond Prices", 1),
    (597, "Govt Bond Yields", 2),
]

# For a quick run (just ETFs + indices), use this subset
QUICK_TARGETS: list[tuple[int, str, int]] = [
    (510, "Main Indices", 2),
    (524, "Indices Asia", 1),
    (525, "Indices Europe", 1),
    (526, "Indices America", 1),
    (549, "S&P US Indices", 1),
    (551, "US Global/Sector ETFs", 1),
    (552, "US Country ETFs", 1),
    (602, "US Commodity ETFs", 1),
    (609, "US ETFs ALL", 40),
    (612, "UK ETFs ALL", 45),
    (613, "JP ETFs ALL", 6),
    (615, "HK ETFs ALL", 3),
    (606, "PL ETFs", 1),
    (557, "All Commodities", 5),
    (534, "Cryptocurrencies", 2),
    (536, "10Y Bond Yields", 1),
]


async def scrape_page(
    client: httpx.AsyncClient,
    page_id: int,
    page_num: int = 1,
) -> list[dict[str, str]]:
    """Scrape a single Stooq browse page for tickers and names.

    Args:
        client: HTTP client.
        page_id: Stooq page ID (the i= parameter).
        page_num: Page number for pagination.

    Returns:
        List of {ticker, name} dicts.
    """
    url = f"https://stooq.com/t/?i={page_id}&v=0&l={page_num}"
    try:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch page %d p%d: %s", page_id, page_num, exc)
        return []

    # Extract ticker→name pairs from the HTML
    # Stooq format: <a href=q/?s=ewa.us>EWA.US</a></b></td><td id=f10 align=left>AUSTRALIA</td>
    # Note: no quotes around the href value in Stooq's HTML
    results: list[dict[str, str]] = []

    # Pattern: ticker link followed by name cell
    # href=q/?s=TICKER>DISPLAY</a> ... <td ...>NAME</td>
    row_pattern = re.compile(
        r'href=q/\?s=([a-zA-Z0-9._^]+)>[^<]*</a>'
        r'.*?<td[^>]*>([^<]+)</td>',
        re.DOTALL
    )

    # Find all table rows with id=r_N pattern (instrument rows)
    row_blocks = re.findall(r'<tr id=r_\d+>(.*?)</tr>', html, re.DOTALL)

    if row_blocks:
        for block in row_blocks:
            match = row_pattern.search(block)
            if match:
                ticker = match.group(1).strip()
                name = match.group(2).strip()
                results.append({"ticker": ticker, "name": name})
    else:
        # Fallback: just extract all ticker links
        ticker_pattern = re.compile(r'href=q/\?s=([a-zA-Z0-9._^]+)')
        tickers = ticker_pattern.findall(html)
        # Deduplicate while preserving order
        seen: set[str] = set()
        for t in tickers:
            if t not in seen:
                seen.add(t)
                results.append({"ticker": t.strip(), "name": ""})

    return results


async def scrape_all_pages(
    page_id: int,
    label: str,
    max_pages: int,
    client: httpx.AsyncClient,
) -> list[dict[str, str]]:
    """Scrape all pages of a paginated Stooq listing.

    Args:
        page_id: Stooq page ID.
        label: Human-readable label for logging.
        max_pages: Maximum number of pages to scrape.
        client: HTTP client.

    Returns:
        Combined list of {ticker, name} dicts from all pages.
    """
    all_results: list[dict[str, str]] = []
    seen_tickers: set[str] = set()

    for page_num in range(1, max_pages + 1):
        results = await scrape_page(client, page_id, page_num)

        # Deduplicate
        new_results = []
        for r in results:
            if r["ticker"] not in seen_tickers:
                seen_tickers.add(r["ticker"])
                new_results.append(r)

        all_results.extend(new_results)

        # If we got fewer than expected, we've reached the last page
        if len(results) < 10:
            break

        # Rate limit
        await asyncio.sleep(0.3)

    logger.info("  %s (i=%d): %d instruments across %d pages",
                label, page_id, len(all_results), min(page_num, max_pages))
    return all_results


async def discover_stooq_universe(
    quick: bool = False,
    output_path: Path | None = None,
) -> list[dict]:
    """Discover the complete Stooq instrument universe by scraping browse pages.

    Args:
        quick: If True, only scrape ETFs and indices (skip stocks).
        output_path: Where to write the discovered tickers JSON.

    Returns:
        List of instrument_map entries for all discovered instruments.
    """
    targets = QUICK_TARGETS if quick else SCRAPE_TARGETS
    classifier = ETFClassifier()
    all_discovered: list[dict[str, str]] = []
    seen_tickers: set[str] = set()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": "MomentumCompass/1.0"},
        follow_redirects=True,
    ) as client:
        for page_id, label, max_pages in targets:
            results = await scrape_all_pages(page_id, label, max_pages, client)
            for r in results:
                if r["ticker"] not in seen_tickers:
                    seen_tickers.add(r["ticker"])
                    all_discovered.append(r)

    logger.info("Total unique tickers discovered: %d", len(all_discovered))

    # Classify each discovered instrument
    entries: list[dict] = []
    for item in all_discovered:
        ticker = item["ticker"]
        name = item["name"]

        # Determine if it's an index
        if ticker.startswith("^"):
            classification = classifier.classify_index(ticker)
        else:
            classification = classifier.classify(ticker, name)

        entry = build_instrument_entry(ticker, name or ticker, classification, source="stooq")
        entries.append(entry)

    # Deduplicate by ID
    seen_ids: dict[str, dict] = {}
    for e in entries:
        if e["id"] not in seen_ids:
            seen_ids[e["id"]] = e
    entries = list(seen_ids.values())

    # Stats
    by_type: dict[str, int] = {}
    for e in entries:
        t = e.get("asset_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    logger.info("=" * 60)
    logger.info("Discovered %d unique instruments", len(entries))
    logger.info("By type:")
    for t, c in sorted(by_type.items()):
        logger.info("  %-25s %6d", t, c)
    logger.info("=" * 60)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(entries, f, indent=2)
        logger.info("Wrote to %s", output_path)

    return entries


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Discover ALL instruments from Stooq browse pages"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: ETFs + indices only (skip stocks)"
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).parent.parent / "data" / "instrument_map.json",
        help="Output path for instrument_map.json"
    )
    parser.add_argument(
        "--merge-yfinance", action="store_true", default=True,
        help="Merge with yfinance gap-fill instruments"
    )

    args = parser.parse_args()

    entries = asyncio.run(discover_stooq_universe(
        quick=args.quick,
        output_path=None,  # Don't write yet
    ))

    if args.merge_yfinance:
        # Load yfinance instruments from generate script
        from scripts.generate_instrument_map import YFINANCE_INSTRUMENTS
        seen_ids = {e["id"] for e in entries}
        for yf_inst in YFINANCE_INSTRUMENTS:
            entry = {
                "id": yf_inst["id"],
                "name": yf_inst["name"],
                "ticker_stooq": None,
                "ticker_yfinance": yf_inst["ticker_yfinance"],
                "source": "yfinance",
                "asset_type": yf_inst["asset_type"],
                "country": yf_inst.get("country"),
                "sector": yf_inst.get("sector"),
                "hierarchy_level": yf_inst["hierarchy_level"],
                "benchmark_id": yf_inst.get("benchmark_id"),
                "currency": yf_inst["currency"],
                "liquidity_tier": yf_inst.get("liquidity_tier", 2),
            }
            if entry["id"] not in seen_ids:
                entries.append(entry)
                seen_ids.add(entry["id"])

    # Sort and write
    type_order = {
        "benchmark": 0, "country_index": 1, "country_etf": 2,
        "regional_etf": 3, "global_sector_etf": 4, "sector_index": 5,
        "sector_etf": 6, "etf": 7, "etf_unclassified": 8,
        "stock": 9, "bond_etf": 10, "bond": 11,
        "commodity_etf": 12, "commodity": 13,
        "currency_pair": 14, "crypto": 15, "macro_indicator": 16,
    }

    entries.sort(key=lambda e: (
        type_order.get(e.get("asset_type", ""), 99),
        e.get("hierarchy_level", 99),
        e.get("country") or "ZZZ",
        e.get("id", ""),
    ))

    with open(args.output, "w") as f:
        json.dump(entries, f, indent=2)
    logger.info("Final: %d instruments written to %s", len(entries), args.output)
