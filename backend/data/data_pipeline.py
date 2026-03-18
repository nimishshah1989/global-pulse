"""Orchestrates data ingestion: instrument discovery, price fetching, and DB persistence.

Two modes of operation:
1. DAILY REFRESH: Fetch latest prices for all instruments in instrument_map.json
   via individual Stooq CSV endpoints + yfinance gap-fill.
2. BULK INGESTION: Process Stooq bulk ZIP downloads to discover ALL instruments
   and ingest historical prices for the complete universe (~25K+ instruments).

The bulk mode is primary for initial setup and weekly full refreshes.
The daily mode is for incremental updates between bulk runs.
"""

import asyncio
import io
import json
import logging
import zipfile
from datetime import date
from pathlib import Path

import polars as pl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from data.stooq_fetcher import StooqFetcher, _parse_csv_response
from data.yfinance_fetcher import YFinanceFetcher

logger = logging.getLogger(__name__)

_INSTRUMENT_MAP_PATH = Path(__file__).parent / "instrument_map.json"


class DataPipeline:
    """Orchestrates data fetching from all sources and database persistence."""

    def __init__(
        self,
        db_session: AsyncSession,
        stooq_fetcher: StooqFetcher,
        yfinance_fetcher: YFinanceFetcher,
    ) -> None:
        """Initialize the data pipeline.

        Args:
            db_session: Async SQLAlchemy session for database operations.
            stooq_fetcher: Configured Stooq fetcher instance.
            yfinance_fetcher: Configured yfinance fetcher instance.
        """
        self.db_session = db_session
        self.stooq_fetcher = stooq_fetcher
        self.yfinance_fetcher = yfinance_fetcher

    async def load_instrument_map(self) -> list[dict]:
        """Load the canonical instrument mapping from instrument_map.json.

        Returns:
            List of instrument dictionaries with all required fields.

        Raises:
            FileNotFoundError: If instrument_map.json does not exist.
            json.JSONDecodeError: If the JSON is malformed.
        """
        logger.info("Loading instrument map from %s", _INSTRUMENT_MAP_PATH)
        with open(_INSTRUMENT_MAP_PATH, "r", encoding="utf-8") as f:
            instruments: list[dict] = json.load(f)

        logger.info("Loaded %d instruments from map", len(instruments))
        return instruments

    async def seed_instruments(self, instruments: list[dict]) -> int:
        """Upsert all instruments from the mapping into the instruments table.

        Uses PostgreSQL ON CONFLICT to update existing records and insert new ones.

        Args:
            instruments: List of instrument dictionaries from instrument_map.json.

        Returns:
            Count of instruments upserted.
        """
        logger.info("Seeding %d instruments into database", len(instruments))

        upsert_sql = text("""
            INSERT INTO instruments (
                id, name, ticker_stooq, ticker_yfinance, source,
                asset_type, country, sector, hierarchy_level,
                benchmark_id, currency, liquidity_tier, is_active
            ) VALUES (
                :id, :name, :ticker_stooq, :ticker_yfinance, :source,
                :asset_type, :country, :sector, :hierarchy_level,
                :benchmark_id, :currency, :liquidity_tier, true
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                ticker_stooq = EXCLUDED.ticker_stooq,
                ticker_yfinance = EXCLUDED.ticker_yfinance,
                source = EXCLUDED.source,
                asset_type = EXCLUDED.asset_type,
                country = EXCLUDED.country,
                sector = EXCLUDED.sector,
                hierarchy_level = EXCLUDED.hierarchy_level,
                benchmark_id = EXCLUDED.benchmark_id,
                currency = EXCLUDED.currency,
                liquidity_tier = EXCLUDED.liquidity_tier
        """)

        # Insert benchmarks first (instruments with benchmark_id = null)
        # then others, to satisfy foreign key constraints.
        benchmarks = [i for i in instruments if i.get("benchmark_id") is None]
        non_benchmarks = [i for i in instruments if i.get("benchmark_id") is not None]

        count = 0
        for batch in [benchmarks, non_benchmarks]:
            for instrument in batch:
                await self.db_session.execute(upsert_sql, instrument)
                count += 1

        await self.db_session.commit()
        logger.info("Seeded %d instruments", count)
        return count

    # ── MODE 1: Daily incremental refresh ───────────────────────────────

    async def refresh_prices(
        self,
        instruments: list[dict],
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        """Fetch OHLCV data for all instruments via individual endpoints.

        Splits instruments by source (stooq vs yfinance), fetches data
        sequentially with rate limiting, then upserts.

        Args:
            instruments: List of instrument dictionaries.
            start_date: Start date for the fetch range.
            end_date: End date for the fetch range.

        Returns:
            Stats dictionary: {"fetched": N, "failed": N, "skipped": N}.
        """
        stooq_instruments = [
            i for i in instruments if i["source"] == "stooq"
        ]
        yfinance_instruments = [
            i for i in instruments if i["source"] == "yfinance"
        ]

        stats = {"fetched": 0, "failed": 0, "skipped": 0}

        # Fetch Stooq instruments (async, with rate limiting built into fetcher)
        logger.info(
            "Fetching %d Stooq instruments from %s to %s",
            len(stooq_instruments),
            start_date,
            end_date,
        )
        for instrument in stooq_instruments:
            ticker = instrument.get("ticker_stooq")
            if not ticker:
                stats["skipped"] += 1
                continue

            try:
                df = await self.stooq_fetcher.fetch_ohlcv(
                    ticker, start_date, end_date
                )
                if df.is_empty():
                    stats["skipped"] += 1
                    continue

                await self._upsert_prices(instrument["id"], df)
                stats["fetched"] += 1
            except Exception as exc:
                logger.error(
                    "Failed to fetch/store %s: %s", instrument["id"], exc
                )
                stats["failed"] += 1

        # Fetch yfinance instruments (sequential via async wrapper)
        logger.info(
            "Fetching %d yfinance instruments", len(yfinance_instruments)
        )
        for instrument in yfinance_instruments:
            ticker = instrument.get("ticker_yfinance")
            if not ticker:
                stats["skipped"] += 1
                continue

            try:
                # Compute period from date range
                days_diff = (end_date - start_date).days
                if days_diff > 365 * 2:
                    period = "3y"
                elif days_diff > 365:
                    period = "2y"
                elif days_diff > 180:
                    period = "1y"
                else:
                    period = "6mo"

                df = await self.yfinance_fetcher.fetch_ohlcv_async(
                    ticker, period=period
                )
                if df.is_empty():
                    stats["skipped"] += 1
                    continue

                # Filter to requested date range
                df = df.filter(
                    (pl.col("date") >= start_date)
                    & (pl.col("date") <= end_date)
                )

                if df.is_empty():
                    stats["skipped"] += 1
                    continue

                await self._upsert_prices(instrument["id"], df)
                stats["fetched"] += 1
            except Exception as exc:
                logger.error(
                    "Failed to fetch/store %s: %s", instrument["id"], exc
                )
                stats["failed"] += 1

        await self.db_session.commit()

        logger.info(
            "Price refresh complete: fetched=%d, failed=%d, skipped=%d",
            stats["fetched"],
            stats["failed"],
            stats["skipped"],
        )
        return stats

    # ── MODE 2: Bulk ingestion from Stooq ZIP downloads ─────────────────

    async def bulk_ingest_region(
        self,
        zip_path: Path,
        region: str,
        instruments: list[dict] | None = None,
    ) -> dict[str, int]:
        """Ingest ALL price data from a Stooq bulk ZIP for a region.

        This is MUCH faster than individual CSV fetches because:
        - Single ZIP download vs thousands of HTTP requests
        - No rate limiting needed
        - All instruments in one pass

        Args:
            zip_path: Path to the downloaded Stooq bulk ZIP.
            region: Region key (us, uk, jp, hk, de, pl, hu).
            instruments: Optional filter — if provided, only ingest these.
                         If None, ingest everything in the ZIP.

        Returns:
            Stats: {"ingested": N, "failed": N, "total_files": N}.
        """
        logger.info("Bulk ingesting region %s from %s", region, zip_path)

        stats = {"ingested": 0, "failed": 0, "total_files": 0}

        # Build lookup of instrument_id → ticker for filtering
        ticker_to_id: dict[str, str] | None = None
        if instruments:
            ticker_to_id = {}
            for inst in instruments:
                ticker = inst.get("ticker_stooq", "")
                if ticker:
                    # Normalize: strip ^ prefix, uppercase
                    normalized = ticker.lstrip("^").replace(".", "_").upper()
                    ticker_to_id[normalized] = inst["id"]

        try:
            with zipfile.ZipFile(zip_path) as zf:
                csv_files = [
                    f for f in zf.namelist() if f.lower().endswith(".csv")
                ]
                stats["total_files"] = len(csv_files)
                logger.info("Found %d CSV files in %s", len(csv_files), zip_path)

                for csv_path in csv_files:
                    ticker_base = Path(csv_path).stem.upper()

                    # Determine instrument_id
                    if ticker_to_id is not None:
                        # Filtered mode: only process mapped instruments
                        instrument_id = ticker_to_id.get(ticker_base)
                        if instrument_id is None:
                            # Try with region suffix
                            from data.stooq_bulk_processor import STOOQ_REGIONS
                            suffix = STOOQ_REGIONS.get(region, {}).get("suffix", "")
                            if suffix:
                                instrument_id = ticker_to_id.get(
                                    f"{ticker_base}_{suffix}"
                                )
                        if instrument_id is None:
                            continue
                    else:
                        # Unfiltered mode: ingest everything
                        from data.stooq_bulk_processor import STOOQ_REGIONS
                        suffix = STOOQ_REGIONS.get(region, {}).get("suffix", "")
                        if suffix:
                            instrument_id = f"{ticker_base}_{suffix}"
                        else:
                            instrument_id = ticker_base

                    try:
                        csv_bytes = zf.read(csv_path)
                        csv_text = csv_bytes.decode("utf-8")
                        df = _parse_csv_response(csv_text, ticker_base)
                        if not df.is_empty():
                            await self._upsert_prices(instrument_id, df)
                            stats["ingested"] += 1
                    except Exception as exc:
                        logger.debug(
                            "Failed to parse %s: %s", csv_path, exc
                        )
                        stats["failed"] += 1

                    # Commit in batches for performance
                    if stats["ingested"] % 500 == 0 and stats["ingested"] > 0:
                        await self.db_session.commit()
                        logger.info(
                            "Bulk ingest progress: %d/%d ingested",
                            stats["ingested"],
                            stats["total_files"],
                        )

        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file: %s", zip_path)
            return stats

        await self.db_session.commit()

        logger.info(
            "Bulk ingest %s complete: ingested=%d, failed=%d, total=%d",
            region,
            stats["ingested"],
            stats["failed"],
            stats["total_files"],
        )
        return stats

    async def bulk_ingest_all(
        self,
        bulk_dir: Path,
        instruments: list[dict] | None = None,
    ) -> dict[str, dict[str, int]]:
        """Ingest price data from all available Stooq bulk ZIPs.

        Args:
            bulk_dir: Directory containing downloaded Stooq ZIP files.
            instruments: Optional filter list. None = ingest everything.

        Returns:
            Dict mapping region → stats.
        """
        from data.stooq_bulk_processor import STOOQ_REGIONS

        all_stats: dict[str, dict[str, int]] = {}

        for region in STOOQ_REGIONS:
            # Find ZIP file for this region
            zip_path = self._find_bulk_zip(bulk_dir, region)
            if zip_path is None:
                logger.info("No ZIP found for region %s in %s, skipping", region, bulk_dir)
                continue

            # Filter instruments to this region
            region_instruments = None
            if instruments:
                suffix = STOOQ_REGIONS[region].get("suffix", "")
                region_instruments = [
                    i for i in instruments
                    if i.get("source") == "stooq"
                    and i.get("ticker_stooq", "").endswith(f".{suffix}")
                ]
                if not region_instruments:
                    logger.info("No mapped instruments for region %s, skipping", region)
                    continue

            stats = await self.bulk_ingest_region(
                zip_path, region, region_instruments
            )
            all_stats[region] = stats

        # Summary
        total_ingested = sum(s["ingested"] for s in all_stats.values())
        total_failed = sum(s["failed"] for s in all_stats.values())
        logger.info(
            "Bulk ingest all complete: %d regions, %d ingested, %d failed",
            len(all_stats),
            total_ingested,
            total_failed,
        )
        return all_stats

    @staticmethod
    def _find_bulk_zip(bulk_dir: Path, region: str) -> Path | None:
        """Find a bulk ZIP file for a region."""
        patterns = [
            f"d_{region}_txt.zip",
            f"{region}_d.zip",
            f"d_{region}.zip",
        ]
        for pat in patterns:
            path = bulk_dir / pat
            if path.exists():
                return path
        return None

    # ── Shared: price upsert ────────────────────────────────────────────

    async def _upsert_prices(
        self,
        instrument_id: str,
        df: pl.DataFrame,
    ) -> None:
        """Upsert OHLCV rows for a single instrument into the prices table.

        Args:
            instrument_id: The canonical instrument ID.
            df: Polars DataFrame with date, open, high, low, close, volume columns.
        """
        upsert_sql = text("""
            INSERT INTO prices (instrument_id, date, open, high, low, close, volume)
            VALUES (:instrument_id, :date, :open, :high, :low, :close, :volume)
            ON CONFLICT (instrument_id, date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """)

        rows = df.to_dicts()
        for row in rows:
            row["instrument_id"] = instrument_id
            # Convert Decimal objects to float for SQLAlchemy binding
            for key in ["open", "high", "low", "close"]:
                if row.get(key) is not None:
                    row[key] = float(row[key])
            await self.db_session.execute(upsert_sql, row)

        logger.debug(
            "Upserted %d price rows for %s", len(rows), instrument_id
        )
