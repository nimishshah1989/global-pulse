"""Tests for the system API endpoints."""

import pytest
from httpx import AsyncClient

from repositories.instrument_repo import VALID_COUNTRY_CODES


@pytest.mark.asyncio
async def test_regime_endpoint(async_client: AsyncClient) -> None:
    """GET /api/regime should return regime data."""
    response = await async_client.get("/api/regime")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert body["data"]["regime"] in ("RISK_ON", "RISK_OFF")
    assert "benchmark" in body["data"]
    assert "benchmark_vs_ma200" in body["data"]


@pytest.mark.asyncio
async def test_data_status_endpoint(async_client: AsyncClient) -> None:
    """GET /api/data-status should return status data."""
    response = await async_client.get("/api/data-status")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "instruments_count" in body["data"]
    assert body["data"]["instruments_count"] > 0


@pytest.mark.asyncio
async def test_matrix_endpoint_shape(async_client: AsyncClient) -> None:
    """GET /api/matrix should return countries, sectors, and matrix keys."""
    response = await async_client.get("/api/matrix")
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert "countries" in data
    assert "sectors" in data
    assert "matrix" in data
    assert isinstance(data["countries"], list)
    assert isinstance(data["sectors"], list)
    assert isinstance(data["matrix"], dict)


@pytest.mark.asyncio
async def test_matrix_has_all_countries(async_client: AsyncClient) -> None:
    """Matrix should include entries for all valid country codes."""
    response = await async_client.get("/api/matrix")
    body = response.json()
    matrix_countries = set(body["data"]["matrix"].keys())
    for code in VALID_COUNTRY_CODES:
        assert code in matrix_countries, (
            f"Country '{code}' missing from matrix"
        )


@pytest.mark.asyncio
async def test_regime_has_meta(async_client: AsyncClient) -> None:
    """Regime response should include meta with timestamp."""
    response = await async_client.get("/api/regime")
    body = response.json()
    assert "meta" in body
    assert "timestamp" in body["meta"]


@pytest.mark.asyncio
async def test_data_status_has_meta(async_client: AsyncClient) -> None:
    """Data status response should include meta with timestamp."""
    response = await async_client.get("/api/data-status")
    body = response.json()
    assert "meta" in body
    assert "timestamp" in body["meta"]
