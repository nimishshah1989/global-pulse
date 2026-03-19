"""Ranking endpoints v2 — country, sector, stock, and ETF rankings.

Uses the simplified 3-indicator RS engine with action matrix.
Supports benchmark parameter for ratio return computation.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.common import ApiResponse, Meta
from models.rs_scores import RankingItemV2
from repositories.instrument_repo import InstrumentRepository
from repositories.ranking_repo import RankingRepository
from services.ranking_service import RankingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rankings", tags=["rankings"])


def _get_ranking_service(session: AsyncSession) -> RankingService:
    instrument_repo = InstrumentRepository(session)
    ranking_repo = RankingRepository(session)
    return RankingService(ranking_repo, instrument_repo)


@router.get("/countries")
async def get_country_rankings(
    as_of: date | None = Query(None, description="Historical date (YYYY-MM-DD)"),
    benchmark: str | None = Query(None, description="Benchmark instrument ID (e.g. ACWI, SPX, GLD)"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItemV2]]:
    """Return RS rankings for all country indices."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_country_rankings(as_of=as_of, benchmark=benchmark)
        return ApiResponse(
            data=items,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc), count=len(items)),
        )
    except Exception as exc:
        logger.exception("Error fetching country rankings")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/{country_code}")
async def get_sector_rankings(
    country_code: str,
    as_of: date | None = Query(None, description="Historical date (YYYY-MM-DD)"),
    benchmark: str | None = Query(None, description="Benchmark instrument ID"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItemV2]]:
    """Return RS rankings for sectors within a country."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_sector_rankings(
            country_code, as_of=as_of, benchmark=benchmark,
        )
        return ApiResponse(
            data=items,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc), count=len(items)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error fetching sector rankings for %s", country_code)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stocks/{country_code}/{sector}")
async def get_stock_rankings(
    country_code: str,
    sector: str,
    benchmark: str | None = Query(None, description="Benchmark instrument ID"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItemV2]]:
    """Return RS rankings for stocks in a country+sector."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_stock_rankings(
            country_code, sector, benchmark=benchmark,
        )
        return ApiResponse(
            data=items,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc), count=len(items)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error fetching stock rankings")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/global-sectors")
async def get_global_sector_rankings(
    benchmark: str | None = Query(None, description="Benchmark instrument ID"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItemV2]]:
    """Return RS rankings for global sector ETFs."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_global_sector_rankings(benchmark=benchmark)
        return ApiResponse(
            data=items,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc), count=len(items)),
        )
    except Exception as exc:
        logger.exception("Error fetching global sector rankings")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/etfs")
async def get_all_etf_rankings(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItemV2]]:
    """Return all ETF rankings — the main investable output."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_all_etf_rankings()
        return ApiResponse(
            data=items,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc), count=len(items)),
        )
    except Exception as exc:
        logger.exception("Error fetching ETF rankings")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/etfs/top")
async def get_top_etfs(
    action: str | None = Query(None, description="Filter by action (BUY, SELL, etc.)"),
    country: str | None = Query(None, description="Filter by country code"),
    sector: str | None = Query(None, description="Filter by sector slug"),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItemV2]]:
    """Return top ETFs with optional filters — the primary decision screen."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_top_etfs(
            action_filter=action,
            country_filter=country,
            sector_filter=sector,
            limit=limit,
        )
        return ApiResponse(
            data=items,
            meta=Meta(timestamp=datetime.now(tz=timezone.utc), count=len(items)),
        )
    except Exception as exc:
        logger.exception("Error fetching top ETFs")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
