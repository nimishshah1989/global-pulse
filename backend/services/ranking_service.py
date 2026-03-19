"""Ranking service v2 — business logic for RS score rankings."""

from __future__ import annotations
import logging
from datetime import date

from models.rs_scores import RankingItemV2
from repositories.instrument_repo import VALID_COUNTRY_CODES, InstrumentRepository
from repositories.ranking_repo import RankingRepository

logger = logging.getLogger(__name__)


class RankingService:
    """Service layer for v2 ranking operations."""

    def __init__(
        self,
        ranking_repo: RankingRepository,
        instrument_repo: InstrumentRepository,
    ) -> None:
        self._ranking_repo = ranking_repo
        self._instrument_repo = instrument_repo

    def _validate_country_code(self, country_code: str) -> None:
        upper = country_code.upper()
        if upper not in VALID_COUNTRY_CODES:
            raise ValueError(
                f"Invalid country code '{country_code}'. "
                f"Valid codes: {sorted(VALID_COUNTRY_CODES)}"
            )

    async def get_country_rankings(
        self, as_of: date | None = None, benchmark: str | None = None,
    ) -> list[RankingItemV2]:
        raw = await self._ranking_repo.get_country_rankings(
            as_of=as_of, benchmark=benchmark,
        )
        return [RankingItemV2(**item) for item in raw]

    async def get_sector_rankings(
        self, country_code: str, as_of: date | None = None,
        benchmark: str | None = None,
    ) -> list[RankingItemV2]:
        self._validate_country_code(country_code)
        raw = await self._ranking_repo.get_sector_rankings(
            country_code.upper(), as_of=as_of, benchmark=benchmark,
        )
        return [RankingItemV2(**item) for item in raw]

    async def get_stock_rankings(
        self, country_code: str, sector: str,
        benchmark: str | None = None,
    ) -> list[RankingItemV2]:
        self._validate_country_code(country_code)
        raw = await self._ranking_repo.get_stock_rankings(
            country_code.upper(), sector.lower(), benchmark=benchmark,
        )
        return [RankingItemV2(**item) for item in raw]

    async def get_global_sector_rankings(
        self, benchmark: str | None = None,
    ) -> list[RankingItemV2]:
        raw = await self._ranking_repo.get_global_sector_rankings(
            benchmark=benchmark,
        )
        return [RankingItemV2(**item) for item in raw]

    async def get_all_etf_rankings(self) -> list[RankingItemV2]:
        raw = await self._ranking_repo.get_all_etf_rankings()
        return [RankingItemV2(**item) for item in raw]

    async def get_top_etfs(
        self,
        action_filter: str | None = None,
        country_filter: str | None = None,
        sector_filter: str | None = None,
        limit: int = 50,
    ) -> list[RankingItemV2]:
        raw = await self._ranking_repo.get_top_etfs(
            action_filter=action_filter,
            country_filter=country_filter,
            sector_filter=sector_filter,
            limit=limit,
        )
        return [RankingItemV2(**item) for item in raw]
