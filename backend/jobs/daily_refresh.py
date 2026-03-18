"""Daily data refresh job — orchestrates fetchers and RS engine."""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

_INSTRUMENT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "instrument_map.json"
_FETCHED_DIR = Path(__file__).resolve().parent.parent / "data" / "fetched"


def _load_instrument_map() -> list[dict]:
    """Load the canonical instrument mapping."""
    try:
        with open(_INSTRUMENT_MAP_PATH, "r", encoding="utf-8") as f:
            instruments: list[dict] = json.load(f)
        logger.info("Loaded %d instruments from map", len(instruments))
        return instruments
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("Failed to load instrument_map.json: %s", exc)
        return []


async def run_stooq_daily_refresh() -> None:
    """Fetch latest daily prices from Stooq for all mapped instruments."""
    start_time = datetime.now(timezone.utc)
    logger.info("Starting Stooq daily refresh at %s", start_time.isoformat())

    instruments = _load_instrument_map()
    stooq_instruments = [i for i in instruments if i.get("source") == "stooq"]
    logger.info("Found %d Stooq instruments to fetch", len(stooq_instruments))

    if not stooq_instruments:
        return

    output_dir = _FETCHED_DIR / "stooq"
    output_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    fail_count = 0

    try:
        from data.stooq_fetcher import StooqFetcher
        fetcher = StooqFetcher()
        today = date.today()

        for instrument in stooq_instruments:
            ticker = instrument.get("ticker_stooq")
            if not ticker:
                continue
            try:
                df = await fetcher.fetch_ohlcv(ticker, today, today)
                if df.is_empty():
                    continue
                out_path = output_dir / f"{instrument['id']}.csv"
                df.write_csv(out_path)
                success_count += 1
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", instrument["id"], exc)
                fail_count += 1
    except ImportError as exc:
        logger.error("Could not import StooqFetcher: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("Stooq refresh done in %.1fs — ok=%d, fail=%d", elapsed, success_count, fail_count)


async def run_yfinance_gap_fill() -> None:
    """Fetch latest prices from yfinance for gap-fill markets."""
    start_time = datetime.now(timezone.utc)
    logger.info("Starting yfinance gap-fill at %s", start_time.isoformat())

    instruments = _load_instrument_map()
    yf_instruments = [i for i in instruments if i.get("source") == "yfinance"]
    logger.info("Found %d yfinance instruments to fetch", len(yf_instruments))

    if not yf_instruments:
        return

    output_dir = _FETCHED_DIR / "yfinance"
    output_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    fail_count = 0

    try:
        from data.yfinance_fetcher import YFinanceFetcher
        fetcher = YFinanceFetcher()

        for instrument in yf_instruments:
            ticker = instrument.get("ticker_yfinance")
            if not ticker:
                continue
            try:
                df = await fetcher.fetch_ohlcv_async(ticker, period="5d")
                if df.is_empty():
                    continue
                out_path = output_dir / f"{instrument['id']}.csv"
                df.write_csv(out_path)
                success_count += 1
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", instrument["id"], exc)
                fail_count += 1
    except ImportError as exc:
        logger.error("Could not import YFinanceFetcher: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("yfinance gap-fill done in %.1fs — ok=%d, fail=%d", elapsed, success_count, fail_count)


async def run_stooq_bulk_download() -> None:
    """Weekly full Stooq bulk download."""
    logger.info("Starting Stooq bulk download")
    try:
        from data.stooq_fetcher import StooqFetcher
        fetcher = StooqFetcher()
        await fetcher.bulk_download()
        logger.info("Stooq bulk download complete")
    except Exception as exc:
        logger.error("Stooq bulk download failed: %s", exc)


async def run_rs_computation() -> None:
    """Run RS engine computation for all active instruments.

    Uses the v1 RS engine (compute_rs_scores) which writes to PostgreSQL
    via SQLAlchemy async sessions.
    """
    start_time = datetime.now(timezone.utc)
    logger.info("Starting RS computation at %s", start_time.isoformat())

    try:
        from scripts.compute_rs_scores import compute_all
        from db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            count = await compute_all(session)
        logger.info("RS computation done: %d instruments scored", count)
    except Exception as exc:
        logger.error("RS computation failed: %s", exc)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("RS computation completed in %.1fs", elapsed)


async def run_opportunity_scan() -> None:
    """Run opportunity scanner on latest RS scores."""
    logger.info("Starting opportunity scan")
    try:
        from engine.opportunity_scanner import OpportunityScanner
        from db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            scanner = OpportunityScanner()
            count = await scanner.scan(session)
            logger.info("Opportunity scan complete: %d signals generated", count)
    except Exception as exc:
        logger.error("Opportunity scan failed: %s", exc)


async def run_daily_refresh() -> None:
    """Full daily refresh pipeline."""
    logger.info("Starting full daily refresh pipeline")

    try:
        await run_stooq_daily_refresh()
    except Exception as exc:
        logger.error("Stooq daily refresh failed: %s", exc)

    try:
        await run_yfinance_gap_fill()
    except Exception as exc:
        logger.error("yfinance gap-fill failed: %s", exc)

    try:
        await run_rs_computation()
    except Exception as exc:
        logger.error("RS computation failed: %s", exc)

    logger.info("Full daily refresh pipeline complete")
