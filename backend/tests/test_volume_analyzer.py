"""Tests for Volume Analyzer — Stage 6 volume conviction adjustment."""

from datetime import date, timedelta
from decimal import Decimal

import polars as pl
import pytest

from engine.volume_analyzer import VolumeAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_volume_df(
    volumes: list[int],
    start_date: date = date(2024, 1, 2),
) -> pl.DataFrame:
    """Create a [date, volume] DataFrame."""
    dates = [start_date + timedelta(days=i) for i in range(len(volumes))]
    return pl.DataFrame({"date": dates, "volume": volumes}).cast(
        {"date": pl.Date, "volume": pl.Int64}
    )


@pytest.fixture
def analyzer() -> VolumeAnalyzer:
    return VolumeAnalyzer()


# ---------------------------------------------------------------------------
# Volume Ratio
# ---------------------------------------------------------------------------

class TestVolumeRatio:
    def test_volume_ratio_above_average(self, analyzer: VolumeAnalyzer) -> None:
        """Recent volume > long-term → ratio > 1."""
        # 80 days of low volume, then 20 days of high volume
        volumes = [1000] * 80 + [3000] * 20
        df = make_volume_df(volumes)
        ratio = analyzer.calculate_volume_ratio(df)
        assert ratio > Decimal("1")

    def test_volume_ratio_below_average(self, analyzer: VolumeAnalyzer) -> None:
        """Recent volume < long-term → ratio < 1."""
        # 80 days of high volume, then 20 days of low volume
        volumes = [3000] * 80 + [1000] * 20
        df = make_volume_df(volumes)
        ratio = analyzer.calculate_volume_ratio(df)
        assert ratio < Decimal("1")

    def test_volume_ratio_equal(self, analyzer: VolumeAnalyzer) -> None:
        """Constant volume → ratio = 1."""
        volumes = [1000] * 100
        df = make_volume_df(volumes)
        ratio = analyzer.calculate_volume_ratio(df)
        assert ratio == Decimal("1.000")

    def test_volume_ratio_insufficient_data(self, analyzer: VolumeAnalyzer) -> None:
        """Fewer than 20 rows → default ratio of 1."""
        volumes = [1000] * 10
        df = make_volume_df(volumes)
        ratio = analyzer.calculate_volume_ratio(df)
        assert ratio == Decimal("1")


# ---------------------------------------------------------------------------
# Volume Multiplier
# ---------------------------------------------------------------------------

class TestVolMultiplier:
    def test_vol_multiplier_high_conviction(self, analyzer: VolumeAnalyzer) -> None:
        """Ratio >= 1.5 → multiplier = 1.15."""
        result = analyzer.calculate_vol_multiplier(Decimal("1.5"))
        assert result == Decimal("1.15")

        result = analyzer.calculate_vol_multiplier(Decimal("2.0"))
        assert result == Decimal("1.15")

    def test_vol_multiplier_moderate(self, analyzer: VolumeAnalyzer) -> None:
        """Ratio 1.0-1.5 → multiplier between 1.0 and 1.15."""
        result = analyzer.calculate_vol_multiplier(Decimal("1.25"))
        # 1.0 + (1.25 - 1.0) * 0.30 = 1.0 + 0.075 = 1.075
        assert result == Decimal("1.075")

    def test_vol_multiplier_neutral(self, analyzer: VolumeAnalyzer) -> None:
        """Ratio 0.5-1.0 → multiplier = 1.0 (neutral)."""
        result = analyzer.calculate_vol_multiplier(Decimal("0.75"))
        assert result == Decimal("1.000")

        result = analyzer.calculate_vol_multiplier(Decimal("0.5"))
        assert result == Decimal("1.000")

    def test_vol_multiplier_thin(self, analyzer: VolumeAnalyzer) -> None:
        """Ratio < 0.5 → multiplier = 0.85."""
        result = analyzer.calculate_vol_multiplier(Decimal("0.3"))
        assert result == Decimal("0.85")

        result = analyzer.calculate_vol_multiplier(Decimal("0.0"))
        assert result == Decimal("0.85")

    def test_vol_multiplier_at_1(self, analyzer: VolumeAnalyzer) -> None:
        """Ratio exactly 1.0 → multiplier = 1.0."""
        result = analyzer.calculate_vol_multiplier(Decimal("1.0"))
        # 1.0 + (1.0 - 1.0) * 0.30 = 1.0
        assert result == Decimal("1.000")


# ---------------------------------------------------------------------------
# Adjusted RS Score
# ---------------------------------------------------------------------------

class TestAdjustedRSScore:
    def test_adjusted_score_tier3_cap(self, analyzer: VolumeAnalyzer) -> None:
        """Tier 3 → capped at 70 regardless of raw score."""
        result = analyzer.calculate_adjusted_rs_score(
            rs_composite=Decimal("90"),
            vol_multiplier=Decimal("1.15"),
            liquidity_tier=3,
        )
        assert result <= Decimal("70")

    def test_adjusted_score_tier1_no_cap(self, analyzer: VolumeAnalyzer) -> None:
        """Tier 1 → no cap applied."""
        result = analyzer.calculate_adjusted_rs_score(
            rs_composite=Decimal("90"),
            vol_multiplier=Decimal("1.15"),
            liquidity_tier=1,
        )
        # 90 * 1.15 = 103.50
        assert result == Decimal("103.50")

    def test_adjusted_score_decimal_precision(self, analyzer: VolumeAnalyzer) -> None:
        """Verify Decimal precision is maintained."""
        result = analyzer.calculate_adjusted_rs_score(
            rs_composite=Decimal("75.55"),
            vol_multiplier=Decimal("1.075"),
            liquidity_tier=2,
        )
        expected = Decimal("81.22")  # 75.55 * 1.075 = 81.21625 → rounds to 81.22
        assert result == expected

    def test_adjusted_score_tier3_below_70(self, analyzer: VolumeAnalyzer) -> None:
        """Tier 3 with score already below 70 → no change from cap."""
        result = analyzer.calculate_adjusted_rs_score(
            rs_composite=Decimal("50"),
            vol_multiplier=Decimal("1.0"),
            liquidity_tier=3,
        )
        assert result == Decimal("50.00")
