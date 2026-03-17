"""Tests for the RRG (Relative Rotation Graph) API endpoints."""

import pytest
from httpx import AsyncClient

VALID_QUADRANTS = {"LEADING", "WEAKENING", "LAGGING", "IMPROVING"}


@pytest.mark.asyncio
async def test_country_rrg_returns_data(async_client: AsyncClient) -> None:
    """GET /api/rrg/countries should return 200 with RRG data."""
    response = await async_client.get("/api/rrg/countries")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0


@pytest.mark.asyncio
async def test_rrg_data_has_trail(async_client: AsyncClient) -> None:
    """Each RRG data point should have a trail array."""
    response = await async_client.get("/api/rrg/countries")
    body = response.json()
    for point in body["data"]:
        assert "trail" in point, f"Missing 'trail' for {point['id']}"
        assert isinstance(point["trail"], list)


@pytest.mark.asyncio
async def test_rrg_trail_length(async_client: AsyncClient) -> None:
    """Each RRG trail should have exactly 8 entries."""
    response = await async_client.get("/api/rrg/countries")
    body = response.json()
    for point in body["data"]:
        assert len(point["trail"]) == 8, (
            f"Trail length is {len(point['trail'])} for {point['id']}, expected 8"
        )


@pytest.mark.asyncio
async def test_rrg_quadrant_valid(async_client: AsyncClient) -> None:
    """All RRG quadrant values must be valid."""
    response = await async_client.get("/api/rrg/countries")
    body = response.json()
    for point in body["data"]:
        assert point["quadrant"] in VALID_QUADRANTS, (
            f"Invalid quadrant '{point['quadrant']}' for {point['id']}"
        )


@pytest.mark.asyncio
async def test_sector_rrg_by_country(async_client: AsyncClient) -> None:
    """GET /api/rrg/sectors/US should return sector RRG data."""
    response = await async_client.get("/api/rrg/sectors/US")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0


@pytest.mark.asyncio
async def test_sector_rrg_invalid_country(async_client: AsyncClient) -> None:
    """GET /api/rrg/sectors/XX should return 422."""
    response = await async_client.get("/api/rrg/sectors/XX")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rrg_data_point_fields(async_client: AsyncClient) -> None:
    """Each RRG data point should have required fields."""
    response = await async_client.get("/api/rrg/countries")
    body = response.json()
    required_fields = {"id", "name", "rs_score", "rs_momentum", "quadrant", "trail"}
    for point in body["data"]:
        for field in required_fields:
            assert field in point, f"Missing field '{field}' in RRG point"


@pytest.mark.asyncio
async def test_rrg_trail_point_fields(async_client: AsyncClient) -> None:
    """Each trail point should have date, rs_score, rs_momentum."""
    response = await async_client.get("/api/rrg/countries")
    body = response.json()
    for point in body["data"]:
        for trail_point in point["trail"]:
            assert "date" in trail_point
            assert "rs_score" in trail_point
            assert "rs_momentum" in trail_point


@pytest.mark.asyncio
async def test_stock_rrg_endpoint(async_client: AsyncClient) -> None:
    """GET /api/rrg/stocks/US/technology should return 200."""
    response = await async_client.get("/api/rrg/stocks/US/technology")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
