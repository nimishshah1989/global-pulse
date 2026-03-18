"""Pytest fixtures for Momentum Compass backend tests."""

from __future__ import annotations
import datetime
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Callable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from models.instruments import InstrumentResponse


@pytest.fixture
def anyio_backend() -> str:
    """Use asyncio as the async backend for tests."""
    return "asyncio"


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP test client for the FastAPI app.

    Imports the app inside the fixture to allow env var overrides
    in earlier fixtures if needed.
    """
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_instrument() -> Callable[..., InstrumentResponse]:
    """Factory fixture that returns an InstrumentResponse with realistic data.

    Usage:
        instrument = sample_instrument()
        instrument = sample_instrument(id="XLK_US", name="Technology Select Sector SPDR")
    """

    def _factory(
        id: str = "AAPL_US",
        name: str = "Apple Inc.",
        ticker_stooq: str | None = "AAPL.US",
        ticker_yfinance: str | None = "AAPL",
        source: str = "stooq",
        asset_type: str = "stock",
        country: str = "US",
        sector: str = "technology",
        hierarchy_level: int = 3,
        benchmark_id: str | None = "XLK_US",
        currency: str = "USD",
        liquidity_tier: int = 1,
        is_active: bool = True,
        metadata: dict | None = None,
    ) -> InstrumentResponse:
        return InstrumentResponse(
            id=id,
            name=name,
            ticker_stooq=ticker_stooq,
            ticker_yfinance=ticker_yfinance,
            source=source,
            asset_type=asset_type,
            country=country,
            sector=sector,
            hierarchy_level=hierarchy_level,
            benchmark_id=benchmark_id,
            currency=currency,
            liquidity_tier=liquidity_tier,
            is_active=is_active,
            metadata=metadata,
        )

    return _factory
