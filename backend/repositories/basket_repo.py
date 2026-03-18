"""Basket repository — PostgreSQL persistence via SQLAlchemy async sessions.

Stores baskets, positions, and NAV history in the database using the
ORM models defined in db/models.py. Falls back to a sample basket seed
on first access if the database is empty.
"""

import datetime
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.models import Basket, BasketNAV, BasketPosition
from engine.basket_engine import BasketEngine

logger = logging.getLogger(__name__)

# Fixed UUIDs for the sample basket (deterministic for testing)
SAMPLE_BASKET_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


class BasketRepository:
    """Database-backed repository for baskets, positions, and NAV history."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Initialize with an async session factory.

        Args:
            session_factory: SQLAlchemy async_sessionmaker for creating
                database sessions.
        """
        self._session_factory = session_factory
        self._engine = BasketEngine()
        self._seeded = False

    async def _ensure_sample_basket(self, session: AsyncSession) -> None:
        """Seed the sample basket if the baskets table is empty.

        Only runs once per repository instance lifetime.
        """
        if self._seeded:
            return
        self._seeded = True

        result = await session.execute(
            select(Basket).where(Basket.id == SAMPLE_BASKET_ID)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return

        now = datetime.datetime(
            2025, 12, 17, 10, 0, 0, tzinfo=datetime.timezone.utc
        )
        weight = 0.333333

        basket = Basket(
            id=SAMPLE_BASKET_ID,
            name="Asia Momentum Leaders",
            description="Leading Asian country ETFs by RS score",
            benchmark_id=None,
            created_at=now,
            status="active",
            weighting_method="equal",
        )
        session.add(basket)

        positions_data = [
            ("11111111-1111-1111-1111-111111111111", "EWJ_US", weight),
            ("22222222-2222-2222-2222-222222222222", "EWT_US", weight),
            ("33333333-3333-3333-3333-333333333333", "INDA_US", 0.333334),
        ]
        for pos_id, instrument_id, w in positions_data:
            pos = BasketPosition(
                id=pos_id,
                basket_id=SAMPLE_BASKET_ID,
                instrument_id=instrument_id,
                weight=w,
                added_at=now,
                removed_at=None,
                status="active",
            )
            session.add(pos)

        # Generate sample NAV history
        nav = 100.0
        bench_nav = 100.0
        num_days = 90
        base_date = datetime.date(2026, 3, 17) - datetime.timedelta(
            days=num_days
        )
        for i in range(num_days):
            d = base_date + datetime.timedelta(days=i)
            if d.weekday() >= 5:
                continue
            nav_change = round(0.002 + 0.001 * (i % 7 - 3), 6)
            bench_change = round(0.001 + 0.0005 * (i % 5 - 2), 6)
            nav = round(nav * (1.0 + nav_change), 6)
            bench_nav = round(bench_nav * (1.0 + bench_change), 6)
            rs_line = round(nav / bench_nav * 100, 4)

            nav_row = BasketNAV(
                basket_id=SAMPLE_BASKET_ID,
                date=d,
                nav=nav,
                benchmark_nav=bench_nav,
                rs_line=rs_line,
            )
            session.add(nav_row)

        await session.commit()
        logger.info("Seeded sample basket %s", SAMPLE_BASKET_ID)

    def _basket_to_dict(
        self, basket: Basket
    ) -> dict[str, Any]:
        """Convert a Basket ORM object to a plain dict for the service layer."""
        positions = []
        for p in basket.positions:
            positions.append({
                "id": uuid.UUID(p.id),
                "basket_id": uuid.UUID(p.basket_id),
                "instrument_id": p.instrument_id,
                "weight": float(p.weight),
                "added_at": p.added_at,
                "removed_at": p.removed_at,
                "status": p.status,
            })
        return {
            "id": uuid.UUID(basket.id),
            "name": basket.name,
            "description": basket.description,
            "benchmark_id": basket.benchmark_id,
            "created_at": basket.created_at,
            "status": basket.status,
            "weighting_method": basket.weighting_method,
            "positions": positions,
        }

    async def create_basket(self, basket: dict[str, Any]) -> dict[str, Any]:
        """Create a new basket and persist it to the database.

        Args:
            basket: Dict with name, description, benchmark_id,
                weighting_method fields.

        Returns:
            Complete basket dict with generated id and timestamps.
        """
        basket_id = str(uuid.uuid4())
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        async with self._session_factory() as session:
            db_basket = Basket(
                id=basket_id,
                name=basket["name"],
                description=basket.get("description"),
                benchmark_id=basket.get("benchmark_id"),
                created_at=now,
                status="active",
                weighting_method=basket.get("weighting_method", "equal"),
            )
            session.add(db_basket)
            await session.commit()

            return {
                "id": uuid.UUID(basket_id),
                "name": db_basket.name,
                "description": db_basket.description,
                "benchmark_id": db_basket.benchmark_id,
                "created_at": now,
                "status": "active",
                "weighting_method": db_basket.weighting_method,
                "positions": [],
            }

    async def get_all_baskets(self) -> list[dict[str, Any]]:
        """Return all baskets sorted by creation date descending.

        Returns:
            List of basket dicts.
        """
        async with self._session_factory() as session:
            await self._ensure_sample_basket(session)

            result = await session.execute(
                select(Basket).order_by(Basket.created_at.desc())
            )
            baskets = result.scalars().all()
            return [self._basket_to_dict(b) for b in baskets]

    async def get_basket(self, basket_id: str) -> dict[str, Any] | None:
        """Retrieve a single basket by ID.

        Args:
            basket_id: UUID string of the basket.

        Returns:
            Basket dict or None if not found.
        """
        async with self._session_factory() as session:
            await self._ensure_sample_basket(session)

            result = await session.execute(
                select(Basket).where(Basket.id == basket_id)
            )
            basket = result.scalar_one_or_none()
            if basket is None:
                return None
            return self._basket_to_dict(basket)

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
        async with self._session_factory() as session:
            result = await session.execute(
                select(Basket).where(Basket.id == basket_id)
            )
            basket = result.scalar_one_or_none()
            if basket is None:
                raise KeyError(f"Basket {basket_id} not found")

            pos_id = str(uuid.uuid4())
            now = datetime.datetime.now(tz=datetime.timezone.utc)

            db_pos = BasketPosition(
                id=pos_id,
                basket_id=basket_id,
                instrument_id=position["instrument_id"],
                weight=float(position["weight"]),
                added_at=now,
                removed_at=None,
                status="active",
            )
            session.add(db_pos)
            await session.commit()

            return {
                "id": uuid.UUID(pos_id),
                "basket_id": uuid.UUID(basket_id),
                "instrument_id": position["instrument_id"],
                "weight": float(position["weight"]),
                "added_at": now,
                "removed_at": None,
                "status": "active",
            }

    async def remove_position(
        self, basket_id: str, position_id: str
    ) -> bool:
        """Remove a position from a basket (soft delete).

        Args:
            basket_id: UUID string of the basket.
            position_id: UUID string of the position.

        Returns:
            True if position was found and removed, False otherwise.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(BasketPosition).where(
                    BasketPosition.id == position_id,
                    BasketPosition.basket_id == basket_id,
                )
            )
            pos = result.scalar_one_or_none()
            if pos is None:
                return False

            pos.status = "removed"
            pos.removed_at = datetime.datetime.now(tz=datetime.timezone.utc)
            await session.commit()
            return True

    async def get_basket_nav(
        self, basket_id: str
    ) -> list[dict[str, Any]]:
        """Retrieve NAV history for a basket.

        Args:
            basket_id: UUID string of the basket.

        Returns:
            List of NAV data point dicts, empty if basket not found.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(BasketNAV)
                .where(BasketNAV.basket_id == basket_id)
                .order_by(BasketNAV.date)
            )
            rows = result.scalars().all()
            return [
                {
                    "basket_id": uuid.UUID(r.basket_id),
                    "date": r.date,
                    "nav": float(r.nav),
                    "benchmark_nav": float(r.benchmark_nav)
                    if r.benchmark_nav is not None
                    else None,
                    "rs_line": float(r.rs_line)
                    if r.rs_line is not None
                    else None,
                }
                for r in rows
            ]

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
        nav_history = await self.get_basket_nav(basket_id)
        perf = self._engine.compute_performance(nav_history)
        perf["basket_id"] = uuid.UUID(basket_id)
        return perf
