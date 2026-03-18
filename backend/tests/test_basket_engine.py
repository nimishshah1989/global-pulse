"""Tests for the BasketEngine."""

from __future__ import annotations
import datetime
from decimal import Decimal

import pytest

from engine.basket_engine import BasketEngine


@pytest.fixture
def engine() -> BasketEngine:
    """Create a fresh BasketEngine instance."""
    return BasketEngine()


def _make_prices(
    closes: list[float], start_date: datetime.date | None = None
) -> list[dict]:
    """Build a price list from a sequence of close values."""
    base = start_date or datetime.date(2026, 1, 1)
    return [
        {"date": base + datetime.timedelta(days=i), "close": c}
        for i, c in enumerate(closes)
    ]


class TestNAV:
    """Tests for compute_nav."""

    def test_nav_starts_at_100(self, engine: BasketEngine) -> None:
        """NAV on the first day should be Decimal('100')."""
        positions = [{"instrument_id": "A", "weight": "1.0"}]
        prices = {"A": _make_prices([100.0, 101.0, 102.0])}
        start = datetime.date(2026, 1, 1)
        nav = engine.compute_nav(positions, prices, start)
        assert len(nav) > 0
        assert nav[0]["nav"] == Decimal("100")

    def test_nav_increases_with_positive_returns(
        self, engine: BasketEngine
    ) -> None:
        """NAV should increase when underlying prices go up."""
        positions = [{"instrument_id": "A", "weight": "1.0"}]
        prices = {"A": _make_prices([100.0, 110.0, 121.0])}
        start = datetime.date(2026, 1, 1)
        nav = engine.compute_nav(positions, prices, start)
        assert nav[-1]["nav"] > Decimal("100")

    def test_nav_decreases_with_negative_returns(
        self, engine: BasketEngine
    ) -> None:
        """NAV should decrease when underlying prices go down."""
        positions = [{"instrument_id": "A", "weight": "1.0"}]
        prices = {"A": _make_prices([100.0, 90.0, 81.0])}
        start = datetime.date(2026, 1, 1)
        nav = engine.compute_nav(positions, prices, start)
        assert nav[-1]["nav"] < Decimal("100")

    def test_nav_with_multiple_positions(
        self, engine: BasketEngine
    ) -> None:
        """NAV with two equal-weight positions averages their returns."""
        positions = [
            {"instrument_id": "A", "weight": "0.5"},
            {"instrument_id": "B", "weight": "0.5"},
        ]
        prices = {
            "A": _make_prices([100.0, 110.0]),  # +10%
            "B": _make_prices([100.0, 90.0]),   # -10%
        }
        start = datetime.date(2026, 1, 1)
        nav = engine.compute_nav(positions, prices, start)
        # 0.5 * 10% + 0.5 * -10% = 0% => NAV stays at 100
        assert nav[-1]["nav"] == Decimal("100")

    def test_nav_empty_positions(self, engine: BasketEngine) -> None:
        """Empty positions list returns empty NAV."""
        nav = engine.compute_nav([], {}, datetime.date(2026, 1, 1))
        assert nav == []


class TestRebalanceWeights:
    """Tests for rebalance_weights."""

    def test_equal_weights_sum_to_one(self, engine: BasketEngine) -> None:
        """Equal weighting: all weights = 1/N, sum = Decimal('1')."""
        positions = [
            {"instrument_id": "A", "weight": Decimal("0")},
            {"instrument_id": "B", "weight": Decimal("0")},
            {"instrument_id": "C", "weight": Decimal("0")},
        ]
        result = engine.rebalance_weights(positions, "equal")
        total = sum(p["weight"] for p in result)
        assert total == Decimal("1")
        # Each should be close to 1/3
        for p in result:
            assert Decimal("0.3") <= p["weight"] <= Decimal("0.4")

    def test_rs_weighted_proportional(self, engine: BasketEngine) -> None:
        """RS-weighted: higher RS score gets higher weight."""
        positions = [
            {"instrument_id": "A", "weight": Decimal("0.5")},
            {"instrument_id": "B", "weight": Decimal("0.5")},
        ]
        rs_scores = {
            "A": Decimal("80"),
            "B": Decimal("20"),
        }
        result = engine.rebalance_weights(
            positions, "rs_weighted", rs_scores
        )
        assert result[0]["weight"] > result[1]["weight"]
        total = sum(p["weight"] for p in result)
        assert total == Decimal("1")

    def test_manual_keeps_existing_weights(
        self, engine: BasketEngine
    ) -> None:
        """Manual method should not change weights."""
        positions = [
            {"instrument_id": "A", "weight": Decimal("0.7")},
            {"instrument_id": "B", "weight": Decimal("0.3")},
        ]
        result = engine.rebalance_weights(positions, "manual")
        assert result[0]["weight"] == Decimal("0.7")
        assert result[1]["weight"] == Decimal("0.3")

    def test_empty_positions_rebalance(
        self, engine: BasketEngine
    ) -> None:
        """Empty positions list returns empty list."""
        result = engine.rebalance_weights([], "equal")
        assert result == []


class TestPerformanceMetrics:
    """Tests for compute_performance."""

    def test_max_drawdown_calculation(self, engine: BasketEngine) -> None:
        """Known drawdown sequence: 100 -> 120 -> 90 = 25% drawdown."""
        nav_history = [
            {"date": datetime.date(2026, 1, 1), "nav": Decimal("100"),
             "benchmark_nav": Decimal("100")},
            {"date": datetime.date(2026, 1, 2), "nav": Decimal("120"),
             "benchmark_nav": Decimal("105")},
            {"date": datetime.date(2026, 1, 3), "nav": Decimal("90"),
             "benchmark_nav": Decimal("103")},
        ]
        perf = engine.compute_performance(nav_history)
        # Max drawdown = (120 - 90) / 120 = 0.25
        assert perf["max_drawdown"] == Decimal("0.250000")

    def test_cumulative_return_calculation(
        self, engine: BasketEngine
    ) -> None:
        """NAV from 100 to 115 = 15% cumulative return."""
        nav_history = [
            {"date": datetime.date(2026, 1, 1), "nav": Decimal("100"),
             "benchmark_nav": Decimal("100")},
            {"date": datetime.date(2026, 1, 2), "nav": Decimal("115"),
             "benchmark_nav": Decimal("105")},
        ]
        perf = engine.compute_performance(nav_history)
        assert perf["cumulative_return"] == Decimal("0.150000")

    def test_empty_nav_history(self, engine: BasketEngine) -> None:
        """Empty NAV history returns zeroed metrics."""
        perf = engine.compute_performance([])
        assert perf["cumulative_return"] == Decimal("0")
        assert perf["max_drawdown"] == Decimal("0")
        assert perf["cagr"] is None

    def test_sharpe_ratio_computed(self, engine: BasketEngine) -> None:
        """Sharpe ratio should be computed when enough data exists."""
        nav_history = [
            {"date": datetime.date(2026, 1, d), "nav": Decimal(str(100 + d)),
             "benchmark_nav": Decimal(str(100 + d * 0.5))}
            for d in range(1, 32)
        ]
        perf = engine.compute_performance(nav_history)
        assert perf["sharpe_ratio"] is not None
        assert isinstance(perf["sharpe_ratio"], Decimal)


class TestContributions:
    """Tests for compute_contributions."""

    def test_contributions_sum(self, engine: BasketEngine) -> None:
        """Sum of contributions should approximate total basket return."""
        positions = [
            {"instrument_id": "A", "name": "Stock A", "weight": Decimal("0.5")},
            {"instrument_id": "B", "name": "Stock B", "weight": Decimal("0.5")},
        ]
        prices = {
            "A": _make_prices([100.0, 120.0]),  # +20%
            "B": _make_prices([100.0, 80.0]),   # -20%
        }
        contributions = engine.compute_contributions(positions, prices)
        total_contrib = sum(c["contribution"] for c in contributions)
        # 0.5 * 0.2 + 0.5 * (-0.2) = 0
        assert total_contrib == Decimal("0")

    def test_contributions_sorted(self, engine: BasketEngine) -> None:
        """Contributions should be sorted descending."""
        positions = [
            {"instrument_id": "A", "name": "A", "weight": Decimal("0.5")},
            {"instrument_id": "B", "name": "B", "weight": Decimal("0.5")},
        ]
        prices = {
            "A": _make_prices([100.0, 80.0]),   # -20%, contrib = -0.1
            "B": _make_prices([100.0, 130.0]),  # +30%, contrib = +0.15
        }
        contributions = engine.compute_contributions(positions, prices)
        assert contributions[0]["contribution"] > contributions[1]["contribution"]


class TestDecimalPrecision:
    """Verify all metrics are Decimal, not float."""

    def test_all_decimal_precision(self, engine: BasketEngine) -> None:
        """Every metric returned by compute_performance must be Decimal."""
        nav_history = [
            {"date": datetime.date(2026, 1, d), "nav": Decimal(str(100 + d)),
             "benchmark_nav": Decimal(str(100 + d * 0.5))}
            for d in range(1, 32)
        ]
        perf = engine.compute_performance(nav_history)

        assert isinstance(perf["cumulative_return"], Decimal)
        assert isinstance(perf["max_drawdown"], Decimal)
        if perf["sharpe_ratio"] is not None:
            assert isinstance(perf["sharpe_ratio"], Decimal)
        if perf["cagr"] is not None:
            assert isinstance(perf["cagr"], Decimal)

    def test_nav_values_are_decimal(self, engine: BasketEngine) -> None:
        """NAV values should be Decimal."""
        positions = [{"instrument_id": "A", "weight": "1.0"}]
        prices = {"A": _make_prices([100.0, 110.0])}
        nav = engine.compute_nav(
            positions, prices, datetime.date(2026, 1, 1)
        )
        for point in nav:
            assert isinstance(point["nav"], Decimal)

    def test_contribution_values_are_decimal(
        self, engine: BasketEngine
    ) -> None:
        """Contribution values should be Decimal."""
        positions = [
            {"instrument_id": "A", "name": "A", "weight": Decimal("1.0")},
        ]
        prices = {"A": _make_prices([100.0, 110.0])}
        contribs = engine.compute_contributions(positions, prices)
        for c in contribs:
            assert isinstance(c["weight"], Decimal)
            assert isinstance(c["return"], Decimal)
            assert isinstance(c["contribution"], Decimal)
