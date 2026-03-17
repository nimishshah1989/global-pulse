"""RRG service -- business logic for Relative Rotation Graph data.

Validates inputs and delegates to the RRG repository.
"""

import logging

from models.rs_scores import RRGDataPoint, RRGTrailPoint
from repositories.instrument_repo import VALID_COUNTRY_CODES
from repositories.rrg_repo import RRGRepository

logger = logging.getLogger(__name__)


class RRGService:
    """Service layer for RRG scatter plot operations."""

    def __init__(self, rrg_repo: RRGRepository) -> None:
        """Initialize with an RRG repository."""
        self._rrg_repo = rrg_repo

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

    def _to_data_point(self, raw: dict) -> RRGDataPoint:
        """Convert a raw dict from the repository into an RRGDataPoint."""
        trail = [RRGTrailPoint(**t) for t in raw.get("trail", [])]
        return RRGDataPoint(
            id=raw["id"],
            name=raw["name"],
            rs_score=raw["rs_score"],
            rs_momentum=raw["rs_momentum"],
            quadrant=raw.get("quadrant"),
            trail=trail,
        )

    async def get_country_rrg(self) -> list[RRGDataPoint]:
        """Return RRG scatter data for all country indices."""
        raw = await self._rrg_repo.get_country_rrg()
        return [self._to_data_point(r) for r in raw]

    async def get_sector_rrg(self, country_code: str) -> list[RRGDataPoint]:
        """Return RRG scatter data for sectors within a country.

        Raises:
            ValueError: If country_code is invalid.
        """
        self._validate_country_code(country_code)
        raw = await self._rrg_repo.get_sector_rrg(country_code.upper())
        return [self._to_data_point(r) for r in raw]

    async def get_stock_rrg(
        self, country_code: str, sector: str
    ) -> list[RRGDataPoint]:
        """Return RRG scatter data for stocks in a country+sector.

        Raises:
            ValueError: If country_code is invalid.
        """
        self._validate_country_code(country_code)
        raw = await self._rrg_repo.get_stock_rrg(
            country_code.upper(), sector.lower()
        )
        return [self._to_data_point(r) for r in raw]
