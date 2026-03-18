"""Unified data ingestion CLI for Momentum Compass.

Orchestrates all data pipeline operations:
  1. generate-map   — Build instrument_map.json from classifier knowledge base
  2. fetch          — Fetch real OHLCV data from Stooq + yfinance
  3. load           — Load fetched CSVs into database
  4. seed-sample    — Generate sample data for development (no network needed)
  5. scrape         — Discover instruments from Stooq browse pages
  6. full           — Run the complete pipeline: generate-map → fetch → load → RS

Usage:
    python -m scripts.ingest_data generate-map
    python -m scripts.ingest_data fetch --source all --days 730
    python -m scripts.ingest_data load
    python -m scripts.ingest_data seed-sample --days 180
    python -m scripts.ingest_data full
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Ensure backend root is on sys.path
_backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)

MAP_FILE = _backend_root / "data" / "instrument_map.json"
FETCH_DIR = _backend_root / "data" / "fetched"


def cmd_generate_map(args: argparse.Namespace) -> None:
    """Generate instrument_map.json from the ETF classifier knowledge base."""
    from scripts.generate_instrument_map import generate
    generate()
    logger.info("Done. instrument_map.json regenerated.")


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch real OHLCV data from Stooq CSV endpoint + yfinance."""
    import httpx

    os.makedirs(FETCH_DIR, exist_ok=True)

    with open(MAP_FILE) as f:
        instruments = json.load(f)

    source_filter = args.source
    if source_filter != "all":
        instruments = [i for i in instruments if i["source"] == source_filter]

    today = date.today()
    start = today - timedelta(days=args.days)
    start_str = start.strftime("%Y%m%d")
    end_str = today.strftime("%Y%m%d")

    yf_instruments = [i for i in instruments if i["source"] == "yfinance"]
    stooq_instruments = [i for i in instruments if i["source"] == "stooq"]

    logger.info(
        "Fetching %d instruments (%d stooq, %d yfinance), %d days",
        len(instruments), len(stooq_instruments), len(yf_instruments), args.days,
    )

    ok_count = 0
    fail_count = 0
    skip_count = 0

    # yfinance instruments first (more reliable)
    if yf_instruments:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed, skipping %d yfinance instruments", len(yf_instruments))
            yf_instruments = []

    for inst in yf_instruments:
        ticker = inst.get("ticker_yfinance")
        if not ticker:
            skip_count += 1
            continue
        try:
            data = yf.download(ticker, period=f"{args.days}d", progress=False)
            if data.empty:
                skip_count += 1
                continue
            if hasattr(data.columns, "levels"):
                data.columns = data.columns.get_level_values(0)
            filepath = FETCH_DIR / f"{inst['id']}.csv"
            data.to_csv(filepath)
            ok_count += 1
            logger.debug("OK %s (%s): %d rows", inst["id"], ticker, len(data))
        except Exception as e:
            logger.warning("FAIL %s (%s): %s", inst["id"], ticker, e)
            fail_count += 1

    # Stooq instruments (with rate limiting)
    delay = args.delay
    for idx, inst in enumerate(stooq_instruments):
        ticker = inst.get("ticker_stooq")
        if not ticker:
            skip_count += 1
            continue

        url = f"https://stooq.com/q/d/l/?s={ticker}&d1={start_str}&d2={end_str}&i=d"
        try:
            response = httpx.get(
                url, timeout=30.0, follow_redirects=True,
                headers={"User-Agent": "MomentumCompass/1.0"},
            )
            if response.status_code == 429:
                logger.warning("Rate limited at %s, waiting 30s...", inst["id"])
                time.sleep(30)
                response = httpx.get(url, timeout=30.0, follow_redirects=True)

            if response.status_code != 200:
                # Try yfinance fallback for US-listed ETFs/indices
                yf_ok = _try_yfinance_fallback(inst, args.days)
                if yf_ok:
                    ok_count += 1
                else:
                    fail_count += 1
                continue

            content = response.text
            if "No data" in content or len(content.strip()) < 50:
                skip_count += 1
                continue

            first_line = content.strip().split("\n")[0].lower()
            if "date" not in first_line and "close" not in first_line:
                skip_count += 1
                continue

            filepath = FETCH_DIR / f"{inst['id']}.csv"
            filepath.write_text(content)
            ok_count += 1
            lines = len(content.strip().split("\n")) - 1
            logger.debug("OK %s (%s): %d rows", inst["id"], ticker, lines)

        except Exception as e:
            logger.warning("FAIL %s (%s): %s", inst["id"], ticker, e)
            # Try yfinance fallback
            yf_ok = _try_yfinance_fallback(inst, args.days)
            if yf_ok:
                ok_count += 1
            else:
                fail_count += 1

        if idx < len(stooq_instruments) - 1:
            time.sleep(delay)

        # Progress update every 50 instruments
        if (idx + 1) % 50 == 0:
            logger.info(
                "Progress: %d/%d stooq instruments (ok=%d, fail=%d, skip=%d)",
                idx + 1, len(stooq_instruments), ok_count, fail_count, skip_count,
            )

    logger.info("=" * 60)
    logger.info("FETCH COMPLETE: ok=%d, fail=%d, skip=%d, total=%d",
                ok_count, fail_count, skip_count, len(instruments))
    logger.info("Data saved to: %s", FETCH_DIR)


def _try_yfinance_fallback(inst: dict, days: int) -> bool:
    """Try fetching from yfinance as fallback for Stooq failures."""
    try:
        import yfinance as yf
    except ImportError:
        return False

    ticker = inst.get("ticker_stooq", "")
    asset_type = inst.get("asset_type", "")

    # Only attempt fallback for US-listed instruments
    if asset_type not in (
        "country_etf", "sector_etf", "global_sector_etf",
        "benchmark", "regional_etf", "bond_etf", "commodity_etf",
        "country_index",
    ):
        return False

    # Convert Stooq ticker to yfinance format
    if ticker.startswith("^"):
        yf_ticker = ticker  # indices use same format
    elif ticker.endswith(".US"):
        yf_ticker = ticker[:-3]  # strip .US suffix
    else:
        return False

    try:
        data = yf.download(yf_ticker, period=f"{days}d", progress=False)
        if data.empty:
            return False
        if hasattr(data.columns, "levels"):
            data.columns = data.columns.get_level_values(0)
        filepath = FETCH_DIR / f"{inst['id']}.csv"
        data.to_csv(filepath)
        logger.info("  -> yfinance fallback OK for %s (%s)", inst["id"], yf_ticker)
        return True
    except Exception:
        return False


def cmd_load(args: argparse.Namespace) -> None:
    """Load fetched CSVs into the database."""
    asyncio.run(_async_load(args))


async def _async_load(args: argparse.Namespace) -> None:
    """Load all fetched CSV data into the database."""
    from scripts.load_fetched_data import load_all_fetched
    from scripts.load_data_to_db import load_to_db

    logger.info("Loading fetched data from %s", FETCH_DIR)
    results = load_all_fetched()

    if not results:
        logger.warning("No data to load. Run 'fetch' first.")
        return

    logger.info("Loading %d instruments into database...", len(results))
    await load_to_db(results)


def cmd_seed_sample(args: argparse.Namespace) -> None:
    """Generate sample data and seed the database (no network needed)."""
    asyncio.run(_async_seed_sample(args))


async def _async_seed_sample(args: argparse.Namespace) -> None:
    """Seed DB with sample data for development."""
    # First regenerate instrument_map if it's stale
    if not MAP_FILE.exists():
        from scripts.generate_instrument_map import generate
        generate()

    from scripts.seed_db import main as seed_main
    await seed_main()


def cmd_scrape(args: argparse.Namespace) -> None:
    """Discover instruments from Stooq browse pages."""
    asyncio.run(_async_scrape(args))


async def _async_scrape(args: argparse.Namespace) -> None:
    """Run the Stooq universe scraper."""
    from scripts.scrape_stooq_universe import discover_stooq_universe

    output_path = Path(args.output) if args.output else MAP_FILE
    entries = await discover_stooq_universe(
        quick=args.quick,
        output_path=output_path,
    )
    logger.info("Discovered %d instruments", len(entries))


def cmd_full(args: argparse.Namespace) -> None:
    """Run the complete pipeline: generate-map -> fetch -> seed-db."""
    logger.info("=" * 60)
    logger.info("FULL PIPELINE START")
    logger.info("=" * 60)

    # Step 1: Generate instrument map
    logger.info("\n--- Step 1: Generate instrument_map.json ---")
    from scripts.generate_instrument_map import generate
    generate()

    # Step 2: Fetch data
    logger.info("\n--- Step 2: Fetch OHLCV data ---")
    fetch_args = argparse.Namespace(
        source="all", days=args.days, delay=args.delay,
    )
    cmd_fetch(fetch_args)

    # Step 3: Seed database (with real or sample data)
    logger.info("\n--- Step 3: Seed database ---")
    asyncio.run(_async_seed_with_fetched_or_sample())

    logger.info("=" * 60)
    logger.info("FULL PIPELINE COMPLETE")
    logger.info("=" * 60)


async def _async_seed_with_fetched_or_sample() -> None:
    """Seed the DB, using fetched data if available, else sample data."""
    csv_files = list(FETCH_DIR.glob("*.csv")) if FETCH_DIR.exists() else []

    if len(csv_files) > 10:
        logger.info("Found %d fetched CSVs, loading real data...", len(csv_files))
        from scripts.load_data_to_db import load_to_db
        from scripts.load_fetched_data import load_all_fetched

        results = load_all_fetched()
        if results:
            await load_to_db(results)
            return

    logger.info("Not enough fetched data, using sample data...")
    from scripts.seed_db import main as seed_main
    await seed_main()


def cmd_status(args: argparse.Namespace) -> None:
    """Show current data status."""
    # Instrument map
    if MAP_FILE.exists():
        with open(MAP_FILE) as f:
            instruments = json.load(f)

        by_source: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for inst in instruments:
            s = inst["source"]
            by_source[s] = by_source.get(s, 0) + 1
            t = inst.get("asset_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        print(f"\ninstrument_map.json: {len(instruments)} instruments")
        print(f"  By source:")
        for s, c in sorted(by_source.items()):
            print(f"    {s:15s} {c:6d}")
        print(f"  By type:")
        for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"    {t:25s} {c:6d}")
    else:
        print("\ninstrument_map.json: NOT FOUND")

    # Fetched data
    if FETCH_DIR.exists():
        csv_files = list(FETCH_DIR.glob("*.csv"))
        print(f"\nFetched data: {len(csv_files)} CSV files in {FETCH_DIR}")
    else:
        print(f"\nFetched data: directory not found ({FETCH_DIR})")

    # Database
    try:
        from config import get_settings
        settings = get_settings()
        print(f"\nDatabase: {settings.DATABASE_URL[:50]}...")
    except Exception:
        print("\nDatabase: not configured (set DATABASE_URL)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Momentum Compass Data Ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  generate-map    Build instrument_map.json from classifier knowledge base
  fetch           Fetch real OHLCV data from Stooq + yfinance
  load            Load fetched CSVs into the database
  seed-sample     Generate sample data and seed database (offline)
  scrape          Discover instruments from Stooq browse pages
  full            Run complete pipeline: generate-map -> fetch -> load
  status          Show current data pipeline status

Examples:
  python -m scripts.ingest_data generate-map
  python -m scripts.ingest_data fetch --source stooq --days 365 --delay 2
  python -m scripts.ingest_data seed-sample
  python -m scripts.ingest_data full --days 730
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # generate-map
    subparsers.add_parser("generate-map", help="Generate instrument_map.json")

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch OHLCV data")
    fetch_parser.add_argument(
        "--source", choices=["all", "stooq", "yfinance"], default="all",
        help="Data source to fetch from (default: all)",
    )
    fetch_parser.add_argument(
        "--days", type=int, default=730,
        help="Number of days of history to fetch (default: 730)",
    )
    fetch_parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Delay between Stooq requests in seconds (default: 2.0)",
    )

    # load
    subparsers.add_parser("load", help="Load fetched data into database")

    # seed-sample
    seed_parser = subparsers.add_parser(
        "seed-sample", help="Seed database with sample data (offline)",
    )
    seed_parser.add_argument(
        "--days", type=int, default=180,
        help="Days of sample data to generate (default: 180)",
    )

    # scrape
    scrape_parser = subparsers.add_parser(
        "scrape", help="Discover instruments from Stooq browse pages",
    )
    scrape_parser.add_argument(
        "--quick", action="store_true",
        help="Quick mode: ETFs + indices only (skip stocks)",
    )
    scrape_parser.add_argument(
        "--output", type=str, default=None,
        help="Output path (default: data/instrument_map.json)",
    )

    # full
    full_parser = subparsers.add_parser(
        "full", help="Run complete pipeline",
    )
    full_parser.add_argument(
        "--days", type=int, default=730,
        help="Days of history to fetch (default: 730)",
    )
    full_parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Delay between Stooq requests (default: 2.0)",
    )

    # status
    subparsers.add_parser("status", help="Show data pipeline status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "generate-map": cmd_generate_map,
        "fetch": cmd_fetch,
        "load": cmd_load,
        "seed-sample": cmd_seed_sample,
        "scrape": cmd_scrape,
        "full": cmd_full,
        "status": cmd_status,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
