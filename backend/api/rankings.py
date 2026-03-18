"""Ranking endpoints for country, sector, and stock RS rankings.

Supports an optional `as_of` query parameter (YYYY-MM-DD) that returns
historical rankings for the requested date. When the engine runs on real
data this queries the rs_scores table at that date; in mock mode it
generates deterministic date-shifted scores so the temporal UI works.
"""

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.common import ApiResponse, Meta
from models.rs_scores import RankingItem
from repositories.instrument_repo import InstrumentRepository
from repositories.ranking_repo import RankingRepository
from services.ranking_service import RankingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rankings", tags=["rankings"])


def _get_ranking_service(session: AsyncSession) -> RankingService:
    """Build the ranking service with DB-backed repositories."""
    instrument_repo = InstrumentRepository(session)
    ranking_repo = RankingRepository(session)
    return RankingService(ranking_repo, instrument_repo)


@router.get("/countries")
async def get_country_rankings(
    as_of: date | None = Query(None, description="Historical date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for all country indices, sorted by score descending."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_country_rankings(as_of=as_of)
        return ApiResponse(
            data=items,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=len(items),
            ),
        )
    except Exception as exc:
        logger.exception("Error fetching country rankings")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/{country_code}")
async def get_sector_rankings(
    country_code: str,
    as_of: date | None = Query(None, description="Historical date (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for sectors within a country."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_sector_rankings(country_code, as_of=as_of)
        return ApiResponse(
            data=items,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=len(items),
            ),
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
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for stocks in a country+sector."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_stock_rankings(country_code, sector)
        return ApiResponse(
            data=items,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=len(items),
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Error fetching stock rankings for %s/%s", country_code, sector
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/global-sectors")
async def get_global_sector_rankings(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for global sector ETFs."""
    try:
        service = _get_ranking_service(session)
        items = await service.get_global_sector_rankings()
        return ApiResponse(
            data=items,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=len(items),
            ),
        )
    except Exception as exc:
        logger.exception("Error fetching global sector rankings")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
