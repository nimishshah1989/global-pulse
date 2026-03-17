"""Opportunity service — business logic for opportunity signal retrieval."""

import logging
from typing import Any

from models.opportunities import (
    MultiLevelAlignmentResponse,
    OpportunityResponse,
)
from repositories.opportunity_repo import OpportunityRepository

logger = logging.getLogger(__name__)


class OpportunityService:
    """Service layer for opportunity signal queries."""

    def __init__(self, repo: OpportunityRepository) -> None:
        """Initialize with an opportunity repository.

        Args:
            repo: OpportunityRepository instance for data access.
        """
        self._repo = repo

    async def get_opportunities(
        self,
        signal_type: str | None = None,
        min_conviction: float | None = None,
        hierarchy_level: int | None = None,
        limit: int = 50,
    ) -> list[OpportunityResponse]:
        """Retrieve filtered opportunity signals.

        Args:
            signal_type: Optional filter by signal type.
            min_conviction: Optional minimum conviction score.
            hierarchy_level: Optional hierarchy level filter.
            limit: Maximum results to return.

        Returns:
            List of OpportunityResponse models.
        """
        raw = await self._repo.get_latest(
            limit=limit,
            signal_type=signal_type,
            min_conviction=min_conviction,
            hierarchy_level=hierarchy_level,
        )
        return [OpportunityResponse(**item) for item in raw]

    async def get_multi_level_alignments(
        self, limit: int = 20
    ) -> list[MultiLevelAlignmentResponse]:
        """Retrieve only multi-level alignment signals.

        Args:
            limit: Maximum results to return.

        Returns:
            List of MultiLevelAlignmentResponse models.
        """
        raw = await self._repo.get_multi_level_alignments(limit=limit)
        results: list[MultiLevelAlignmentResponse] = []
        for item in raw:
            meta: dict[str, Any] = item.get("metadata", {})
            results.append(
                MultiLevelAlignmentResponse(
                    id=item["id"],
                    date=item["date"],
                    conviction_score=item["conviction_score"],
                    description=item["description"],
                    country_id=meta.get("country_id", ""),
                    country_name=meta.get("country_name", ""),
                    country_quadrant=meta.get("country_quadrant", ""),
                    sector_id=meta.get("sector_id", ""),
                    sector_name=meta.get("sector_name", ""),
                    sector_quadrant=meta.get("sector_quadrant", ""),
                    stock_id=meta.get("stock_id", ""),
                    stock_name=meta.get("stock_name", ""),
                    stock_quadrant=meta.get("stock_quadrant", ""),
                )
            )
        return results
