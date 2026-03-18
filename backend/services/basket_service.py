"""Basket service — business logic for basket CRUD and performance."""

from __future__ import annotations
import logging
import uuid

from models.baskets import (
    BasketCreate,
    BasketPerformanceResponse,
    BasketPositionCreate,
    BasketPositionResponse,
    BasketResponse,
)
from repositories.basket_repo import BasketRepository

logger = logging.getLogger(__name__)


class BasketService:
    """Service layer for basket operations."""

    def __init__(self, repo: BasketRepository) -> None:
        """Initialize with a basket repository.

        Args:
            repo: BasketRepository instance for data access.
        """
        self._repo = repo

    async def create_basket(self, data: BasketCreate) -> BasketResponse:
        """Create a new basket.

        Args:
            data: BasketCreate model with name, description, etc.

        Returns:
            BasketResponse with the created basket's details.
        """
        raw = await self._repo.create_basket(data.model_dump())
        positions = [
            BasketPositionResponse(**p)
            for p in raw.get("positions", [])
        ]
        return BasketResponse(
            id=raw["id"],
            name=raw["name"],
            description=raw.get("description"),
            benchmark_id=raw.get("benchmark_id"),
            created_at=raw["created_at"],
            status=raw.get("status", "active"),
            weighting_method=raw.get("weighting_method", "equal"),
            positions=positions,
        )

    async def list_baskets(self) -> list[BasketResponse]:
        """List all baskets.

        Returns:
            List of BasketResponse models.
        """
        raw_list = await self._repo.get_all_baskets()
        results: list[BasketResponse] = []
        for raw in raw_list:
            positions = [
                BasketPositionResponse(**p)
                for p in raw.get("positions", [])
            ]
            results.append(
                BasketResponse(
                    id=raw["id"],
                    name=raw["name"],
                    description=raw.get("description"),
                    benchmark_id=raw.get("benchmark_id"),
                    created_at=raw["created_at"],
                    status=raw.get("status", "active"),
                    weighting_method=raw.get("weighting_method", "equal"),
                    positions=positions,
                )
            )
        return results

    async def get_basket(self, basket_id: str) -> BasketResponse | None:
        """Get a single basket by ID.

        Args:
            basket_id: UUID string of the basket.

        Returns:
            BasketResponse or None if not found.
        """
        raw = await self._repo.get_basket(basket_id)
        if raw is None:
            return None
        positions = [
            BasketPositionResponse(**p)
            for p in raw.get("positions", [])
        ]
        return BasketResponse(
            id=raw["id"],
            name=raw["name"],
            description=raw.get("description"),
            benchmark_id=raw.get("benchmark_id"),
            created_at=raw["created_at"],
            status=raw.get("status", "active"),
            weighting_method=raw.get("weighting_method", "equal"),
            positions=positions,
        )

    async def add_position(
        self, basket_id: str, position: BasketPositionCreate
    ) -> BasketPositionResponse:
        """Add a position to a basket.

        Args:
            basket_id: UUID string of the basket.
            position: BasketPositionCreate with instrument_id and weight.

        Returns:
            BasketPositionResponse for the new position.

        Raises:
            KeyError: If basket not found.
        """
        raw = await self._repo.add_position(
            basket_id, position.model_dump()
        )
        return BasketPositionResponse(**raw)

    async def remove_position(
        self, basket_id: str, position_id: str
    ) -> bool:
        """Remove a position from a basket.

        Args:
            basket_id: UUID string of the basket.
            position_id: UUID string of the position.

        Returns:
            True if removed, False if not found.
        """
        return await self._repo.remove_position(basket_id, position_id)

    async def get_performance(
        self, basket_id: str
    ) -> BasketPerformanceResponse | None:
        """Get performance metrics for a basket.

        Args:
            basket_id: UUID string of the basket.

        Returns:
            BasketPerformanceResponse or None if basket not found.
        """
        basket = await self._repo.get_basket(basket_id)
        if basket is None:
            return None

        raw = await self._repo.get_basket_performance(basket_id)
        return BasketPerformanceResponse(
            basket_id=raw["basket_id"],
            cumulative_return=raw["cumulative_return"],
            cagr=raw.get("cagr"),
            max_drawdown=raw["max_drawdown"],
            sharpe_ratio=raw.get("sharpe_ratio"),
            pct_weeks_outperforming=raw.get("pct_weeks_outperforming"),
        )
