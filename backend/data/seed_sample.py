"""Generate realistic sample OHLCV data for development and testing.

Creates synthetic price and volume data following random walk patterns
with slight upward drift. Price ranges and volume levels are calibrated
per asset type to look realistic.
"""

import logging
import random
from datetime import date, timedelta
from decimal import Decimal

import polars as pl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Price ranges by asset type
_PRICE_RANGES: dict[str, tuple[float, float]] = {
    "country_index": (10000.0, 50000.0),
    "sector_etf": (30.0, 300.0),
    "sector_index": (5000.0, 40000.0),
    "country_etf": (20.0, 100.0),
    "global_sector_etf": (30.0, 200.0),
    "benchmark": (50.0, 200.0),
}

# Volume ranges by liquidity tier
_VOLUME_RANGES: dict[int, tuple[int, int]] = {
    1: (5_000_000, 50_000_000),
    2: (500_000, 5_000_000),
    3: (100_000, 500_000),
}


def _generate_trading_dates(num_days: int, end_date: date | None = None) -> list[date]:
    """Generate a list of trading dates (weekdays only).

    Args:
        num_days: Number of trading days to generate.
        end_date: Last date in the series. Defaults to today.

    Returns:
        Sorted list of trading dates.
    """
    if end_date is None:
        end_date = date.today()

    dates: list[date] = []
    current = end_date
    while len(dates) < num_days:
        if current.weekday() < 5:  # Monday=0 through Friday=4
            dates.append(current)
        current -= timedelta(days=1)

    dates.reverse()
    return dates


def generate_sample_data(
    instruments: list[dict],
    days: int = 180,
    seed: int | None = 42,
) -> dict[str, pl.DataFrame]:
    """Generate realistic sample OHLCV data for a list of instruments.

    Uses a geometric random walk with slight upward drift to produce
    realistic-looking price series. Volume is randomized within ranges
    determined by each instrument's liquidity tier.

    Args:
        instruments: List of instrument dictionaries from instrument_map.json.
        days: Number of trading days to generate.
        seed: Random seed for reproducibility. None for non-deterministic.

    Returns:
        Dictionary mapping instrument ID to Polars DataFrame with OHLCV data.
    """
    if seed is not None:
        random.seed(seed)

    trading_dates = _generate_trading_dates(days)
    result: dict[str, pl.DataFrame] = {}

    for instrument in instruments:
        inst_id = instrument["id"]
        asset_type = instrument.get("asset_type", "benchmark")
        liquidity_tier = instrument.get("liquidity_tier", 2)

        price_low, price_high = _PRICE_RANGES.get(
            asset_type, (50.0, 200.0)
        )
        vol_low, vol_high = _VOLUME_RANGES.get(liquidity_tier, (500_000, 5_000_000))

        # Start price in the middle of the range
        start_price = (price_low + price_high) / 2.0

        # Random walk parameters
        daily_drift = 0.0003  # slight upward bias (~7.5% annualized)
        daily_volatility = 0.015  # ~24% annualized volatility

        dates_list: list[date] = []
        opens: list[Decimal] = []
        highs: list[Decimal] = []
        lows: list[Decimal] = []
        closes: list[Decimal] = []
        volumes: list[int] = []

        price = start_price

        for trading_date in trading_dates:
            # Generate daily return
            ret = random.gauss(daily_drift, daily_volatility)
            close_price = price * (1.0 + ret)

            # Ensure price stays positive and within reasonable bounds
            close_price = max(close_price, price_low * 0.5)
            close_price = min(close_price, price_high * 2.0)

            # Generate intraday range
            intraday_range = abs(random.gauss(0, daily_volatility * 0.7)) * price
            open_price = price + random.gauss(0, daily_volatility * 0.3) * price
            high_price = max(open_price, close_price) + intraday_range * 0.5
            low_price = min(open_price, close_price) - intraday_range * 0.5
            low_price = max(low_price, price_low * 0.3)  # floor

            volume = random.randint(vol_low, vol_high)

            dates_list.append(trading_date)
            opens.append(Decimal(str(round(open_price, 6))))
            highs.append(Decimal(str(round(high_price, 6))))
            lows.append(Decimal(str(round(low_price, 6))))
            closes.append(Decimal(str(round(close_price, 6))))
            volumes.append(volume)

            price = close_price

        df = pl.DataFrame(
            {
                "date": dates_list,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            },
            schema={
                "date": pl.Date,
                "open": pl.Decimal(precision=18, scale=6),
                "high": pl.Decimal(precision=18, scale=6),
                "low": pl.Decimal(precision=18, scale=6),
                "close": pl.Decimal(precision=18, scale=6),
                "volume": pl.Int64,
            },
        )

        result[inst_id] = df

    logger.info(
        "Generated sample data for %d instruments (%d days each)",
        len(result),
        days,
    )
    return result


async def seed_sample_to_db(
    session: AsyncSession,
    sample_data: dict[str, pl.DataFrame],
) -> int:
    """Insert sample OHLCV data into the prices table.

    Args:
        session: Async SQLAlchemy session.
        sample_data: Dictionary mapping instrument_id to OHLCV DataFrames.

    Returns:
        Total count of rows inserted.
    """
    insert_sql = text("""
        INSERT OR REPLACE INTO prices (instrument_id, date, open, high, low, close, volume)
        VALUES (:instrument_id, :date, :open, :high, :low, :close, :volume)
    """)

    total_rows = 0

    for instrument_id, df in sample_data.items():
        rows = df.to_dicts()
        for row in rows:
            row["instrument_id"] = instrument_id
            for key in ["open", "high", "low", "close"]:
                if row.get(key) is not None:
                    row[key] = float(row[key])
            await session.execute(insert_sql, row)
        total_rows += len(rows)

    await session.commit()
    logger.info("Seeded %d total price rows into database", total_rows)
    return total_rows
