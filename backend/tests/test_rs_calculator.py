"""Tests for RS Calculator — every stage tested independently.

All assertions use Decimal comparisons. Helper functions generate
sample Polars DataFrames for reproducible tests.
"""

from datetime import date, timedelta
from decimal import Decimal

import polars as pl
import pytest

from engine.rs_calculator import RSCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_price_df(
    prices: list[float],
    start_date: date = date(2024, 1, 2),
) -> pl.DataFrame:
    """Create a simple [date, close] DataFrame from a list of prices."""
    dates = [start_date + timedelta(days=i) for i in range(len(prices))]
    return pl.DataFrame({"date": dates, "close": prices}).cast(
        {"date": pl.Date, "close": pl.Float64}
    )


def make_constant_price_df(
    price: float,
    n: int,
    start_date: date = date(2024, 1, 2),
) -> pl.DataFrame:
    """Create a constant-price DataFrame with n rows."""
    return make_price_df([price] * n, start_date)


@pytest.fixture
def calc() -> RSCalculator:
    return RSCalculator()


# ---------------------------------------------------------------------------
# Stage 1: RS Line
# ---------------------------------------------------------------------------

class TestRSLine:
    def test_rs_line_basic(self, calc: RSCalculator) -> None:
        """Known prices produce expected RS line values."""
        asset = make_price_df([100.0, 110.0, 120.0])
        bench = make_price_df([100.0, 100.0, 100.0])
        result = calc.calculate_rs_line(asset, bench)

        assert result.height == 3
        # First value normalized to 100
        assert Decimal(str(result["rs_line"][0])) == Decimal("100")
        # Asset doubled relative performance vs flat bench
        assert Decimal(str(round(result["rs_line"][1], 4))) == Decimal("110.0")
        assert Decimal(str(round(result["rs_line"][2], 4))) == Decimal("120.0")

    def test_rs_line_equal_prices(self, calc: RSCalculator) -> None:
        """Same prices for asset and benchmark → RS line stays at 100."""
        prices = make_price_df([50.0, 55.0, 60.0, 58.0])
        result = calc.calculate_rs_line(prices, prices)

        for val in result["rs_line"].to_list():
            assert abs(Decimal(str(val)) - Decimal("100")) < Decimal("0.01")

    def test_rs_line_outperforming(self, calc: RSCalculator) -> None:
        """Asset going up, benchmark flat → RS line rises."""
        asset = make_price_df([100.0, 105.0, 110.0, 120.0])
        bench = make_price_df([100.0, 100.0, 100.0, 100.0])
        result = calc.calculate_rs_line(asset, bench)

        values = result["rs_line"].to_list()
        assert values[-1] > values[0]

    def test_rs_line_empty_join(self, calc: RSCalculator) -> None:
        """Non-overlapping dates → empty result."""
        asset = make_price_df([100.0], start_date=date(2024, 1, 1))
        bench = make_price_df([100.0], start_date=date(2025, 1, 1))
        result = calc.calculate_rs_line(asset, bench)
        assert result.height == 0


# ---------------------------------------------------------------------------
# Stage 2: RS Trend
# ---------------------------------------------------------------------------

class TestRSTrend:
    def test_rs_trend_above_ma(self, calc: RSCalculator) -> None:
        """RS line consistently above SMA → OUTPERFORMING."""
        # Build rising RS line with 160 points, use short MA for testability
        values = [100.0 + i * 0.5 for i in range(160)]
        rs_df = make_price_df(values)
        rs_df = rs_df.rename({"close": "rs_line"})

        # Use ma_period=5 for this test so we get results
        result = calc.calculate_rs_trend(rs_df, ma_period=5)
        # Last value should be OUTPERFORMING (rising line above its MA)
        last_trend = result["rs_trend"][-1]
        assert last_trend == "OUTPERFORMING"

    def test_rs_trend_below_ma(self, calc: RSCalculator) -> None:
        """RS line below SMA → UNDERPERFORMING."""
        # Build declining RS line
        values = [200.0 - i * 0.5 for i in range(160)]
        rs_df = make_price_df(values)
        rs_df = rs_df.rename({"close": "rs_line"})

        result = calc.calculate_rs_trend(rs_df, ma_period=5)
        last_trend = result["rs_trend"][-1]
        assert last_trend == "UNDERPERFORMING"

    def test_rs_trend_insufficient_data(self, calc: RSCalculator) -> None:
        """Fewer rows than MA period → trend is None."""
        rs_df = pl.DataFrame({
            "date": [date(2024, 1, i + 1) for i in range(3)],
            "rs_line": [100.0, 101.0, 102.0],
        }).cast({"date": pl.Date})

        result = calc.calculate_rs_trend(rs_df, ma_period=5)
        for trend in result["rs_trend"].to_list():
            assert trend is None


# ---------------------------------------------------------------------------
# Stage 3: Excess Returns & Percentile Rank
# ---------------------------------------------------------------------------

class TestExcessReturns:
    def test_excess_returns_positive(self, calc: RSCalculator) -> None:
        """Asset beats benchmark → positive excess return."""
        n = TRADING_DAYS_1M + 1
        asset = make_price_df([100.0] + [100.0] * (n - 2) + [120.0])
        bench = make_price_df([100.0] + [100.0] * (n - 2) + [105.0])
        er = calc.calculate_excess_returns(asset, bench)

        assert "1M" in er
        assert er["1M"] > Decimal("0")

    def test_excess_returns_negative(self, calc: RSCalculator) -> None:
        """Asset trails benchmark → negative excess return."""
        n = TRADING_DAYS_1M + 1
        asset = make_price_df([100.0] + [100.0] * (n - 2) + [95.0])
        bench = make_price_df([100.0] + [100.0] * (n - 2) + [110.0])
        er = calc.calculate_excess_returns(asset, bench)

        assert "1M" in er
        assert er["1M"] < Decimal("0")

    def test_excess_returns_insufficient_data(self, calc: RSCalculator) -> None:
        """Too few data points → timeframe omitted from results."""
        asset = make_price_df([100.0, 110.0])
        bench = make_price_df([100.0, 105.0])
        er = calc.calculate_excess_returns(asset, bench)
        assert "1M" not in er


class TestPercentileRank:
    def test_percentile_rank_best(self, calc: RSCalculator) -> None:
        """Highest returns in group → percentile = 100."""
        peers = [Decimal("0.01"), Decimal("0.05"), Decimal("0.10"), Decimal("0.20")]
        rank = calc.calculate_percentile_rank(Decimal("0.20"), peers)
        assert rank == Decimal("100.00")

    def test_percentile_rank_worst(self, calc: RSCalculator) -> None:
        """Lowest returns in group → percentile = 0."""
        peers = [Decimal("0.01"), Decimal("0.05"), Decimal("0.10"), Decimal("0.20")]
        rank = calc.calculate_percentile_rank(Decimal("0.01"), peers)
        assert rank == Decimal("0.00")

    def test_percentile_rank_median(self, calc: RSCalculator) -> None:
        """Middle returns in a 5-element group → percentile = 50."""
        peers = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("5")]
        rank = calc.calculate_percentile_rank(Decimal("3"), peers)
        assert rank == Decimal("50.00")

    def test_percentile_rank_single_element(self, calc: RSCalculator) -> None:
        """Single-element peer group → returns 50."""
        rank = calc.calculate_percentile_rank(Decimal("0.10"), [Decimal("0.10")])
        assert rank == Decimal("50")


# ---------------------------------------------------------------------------
# Stage 4: Composite
# ---------------------------------------------------------------------------

# Import constants for reference
from engine.rs_calculator import TRADING_DAYS_1M


class TestComposite:
    def test_composite_weights_sum(self) -> None:
        """Weights 0.10 + 0.25 + 0.35 + 0.30 = 1.0."""
        from engine.rs_calculator import WEIGHT_1M, WEIGHT_3M, WEIGHT_6M, WEIGHT_12M
        assert WEIGHT_1M + WEIGHT_3M + WEIGHT_6M + WEIGHT_12M == Decimal("1.00")

    def test_composite_all_100(self, calc: RSCalculator) -> None:
        """All percentiles 100 → composite = 100."""
        result = calc.calculate_composite(
            Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100")
        )
        assert result == Decimal("100.00")

    def test_composite_all_0(self, calc: RSCalculator) -> None:
        """All percentiles 0 → composite = 0."""
        result = calc.calculate_composite(
            Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")
        )
        assert result == Decimal("0.00")

    def test_composite_mixed(self, calc: RSCalculator) -> None:
        """Known percentiles produce exact known composite."""
        # 80*0.10 + 60*0.25 + 40*0.35 + 20*0.30
        # = 8.0 + 15.0 + 14.0 + 6.0 = 43.0
        result = calc.calculate_composite(
            Decimal("80"), Decimal("60"), Decimal("40"), Decimal("20")
        )
        assert result == Decimal("43.00")


# ---------------------------------------------------------------------------
# Stage 5: Momentum
# ---------------------------------------------------------------------------

class TestMomentum:
    def test_momentum_positive(self, calc: RSCalculator) -> None:
        """Improving RS → positive momentum."""
        n = 30
        values = [float(50 + i) for i in range(n)]
        df = pl.DataFrame({
            "date": [date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
            "rs_composite": values,
        }).cast({"date": pl.Date})

        result = calc.calculate_momentum(df, lookback=20)
        last_mom = result["rs_momentum"][-1]
        assert last_mom is not None
        assert Decimal(str(last_mom)) > Decimal("0")

    def test_momentum_negative(self, calc: RSCalculator) -> None:
        """Declining RS → negative momentum."""
        n = 30
        values = [float(80 - i) for i in range(n)]
        df = pl.DataFrame({
            "date": [date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
            "rs_composite": values,
        }).cast({"date": pl.Date})

        result = calc.calculate_momentum(df, lookback=20)
        last_mom = result["rs_momentum"][-1]
        assert last_mom is not None
        assert Decimal(str(last_mom)) < Decimal("0")

    def test_momentum_clipping(self, calc: RSCalculator) -> None:
        """Extreme values clipped to [-50, 50]."""
        n = 25
        # Jump from 0 to 200 → raw momentum would be huge
        values = [0.0] * 20 + [200.0] * 5
        df = pl.DataFrame({
            "date": [date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
            "rs_composite": values,
        }).cast({"date": pl.Date})

        result = calc.calculate_momentum(df, lookback=20)
        for mom in result["rs_momentum"].to_list():
            if mom is not None:
                assert Decimal(str(mom)) <= Decimal("50")
                assert Decimal(str(mom)) >= Decimal("-50")

    def test_momentum_null_for_insufficient_lookback(self, calc: RSCalculator) -> None:
        """First `lookback` rows should have null momentum."""
        n = 25
        values = [50.0] * n
        df = pl.DataFrame({
            "date": [date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
            "rs_composite": values,
        }).cast({"date": pl.Date})

        result = calc.calculate_momentum(df, lookback=20)
        # First 20 values should be null
        for i in range(20):
            assert result["rs_momentum"][i] is None
