"""Basket CRUD and performance endpoints.

Provides basket creation, position management, NAV tracking,
and performance metric retrieval.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from models.baskets import (
    BasketCreate,
    BasketPerformanceResponse,
    BasketPositionCreate,
    BasketPositionResponse,
    BasketResponse,
)
from models.common import ApiResponse, Meta
from repositories.basket_repo import BasketRepository
from services.basket_service import BasketService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/baskets", tags=["baskets"])


def _get_service() -> BasketService:
    """Build the basket service with its dependencies."""
    repo = BasketRepository()
    return BasketService(repo)


@router.post("/", status_code=201)
async def create_basket(
    body: BasketCreate,
) -> ApiResponse[BasketResponse]:
    """Create a new basket.

    Accepts name, description, benchmark_id, and weighting_method.
    Returns the created basket with an empty position list.
    """
    service = _get_service()
    basket = await service.create_basket(body)
    return ApiResponse(
        data=basket,
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=1,
        ),
    )


@router.get("/")
async def list_baskets() -> ApiResponse[list[BasketResponse]]:
    """List all baskets sorted by creation date descending."""
    service = _get_service()
    baskets = await service.list_baskets()
    return ApiResponse(
        data=baskets,
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=len(baskets),
        ),
    )


@router.get("/{basket_id}")
async def get_basket(basket_id: str) -> ApiResponse[BasketResponse]:
    """Get basket detail including positions and NAV history.

    Raises 404 if basket not found.
    """
    service = _get_service()
    basket = await service.get_basket(basket_id)
    if basket is None:
        raise HTTPException(status_code=404, detail="Basket not found")
    return ApiResponse(
        data=basket,
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=1,
        ),
    )


@router.post("/{basket_id}/positions", status_code=201)
async def add_position(
    basket_id: str,
    body: BasketPositionCreate,
) -> ApiResponse[BasketPositionResponse]:
    """Add a position to an existing basket.

    Raises 404 if basket not found.
    """
    service = _get_service()
    try:
        position = await service.add_position(basket_id, body)
    except KeyError:
        raise HTTPException(status_code=404, detail="Basket not found")
    return ApiResponse(
        data=position,
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=1,
        ),
    )


@router.delete("/{basket_id}/positions/{position_id}")
async def remove_position(
    basket_id: str,
    position_id: str,
) -> ApiResponse[dict]:
    """Remove a position from a basket.

    Raises 404 if basket or position not found.
    """
    service = _get_service()
    removed = await service.remove_position(basket_id, position_id)
    if not removed:
        raise HTTPException(
            status_code=404, detail="Basket or position not found"
        )
    return ApiResponse(
        data={"removed": True},
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=1,
        ),
    )


@router.get("/{basket_id}/performance")
async def get_performance(
    basket_id: str,
) -> ApiResponse[BasketPerformanceResponse]:
    """Get performance metrics for a basket.

    Includes cumulative return, CAGR, max drawdown, Sharpe ratio,
    and percentage of weeks outperforming the benchmark.

    Raises 404 if basket not found.
    """
    service = _get_service()
    perf = await service.get_performance(basket_id)
    if perf is None:
        raise HTTPException(status_code=404, detail="Basket not found")
    return ApiResponse(
        data=perf,
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=1,
        ),
    )
