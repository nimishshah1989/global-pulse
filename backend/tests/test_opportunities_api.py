"""Tests for the opportunities API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_opportunities_200(async_client: AsyncClient) -> None:
    """GET /api/opportunities/ should return 200."""
    response = await async_client.get("/api/opportunities")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_response_envelope_shape(async_client: AsyncClient) -> None:
    """Response should have data (list) and meta with timestamp and count."""
    response = await async_client.get("/api/opportunities")
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    assert "timestamp" in body["meta"]
    assert "count" in body["meta"]
    assert isinstance(body["meta"]["count"], int)


@pytest.mark.asyncio
async def test_filter_by_signal_type(async_client: AsyncClient) -> None:
    """Filtering by signal_type should only return that type."""
    response = await async_client.get(
        "/api/opportunities", params={"signal_type": "volume_breakout"}
    )
    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert item["signal_type"] == "volume_breakout"


@pytest.mark.asyncio
async def test_filter_by_min_conviction(async_client: AsyncClient) -> None:
    """Filtering by min_conviction should exclude lower-scoring signals."""
    response = await async_client.get(
        "/api/opportunities", params={"min_conviction": 80.0}
    )
    assert response.status_code == 200
    body = response.json()
    for item in body["data"]:
        assert float(item["conviction_score"]) >= 80.0


@pytest.mark.asyncio
async def test_multi_level_endpoint(async_client: AsyncClient) -> None:
    """GET /api/opportunities/multi-level should return alignment signals."""
    response = await async_client.get("/api/opportunities/multi-level")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], list)
    # Should have at least the mock multi-level alignment
    assert len(body["data"]) >= 1
    for item in body["data"]:
        assert "country_id" in item
        assert "sector_id" in item
        assert "stock_id" in item


@pytest.mark.asyncio
async def test_opportunities_have_required_fields(
    async_client: AsyncClient,
) -> None:
    """Each opportunity should have the required fields."""
    response = await async_client.get("/api/opportunities")
    body = response.json()
    required_fields = {
        "id", "instrument_id", "date", "signal_type",
        "conviction_score", "description",
    }
    for item in body["data"]:
        for field in required_fields:
            assert field in item, f"Missing field '{field}' in {item}"


@pytest.mark.asyncio
async def test_limit_parameter(async_client: AsyncClient) -> None:
    """Limit parameter should cap the number of results."""
    response = await async_client.get(
        "/api/opportunities", params={"limit": 2}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) <= 2
