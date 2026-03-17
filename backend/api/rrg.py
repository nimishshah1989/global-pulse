"""RRG (Relative Rotation Graph) scatter data endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.common import ApiResponse, Meta
from models.rs_scores import RRGDataPoint
from repositories.rrg_repo import RRGRepository
from services.rrg_service import RRGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rrg", tags=["rrg"])


def _get_rrg_service(session: AsyncSession) -> RRGService:
    """Build the RRG service with DB-backed repository."""
    rrg_repo = RRGRepository(session)
    return RRGService(rrg_repo)


@router.get("/countries")
async def get_country_rrg(
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RRGDataPoint]]:
    """Return RRG scatter data for all country indices."""
    try:
        service = _get_rrg_service(session)
        items = await service.get_country_rrg()
        return ApiResponse(
            data=items,
            meta=Meta(
                timestamp=datetime.now(tz=timezone.utc),
                count=len(items),
            ),
        )
    except Exception as exc:
        logger.exception("Error fetching country RRG data")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/{country_code}")
async def get_sector_rrg(
    country_code: str,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RRGDataPoint]]:
    """Return RRG scatter data for sectors within a country."""
    try:
        service = _get_rrg_service(session)
        items = await service.get_sector_rrg(country_code)
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
        logger.exception("Error fetching sector RRG data for %s", country_code)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stocks/{country_code}/{sector}")
async def get_stock_rrg(
    country_code: str,
    sector: str,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[RRGDataPoint]]:
    """Return RRG scatter data for stocks in a country+sector."""
    try:
        service = _get_rrg_service(session)
        items = await service.get_stock_rrg(country_code, sector)
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
            "Error fetching stock RRG data for %s/%s", country_code, sector
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
