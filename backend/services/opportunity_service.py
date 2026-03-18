"""Opportunity service — business logic for opportunity signal retrieval."""

from __future__ import annotations
import logging
from models.opportunities import OpportunityResponse
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
    ) -> list[OpportunityResponse]:
        """Retrieve only multi-level alignment signals.

        Returns them as OpportunityResponse so the frontend can consume
        them using the same Opportunity type (with metadata containing the
        alignment chain).

        Args:
            limit: Maximum results to return.

        Returns:
            List of OpportunityResponse models.
        """
        raw = await self._repo.get_multi_level_alignments(limit=limit)
        return [OpportunityResponse(**item) for item in raw]
