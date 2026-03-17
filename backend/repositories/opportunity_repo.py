"""Opportunity repository — in-memory mock data for opportunity signals.

Generates realistic opportunity signals until backed by a real database.
Pre-populated with representative samples of each signal type.
"""

import datetime
import uuid
from typing import Any


def _make_opportunity(
    instrument_id: str,
    signal_type: str,
    conviction_score: float,
    description: str,
    metadata: dict[str, Any] | None = None,
    days_ago: int = 0,
) -> dict[str, Any]:
    """Build a single opportunity dict with auto-generated id and timestamps."""
    today = datetime.date(2026, 3, 17)
    signal_date = today - datetime.timedelta(days=days_ago)
    return {
        "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"{instrument_id}-{signal_type}-{days_ago}"),
        "instrument_id": instrument_id,
        "date": signal_date,
        "signal_type": signal_type,
        "conviction_score": conviction_score,
        "description": description,
        "metadata": metadata or {},
        "created_at": datetime.datetime(
            signal_date.year, signal_date.month, signal_date.day,
            2, 0, 0, tzinfo=datetime.timezone.utc,
        ),
    }


def _build_mock_opportunities() -> list[dict[str, Any]]:
    """Create a pre-populated set of realistic mock opportunities."""
    return [
        # 3 quadrant_entry_leading signals
        _make_opportunity(
            "EWJ_US", "quadrant_entry_leading", 78.50,
            "EWJ_US entered LEADING quadrant (from IMPROVING)",
            {"previous_quadrant": "IMPROVING", "current_quadrant": "LEADING",
             "adjusted_rs_score": "78.50", "rs_momentum": "12.30"},
            days_ago=0,
        ),
        _make_opportunity(
            "XLK_US", "quadrant_entry_leading", 82.15,
            "XLK_US entered LEADING quadrant (from WEAKENING)",
            {"previous_quadrant": "WEAKENING", "current_quadrant": "LEADING",
             "adjusted_rs_score": "82.15", "rs_momentum": "8.40"},
            days_ago=1,
        ),
        _make_opportunity(
            "EWT_US", "quadrant_entry_leading", 71.30,
            "EWT_US entered LEADING quadrant (from IMPROVING)",
            {"previous_quadrant": "IMPROVING", "current_quadrant": "LEADING",
             "adjusted_rs_score": "71.30", "rs_momentum": "15.60"},
            days_ago=2,
        ),
        # 2 volume_breakout signals
        _make_opportunity(
            "INDA_US", "volume_breakout", 74.25,
            "INDA_US RS turning positive with volume 1.8x average",
            {"rs_momentum": "5.20", "volume_ratio": "1.800",
             "adjusted_rs_score": "74.25"},
            days_ago=0,
        ),
        _make_opportunity(
            "XLE_US", "volume_breakout", 68.90,
            "XLE_US RS turning positive with volume 1.6x average",
            {"rs_momentum": "3.10", "volume_ratio": "1.600",
             "adjusted_rs_score": "68.90"},
            days_ago=1,
        ),
        # 1 multi_level_alignment (India -> NIFTY Metal -> Tata Steel)
        _make_opportunity(
            "TATASTEEL_IN", "multi_level_alignment", 72.40,
            "India LEADING globally -> NIFTY Metal LEADING in India -> "
            "Tata Steel LEADING in NIFTY Metal",
            {
                "country_id": "NIFTY50_IN",
                "country_name": "India",
                "country_quadrant": "LEADING",
                "sector_id": "NIFTYMETAL_IN",
                "sector_name": "NIFTY Metal",
                "sector_quadrant": "LEADING",
                "stock_id": "TATASTEEL_IN",
                "stock_name": "Tata Steel",
                "stock_quadrant": "LEADING",
            },
            days_ago=0,
        ),
        # 1 regime_change
        _make_opportunity(
            "ACWI_US", "regime_change", 95.00,
            "Global regime changed to RISK_OFF — ACWI crossed below 200-day MA",
            {"previous_regime": "RISK_ON", "current_regime": "RISK_OFF"},
            days_ago=5,
        ),
        # 2 extension_alerts
        _make_opportunity(
            "XLK_US", "extension_alert", 88.50,
            "XLK_US extended — RS in top 5% across all timeframes",
            {"rs_pct_3m": "97.20", "rs_pct_6m": "96.80", "rs_pct_12m": "93.10"},
            days_ago=0,
        ),
        _make_opportunity(
            "EWJ_US", "extension_alert", 79.00,
            "EWJ_US extended — RS in top 5% across all timeframes",
            {"rs_pct_3m": "96.50", "rs_pct_6m": "95.30", "rs_pct_12m": "91.40"},
            days_ago=1,
        ),
    ]


class OpportunityRepository:
    """In-memory repository for opportunity signals."""

    def __init__(self) -> None:
        """Initialize with pre-populated mock opportunities."""
        self._opportunities: list[dict[str, Any]] = _build_mock_opportunities()

    async def get_latest(
        self,
        limit: int = 50,
        signal_type: str | None = None,
        min_conviction: float | None = None,
        hierarchy_level: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve latest opportunity signals with optional filters.

        Args:
            limit: Maximum number of results to return.
            signal_type: Filter by signal type string.
            min_conviction: Minimum conviction score threshold.
            hierarchy_level: Filter by instrument hierarchy level
                (not enforced in mock — included for interface compliance).

        Returns:
            List of opportunity dicts sorted by date desc, then conviction desc.
        """
        results = list(self._opportunities)

        if signal_type is not None:
            results = [o for o in results if o["signal_type"] == signal_type]

        if min_conviction is not None:
            results = [
                o for o in results if o["conviction_score"] >= min_conviction
            ]

        results.sort(
            key=lambda o: (o["date"], o["conviction_score"]),
            reverse=True,
        )

        return results[:limit]

    async def get_multi_level_alignments(
        self, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Retrieve only multi-level alignment signals.

        Args:
            limit: Maximum number of results.

        Returns:
            List of multi_level_alignment opportunity dicts.
        """
        results = [
            o for o in self._opportunities
            if o["signal_type"] == "multi_level_alignment"
        ]
        results.sort(
            key=lambda o: o["conviction_score"], reverse=True
        )
        return results[:limit]

    async def create(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """Persist a new opportunity signal.

        Args:
            opportunity: Opportunity dict (id and created_at are auto-set
                if missing).

        Returns:
            The stored opportunity dict with all fields populated.
        """
        if "id" not in opportunity:
            opportunity["id"] = uuid.uuid4()
        if "created_at" not in opportunity:
            opportunity["created_at"] = datetime.datetime.now(
                tz=datetime.timezone.utc
            )
        self._opportunities.append(opportunity)
        return opportunity
