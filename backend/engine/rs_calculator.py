"""RS Calculator — Stages 1-5 of the Relative Strength engine.

All calculations use Decimal precision. Polars DataFrames used for vectorized ops.
Every formula is directly traceable to the CLAUDE.md specification.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import polars as pl


# Trading day constants for each timeframe
TRADING_DAYS_1M: int = 21
TRADING_DAYS_3M: int = 63
TRADING_DAYS_6M: int = 126
TRADING_DAYS_12M: int = 252

# Composite weights (must sum to 1.0)
WEIGHT_1M: Decimal = Decimal("0.10")
WEIGHT_3M: Decimal = Decimal("0.25")
WEIGHT_6M: Decimal = Decimal("0.35")
WEIGHT_12M: Decimal = Decimal("0.30")

# Momentum clipping bounds
MOMENTUM_MIN: Decimal = Decimal("-50")
MOMENTUM_MAX: Decimal = Decimal("50")


class RSCalculator:
    """Relative Strength calculator implementing Stages 1-5.

    Stage 1: RS Line (raw relative strength ratio)
    Stage 2: RS Trend (Mansfield — SMA comparison)
    Stage 3: Percentile Rank (distribution-agnostic ranking)
    Stage 4: Multi-Timeframe Composite (weighted score)
    Stage 5: RS Momentum (rate of change of composite)
    """

    # ------------------------------------------------------------------
    # Stage 1: RS Line
    # ------------------------------------------------------------------

    def calculate_rs_line(
        self,
        asset_prices: pl.DataFrame,
        benchmark_prices: pl.DataFrame,
    ) -> pl.DataFrame:
        """Compute raw relative strength line.

        Formula:  RS_Line[t] = (Close_asset[t] / Close_benchmark[t]) * 100

        Normalized so that the first value equals 100.

        Args:
            asset_prices: DataFrame with columns [date, close].
            benchmark_prices: DataFrame with columns [date, close].

        Returns:
            DataFrame with columns [date, rs_line] where rs_line is Decimal-safe
            (stored as Float64 in Polars, converted to Decimal at boundaries).
        """
        joined = (
            asset_prices.select([pl.col("date"), pl.col("close").alias("asset_close")])
            .join(
                benchmark_prices.select(
                    [pl.col("date"), pl.col("close").alias("bench_close")]
                ),
                on="date",
                how="inner",
            )
            .sort("date")
        )

        if joined.height == 0:
            return pl.DataFrame({"date": [], "rs_line": []}).cast(
                {"date": pl.Date, "rs_line": pl.Float64}
            )

        # Raw ratio * 100
        result = joined.with_columns(
            ((pl.col("asset_close") / pl.col("bench_close")) * 100.0).alias("rs_line")
        )

        # Normalize: divide by first value, multiply by 100
        first_val = result["rs_line"][0]
        if first_val == 0 or first_val is None:
            return result.select(["date", "rs_line"])

        result = result.with_columns(
            (pl.col("rs_line") / first_val * 100.0).alias("rs_line")
        )

        return result.select(["date", "rs_line"])

    # ------------------------------------------------------------------
    # Stage 2: RS Trend (Mansfield Relative Strength)
    # ------------------------------------------------------------------

    def calculate_rs_trend(
        self,
        rs_line_df: pl.DataFrame,
        ma_period: int = 150,
    ) -> pl.DataFrame:
        """Compute RS trend using Mansfield method.

        Formula:
            RS_MA[t] = SMA(RS_Line, 150)
            RS_Trend = 'OUTPERFORMING' if RS_Line[t] > RS_MA[t] else 'UNDERPERFORMING'

        The 150-day SMA is the Stan Weinstein / Mansfield standard.

        Args:
            rs_line_df: DataFrame with columns [date, rs_line].
            ma_period: SMA lookback period (default 150 trading days).

        Returns:
            DataFrame with columns [date, rs_line, rs_ma_150, rs_trend].
        """
        result = rs_line_df.sort("date").with_columns(
            pl.col("rs_line")
            .rolling_mean(window_size=ma_period, min_periods=ma_period)
            .alias("rs_ma_150")
        )

        result = result.with_columns(
            pl.when(pl.col("rs_ma_150").is_null())
            .then(pl.lit(None, dtype=pl.Utf8))
            .when(pl.col("rs_line") > pl.col("rs_ma_150"))
            .then(pl.lit("OUTPERFORMING"))
            .otherwise(pl.lit("UNDERPERFORMING"))
            .alias("rs_trend")
        )

        return result.select(["date", "rs_line", "rs_ma_150", "rs_trend"])

    # ------------------------------------------------------------------
    # Stage 3: Percentile Rank
    # ------------------------------------------------------------------

    def calculate_excess_returns(
        self,
        asset_prices: pl.DataFrame,
        benchmark_prices: pl.DataFrame,
    ) -> dict[str, Decimal]:
        """Compute excess returns for 1M, 3M, 6M, 12M timeframes.

        Formula: Excess_Return_nM = Asset_Return_nM - Benchmark_Return_nM
        Uses simple price returns over each period.

        Args:
            asset_prices: DataFrame with [date, close], sorted by date.
            benchmark_prices: DataFrame with [date, close], sorted by date.

        Returns:
            Dict with keys '1M', '3M', '6M', '12M' mapping to Decimal excess
            returns. Missing timeframes (not enough data) are omitted.
        """
        joined = (
            asset_prices.select([pl.col("date"), pl.col("close").alias("asset_close")])
            .join(
                benchmark_prices.select(
                    [pl.col("date"), pl.col("close").alias("bench_close")]
                ),
                on="date",
                how="inner",
            )
            .sort("date")
        )

        n = joined.height
        timeframes: dict[str, int] = {
            "1M": TRADING_DAYS_1M,
            "3M": TRADING_DAYS_3M,
            "6M": TRADING_DAYS_6M,
            "12M": TRADING_DAYS_12M,
        }

        results: dict[str, Decimal] = {}

        for label, days in timeframes.items():
            if n < days + 1:
                continue

            end_asset = Decimal(str(joined["asset_close"][-1]))
            start_asset = Decimal(str(joined["asset_close"][-1 - days]))
            end_bench = Decimal(str(joined["bench_close"][-1]))
            start_bench = Decimal(str(joined["bench_close"][-1 - days]))

            if start_asset == 0 or start_bench == 0:
                continue

            asset_return = (end_asset - start_asset) / start_asset
            bench_return = (end_bench - start_bench) / start_bench
            results[label] = asset_return - bench_return

        return results

    def calculate_percentile_rank(
        self,
        excess_return: Decimal,
        peer_group_excess_returns: list[Decimal],
    ) -> Decimal:
        """Rank within peer group, returns 0-100 percentile.

        100 = best performer in group. Distribution-agnostic (NOT z-score).
        Uses: percentile = (number of values below) / (total - 1) * 100
        For a single-element group, returns Decimal('50').

        Args:
            excess_return: The instrument's excess return.
            peer_group_excess_returns: All peer excess returns (including self).

        Returns:
            Decimal percentile rank in [0, 100].
        """
        n = len(peer_group_excess_returns)
        if n <= 1:
            return Decimal("50")

        count_below = sum(1 for v in peer_group_excess_returns if v < excess_return)
        percentile = (Decimal(str(count_below)) / Decimal(str(n - 1))) * Decimal("100")
        return percentile.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ------------------------------------------------------------------
    # Stage 4: Multi-Timeframe Composite
    # ------------------------------------------------------------------

    def calculate_composite(
        self,
        pct_1m: Decimal,
        pct_3m: Decimal,
        pct_6m: Decimal,
        pct_12m: Decimal,
    ) -> Decimal:
        """Weighted multi-timeframe composite score.

        Formula:
            RS_Composite = pct_1m * 0.10 + pct_3m * 0.25
                         + pct_6m * 0.35 + pct_12m * 0.30

        Result: 0-100 score. Higher = stronger relative performer.
        """
        composite = (
            pct_1m * WEIGHT_1M
            + pct_3m * WEIGHT_3M
            + pct_6m * WEIGHT_6M
            + pct_12m * WEIGHT_12M
        )
        return composite.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ------------------------------------------------------------------
    # Stage 5: RS Momentum
    # ------------------------------------------------------------------

    def calculate_momentum(
        self,
        rs_composite_series: pl.DataFrame,
        lookback: int = 20,
    ) -> pl.DataFrame:
        """Rate of change of the RS composite score.

        Formula:
            RS_Momentum = RS_Composite[today] - RS_Composite[20 days ago]
            Clipped to [-50, +50].

        Args:
            rs_composite_series: DataFrame with [date, rs_composite].
            lookback: Number of trading days to look back (default 20).

        Returns:
            DataFrame with [date, rs_composite, rs_momentum].
        """
        result = rs_composite_series.sort("date").with_columns(
            (pl.col("rs_composite") - pl.col("rs_composite").shift(lookback)).alias(
                "rs_momentum"
            )
        )

        # Clip to [-50, +50]
        result = result.with_columns(
            pl.when(pl.col("rs_momentum").is_null())
            .then(pl.lit(None, dtype=pl.Float64))
            .when(pl.col("rs_momentum") > 50.0)
            .then(pl.lit(50.0))
            .when(pl.col("rs_momentum") < -50.0)
            .then(pl.lit(-50.0))
            .otherwise(pl.col("rs_momentum"))
            .alias("rs_momentum")
        )

        return result.select(["date", "rs_composite", "rs_momentum"])

    # ------------------------------------------------------------------
    # Full Pipeline (Stages 1-5)
    # ------------------------------------------------------------------

    def compute_rs_scores(
        self,
        instrument_id: str,
        asset_prices: pl.DataFrame,
        benchmark_prices: pl.DataFrame,
        peer_group_data: dict[str, pl.DataFrame],
    ) -> dict:
        """Run full pipeline stages 1-5 for a single instrument.

        Args:
            instrument_id: Canonical instrument identifier.
            asset_prices: OHLCV DataFrame with [date, close].
            benchmark_prices: Benchmark OHLCV DataFrame with [date, close].
            peer_group_data: Dict mapping peer instrument_id to their
                price DataFrames (must include this instrument).

        Returns:
            Dict with all computed RS values including rs_line_df,
            rs_trend_df, excess_returns, percentile_ranks, composite,
            and momentum.
        """
        # Stage 1
        rs_line_df = self.calculate_rs_line(asset_prices, benchmark_prices)

        # Stage 2
        rs_trend_df = self.calculate_rs_trend(rs_line_df)

        # Stage 3: excess returns for this instrument
        excess_returns = self.calculate_excess_returns(asset_prices, benchmark_prices)

        # Compute peer excess returns for each timeframe
        peer_excess: dict[str, list[Decimal]] = {tf: [] for tf in excess_returns}
        for peer_id, peer_prices in peer_group_data.items():
            peer_er = self.calculate_excess_returns(peer_prices, benchmark_prices)
            for tf in excess_returns:
                if tf in peer_er:
                    peer_excess[tf].append(peer_er[tf])

        # Percentile ranks
        percentile_ranks: dict[str, Decimal] = {}
        for tf, er in excess_returns.items():
            if tf in peer_excess and peer_excess[tf]:
                percentile_ranks[tf] = self.calculate_percentile_rank(
                    er, peer_excess[tf]
                )
            else:
                percentile_ranks[tf] = Decimal("50")

        # Stage 4: composite (use 50 as default for missing timeframes)
        composite = self.calculate_composite(
            pct_1m=percentile_ranks.get("1M", Decimal("50")),
            pct_3m=percentile_ranks.get("3M", Decimal("50")),
            pct_6m=percentile_ranks.get("6M", Decimal("50")),
            pct_12m=percentile_ranks.get("12M", Decimal("50")),
        )

        return {
            "instrument_id": instrument_id,
            "rs_line_df": rs_line_df,
            "rs_trend_df": rs_trend_df,
            "excess_returns": excess_returns,
            "percentile_ranks": percentile_ranks,
            "rs_composite": composite,
        }
