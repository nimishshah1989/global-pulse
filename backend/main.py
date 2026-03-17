"""Momentum Compass API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.baskets import router as baskets_router
from api.opportunities import router as opportunities_router
from api.rankings import router as rankings_router
from api.rrg import router as rrg_router
from api.system import router as system_router
from config import get_settings
from db.session import engine

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate database connection on startup, dispose engine on shutdown."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection validated successfully.")
    except Exception as exc:
        logger.error("Failed to connect to database: %s", exc)
        raise

    yield

    await engine.dispose()
    logger.info("Database engine disposed.")


app = FastAPI(
    title="Momentum Compass API",
    description="Global Relative Strength Engine for the JSL Wealth Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins in development
if settings.is_development:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register routers
app.include_router(system_router)
app.include_router(rankings_router)
app.include_router(rrg_router)
app.include_router(baskets_router)
app.include_router(opportunities_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
