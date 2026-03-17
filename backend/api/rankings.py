"""Ranking endpoints for country, sector, and stock RS rankings."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from models.common import ApiResponse, Meta
from models.rs_scores import RankingItem
from repositories.instrument_repo import InstrumentRepository
from repositories.ranking_repo import RankingRepository
from services.ranking_service import RankingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rankings", tags=["rankings"])


def _get_ranking_service() -> RankingService:
    """Build the ranking service with its dependencies."""
    instrument_repo = InstrumentRepository()
    ranking_repo = RankingRepository()
    return RankingService(ranking_repo, instrument_repo)


@router.get("/countries")
async def get_country_rankings() -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for all country indices, sorted by score descending."""
    try:
        service = _get_ranking_service()
        items = await service.get_country_rankings()
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
async def get_sector_rankings(country_code: str) -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for sectors within a country."""
    try:
        service = _get_ranking_service()
        items = await service.get_sector_rankings(country_code)
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
    country_code: str, sector: str
) -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for stocks in a country+sector."""
    try:
        service = _get_ranking_service()
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
async def get_global_sector_rankings() -> ApiResponse[list[RankingItem]]:
    """Return RS rankings for global sector ETFs."""
    try:
        service = _get_ranking_service()
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
