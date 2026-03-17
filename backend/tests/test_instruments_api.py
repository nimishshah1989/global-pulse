"""Tests for the instruments API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_instruments_returns_200(async_client: AsyncClient) -> None:
    """GET /api/instruments should return 200."""
    response = await async_client.get("/api/instruments")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_instruments_has_data(async_client: AsyncClient) -> None:
    """GET /api/instruments should return a non-empty list with meta."""
    response = await async_client.get("/api/instruments")
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    assert "timestamp" in body["meta"]
    assert body["meta"]["count"] == len(body["data"])


@pytest.mark.asyncio
async def test_filter_by_country(async_client: AsyncClient) -> None:
    """GET /api/instruments?country=US should return only US instruments."""
    response = await async_client.get("/api/instruments", params={"country": "US"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    for item in body["data"]:
        assert item["country"] == "US"


@pytest.mark.asyncio
async def test_filter_by_hierarchy_level(async_client: AsyncClient) -> None:
    """GET /api/instruments?hierarchy_level=1 should return only level 1 instruments."""
    response = await async_client.get("/api/instruments", params={"hierarchy_level": 1})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    for item in body["data"]:
        assert item["hierarchy_level"] == 1


@pytest.mark.asyncio
async def test_instrument_prices_endpoint(async_client: AsyncClient) -> None:
    """GET /api/instruments/{id}/prices should return price data."""
    # SPX is a known instrument in the map
    response = await async_client.get("/api/instruments/SPX/prices")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    assert body["meta"]["count"] == len(body["data"])

    # Verify price record structure
    first = body["data"][0]
    assert "instrument_id" in first
    assert "date" in first
    assert "close" in first
    assert first["instrument_id"] == "SPX"


@pytest.mark.asyncio
async def test_instrument_rs_endpoint(async_client: AsyncClient) -> None:
    """GET /api/instruments/{id}/rs should return RS score data."""
    response = await async_client.get("/api/instruments/SPX/rs")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    assert body["meta"]["count"] == len(body["data"])

    # Verify RS score record structure
    first = body["data"][0]
    assert "instrument_id" in first
    assert "date" in first
    assert "adjusted_rs_score" in first
    assert "quadrant" in first
    assert "rs_momentum" in first
    assert first["instrument_id"] == "SPX"


@pytest.mark.asyncio
async def test_instrument_not_found_404(async_client: AsyncClient) -> None:
    """GET /api/instruments/NONEXISTENT/prices should return 404."""
    response = await async_client.get("/api/instruments/NONEXISTENT/prices")
    assert response.status_code == 404

    response = await async_client.get("/api/instruments/NONEXISTENT/rs")
    assert response.status_code == 404
