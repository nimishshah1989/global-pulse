"""Tests for the baskets API endpoints."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

from repositories.basket_repo import SAMPLE_BASKET_ID, SAMPLE_POS_EWJ


@pytest.mark.asyncio
async def test_list_baskets_200(async_client: AsyncClient) -> None:
    """GET /api/baskets/ should return 200."""
    response = await async_client.get("/api/baskets/")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    assert body["meta"]["count"] >= 1  # sample basket


@pytest.mark.asyncio
async def test_create_basket_201(async_client: AsyncClient) -> None:
    """POST /api/baskets/ should return 201 with new basket."""
    payload = {
        "name": "Test Basket",
        "description": "A test basket",
        "benchmark_id": "ACWI_US",
        "weighting_method": "equal",
    }
    response = await async_client.post("/api/baskets/", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["name"] == "Test Basket"
    assert body["data"]["status"] == "active"
    assert "id" in body["data"]


@pytest.mark.asyncio
async def test_get_basket_detail(async_client: AsyncClient) -> None:
    """GET /api/baskets/{id} should return basket with positions."""
    response = await async_client.get(
        f"/api/baskets/{SAMPLE_BASKET_ID}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["name"] == "Asia Momentum Leaders"
    assert len(body["data"]["positions"]) == 3


@pytest.mark.asyncio
async def test_basket_not_found_404(async_client: AsyncClient) -> None:
    """GET /api/baskets/{bad_id} should return 404."""
    response = await async_client.get(
        "/api/baskets/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_position(async_client: AsyncClient) -> None:
    """POST /api/baskets/{id}/positions should add a position."""
    payload = {
        "instrument_id": "EWY_US",
        "weight": "0.25",
    }
    response = await async_client.post(
        f"/api/baskets/{SAMPLE_BASKET_ID}/positions",
        json=payload,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["instrument_id"] == "EWY_US"


@pytest.mark.asyncio
async def test_add_position_to_nonexistent_basket(
    async_client: AsyncClient,
) -> None:
    """POST to nonexistent basket should return 404."""
    payload = {"instrument_id": "EWY_US", "weight": "0.25"}
    response = await async_client.post(
        "/api/baskets/00000000-0000-0000-0000-000000000000/positions",
        json=payload,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_position(async_client: AsyncClient) -> None:
    """DELETE /api/baskets/{id}/positions/{pos_id} should remove it."""
    response = await async_client.delete(
        f"/api/baskets/{SAMPLE_BASKET_ID}/positions/{SAMPLE_POS_EWJ}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["removed"] is True


@pytest.mark.asyncio
async def test_remove_nonexistent_position(
    async_client: AsyncClient,
) -> None:
    """DELETE nonexistent position should return 404."""
    response = await async_client.delete(
        f"/api/baskets/{SAMPLE_BASKET_ID}/positions/"
        "00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_basket_performance_shape(
    async_client: AsyncClient,
) -> None:
    """GET /api/baskets/{id}/performance should return performance metrics."""
    response = await async_client.get(
        f"/api/baskets/{SAMPLE_BASKET_ID}/performance"
    )
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert "cumulative_return" in data
    assert "max_drawdown" in data
    assert "basket_id" in data


@pytest.mark.asyncio
async def test_performance_has_decimal_fields(
    async_client: AsyncClient,
) -> None:
    """Performance fields should be numeric (serialized from Decimal)."""
    response = await async_client.get(
        f"/api/baskets/{SAMPLE_BASKET_ID}/performance"
    )
    body = response.json()
    data = body["data"]
    # These should be numeric strings/numbers, not None
    assert data["cumulative_return"] is not None
    assert data["max_drawdown"] is not None
    # Verify they can be converted to float (valid numeric)
    float(data["cumulative_return"])
    float(data["max_drawdown"])


@pytest.mark.asyncio
async def test_performance_not_found_404(
    async_client: AsyncClient,
) -> None:
    """Performance for nonexistent basket should return 404."""
    response = await async_client.get(
        "/api/baskets/00000000-0000-0000-0000-000000000000/performance"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_response_envelope_meta(
    async_client: AsyncClient,
) -> None:
    """All basket endpoints should return proper meta."""
    response = await async_client.get("/api/baskets/")
    body = response.json()
    assert "timestamp" in body["meta"]
    assert "count" in body["meta"]
