"""Volume Analyzer — Stage 6 of the RS engine.

Volume conviction adjustment. Volume confirms or denies RS signals.
All calculations use Decimal precision.
"""

from decimal import Decimal, ROUND_HALF_UP

import polars as pl


class VolumeAnalyzer:
    """Analyzes volume to produce conviction-adjusted RS scores.

    Volume_Ratio > 1.0 → above-average participation (conviction).
    Volume_Ratio < 1.0 → below-average participation (thinning).
    """

    def calculate_volume_ratio(self, volume_series: pl.DataFrame) -> Decimal:
        """Compute volume ratio: SMA(Volume, 20) / SMA(Volume, 100).

        Args:
            volume_series: DataFrame with columns [date, volume], sorted by date.
                Must have at least 100 rows for a meaningful ratio.

        Returns:
            Decimal volume ratio. Returns Decimal('1') if insufficient data.
        """
        df = volume_series.sort("date")
        n = df.height

        if n < 20:
            return Decimal("1")

        # SMA(20) of the most recent 20 bars
        recent_20 = df["volume"].tail(20)
        sma_20 = Decimal(str(recent_20.mean()))

        # SMA(100) — use whatever data is available up to 100
        lookback = min(n, 100)
        recent_100 = df["volume"].tail(lookback)
        sma_100 = Decimal(str(recent_100.mean()))

        if sma_100 == 0:
            return Decimal("1")

        ratio = sma_20 / sma_100
        return ratio.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    def calculate_vol_multiplier(self, volume_ratio: Decimal) -> Decimal:
        """Compute conservative volume adjustment multiplier (0.85-1.15).

        Rules:
            >= 1.5 → 1.15
            >= 1.0 → 1.0 + (ratio - 1.0) * 0.30
            >= 0.5 → 1.0 (neutral — don't penalize normal)
            <  0.5 → 0.85 (thin volume — discount signal)

        Args:
            volume_ratio: The SMA(20)/SMA(100) volume ratio.

        Returns:
            Decimal multiplier in [0.85, 1.15].
        """
        if volume_ratio >= Decimal("1.5"):
            return Decimal("1.15")
        elif volume_ratio >= Decimal("1.0"):
            multiplier = Decimal("1.0") + (volume_ratio - Decimal("1.0")) * Decimal(
                "0.30"
            )
            return multiplier.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        elif volume_ratio >= Decimal("0.5"):
            return Decimal("1.000")
        else:
            return Decimal("0.85")

    def calculate_adjusted_rs_score(
        self,
        rs_composite: Decimal,
        vol_multiplier: Decimal,
        liquidity_tier: int,
    ) -> Decimal:
        """Compute volume-adjusted RS score.

        Formula: Adjusted_RS_Score = rs_composite * vol_multiplier

        IMPORTANT: If liquidity_tier == 3, cap at 70 regardless of raw score.

        Args:
            rs_composite: The raw RS composite score (0-100).
            vol_multiplier: Volume conviction multiplier (0.85-1.15).
            liquidity_tier: 1, 2, or 3.

        Returns:
            Decimal adjusted score, capped at 70 for tier 3 instruments.
        """
        adjusted = rs_composite * vol_multiplier
        adjusted = adjusted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if liquidity_tier == 3:
            adjusted = min(adjusted, Decimal("70"))

        return adjusted
