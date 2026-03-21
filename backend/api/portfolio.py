"""Portfolio API endpoints — model portfolio with positions, NAV, and metrics.

Exposes the simulated model portfolio built from BUY signals in the ranking
engine, with inverse-volatility weighting, stop losses, and weekly rebalancing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.common import ApiResponse, Meta
from models.portfolio import (
    NAVPoint,
    PortfolioPosition,
    PortfolioResponse,
    PortfolioSummary,
    PortfolioTrade,
)
from repositories.portfolio_repo import PortfolioRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/model")
async def get_model_portfolio(
    portfolio_type: str = Query(
        "etf_only",
        description="Portfolio universe: etf_only, stock_etf, stock_only",
    ),
    country: str | None = Query(
        None, description="Restrict to a single country code (e.g. US, IN)",
    ),
    benchmark: str = Query(
        "ACWI", description="Benchmark instrument ID (e.g. ACWI, SPX)",
    ),
    days: int = Query(
        252, ge=30, le=1260, description="Lookback window in trading days",
    ),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[PortfolioResponse]:
    """Return the full model portfolio — positions, NAV history, and metrics."""
    try:
        repo = PortfolioRepository(session)
        raw = await repo.get_model_portfolio(
            portfolio_type=portfolio_type,
            country=country,
            lookback_days=days,
            benchmark_id=benchmark,
        )
        response = _build_response(raw)
        return ApiResponse(
            data=response,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=response.summary.total_positions,
            ),
        )
    except Exception as exc:
        logger.exception("Error building model portfolio")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/model/positions")
async def get_portfolio_positions(
    portfolio_type: str = Query("etf_only"),
    country: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PortfolioPosition]]:
    """Return just the current positions in the model portfolio."""
    try:
        repo = PortfolioRepository(session)
        raw = await repo.get_model_portfolio(
            portfolio_type=portfolio_type,
            country=country,
        )
        positions = [PortfolioPosition(**p) for p in raw.get("positions", [])]
        return ApiResponse(
            data=positions,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=len(positions),
            ),
        )
    except Exception as exc:
        logger.exception("Error fetching portfolio positions")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/model/nav")
async def get_portfolio_nav(
    portfolio_type: str = Query("etf_only"),
    country: str | None = Query(None),
    benchmark: str = Query("ACWI"),
    days: int = Query(252, ge=30, le=1260),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[NAVPoint]]:
    """Return NAV history for charting."""
    try:
        repo = PortfolioRepository(session)
        raw = await repo.get_model_portfolio(
            portfolio_type=portfolio_type,
            country=country,
            lookback_days=days,
            benchmark_id=benchmark,
        )
        nav_points = [NAVPoint(**n) for n in raw.get("nav_history", [])]
        return ApiResponse(
            data=nav_points,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=len(nav_points),
            ),
        )
    except Exception as exc:
        logger.exception("Error fetching portfolio NAV")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_response(raw: dict) -> PortfolioResponse:
    """Convert the raw dict from PortfolioRepository into typed Pydantic models."""
    summary = PortfolioSummary(**raw.get("summary", {}))
    positions = [PortfolioPosition(**p) for p in raw.get("positions", [])]
    nav_history = [NAVPoint(**n) for n in raw.get("nav_history", [])]
    recent_trades = [PortfolioTrade(**t) for t in raw.get("recent_trades", [])]

    return PortfolioResponse(
        summary=summary,
        positions=positions,
        nav_history=nav_history,
        recent_trades=recent_trades,
    )
