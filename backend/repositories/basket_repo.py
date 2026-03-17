"""Basket repository — in-memory dict-based storage for baskets.

Pre-populated with one sample basket: "Asia Momentum Leaders" containing
EWJ (Japan), EWT (Taiwan), INDA (India) with equal weights and 90 days
of mock NAV history.
"""

import datetime
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from engine.basket_engine import BasketEngine


# Fixed UUIDs for the sample basket (deterministic for testing)
SAMPLE_BASKET_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
SAMPLE_POS_EWJ = uuid.UUID("11111111-1111-1111-1111-111111111111")
SAMPLE_POS_EWT = uuid.UUID("22222222-2222-2222-2222-222222222222")
SAMPLE_POS_INDA = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _build_sample_nav(num_days: int = 90) -> list[dict[str, Any]]:
    """Generate 90 days of plausible NAV history for the sample basket."""
    nav = Decimal("100")
    bench_nav = Decimal("100")
    results: list[dict[str, Any]] = []
    base_date = datetime.date(2026, 3, 17) - datetime.timedelta(days=num_days)

    for i in range(num_days):
        d = base_date + datetime.timedelta(days=i)
        # Skip weekends
        if d.weekday() >= 5:
            continue

        # Simulate slight upward drift with small oscillation
        nav_change = Decimal(str(round(0.002 + 0.001 * (i % 7 - 3), 6)))
        bench_change = Decimal(str(round(0.001 + 0.0005 * (i % 5 - 2), 6)))

        nav = nav * (Decimal("1") + nav_change)
        nav = nav.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        bench_nav = bench_nav * (Decimal("1") + bench_change)
        bench_nav = bench_nav.quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )

        rs_line = (nav / bench_nav * Decimal("100")).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        results.append({
            "basket_id": SAMPLE_BASKET_ID,
            "date": d,
            "nav": nav,
            "benchmark_nav": bench_nav,
            "rs_line": rs_line,
        })

    return results


def _build_sample_basket() -> dict[str, Any]:
    """Create the pre-populated sample basket."""
    now = datetime.datetime(2025, 12, 17, 10, 0, 0, tzinfo=datetime.timezone.utc)
    weight = Decimal("0.333333")

    return {
        "id": SAMPLE_BASKET_ID,
        "name": "Asia Momentum Leaders",
        "description": "Leading Asian country ETFs by RS score",
        "benchmark_id": "ACWI_US",
        "created_at": now,
        "status": "active",
        "weighting_method": "equal",
        "positions": [
            {
                "id": SAMPLE_POS_EWJ,
                "basket_id": SAMPLE_BASKET_ID,
                "instrument_id": "EWJ_US",
                "weight": weight,
                "added_at": now,
                "removed_at": None,
                "status": "active",
            },
            {
                "id": SAMPLE_POS_EWT,
                "basket_id": SAMPLE_BASKET_ID,
                "instrument_id": "EWT_US",
                "weight": weight,
                "added_at": now,
                "removed_at": None,
                "status": "active",
            },
            {
                "id": SAMPLE_POS_INDA,
                "basket_id": SAMPLE_BASKET_ID,
                "instrument_id": "INDA_US",
                "weight": Decimal("0.333334"),
                "added_at": now,
                "removed_at": None,
                "status": "active",
            },
        ],
    }


class BasketRepository:
    """In-memory repository for baskets, positions, and NAV history."""

    def __init__(self) -> None:
        """Initialize with pre-populated sample basket and NAV history."""
        sample = _build_sample_basket()
        self._baskets: dict[str, dict[str, Any]] = {
            str(sample["id"]): sample,
        }
        self._nav_history: dict[str, list[dict[str, Any]]] = {
            str(SAMPLE_BASKET_ID): _build_sample_nav(),
        }
        self._engine = BasketEngine()

    async def create_basket(self, basket: dict[str, Any]) -> dict[str, Any]:
        """Create a new basket and store it.

        Args:
            basket: Dict with name, description, benchmark_id,
                weighting_method fields.

        Returns:
            Complete basket dict with generated id and timestamps.
        """
        basket_id = uuid.uuid4()
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        stored: dict[str, Any] = {
            "id": basket_id,
            "name": basket["name"],
            "description": basket.get("description"),
            "benchmark_id": basket.get("benchmark_id"),
            "created_at": now,
            "status": "active",
            "weighting_method": basket.get("weighting_method", "equal"),
            "positions": [],
        }
        self._baskets[str(basket_id)] = stored
        self._nav_history[str(basket_id)] = []
        return stored

    async def get_all_baskets(self) -> list[dict[str, Any]]:
        """Return all baskets sorted by creation date descending.

        Returns:
            List of basket dicts.
        """
        baskets = list(self._baskets.values())
        baskets.sort(key=lambda b: b["created_at"], reverse=True)
        return baskets

    async def get_basket(self, basket_id: str) -> dict[str, Any] | None:
        """Retrieve a single basket by ID.

        Args:
            basket_id: UUID string of the basket.

        Returns:
            Basket dict or None if not found.
        """
        return self._baskets.get(basket_id)

    async def add_position(
        self, basket_id: str, position: dict[str, Any]
    ) -> dict[str, Any]:
        """Add a position to an existing basket.

        Args:
            basket_id: UUID string of the basket.
            position: Dict with instrument_id and weight.

        Returns:
            Complete position dict with generated id.

        Raises:
            KeyError: If basket_id does not exist.
        """
        basket = self._baskets.get(basket_id)
        if basket is None:
            raise KeyError(f"Basket {basket_id} not found")

        pos_id = uuid.uuid4()
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        stored_pos: dict[str, Any] = {
            "id": pos_id,
            "basket_id": uuid.UUID(basket_id),
            "instrument_id": position["instrument_id"],
            "weight": Decimal(str(position["weight"])),
            "added_at": now,
            "removed_at": None,
            "status": "active",
        }
        basket["positions"].append(stored_pos)
        return stored_pos

    async def remove_position(
        self, basket_id: str, position_id: str
    ) -> bool:
        """Remove a position from a basket.

        Args:
            basket_id: UUID string of the basket.
            position_id: UUID string of the position.

        Returns:
            True if position was found and removed, False otherwise.
        """
        basket = self._baskets.get(basket_id)
        if basket is None:
            return False

        for pos in basket["positions"]:
            if str(pos["id"]) == position_id:
                pos["status"] = "removed"
                pos["removed_at"] = datetime.datetime.now(
                    tz=datetime.timezone.utc
                )
                return True

        return False

    async def get_basket_nav(
        self, basket_id: str
    ) -> list[dict[str, Any]]:
        """Retrieve NAV history for a basket.

        Args:
            basket_id: UUID string of the basket.

        Returns:
            List of NAV data point dicts, empty if basket not found.
        """
        return self._nav_history.get(basket_id, [])

    async def get_basket_performance(
        self, basket_id: str
    ) -> dict[str, Any]:
        """Compute performance metrics for a basket from its NAV history.

        Args:
            basket_id: UUID string of the basket.

        Returns:
            Dict with performance metrics. Returns zeroed metrics
            if no NAV history exists.
        """
        nav_history = self._nav_history.get(basket_id, [])
        perf = self._engine.compute_performance(nav_history)
        basket = self._baskets.get(basket_id)
        basket_uuid = uuid.UUID(basket_id) if basket else uuid.uuid4()
        perf["basket_id"] = basket_uuid
        return perf
