"""Tests for Quadrant Classifier — Stage 7 RRG Framework."""

from decimal import Decimal

import pytest

from engine.quadrant_classifier import classify_quadrant


class TestClassifyQuadrant:
    def test_leading(self) -> None:
        """Score > 50, momentum > 0 → LEADING."""
        assert classify_quadrant(Decimal("75"), Decimal("10")) == "LEADING"

    def test_weakening(self) -> None:
        """Score > 50, momentum <= 0 → WEAKENING."""
        assert classify_quadrant(Decimal("75"), Decimal("-5")) == "WEAKENING"
        assert classify_quadrant(Decimal("75"), Decimal("0")) == "WEAKENING"

    def test_lagging(self) -> None:
        """Score <= 50, momentum <= 0 → LAGGING."""
        assert classify_quadrant(Decimal("30"), Decimal("-10")) == "LAGGING"

    def test_improving(self) -> None:
        """Score <= 50, momentum > 0 → IMPROVING."""
        assert classify_quadrant(Decimal("30"), Decimal("10")) == "IMPROVING"

    def test_boundary_score_50_momentum_0(self) -> None:
        """Edge case: score = 50, momentum = 0 → LAGGING (<=, <=)."""
        assert classify_quadrant(Decimal("50"), Decimal("0")) == "LAGGING"

    def test_boundary_score_50_momentum_positive(self) -> None:
        """Edge case: score = 50, momentum > 0 → IMPROVING (<=, >)."""
        assert classify_quadrant(Decimal("50"), Decimal("1")) == "IMPROVING"

    def test_boundary_score_51_momentum_0(self) -> None:
        """Edge case: score = 51, momentum = 0 → WEAKENING (>, <=)."""
        assert classify_quadrant(Decimal("51"), Decimal("0")) == "WEAKENING"

    def test_boundary_score_51_momentum_positive(self) -> None:
        """Edge case: score = 51, momentum > 0 → LEADING."""
        assert classify_quadrant(Decimal("51"), Decimal("0.01")) == "LEADING"
