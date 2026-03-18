"""Stooq data fetcher -- CSV download for individual tickers and bulk download.

Primary data source for US, UK, Japan, Hong Kong stocks/ETFs and global indices.
Downloads OHLCV data from stooq.com via individual CSV endpoints or bulk ZIP files.
"""
from __future__ import annotations

import asyncio
import io
import logging
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import polars as pl

logger = logging.getLogger(__name__)

# Rate limiting: max 5 requests per second
_RATE_LIMIT_INTERVAL = 0.2  # seconds between requests
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # exponential backoff base in seconds

# Expected CSV columns from Stooq
_EXPECTED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


class StooqFetcher:
    """Fetches OHLCV data from Stooq via CSV endpoints and bulk ZIP downloads."""

    def __init__(
        self,
        base_url: str = "https://stooq.com/q/d/l/",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the Stooq fetcher.

        Args:
            base_url: Base URL for Stooq CSV download endpoint.
            http_client: Optional pre-configured async HTTP client.
                         If None, a new client will be created per request.
        """
        self.base_url = base_url.rstrip("/")
        self._http_client = http_client
        self._last_request_time: float = 0.0
        self._rate_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the configured HTTP client or create a temporary one."""
        if self._http_client is not None:
            return self._http_client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "MomentumCompass/1.0"},
        )

    async def _rate_limit(self) -> None:
        """Enforce rate limiting of max 5 requests per second."""
        async with self._rate_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < _RATE_LIMIT_INTERVAL:
                await asyncio.sleep(_RATE_LIMIT_INTERVAL - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    def build_url(self, ticker: str, start_date: date, end_date: date) -> str:
        """Build the Stooq CSV download URL for a given ticker and date range.

        Args:
            ticker: Stooq ticker symbol (e.g., "^SPX", "AAPL.US").
            start_date: Start date for the data range.
            end_date: End date for the data range.

        Returns:
            Fully constructed download URL string.
        """
        d1 = start_date.strftime("%Y%m%d")
        d2 = end_date.strftime("%Y%m%d")
        return f"{self.base_url}?s={ticker}&d1={d1}&d2={d2}&i=d"

    async def fetch_ohlcv(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pl.DataFrame:
        """Fetch OHLCV data for a single ticker from Stooq.

        Args:
            ticker: Stooq ticker symbol (e.g., "^SPX", "AAPL.US").
            start_date: Start date for the data range.
            end_date: End date for the data range.

        Returns:
            Polars DataFrame with columns: date, open, high, low, close, volume.
            Returns empty DataFrame on 404 or if no data is available.
        """
        url = self.build_url(ticker, start_date, end_date)
        owns_client = self._http_client is None
        client = await self._get_client()

        try:
            for attempt in range(1, _MAX_RETRIES + 1):
                await self._rate_limit()

                try:
                    response = await client.get(url)

                    if response.status_code == 404:
                        logger.warning(
                            "Ticker %s not found on Stooq (404)", ticker
                        )
                        return _empty_ohlcv_frame()

                    if response.status_code == 429:
                        wait_time = _BACKOFF_BASE ** attempt
                        logger.warning(
                            "Rate limited by Stooq for %s, retrying in %.1fs "
                            "(attempt %d/%d)",
                            ticker,
                            wait_time,
                            attempt,
                            _MAX_RETRIES,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return _parse_csv_response(response.text, ticker)

                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 429 and attempt < _MAX_RETRIES:
                        wait_time = _BACKOFF_BASE ** attempt
                        logger.warning(
                            "Rate limited (429) for %s, retry %d/%d in %.1fs",
                            ticker,
                            attempt,
                            _MAX_RETRIES,
                            wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(
                        "HTTP error fetching %s from Stooq: %s",
                        ticker,
                        exc,
                    )
                    return _empty_ohlcv_frame()

                except httpx.RequestError as exc:
                    if attempt < _MAX_RETRIES:
                        wait_time = _BACKOFF_BASE ** attempt
                        logger.warning(
                            "Request error for %s, retry %d/%d in %.1fs: %s",
                            ticker,
                            attempt,
                            _MAX_RETRIES,
                            wait_time,
                            exc,
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(
                        "Failed to fetch %s from Stooq after %d retries: %s",
                        ticker,
                        _MAX_RETRIES,
                        exc,
                    )
                    return _empty_ohlcv_frame()

        finally:
            if owns_client:
                await client.aclose()

        return _empty_ohlcv_frame()

    async def fetch_bulk(self, region: str) -> dict[str, pl.DataFrame]:
        """Download and parse a bulk ZIP file from Stooq for a given region.

        Downloads the full regional database from stooq.com/db/h/ and parses
        each instrument CSV into a Polars DataFrame.

        Args:
            region: Region identifier (e.g., "us", "uk", "jp", "hk").

        Returns:
            Dictionary mapping ticker strings to their OHLCV DataFrames.
        """
        bulk_url = f"https://stooq.com/db/h/{region}_d.zip"
        owns_client = self._http_client is None
        client = await self._get_client()

        result: dict[str, pl.DataFrame] = {}

        try:
            logger.info("Downloading bulk data for region: %s", region)
            response = await client.get(bulk_url, follow_redirects=True)
            response.raise_for_status()

            zip_buffer = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_buffer) as zf:
                csv_files = [
                    name for name in zf.namelist() if name.endswith(".csv")
                ]
                logger.info(
                    "Found %d CSV files in %s bulk download",
                    len(csv_files),
                    region,
                )

                for csv_path in csv_files:
                    ticker = Path(csv_path).stem.upper()
                    try:
                        csv_bytes = zf.read(csv_path)
                        csv_text = csv_bytes.decode("utf-8")
                        df = _parse_csv_response(csv_text, ticker)
                        if not df.is_empty():
                            result[ticker] = df
                    except Exception as exc:
                        logger.warning(
                            "Failed to parse %s from bulk ZIP: %s",
                            csv_path,
                            exc,
                        )

        except httpx.HTTPError as exc:
            logger.error(
                "Failed to download bulk data for region %s: %s",
                region,
                exc,
            )
        finally:
            if owns_client:
                await client.aclose()

        logger.info(
            "Parsed %d instruments from %s bulk download",
            len(result),
            region,
        )
        return result


def _empty_ohlcv_frame() -> pl.DataFrame:
    """Return an empty DataFrame with the standard OHLCV schema."""
    return pl.DataFrame(
        schema={
            "date": pl.Date,
            "open": pl.Decimal(precision=18, scale=6),
            "high": pl.Decimal(precision=18, scale=6),
            "low": pl.Decimal(precision=18, scale=6),
            "close": pl.Decimal(precision=18, scale=6),
            "volume": pl.Int64,
        }
    )


def _parse_csv_response(csv_text: str, ticker: str) -> pl.DataFrame:
    """Parse a Stooq CSV response into a standardized Polars DataFrame.

    Args:
        csv_text: Raw CSV text from Stooq.
        ticker: Ticker symbol (for logging purposes).

    Returns:
        Polars DataFrame with columns: date, open, high, low, close, volume.
    """
    csv_text = csv_text.strip()
    if not csv_text or "No data" in csv_text:
        logger.info("No data returned by Stooq for %s", ticker)
        return _empty_ohlcv_frame()

    try:
        df = pl.read_csv(
            io.StringIO(csv_text),
            try_parse_dates=False,
            infer_schema_length=0,  # read everything as string first
        )
    except Exception as exc:
        logger.error("Failed to parse CSV for %s: %s", ticker, exc)
        return _empty_ohlcv_frame()

    # Normalize column names to lowercase
    df = df.rename({col: col.strip().lower() for col in df.columns})

    required = {"date", "close"}
    if not required.issubset(set(df.columns)):
        logger.error(
            "CSV for %s missing required columns. Got: %s",
            ticker,
            df.columns,
        )
        return _empty_ohlcv_frame()

    try:
        df = df.with_columns(
            pl.col("date").str.to_date("%Y-%m-%d").alias("date"),
        )

        # Cast price columns to Decimal
        for col_name in ["open", "high", "low", "close"]:
            if col_name in df.columns:
                df = df.with_columns(
                    pl.col(col_name)
                    .cast(pl.Float64)
                    .cast(pl.Decimal(precision=18, scale=6))
                    .alias(col_name)
                )

        # Cast volume to Int64
        if "volume" in df.columns:
            df = df.with_columns(
                pl.col("volume").cast(pl.Int64).alias("volume")
            )
        else:
            df = df.with_columns(pl.lit(None).cast(pl.Int64).alias("volume"))

        # Ensure all expected columns exist
        for col_name in ["open", "high", "low"]:
            if col_name not in df.columns:
                df = df.with_columns(
                    pl.lit(None)
                    .cast(pl.Decimal(precision=18, scale=6))
                    .alias(col_name)
                )

        # Select and order columns
        df = df.select(["date", "open", "high", "low", "close", "volume"])
        df = df.sort("date")

    except Exception as exc:
        logger.error(
            "Failed to cast/transform columns for %s: %s", ticker, exc
        )
        return _empty_ohlcv_frame()

    logger.debug("Parsed %d rows for %s from Stooq", len(df), ticker)
    return df
