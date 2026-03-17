"""Liquidity Scorer — Stage 8 tier assignment + Stage 10 extension warning.

Assigns liquidity tiers based on average daily traded value and checks
for extended RS conditions that warrant risk management attention.
"""

from decimal import Decimal


# Tier thresholds in USD equivalent
TIER_1_THRESHOLD: Decimal = Decimal("5000000")   # $5M daily value
TIER_2_THRESHOLD: Decimal = Decimal("500000")     # $500K daily value

# Extension warning thresholds (percentile ranks)
EXTENSION_3M_THRESHOLD: Decimal = Decimal("95")
EXTENSION_6M_THRESHOLD: Decimal = Decimal("95")
EXTENSION_12M_THRESHOLD: Decimal = Decimal("90")


class LiquidityScorer:
    """Scores instrument liquidity and detects extended RS conditions."""

    def calculate_liquidity_tier(self, avg_daily_value: Decimal) -> int:
        """Assign liquidity tier based on average daily traded value.

        Tiers:
            >= $5M daily  → Tier 1 (full confidence in all signals)
            >= $500K daily → Tier 2 (volume as supporting evidence only)
            <  $500K daily → Tier 3 (flag, don't rely on volume signals)

        For non-USD instruments, avg_daily_value should already be
        converted to USD equivalent.

        Args:
            avg_daily_value: 20-day average of (Close * Volume) in USD.

        Returns:
            Integer tier: 1, 2, or 3.
        """
        if avg_daily_value >= TIER_1_THRESHOLD:
            return 1
        elif avg_daily_value >= TIER_2_THRESHOLD:
            return 2
        else:
            return 3

    def check_extension_warning(
        self,
        rs_pct_3m: Decimal,
        rs_pct_6m: Decimal,
        rs_pct_12m: Decimal,
    ) -> bool:
        """Check if instrument RS is extended across all timeframes.

        Extension condition:
            3M > 95 AND 6M > 95 AND 12M > 90

        This is NOT a sell signal — it is a risk management nudge indicating
        the asset has been in the top percentiles across all timeframes.

        Args:
            rs_pct_3m: 3-month RS percentile rank.
            rs_pct_6m: 6-month RS percentile rank.
            rs_pct_12m: 12-month RS percentile rank.

        Returns:
            True if extension warning should be flagged.
        """
        return (
            rs_pct_3m > EXTENSION_3M_THRESHOLD
            and rs_pct_6m > EXTENSION_6M_THRESHOLD
            and rs_pct_12m > EXTENSION_12M_THRESHOLD
        )
