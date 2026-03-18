"""Ranking service -- business logic for RS score rankings.

Validates inputs and delegates to the ranking repository.
"""

import logging
from datetime import date

from models.rs_scores import RankingItem
from repositories.instrument_repo import VALID_COUNTRY_CODES, InstrumentRepository
from repositories.ranking_repo import RankingRepository

logger = logging.getLogger(__name__)


class RankingService:
    """Service layer for ranking operations with input validation."""

    def __init__(
        self,
        ranking_repo: RankingRepository,
        instrument_repo: InstrumentRepository,
    ) -> None:
        """Initialize with ranking and instrument repositories."""
        self._ranking_repo = ranking_repo
        self._instrument_repo = instrument_repo

    def _validate_country_code(self, country_code: str) -> None:
        """Validate that a country code is supported.

        Raises:
            ValueError: If the country code is not in the valid set.
        """
        upper = country_code.upper()
        if upper not in VALID_COUNTRY_CODES:
            raise ValueError(
                f"Invalid country code '{country_code}'. "
                f"Valid codes: {sorted(VALID_COUNTRY_CODES)}"
            )

    async def get_country_rankings(
        self, as_of: date | None = None
    ) -> list[RankingItem]:
        """Return RS rankings for all country indices."""
        raw = await self._ranking_repo.get_country_rankings(as_of=as_of)
        return [RankingItem(**item) for item in raw]

    async def get_sector_rankings(
        self, country_code: str, as_of: date | None = None
    ) -> list[RankingItem]:
        """Return RS rankings for sectors within a country.

        Raises:
            ValueError: If country_code is invalid.
        """
        self._validate_country_code(country_code)
        raw = await self._ranking_repo.get_sector_rankings(
            country_code.upper(), as_of=as_of
        )
        return [RankingItem(**item) for item in raw]

    async def get_stock_rankings(
        self, country_code: str, sector: str
    ) -> list[RankingItem]:
        """Return RS rankings for stocks in a country+sector.

        Raises:
            ValueError: If country_code is invalid.
        """
        self._validate_country_code(country_code)
        raw = await self._ranking_repo.get_stock_rankings(
            country_code.upper(), sector.lower()
        )
        return [RankingItem(**item) for item in raw]

    async def get_global_sector_rankings(self) -> list[RankingItem]:
        """Return RS rankings for global sector ETFs."""
        raw = await self._ranking_repo.get_global_sector_rankings()
        return [RankingItem(**item) for item in raw]
