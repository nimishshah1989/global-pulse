"""Tests for Liquidity Scorer — Stage 8 + Stage 10."""

from decimal import Decimal

import pytest

from engine.liquidity_scorer import LiquidityScorer


@pytest.fixture
def scorer() -> LiquidityScorer:
    return LiquidityScorer()


class TestLiquidityTier:
    def test_tier1_high_value(self, scorer: LiquidityScorer) -> None:
        """$10M daily → tier 1."""
        assert scorer.calculate_liquidity_tier(Decimal("10000000")) == 1

    def test_tier2_medium_value(self, scorer: LiquidityScorer) -> None:
        """$1M daily → tier 2."""
        assert scorer.calculate_liquidity_tier(Decimal("1000000")) == 2

    def test_tier3_low_value(self, scorer: LiquidityScorer) -> None:
        """$100K daily → tier 3."""
        assert scorer.calculate_liquidity_tier(Decimal("100000")) == 3

    def test_tier_boundary_5m(self, scorer: LiquidityScorer) -> None:
        """Exact $5M → tier 1."""
        assert scorer.calculate_liquidity_tier(Decimal("5000000")) == 1

    def test_tier_boundary_500k(self, scorer: LiquidityScorer) -> None:
        """Exact $500K → tier 2."""
        assert scorer.calculate_liquidity_tier(Decimal("500000")) == 2

    def test_tier_boundary_just_below_5m(self, scorer: LiquidityScorer) -> None:
        """Just below $5M → tier 2."""
        assert scorer.calculate_liquidity_tier(Decimal("4999999.99")) == 2

    def test_tier_boundary_just_below_500k(self, scorer: LiquidityScorer) -> None:
        """Just below $500K → tier 3."""
        assert scorer.calculate_liquidity_tier(Decimal("499999.99")) == 3


class TestExtensionWarning:
    def test_extension_warning_triggered(self, scorer: LiquidityScorer) -> None:
        """All above thresholds → True."""
        assert scorer.check_extension_warning(
            rs_pct_3m=Decimal("96"),
            rs_pct_6m=Decimal("96"),
            rs_pct_12m=Decimal("91"),
        ) is True

    def test_extension_warning_not_triggered_3m(self, scorer: LiquidityScorer) -> None:
        """3M below threshold → False."""
        assert scorer.check_extension_warning(
            rs_pct_3m=Decimal("94"),
            rs_pct_6m=Decimal("96"),
            rs_pct_12m=Decimal("91"),
        ) is False

    def test_extension_warning_not_triggered_6m(self, scorer: LiquidityScorer) -> None:
        """6M below threshold → False."""
        assert scorer.check_extension_warning(
            rs_pct_3m=Decimal("96"),
            rs_pct_6m=Decimal("94"),
            rs_pct_12m=Decimal("91"),
        ) is False

    def test_extension_warning_not_triggered_12m(self, scorer: LiquidityScorer) -> None:
        """12M below threshold → False."""
        assert scorer.check_extension_warning(
            rs_pct_3m=Decimal("96"),
            rs_pct_6m=Decimal("96"),
            rs_pct_12m=Decimal("89"),
        ) is False

    def test_extension_warning_at_exact_thresholds(self, scorer: LiquidityScorer) -> None:
        """At exact thresholds (95, 95, 90) → False (strict >)."""
        assert scorer.check_extension_warning(
            rs_pct_3m=Decimal("95"),
            rs_pct_6m=Decimal("95"),
            rs_pct_12m=Decimal("90"),
        ) is False
