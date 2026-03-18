"""Opportunity signal endpoints.

Provides filtered access to auto-generated trading signals and
multi-level alignment opportunities. DB-backed with mock fallback.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.common import ApiResponse, Meta
from models.opportunities import OpportunityResponse
from repositories.opportunity_repo import OpportunityRepository
from services.opportunity_service import OpportunityService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _get_service(session: AsyncSession) -> OpportunityService:
    """Build the opportunity service with DB-backed repository."""
    repo = OpportunityRepository(session)
    return OpportunityService(repo)


@router.get("")
async def list_opportunities(
    signal_type: str | None = Query(None, description="Filter by signal type"),
    min_conviction: float | None = Query(
        None, description="Minimum conviction score (0-100)"
    ),
    hierarchy_level: int | None = Query(
        None, description="Filter by hierarchy level (1, 2, or 3)"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OpportunityResponse]]:
    """List opportunity signals with optional filters."""
    service = _get_service(session)
    items = await service.get_opportunities(
        signal_type=signal_type,
        min_conviction=min_conviction,
        hierarchy_level=hierarchy_level,
        limit=limit,
    )
    return ApiResponse(
        data=items,
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=len(items),
        ),
    )


@router.get("/multi-level")
async def get_multi_level_alignments(
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OpportunityResponse]]:
    """Return only multi-level alignment signals.

    These are the highest-conviction outputs showing the full chain:
    Country LEADING -> Sector LEADING -> Stock LEADING.
    """
    service = _get_service(session)
    items = await service.get_multi_level_alignments(limit=limit)
    return ApiResponse(
        data=items,
        meta=Meta(
            timestamp=datetime.now(tz=timezone.utc),
            count=len(items),
        ),
    )
