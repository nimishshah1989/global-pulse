"""RS Engine v2 — Simplified 3-indicator system with OBV.

Three indicators:
1. Price Trend: RS Line vs MA (outperforming/underperforming)
2. Momentum: Rate of change of RS Line (accelerating/decelerating)
3. Volume Character: OBV trend (accumulation/distribution)

Action Matrix (8 outcomes):
  OUT + ACC + ACCUM  → BUY
  OUT + ACC + DIST   → HOLD
  OUT + DEC + ACCUM  → HOLD
  OUT + DEC + DIST   → REDUCE
  UNDER + DEC + DIST → SELL
  UNDER + DEC + ACCUM→ WATCH
  UNDER + ACC + ACCUM→ ACCUMULATE
  UNDER + ACC + DIST → AVOID
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import polars as pl


# Timeframe presets: (MA period, momentum lookback)
TIMEFRAME_SHORT = (20, 10)
TIMEFRAME_MEDIUM = (50, 25)
TIMEFRAME_LONG = (150, 75)

TIMEFRAME_MAP: dict[str, tuple[int, int]] = {
    "short": TIMEFRAME_SHORT,
    "medium": TIMEFRAME_MEDIUM,
    "long": TIMEFRAME_LONG,
}

# OBV MA period for trend determination
OBV_MA_PERIOD = 20

# Regime filter
REGIME_MA_PERIOD = 200

# Action labels and colors
ACTION_CONFIG: dict[str, dict[str, str]] = {
    "BUY": {"color": "emerald", "label": "Buy / Overweight"},
    "HOLD_DIVERGENCE": {"color": "yellow", "label": "Hold (divergence)"},
    "HOLD_FADING": {"color": "yellow", "label": "Hold (fading)"},
    "REDUCE": {"color": "orange", "label": "Reduce"},
    "SELL": {"color": "red", "label": "Sell / Underweight"},
    "WATCH": {"color": "blue", "label": "Watch"},
    "ACCUMULATE": {"color": "teal", "label": "Accumulate"},
    "AVOID": {"color": "slate", "label": "Avoid"},
}


def calculate_rs_line(
    asset_prices: pl.DataFrame,
    benchmark_prices: pl.DataFrame,
) -> pl.DataFrame:
    """Compute RS Line = Asset Close / Benchmark Close × 100.

    Args:
        asset_prices: DataFrame with [date, close].
        benchmark_prices: DataFrame with [date, close].

    Returns:
        DataFrame with [date, asset_close, bench_close, rs_line].
    """
    joined = (
        asset_prices.select([
            pl.col("date"),
            pl.col("close").alias("asset_close"),
        ])
        .join(
            benchmark_prices.select([
                pl.col("date"),
                pl.col("close").alias("bench_close"),
            ]),
            on="date",
            how="inner",
        )
        .sort("date")
    )

    if joined.height == 0:
        return pl.DataFrame(schema={
            "date": pl.Date,
            "asset_close": pl.Float64,
            "bench_close": pl.Float64,
            "rs_line": pl.Float64,
        })

    result = joined.with_columns(
        (pl.col("asset_close") / pl.col("bench_close") * 100.0).alias("rs_line")
    )

    return result


def calculate_price_trend(
    rs_line_df: pl.DataFrame,
    ma_period: int = 50,
) -> pl.DataFrame:
    """Indicator 1: Price Trend — RS Line vs its MA.

    OUTPERFORMING = RS Line > MA (asset beating benchmark)
    UNDERPERFORMING = RS Line < MA (asset lagging benchmark)

    Returns:
        DataFrame with added columns [rs_ma, price_trend].
    """
    result = rs_line_df.sort("date").with_columns(
        pl.col("rs_line")
        .rolling_mean(window_size=ma_period, min_periods=min(ma_period, 20))
        .alias("rs_ma")
    )

    result = result.with_columns(
        pl.when(pl.col("rs_ma").is_null())
        .then(pl.lit(None, dtype=pl.Utf8))
        .when(pl.col("rs_line") > pl.col("rs_ma"))
        .then(pl.lit("OUTPERFORMING"))
        .otherwise(pl.lit("UNDERPERFORMING"))
        .alias("price_trend")
    )

    return result


def calculate_momentum(
    rs_line_df: pl.DataFrame,
    lookback: int = 25,
) -> pl.DataFrame:
    """Indicator 2: Momentum — Rate of Change of RS Line.

    RS Momentum = (RS Line today / RS Line N days ago - 1) × 100
    ACCELERATING if > 0, DECELERATING if < 0.

    Returns:
        DataFrame with added columns [rs_momentum, rs_momentum_pct, momentum_trend].
    """
    result = rs_line_df.sort("date").with_columns(
        pl.col("rs_line").shift(lookback).alias("_rs_prev")
    )

    result = result.with_columns(
        pl.when(pl.col("_rs_prev").is_null() | (pl.col("_rs_prev") == 0))
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(
            (pl.col("rs_line") / pl.col("_rs_prev") - 1.0) * 100.0
        )
        .alias("rs_momentum_pct")
    )

    result = result.with_columns(
        pl.when(pl.col("rs_momentum_pct").is_null())
        .then(pl.lit(None, dtype=pl.Utf8))
        .when(pl.col("rs_momentum_pct") > 0)
        .then(pl.lit("ACCELERATING"))
        .otherwise(pl.lit("DECELERATING"))
        .alias("momentum_trend")
    )

    return result.drop("_rs_prev")


def calculate_obv(prices_df: pl.DataFrame) -> pl.DataFrame:
    """Indicator 3: On-Balance Volume.

    OBV rules:
        close > prev_close → OBV += volume  (buying)
        close < prev_close → OBV -= volume  (selling)
        close == prev_close → OBV unchanged

    Returns:
        DataFrame with added columns [obv, obv_ma, volume_character].
    """
    df = prices_df.sort("date")

    if "volume" not in df.columns or df.height < 2:
        return df.with_columns(
            pl.lit(0.0).alias("obv"),
            pl.lit(0.0).alias("obv_ma"),
            pl.lit("NEUTRAL").alias("volume_character"),
        )

    # Calculate OBV using cumulative sum of signed volume
    df = df.with_columns(
        pl.col("close").shift(1).alias("_prev_close")
    )

    df = df.with_columns(
        pl.when(pl.col("_prev_close").is_null())
        .then(pl.lit(0.0))
        .when(pl.col("close") > pl.col("_prev_close"))
        .then(pl.col("volume").cast(pl.Float64))
        .when(pl.col("close") < pl.col("_prev_close"))
        .then(-pl.col("volume").cast(pl.Float64))
        .otherwise(pl.lit(0.0))
        .alias("_obv_delta")
    )

    df = df.with_columns(
        pl.col("_obv_delta").cum_sum().alias("obv")
    )

    # OBV MA for trend determination
    df = df.with_columns(
        pl.col("obv")
        .rolling_mean(window_size=OBV_MA_PERIOD, min_periods=5)
        .alias("obv_ma")
    )

    df = df.with_columns(
        pl.when(pl.col("obv_ma").is_null())
        .then(pl.lit("NEUTRAL"))
        .when(pl.col("obv") > pl.col("obv_ma"))
        .then(pl.lit("ACCUMULATION"))
        .otherwise(pl.lit("DISTRIBUTION"))
        .alias("volume_character")
    )

    return df.drop(["_prev_close", "_obv_delta"])


def determine_action(
    price_trend: str | None,
    momentum_trend: str | None,
    volume_character: str | None,
) -> str:
    """Map 3 indicators to one of 8 actions.

    Args:
        price_trend: OUTPERFORMING or UNDERPERFORMING
        momentum_trend: ACCELERATING or DECELERATING
        volume_character: ACCUMULATION or DISTRIBUTION

    Returns:
        Action string: BUY, HOLD_DIVERGENCE, HOLD_FADING, REDUCE,
        SELL, WATCH, ACCUMULATE, or AVOID.
    """
    if price_trend is None or momentum_trend is None:
        return "WATCH"

    out = price_trend == "OUTPERFORMING"
    acc = momentum_trend == "ACCELERATING"
    accum = volume_character in ("ACCUMULATION", "NEUTRAL", None)

    if out and acc and accum:
        return "BUY"
    elif out and acc and not accum:
        return "HOLD_DIVERGENCE"
    elif out and not acc and accum:
        return "HOLD_FADING"
    elif out and not acc and not accum:
        return "REDUCE"
    elif not out and not acc and not accum:
        return "SELL"
    elif not out and not acc and accum:
        return "WATCH"
    elif not out and acc and accum:
        return "ACCUMULATE"
    elif not out and acc and not accum:
        return "AVOID"
    else:
        return "WATCH"


def calculate_regime(acwi_prices: pl.DataFrame) -> str:
    """Determine RISK_ON / RISK_OFF from ACWI vs 200-day MA.

    Args:
        acwi_prices: DataFrame with [date, close].

    Returns:
        'RISK_ON' or 'RISK_OFF'.
    """
    df = acwi_prices.sort("date")

    if df.height < REGIME_MA_PERIOD:
        return "RISK_ON"

    df = df.with_columns(
        pl.col("close")
        .rolling_mean(window_size=REGIME_MA_PERIOD, min_periods=REGIME_MA_PERIOD)
        .alias("sma_200")
    )

    latest = df.filter(pl.col("sma_200").is_not_null()).tail(1)

    if latest.height == 0:
        return "RISK_ON"

    current_price = latest["close"][0]
    sma_value = latest["sma_200"][0]

    return "RISK_ON" if current_price >= sma_value else "RISK_OFF"


def compute_instrument_scores(
    instrument_id: str,
    asset_prices: pl.DataFrame,
    benchmark_prices: pl.DataFrame,
    timeframe: str = "medium",
) -> dict[str, Any] | None:
    """Full v2 pipeline for a single instrument.

    Args:
        instrument_id: Canonical instrument ID.
        asset_prices: DataFrame with [date, close, volume (optional)].
        benchmark_prices: DataFrame with [date, close].
        timeframe: 'short', 'medium', or 'long'.

    Returns:
        Dict with all computed indicators, or None if insufficient data.
    """
    ma_period, mom_lookback = TIMEFRAME_MAP.get(timeframe, TIMEFRAME_MEDIUM)

    # Need at least ma_period + some buffer
    if asset_prices.height < ma_period or benchmark_prices.height < ma_period:
        return None

    # Indicator 1: Price Trend
    rs_df = calculate_rs_line(asset_prices, benchmark_prices)
    if rs_df.height < ma_period:
        return None

    rs_trend_df = calculate_price_trend(rs_df, ma_period=ma_period)

    # Indicator 2: Momentum
    rs_mom_df = calculate_momentum(rs_trend_df, lookback=mom_lookback)

    # Get latest values
    latest = rs_mom_df.tail(1)
    if latest.height == 0:
        return None

    rs_line = float(latest["rs_line"][0])
    rs_ma = float(latest["rs_ma"][0]) if latest["rs_ma"][0] is not None else None
    price_trend = latest["price_trend"][0]
    momentum_pct = (
        float(latest["rs_momentum_pct"][0])
        if latest["rs_momentum_pct"][0] is not None
        else 0.0
    )
    momentum_trend = latest["momentum_trend"][0]

    # Indicator 3: OBV
    obv_df = calculate_obv(asset_prices)
    obv_latest = obv_df.tail(1)
    if obv_latest.height > 0:
        obv_value = float(obv_latest["obv"][0])
        obv_ma_value = (
            float(obv_latest["obv_ma"][0])
            if obv_latest["obv_ma"][0] is not None
            else 0.0
        )
        volume_character = obv_latest["volume_character"][0]
    else:
        obv_value = 0.0
        obv_ma_value = 0.0
        volume_character = "NEUTRAL"

    # Action
    action = determine_action(price_trend, momentum_trend, volume_character)

    # RS score for ranking (0-100 based on where RS line is relative to MA)
    if rs_ma is not None and rs_ma > 0:
        rs_score = round(((rs_line / rs_ma) - 1.0) * 1000 + 50, 2)
        rs_score = max(0.0, min(100.0, rs_score))
    else:
        rs_score = 50.0

    return {
        "instrument_id": instrument_id,
        # Indicator 1
        "rs_line": round(rs_line, 4),
        "rs_ma": round(rs_ma, 4) if rs_ma is not None else None,
        "price_trend": price_trend,
        # Indicator 2
        "rs_momentum_pct": round(momentum_pct, 2),
        "momentum_trend": momentum_trend,
        # Indicator 3
        "obv": round(obv_value, 0),
        "obv_ma": round(obv_ma_value, 0),
        "volume_character": volume_character,
        # Action
        "action": action,
        # Score for ranking/sorting
        "rs_score": rs_score,
    }


def compute_chart_data(
    asset_prices: pl.DataFrame,
    benchmark_prices: pl.DataFrame,
    timeframe: str = "medium",
) -> dict[str, list[dict[str, Any]]]:
    """Compute RS line + OBV chart data for an instrument.

    Returns dict with keys:
        rs_chart: [{date, rs_line, rs_ma, price_trend}]
        obv_chart: [{date, obv, obv_ma, volume_character}]
        price_chart: [{date, close, volume}]
    """
    ma_period, mom_lookback = TIMEFRAME_MAP.get(timeframe, TIMEFRAME_MEDIUM)

    # RS Line chart
    rs_df = calculate_rs_line(asset_prices, benchmark_prices)
    rs_trend_df = calculate_price_trend(rs_df, ma_period=ma_period)
    rs_mom_df = calculate_momentum(rs_trend_df, lookback=mom_lookback)

    rs_chart = []
    for row in rs_mom_df.iter_rows(named=True):
        rs_chart.append({
            "date": str(row["date"]),
            "rs_line": round(row["rs_line"], 4) if row["rs_line"] is not None else None,
            "rs_ma": round(row["rs_ma"], 4) if row["rs_ma"] is not None else None,
            "price_trend": row["price_trend"],
            "rs_momentum_pct": (
                round(row["rs_momentum_pct"], 2)
                if row.get("rs_momentum_pct") is not None
                else None
            ),
        })

    # OBV chart
    obv_df = calculate_obv(asset_prices)
    obv_chart = []
    for row in obv_df.iter_rows(named=True):
        obv_chart.append({
            "date": str(row["date"]),
            "obv": round(row["obv"], 0) if row.get("obv") is not None else None,
            "obv_ma": round(row["obv_ma"], 0) if row.get("obv_ma") is not None else None,
            "volume_character": row.get("volume_character"),
        })

    # Price chart
    price_chart = []
    for row in asset_prices.sort("date").iter_rows(named=True):
        entry: dict[str, Any] = {
            "date": str(row["date"]),
            "close": round(row["close"], 4) if row.get("close") is not None else None,
        }
        if "volume" in asset_prices.columns:
            entry["volume"] = row.get("volume")
        price_chart.append(entry)

    return {
        "rs_chart": rs_chart,
        "obv_chart": obv_chart,
        "price_chart": price_chart,
    }
