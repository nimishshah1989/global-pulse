"""Orchestrates daily data refresh: load instrument map, fetch from sources, upsert to DB.

This is the main entry point for populating the prices table. It reads the
canonical instrument_map.json, splits instruments by source, fetches OHLCV
data from Stooq or yfinance, and upserts results into PostgreSQL.
"""

import json
import logging
from datetime import date
from pathlib import Path

import polars as pl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from data.stooq_fetcher import StooqFetcher
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

    async def refresh_prices(
        self,
        instruments: list[dict],
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        """Fetch OHLCV data for all instruments and upsert into the prices table.

        Splits instruments by source (stooq vs yfinance), fetches data in
        parallel for stooq and sequentially for yfinance, then upserts.

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
