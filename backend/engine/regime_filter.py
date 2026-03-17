"""Regime Filter — Stage 9 global risk overlay.

Determines whether the global market regime is RISK_ON or RISK_OFF
by comparing the ACWI (iShares MSCI ACWI ETF) price to its 200-day SMA.
"""

import polars as pl


# Standard lookback for regime determination
REGIME_MA_PERIOD: int = 200


def calculate_regime(
    acwi_prices: pl.DataFrame,
    ma_period: int = REGIME_MA_PERIOD,
) -> str:
    """Determine global market regime from ACWI price vs 200-day SMA.

    Rules:
        Price >= 200-day SMA → RISK_ON (normal operation, surface momentum leaders)
        Price <  200-day SMA → RISK_OFF (defensive, identify survivors)

    When RISK_OFF:
        - All opportunity signals get a warning flag
        - Recommendations shift from 'buy leaders' to 'identify survivors'
        - Basket suggestions favor defensive sectors

    Args:
        acwi_prices: DataFrame with columns [date, close], sorted by date.
            Must have at least ``ma_period`` rows for a valid SMA.
        ma_period: SMA lookback period (default 200 trading days).

    Returns:
        'RISK_ON' or 'RISK_OFF'. Returns 'RISK_ON' if insufficient data
        to compute the SMA (conservative default).
    """
    df = acwi_prices.sort("date")

    if df.height < ma_period:
        return "RISK_ON"

    # Compute 200-day SMA
    df = df.with_columns(
        pl.col("close")
        .rolling_mean(window_size=ma_period, min_periods=ma_period)
        .alias("sma_200")
    )

    # Get the latest row with a valid SMA
    latest = df.filter(pl.col("sma_200").is_not_null()).tail(1)

    if latest.height == 0:
        return "RISK_ON"

    current_price = latest["close"][0]
    sma_value = latest["sma_200"][0]

    if current_price >= sma_value:
        return "RISK_ON"
    else:
        return "RISK_OFF"
