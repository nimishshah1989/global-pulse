"""Tests for Regime Filter — Stage 9 global risk overlay."""

from datetime import date, timedelta
from decimal import Decimal

import polars as pl
import pytest

from engine.regime_filter import calculate_regime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_price_df(
    prices: list[float],
    start_date: date = date(2023, 1, 2),
) -> pl.DataFrame:
    """Create a [date, close] DataFrame."""
    dates = [start_date + timedelta(days=i) for i in range(len(prices))]
    return pl.DataFrame({"date": dates, "close": prices}).cast(
        {"date": pl.Date, "close": pl.Float64}
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRegimeFilter:
    def test_risk_on(self) -> None:
        """Price above 200-day SMA → RISK_ON."""
        # 200 days of slowly rising prices, then a jump above
        prices = [100.0 + i * 0.1 for i in range(200)] + [150.0]
        df = make_price_df(prices)
        assert calculate_regime(df, ma_period=200) == "RISK_ON"

    def test_risk_off(self) -> None:
        """Price below 200-day SMA → RISK_OFF."""
        # 200 days of prices around 100, then a sharp drop
        prices = [100.0] * 200 + [70.0]
        df = make_price_df(prices)
        assert calculate_regime(df, ma_period=200) == "RISK_OFF"

    def test_exact_crossover(self) -> None:
        """Price exactly at SMA → RISK_ON (>= comparison)."""
        # Constant price → SMA equals price
        prices = [100.0] * 201
        df = make_price_df(prices)
        assert calculate_regime(df, ma_period=200) == "RISK_ON"

    def test_insufficient_data(self) -> None:
        """Fewer than ma_period rows → default RISK_ON."""
        prices = [100.0] * 50
        df = make_price_df(prices)
        assert calculate_regime(df, ma_period=200) == "RISK_ON"

    def test_custom_ma_period(self) -> None:
        """Custom MA period works correctly."""
        # 10 days rising then drop below
        prices = [100.0 + i for i in range(10)] + [95.0]
        df = make_price_df(prices)
        result = calculate_regime(df, ma_period=10)
        # SMA of [100,101,...,109,95] last 10 = [101,...,109,95]
        # The SMA-10 at the last point covers indices 1-10: mean of 101..109,95
        # = (101+102+103+104+105+106+107+108+109+95)/10 = 1040/10 = 104.0
        # Price 95 < 104 → RISK_OFF
        assert result == "RISK_OFF"
