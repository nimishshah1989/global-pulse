"""Momentum Compass API -- FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.baskets import router as baskets_router
from api.instruments import router as instruments_router
from api.opportunities import router as opportunities_router
from api.portfolio import router as portfolio_router
from api.rankings import router as rankings_router
from api.rrg import router as rrg_router
from api.system import router as system_router
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle.

    Attempts database connection validation but falls back gracefully
    when PostgreSQL is unavailable (JSON-backed repos still work).
    """
    try:
        import asyncio

        from db.models import Base
        from db.session import get_engine
        from sqlalchemy import text

        eng = get_engine()
        # Create tables if they don't exist (safe for production — no-op if already created)
        async with asyncio.timeout(30):
            async with eng.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with eng.connect() as conn:
                await conn.execute(text("SELECT 1"))
        logger.info("Database connection validated successfully.")
    except Exception as exc:
        logger.warning(
            "Database not available (%s). Running with JSON-backed repositories.",
            exc,
        )

    yield

    try:
        from db.session import get_engine

        await get_engine().dispose()
        logger.info("Database engine disposed.")
    except Exception:
        pass


app = FastAPI(
    title="Momentum Compass API",
    description="Global Relative Strength Engine for the JSL Wealth Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"] if settings.is_development
        else ["https://global-pulse.jslwealth.in", "http://global-pulse.jslwealth.in"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(system_router)
app.include_router(instruments_router)
app.include_router(rankings_router)
app.include_router(rrg_router)
app.include_router(baskets_router)
app.include_router(portfolio_router)
app.include_router(opportunities_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
