"""yfinance data fetcher for gap-fill markets.

Covers India, South Korea, China, Taiwan, Australia, Brazil, Canada,
and the ACWI global benchmark -- markets not available via Stooq bulk download.
"""

import asyncio
import logging
from datetime import date

import polars as pl

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class YFinanceFetcher:
    """Fetches OHLCV data from Yahoo Finance via the yfinance library.

    yfinance is synchronous, so all fetch methods wrap calls in
    asyncio.to_thread when used from an async context.
    """

    def fetch_ohlcv(
        self,
        ticker: str,
        period: str = "3y",
    ) -> pl.DataFrame:
        """Fetch OHLCV data for a single ticker using yfinance.

        Args:
            ticker: Yahoo Finance ticker symbol (e.g., "^NSEI", "RELIANCE.NS").
            period: Lookback period string (e.g., "3y", "1y", "6mo").

        Returns:
            Polars DataFrame with columns: date, open, high, low, close, volume.
            Returns empty DataFrame if the ticker is invalid or no data is found.
        """
        logger.info("Fetching %s from yfinance (period=%s)", ticker, period)

        if yf is None:
            logger.error("yfinance is not installed; cannot fetch %s", ticker)
            return _empty_ohlcv_frame()

        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period=period, auto_adjust=True)
        except Exception as exc:
            logger.error(
                "yfinance error fetching %s: %s", ticker, exc
            )
            return _empty_ohlcv_frame()

        if hist is None or hist.empty:
            logger.warning("No data returned by yfinance for %s", ticker)
            return _empty_ohlcv_frame()

        try:
            # Reset index to get Date as a column
            hist = hist.reset_index()

            # Rename columns to lowercase standard format
            rename_map = {
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
            hist = hist.rename(columns=rename_map)

            # Select only needed columns (yfinance may include Dividends, Stock Splits)
            available_cols = [
                c for c in ["date", "open", "high", "low", "close", "volume"]
                if c in hist.columns
            ]
            hist = hist[available_cols]

            # Convert pandas to polars
            df = pl.from_pandas(hist)

            # Ensure date column is Date type (yfinance returns datetime with tz)
            if df.schema["date"] != pl.Date:
                df = df.with_columns(
                    pl.col("date").cast(pl.Date).alias("date")
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
                df = df.with_columns(
                    pl.lit(None).cast(pl.Int64).alias("volume")
                )

            # Ensure all columns exist
            for col_name in ["open", "high", "low"]:
                if col_name not in df.columns:
                    df = df.with_columns(
                        pl.lit(None)
                        .cast(pl.Decimal(precision=18, scale=6))
                        .alias(col_name)
                    )

            df = df.select(["date", "open", "high", "low", "close", "volume"])
            df = df.sort("date")

            logger.info(
                "Fetched %d rows for %s from yfinance", len(df), ticker
            )
            return df

        except Exception as exc:
            logger.error(
                "Failed to convert yfinance data for %s: %s", ticker, exc
            )
            return _empty_ohlcv_frame()

    async def fetch_ohlcv_async(
        self,
        ticker: str,
        period: str = "3y",
    ) -> pl.DataFrame:
        """Async wrapper around fetch_ohlcv using asyncio.to_thread.

        Args:
            ticker: Yahoo Finance ticker symbol.
            period: Lookback period string.

        Returns:
            Polars DataFrame with standard OHLCV columns.
        """
        return await asyncio.to_thread(self.fetch_ohlcv, ticker, period)


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
