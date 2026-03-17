"""Tests for the OpportunityScanner engine."""

from decimal import Decimal

import pytest

from engine.opportunity_scanner import OpportunityScanner


@pytest.fixture
def scanner() -> OpportunityScanner:
    """Create a fresh scanner instance."""
    return OpportunityScanner()


class TestQuadrantEntryDetection:
    """Tests for scan_quadrant_entries."""

    def test_quadrant_entry_detection(self, scanner: OpportunityScanner) -> None:
        """Instrument changes from LAGGING to LEADING produces a signal."""
        previous = [
            {"instrument_id": "XLK_US", "quadrant": "LAGGING",
             "adjusted_rs_score": "60", "rs_momentum": "5"},
        ]
        current = [
            {"instrument_id": "XLK_US", "quadrant": "LEADING",
             "adjusted_rs_score": "65.50", "rs_momentum": "10.20"},
        ]
        signals = scanner.scan_quadrant_entries(current, previous)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "quadrant_entry_leading"
        assert signals[0]["instrument_id"] == "XLK_US"

    def test_no_signal_when_quadrant_unchanged(
        self, scanner: OpportunityScanner
    ) -> None:
        """No signal when quadrant stays the same."""
        previous = [
            {"instrument_id": "XLK_US", "quadrant": "LEADING",
             "adjusted_rs_score": "70", "rs_momentum": "5"},
        ]
        current = [
            {"instrument_id": "XLK_US", "quadrant": "LEADING",
             "adjusted_rs_score": "72", "rs_momentum": "6"},
        ]
        signals = scanner.scan_quadrant_entries(current, previous)
        assert len(signals) == 0

    def test_improving_entry_produces_signal(
        self, scanner: OpportunityScanner
    ) -> None:
        """Entry into IMPROVING quadrant produces a signal."""
        previous = [
            {"instrument_id": "EWZ_US", "quadrant": "LAGGING",
             "adjusted_rs_score": "40", "rs_momentum": "-5"},
        ]
        current = [
            {"instrument_id": "EWZ_US", "quadrant": "IMPROVING",
             "adjusted_rs_score": "45", "rs_momentum": "3"},
        ]
        signals = scanner.scan_quadrant_entries(current, previous)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "quadrant_entry_improving"


class TestVolumeBreakout:
    """Tests for scan_volume_breakouts."""

    def test_volume_breakout_detection(
        self, scanner: OpportunityScanner
    ) -> None:
        """Positive momentum + volume_ratio > 1.5 produces a signal."""
        scores = [
            {"instrument_id": "INDA_US", "rs_momentum": "5.20",
             "volume_ratio": "1.80", "adjusted_rs_score": "74.25"},
        ]
        signals = scanner.scan_volume_breakouts(scores)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "volume_breakout"

    def test_no_breakout_with_negative_momentum(
        self, scanner: OpportunityScanner
    ) -> None:
        """Negative momentum should not trigger volume breakout."""
        scores = [
            {"instrument_id": "INDA_US", "rs_momentum": "-2.00",
             "volume_ratio": "1.80", "adjusted_rs_score": "74.25"},
        ]
        signals = scanner.scan_volume_breakouts(scores)
        assert len(signals) == 0

    def test_no_breakout_with_low_volume(
        self, scanner: OpportunityScanner
    ) -> None:
        """Volume ratio <= 1.5 should not trigger breakout."""
        scores = [
            {"instrument_id": "INDA_US", "rs_momentum": "5.00",
             "volume_ratio": "1.20", "adjusted_rs_score": "74.25"},
        ]
        signals = scanner.scan_volume_breakouts(scores)
        assert len(signals) == 0


class TestMultiLevelAlignment:
    """Tests for scan_multi_level_alignments."""

    def test_multi_level_alignment(
        self, scanner: OpportunityScanner
    ) -> None:
        """Country + sector + stock all LEADING produces a signal."""
        country_scores = [
            {"instrument_id": "NIFTY50_IN", "quadrant": "LEADING",
             "adjusted_rs_score": "75.00", "country": "IN", "name": "India"},
        ]
        sector_scores = [
            {"instrument_id": "NIFTYMETAL_IN", "quadrant": "LEADING",
             "adjusted_rs_score": "80.00", "country": "IN",
             "sector": "metal", "name": "NIFTY Metal"},
        ]
        stock_scores = [
            {"instrument_id": "TATASTEEL_IN", "quadrant": "LEADING",
             "adjusted_rs_score": "72.40", "country": "IN",
             "sector": "metal", "name": "Tata Steel"},
        ]
        signals = scanner.scan_multi_level_alignments(
            country_scores, sector_scores, stock_scores
        )
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "multi_level_alignment"
        assert signals[0]["conviction_score"] == Decimal("72.40")

    def test_multi_level_alignment_partial(
        self, scanner: OpportunityScanner
    ) -> None:
        """Only 2 of 3 levels LEADING produces no signal."""
        country_scores = [
            {"instrument_id": "NIFTY50_IN", "quadrant": "LEADING",
             "adjusted_rs_score": "75.00", "country": "IN", "name": "India"},
        ]
        sector_scores = [
            {"instrument_id": "NIFTYMETAL_IN", "quadrant": "WEAKENING",
             "adjusted_rs_score": "60.00", "country": "IN",
             "sector": "metal", "name": "NIFTY Metal"},
        ]
        stock_scores = [
            {"instrument_id": "TATASTEEL_IN", "quadrant": "LEADING",
             "adjusted_rs_score": "72.40", "country": "IN",
             "sector": "metal", "name": "Tata Steel"},
        ]
        signals = scanner.scan_multi_level_alignments(
            country_scores, sector_scores, stock_scores
        )
        assert len(signals) == 0


class TestExtensionAlert:
    """Tests for scan_extension_alerts."""

    def test_extension_alert(self, scanner: OpportunityScanner) -> None:
        """Extension warning True produces a signal."""
        scores = [
            {"instrument_id": "XLK_US", "extension_warning": True,
             "adjusted_rs_score": "88.50",
             "rs_pct_3m": "97.20", "rs_pct_6m": "96.80", "rs_pct_12m": "93.10"},
        ]
        signals = scanner.scan_extension_alerts(scores)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "extension_alert"

    def test_no_extension_when_not_flagged(
        self, scanner: OpportunityScanner
    ) -> None:
        """Extension warning False produces no signal."""
        scores = [
            {"instrument_id": "XLK_US", "extension_warning": False,
             "adjusted_rs_score": "60.00",
             "rs_pct_3m": "70", "rs_pct_6m": "65", "rs_pct_12m": "60"},
        ]
        signals = scanner.scan_extension_alerts(scores)
        assert len(signals) == 0


class TestRegimeChange:
    """Tests for scan_regime_changes."""

    def test_regime_change_risk_off(
        self, scanner: OpportunityScanner
    ) -> None:
        """RISK_ON to RISK_OFF produces a signal."""
        signals = scanner.scan_regime_changes("RISK_OFF", "RISK_ON")
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "regime_change"
        assert "RISK_OFF" in signals[0]["description"]
        assert signals[0]["conviction_score"] == Decimal("95.00")

    def test_regime_change_risk_on(
        self, scanner: OpportunityScanner
    ) -> None:
        """RISK_OFF to RISK_ON produces a signal."""
        signals = scanner.scan_regime_changes("RISK_ON", "RISK_OFF")
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "regime_change"

    def test_no_regime_change(self, scanner: OpportunityScanner) -> None:
        """Same regime produces no signal."""
        signals = scanner.scan_regime_changes("RISK_ON", "RISK_ON")
        assert len(signals) == 0


class TestConvictionScoreRange:
    """Verify all conviction scores are Decimal in [0, 100]."""

    def test_conviction_score_range(
        self, scanner: OpportunityScanner
    ) -> None:
        """All emitted signals should have conviction_score in [0, 100]."""
        current = [
            {"instrument_id": "XLK_US", "quadrant": "LEADING",
             "adjusted_rs_score": "82.15", "rs_momentum": "8.40",
             "volume_ratio": "1.80", "extension_warning": True,
             "rs_pct_3m": "97", "rs_pct_6m": "96", "rs_pct_12m": "93"},
        ]
        previous = [
            {"instrument_id": "XLK_US", "quadrant": "LAGGING",
             "adjusted_rs_score": "40", "rs_momentum": "-5"},
        ]
        signals = scanner.scan_quadrant_entries(current, previous)
        signals += scanner.scan_volume_breakouts(current)
        signals += scanner.scan_extension_alerts(current)
        signals += scanner.scan_regime_changes("RISK_OFF", "RISK_ON")

        for signal in signals:
            score = signal["conviction_score"]
            assert isinstance(score, Decimal), (
                f"conviction_score should be Decimal, got {type(score)}"
            )
            assert Decimal("0") <= score <= Decimal("100"), (
                f"conviction_score {score} out of [0, 100] range"
            )


class TestFullScan:
    """Tests for run_full_scan."""

    def test_full_scan_returns_sorted(
        self, scanner: OpportunityScanner
    ) -> None:
        """Full scan results should be sorted by conviction_score desc."""
        current = [
            {"instrument_id": "XLK_US", "quadrant": "LEADING",
             "adjusted_rs_score": "82.15", "rs_momentum": "8.40",
             "volume_ratio": "1.80", "extension_warning": False,
             "rs_pct_3m": "70", "rs_pct_6m": "65", "rs_pct_12m": "60"},
            {"instrument_id": "EWJ_US", "quadrant": "IMPROVING",
             "adjusted_rs_score": "45", "rs_momentum": "3",
             "volume_ratio": "1.1", "extension_warning": False,
             "rs_pct_3m": "50", "rs_pct_6m": "50", "rs_pct_12m": "50"},
        ]
        previous = [
            {"instrument_id": "XLK_US", "quadrant": "LAGGING",
             "adjusted_rs_score": "40", "rs_momentum": "-5"},
            {"instrument_id": "EWJ_US", "quadrant": "LAGGING",
             "adjusted_rs_score": "30", "rs_momentum": "-10"},
        ]
        signals = scanner.run_full_scan(
            current_scores=current,
            previous_scores=previous,
            country_scores=[],
            sector_scores=[],
            stock_scores=[],
            prices={},
            rs_lines={},
            current_regime="RISK_OFF",
            previous_regime="RISK_ON",
        )
        assert len(signals) > 0
        conviction_scores = [s["conviction_score"] for s in signals]
        assert conviction_scores == sorted(conviction_scores, reverse=True)
