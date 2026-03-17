"""Tests for the rankings API endpoints."""

import pytest
from httpx import AsyncClient

VALID_QUADRANTS = {"LEADING", "WEAKENING", "LAGGING", "IMPROVING"}
REQUIRED_RANKING_FIELDS = {
    "instrument_id",
    "name",
    "adjusted_rs_score",
    "quadrant",
    "rs_momentum",
    "volume_ratio",
    "rs_trend",
    "rs_pct_1m",
    "rs_pct_3m",
    "rs_pct_6m",
    "rs_pct_12m",
    "liquidity_tier",
    "extension_warning",
}


@pytest.mark.asyncio
async def test_country_rankings_returns_200(async_client: AsyncClient) -> None:
    """GET /api/rankings/countries should return 200."""
    response = await async_client.get("/api/rankings/countries")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_country_rankings_response_shape(async_client: AsyncClient) -> None:
    """Response should have data (list) and meta with timestamp."""
    response = await async_client.get("/api/rankings/countries")
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    assert "timestamp" in body["meta"]


@pytest.mark.asyncio
async def test_sector_rankings_valid_country(async_client: AsyncClient) -> None:
    """GET /api/rankings/sectors/US should return 200 with sector data."""
    response = await async_client.get("/api/rankings/sectors/US")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0  # US has sector ETFs in the map


@pytest.mark.asyncio
async def test_sector_rankings_invalid_country(async_client: AsyncClient) -> None:
    """GET /api/rankings/sectors/XX should return 422."""
    response = await async_client.get("/api/rankings/sectors/XX")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stock_rankings_valid(async_client: AsyncClient) -> None:
    """GET /api/rankings/stocks/US/technology should return 200."""
    response = await async_client.get("/api/rankings/stocks/US/technology")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    # May be empty since no Level 3 stocks in instrument_map yet
    assert body["meta"]["count"] is not None


@pytest.mark.asyncio
async def test_stock_rankings_invalid_country(async_client: AsyncClient) -> None:
    """GET /api/rankings/stocks/ZZ/technology should return 422."""
    response = await async_client.get("/api/rankings/stocks/ZZ/technology")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_global_sector_rankings(async_client: AsyncClient) -> None:
    """GET /api/rankings/global-sectors should return 200 with data."""
    response = await async_client.get("/api/rankings/global-sectors")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0  # Global sector ETFs exist in the map


@pytest.mark.asyncio
async def test_all_ranking_items_have_required_fields(
    async_client: AsyncClient,
) -> None:
    """Every ranking item must contain all required fields."""
    response = await async_client.get("/api/rankings/countries")
    body = response.json()
    for item in body["data"]:
        for field in REQUIRED_RANKING_FIELDS:
            assert field in item, f"Missing field '{field}' in ranking item {item}"


@pytest.mark.asyncio
async def test_quadrant_values_valid(async_client: AsyncClient) -> None:
    """All quadrant values must be one of the four valid quadrants."""
    response = await async_client.get("/api/rankings/countries")
    body = response.json()
    for item in body["data"]:
        assert item["quadrant"] in VALID_QUADRANTS, (
            f"Invalid quadrant '{item['quadrant']}' for {item['instrument_id']}"
        )


@pytest.mark.asyncio
async def test_country_rankings_sorted_descending(
    async_client: AsyncClient,
) -> None:
    """Country rankings should be sorted by adjusted_rs_score descending."""
    response = await async_client.get("/api/rankings/countries")
    body = response.json()
    scores = [float(item["adjusted_rs_score"]) for item in body["data"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_sector_rankings_case_insensitive(
    async_client: AsyncClient,
) -> None:
    """Country code should be case insensitive."""
    response_upper = await async_client.get("/api/rankings/sectors/US")
    response_lower = await async_client.get("/api/rankings/sectors/us")
    assert response_upper.status_code == 200
    assert response_lower.status_code == 200
